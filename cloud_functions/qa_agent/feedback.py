"""
Admin feedback loop — notes the operator types on the dashboard that
steer the next scheduled run's synthesizer.

Spec: docs/prd/qa-feedback-loop.md, docs/design/qa-feedback-loop.md.

Stored at qa_config/feedback as a single doc with an array of items.
≤10 active items at a time (prompt-size guard); items auto-dismiss
after `max_applies` runs reference them.

Public surface:
  load(db=None) -> dict
  add_item(text, *, actor, max_applies=5, db=None) -> dict
  dismiss(item_id, db=None) -> bool
  active_items(db=None) -> list[dict]
  mark_applied(item_ids, *, run_id, db=None) -> None
  validate_text(text) -> Optional[str]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional


# ---- Constants -------------------------------------------------------------

MAX_ACTIVE_ITEMS = 10
MIN_TEXT_LEN = 5
MAX_TEXT_LEN = 500
DEFAULT_MAX_APPLIES = 5
MAX_APPLIES_BOUND = 20

DOC_PATH = ("qa_config", "feedback")


# ---- Firestore I/O ---------------------------------------------------------


def _client():
    from google.cloud import firestore  # noqa: WPS433 — lazy for tests
    return firestore.Client()


def _doc_ref(db):
    return db.collection(DOC_PATH[0]).document(DOC_PATH[1])


def load(db=None) -> dict:
    """Read qa_config/feedback. Returns {items: []} if the doc doesn't
    exist yet."""
    db = db or _client()
    snap = _doc_ref(db).get()
    if not snap.exists:
        return {"items": []}
    data = snap.to_dict() or {}
    if "items" not in data or not isinstance(data.get("items"), list):
        data["items"] = []
    return data


def _save(payload: dict, *, actor: str = "", db=None) -> None:
    db = db or _client()
    payload = dict(payload)
    payload["updated_at"] = _now_iso()
    if actor:
        payload["updated_by"] = actor
    _doc_ref(db).set(payload, merge=False)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- Validation -----------------------------------------------------------


def validate_text(text) -> Optional[str]:
    """Returns an error message if `text` is unusable, None if OK."""
    if not isinstance(text, str):
        return f"text must be a string, got {type(text).__name__}"
    stripped = text.strip()
    if len(stripped) < MIN_TEXT_LEN:
        return f"text must be at least {MIN_TEXT_LEN} characters"
    if len(stripped) > MAX_TEXT_LEN:
        return f"text must be at most {MAX_TEXT_LEN} characters"
    return None


# ---- Mutations ------------------------------------------------------------


def add_item(text: str, *, actor: str = "",
             max_applies: int = DEFAULT_MAX_APPLIES,
             db=None) -> dict:
    """Add a new active feedback item. Raises ValueError if `text` is
    invalid or there are already MAX_ACTIVE_ITEMS active items."""
    err = validate_text(text)
    if err:
        raise ValueError(err)
    max_applies = max(1, min(MAX_APPLIES_BOUND, int(max_applies)))

    db = db or _client()
    payload = load(db=db)

    active_count = sum(
        1 for it in payload["items"]
        if it.get("status") == "active"
    )
    if active_count >= MAX_ACTIVE_ITEMS:
        raise ValueError(
            f"already have {MAX_ACTIVE_ITEMS} active feedback items "
            f"— dismiss one before adding another"
        )

    item = {
        "id": f"fb_{uuid.uuid4().hex[:8]}",
        "text": text.strip(),
        "status": "active",
        "created_at": _now_iso(),
        "created_by": actor,
        "applied_count": 0,
        "max_applies": max_applies,
        "last_applied_run_id": None,
        "last_applied_at": None,
    }
    payload["items"].append(item)
    _save(payload, actor=actor, db=db)
    return item


def dismiss(item_id: str, db=None) -> bool:
    """Mark an item dismissed. Returns True if found + updated, False
    if no item with that id."""
    db = db or _client()
    payload = load(db=db)
    found = False
    for it in payload["items"]:
        if it.get("id") == item_id:
            it["status"] = "dismissed"
            found = True
            break
    if found:
        _save(payload, db=db)
    return found


def mark_applied(item_ids: List[str], *, run_id: str, db=None) -> None:
    """Increment applied_count for each id, set last_applied_run_id +
    last_applied_at, auto-dismiss any item that hits max_applies.
    Unknown ids are silently ignored."""
    if not item_ids:
        return
    db = db or _client()
    payload = load(db=db)
    id_set = set(item_ids)
    now = _now_iso()
    changed = False
    for it in payload["items"]:
        if it.get("id") in id_set:
            it["applied_count"] = int(it.get("applied_count", 0)) + 1
            it["last_applied_run_id"] = run_id
            it["last_applied_at"] = now
            if it["applied_count"] >= int(it.get("max_applies", DEFAULT_MAX_APPLIES)):
                it["status"] = "dismissed"
            changed = True
    if changed:
        _save(payload, db=db)


# ---- Reads ---------------------------------------------------------------


def active_items(db=None) -> List[dict]:
    """Active items only, capped at MAX_ACTIVE_ITEMS. Most-recent first
    so the synthesizer sees the freshest feedback at the top of its
    prompt."""
    payload = load(db=db)
    active = [it for it in payload["items"] if it.get("status") == "active"]
    # Newest first by created_at (string ISO sort works because UTC).
    active.sort(key=lambda it: it.get("created_at", ""), reverse=True)
    return active[:MAX_ACTIVE_ITEMS]


# Default cap for the Steer panel's "Retired" section. Operators only
# care about recent retirements; older history is in Firestore.
DEFAULT_RECENTLY_DISMISSED_LIMIT = 10


def recently_dismissed_items(limit: int = DEFAULT_RECENTLY_DISMISSED_LIMIT,
                             db=None) -> List[dict]:
    """Return up to `limit` most-recently-dismissed items, sorted by
    last_applied_at desc with created_at as fallback.

    Operators rely on this to confirm "the feedback I left actually
    drove runs and retired" — without it, an item that hits
    max_applies just disappears from the Steer panel and the loop
    looks broken from the outside.

    Sort order: prefer last_applied_at (when the auto-dismiss fired);
    fall back to created_at for items dismissed manually before any
    run referenced them.
    """
    payload = load(db=db)
    dismissed = [
        it for it in payload["items"]
        if it.get("status") == "dismissed"
    ]
    # ISO-8601 strings sort lexicographically, which matches
    # chronological order for UTC.
    def _sort_key(it):
        return it.get("last_applied_at") or it.get("created_at", "")
    dismissed.sort(key=_sort_key, reverse=True)
    return dismissed[: max(0, int(limit))]
