"""Outbound service-to-service credentials for counselor_agent (#223).

profile_manager_v2 now verifies callers; counselor_agent authenticates its
own calls with a Google-signed OIDC ID token minted by the runtime service
account (audience = the profile manager's URL). PM recognizes the runtime SA
via TRUSTED_SERVICE_EMAILS and then honors the user_email this service
forwards — counselor_agent itself verified the human at its own entry gate.

Fails open by design: with no metadata server (local dev, unit tests) the
headers are simply omitted; the backend's AUTH_MODE decides what that means.
"""
import logging
import os
import time

logger = logging.getLogger(__name__)

# google-auth is imported lazily so test conftests that stub the `google`
# package can still import counselor modules (headers are monkeypatched or
# simply empty in tests; production always has the real package).

# Tokens live 1h; refresh with 5 minutes of slack.
_TOKEN_TTL_SECONDS = 55 * 60
_cache = {}  # audience -> (token, fetched_at)


def _audience() -> str:
    return (os.getenv('PROFILE_MANAGER_URL') or '').rstrip('/')


def pm_auth_headers() -> dict:
    """{'Authorization': 'Bearer <oidc>'} for profile-manager calls, or {}
    when no runtime credentials are available. Never raises."""
    audience = _audience()
    if not audience:
        return {}
    cached = _cache.get(audience)
    now = time.monotonic()
    if cached and now - cached[1] < _TOKEN_TTL_SECONDS:
        return {'Authorization': f'Bearer {cached[0]}'}
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
        token = google_id_token.fetch_id_token(google_requests.Request(), audience)
        _cache[audience] = (token, now)
        return {'Authorization': f'Bearer {token}'}
    except Exception as e:  # noqa: BLE001 — local dev / tests have no metadata server
        logger.info(f"[SVC_AUTH] no service identity token available: {e}")
        return {}
