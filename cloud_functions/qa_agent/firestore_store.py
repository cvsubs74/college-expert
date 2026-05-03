"""
Firestore I/O for the QA agent.

Two collections:
  qa_scenarios/{archetype_id}  — per-archetype history
  qa_runs/{run_id}             — per-run reports

The store is tiny and intentionally untyped (we read/write plain dicts)
so changes to the report shape don't require a migration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _client():
    """Lazy init so unit tests can patch this function."""
    from google.cloud import firestore
    return firestore.Client()


# ---- Scenario history -------------------------------------------------------


def load_history(archetype_ids: List[str], db=None) -> Dict[str, dict]:
    """Return {archetype_id: history_dict} for the given ids. Missing
    docs come back as empty dicts so the selection policy can treat
    them as "never run."""
    db = db or _client()
    out: Dict[str, dict] = {}
    for aid in archetype_ids:
        snap = db.collection("qa_scenarios").document(aid).get()
        out[aid] = snap.to_dict() if snap.exists else {}
    return out


def update_history(archetype_id: str, *, last_result: str, db=None) -> None:
    """Record one run outcome against an archetype. Keeps a rolling
    last_result + last_run_at; failures-last-30d is incremented on
    failure and decayed by the retention job."""
    db = db or _client()
    ref = db.collection("qa_scenarios").document(archetype_id)
    snap = ref.get()
    cur = snap.to_dict() if snap.exists else {}

    now = datetime.now(timezone.utc).isoformat()
    failures = int(cur.get("failures_last_30d", 0))
    runs = int(cur.get("runs_last_30d", 0)) + 1
    if last_result == "fail":
        failures += 1

    ref.set({
        "id": archetype_id,
        "last_run_at": now,
        "last_result": last_result,
        "failures_last_30d": failures,
        "runs_last_30d": runs,
    }, merge=True)


# ---- Run reports ------------------------------------------------------------


def write_report(run_id: str, report: dict, db=None) -> None:
    db = db or _client()
    db.collection("qa_runs").document(run_id).set(report)


def read_report(run_id: str, db=None) -> Optional[dict]:
    db = db or _client()
    snap = db.collection("qa_runs").document(run_id).get()
    return snap.to_dict() if snap.exists else None


def list_recent_runs(limit: int = 30, db=None) -> List[dict]:
    """Most-recent runs first. Used by the admin UI."""
    db = db or _client()
    from google.cloud import firestore
    q = (
        db.collection("qa_runs")
        .order_by("started_at", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    return [doc.to_dict() for doc in q.stream()]
