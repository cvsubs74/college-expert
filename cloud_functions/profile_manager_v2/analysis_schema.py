"""Shared analysis-doc schemas (#310).

The SINGLE source of truth for BOTH:
  - the agent-facing describe surface (GET /get-analysis-schema, exposed only
    through the MCP tool get_analysis_schema — never wired into the app UI), and
  - agent-write validation (validate_against), used by /save-external-fit and
    /save-external-major-chances.

Keeping both off one definition guarantees an agent is never told a shape the
server won't accept (or vice versa). Each schema carries a human-readable
`trust_rules` note stating which fields the server RE-DERIVES server-side (and
therefore ignores from the agent) — the honest contract behind the free agentic
save route: the agent can save an analysis for free, but it cannot fabricate.

`validate_against(kind, payload) -> (ok, errors)` is SHAPE/type/enum/required
validation only. Trust re-application (selectivity flooring, KB re-derivation of
entry_path/entry_risk, numeric-claim stripping, catalog name-match) is enforced
on the save path itself, not here.
"""

from typing import Dict, List, Tuple

FIT_CATEGORIES = ('SAFETY', 'TARGET', 'REACH', 'SUPER_REACH')
CHANCES_TIERS = ('strong', 'possible', 'reach', 'long_shot')


FIT_SCHEMA = {
    'kind': 'fit',
    'description': (
        'A complete college-fit analysis, the same shape the in-app Stratia '
        'generator produces. Compute it yourself from the student profile '
        '(get_profile) and the school knowledge base (get_university), then save '
        'it with save_fit_analysis. Only fit_category, match_percentage and '
        'explanation are required; the richer advisory blocks (factors, '
        'gap_analysis, recommendations, test_strategy, essay_angles, '
        'application_timeline, scholarship_matches, major_strategy) render in the '
        'app when present.'
    ),
    'fields': {
        'fit_category': {
            'type': 'string', 'required': True, 'enum': list(FIT_CATEGORIES),
            'note': 'your read — the server FLOORS it by the school KB selectivity',
        },
        'match_percentage': {
            'type': 'integer', 'required': True, 'min': 0, 'max': 100,
            'note': "clamped into the final fit_category's band",
        },
        'explanation': {
            'type': 'string', 'required': True,
            'note': '5-6 sentence analysis in your own counselor voice',
        },
        'factors': {
            'type': 'array', 'required': False,
            'note': ('[{name, score, max, detail}] — Academic 0-40, Holistic 0-30, '
                     'Major Fit 0-15, Selectivity -15..5; scores are clamped to those bounds'),
        },
        'gap_analysis': {'type': 'object', 'required': False},
        'recommendations': {'type': 'array', 'required': False},
        'test_strategy': {
            'type': 'object', 'required': False,
            'note': 'recommendation is forced to "Don\'t Submit" when the student has no test scores',
        },
        'essay_angles': {'type': 'array', 'required': False},
        'application_timeline': {'type': 'object', 'required': False},
        'scholarship_matches': {'type': 'array', 'required': False},
        'major_strategy': {'type': 'object', 'required': False},
    },
    'trust_rules': (
        "fit_category is FLOORED by the school's KB acceptance rate (a <8% school "
        "can never be SAFETY/TARGET/REACH; an 8-15% school can never be "
        "SAFETY/TARGET) and CEILINGED for accessible schools, then "
        "match_percentage is clamped into that category's band — anything you "
        "send that violates the selectivity floor/ceiling is overridden. Factor "
        "scores are clamped to their documented ranges. test_strategy is forced "
        "to \"Don't Submit\" when the student has no test scores. acceptance_rate "
        "and KB provenance (kb_data_year) are taken from the knowledge base, not "
        "from you. Never fabricate a percentage, GPA, or admit rate."
    ),
}


MAJOR_CHANCES_SCHEMA = {
    'kind': 'major_chances',
    'description': (
        'A per-college major-chances ranking. Send {"majors": [{"name", "tier", '
        '"rationale"}]} — the SAME flat shape the ranking LLM produces. Scan the '
        "school's real offered catalog (get_university_majors), select the majors "
        'that fit the student, and rank each into a likelihood TIER with a '
        'one-to-three-sentence rationale. Save it with save_major_chances.'
    ),
    'fields': {
        'majors': {
            'type': 'array', 'required': True,
            'item_fields': {
                'name': {
                    'type': 'string', 'required': True,
                    'note': ('must match a major the school actually offers — the '
                             "server catalog-matches names and DROPS any the school doesn't offer"),
                },
                'tier': {
                    'type': 'string', 'required': True, 'enum': list(CHANCES_TIERS),
                    'note': 'admission-chance tier; unknown values are coerced (conservatively) to reach',
                },
                'rationale': {
                    'type': 'string', 'required': False,
                    'note': 'counselor judgment; any %/GPA not present in the KB is stripped',
                },
                'college': {'type': 'string', 'required': False},
            },
        },
    },
    'trust_rules': (
        'entry_path and entry_risk are RE-DERIVED from the knowledge base for '
        'each major — anything you send for them is ignored. Major names are '
        "matched to the school's real offered catalog; a name the school doesn't "
        'offer is DROPPED (chances only ever show real majors). tiers are coerced '
        'to strong/possible/reach/long_shot. Any percentage or GPA in a rationale '
        "that the KB doesn't contain is stripped into data_notes. capped_door "
        'majors always get the door-lock caveat regardless of tier. Never '
        'fabricate a percentage, GPA, or admit rate.'
    ),
}


_SCHEMAS = {'fit': FIT_SCHEMA, 'major_chances': MAJOR_CHANCES_SCHEMA}


def get_schema(kind: str) -> Dict:
    """The schema dict for `kind` ('fit' | 'major_chances'), or None."""
    return _SCHEMAS.get(kind)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _validate_fit(payload: Dict, errors: List[str]) -> None:
    cat = payload.get('fit_category')
    if cat is None:
        errors.append('fit_category is required')
    elif cat not in FIT_CATEGORIES:
        errors.append(f'fit_category must be one of {list(FIT_CATEGORIES)} (got {cat!r})')

    mp = payload.get('match_percentage')
    if mp is None:
        errors.append('match_percentage is required')
    elif not _is_number(mp):
        errors.append('match_percentage must be a number 0-100')
    elif not (0 <= mp <= 100):
        errors.append('match_percentage must be between 0 and 100')

    exp = payload.get('explanation')
    if not isinstance(exp, str) or not exp.strip():
        errors.append('explanation is required (a non-empty string)')

    factors = payload.get('factors')
    if factors is not None and not isinstance(factors, list):
        errors.append('factors, when present, must be a list')


def _validate_major_chances(payload: Dict, errors: List[str]) -> None:
    majors = payload.get('majors')
    if not isinstance(majors, list) or not majors:
        errors.append('majors is required (a non-empty list of {name, tier, rationale})')
        return
    for i, m in enumerate(majors):
        if not isinstance(m, dict):
            errors.append(f'majors[{i}] must be an object')
            continue
        name = m.get('name')
        if not isinstance(name, str) or not name.strip():
            errors.append(f'majors[{i}].name is required (a non-empty string)')
        tier = m.get('tier')
        if tier is None:
            errors.append(f'majors[{i}].tier is required')
        elif not isinstance(tier, str) or tier.strip().lower() not in CHANCES_TIERS:
            errors.append(
                f'majors[{i}].tier must be one of {list(CHANCES_TIERS)} (got {tier!r})')
        rationale = m.get('rationale')
        if rationale is not None and not isinstance(rationale, str):
            errors.append(f'majors[{i}].rationale, when present, must be a string')


def validate_against(kind: str, payload: Dict) -> Tuple[bool, List[str]]:
    """(ok, errors) shape/type/enum/required validation for an agent-supplied
    payload of `kind`. Trust re-application happens separately on the save path."""
    schema = _SCHEMAS.get(kind)
    if schema is None:
        return False, [f'unknown kind: {kind!r} (expected fit | major_chances)']
    if not isinstance(payload, dict):
        return False, ['payload must be an object']
    errors: List[str] = []
    if kind == 'fit':
        _validate_fit(payload, errors)
    elif kind == 'major_chances':
        _validate_major_chances(payload, errors)
    return (not errors), errors
