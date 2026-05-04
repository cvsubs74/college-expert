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
from typing import List, Optional

# Cap the per-journey scenario list so the dashboard doesn't render
# 50 items for a heavily-tested journey.
MAX_SCENARIOS_PER_JOURNEY = 10

# Cap the rendered validated_features list. total_features still
# reflects the full count.
MAX_VALIDATED_FEATURES = 20

# Cap the rendered universities_untested list — avoid dumping 100+ ids
# when the allowlist grows. allowlist_size still reflects the real
# count.
MAX_UNTESTED_UNIVERSITIES = 25


# Known short-form aliases for universities → canonical (allowlist) id.
# The synthesizer + static scenarios historically produced both forms,
# which double-counted the same school in the universities-tested list.
# Folding at coverage-build time means the dashboard renders one row per
# school even with mixed-form historical data still in Firestore.
_CANONICAL_ALIASES = {
    "mit": "massachusetts_institute_of_technology",
    "ucla": "university_of_california_los_angeles",
}


def _canonicalize(uni: str) -> str:
    """Return the canonical id for a university alias, or the input
    unchanged if no alias is registered. Opt-in by entry — unknown ids
    pass through so the data stays interpretable even when the alias
    map lags behind a new school in the allowlist."""
    return _CANONICAL_ALIASES.get(uni, uni)


# ---- Public ----------------------------------------------------------------


def build_coverage(runs: List[dict], *,
                   colleges_allowlist: Optional[List[str]] = None) -> dict:
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
    # text → count (whitespace-normalized)
    feature_counts: dict = {}
    # university id → {count, last_tested_at}
    universities: dict = {}

    for run in runs or []:
        run_started_at = run.get("started_at", "")
        for scen in run.get("scenarios") or []:
            if not _is_passed(scen):
                continue

            # Aggregate the scenario's `tests` bullets into the
            # validated-features list — the answer to "what specific
            # behaviors has the QA agent confirmed work today?"
            for bullet in scen.get("tests") or []:
                if not isinstance(bullet, str):
                    continue
                key = " ".join(bullet.split())  # collapse whitespace
                if not key:
                    continue
                feature_counts[key] = feature_counts.get(key, 0) + 1

            # Aggregate the scenario's colleges_template into the
            # universities-tested map — answers "which schools has the
            # QA agent exercised?". Each appearance counts (one per
            # passing scenario-instance), and we track the latest
            # timestamp so the dashboard can render "last tested 5m ago".
            for uni in scen.get("colleges_template") or []:
                if not isinstance(uni, str) or not uni:
                    continue
                uni = _canonicalize(uni)
                slot = universities.setdefault(uni, {
                    "id": uni, "count": 0, "last_tested_at": "",
                })
                slot["count"] += 1
                stamp = run_started_at or scen.get("started_at") or ""
                if stamp > slot["last_tested_at"]:
                    slot["last_tested_at"] = stamp

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

    # Validated features: every distinct test bullet across passing
    # scenarios, with how many times it's been verified. Sorted by
    # count desc, capped at MAX_VALIDATED_FEATURES for the UI; the
    # full count remains in `total_features`.
    validated_features = sorted(
        ({"text": text, "count": count} for text, count in feature_counts.items()),
        key=lambda f: (-f["count"], f["text"]),
    )

    # Universities tested — sorted by count desc, then alpha for stable
    # rendering when counts tie. Untested = allowlist - tested set;
    # capped to keep the response compact.
    universities_tested = sorted(
        universities.values(),
        key=lambda u: (-u["count"], u["id"]),
    )
    tested_ids = {u["id"] for u in universities_tested}
    allowlist = list(colleges_allowlist or [])
    untested = sorted(uid for uid in allowlist if uid not in tested_ids)

    return {
        "journeys": journeys,
        "total_journeys": len(journeys),
        "validated_features": validated_features[:MAX_VALIDATED_FEATURES],
        "total_features": len(validated_features),
        "universities_tested": universities_tested,
        "total_universities_tested": len(universities_tested),
        "universities_untested": untested[:MAX_UNTESTED_UNIVERSITIES],
        "allowlist_size": len(allowlist),
    }


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
