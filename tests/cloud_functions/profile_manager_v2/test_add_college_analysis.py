"""Bundled add-college analysis billing (#310): ONE credit → BOTH the fit AND
the major-chances ranking, as a single billed unit.

Pins the invariants that keep the bundle honest (mirrors fit_billing/
generation_billing discipline, extended to two artifacts on one charge):
  - deduct EXACTLY once, AFTER both artifacts, only on success
  - 402 insufficient_credits (never computes) / 503 on the credits_read_failed marker
  - a fit failure / save failure → 500, unbilled
  - a fallback fit is never billed
  - a KB-majors miss → major_chances null + kb_gap, still one charge, fit saved
  - a ranking hiccup degrades chances to null without failing or double-charging
"""

from unittest.mock import patch

import add_college_analysis as aca


_FIT_OK = {'fit_category': 'TARGET', 'match_percentage': 65, 'acceptance_rate': 30}
_RANKING_OK = {'tiers': {'strong': [], 'possible': [], 'reach': [{'name': 'CS'}], 'long_shot': []}}
_FACTS = {'success': True, 'data_year': 2026,
          'colleges': [{'name': 'C', 'majors': [{'name': 'Computer Science'}]}]}


class FakeDB:
    def __init__(self, profile=None, list_item=None):
        self.profile = profile if profile is not None else {'intended_majors': ['Computer Science']}
        self.list_item = list_item
        self.kb_gap_calls = []

    def get_profile(self, user_id):
        return self.profile

    def get_college_list_item(self, user_id, university_id):
        return self.list_item

    def increment_kb_gap(self, university_id, names):
        self.kb_gap_calls.append((university_id, list(names)))
        return True


_UNSET = object()


def _run(*, body=None, has_credits=True, remaining=5, credits_error=None,
         profile=None, university_profile={'metadata': {}}, fit=_UNSET,
         save_fit_ok=True, facts=_UNSET, catalog_rows=None,
         ranking_payload=None, deduct_ok=True):
    body = body or {'user_email': 's@x.com', 'university_id': 'uw'}
    fit = _FIT_OK if fit is _UNSET else fit
    facts = _FACTS if facts is _UNSET else facts
    catalog_rows = [{'name': 'Computer Science'}] if catalog_rows is None else catalog_rows
    ranking_payload = ranking_payload or ({'success': True, 'ranking': _RANKING_OK}, 200)
    db = FakeDB(profile=profile)
    calls = {'check': 0, 'deduct': 0}

    def fake_check(user_email, needed):
        calls['check'] += 1
        if credits_error:
            return {'error': credits_error}
        return {'has_credits': has_credits, 'credits_remaining': remaining}

    def fake_deduct(user_email, count, reason):
        calls['deduct'] += 1
        calls['deduct_args'] = (user_email, count, reason)
        return {'success': deduct_ok, 'credits_remaining': remaining - count,
                'error': None if deduct_ok else 'firestore down'}

    with patch.object(aca, 'check_credits_available', side_effect=fake_check), \
         patch.object(aca, 'deduct_credit', side_effect=fake_deduct), \
         patch.object(aca, 'get_db', return_value=db), \
         patch.object(aca, 'fetch_university_profile', return_value=university_profile), \
         patch.object(aca, 'calculate_fit_for_college', return_value=(dict(fit) if fit else None)), \
         patch.object(aca, 'save_fit_analysis', return_value={'success': save_fit_ok}), \
         patch.object(aca, 'fetch_university_majors', return_value=facts), \
         patch.object(aca, 'build_full_catalog_rows', return_value=catalog_rows), \
         patch.object(aca, 'run_ranking_generation', return_value=ranking_payload) as p_rank:
        payload, status = aca.run_add_college_analysis(body)
    calls['rank'] = p_rank.call_count
    return payload, status, calls, db


def test_success_deducts_once_for_both_artifacts():
    payload, status, calls, _ = _run()
    assert status == 200 and payload['success'] is True
    assert payload['fit_analysis']['fit_category'] == 'TARGET'
    assert payload['major_chances'] == _RANKING_OK
    # ONE credit for the bundle — not two.
    assert calls['deduct'] == 1
    assert calls['deduct_args'] == ('s@x.com', 1, 'add_college_analysis')
    assert payload['credits_remaining'] == 4


def test_force_is_accepted_and_regenerates():
    payload, status, calls, _ = _run(
        body={'user_email': 's@x.com', 'university_id': 'uw', 'force': True})
    assert status == 200 and calls['deduct'] == 1
    assert payload['major_chances'] == _RANKING_OK


def test_insufficient_credits_402_never_computes():
    payload, status, calls, _ = _run(has_credits=False, remaining=0)
    assert status == 402
    assert payload == {'success': False, 'error': 'insufficient_credits',
                       'credits_remaining': 0}
    assert calls['deduct'] == 0 and calls['rank'] == 0


def test_credits_read_failure_is_503_unbilled():
    payload, status, calls, _ = _run(credits_error='credits_read_failed')
    assert status == 503 and payload['retryable'] is True
    assert calls['deduct'] == 0 and calls['rank'] == 0


def test_fit_failure_is_500_unbilled():
    payload, status, calls, _ = _run(fit=None)
    assert status == 500 and calls['deduct'] == 0 and calls['rank'] == 0


def test_fit_save_failure_is_500_unbilled():
    payload, status, calls, _ = _run(save_fit_ok=False)
    assert status == 500 and calls['deduct'] == 0 and calls['rank'] == 0


def test_missing_university_profile_is_404_unbilled():
    payload, status, calls, _ = _run(university_profile=None)
    assert status == 404 and calls['deduct'] == 0


def test_fallback_fit_is_never_billed():
    fb = {'fit_category': 'REACH', 'match_percentage': 45, 'is_fallback': True}
    payload, status, calls, _ = _run(fit=fb)
    assert status == 200 and calls['deduct'] == 0
    assert payload['major_chances'] is None
    assert payload['billing_note'] == 'fallback analysis — not charged'
    # A fallback fit skips the chances step entirely (nothing worth ranking).
    assert calls['rank'] == 0


def test_kb_majors_miss_yields_null_chances_and_still_charges_once():
    # facts present but no offered majors → chances null + kb_gap, fit still
    # saved, and the single bundle credit still applies (adding always costs 1).
    payload, status, calls, db = _run(catalog_rows=[])
    assert status == 200 and payload['success'] is True
    assert payload['fit_analysis']['fit_category'] == 'TARGET'
    assert payload['major_chances'] is None
    assert 'note' in payload
    assert calls['rank'] == 0          # never reached the ranking generator
    assert calls['deduct'] == 1        # one charge for the fit — never a second
    assert db.kb_gap_calls == [('uw', ['Computer Science'])]


def test_kb_unavailable_blip_yields_null_chances_no_gap_still_charges():
    payload, status, calls, db = _run(facts=None)
    assert status == 200 and payload['major_chances'] is None
    assert 'note' in payload
    assert calls['deduct'] == 1
    assert db.kb_gap_calls == []       # a transport blip is not a data gap


def test_ranking_hiccup_degrades_to_null_without_failing_or_double_charging():
    payload, status, calls, _ = _run(ranking_payload=({'success': False}, 500))
    assert status == 200 and payload['success'] is True
    assert payload['major_chances'] is None and 'note' in payload
    assert calls['deduct'] == 1        # fit is the billed primary artifact


def test_deduct_failure_after_success_still_ships_the_bundle(caplog):
    import logging
    with caplog.at_level(logging.WARNING):
        payload, status, calls, _ = _run(deduct_ok=False)
    assert status == 200 and payload['success'] is True
    assert payload['fit_analysis']['fit_category'] == 'TARGET'
    assert any('deduct_credit FAILED' in r.message for r in caplog.records)
