"""Shared check→402→generate→deduct-once sequencing for billed LLM artifacts
(#284): generate-major-map and generate-major-strategy.

Mirrors fit_billing.run_compute_single_fit's tested invariants — deduct
exactly once AFTER a successful generate+save, never on failure, 402 with
credits_remaining before any generation work — parameterized by the deduction
reason so both endpoints share one audited code path. Cache short-circuits and
the never-charge-on-miss rule live in the callers (major_llm), BEFORE this
gate, so a student with an empty balance still gets the free answers free.
"""

import logging
from typing import Callable, Dict, Tuple

from credits import check_credits_available, deduct_credit

logger = logging.getLogger(__name__)

GENERATION_CREDIT_COST = 1


def run_billed_generation(user_email: str, reason: str,
                          generate: Callable[[], Tuple[Dict, int]]) -> Tuple[Dict, int]:
    """Run a billed generation sequence. Returns (payload, status).

    Args:
        user_email: the student being billed.
        reason: deduction reason recorded in the credit ledger
            ('major_map' / 'major_strategy').
        generate: zero-arg callable that generates AND persists the artifact.
            Returns (payload, status); success is status 200 with
            payload['success'] True. Only invoked after the credit gate
            passes; the deduction fires only when it succeeds.
    """
    credit_check = check_credits_available(user_email, GENERATION_CREDIT_COST)
    if not credit_check.get('has_credits'):
        logger.warning(f"[GEN_BILLING] Insufficient credits for {user_email} ({reason})")
        return {
            'success': False,
            'error': 'insufficient_credits',
            'credits_remaining': credit_check.get('credits_remaining', 0),
        }, 402

    payload, status = generate()
    if status != 200 or not payload.get('success'):
        # Failed generation or save (LLM/persistence) — never charge.
        return payload, status

    deducted = deduct_credit(user_email, GENERATION_CREDIT_COST, reason)
    if not deducted.get('success'):
        # Artifact already generated and saved — ship it, but make the
        # revenue leak loud (same rule as fit_billing, #296 review F4).
        logger.warning(
            f"[GEN_BILLING] deduct_credit FAILED after successful {reason} "
            f"generation for {user_email}: {deducted.get('error')}"
        )
    payload['credits_remaining'] = deducted.get('credits_remaining')
    return payload, status
