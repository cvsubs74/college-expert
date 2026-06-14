"""PKCE (RFC 7636) helpers + opaque token generation. Stdlib only."""
import base64
import hashlib
import secrets


def new_token(prefix: str = "") -> str:
    """A URL-safe, high-entropy opaque token, optionally prefixed."""
    return f"{prefix}{secrets.token_urlsafe(32)}"


def s256_challenge(verifier: str) -> str:
    """The S256 code_challenge for a given code_verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """True iff `code_verifier` matches `code_challenge` under S256.

    Constant-time comparison. (We only ever issue S256 challenges.)
    """
    if not code_verifier or not code_challenge:
        return False
    return secrets.compare_digest(s256_challenge(code_verifier), code_challenge)
