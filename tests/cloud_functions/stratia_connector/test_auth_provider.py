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


class _Client:
    def __init__(self, cid):
        self.client_id = cid
