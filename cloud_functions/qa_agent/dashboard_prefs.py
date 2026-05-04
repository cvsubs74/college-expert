"""
Admin-configurable dashboard preferences.

Stored at qa_config/dashboard_prefs. Single setting today (`recent_n` —
size of the most-recent-runs window the System Health pill summarizes),
shape extensible.

Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.

Document shape:
    {
      "recent_n": 20,                    # 5..100, default 20
      "updated_at": "<iso>",
      "updated_by": "<email>"
    }

Defaults (no doc): recent_n=20.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


# ---- Constants -------------------------------------------------------------

DEFAULT_RECENT_N = 20
RECENT_N_MIN = 5
RECENT_N_MAX = 100

DEFAULTS = {"recent_n": DEFAULT_RECENT_N}


# ---- Firestore I/O ---------------------------------------------------------


def _client():
    from google.cloud import firestore
    return firestore.Client()


def load_prefs(db=None) -> dict:
    """Read qa_config/dashboard_prefs. Returns DEFAULTS if the doc
    doesn't exist or is missing fields."""
    db = db or _client()
    snap = db.collection("qa_config").document("dashboard_prefs").get()
    stored = snap.to_dict() if snap.exists else None
    if not stored:
        return dict(DEFAULTS)

    merged = dict(DEFAULTS)
    # Only copy known fields. recent_n must be a real int (not bool).
    raw_n = stored.get("recent_n")
    if isinstance(raw_n, int) and not isinstance(raw_n, bool):
        if RECENT_N_MIN <= raw_n <= RECENT_N_MAX:
            merged["recent_n"] = raw_n
    return merged


def save_prefs(new_prefs: dict, *, actor: str = "", db=None) -> None:
    """Write qa_config/dashboard_prefs. Caller is responsible for
    validating the prefs shape before calling (use validate_prefs)."""
    db = db or _client()
    payload = dict(new_prefs)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_by"] = actor
    db.collection("qa_config").document("dashboard_prefs").set(payload, merge=False)


def validate_prefs(new_prefs: dict) -> Optional[str]:
    """Returns an error string if the shape is bad, None if OK.

    Empty payload is OK — load_prefs returns defaults at read time.
    """
    if "recent_n" in new_prefs:
        n = new_prefs["recent_n"]
        # Reject bool because bool is a subclass of int but never what
        # the caller meant.
        if not isinstance(n, int) or isinstance(n, bool):
            return (
                f"recent_n must be an integer in "
                f"[{RECENT_N_MIN}, {RECENT_N_MAX}], got {n!r}"
            )
        if not (RECENT_N_MIN <= n <= RECENT_N_MAX):
            return (
                f"recent_n must be in "
                f"[{RECENT_N_MIN}, {RECENT_N_MAX}], got {n}"
            )
    return None
