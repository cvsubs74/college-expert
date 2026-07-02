"""Major Strategy phase 2 (#284, epic #280): the two billed LLM artifacts.

- Major Map (POST /generate-major-map, 1 credit, reason 'major_map'):
  student profile → 3-6 career-theme clusters that cite the student's OWN
  courses/APs/ECs/awards as evidence, each with majors tagged
  core/adjacent/strategic_alternative. Pure counselor inference
  (basis 'inference') — the prompt forbids school-specific claims, admit
  rates, and any number not present in the profile.

- Per-school Major Strategy (POST /generate-major-strategy, 1 credit, reason
  'major_strategy'): constrained synthesis over ONLY the KB's trust-labeled
  extract (?action=majors) + the flat student profile — never the raw
  50-150KB university profile. Every fact line the LLM sees is tagged
  [VERIFIED]/[REPORTED]/[OPINION]/[MISSING]; a deterministic post-hoc
  validator strips any %/GPA figure the extract doesn't contain
  (validate_numeric_claims), and a belt-and-suspenders guard appends the
  capped_door door-lock warning when the LLM didn't (ensure_door_lock_warning).

Billing rides generation_billing.run_billed_generation (check → 402 →
generate → deduct exactly once after success). The two free reads and the
never-charge-on-miss path run BEFORE that gate: a KB miss returns
200 {strategy: null, gaps} unbilled and increments kb_gaps/{university_id} —
the demand signal that prioritizes collection (#193).
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from google import genai

from firestore_db import get_db
from fit_computation import build_profile_content_from_fields
from gemini_fallback import generate_content_with_fallback
from generation_billing import run_billed_generation
from major_match import match_major

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KNOWLEDGE_BASE_UNIVERSITIES_URL = os.getenv(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app"
)

MODEL = 'gemini-2.5-flash-lite'
MAX_STRATEGY_MAJORS = 4
_RELATIONS = ('core', 'adjacent', 'strategic_alternative')

SYNTHESIS_FIELDS = ('primary_call', 'second_choice_play', 'backup_rationale',
                    'undeclared_tactic', 'essay_implication')


# ---------------------------------------------------------------------------
# KB fetch (sibling of essay_copilot.fetch_university_profile — but a single
# attempt: callers here either degrade gracefully or fail unbilled, so the
# 4-id × 3-retry ladder would only burn the caller's timeout)
# ---------------------------------------------------------------------------

def fetch_university_majors(university_id: str, query: Optional[str] = None,
                            timeout: int = 30) -> Optional[Dict]:
    """The KB's trust-labeled majors extract (?id=X&action=majors).

    Returns the parsed response body (success may be False when the school
    isn't in the KB) or None on transport/JSON failure. Never raises.
    """
    try:
        params = {'id': (university_id or '').strip(), 'action': 'majors'}
        if query:
            params['q'] = query
        r = requests.get(KNOWLEDGE_BASE_UNIVERSITIES_URL, params=params, timeout=timeout)
        data = r.json()
        if data.get('success') and 'colleges' not in data:
            # Deploy skew: an older KB ignores unknown actions and returns a
            # full profile with success:true — refuse to mis-parse it.
            logger.warning("[MAJOR_LLM] KB returned a non-majors payload for %s", university_id)
            return None
        return data
    except Exception as e:
        logger.warning(f"[MAJOR_LLM] majors fetch failed for {university_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Major Map — readiness, fingerprint, prompt, generation
# ---------------------------------------------------------------------------

def check_map_readiness(profile: Optional[Dict]) -> List[str]:
    """Missing-requirements list for the Major Map (empty list = ready).

    Requires grade AND at least 2 of {courses non-empty, extracurriculars
    non-empty, any gpa_* field}. The returned names tell the student what to
    add — the 422 is a guidance surface, not just a refusal.
    """
    profile = profile or {}
    missing = []
    if not (profile.get('grade') or profile.get('grade_level')):
        missing.append('grade')
    present = []
    if profile.get('courses'):
        present.append('courses')
    if profile.get('extracurriculars'):
        present.append('extracurriculars')
    if any(k.startswith('gpa_') and profile.get(k) not in (None, '', 0)
           for k in profile):
        present.append('gpa')
    if len(present) < 2:
        missing.extend(s for s in ('courses', 'extracurriculars', 'gpa')
                       if s not in present)
    return missing


def _item_names(items, keys=('name', 'activity')) -> List[str]:
    names = []
    for it in (items or []):
        if isinstance(it, dict):
            for k in keys:
                if it.get(k):
                    names.append(str(it[k]))
                    break
        elif it:
            names.append(str(it))
    return names


def profile_fingerprint(profile: Optional[Dict]) -> Dict:
    """sha1 over the majors-relevant profile fields, plus per-part hashes so
    get-major-map can say WHAT changed (stale_reasons), not just that
    something did. Parts: intended_majors + course names + EC names + grade."""
    profile = profile or {}
    parts = {
        'intended_majors': sorted(m.strip().lower() for m in (profile.get('intended_majors') or [])
                                  if isinstance(m, str) and m.strip()),
        'courses': sorted(_item_names(profile.get('courses'), ('name',))),
        'extracurriculars': sorted(_item_names(profile.get('extracurriculars'))),
        'grade': str(profile.get('grade') or profile.get('grade_level') or ''),
    }
    part_hashes = {
        k: hashlib.sha1(json.dumps(v, sort_keys=True).encode()).hexdigest()
        for k, v in parts.items()
    }
    combined = hashlib.sha1(
        json.dumps(part_hashes, sort_keys=True).encode()).hexdigest()
    return {'sha1': combined, 'parts': part_hashes}


def _intended_majors(profile: Dict) -> List[str]:
    majors = [m.strip() for m in (profile.get('intended_majors') or [])
              if isinstance(m, str) and m.strip()]
    single = profile.get('intended_major')
    if not majors and isinstance(single, str) and single.strip():
        majors = [single.strip()]
    return majors


def build_major_map_prompt(profile: Dict) -> str:
    """Prompt over the FLAT student profile. Grade-aware tone; pre-professional
    intents translated to real majors; hard anti-fabrication rules."""
    grade = str(profile.get('grade') or profile.get('grade_level') or '')
    intended = _intended_majors(profile)
    if grade in ('9', '10'):
        tone = ("The student is in grade {g} — use an EXPLORATION tone: this map opens "
                "doors and suggests low-stakes ways to test interests; nothing is a "
                "commitment yet.").format(g=grade or '9/10')
    else:
        tone = ("The student is in grade {g} — use a DECISION tone: the map should help "
                "them converge on a coherent candidate set their application record "
                "can support.").format(g=grade or '11/12')

    return f"""You are a private college admissions counselor helping a student discover which majors are worth considering, based ONLY on their own record below.

**STUDENT PROFILE (the only evidence you may use):**
{build_profile_content_from_fields(profile)}

Stated intended major(s): {', '.join(intended) or 'none stated — this is a discovery exercise'}

{tone}

**YOUR TASK:** Produce 3-6 career-theme clusters. Each cluster names a theme the student's record actually supports, explains why in `why_you` by citing the student's OWN courses, APs, extracurriculars, or awards VERBATIM (repeat the exact names in `evidence`), and lists candidate majors with a `relation`:
- "core" — the obvious direct major for this theme
- "adjacent" — a nearby major the student may not have considered
- "strategic_alternative" — a different door to the same career outcomes

Each major gets a one-line `why` and a `watch_out` — a GENERIC caution about that major nationally (e.g. "computer science is capped or restricted at many public flagships"), NEVER a claim about any specific school.

If the stated intents include pre-professional labels like "pre-med", "pre-law", or "business", translate them: pre-med maps to many majors — name the real doors (e.g. Biology, Biochemistry, Neuroscience, Public Health, even Philosophy) and say so.

Close with `questions_to_explore`: 3-6 questions the student should answer next to sharpen this map.

**HARD RULES (violating any of these makes the output unusable):**
1. NEVER name a specific university or make any school-specific claim.
2. NEVER state an admit rate, percentage, GPA cutoff, or ANY number that does not appear verbatim in the student profile above.
3. Every `evidence` entry must be copied from the student's own record above.
4. This entire artifact is counselor inference — write it as judgment, not fact.

**OUTPUT — return ONLY valid JSON, no markdown fences:**
{{
  "clusters": [
    {{
      "theme": "<career-theme name>",
      "why_you": "<2-3 sentences citing the student's own record>",
      "evidence": ["<exact course/AP/EC/award name from the profile>", "..."],
      "majors": [
        {{"name": "<major>", "relation": "core|adjacent|strategic_alternative",
          "why": "<one line>", "watch_out": "<generic caution, never school-specific>"}}
      ]
    }}
  ],
  "questions_to_explore": ["<question>", "..."]
}}"""


def _llm_json(prompt: str) -> Optional[Dict]:
    """Call Gemini (with the shared model-fallback chain) and parse a
    strict-JSON response. Returns the parsed object or None on any failure.
    Tests monkeypatch this seam — no live LLM calls in the suite."""
    if not GEMINI_API_KEY:
        logger.error("[MAJOR_LLM] No GEMINI_API_KEY configured")
        return None
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        # Default chain's primary IS gemini-2.5-flash-lite (MODEL); overloads
        # walk to progressively different capacity pools.
        response = generate_content_with_fallback(client, contents=prompt, config=None)
        text = (response.text or '').strip()
        if text.startswith('```'):
            lines = text.split('\n')
            end = len(lines) - 1 if lines[-1].strip() == '```' else len(lines)
            text = '\n'.join(lines[1:end]).strip()
            if text.startswith('json'):
                text = text[4:].strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"[MAJOR_LLM] LLM call/parse failed: {e}")
        return None


def _normalize_clusters(clusters) -> List[Dict]:
    """Bound and shape-check the LLM's clusters; invalid relations coerce to
    'adjacent' rather than leaking arbitrary labels to the UI."""
    out = []
    for c in (clusters or [])[:6]:
        if not isinstance(c, dict) or not c.get('theme'):
            continue
        majors = []
        for m in (c.get('majors') or [])[:8]:
            if not isinstance(m, dict) or not m.get('name'):
                continue
            majors.append({
                'name': str(m['name']),
                'relation': m.get('relation') if m.get('relation') in _RELATIONS else 'adjacent',
                'why': str(m.get('why') or ''),
                'watch_out': str(m.get('watch_out') or ''),
            })
        if not majors:
            continue
        out.append({
            'theme': str(c['theme']),
            'why_you': str(c.get('why_you') or ''),
            'evidence': [str(e) for e in (c.get('evidence') or []) if e][:8],
            'majors': majors,
        })
    return out


def run_generate_major_map(data: Dict) -> Tuple[Dict, int]:
    """POST /generate-major-map — readiness 422 (unbilled) → cache-unless-force
    (free) → billed LLM generation with archive-on-overwrite."""
    user_email = data.get('user_email')
    force = bool(data.get('force'))
    db = get_db()

    profile = db.get_profile(user_email)
    missing = check_map_readiness(profile)
    if missing:
        return {'success': False, 'error': 'profile_incomplete',
                'missing': missing}, 422

    fingerprint = profile_fingerprint(profile)
    if not force:
        existing = db.get_major_map(user_email)
        if existing and (existing.get('profile_fingerprint') or {}).get('sha1') == fingerprint['sha1']:
            logger.info(f"[MAJOR_LLM] Returning cached major map for {user_email} (no charge)")
            return {'success': True, 'map': existing, 'from_cache': True}, 200

    def _generate():
        parsed = _llm_json(build_major_map_prompt(profile))
        clusters = _normalize_clusters((parsed or {}).get('clusters'))
        if not clusters:
            return {'success': False,
                    'error': 'map generation failed — try again'}, 500
        map_doc = {
            'clusters': clusters,
            'questions_to_explore': [str(q) for q in (parsed.get('questions_to_explore') or [])
                                     if isinstance(q, str) and q.strip()][:8],
            'generated_at': datetime.utcnow().isoformat(),
            'model': MODEL,
            'basis': 'inference',   # counselor inference — never school facts
            'intended_majors_at_generation': _intended_majors(profile),
            'profile_fingerprint': fingerprint,
        }
        prior = db.get_major_map(user_email)
        if prior:
            # History never destroyed (mirrors fit_analysis archive-on-save);
            # a failed archive logs but doesn't block the save the student paid for.
            db.archive_major_map(user_email, prior)
        if not db.save_major_map(user_email, map_doc):
            return {'success': False,
                    'error': 'map generated but could not be saved — try again'}, 500
        return {'success': True, 'map': map_doc, 'from_cache': False}, 200

    return run_billed_generation(user_email, 'major_map', _generate)


def get_major_map_payload(user_email: str) -> Tuple[Dict, int]:
    """GET /get-major-map (free): {success, map|null, stale, stale_reasons}."""
    db = get_db()
    map_doc = db.get_major_map(user_email)
    if not map_doc:
        return {'success': True, 'map': None, 'stale': False, 'stale_reasons': []}, 200
    stale_reasons = []
    stored = map_doc.get('profile_fingerprint') or {}
    if stored.get('sha1'):
        current = profile_fingerprint(db.get_profile(user_email))
        if stored['sha1'] != current['sha1']:
            stored_parts = stored.get('parts') or {}
            stale_reasons = [f'{k} changed since this map was generated'
                             for k, v in current['parts'].items()
                             if stored_parts.get(k) != v] or ['profile changed since this map was generated']
    return {'success': True, 'map': map_doc,
            'stale': bool(stale_reasons), 'stale_reasons': stale_reasons}, 200


# ---------------------------------------------------------------------------
# Per-school Major Strategy — major resolution, fact filtering, labeled
# extract, numeric-claim validator, door-lock guard, generation
# ---------------------------------------------------------------------------

def resolve_strategy_majors(data: Dict, profile: Dict,
                            list_item: Optional[Dict]) -> Tuple[List[str], Optional[str]]:
    """Majors considered for the strategy: explicit request majors[] (≤4),
    else the school's saved major_choice.primary ∪ profile.intended_majors,
    deduped case-insensitively, capped at 4. Returns (majors, error)."""
    requested = data.get('majors')
    if requested is not None:
        if not isinstance(requested, list):
            return [], 'majors must be a list of strings'
        cleaned, seen = [], set()
        for m in requested:
            if not isinstance(m, str) or not m.strip():
                continue
            key = m.strip().lower()
            if key not in seen:
                seen.add(key)
                cleaned.append(m.strip())
        if not cleaned:
            return [], 'majors must be a non-empty list of strings'
        if len(cleaned) > MAX_STRATEGY_MAJORS:
            return [], f'at most {MAX_STRATEGY_MAJORS} majors (got {len(cleaned)})'
        return cleaned, None

    majors, seen = [], set()
    choice = (list_item or {}).get('major_choice')
    primary = choice.get('primary') if isinstance(choice, dict) else None
    for m in [primary] + _intended_majors(profile or {}):
        if not isinstance(m, str) or not m.strip():
            continue
        key = m.strip().lower()
        if key not in seen:
            seen.add(key)
            majors.append(m.strip())
    return majors[:MAX_STRATEGY_MAJORS], None


def filter_facts_to_majors(facts: Dict, majors_considered: List[str]) -> Tuple[List[Dict], List[Dict], List[str]]:
    """Filter the KB extract to the majors considered.

    Returns (matched, related, gaps):
    - matched: rows bound with exact/strong confidence (a fuzzy bind risks the
      WRONG door's facts headlining a paid strategy — those surface as related
      instead, per the phase-1 binding rule).
    - related: near-miss rows from the same colleges as the matches — the
      backup candidates the synthesis may draw on.
    - gaps: considered names with no exact/strong bind.
    """
    rows_by_name, college_of = {}, {}
    for c in (facts.get('colleges') or []):
        for m in (c.get('majors') or []):
            if isinstance(m, dict) and m.get('name'):
                rows_by_name[m['name']] = m
                college_of[m['name']] = c

    names = list(rows_by_name)
    matched, gaps = [], []
    matched_names, near_names = set(), []
    for q in majors_considered:
        res = match_major(q, names)
        if res['confidence'] in ('exact', 'strong'):
            kb_name = res['kb_major_name']
            if kb_name not in matched_names:
                matched_names.add(kb_name)
                college = college_of[kb_name]
                row = dict(rows_by_name[kb_name])
                row['requested_as'] = q
                row['college'] = college.get('name')
                row['college_context'] = {
                    'admissions_model': college.get('admissions_model'),
                    'is_restricted_or_capped': college.get('is_restricted_or_capped'),
                    'acceptance_rate_estimate': college.get('acceptance_rate_estimate'),
                    'strategic_fit_advice': college.get('strategic_fit_advice'),
                }
                matched.append(row)
        else:
            gaps.append(q)
        for nm in (res.get('near_misses') or []):
            if nm not in near_names:
                near_names.append(nm)

    # Backup candidates: sibling majors from the same college as a match
    # (exact matches return no near_misses, but the same-college siblings ARE
    # the backup set the synthesis should weigh), then matcher near-misses.
    matched_colleges = {r['college'] for r in matched}
    sibling_names = [name for name, college in college_of.items()
                     if college.get('name') in matched_colleges]
    related = []
    for nm in sibling_names + near_names:
        if nm in matched_names or nm not in rows_by_name:
            continue
        if any(r['name'] == nm for r in related):
            continue
        college = college_of[nm]
        if matched and college.get('name') not in matched_colleges:
            continue  # backups come from the same college as a match
        row = dict(rows_by_name[nm])
        row['college'] = college.get('name')
        row['related'] = True
        related.append(row)
        if len(related) >= 6:
            break
    return matched, related, gaps


def _fact_tag(basis: Optional[str], verified: bool) -> str:
    if basis == 'kb_verified':
        return '[VERIFIED]'
    if basis == 'opinion':
        return '[OPINION]'
    if basis == 'kb_reported':
        return '[REPORTED]'
    return '[VERIFIED]' if verified else '[REPORTED]'


def build_labeled_extract(facts: Dict, matched: List[Dict], related: List[Dict]) -> str:
    """Deterministic fact sheet for the synthesis prompt. Every line carries a
    trust tag; held-nulls become explicit [MISSING] lines (the school doesn't
    publish it — never blank, never estimated)."""
    verified = facts.get('verification_status') == 'verified'
    lines = [
        f"SCHOOL: {facts.get('official_name') or facts.get('university_id')}",
        f"KB data year: {facts.get('data_year')}; verification: "
        f"{facts.get('verification_status')}; richness tier {facts.get('richness_tier')}",
    ]
    seen_colleges = set()

    def _row_lines(row, related_row=False):
        header = f"MAJOR: {row.get('name')}"
        if row.get('college'):
            header += f" (in {row['college']})"
        if related_row:
            header += " — RELATED/BACKUP candidate, not one the student asked about"
        lines.append(header)

        ep = row.get('entry_path') or {}
        ep_value = ep.get('value') if isinstance(ep, dict) else ep
        ep_raw = ep.get('raw') if isinstance(ep, dict) else None
        ep_tag = _fact_tag(ep.get('basis') if isinstance(ep, dict) else None, verified)
        if ep_value and ep_value != 'unclear':
            line = f"  {ep_tag} entry_path: {ep_value}"
            if ep_raw:
                line += f' (school\'s wording: "{ep_raw}")'
            lines.append(line)
        elif ep_raw:
            lines.append(f'  [MISSING] entry_path unclear — the school\'s own wording: "{ep_raw}"')
        else:
            lines.append('  [MISSING] entry_path: the school does not publish how this major is entered')

        risk = row.get('entry_risk')
        if risk == 'capped_door':
            lines.append(f"  {_fact_tag(None, verified)} entry_risk: capped_door — if not admitted "
                         "directly, the student CANNOT switch into this major later")
        elif risk:
            lines.append(f"  {_fact_tag(None, verified)} entry_risk: {risk}")

        door = row.get('door_policy') or {}
        door_tag = _fact_tag(door.get('basis'), verified)
        for key, label in (('direct_admit_only', 'direct admit only'),
                           ('internal_transfer_allowed', 'internal transfer allowed'),
                           ('internal_transfer_gpa', 'internal transfer GPA bar')):
            val = door.get(key)
            if val is None:
                lines.append(f"  [MISSING] {label}: not published")
            else:
                lines.append(f"  {door_tag} {label}: {val}")

        imp = row.get('is_impacted') or {}
        imp_value = imp.get('value') if isinstance(imp, dict) else imp
        if imp_value is True:
            lines.append(f"  {_fact_tag(imp.get('basis') if isinstance(imp, dict) else None, verified)} "
                         "officially impacted: yes")
        elif imp_value is False:
            lines.append(f"  {_fact_tag(imp.get('basis') if isinstance(imp, dict) else None, verified)} "
                         "no official impaction designation (does NOT mean easy entry — use entry_risk)")
        else:
            lines.append("  [MISSING] impaction status: not published")

        reported = row.get('reported_stats')
        if isinstance(reported, dict):
            for k, v in reported.items():
                if k != 'basis' and v not in (None, '', []):
                    lines.append(f"  [REPORTED] {k}: {v} (unverified legacy data — hedge)")
        else:
            lines.append("  [MISSING] per-major admit rate: the school does not publish this")

        prereqs = row.get('prerequisite_courses') or []
        if prereqs:
            lines.append(f"  {_fact_tag(None, verified)} prerequisite courses: {', '.join(str(p) for p in prereqs[:8])}")

        ctx = row.get('college_context') or {}
        college_name = row.get('college')
        if college_name and college_name not in seen_colleges:
            seen_colleges.add(college_name)
            if ctx.get('admissions_model'):
                lines.append(f"  {_fact_tag(None, verified)} college admissions model: {ctx['admissions_model']}")
            if ctx.get('is_restricted_or_capped') is True:
                lines.append(f"  {_fact_tag(None, verified)} college is restricted/capped: yes")
            est = ctx.get('acceptance_rate_estimate')
            if isinstance(est, dict) and est.get('value') not in (None, ''):
                lines.append(f"  [REPORTED] college acceptance estimate: {est['value']} (unverified)")
            advice = ctx.get('strategic_fit_advice')
            if isinstance(advice, dict) and advice.get('text'):
                lines.append(f"  [OPINION] counselor note on this college: {advice['text']}")

    for row in matched:
        _row_lines(row)
    for row in related:
        _row_lines(row, related_row=True)

    notes = facts.get('strategy_notes') or {}
    tactics = (notes.get('major_selection_tactics') or {}).get('items') or []
    for t in tactics[:6]:
        lines.append(f"[OPINION] school-level tactic: {t}")
    alt = (notes.get('alternate_major_strategy') or {}).get('text')
    if alt:
        lines.append(f"[OPINION] alternate-major strategy: {alt}")
    for note in (facts.get('data_notes') or []):
        lines.append(f"[NOTE] {note}")
    return '\n'.join(lines)


# --- numeric-claim validator (hard AC — deterministic, unit-tested) ----------

_PCT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(?:%|％|percent\b)', re.IGNORECASE)
_GPA_RE = re.compile(r'\b(\d\.\d+)\b')
_NUM_RE = re.compile(r'\d+(?:\.\d+)?')
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

# Extract lines whose numbers must NOT legitimize synthesis claims: the
# metadata header (KB data year / richness tier — review F2: 'tier 2' was
# whitelisting a fabricated '2%') and prose notes.
_EXTRACT_METADATA_PREFIXES = ('SCHOOL:', 'KB data year:', '[NOTE]')


def _allowed_pools(extract_text: str) -> tuple:
    """(pct_pool, gpa_pool) built from FACT lines only, type-separated:
    a GPA bar in the extract must not legitimize a percent claim and vice
    versa (review F2 — '3.5 GPA' was whitelisting a fabricated '3.5%')."""
    pct_pool, gpa_pool = set(), set()
    for line in (extract_text or '').splitlines():
        stripped = line.strip()
        if any(stripped.startswith(pfx) for pfx in _EXTRACT_METADATA_PREFIXES):
            continue
        nums = {str(float(n)) for n in _NUM_RE.findall(line)}
        if 'gpa' in line.lower():
            gpa_pool |= nums
        else:
            pct_pool |= nums
    return pct_pool, gpa_pool


def _sentence_numeric_tokens(sentence: str) -> List[tuple]:
    """The (kind, token) pairs this validator polices: percent figures and
    decimal GPA-like tokens. Plain integers ('top 3', 'two essays') never
    count. Percent matches are removed before GPA scanning so '4.9%' isn't
    double-counted as a GPA."""
    pct = [('pct', m.group(1)) for m in _PCT_RE.finditer(sentence)]
    rest = _PCT_RE.sub(' ', sentence)
    gpa = [('gpa', m.group(1)) for m in _GPA_RE.finditer(rest)]
    return pct + gpa


def validate_numeric_claims(synthesis: Dict, extract_text: str) -> Tuple[Dict, List[str]]:
    """Anti-fabrication pass over every synthesis string field: any sentence
    carrying a %/GPA token NOT present in the labeled extract is removed and
    logged into the returned data notes. Deterministic — no LLM judgment.

    Returns (cleaned_synthesis, stripped_notes)."""
    pct_pool, gpa_pool = _allowed_pools(extract_text)
    notes = []

    def _clean_text(text: str) -> str:
        kept = []
        for sentence in _SENTENCE_SPLIT_RE.split(text):
            bad = [t for kind, t in _sentence_numeric_tokens(sentence)
                   if str(float(t)) not in (pct_pool if kind == 'pct' else gpa_pool)]
            if bad:
                logger.warning("[MAJOR_LLM] stripped unverifiable numeric claim "
                               f"({', '.join(bad)}): {sentence.strip()!r}")
                notes.append('Removed an unverifiable numeric claim from the '
                             f'synthesis: "{sentence.strip()}"')
            else:
                kept.append(sentence)
        return ' '.join(kept).strip()

    cleaned = {}
    for key, value in synthesis.items():
        if isinstance(value, str):
            cleaned[key] = _clean_text(value)
        elif isinstance(value, list):
            items = [_clean_text(v) if isinstance(v, str) else v for v in value]
            cleaned[key] = [v for v in items if v not in ('', None)]
        else:
            cleaned[key] = value
    return cleaned, notes


# --- deterministic capped_door guard (belt-and-suspenders) --------------------

# Only NEGATED/locking phrasings count as an existing warning — neutral
# 'switch into X later' is the backdoor RECOMMENDATION this guard exists to
# counter, and must not suppress it (review F3).
_DOOR_LOCK_MARKERS = (
    "can't switch", 'cannot switch', 'door locks', 'locks behind',
    'direct admit only', 'direct-admit only', 'no internal transfer',
    'not admitted directly', "can't transfer in", 'cannot transfer in',
    'transfers are not permitted', 'no side door',
)


def ensure_door_lock_warning(synthesis: Dict, capped_majors: List[str]) -> Tuple[Dict, bool]:
    """If a considered major is capped_door and NO synthesis field already
    carries a door-lock warning, APPEND a deterministic one to primary_call —
    the anti-backdoor AC must hold even when the LLM ignores the prompt.
    Runs AFTER the numeric validator (the warning itself is number-free)."""
    if not capped_majors:
        return synthesis, False
    blob_parts = []
    for value in synthesis.values():
        if isinstance(value, str):
            blob_parts.append(value)
        elif isinstance(value, list):
            blob_parts.extend(v for v in value if isinstance(v, str))
    blob = ' '.join(blob_parts).lower()
    if any(marker in blob for marker in _DOOR_LOCK_MARKERS):
        return synthesis, False
    names = ', '.join(capped_majors)
    warning = (f"Heads up: {names} at this school locks its door — if you're not "
               "admitted to it directly, you can't switch in later. Never plan an "
               "apply-easier-then-transfer route here, and make sure your application "
               "and essays cohere with the major you list.")
    primary = (synthesis.get('primary_call') or '').strip()
    synthesis['primary_call'] = f"{primary} {warning}".strip()
    return synthesis, True


def build_strategy_prompt(extract_text: str, profile: Dict,
                          majors_considered: List[str]) -> str:
    grade = str(profile.get('grade') or profile.get('grade_level') or 'unknown')
    return f"""You are a private college admissions counselor advising a student on which major to LIST when applying to ONE school. You must reason ONLY from the labeled fact extract below — it is everything our knowledge base knows about entering these majors at this school.

**LABELED FACT EXTRACT (your ONLY source of school facts):**
{extract_text}

**STUDENT (grade {grade}):**
{build_profile_content_from_fields(profile)}

Majors the student is considering here: {', '.join(majors_considered)}

**HOW TO READ THE TAGS:**
- [VERIFIED] — quote-backed official data; cite plainly.
- [REPORTED] — unverified legacy data; hedge it ("students report…", "reportedly…").
- [OPINION] — counselor take; present as judgment.
- [MISSING] — the school does not publish this; SAY SO. Never estimate or fill it in.

**HARD RULES:**
1. NEVER state a percentage, admit rate, GPA, or any number that does not appear in the extract above. If a number is [MISSING], say the school doesn't publish it.
2. Frame every recommendation as counselor judgment ("my read", "I'd list…"), not fact.
3. ANTI-BACKDOOR: when a considered major's entry_risk is capped_door, you MUST warn that the door locks — if the student isn't admitted directly they cannot switch in later. NEVER recommend applying to an easier major planning to transfer in. Note that the essays must cohere with the listed major (admissions reads interest-fit).
4. SCHOOL-TYPE: when the extract shows the school admits by university rather than by major (open_declaration paths dominate, or the admissions model says university-level admission), say plainly that the listed major barely affects admission here — do not invent tactics with false gravity.

**OUTPUT — return ONLY valid JSON, no markdown fences:**
{{
  "primary_call": "<which major to list and why — the headline read>",
  "second_choice_play": "<how to use a second-choice major on this application, or why not to>",
  "backup_rationale": "<which on-campus backup makes sense and why (use RELATED/BACKUP rows if helpful)>",
  "undeclared_tactic": "<whether applying undeclared/undecided is a real option here and the tradeoff>",
  "essay_implication": "<what the major choice means for the essays — what story must cohere>",
  "what_to_verify_yourself": ["<specific thing to confirm on the school's official pages>", "..."]
}}"""


def run_generate_major_strategy(data: Dict) -> Tuple[Dict, int]:
    """POST /generate-major-strategy — deterministic extraction FIRST (free),
    so a KB miss returns 200 {strategy:null, gaps} without ever touching the
    credit gate, then billed synthesis with archive-on-overwrite."""
    user_email = data.get('user_email')
    university_id = data.get('university_id')
    db = get_db()

    profile = db.get_profile(user_email) or {}
    list_item = db.get_college_list_item(user_email, university_id)
    majors_considered, err = resolve_strategy_majors(data, profile, list_item)
    if err:
        return {'success': False, 'error': err}, 400
    if not majors_considered:
        return {'success': False,
                'error': 'no majors to strategize — set intended majors or pass majors[]'}, 400

    facts = fetch_university_majors(university_id)
    if facts is None:
        return {'success': False,
                'error': f'knowledge base unavailable for {university_id} — try again'}, 502
    if not facts.get('success'):
        return {'success': False,
                'error': facts.get('error') or f'university {university_id} not found'}, 404

    matched, related, gaps = filter_facts_to_majors(facts, majors_considered)
    if not matched:
        # Never charge for "we don't know" (hard AC) — and record the demand
        # signal that prioritizes this school's collection (#193).
        db.increment_kb_gap(university_id, majors_considered)
        logger.info(f"[MAJOR_LLM] KB gap for {university_id}: {majors_considered} (no charge)")
        return {
            'success': True,
            'strategy': None,
            'gaps': gaps,
            'note': ('our knowledge base has no entry-path data for these majors at '
                     'this school yet — nothing was charged, and the gap is now on '
                     'the collection priority list'),
        }, 200

    def _generate():
        extract_text = build_labeled_extract(facts, matched, related)
        parsed = _llm_json(build_strategy_prompt(extract_text, profile, majors_considered))
        if not isinstance(parsed, dict) or not (parsed.get('primary_call') or '').strip():
            return {'success': False,
                    'error': 'strategy generation failed — try again'}, 500
        synthesis = {k: str(parsed.get(k) or '') for k in SYNTHESIS_FIELDS}
        synthesis['what_to_verify_yourself'] = [
            str(v) for v in (parsed.get('what_to_verify_yourself') or [])
            if isinstance(v, str) and v.strip()][:8]

        synthesis, stripped_notes = validate_numeric_claims(synthesis, extract_text)
        if not (synthesis.get('primary_call') or '').strip():
            # The validator wiped the headline (everything in it was
            # fabricated numbers) — that's a failed generation, and a failed
            # generation is never billed (review F6).
            return {'success': False,
                    'error': 'strategy generation failed — try again'}, 500
        capped = [r['name'] for r in matched if r.get('entry_risk') == 'capped_door']
        synthesis, warning_appended = ensure_door_lock_warning(synthesis, capped)

        strategy_doc = {
            'university_id': university_id,
            'facts': {'matched': matched, 'related': related, 'extract': extract_text},
            'synthesis': synthesis,
            'gaps': gaps,
            'data_notes': list(facts.get('data_notes') or []) + stripped_notes,
            'kb_data_year': facts.get('data_year'),
            'verification_status': facts.get('verification_status'),
            'richness_tier': facts.get('richness_tier'),
            'majors_considered': majors_considered,
            'intended_majors_at_generation': _intended_majors(profile),
            'generated_at': datetime.utcnow().isoformat(),
            'model': MODEL,
            'basis': 'inference over labeled KB facts',
            'door_lock_warning_appended': warning_appended,
        }
        prior = db.get_major_strategy(user_email, university_id)
        if prior:
            history_key = str(prior.get('kb_data_year') or 'pre-versioning')
            db.archive_major_strategy(user_email, university_id, prior, history_key)
        if not db.save_major_strategy(user_email, university_id, strategy_doc):
            return {'success': False,
                    'error': 'strategy generated but could not be saved — try again'}, 500
        return {'success': True, 'strategy': strategy_doc, 'gaps': gaps}, 200

    return run_billed_generation(user_email, 'major_strategy', _generate)


def get_major_strategy_payload(user_email: str, university_id: str) -> Tuple[Dict, int]:
    """GET /get-major-strategy (free): {success, strategy|null, stale}.
    stale = the saved strategy's kb_data_year is older than the KB doc's
    current data_year (read cheaply off the action=majors envelope; a failed
    check degrades to stale:false rather than blocking the read)."""
    db = get_db()
    strategy = db.get_major_strategy(user_email, university_id)
    if not strategy:
        return {'success': True, 'strategy': None, 'stale': False}, 200
    stale = False
    current_year = None
    facts = fetch_university_majors(university_id, timeout=15)
    if facts and facts.get('success'):
        current_year = facts.get('data_year')
        try:
            if current_year is not None and strategy.get('kb_data_year') is not None:
                stale = int(strategy['kb_data_year']) < int(current_year)
        except (TypeError, ValueError):
            stale = False
    return {'success': True, 'strategy': strategy, 'stale': stale,
            'current_kb_year': current_year}, 200


# ---------------------------------------------------------------------------
# set-major-choice enrichment: door_flags for the Launchpad callout (#284)
# ---------------------------------------------------------------------------

def derive_door_flags(majors_payload: Optional[Dict], primary_major: Optional[str]) -> Optional[Dict]:
    """{entry_path, entry_risk} for the best exact/strong-matching returned
    major, or None. The classifier itself stays KB-side (major_facts.py) —
    this only reads its labeled output; a fuzzy bind stamps nothing (a wrong
    door flag is worse than no flag)."""
    if not majors_payload or not isinstance(primary_major, str) or not primary_major.strip():
        return None
    rows = {}
    for c in (majors_payload.get('colleges') or []):
        for m in (c.get('majors') or []):
            if isinstance(m, dict) and m.get('name'):
                rows[m['name']] = m
    if not rows:
        return None
    res = match_major(primary_major, list(rows))
    if res['confidence'] not in ('exact', 'strong'):
        return None
    row = rows[res['kb_major_name']]
    ep = row.get('entry_path')
    entry_path = ep.get('value') if isinstance(ep, dict) else ep
    return {'entry_path': entry_path, 'entry_risk': row.get('entry_risk')}


def stamp_door_flags(user_email: str, university_id: str, choice: Dict) -> Optional[Dict]:
    """Best-effort door_flags enrichment for a just-saved major_choice: one
    extra KB call (action=majors&q=<primary>, single attempt), stamped onto
    the stored choice. Any failure → no flags; NEVER blocks the save."""
    try:
        primary = (choice or {}).get('primary')
        payload = fetch_university_majors(university_id, query=primary)
        flags = derive_door_flags(payload, primary)
        if not flags:
            return None
        updated_choice = {**choice, 'door_flags': flags}
        if get_db().update_college_list_item(user_email, university_id,
                                             {'major_choice': updated_choice}):
            return flags
        return None
    except Exception as e:
        logger.warning(f"[MAJOR_LLM] door_flags stamping failed for {university_id}: {e}")
        return None
