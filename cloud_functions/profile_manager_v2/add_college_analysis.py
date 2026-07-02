"""Bundled add-college analysis (#310): ONE credit → BOTH the fit analysis AND
the per-college major-chances ranking.

Owner decision (2026-07-02): adding a college to the Launchpad ALWAYS consumes
1 credit and produces BOTH artifacts as a single billed unit (1 credit for the
bundle, never 2). The agent route saves credits on regeneration only; the in-app
add is always the paid Stratia generation.

Billing mirrors fit_billing.run_compute_single_fit's tested invariants — check →
402 insufficient_credits / 503 on the #298 credits_read_failed marker → generate
→ deduct exactly ONCE after success, never on failure, never on a fallback fit
(#296 review F2) — but the billed unit produces two artifacts for the one charge:

  (a) the fit via calculate_fit_for_college (resolution-order major) + save
      (archives the prior fit to history, as compute-single-fit does today);
  (b) the KB majors (fetch_university_majors); if present, the major-chances
      ranking via run_ranking_generation (the UNBILLED core of
      run_rank_college_majors) + save (archives the prior ranking).

The FIT is the primary artifact: if it fails or its save fails the whole add is
a 500 and NOTHING is billed. A KB-majors miss (or a chances hiccup) degrades
major_chances to null with a note — never a second charge, never a failure, and
the fit is still saved. A fallback fit (is_fallback) is not billed.

The granular per-artifact endpoints (compute-single-fit, rank-college-majors)
stay for in-app regeneration of a single artifact.
"""

import logging
from typing import Dict, Optional, Tuple

from credits import check_credits_available, deduct_credit
from essay_copilot import fetch_university_profile
from firestore_db import get_db
from fit_analysis import save_fit_analysis
from fit_computation import calculate_fit_for_college
from majors import resolve_intended_major
from major_llm import (
    _intended_majors,
    build_full_catalog_rows,
    fetch_university_majors,
    run_ranking_generation,
)

logger = logging.getLogger(__name__)

ADD_ANALYSIS_CREDIT_COST = 1
ADD_ANALYSIS_REASON = 'add_college_analysis'


def _compute_and_save_fit(user_email: str, university_id: str, db, profile: Dict,
                          explicit_major: Optional[str]) -> Tuple[Optional[Dict], Optional[Tuple[Dict, int]]]:
    """Compute + save the fit (archives prior). Returns (fit_analysis, error).
    On success `error` is None; on failure `fit_analysis` is None and `error` is
    the (payload, status) to return unbilled. Mirrors main.py's compute-single-fit
    closure so the bundled fit is identical to the granular one."""
    university_profile = fetch_university_profile(university_id)
    if not university_profile:
        return None, ({'success': False, 'error': 'University profile not found'}, 404)

    # Resolution-order major (#281): explicit → saved major_choice → intended.
    list_item = db.get_college_list_item(user_email, university_id)
    resolution = resolve_intended_major(profile, list_item, explicit=explicit_major)

    fit_analysis = calculate_fit_for_college(user_email, university_id,
                                             intended_major=resolution['major'])
    if not fit_analysis:
        return None, ({'success': False, 'error': 'Fit computation failed — try again'}, 500)
    fit_analysis['intended_major_used'] = resolution['major'] or None
    fit_analysis['intended_major_source'] = resolution['source']

    save_result = save_fit_analysis(user_email, university_id, fit_analysis)
    if not save_result.get('success'):
        # An unsaved fit isn't delivered value — fail without charging.
        return None, ({'success': False,
                       'error': 'Fit computed but could not be saved — try again'}, 500)
    return fit_analysis, None


_CHANCES_KB_MISS_NOTE = (
    "this school has no major data in our knowledge base yet — the major-chances "
    "ranking was skipped (the gap is queued for collection); your fit analysis was "
    "still generated"
)
_CHANCES_HICCUP_NOTE = (
    "the major-chances ranking couldn't be generated right now — your fit analysis "
    "was still generated; try regenerating chances later"
)


def _generate_major_chances(user_email: str, university_id: str, db,
                            profile: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """Generate + save the ranking as part of the billed unit (no second
    charge). Returns (ranking_doc_or_None, note). A KB-majors miss records the
    demand signal and yields (None, note); a transport blip or ranking hiccup
    yields (None, note) too — never a failure, since the fit is the primary
    (billed) artifact and already succeeded."""
    facts = fetch_university_majors(university_id)
    if facts is None:
        # Transport blip — not a data gap; don't record kb_gap, just note it.
        return None, _CHANCES_HICCUP_NOTE

    gap_signal = _intended_majors(profile) or ['(whole catalog)']
    if not facts.get('success'):
        db.increment_kb_gap(university_id, gap_signal)
        return None, _CHANCES_KB_MISS_NOTE

    catalog_rows = build_full_catalog_rows(facts)
    if not catalog_rows:
        db.increment_kb_gap(university_id, gap_signal)
        return None, _CHANCES_KB_MISS_NOTE

    payload, status = run_ranking_generation(user_email, university_id, db,
                                             profile, facts, catalog_rows)
    if status != 200 or not payload.get('success'):
        return None, _CHANCES_HICCUP_NOTE
    return payload.get('ranking'), None


def run_add_college_analysis(data: Dict) -> Tuple[Dict, int]:
    """POST /add-college-analysis {user_email, university_id, force?}.

    ONE credit gate around BOTH artifacts. Returns (payload, status) where a
    successful payload is {success, fit_analysis, major_chances|null,
    university_id, note?}. `force` is accepted for the card's regenerate — the
    bundle always regenerates both artifacts, so it is a no-op beyond intent.
    """
    user_email = data.get('user_email')
    university_id = data.get('university_id')
    explicit_major = data.get('intended_major')
    db = get_db()

    credit_check = check_credits_available(user_email, ADD_ANALYSIS_CREDIT_COST)
    if credit_check.get('error') == 'credits_read_failed':
        # #298: a ledger read blip is retryable infra trouble — a 402 here would
        # show a paying user the upgrade modal for our outage.
        logger.warning(f"[ADD_ANALYSIS] Credit ledger unavailable for {user_email} — 503")
        return {'success': False, 'error': 'credits_unavailable_retry', 'retryable': True}, 503
    if not credit_check.get('has_credits'):
        logger.warning(f"[ADD_ANALYSIS] Insufficient credits for {user_email}")
        return {'success': False, 'error': 'insufficient_credits',
                'credits_remaining': credit_check.get('credits_remaining', 0)}, 402

    profile = db.get_profile(user_email)
    if not profile:
        return {'success': False, 'error': 'Profile not found'}, 404

    # (a) FIT — the primary artifact. Its failure fails the whole add, unbilled.
    fit_analysis, err = _compute_and_save_fit(user_email, university_id, db,
                                              profile, explicit_major)
    if err:
        payload, status = err
        return payload, status

    if fit_analysis.get('is_fallback'):
        # The LLM degraded to a placeholder fit — never charge for "analysis
        # unavailable, please retry" (mirror fit_billing F2). The fit doc is
        # still saved/returned for UI stability; chances are skipped.
        logger.warning(f"[ADD_ANALYSIS] Fallback fit for {university_id} — not billed")
        return {
            'success': True,
            'fit_analysis': fit_analysis,
            'major_chances': None,
            'university_id': university_id,
            'credits_remaining': credit_check.get('credits_remaining'),
            'billing_note': 'fallback analysis — not charged',
        }, 200

    # (b) MAJOR CHANCES — same credit; a miss/hiccup degrades to null + note.
    major_chances, note = _generate_major_chances(user_email, university_id, db, profile)

    # Bill exactly once, AFTER both artifacts, for the whole unit.
    deducted = deduct_credit(user_email, ADD_ANALYSIS_CREDIT_COST, ADD_ANALYSIS_REASON)
    if not deducted.get('success'):
        # Artifacts already generated and saved — ship them, but make the
        # revenue leak loud (same rule as fit_billing, #296 review F4).
        logger.warning(
            f"[ADD_ANALYSIS] deduct_credit FAILED after successful add for "
            f"{user_email}/{university_id}: {deducted.get('error')}"
        )

    payload = {
        'success': True,
        'fit_analysis': fit_analysis,
        'major_chances': major_chances,
        'university_id': university_id,
        'credits_remaining': deducted.get('credits_remaining'),
    }
    if note:
        payload['note'] = note
    return payload, 200
