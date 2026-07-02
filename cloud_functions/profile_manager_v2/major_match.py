"""Major-name matching against a school's KB major list.

Majors are free-text strings with no cross-university taxonomy (no CIP codes
yet — #287 collector ask), so matching is a normalize + abbreviation +
overlap ladder. Binding rule (#280 design): only 'exact'/'strong' matches
auto-canonicalize a student's choice to the KB spelling; 'fuzzy' is stored
as-given with matched=False so downstream advice warns instead of guessing —
a wrong-door binding is the exact failure this feature exists to prevent.
"""
import re
from typing import Dict, List, Optional, Tuple

# Common shorthand → canonical phrase. Applied whole-string and per-token.
_ABBREVIATIONS = {
    'cs': 'computer science',
    'compsci': 'computer science',
    'comp sci': 'computer science',
    'ee': 'electrical engineering',
    'ece': 'electrical and computer engineering',
    'meche': 'mechanical engineering',
    'mech e': 'mechanical engineering',
    'mecheng': 'mechanical engineering',
    'cheme': 'chemical engineering',
    'civ e': 'civil engineering',
    'econ': 'economics',
    'bio': 'biology',
    'biochem': 'biochemistry',
    'bme': 'biomedical engineering',
    'poli sci': 'political science',
    'polisci': 'political science',
    'psych': 'psychology',
    'cogsci': 'cognitive science',
    'cog sci': 'cognitive science',
    'stats': 'statistics',
    'math': 'mathematics',
    'ir': 'international relations',
    'ib': 'international business',
    'premed': 'pre medicine',
    'pre med': 'pre medicine',
    'prelaw': 'pre law',
    'pre law': 'pre law',
    'ds': 'data science',
    'ai': 'artificial intelligence',
    'me': 'mechanical engineering',
}

# Degree suffixes/noise stripped before comparison. Kept in parity with the
# KB's major_catalog.normalize_major (#306) — including program/track/
# concentration — so a catalog key and a match result line up.
_SUFFIX_RE = re.compile(
    r'[,\s]*(\(|\b)(b\.?s\.?e?\.?|b\.?a\.?|a\.?b\.?|bachelor(s)?( of (science|arts))?|'
    r'major|degree|program|track|concentration)(\))?\s*$', re.IGNORECASE)
_PUNCT_RE = re.compile(r'[^a-z0-9+& ]+')


def normalize_major(name: str) -> str:
    """Lowercase, strip degree suffixes and punctuation, expand shorthand."""
    if not isinstance(name, str):
        return ''
    s = name.strip().lower()
    prev = None
    while prev != s:
        prev = s
        s = _SUFFIX_RE.sub('', s).strip()
    s = _PUNCT_RE.sub(' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if s in _ABBREVIATIONS:
        return _ABBREVIATIONS[s]
    tokens = [_ABBREVIATIONS.get(t, t) for t in s.split(' ')]
    return ' '.join(tokens)


def _token_overlap(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def match_major(query: str, candidates: List[str]) -> Dict:
    """Match a free-text major name against a school's KB major names.

    Returns {found, kb_major_name, confidence: 'exact'|'strong'|'fuzzy'|'none',
    near_misses: [up to 5 names by overlap]}. Only exact/strong should be
    auto-bound; see module docstring.
    """
    q_raw = (query or '').strip()
    q = normalize_major(q_raw)
    scored: List[Tuple[float, str]] = []
    best: Optional[Dict] = None

    for cand in candidates or []:
        if not isinstance(cand, str) or not cand.strip():
            continue
        if cand.strip().lower() == q_raw.lower():
            return {'found': True, 'kb_major_name': cand, 'confidence': 'exact',
                    'near_misses': []}
        c = normalize_major(cand)
        if c and c == q:
            best = {'found': True, 'kb_major_name': cand, 'confidence': 'strong'}
        overlap = _token_overlap(q, c) if q and c else 0.0
        scored.append((overlap, cand))

    scored.sort(key=lambda x: x[0], reverse=True)
    near = [name for score, name in scored[:5] if score > 0]

    if best:
        best['near_misses'] = [n for n in near if n != best['kb_major_name']][:5]
        return best
    if scored and scored[0][0] >= 0.6:
        return {'found': True, 'kb_major_name': scored[0][1], 'confidence': 'fuzzy',
                'near_misses': near}
    return {'found': False, 'kb_major_name': None, 'confidence': 'none',
            'near_misses': near}


def kb_major_names(university_profile: dict) -> List[str]:
    """All major names in a KB profile's academic_structure."""
    names = []
    structure = (university_profile or {}).get('academic_structure') or {}
    for college in (structure.get('colleges') or []):
        if not isinstance(college, dict):
            continue
        for major in (college.get('majors') or []):
            if isinstance(major, dict) and major.get('name'):
                names.append(major['name'])
    return names
