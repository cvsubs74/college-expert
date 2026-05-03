"""
Ground truth fetcher.

Before each scenario runs, the runner asks ground_truth.fetch_ground_truth()
for the canonical record of every college the scenario will add. The
returned bag is the source-of-truth that cross-reference assertions
later compare runtime API responses against.

A KB miss for a given college returns an empty record (NOT raises).
That way one missing university doesn't blow up the whole scenario;
assertions that depend on the missing record will mark themselves
SKIP rather than fail.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ---- Public entry ----------------------------------------------------------


def fetch_ground_truth(
    college_ids: List[str],
    *,
    kb_client: Optional[Callable[[str], Optional[dict]]] = None,
    kb_url: Optional[str] = None,
    timeout: int = 10,
) -> Dict[str, dict]:
    """Returns {college_id: record}. Records are normalized so downstream
    assertions don't have to walk variant KB shapes.

    `kb_client` (testable): a function that takes a college_id and
    returns the raw KB record (or None for a miss). When omitted, an
    HTTP-based default is built from `kb_url`.
    """
    if kb_client is None:
        kb_url = kb_url or os.getenv("KNOWLEDGE_BASE_UNIVERSITIES_URL", "")
        if not kb_url:
            logger.warning("ground_truth: no kb_url; truth bag will be empty")
            kb_client = lambda _id: None  # noqa: E731
        else:
            kb_client = _http_kb_client(kb_url, timeout=timeout)

    bag: Dict[str, dict] = {}
    for cid in college_ids:
        try:
            raw = kb_client(cid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ground_truth: kb client raised for %s: %s", cid, exc)
            raw = None
        bag[cid] = _normalize(raw) if raw else {}
    return bag


# ---- HTTP default ---------------------------------------------------------


def _http_kb_client(kb_url: str, *, timeout: int):
    """Build a kb_client that hits the live KB function. The endpoint
    shape is /university/<id> returning the canonical record."""
    base = kb_url.rstrip("/")

    def _fetch(college_id: str) -> Optional[dict]:
        # Try /university/<id> first; fall back to /search?q=<id>.
        for path in (f"{base}/university/{college_id}",
                     f"{base}/get-university?id={college_id}"):
            try:
                resp = requests.get(path, timeout=timeout)
                if resp.status_code == 200:
                    body = resp.json()
                    if isinstance(body, dict):
                        return body
            except requests.RequestException:
                continue
        return None

    return _fetch


# ---- Normalization --------------------------------------------------------


def _normalize(raw: dict) -> dict:
    """Pull the fields the cross-reference assertions need out of the KB
    record's variant shapes. Add computed fields:

      - essays_required: count of supplemental_essays where required=True
      - essays_total: total count (required + optional)
    """
    out = {
        "id": raw.get("id") or raw.get("university_id"),
        "name": raw.get("name") or raw.get("university_name"),
    }
    if "application_deadline" in raw:
        out["application_deadline"] = raw["application_deadline"]
    elif "deadline" in raw:
        out["application_deadline"] = raw["deadline"]
    if "deadline_type" in raw:
        out["deadline_type"] = raw["deadline_type"]
    if "mascot" in raw:
        out["mascot"] = raw["mascot"]
    if "location" in raw:
        out["location"] = raw["location"]
    if "financial_aid" in raw:
        out["financial_aid"] = raw["financial_aid"]

    essays = raw.get("supplemental_essays") or raw.get("essays") or []
    if isinstance(essays, list):
        out["essays_total"] = len(essays)
        required = [e for e in essays if isinstance(e, dict) and e.get("required")]
        out["essays_required"] = len(required)
    return out
