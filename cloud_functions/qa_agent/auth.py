"""
Auth: mint a Firebase ID token for the test user so the QA agent can call
production endpoints with the same auth path a real user would.

Flow:
  1. Use Firebase Admin SDK (running under the qa_agent service account
     with appropriate IAM) to mint a *custom token* for the test UID.
  2. Exchange that custom token for an *ID token* via the Firebase Auth
     REST endpoint (signInWithCustomToken).
  3. Cache the ID token for its lifetime (1 hour); refresh when expired.

The production cloud functions verify ID tokens with their own Firebase
auth gate. This module gives us the same kind of token a real signed-in
browser would carry.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class IdTokenBundle:
    id_token: str
    refresh_token: str
    expires_at: float  # unix timestamp


# Module-level cache. Cloud Functions may reuse the same instance across
# invocations; reusing the token saves the custom-token mint + REST round
# trip on warm starts.
_cached: Optional[IdTokenBundle] = None


def _now() -> float:
    return time.time()


def _firebase_admin():
    """Initialize firebase_admin lazily.

    Lazy import keeps unit tests fast — they patch this function rather
    than load the real google-auth library.
    """
    import firebase_admin
    from firebase_admin import auth, credentials

    if not firebase_admin._apps:
        # When deployed, the runtime auto-discovers credentials from the
        # service account attached to the Cloud Function. Locally / in
        # tests, GOOGLE_APPLICATION_CREDENTIALS points at a JSON key.
        firebase_admin.initialize_app()

    return auth


def mint_custom_token(uid: str) -> str:
    """Mint a Firebase custom token for `uid`. Service account needs
    iam.serviceAccountTokenCreator on itself."""
    auth = _firebase_admin()
    token_bytes = auth.create_custom_token(uid)
    return token_bytes.decode("utf-8")


def exchange_for_id_token(custom_token: str, api_key: str) -> IdTokenBundle:
    """Exchange a custom token for an ID token via the Firebase Auth REST
    API. Returns the ID token + refresh token + expiry."""
    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"
        f"?key={api_key}"
    )
    resp = requests.post(
        url,
        json={"token": custom_token, "returnSecureToken": True},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    expires_in = int(body.get("expiresIn", 3600))
    return IdTokenBundle(
        id_token=body["idToken"],
        refresh_token=body.get("refreshToken", ""),
        # Subtract 60s buffer so we refresh before the real expiry.
        expires_at=_now() + expires_in - 60,
    )


def get_id_token(uid: str, api_key: Optional[str] = None) -> str:
    """Public entry: return a fresh ID token for `uid`, cached if valid.

    `api_key` defaults to env var FIREBASE_WEB_API_KEY. Required because
    the custom-token-exchange REST API is identified by the project's
    web API key (not the service account's credentials)."""
    global _cached
    api_key = api_key or os.getenv("FIREBASE_WEB_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FIREBASE_WEB_API_KEY env var is required for QA agent auth"
        )

    if _cached and _cached.expires_at > _now():
        return _cached.id_token

    custom = mint_custom_token(uid)
    bundle = exchange_for_id_token(custom, api_key)
    _cached = bundle
    logger.info("qa_agent: minted fresh ID token for uid=%s, ttl=%ds",
                uid, int(bundle.expires_at - _now()))
    return bundle.id_token


def reset_cache() -> None:
    """Test helper. Clears the module cache so a fresh token is requested
    on the next call."""
    global _cached
    _cached = None
