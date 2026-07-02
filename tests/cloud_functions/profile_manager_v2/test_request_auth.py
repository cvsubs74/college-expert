"""Caller-identity verification (#223): the verified credential — never the
raw X-User-Email — is what scopes data access, across all three AUTH_MODEs."""

import types
from unittest.mock import patch

import request_auth


def _req(headers=None, path='/get-profile'):
    return types.SimpleNamespace(headers=headers or {}, path=path)


def _bearer(req_headers=None):
    h = {'Authorization': 'Bearer tok'}
    h.update(req_headers or {})
    return _req(headers=h)


def _fb_claims(email='student@x.com', verified=True):
    return {'email': email, 'email_verified': verified}


def _svc_claims(email, aud, verified=True):
    return {'email': email, 'email_verified': verified, 'aud': aud}


_ENV = {
    'AUTH_MODE': 'enforce',
    'FIREBASE_PROJECT_ID': 'college-counselling-478115',
    'TRUSTED_SERVICE_EMAILS': 'svc@dev.gserviceaccount.com',
    'SELF_AUDIENCES': 'https://pm.example,https://fn.example/pm',
}


def _run_gate(req, claimed, env=None, firebase=None, oidc=None, decode=None):
    env_full = {**_ENV, **(env or {})}
    with patch.dict('os.environ', env_full, clear=False), \
         patch.object(request_auth, '_decode_unverified',
                      side_effect=decode or (lambda t: {'iss': 'https://securetoken.google.com/x'})), \
         patch.object(request_auth, '_verify_firebase',
                      side_effect=firebase or (lambda t, a: _fb_claims())), \
         patch.object(request_auth, '_verify_google_oidc',
                      side_effect=oidc or (lambda t: (_ for _ in ()).throw(ValueError('no oidc')))):
        return request_auth.gate_request(req, claimed)


class TestEnforceMode:
    def test_anonymous_is_401(self):
        allow, identity, rejection = _run_gate(_req(), 'victim@x.com')
        assert allow is False
        assert rejection[1] == 401
        assert rejection[0]['error'] == 'authentication required'

    def test_invalid_token_is_401(self):
        allow, _, rejection = _run_gate(
            _bearer(), 'victim@x.com',
            decode=lambda t: (_ for _ in ()).throw(ValueError('garbage')))
        assert allow is False and rejection[1] == 401

    def test_expired_or_bad_signature_is_401(self):
        allow, _, rejection = _run_gate(
            _bearer(), 'victim@x.com',
            firebase=lambda t, a: (_ for _ in ()).throw(ValueError('Token expired')))
        assert allow is False and rejection[1] == 401

    def test_verified_user_matching_claim_allows(self):
        allow, identity, rejection = _run_gate(_bearer(), 'student@x.com')
        assert allow is True and rejection is None
        assert identity == {'kind': 'user', 'email': 'student@x.com', 'error': None}

    def test_the_idor_attack_is_403(self):
        """The whole point: a valid login for attacker@x.com must not read
        victim@x.com's data by setting X-User-Email."""
        allow, identity, rejection = _run_gate(
            _bearer(), 'victim@x.com',
            firebase=lambda t, a: _fb_claims('attacker@x.com'))
        assert allow is False
        assert rejection[1] == 403
        assert 'identity mismatch' in rejection[0]['error']

    def test_claim_matching_is_case_insensitive(self):
        allow, _, _ = _run_gate(_bearer(), 'Student@X.com')
        assert allow is True

    def test_unverified_firebase_email_is_401(self):
        allow, _, rejection = _run_gate(
            _bearer(), 'student@x.com',
            firebase=lambda t, a: _fb_claims(verified=False))
        assert allow is False and rejection[1] == 401

    def test_route_without_claimed_email_still_requires_credential(self):
        allow, _, rejection = _run_gate(_req(), None)
        assert allow is False and rejection[1] == 401


class TestServiceCallers:
    def _svc(self, claimed='student@x.com', **kw):
        return _run_gate(
            _bearer(), claimed,
            decode=lambda t: {'iss': 'https://accounts.google.com'},
            **kw)

    def test_trusted_service_with_our_audience_vouches_for_claimed(self):
        allow, identity, rejection = self._svc(
            oidc=lambda t: _svc_claims('svc@dev.gserviceaccount.com', 'https://pm.example'))
        assert allow is True and rejection is None
        assert identity['kind'] == 'service'

    def test_wrong_audience_is_rejected(self):
        """Audience binding: a token minted for ANOTHER service must not
        work here (confused-deputy / token replay)."""
        allow, _, rejection = self._svc(
            oidc=lambda t: _svc_claims('svc@dev.gserviceaccount.com', 'https://other.example'))
        assert allow is False and rejection[1] == 401

    def test_untrusted_service_account_is_rejected(self):
        allow, _, rejection = self._svc(
            oidc=lambda t: _svc_claims('evil@attacker.gserviceaccount.com', 'https://pm.example'))
        assert allow is False and rejection[1] == 401

    def test_trailing_slash_audience_normalized(self):
        allow, _, _ = self._svc(
            oidc=lambda t: _svc_claims('svc@dev.gserviceaccount.com', 'https://pm.example/'))
        assert allow is True


class TestRolloutModes:
    def test_log_mode_allows_anonymous(self):
        allow, identity, rejection = _run_gate(_req(), 'x@y.com', env={'AUTH_MODE': 'log'})
        assert allow is True and rejection is None
        assert identity['kind'] == 'anonymous'

    def test_log_mode_allows_mismatch_but_still_verifies(self):
        allow, identity, _ = _run_gate(
            _bearer(), 'victim@x.com', env={'AUTH_MODE': 'log'},
            firebase=lambda t, a: _fb_claims('attacker@x.com'))
        assert allow is True
        assert identity['email'] == 'attacker@x.com'  # verified truth is surfaced

    def test_off_mode_bypasses_everything(self):
        allow, identity, _ = _run_gate(_req(), 'x@y.com', env={'AUTH_MODE': 'off'})
        assert allow is True and identity['kind'] == 'off'

    def test_default_and_garbage_modes_are_log(self):
        with patch.dict('os.environ', {'AUTH_MODE': ''}, clear=False):
            assert request_auth._mode() == 'log'
        with patch.dict('os.environ', {'AUTH_MODE': 'bananas'}, clear=False):
            assert request_auth._mode() == 'log'
