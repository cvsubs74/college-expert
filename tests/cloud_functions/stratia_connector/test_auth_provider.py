"""OAuth provider token lifecycle. Needs `mcp` (skipped where not installed,
e.g. the lightweight CI backend image)."""
import pytest

pytest.importorskip("mcp")
# A full-suite run may stub a fake `google` package (counselor_agent conftest);
# skip rather than error when the real google.auth isn't importable.
pytest.importorskip("google.auth")

import asyncio

from auth_provider import GoogleOAuthProvider
from store import OAuthStore


def _provider():
    return GoogleOAuthProvider(OAuthStore(use_firestore=False))


def test_auth_code_exchange_issues_tokens_bound_to_email():
    p = _provider()
    # Simulate what complete_google_login stores after verifying a Google email.
    p.store.put_code("mcp_abc", {
        "client_id": "c1", "redirect_uri": "https://claude.ai/cb",
        "redirect_uri_provided_explicitly": True, "code_challenge": "chal",
        "scopes": ["stratia"], "resource": None, "email": "stu@x.com",
    }, ttl=60)

    from mcp.server.auth.provider import AuthorizationCode
    code = asyncio.run(p.load_authorization_code(_Client("c1"), "mcp_abc"))
    assert isinstance(code, AuthorizationCode)

    token = asyncio.run(p.exchange_authorization_code(_Client("c1"), code))
    assert token.access_token.startswith("at_")
    # token resolves back to the verified email; code is now consumed
    assert p.email_for_token(token.access_token) == "stu@x.com"
    assert p.store.get_code("mcp_abc") is None


def test_refresh_rotates_and_keeps_email():
    p = _provider()
    tok = p._issue_tokens("c1", ["stratia"], "stu@x.com")
    from mcp.server.auth.provider import RefreshToken
    rt = asyncio.run(p.load_refresh_token(_Client("c1"), tok.refresh_token))
    assert isinstance(rt, RefreshToken)
    new = asyncio.run(p.exchange_refresh_token(_Client("c1"), rt, ["stratia"]))
    assert new.access_token != tok.access_token
    assert p.email_for_token(new.access_token) == "stu@x.com"
    assert p.store.get_refresh(tok.refresh_token) is None  # old refresh rotated out


def test_verify_unknown_token_returns_none():
    p = _provider()
    assert asyncio.run(p.verify_token("nope")) is None


def test_issued_token_is_audience_bound_and_carries_subject():
    p = _provider()
    tok = p._issue_tokens("c1", ["stratia"], "stu@x.com", resource=None)
    at = asyncio.run(p.verify_token(tok.access_token))
    assert at.subject == "stu@x.com"           # RFC 9068 sub
    assert at.resource and at.resource.endswith("/mcp")  # RFC 8707 audience-bound


def test_auth_code_is_single_use():
    p = _provider()
    p.store.put_code("mcp_x", {
        "client_id": "c1", "redirect_uri": "https://claude.ai/cb",
        "redirect_uri_provided_explicitly": True, "code_challenge": "chal",
        "scopes": ["stratia"], "resource": None, "email": "stu@x.com",
    }, ttl=60)
    code = asyncio.run(p.load_authorization_code(_Client("c1"), "mcp_x"))
    asyncio.run(p.exchange_authorization_code(_Client("c1"), code))  # first ok
    import pytest
    from mcp.server.auth.provider import TokenError
    with pytest.raises(TokenError):
        asyncio.run(p.exchange_authorization_code(_Client("c1"), code))  # replay rejected


def test_audience_mismatch_rejected_at_exchange():
    p = _provider()
    p.store.put_code("mcp_y", {
        "client_id": "c1", "redirect_uri": "https://claude.ai/cb",
        "redirect_uri_provided_explicitly": True, "code_challenge": "chal",
        "scopes": ["stratia"], "resource": "https://evil.example.com/mcp",
        "email": "stu@x.com",
    }, ttl=60)
    code = asyncio.run(p.load_authorization_code(_Client("c1"), "mcp_y"))
    import pytest
    from mcp.server.auth.provider import TokenError
    with pytest.raises(TokenError):
        asyncio.run(p.exchange_authorization_code(_Client("c1"), code))


def test_google_login_requires_verified_email(monkeypatch):
    import pytest
    p = _provider()
    p.store.put_state("st1", {
        "client_id": "c1", "redirect_uri": "https://claude.ai/cb",
        "redirect_uri_provided_explicitly": True, "code_challenge": "chal",
        "scopes": ["stratia"], "client_state": "abc", "resource": None,
    }, ttl=60)

    import auth_provider as ap

    class _Tok:
        def raise_for_status(self): pass
        def json(self): return {"id_token": "fake"}

    monkeypatch.setattr(ap.requests, "post", lambda *a, **k: _Tok())
    # Google returns an UNVERIFIED email → must be rejected.
    monkeypatch.setattr(ap.google_id_token, "verify_oauth2_token",
                       lambda *a, **k: {"email": "stu@x.com", "email_verified": False})
    with pytest.raises(ValueError):
        p.complete_google_login("g_code", "st1")


class _Client:
    def __init__(self, cid):
        self.client_id = cid
