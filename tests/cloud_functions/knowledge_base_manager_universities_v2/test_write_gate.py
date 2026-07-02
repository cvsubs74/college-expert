"""KB write gate (#223): ingest/delete require a credential (trusted service
OIDC or the KB_WRITE_TOKEN used by the ingest CLI); reads stay public."""

import types
from unittest.mock import patch


def _req(headers=None, method='POST', path='/'):
    return types.SimpleNamespace(headers=headers or {}, method=method, path=path)


def _gate(kb, req, mode='enforce', token_env='sekrit', identity=None):
    env = {'AUTH_MODE': mode}
    if token_env is not None:
        env['KB_WRITE_TOKEN'] = token_env
    with patch.dict('os.environ', env, clear=False), \
         patch.object(kb.main, 'authenticate',
                      return_value=identity or {'kind': 'anonymous', 'email': None, 'error': None}):
        return kb.main.gate_write(req)


class TestKbWriteGate:
    def test_anonymous_write_rejected_in_enforce(self, kb):
        allow, rejection = _gate(kb, _req())
        assert allow is False
        assert rejection[1] == 401

    def test_cli_write_token_allows(self, kb):
        allow, rejection = _gate(kb, _req(headers={'X-Admin-Token': 'sekrit'}))
        assert allow is True and rejection is None

    def test_wrong_admin_token_rejected(self, kb):
        allow, rejection = _gate(kb, _req(headers={'X-Admin-Token': 'nope'}))
        assert allow is False and rejection[1] == 401

    def test_unset_token_env_never_matches_empty_header(self, kb):
        # No configured token + no header must NOT accidentally compare '' == ''.
        allow, rejection = _gate(kb, _req(), token_env=None)
        assert allow is False and rejection[1] == 401

    def test_trusted_service_allows(self, kb):
        allow, _ = _gate(kb, _req(), identity={'kind': 'service',
                                               'email': 'svc@dev.gserviceaccount.com',
                                               'error': None})
        assert allow is True

    def test_user_token_is_not_enough_for_writes(self, kb):
        # A student's Firebase token must not let them rewrite the KB.
        allow, rejection = _gate(kb, _req(), identity={'kind': 'user',
                                                       'email': 's@x.com', 'error': None})
        assert allow is False and rejection[1] == 401

    def test_log_mode_allows_but_would_log(self, kb):
        allow, rejection = _gate(kb, _req(), mode='log')
        assert allow is True and rejection is None

    def test_off_mode_bypasses(self, kb):
        allow, _ = _gate(kb, _req(), mode='off')
        assert allow is True


class TestReadsStayPublic:
    def test_get_by_id_needs_no_credential(self, kb, make_profile):
        with patch.dict('os.environ', {'AUTH_MODE': 'enforce'}, clear=False):
            kb.main.ingest_university(make_profile(), year=2026)  # direct fn call, no HTTP gate
            result = kb.main.get_university('testu')
        assert result['success'] is True
