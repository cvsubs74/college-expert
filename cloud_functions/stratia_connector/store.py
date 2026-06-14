"""OAuth state persistence for the connector.

Cloud Run runs multiple instances, and the /authorize, Google-callback, and
/token steps of one sign-in can land on different instances — so OAuth state
(registered clients, in-flight login states, auth codes, access/refresh tokens)
must be shared. This module provides a small key/value store over Firestore
with an in-memory fallback for local dev and tests.

Records are plain dicts; expiry is an epoch float checked on read.
"""
import time
from typing import Optional

# Logical record kinds → Firestore collection names.
_COLLECTIONS = {
    "client": "oauth_clients",
    "state": "oauth_states",
    "code": "oauth_codes",
    "access": "oauth_access_tokens",
    "refresh": "oauth_refresh_tokens",
    "rate": "oauth_rate_limits",
}


class _MemoryBackend:
    def __init__(self):
        self._d = {kind: {} for kind in _COLLECTIONS}

    def put(self, kind, key, value):
        self._d[kind][key] = dict(value)

    def get(self, kind, key):
        v = self._d[kind].get(key)
        return dict(v) if v is not None else None

    def delete(self, kind, key):
        self._d[kind].pop(key, None)


class _FirestoreBackend:
    def __init__(self, project):
        from google.cloud import firestore  # lazy: not needed for tests/local-mem
        self._db = firestore.Client(project=project)

    def _ref(self, kind, key):
        return self._db.collection(_COLLECTIONS[kind]).document(key)

    def put(self, kind, key, value):
        self._ref(kind, key).set(dict(value))

    def get(self, kind, key):
        snap = self._ref(kind, key).get()
        return snap.to_dict() if snap.exists else None

    def delete(self, kind, key):
        self._ref(kind, key).delete()


class OAuthStore:
    def __init__(self, use_firestore=False, project=None):
        self._b = _FirestoreBackend(project) if use_firestore else _MemoryBackend()

    # -- clients (Dynamic Client Registration) ------------------------------
    def put_client(self, client_id: str, info: dict, ttl: int):
        self._b.put("client", client_id, {**info, "_exp": time.time() + ttl})

    def get_client(self, client_id: str) -> Optional[dict]:
        rec = self._b.get("client", client_id)
        if rec is None:
            return None
        if rec.get("_exp", 0) < time.time():
            self._b.delete("client", client_id)
            return None
        rec.pop("_exp", None)  # not part of the OAuthClientInformationFull schema
        return rec

    # -- in-flight login state (our state → context for the Google round-trip)
    def put_state(self, state: str, ctx: dict, ttl: int):
        self._b.put("state", state, {**ctx, "_exp": time.time() + ttl})

    def pop_state(self, state: str) -> Optional[dict]:
        return self._pop_if_fresh("state", state)

    # -- authorization codes ------------------------------------------------
    # The SDK token handler loads a code (to validate + check PKCE) and only
    # then exchanges it, so `get_code` is non-destructive; `delete_code` is
    # called once the exchange succeeds.
    def put_code(self, code: str, ctx: dict, ttl: int):
        self._b.put("code", code, {**ctx, "_exp": time.time() + ttl})

    def get_code(self, code: str) -> Optional[dict]:
        rec = self._b.get("code", code)
        if rec is None:
            return None
        if rec.get("_exp", 0) < time.time():
            self._b.delete("code", code)
            return None
        return rec

    def delete_code(self, code: str):
        self._b.delete("code", code)

    # -- access tokens ------------------------------------------------------
    def put_access(self, token: str, ctx: dict, ttl: int):
        self._b.put("access", token, {**ctx, "_exp": time.time() + ttl})

    def get_access(self, token: str) -> Optional[dict]:
        rec = self._b.get("access", token)
        if rec is None:
            return None
        if rec.get("_exp", 0) < time.time():
            self._b.delete("access", token)
            return None
        return rec

    def delete_access(self, token: str):
        self._b.delete("access", token)

    # -- refresh tokens (long-lived; rotated on use; TTL'd) -----------------
    def put_refresh(self, token: str, ctx: dict, ttl: int):
        self._b.put("refresh", token, {**ctx, "_exp": time.time() + ttl})

    def get_refresh(self, token: str) -> Optional[dict]:
        rec = self._b.get("refresh", token)
        if rec is None:
            return None
        if rec.get("_exp", 0) < time.time():
            self._b.delete("refresh", token)
            return None
        return rec

    def delete_refresh(self, token: str):
        self._b.delete("refresh", token)

    # -- rate limiting (fixed window; soft, read-modify-write) --------------
    def rate_allow(self, key: str, limit: int, window: int, now: float = None) -> bool:
        """True if `key` is under `limit` for the current `window`-second bucket,
        else False. Increments the bucket count. Soft across instances (no
        transaction) — adequate for abuse/credit-spend throttling."""
        now = now if now is not None else time.time()
        bucket = int(now // window)
        bkey = f"{key}:{bucket}"
        rec = self._b.get("rate", bkey)
        count = (rec or {}).get("count", 0)
        if count >= limit:
            return False
        self._b.put("rate", bkey, {"count": count + 1, "_exp": now + window})
        return True

    # -- helpers ------------------------------------------------------------
    def _pop_if_fresh(self, kind, key):
        rec = self._b.get(kind, key)
        if rec is None:
            return None
        self._b.delete(kind, key)  # one-time use
        if rec.get("_exp", 0) < time.time():
            return None
        return rec
