"""Agent-only, FREE, trust-enforced analysis writes (#310).

The agentic credit-saving route: ChatGPT/Claude compute the fit and/or the
per-college major-chances themselves (their subscription bears the LLM cost) and
save them into the SAME Firestore structure via MCP — 0 Stratia credits. The
in-app Generate is 1 credit; a saved agent analysis is free.

THE CRITICAL CORRECTNESS SURFACE: an agent must NOT be able to write fabricated
or malformed data. Every agent write is re-validated and trust-enforced
server-side by reusing the EXACT in-app normalizers/post-processors, so an
agent-saved artifact and a Stratia-generated one are indistinguishable in trust:

  - save-external-fit re-applies fit_computation.post_process_fit (the same
    selectivity floor/ceiling, match% band clamp, factor bounds, and
    don't-submit-when-no-scores the in-app LLM path runs) and sources
    acceptance_rate + KB provenance from the KNOWLEDGE BASE, never from the
    agent — so an inflated category for a hyper-selective school is floored.
  - save-external-major-chances runs the agent's ranking through
    major_llm.assemble_and_save_ranking → normalize_college_major_ranking, which
    re-derives entry_path/entry_risk from the KB, strips fabricated %/GPA from
    rationales, applies the capped_door door-lock, catalog-matches names
    (dropping off-catalog ones), and coerces tiers.

Provenance (`source`: claude/chatgpt) makes the origin honest without weakening
trust; `basis: inference` marks it as counselor judgment like every generated
artifact.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from analysis_schema import validate_against
from essay_copilot import fetch_university_profile
from firestore_db import get_db
from fit_analysis import save_fit_analysis
from fit_computation import post_process_fit
from fit_staleness import _acceptance_rate, build_kb_provenance
from major_llm import (
    assemble_and_save_ranking,
    build_full_catalog_rows,
    fetch_university_majors,
)

logger = logging.getLogger(__name__)


# The ONLY fit keys taken from the agent — the counselor-judgment content the
# post-processor then trust-clamps. Everything else (identity, logo, selectivity
# tier, acceptance_rate, KB provenance, match_score, timestamps) is server-owned
# and rebuilt below, so an agent can't inject extra keys (e.g. a tracking
# logo_url render sink, or a fake `verified`/`kb_data_year`) into the saved doc
# (#314 review F: no extra-field passthrough).
_ALLOWED_FIT_CONTENT_FIELDS = frozenset({
    'fit_category', 'match_percentage', 'explanation', 'factors', 'gap_analysis',
    'recommendations', 'test_strategy', 'essay_angles', 'application_timeline',
    'scholarship_matches', 'major_strategy', 'demonstrated_interest_tips',
    'red_flags_to_avoid',
})


def _normalize_source(source: Optional[str]) -> str:
    """Honest, bounded provenance label. The connector passes claude/chatgpt/etc.
    from the authenticated client's OAuth registration; a missing/odd value falls
    back to a neutral 'agent' — never fabricated as Claude."""
    s = (source or '').strip().lower()
    return s[:32] if s else 'agent'


def run_save_external_fit(user_email: str, university_id: str,
                          fit_analysis: Dict, source: Optional[str]) -> Tuple[Dict, int]:
    """POST /save-external-fit — validate shape, RE-APPLY the deterministic fit
    post-processing (selectivity floor/ceiling, match% band, factor bounds,
    don't-submit-when-no-scores), stamp source/basis/identity/KB provenance from
    the KB (never the agent), archive the prior fit, and save. FREE (0 credits)."""
    ok, errors = validate_against('fit', fit_analysis)
    if not ok:
        return {'success': False, 'error': 'invalid fit_analysis', 'field_errors': errors}, 400

    db = get_db()
    profile = db.get_profile(user_email) or {}
    university_data = fetch_university_profile(university_id)
    # Require the KB doc: the selectivity floor is enforced against the KB
    # acceptance rate, so a school missing from the KB is a floor-dodge window
    # (#314 review F). Symmetric with the in-app compute-single-fit (404s on a
    # missing university) and with the chances save path.
    if not university_data:
        return {'success': False,
                'error': f'{university_id} is not in the knowledge base — a fit '
                         'cannot be trust-validated for a school we do not have'}, 400

    # Rebuild from the content allow-list ONLY — agent junk keys are dropped.
    fit = {k: fit_analysis[k] for k in _ALLOWED_FIT_CONTENT_FIELDS if k in fit_analysis}
    # Trust re-application: the same deterministic post-processor the in-app LLM
    # path runs — an inflated fit_category for a <8% school is floored here.
    # acceptance_rate comes ONLY from the KB (never the agent), so the floor
    # cannot be dodged with a fake rate.
    acceptance_rate = _acceptance_rate(university_data)
    post_process_fit(fit, acceptance_rate, profile)

    # Server-owned stamps (the agent cannot forge these):
    fit['source'] = _normalize_source(source)
    fit['basis'] = 'inference'
    fit['university_id'] = university_id
    if acceptance_rate is not None:
        fit['acceptance_rate'] = acceptance_rate
    # Identity + logo from the KB, never the agent (logo_url is a live
    # background-image render sink — #314 review F).
    if university_data.get('official_name'):
        fit['university_name'] = university_data['official_name']
    if university_data.get('location') is not None:
        fit['location'] = university_data['location']
    logo = (university_data.get('logo_url')
            or (university_data.get('profile') or {}).get('logo_url'))
    if logo:
        fit['logo_url'] = logo
    fit.update(build_kb_provenance(university_data))  # kb_data_year etc. from the KB
    fit['calculated_at'] = datetime.utcnow().isoformat()

    result = save_fit_analysis(user_email, university_id, fit)  # archives prior
    if not result.get('success'):
        return {'success': False,
                'error': 'fit validated but could not be saved — try again'}, 500
    return {'success': True, 'fit_analysis': fit}, 200


def run_save_external_major_chances(user_email: str, university_id: str,
                                    ranking: Dict, source: Optional[str]) -> Tuple[Dict, int]:
    """POST /save-external-major-chances — validate shape, then run the agent's
    ranking through the SAME trust machinery as the in-app ranker
    (normalize_college_major_ranking, via assemble_and_save_ranking):
    entry_path/entry_risk re-derived from the KB, fabricated %/GPA stripped,
    capped_door door-lock applied, names catalog-matched (off-catalog dropped),
    tiers coerced. Stamp source/basis, archive the prior, save. FREE (0 credits).
    A school with no KB majors → 400 (chances can't be validated)."""
    ok, errors = validate_against('major_chances', ranking)
    if not ok:
        return {'success': False, 'error': 'invalid ranking', 'field_errors': errors}, 400

    db = get_db()
    profile = db.get_profile(user_email) or {}

    facts = fetch_university_majors(university_id)
    if facts is None:
        return {'success': False,
                'error': f'knowledge base unavailable for {university_id} — try again'}, 502
    if not facts.get('success'):
        return {'success': False,
                'error': f'no knowledge-base major data for {university_id} — '
                         'chances cannot be validated for a school with no KB majors'}, 400

    catalog_rows = build_full_catalog_rows(facts)
    if not catalog_rows:
        return {'success': False,
                'error': 'this school has no knowledge-base majors — chances '
                         'cannot be validated for a school with no KB majors'}, 400

    ranking_doc = assemble_and_save_ranking(
        user_email, university_id, db, profile, facts, catalog_rows, ranking,
        source=_normalize_source(source))
    if ranking_doc is None:
        return {'success': False,
                'error': 'ranking validated but could not be saved — try again'}, 500
    return {'success': True, 'ranking': ranking_doc}, 200
