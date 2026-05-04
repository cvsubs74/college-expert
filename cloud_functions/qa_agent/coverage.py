"""
Coverage builder — "what end-to-end journeys is the QA agent actually
validating today?"

Walks recent runs, collects PASSING scenarios, and groups by their
`surfaces_covered` tuple to produce one row per distinct journey.

Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.

Public surface:
  build_coverage(runs: List[dict]) -> dict

Output shape:
  {
    "journeys": [
      {
        "id": "<stable hash of surfaces tuple>",
        "surfaces": ["<sorted surface names>"],
        "summary": "<plain-English description>",
        "scenarios": [{"id": ..., "verified_at": ...}, ...],  # capped
        "verified_count": <int — every passing instance, including dupes>,
      },
      ...
    ],
    "total_journeys": <int>,
  }

Sort order: most-validated journeys first.
"""

from __future__ import annotations

import hashlib
from typing import List

# Cap the per-journey scenario list so the dashboard doesn't render
# 50 items for a heavily-tested journey.
MAX_SCENARIOS_PER_JOURNEY = 10


# ---- Public ----------------------------------------------------------------


def build_coverage(runs: List[dict]) -> dict:
    """Aggregate passing scenarios into validated journeys.

    A "journey" = the set of `surfaces_covered` a scenario touches.
    Multiple scenarios can share the same journey, and a single scenario
    can appear in many runs over time. We:
      - keep one entry per (sorted) surfaces tuple
      - count every PASSING run-instance (verified_count)
      - keep the most recent verified_at per scenario_id
      - cap the per-journey scenarios list to keep the UI tight
    """
    # journey_id → {surfaces, scenarios_by_id, verified_count}
    by_journey: dict = {}

    for run in runs or []:
        run_started_at = run.get("started_at", "")
        for scen in run.get("scenarios") or []:
            if not _is_passed(scen):
                continue
            surfaces = scen.get("surfaces_covered") or []
            if not surfaces:
                continue  # legacy / no signal — skip rather than bucket as ""

            sorted_surfaces = sorted(set(surfaces))
            jid = _journey_id(sorted_surfaces)

            slot = by_journey.setdefault(jid, {
                "id": jid,
                "surfaces": sorted_surfaces,
                "scenarios_by_id": {},
                "verified_count": 0,
            })
            slot["verified_count"] += 1

            scen_id = scen.get("scenario_id") or "<unknown>"
            # Prefer the RUN's started_at — scenarios usually inherit it
            # from the run rather than carrying their own. Fall back to
            # any scenario-level timestamp for legacy/edge data.
            verified_at = run_started_at or scen.get("started_at") or ""
            existing = slot["scenarios_by_id"].get(scen_id)
            if not existing or verified_at > existing["verified_at"]:
                slot["scenarios_by_id"][scen_id] = {
                    "id": scen_id,
                    "verified_at": verified_at,
                }

    # Build journeys list, capping per-journey scenarios.
    journeys = []
    for slot in by_journey.values():
        scens = sorted(
            slot["scenarios_by_id"].values(),
            key=lambda s: s["verified_at"],
            reverse=True,
        )[:MAX_SCENARIOS_PER_JOURNEY]
        journeys.append({
            "id": slot["id"],
            "surfaces": slot["surfaces"],
            "summary": _summarize_journey(slot["surfaces"]),
            "scenarios": scens,
            "verified_count": slot["verified_count"],
        })

    journeys.sort(key=lambda j: j["verified_count"], reverse=True)
    return {"journeys": journeys, "total_journeys": len(journeys)}


# ---- Helpers ---------------------------------------------------------------


def _is_passed(d: dict) -> bool:
    """Tolerate Firestore round-trips that turn booleans into strings."""
    v = d.get("passed")
    if v is True:
        return True
    if isinstance(v, str) and v.lower() == "true":
        return True
    return False


def _journey_id(sorted_surfaces: List[str]) -> str:
    """Deterministic 12-char id from the sorted surfaces tuple."""
    key = "|".join(sorted_surfaces)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


# Friendly labels for known surfaces. Anything unrecognised falls back
# to its raw key.
_SURFACE_LABELS = {
    "profile": "profile build",
    "college_list": "college list",
    "roadmap": "roadmap",
    "fit": "fit analysis",
    "essay": "essay tracker",
    "essays": "essay tracker",
    "scholarships": "scholarships",
    "deadlines": "deadlines",
}


def _summarize_journey(surfaces: List[str]) -> str:
    """One-line description of the journey, for the dashboard card."""
    if not surfaces:
        return "Empty journey"
    parts = [_SURFACE_LABELS.get(s, s) for s in surfaces]
    if len(parts) == 1:
        return f"{parts[0].capitalize()} only"
    return " → ".join(parts).capitalize()
