"""Outbound service identity for counselor→PM calls (#223)."""

import sys
import types
from unittest.mock import patch

import svc_auth


def _stub_google(monkeypatch, fetch):
    fake_id_token = types.SimpleNamespace(fetch_id_token=fetch)
    fake_transport = types.SimpleNamespace(Request=lambda: None)
    monkeypatch.setitem(sys.modules, 'google.oauth2', types.SimpleNamespace(id_token=fake_id_token))
    monkeypatch.setitem(sys.modules, 'google.oauth2.id_token', fake_id_token)
    monkeypatch.setitem(sys.modules, 'google.auth.transport', types.SimpleNamespace(requests=fake_transport))
    monkeypatch.setitem(sys.modules, 'google.auth.transport.requests', fake_transport)


def test_headers_carry_token_and_cache_per_audience(monkeypatch):
    svc_auth._cache.clear()
    calls = []
    _stub_google(monkeypatch, lambda request, audience: calls.append(audience) or 'oidc-token')
    with patch.dict('os.environ', {'PROFILE_MANAGER_URL': 'https://pm.example/'}, clear=False):
        h1 = svc_auth.pm_auth_headers()
        h2 = svc_auth.pm_auth_headers()
    assert h1 == {'Authorization': 'Bearer oidc-token'} and h2 == h1
    assert calls == ['https://pm.example']   # trailing slash normalized; one fetch
    svc_auth._cache.clear()


def test_no_metadata_server_degrades_to_empty(monkeypatch):
    svc_auth._cache.clear()
    def boom(request, audience):
        raise RuntimeError('no metadata server')
    _stub_google(monkeypatch, boom)
    with patch.dict('os.environ', {'PROFILE_MANAGER_URL': 'https://pm.example'}, clear=False):
        assert svc_auth.pm_auth_headers() == {}


def test_unconfigured_pm_url_is_empty(monkeypatch):
    with patch.dict('os.environ', {'PROFILE_MANAGER_URL': ''}, clear=False):
        assert svc_auth.pm_auth_headers() == {}
