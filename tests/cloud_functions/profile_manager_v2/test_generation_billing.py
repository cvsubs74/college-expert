"""Billed-generation sequencing (#284): check → 402 insufficient_credits →
generate → deduct exactly once AFTER success, never on failure. Mirrors
test_fit_billing's rigor for the shared helper both major endpoints ride."""

import logging
from unittest.mock import patch

import generation_billing


def _run(*, has_credits=True, remaining=5, gen_payload=None, gen_status=200,
         deduct_success=True, reason='major_map'):
    """Drive run_billed_generation with patched credit seams.
    Returns (payload, status, calls)."""
    calls = {'check': 0, 'deduct': 0, 'generate': 0}

    def fake_check(user_email, needed):
        calls['check'] += 1
        return {'has_credits': has_credits, 'credits_remaining': remaining,
                'credits_needed': needed}

    def fake_deduct(user_email, count, why):
        calls['deduct'] += 1
        calls['deduct_args'] = (user_email, count, why)
        return ({'success': True, 'credits_remaining': remaining - count}
                if deduct_success else {'success': False, 'error': 'firestore down'})

    def generate():
        calls['generate'] += 1
        if gen_payload is not None:
            return dict(gen_payload), gen_status
        return {'success': True, 'map': {'clusters': [{}]}}, 200

    with patch.object(generation_billing, 'check_credits_available', side_effect=fake_check), \
         patch.object(generation_billing, 'deduct_credit', side_effect=fake_deduct):
        payload, status = generation_billing.run_billed_generation(
            's@x.com', reason, generate)
    return payload, status, calls


def test_insufficient_credits_returns_402_and_never_generates():
    payload, status, calls = _run(has_credits=False, remaining=0)
    assert status == 402
    assert payload == {'success': False, 'error': 'insufficient_credits',
                       'credits_remaining': 0}
    assert calls['generate'] == 0 and calls['deduct'] == 0


def test_successful_generation_deducts_exactly_once_with_reason():
    payload, status, calls = _run(remaining=5, reason='major_strategy')
    assert status == 200 and payload['success'] is True
    assert calls['deduct'] == 1
    assert calls['deduct_args'] == ('s@x.com', 1, 'major_strategy')
    assert payload['credits_remaining'] == 4


def test_failed_generation_never_deducts():
    payload, status, calls = _run(
        gen_payload={'success': False, 'error': 'generation failed — try again'},
        gen_status=500)
    assert status == 500 and payload['success'] is False
    assert calls['deduct'] == 0
    assert 'credits_remaining' not in payload


def test_non_200_passthrough_never_deducts():
    # Input-shaped failures (404/422) ride the generate closure untouched
    # and unbilled — same passthrough rule as fit_billing.
    payload, status, calls = _run(
        gen_payload={'error': 'not found'}, gen_status=404)
    assert status == 404 and payload == {'error': 'not found'}
    assert calls['deduct'] == 0


def test_deduct_failure_after_success_still_ships_the_artifact(caplog):
    # The student got the artifact — ship it, log the revenue leak loudly
    # (same rule as fit_billing / #296 review F4).
    with caplog.at_level(logging.WARNING):
        payload, status, calls = _run(deduct_success=False)
    assert status == 200 and payload['success'] is True
    assert any('deduct_credit FAILED' in r.message for r in caplog.records)
