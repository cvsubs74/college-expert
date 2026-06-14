"""PKCE + OAuth store (in-memory backend). Stdlib only — CI-safe."""
import time

import pkce
from store import OAuthStore


class TestPkce:
    def test_round_trip(self):
        v = pkce.new_token()
        assert pkce.verify_pkce(v, pkce.s256_challenge(v)) is True

    def test_mismatch_rejected(self):
        assert pkce.verify_pkce("a" * 50, pkce.s256_challenge("b" * 50)) is False

    def test_empty_rejected(self):
        assert pkce.verify_pkce("", "x") is False
        assert pkce.verify_pkce("x", "") is False

    def test_tokens_unique_and_prefixed(self):
        a, b = pkce.new_token("at_"), pkce.new_token("at_")
        assert a != b and a.startswith("at_")


class TestStore:
    def test_client_round_trip(self):
        s = OAuthStore(use_firestore=False)
        s.put_client("c1", {"client_id": "c1", "x": 1})
        assert s.get_client("c1")["x"] == 1
        assert s.get_client("missing") is None

    def test_state_is_one_time(self):
        s = OAuthStore(use_firestore=False)
        s.put_state("st", {"email": "a@b.com"}, ttl=60)
        assert s.pop_state("st")["email"] == "a@b.com"
        assert s.pop_state("st") is None  # consumed

    def test_expired_state_returns_none(self):
        s = OAuthStore(use_firestore=False)
        s.put_state("st", {"email": "a@b.com"}, ttl=-1)
        assert s.pop_state("st") is None

    def test_code_get_is_non_destructive_until_delete(self):
        s = OAuthStore(use_firestore=False)
        s.put_code("mcp_x", {"email": "a@b.com", "client_id": "c1"}, ttl=60)
        assert s.get_code("mcp_x")["email"] == "a@b.com"
        assert s.get_code("mcp_x") is not None  # still there
        s.delete_code("mcp_x")
        assert s.get_code("mcp_x") is None

    def test_access_token_expiry(self):
        s = OAuthStore(use_firestore=False)
        s.put_access("at", {"email": "a@b.com", "client_id": "c1", "scopes": ["stratia"]}, ttl=60)
        assert s.get_access("at")["email"] == "a@b.com"
        s.put_access("at2", {"email": "a@b.com", "client_id": "c1", "scopes": []}, ttl=-1)
        assert s.get_access("at2") is None

    def test_refresh_round_trip_and_delete(self):
        s = OAuthStore(use_firestore=False)
        s.put_refresh("rt", {"email": "a@b.com", "client_id": "c1", "scopes": ["stratia"]})
        assert s.get_refresh("rt")["email"] == "a@b.com"
        s.delete_refresh("rt")
        assert s.get_refresh("rt") is None
