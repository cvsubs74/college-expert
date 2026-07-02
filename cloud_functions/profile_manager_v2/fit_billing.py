"""Cache/charge sequencing for POST /compute-single-fit (#285).

Restores the legacy ES billing contract in the active Firestore handler:
cache-unless-force → 402 insufficient_credits → compute → deduct 1 AFTER a
successful compute+save. Lives in its own module so the sequencing invariants
(deduct exactly once on success, never on failure or cache hit, force default
True when the key is absent) are unit-testable without the HTTP layer.
"""

import logging
from typing import Callable, Dict, Tuple

from credits import check_credits_available, deduct_credit
from fit_analysis import get_fit_analysis

logger = logging.getLogger(__name__)

FIT_CREDIT_COST = 1
FIT_CREDIT_REASON = 'fit_analysis'


def run_compute_single_fit(data: Dict, compute_and_save: Callable[[], Tuple[Dict, int]]) -> Tuple[Dict, int]:
    """Run the billed compute-single-fit sequence. Returns (payload, status).

    Args:
        data: parsed request body — reads user_email, university_id and the
            optional force_recompute flag.
        compute_and_save: zero-arg callable that fetches inputs, computes the
            fit, and persists it. Returns (payload, status); success is
            status 200 with payload['success'] True. Only invoked after the
            credit gate passes; the deduction fires only when it succeeds.

    Compatibility rule (load-bearing): an ABSENT force_recompute key defaults
    to True — pre-#285 callers (the QA agent, older MCP clients) never send it
    and rely on the always-compute behavior they were built against. Only an
    explicit false opts into the free cached path.
    """
    user_email = data.get('user_email')
    university_id = data.get('university_id')
    force_recompute = data.get('force_recompute', True)

    if not force_recompute:
        cached = get_fit_analysis(user_email, university_id)
        # A cached FALLBACK doc ("analysis unavailable — retry") is a miss:
        # serving it free would make a paid recompute the only path to a real
        # analysis (#296 review F2).
        if cached and not cached.get('is_fallback'):
            logger.info(f"[FIT] Returning cached fit for {university_id} (no charge)")
            return {
                'success': True,
                'fit_analysis': cached,
                'university_id': university_id,
                'from_cache': True,
            }, 200
        # No (real) cached fit → fall through to a (charged) compute.

    credit_check = check_credits_available(user_email, FIT_CREDIT_COST)
    if not credit_check.get('has_credits'):
        logger.warning(f"[FIT] Insufficient credits for {user_email}")
        return {
            'success': False,
            'error': 'insufficient_credits',
            'credits_remaining': credit_check.get('credits_remaining', 0),
        }, 402

    payload, status = compute_and_save()
    if status != 200 or not payload.get('success'):
        # Failed compute or save (404 inputs, 500 LLM/persistence) — never charge.
        return payload, status

    if (payload.get('fit_analysis') or {}).get('is_fallback'):
        # The LLM failed and the compute degraded to a placeholder doc —
        # never charge a student for "analysis unavailable, please retry"
        # (#296 review F2). The doc is still saved/returned for UI stability.
        logger.warning(f"[FIT] Fallback fit for {university_id} — not billed")
        payload['from_cache'] = False
        payload['credits_remaining'] = credit_check.get('credits_remaining')
        payload['billing_note'] = 'fallback analysis — not charged'
        return payload, status

    deducted = deduct_credit(user_email, FIT_CREDIT_COST, FIT_CREDIT_REASON)
    if not deducted.get('success'):
        # Fit already computed and saved — ship it, but make the revenue
        # leak loud (#296 review F4).
        logger.warning(
            f"[FIT] deduct_credit FAILED after successful compute for "
            f"{user_email}/{university_id}: {deducted.get('error')}"
        )
    payload['from_cache'] = False
    payload['credits_remaining'] = deducted.get('credits_remaining')
    return payload, status
