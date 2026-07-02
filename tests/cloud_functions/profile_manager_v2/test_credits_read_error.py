"""#298: a credit-ledger READ failure must never re-initialize (WRITE) a
fresh free-tier record over a paying user's balance, and must surface as a
retryable error — never as insufficient_credits (the upsell modal)."""

from unittest.mock import patch

import credits as credits_mod
import fit_billing


class _RaisingDB:
    def __init__(self):
        self.saves = []

    def get_credits(self, user_id):
        raise RuntimeError('firestore read blip')

    def save_credits(self, user_id, record):
        self.saves.append((user_id, record))
        return True


class _EmptyDB(_RaisingDB):
    def get_credits(self, user_id):
        return None   # confirmed-missing document


def test_read_error_returns_marker_and_never_writes():
    db = _RaisingDB()
    with patch.object(credits_mod, 'get_db', return_value=db):
        out = credits_mod.get_user_credits('paying@user.com')
    assert out['error'] == 'credits_read_failed' and out['retryable'] is True
    assert db.saves == []                      # the dangerous write never happens


def test_confirmed_missing_doc_still_initializes():
    db = _EmptyDB()
    with patch.object(credits_mod, 'get_db', return_value=db):
        out = credits_mod.get_user_credits('new@user.com')
    assert out['tier'] == 'free' and out['credits_remaining'] == 3
    assert len(db.saves) == 1                  # init happens on true absence only


def test_check_maps_read_error_to_retryable_not_broke():
    db = _RaisingDB()
    with patch.object(credits_mod, 'get_db', return_value=db):
        out = credits_mod.check_credits_available('paying@user.com', 1)
    assert out['has_credits'] is False
    assert out['error'] == 'credits_read_failed' and out['retryable'] is True
    assert out['credits_remaining'] is None    # unknown, not zero


def test_deduct_on_read_error_neither_writes_nor_misreports():
    db = _RaisingDB()
    with patch.object(credits_mod, 'get_db', return_value=db):
        out = credits_mod.deduct_credit('paying@user.com', 1, 'fit_analysis')
    assert out == {'success': False, 'error': 'credits_read_failed', 'retryable': True}
    assert db.saves == []


def test_fit_billing_returns_503_retryable_not_402():
    body = {'user_email': 'paying@user.com', 'university_id': 'duke'}
    compute_calls = []

    with patch.object(fit_billing, 'get_fit_analysis', return_value=None), \
         patch.object(fit_billing, 'check_credits_available',
                      return_value={'has_credits': False, 'credits_remaining': None,
                                    'credits_needed': 1,
                                    'error': 'credits_read_failed', 'retryable': True}), \
         patch.object(fit_billing, 'deduct_credit') as deduct:
        payload, status = fit_billing.run_compute_single_fit(
            body, lambda: compute_calls.append(1) or ({'success': True}, 200))
    assert status == 503
    assert payload['error'] == 'credits_unavailable_retry'
    assert compute_calls == [] and not deduct.called
