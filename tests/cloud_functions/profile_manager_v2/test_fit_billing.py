"""compute-single-fit billing sequence (#285): cache-unless-force → 402
insufficient_credits → compute → deduct exactly once AFTER success. The
sequencing lives in fit_billing.run_compute_single_fit so it's testable
without the HTTP layer; main.py only wires the compute closure in."""

from unittest.mock import patch

import fit_billing


_FIT = {'fit_category': 'TARGET', 'match_percentage': 72}


def _run(body, *, cached=None, has_credits=True, remaining=5,
         compute_payload=None, compute_status=200):
    """Drive run_compute_single_fit with patched credit/cache seams.
    Returns (payload, status, calls) where calls records every side effect."""
    calls = {'get_cached': 0, 'check': 0, 'deduct': 0, 'compute': 0}

    def fake_get(user_email, university_id):
        calls['get_cached'] += 1
        return cached

    def fake_check(user_email, needed):
        calls['check'] += 1
        return {'has_credits': has_credits, 'credits_remaining': remaining,
                'credits_needed': needed}

    def fake_deduct(user_email, count, reason):
        calls['deduct'] += 1
        calls['deduct_args'] = (user_email, count, reason)
        return {'success': True, 'credits_remaining': remaining - count,
                'credits_deducted': count, 'reason': reason}

    def compute():
        calls['compute'] += 1
        if compute_payload is not None:
            return dict(compute_payload), compute_status
        return {'success': True, 'fit_analysis': dict(_FIT),
                'university_id': body.get('university_id')}, 200

    with patch.object(fit_billing, 'get_fit_analysis', side_effect=fake_get), \
         patch.object(fit_billing, 'check_credits_available', side_effect=fake_check), \
         patch.object(fit_billing, 'deduct_credit', side_effect=fake_deduct):
        payload, status = fit_billing.run_compute_single_fit(body, compute)
    return payload, status, calls


def test_absent_force_recompute_defaults_to_compute():
    # Compatibility rule (load-bearing): the QA agent and pre-#285 MCP clients
    # never send force_recompute — they must keep recomputing, cache untouched.
    body = {'user_email': 's@x.com', 'university_id': 'duke'}
    payload, status, calls = _run(body, cached=dict(_FIT))
    assert status == 200 and payload['success'] is True
    assert calls['get_cached'] == 0          # cache never consulted
    assert calls['compute'] == 1
    assert payload['from_cache'] is False


def test_force_false_with_cached_fit_returns_cache_free():
    body = {'user_email': 's@x.com', 'university_id': 'duke',
            'force_recompute': False}
    payload, status, calls = _run(body, cached=dict(_FIT))
    assert status == 200
    assert payload == {'success': True, 'fit_analysis': _FIT,
                       'university_id': 'duke', 'from_cache': True}
    # No charge of any kind on a cache hit.
    assert calls['check'] == 0 and calls['deduct'] == 0 and calls['compute'] == 0


def test_force_false_without_cached_fit_falls_through_to_charged_compute():
    body = {'user_email': 's@x.com', 'university_id': 'duke',
            'force_recompute': False}
    payload, status, calls = _run(body, cached=None)
    assert status == 200 and payload['from_cache'] is False
    assert calls['get_cached'] == 1 and calls['compute'] == 1 and calls['deduct'] == 1


def test_insufficient_credits_returns_402_and_never_computes():
    body = {'user_email': 's@x.com', 'university_id': 'duke',
            'force_recompute': True}
    payload, status, calls = _run(body, has_credits=False, remaining=0)
    assert status == 402
    assert payload == {'success': False, 'error': 'insufficient_credits',
                       'credits_remaining': 0}
    assert calls['compute'] == 0 and calls['deduct'] == 0


def test_successful_compute_deducts_exactly_once_with_reason():
    body = {'user_email': 's@x.com', 'university_id': 'duke',
            'force_recompute': True}
    payload, status, calls = _run(body, remaining=5)
    assert status == 200 and payload['success'] is True
    assert calls['deduct'] == 1
    assert calls['deduct_args'] == ('s@x.com', 1, 'fit_analysis')
    # The deduct result's balance is surfaced to the caller.
    assert payload['credits_remaining'] == 4
    assert payload['from_cache'] is False


def test_failed_compute_never_deducts():
    body = {'user_email': 's@x.com', 'university_id': 'duke'}
    payload, status, calls = _run(
        body,
        compute_payload={'success': False, 'error': 'Fit computation failed — try again'},
        compute_status=500)
    assert status == 500 and payload['success'] is False
    assert calls['deduct'] == 0


def test_missing_inputs_404_from_compute_never_deducts():
    # Profile/university 404s ride the compute closure — they pass through
    # untouched and unbilled.
    body = {'user_email': 's@x.com', 'university_id': 'duke'}
    payload, status, calls = _run(
        body, compute_payload={'error': 'Profile not found'}, compute_status=404)
    assert status == 404 and payload == {'error': 'Profile not found'}
    assert calls['deduct'] == 0
