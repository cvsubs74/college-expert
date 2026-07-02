"""Deterministic, trust-labeled majors extract (`?action=majors`).

The single implementation of "what does the KB actually know about entering
each major at this school" — consumed by the MCP connector, the app, and any
future counselor surface, so the trust rules live in exactly one place.

Trust doctrine (epic #280 / REDESIGN.md null-over-guess):
- basis 'kb_verified' only when the profile was produced by the verified
  collector (metadata.verification_status == 'verified'); everything else is
  'kb_reported' — present but unprovenanced. Legacy-only numeric fields
  (per-major acceptance_rate, average_gpa_admitted, ...) are ALWAYS
  'kb_reported': the verified collector never emits them, so presence proves
  legacy origin.
- `is_impacted: false` must NEVER be read as "not competitive": verified
  UIUC CS is is_impacted=false (no official designation) at a ~7% admit.
  The honest competitiveness signal is structural — `entry_risk` says
  whether the door locks behind you.
- The entry-path classifier keeps an explicit 'unclear' bucket carrying the
  school's verbatim wording; a guessed door policy is the worst trust
  failure this feature can commit.
"""
import re
from typing import Dict, List, Optional

ENTRY_PATHS = ('direct_admit', 'pre_major', 'secondary_application',
               'open_declaration', 'unclear')

# Keyword lexicon over admissions_pathway / admissions_model free text.
# Order matters: more specific negative/secondary phrasings are checked
# before generic 'direct admit' phrasing.
_SECONDARY_PATTERNS = (
    'apply as sophomore', 'apply in sophomore', 'secondary application',
    'secondary admission', 'internal application', 'competitive application',
    'apply to the major after', 'apply after enrolling',
    'separate application', 'application after enrollment',
    'internal transfer application',
)
_PRE_MAJOR_PATTERNS = (
    'pre-major', 'pre major', 'premajor', 'pre-business', 'pre-nursing',
    'pre-engineering', 'admitted as pre-', 'pre-professional program',
)
# Negated phrasings that must be neutralized BEFORE pattern matching —
# 'no secondary application' must not fire the secondary bucket (real case:
# Michigan Applied Exercise Science).
_NEGATED_PHRASES = (
    'no secondary application', 'no separate application',
    'no internal application', 'without a secondary application',
    'no additional application', 'no competitive application',
)
_OPEN_PATTERNS = (
    'chosen after enrolling', 'declared in', 'declared after',
    'declare their major', 'declare a major', 'freely declare',
    'no separate admission', 'open enrollment', 'open to all',
    'not admitted by major', 'apply to the university, not',
    'concentration declared', 'selected after enrollment', 'undeclared',
)
_DIRECT_PATTERNS = (
    'direct admit', 'direct-admit', 'directly admit', 'admitted directly',
    'direct entry', 'direct freshman', 'admission to the major',
    'admitted to the major', 'admit by major', 'admits by major',
    'apply directly',
)


def classify_entry_path(pathway_text: Optional[str],
                        direct_admit_only: Optional[bool] = None) -> str:
    """Classify free-text admissions_pathway into an entry-path enum.

    Deliberately conservative: conflicting or unmatched text → 'unclear'
    (the consumer renders the school's verbatim wording instead of a badge).
    """
    if direct_admit_only is True:
        return 'direct_admit'
    if not isinstance(pathway_text, str):
        return 'unclear'
    text = pathway_text.strip().lower()
    if not text:
        return 'unclear'
    # Neutralize explicit negations so 'no secondary application' can't
    # assert the very thing it denies.
    for neg in _NEGATED_PHRASES:
        text = text.replace(neg, ' ')

    hits = set()
    if any(p in text for p in _SECONDARY_PATTERNS):
        hits.add('secondary_application')
    if any(p in text for p in _PRE_MAJOR_PATTERNS):
        hits.add('pre_major')
    if any(p in text for p in _DIRECT_PATTERNS):
        hits.add('direct_admit')
    if any(p in text for p in _OPEN_PATTERNS):
        hits.add('open_declaration')

    # Composite realities resolve to the gate the APPLICANT faces first:
    # pre-major + secondary application is the classic pre-major system.
    if hits == {'pre_major', 'secondary_application'}:
        return 'pre_major'
    if len(hits) == 1:
        return hits.pop()
    return 'unclear'


def _num(value):
    """Best-effort float for Union[float, str] KB fields; None when unparseable."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r'\d+(\.\d+)?', value)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return None
    return None


def derive_entry_risk(major: Dict, college: Dict, entry_path: str) -> str:
    """Structural competitiveness signal: does the door lock behind you?

    capped_door — if not admitted directly you can't switch in later.
    elevated — officially capped/impacted, high transfer GPA bar, or a
               competitive secondary gate.
    standard — a known path with no risk flags.
    unknown — not enough structure to say (never guessed).
    """
    transfer_allowed = major.get('internal_transfer_allowed')
    raw_gpa = _num(major.get('internal_transfer_gpa'))
    # GPA plausibility guard: free-text fields yield course numbers ('MOL 214')
    # or unit counts — only 0 < x <= 5 is a GPA.
    gpa_bar = raw_gpa if raw_gpa is not None and 0 < raw_gpa <= 5 else None
    if transfer_allowed is False:
        return 'capped_door'
    if major.get('direct_admit_only') is True:
        # Self-contradictory legacy rows exist (UF CS: direct_admit_only true
        # AND internal_transfer_allowed true with a 2.5 GPA path). A stated
        # transfer path means the door is NOT locked — a false 'capped_door'
        # is this feature's worst trust failure. Restricted-but-open lands on
        # 'elevated'.
        if transfer_allowed is True or gpa_bar is not None:
            return 'elevated'
        return 'capped_door'
    if (major.get('is_impacted') is True
            or (college or {}).get('is_restricted_or_capped') is True
            or (gpa_bar is not None and gpa_bar >= 3.5)
            or entry_path == 'secondary_application'):
        return 'elevated'
    if entry_path != 'unclear':
        return 'standard'
    known_structure = any(
        major.get(k) is not None
        for k in ('is_impacted', 'internal_transfer_allowed', 'direct_admit_only'))
    return 'standard' if known_structure else 'unknown'


# Fields only the legacy collector produced — presence proves legacy origin,
# so their basis is ALWAYS kb_reported regardless of verification status.
_LEGACY_ONLY_STATS = ('acceptance_rate', 'average_gpa_admitted',
                      'minimum_gpa_to_declare', 'weeder_courses')


def _major_row(major: Dict, college: Dict, basis: str) -> Dict:
    pathway_raw = major.get('admissions_pathway')
    entry_path = classify_entry_path(pathway_raw, major.get('direct_admit_only'))
    reported = {}
    for k in _LEGACY_ONLY_STATS:
        if major.get(k) not in (None, '', []):
            reported[k] = major[k]
    row = {
        'name': major.get('name'),
        'degree_type': major.get('degree_type'),
        'entry_path': {
            'value': entry_path,
            'raw': pathway_raw or None,
            'basis': basis if pathway_raw else None,
        },
        'entry_risk': derive_entry_risk(major, college, entry_path),
        'is_impacted': {
            'value': major.get('is_impacted'),
            'basis': basis if major.get('is_impacted') is not None else None,
            'note': ('official designation only — false does NOT mean '
                     'the major is easy to enter; check entry_risk'
                     if major.get('is_impacted') is False and basis == 'kb_verified'
                     else None),
        },
        'door_policy': {
            'direct_admit_only': major.get('direct_admit_only'),
            'internal_transfer_allowed': major.get('internal_transfer_allowed'),
            'internal_transfer_gpa': major.get('internal_transfer_gpa'),
            'basis': basis,
        },
        'prerequisite_courses': major.get('prerequisite_courses') or [],
        'special_requirements': major.get('special_requirements'),
        'reported_stats': ({**reported, 'basis': 'kb_reported'} if reported else None),
    }
    return row


def _tier(verified: bool, colleges: List[Dict]) -> int:
    """richness_tier: 1 verified · 2 legacy-rich · 3 legacy-thin · 4 no majors."""
    majors = [m for c in colleges for m in (c.get('majors') or []) if isinstance(m, dict)]
    if not majors:
        return 4
    if verified:
        return 1
    with_pathway = sum(1 for m in majors if m.get('admissions_pathway'))
    has_depth = any(
        m.get(k) not in (None, '', [])
        for m in majors
        for k in ('internal_transfer_gpa', 'minimum_gpa_to_declare',
                  'prerequisite_courses', 'internal_transfer_allowed',
                  'direct_admit_only'))
    if with_pathway >= 0.6 * len(majors) and has_depth:
        return 2
    return 3


def extract_major_facts(profile: Dict, college: Optional[str] = None,
                        query: Optional[str] = None) -> Dict:
    """Trust-labeled per-major facts for one university profile."""
    profile = profile or {}
    metadata = profile.get('metadata') or {}
    verified = (metadata.get('verification_status') == 'verified')
    basis = 'kb_verified' if verified else 'kb_reported'
    structure = profile.get('academic_structure') or {}
    strategy = profile.get('application_strategy') or {}
    colleges_raw = [c for c in (structure.get('colleges') or []) if isinstance(c, dict)]

    college_filter = (college or '').strip().lower()
    query_filter = (query or '').strip().lower()

    colleges = []
    for c in colleges_raw:
        if college_filter and college_filter not in (c.get('name') or '').lower():
            continue
        majors = []
        for m in (c.get('majors') or []):
            if not isinstance(m, dict):
                continue
            if query_filter and query_filter not in (m.get('name') or '').lower():
                continue
            majors.append(_major_row(m, c, basis))
        if query_filter and not majors:
            continue
        colleges.append({
            'name': c.get('name'),
            'admissions_model': c.get('admissions_model'),
            'is_restricted_or_capped': c.get('is_restricted_or_capped'),
            'acceptance_rate_estimate': (
                {'value': c.get('acceptance_rate_estimate'), 'basis': 'kb_reported'}
                if c.get('acceptance_rate_estimate') not in (None, '') else None),
            'strategic_fit_advice': (
                {'text': c.get('strategic_fit_advice'), 'basis': 'opinion'}
                if c.get('strategic_fit_advice') else None),
            'majors': majors,
        })

    tier = _tier(verified, colleges_raw)

    data_notes = []
    if not verified:
        data_notes.append(
            'Major-level facts for this school are reported but not yet '
            're-verified against official publications — treat as directional.')
    if tier == 3:
        data_notes.append(
            'Entry-path detail is thin for this school — verify door policies '
            'on its official admissions pages before strategizing.')
    if tier == 4:
        data_notes.append('No majors are stored for this school yet.')
    all_rows = [m for c in colleges for m in c['majors']]
    if any(m['entry_path']['value'] == 'unclear' for m in all_rows):
        data_notes.append(
            "Majors with entry_path 'unclear' carry the school's verbatim "
            'wording in entry_path.raw — never assume a door policy from them.')
    if not any(m.get('reported_stats') for m in all_rows) and all_rows:
        data_notes.append(
            'This school does not publish per-major admit rates in our data — '
            'competitiveness must come from the structural entry_risk signal.')

    return {
        'structure_type': structure.get('structure_type'),
        'verification_status': 'verified' if verified else 'legacy',
        'richness_tier': tier,
        'colleges': colleges,
        'strategy_notes': {
            'major_selection_tactics': {
                'items': strategy.get('major_selection_tactics') or [],
                'basis': 'opinion',
            },
            'alternate_major_strategy': {
                'text': strategy.get('alternate_major_strategy') or None,
                'basis': 'opinion',
            },
        },
        'data_notes': data_notes,
    }
