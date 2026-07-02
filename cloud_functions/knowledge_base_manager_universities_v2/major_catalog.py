"""Global major catalog — the union of every major offered across all
university profiles (#303).

The school-agnostic Major Map used to suggest free-form LLM major names with
no guarantee any college offers them. This catalog is the reusable source of
truth for "majors that actually exist somewhere": a single Firestore doc
`major_catalog/current` aggregating `academic_structure.colleges[].majors[]`
across the whole KB, keyed by a normalized name so trivial spelling variants
collapse.

Design:
- Storage: ONE doc (point-read cheap; ~1.4k majors well under Firestore's
  1 MiB at current KB scale). If it ever approaches the limit, shard by first
  letter or move to per-major docs — noted, not needed now.
- `university_ids` per entry is a SET (stored as a sorted list) so re-ingest
  is idempotent: dropping then re-adding a school never double-counts, and
  offered_count = len(university_ids).
- `scripts/build_major_catalog.py` rebuilds the whole doc from a full KB scan
  (the reliable source of truth); `ingest_university` upserts one school
  incrementally (best-effort — a catalog failure must never fail an ingest).

Everything here is pure (dict in / dict out); the Firestore read/write lives
in firestore_db.py so this module unit-tests without a fake.
"""
import re
from typing import Dict, Iterable, List, Optional

# Shorthand → canonical, applied whole-string then per-token. Mirrors
# profile_manager_v2/major_match.py (kept in sync by hand — different service,
# no shared package).
_ABBREVIATIONS = {
    'cs': 'computer science', 'compsci': 'computer science', 'comp sci': 'computer science',
    'ee': 'electrical engineering', 'ece': 'electrical and computer engineering',
    'meche': 'mechanical engineering', 'mech e': 'mechanical engineering',
    'mecheng': 'mechanical engineering', 'cheme': 'chemical engineering',
    'civ e': 'civil engineering', 'econ': 'economics', 'bio': 'biology',
    'biochem': 'biochemistry', 'bme': 'biomedical engineering',
    'poli sci': 'political science', 'polisci': 'political science',
    'psych': 'psychology', 'cogsci': 'cognitive science', 'cog sci': 'cognitive science',
    'stats': 'statistics', 'math': 'mathematics', 'ir': 'international relations',
    'ib': 'international business', 'ds': 'data science',
    'ai': 'artificial intelligence',
}
_SUFFIX_RE = re.compile(
    r'[,\s]*(\(|\b)(b\.?s\.?e?\.?|b\.?a\.?|a\.?b\.?|bachelor(s)?( of (science|arts))?|'
    r'major|degree|program|track|concentration)(\))?\s*$', re.IGNORECASE)
_PUNCT_RE = re.compile(r'[^a-z0-9+& ]+')


def normalize_major(name: str) -> str:
    """Lowercase, strip degree/program suffixes and punctuation, expand
    shorthand. '' for unusable input (dropped from the catalog)."""
    if not isinstance(name, str):
        return ''
    s = name.strip().lower()
    prev = None
    while prev != s:
        prev = s
        s = _SUFFIX_RE.sub('', s).strip()
    s = _PUNCT_RE.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if not s:
        return ''
    if s in _ABBREVIATIONS:
        return _ABBREVIATIONS[s]
    return ' '.join(_ABBREVIATIONS.get(t, t) for t in s.split(' '))


def major_names(profile: Optional[Dict]) -> List[str]:
    """Every major name in one profile's academic_structure (raw display names)."""
    names = []
    structure = (profile or {}).get('academic_structure') or {}
    for college in (structure.get('colleges') or []):
        if not isinstance(college, dict):
            continue
        for major in (college.get('majors') or []):
            if isinstance(major, dict) and isinstance(major.get('name'), str) and major['name'].strip():
                names.append(major['name'].strip())
    return names


def _blank_catalog() -> Dict:
    return {'majors': {}, 'university_ids': [], 'university_count': 0}


def add_school(catalog: Optional[Dict], university_id: str, profile: Dict) -> Dict:
    """Return a NEW catalog with `university_id`'s current majors merged in,
    idempotently: the school is first removed from every entry (so a re-ingest
    with a changed major list can't leave stale contributions), then re-added.

    Entry shape: majors[normalized] = {'display': str, 'university_ids': [sorted]}.
    `display` is the shortest observed raw name for that normalized key (a
    stable, readable representative).
    """
    cat = _drop_school(catalog, university_id)
    majors = cat['majors']
    for raw in major_names(profile):
        key = normalize_major(raw)
        if not key:
            continue
        entry = majors.get(key)
        if entry is None:
            entry = {'display': raw, 'university_ids': []}
            majors[key] = entry
        # Prefer the shortest raw name as the display representative.
        if len(raw) < len(entry['display']):
            entry['display'] = raw
        if university_id not in entry['university_ids']:
            entry['university_ids'] = sorted(set(entry['university_ids']) | {university_id})
    uids = set(cat['university_ids']) | {university_id}
    cat['university_ids'] = sorted(uids)
    cat['university_count'] = len(uids)
    return cat


def _drop_school(catalog: Optional[Dict], university_id: str) -> Dict:
    """A copy of the catalog with `university_id` removed from every entry;
    entries left with no schools are dropped."""
    import copy
    cat = copy.deepcopy(catalog) if catalog else _blank_catalog()
    cat.setdefault('majors', {})
    cat.setdefault('university_ids', [])
    kept = {}
    for key, entry in cat['majors'].items():
        ids = [u for u in (entry.get('university_ids') or []) if u != university_id]
        if ids:
            kept[key] = {'display': entry.get('display') or key, 'university_ids': ids}
    cat['majors'] = kept
    uids = [u for u in cat['university_ids'] if u != university_id]
    cat['university_ids'] = uids
    cat['university_count'] = len(uids)
    return cat


def build_catalog(profiles_by_id: Iterable) -> Dict:
    """Full rebuild from (university_id, profile) pairs — the source of truth
    the backfill script writes."""
    cat = _blank_catalog()
    for university_id, profile in profiles_by_id:
        if university_id and isinstance(profile, dict):
            cat = add_school(cat, university_id, profile)
    return cat


def catalog_view(catalog: Optional[Dict], limit: Optional[int] = None,
                 min_schools: int = 1, query: Optional[str] = None) -> Dict:
    """Lean, sorted projection for the read endpoint — names + offered_count,
    never the raw id lists. Sorted by offered_count desc, then name."""
    catalog = catalog or _blank_catalog()
    q = (query or '').strip().lower()
    rows = []
    for key, entry in (catalog.get('majors') or {}).items():
        count = len(entry.get('university_ids') or [])
        if count < min_schools:
            continue
        display = entry.get('display') or key
        if q and q not in display.lower() and q not in key:
            continue
        rows.append({'name': display, 'normalized': key, 'offered_count': count})
    rows.sort(key=lambda r: (-r['offered_count'], r['name'].lower()))
    total = len(rows)
    if limit is not None:
        rows = rows[:limit]
    return {
        'majors': rows,
        'total': total,
        'university_count': catalog.get('university_count', 0),
        'updated_at': catalog.get('updated_at'),
    }
