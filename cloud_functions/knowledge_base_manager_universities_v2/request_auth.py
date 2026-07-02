"""Caller-identity verification for the Stratia backends (#223).

The backends are public `*.run.app` URLs that historically trusted a raw
caller-supplied `X-User-Email` / `user_email` — an open IDOR. This module
verifies a real credential and makes the VERIFIED identity the thing that
scopes data access:

- **End users** (frontend, QA agent) send a Firebase ID token
  (`Authorization: Bearer <jwt>`, issuer securetoken.google.com/<project>).
  The token's own verified email IS the identity.
- **Trusted services** (Stratia MCP connector, counselor_agent) send a
  Google-signed OIDC ID token minted by their Cloud Run/Functions runtime
  service account, audience-bound to THIS service's URL. The service has
  already verified the human upstream (connector: Google OAuth; counselor:
  this same gate), so its claimed `X-User-Email`/`user_email` is honored.

Rollout is governed by AUTH_MODE (env):
- ``off``      — legacy behavior, claimed identity trusted (emergency valve).
- ``log``      — verify when a credential is present; log anonymous/invalid
                 callers and identity mismatches, but allow (dual-accept
                 migration window — the #223 AC's rollout flag).
- ``enforce``  — no valid credential → 401; a user token whose email doesn't
                 match the claimed identity → 403. The verified identity wins.

Config (env): AUTH_MODE, FIREBASE_PROJECT_ID, TRUSTED_SERVICE_EMAILS (csv),
SELF_AUDIENCES (csv of this service's accepted audience URLs).

Kept self-contained — these Cloud Functions deploy independently and share no
common package, so an identical copy lives in each backend service
(profile_manager_v2, counselor_agent, knowledge_base_manager_universities_v2).
"""
import logging
import os

logger = logging.getLogger(__name__)

_CLOCK_SKEW_SECONDS = 10

# google-auth is imported lazily: several test conftests stub the `google`
# package, and this module must stay importable there (verification is
# monkeypatched in unit tests; production always has the real package).
_transport_cache = None


def _transport():
    """Shared token-verification transport. Cert fetches happen on every
    verification; honor Google's cache headers when cachecontrol is
    available so steady-state verification is local-only."""
    global _transport_cache
    if _transport_cache is None:
        import requests as _requests
        from google.auth.transport import requests as google_requests
        try:
            from cachecontrol import CacheControl
            session = CacheControl(_requests.Session())
        except Exception:  # noqa: BLE001 — caching is an optimization, never a gate
            session = _requests.Session()
        _transport_cache = google_requests.Request(session=session)
    return _transport_cache


# Thin seams over google-auth — unit tests monkeypatch these three.
def _decode_unverified(token):
    from google.auth import jwt as google_jwt
    return google_jwt.decode(token, verify=False)


def _verify_firebase(token, audience):
    from google.oauth2 import id_token as google_id_token
    return google_id_token.verify_firebase_token(
        token, _transport(), audience=audience,
        clock_skew_in_seconds=_CLOCK_SKEW_SECONDS)


def _verify_google_oidc(token):
    from google.oauth2 import id_token as google_id_token
    return google_id_token.verify_oauth2_token(
        token, _transport(), audience=None,
        clock_skew_in_seconds=_CLOCK_SKEW_SECONDS)


def _mode() -> str:
    mode = (os.getenv('AUTH_MODE') or 'log').strip().lower()
    return mode if mode in ('off', 'log', 'enforce') else 'log'


def _trusted_service_emails() -> set:
    raw = os.getenv('TRUSTED_SERVICE_EMAILS') or ''
    return {e.strip().lower() for e in raw.split(',') if e.strip()}


def _self_audiences() -> set:
    raw = os.getenv('SELF_AUDIENCES') or ''
    return {a.strip().rstrip('/') for a in raw.split(',') if a.strip()}


def _bearer_token(req) -> str:
    header = (req.headers.get('Authorization') or '').strip()
    if header.lower().startswith('bearer '):
        return header[7:].strip()
    return ''


def authenticate(req) -> dict:
    """Classify the caller from its Authorization header.

    Returns {'kind': 'user'|'service'|'anonymous'|'invalid',
             'email': str|None, 'error': str|None}.
    Never raises; verification failures come back as kind='invalid'.
    """
    token = _bearer_token(req)
    if not token:
        return {'kind': 'anonymous', 'email': None, 'error': None}

    # Route on the (unverified) issuer, then verify with the right verifier —
    # routing is a hint only; nothing is trusted until verification passes.
    try:
        unverified = _decode_unverified(token)
    except Exception as e:  # noqa: BLE001 — malformed token
        return {'kind': 'invalid', 'email': None, 'error': f'malformed token: {e}'}
    issuer = unverified.get('iss') or ''

    try:
        if 'securetoken.google.com' in issuer:
            project = os.getenv('FIREBASE_PROJECT_ID') or os.getenv('GCP_PROJECT_ID')
            if not project:
                # Fail CLOSED: verifying with audience=None skips the project
                # pin, so any Firebase project's token (shared securetoken
                # keys) would verify — cross-project impersonation (#301 review).
                return {'kind': 'invalid', 'email': None,
                        'error': 'FIREBASE_PROJECT_ID unconfigured — cannot verify audience'}
            claims = _verify_firebase(token, project)
            email = (claims.get('email') or '').lower()
            if not email or not claims.get('email_verified', False):
                return {'kind': 'invalid', 'email': None,
                        'error': 'firebase token lacks a verified email'}
            return {'kind': 'user', 'email': email, 'error': None}

        # Google OIDC (service-to-service): verify signature/expiry first,
        # then bind to OUR audience and the trusted-caller allowlist.
        claims = _verify_google_oidc(token)
        aud = (claims.get('aud') or '').rstrip('/')
        if aud not in _self_audiences():
            return {'kind': 'invalid', 'email': None,
                    'error': f'token audience {aud!r} is not this service'}
        email = (claims.get('email') or '').lower()
        if email not in _trusted_service_emails() or not claims.get('email_verified', False):
            return {'kind': 'invalid', 'email': None,
                    'error': f'caller {email!r} is not a trusted service'}
        return {'kind': 'service', 'email': email, 'error': None}

    except Exception as e:  # noqa: BLE001 — bad signature, expired, wrong iss…
        return {'kind': 'invalid', 'email': None, 'error': str(e)}


def _normalize_claims(claimed_emails) -> set:
    """The set of distinct non-empty user identities a request references."""
    if claimed_emails is None:
        values = []
    elif isinstance(claimed_emails, str):
        values = [claimed_emails]
    else:
        values = list(claimed_emails)
    return {v.strip().lower() for v in values if isinstance(v, str) and v.strip()}


def gate_request(req, claimed_emails=None) -> tuple:
    """Apply the AUTH_MODE policy to one request.

    Args:
        req: the flask request.
        claimed_emails: EVERY user identity the request references — pass all
            candidate values (X-User-Email header, user_email/user_id in args,
            JSON body, and form), not one caller-chosen source. A str is
            accepted for convenience. None for routes that don't act on a
            specific user.

    Returns (allow: bool, identity: dict, rejection: (body, status)|None).
    The caller must return `rejection` when allow is False. When a verified
    USER token is present it is authoritative: the request is rejected in
    enforce mode (403) if ANY referenced identity differs from the token
    email — an attacker can't satisfy the gate with a matching header while
    the handler acts on a victim id in the body (#301 review, high).
    """
    mode = _mode()
    if mode == 'off':
        return True, {'kind': 'off', 'email': None, 'error': None}, None

    identity = authenticate(req)
    claimed = _normalize_claims(claimed_emails)

    if identity['kind'] == 'user':
        mismatched = claimed - {identity['email']}
        if mismatched:
            msg = (f"identity mismatch: token={identity['email']} "
                   f"claimed={sorted(claimed)} path={req.path}")
            if mode == 'enforce':
                logger.warning(f"[AUTH] REJECT {msg}")
                return False, identity, (
                    {'success': False, 'error': 'forbidden: identity mismatch'}, 403)
            logger.warning(f"[AUTH] (log mode) {msg}")
        return True, identity, None

    if identity['kind'] == 'service':
        # Upstream trusted service vouches for the claimed user identity.
        return True, identity, None

    # anonymous or invalid
    detail = identity['error'] or 'no credential'
    if mode == 'enforce':
        logger.warning(f"[AUTH] REJECT {identity['kind']} caller "
                       f"path={req.path} claimed={sorted(claimed)}: {detail}")
        return False, identity, (
            {'success': False, 'error': 'authentication required'}, 401)
    log = logger.warning if identity['kind'] == 'invalid' else logger.info
    log(f"[AUTH] (log mode) {identity['kind']} caller "
        f"path={req.path} claimed={sorted(claimed)}: {detail}")
    return True, identity, None
