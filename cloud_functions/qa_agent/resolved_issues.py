"""
Resolved-issues builder — "what bugs did the QA agent catch and when
were they fixed?"

Walks runs in chronological order; for each (scenario_id, step_name)
pair, tracks the most recent failure. When the next run shows that
pair PASSING, emits one entry capturing the fix.

Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.

Public surface:
  build_resolved_issues(runs: List[dict]) -> dict

Output shape:
  {
    "fixes": [
      {
        "scenario_id": "synth_high_achiever_junior_all_ucs",
        "step_name": "roadmap_generate",
        "failing_message": "metadata.template_used=='junior_fall': got 'sophomore_spring'",
        "failed_at_run": "run_20260504T010246Z_bdba3a",
        "fixed_at_run": "run_20260504T011634Z_46140b",
        "fixed_at_time": "2026-05-04T01:16:34Z",
      },
      ...
    ],
    "total_fixes": 4,
    "lookback_runs": 30,
  }

Most-recently-fixed bugs are listed first; the list is capped at
MAX_FIXES so the dashboard stays tight.
"""

from __future__ import annotations

from typing import List

# Cap the displayed fixes so a long backlog doesn't bloat the response.
MAX_FIXES = 10


# ---- Public ----------------------------------------------------------------


def build_resolved_issues(runs: List[dict]) -> dict:
    """Detect FAIL → PASS transitions across the supplied runs.

    Input runs are most-recent-first (firestore_store.list_recent_runs
    returns them that way). Internally we walk oldest → newest so we
    can spot when a previously-failing (scenario, step) pair starts
    passing.
    """
    runs = list(runs or [])
    # Process oldest-first.
    chronological = sorted(
        (r for r in runs if r.get("started_at")),
        key=lambda r: r["started_at"],
    )

    # State: (scenario_id, step_name) → {failing_message, failed_at_run}
    # for the most recent observed failure of that pair. Cleared when
    # we observe the pair passing.
    pending_failures: dict = {}
    fixes: List[dict] = []

    for run in chronological:
        run_id = run.get("run_id", "<unknown>")
        run_started = run.get("started_at", "")
        for scen in run.get("scenarios") or []:
            scen_id = scen.get("scenario_id") or "<unknown>"
            failing_steps = _failing_steps(scen)

            # Scenario-level pass: any pending failures for this scenario
            # that aren't repeated here are fixed.
            scen_passed = _is_passed(scen) and not failing_steps

            # Walk every step we've seen failing in the past for this scenario.
            # If it's not in failing_steps now, it's fixed.
            for (sid, step_name), pending in list(pending_failures.items()):
                if sid != scen_id:
                    continue
                if step_name in failing_steps:
                    # Same step still failing; refresh the pending record.
                    pending["failing_message"] = failing_steps[step_name]
                    pending["failed_at_run"] = run_id
                else:
                    # Step is no longer in this scenario's failing set —
                    # whether the scenario as a whole passed or it just
                    # failed on a *different* step, this specific bug is
                    # resolved (per the design's per-(scenario, step)
                    # tracking rule).
                    fixes.append({
                        "scenario_id": sid,
                        "step_name": step_name,
                        "failing_message": pending["failing_message"],
                        "failed_at_run": pending["failed_at_run"],
                        "fixed_at_run": run_id,
                        "fixed_at_time": run_started,
                    })
                    del pending_failures[(sid, step_name)]

            # Add any new failing steps to the pending map.
            for step_name, msg in failing_steps.items():
                pending_failures[(scen_id, step_name)] = {
                    "failing_message": msg,
                    "failed_at_run": run_id,
                }

    # Most-recently-fixed first.
    fixes.sort(key=lambda f: f["fixed_at_time"], reverse=True)

    # The dashboard caps the displayed list, but total_fixes reflects ALL
    # detected fixes in the window so the operator sees the real count.
    total = len(fixes)
    return {
        "fixes": fixes[:MAX_FIXES],
        "total_fixes": total,
        "lookback_runs": len(runs),
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


def _failing_steps(scenario: dict) -> dict:
    """Extract {step_name: first_failing_assertion_message} for a scenario.

    Returns empty dict for passing scenarios. The first failing
    assertion message is enough for the dashboard's "what was broken"
    evidence; we don't dump the whole step body.
    """
    out = {}
    for step in scenario.get("steps") or []:
        if _is_passed(step):
            continue
        name = step.get("name") or "<step>"
        msg = ""
        for a in step.get("assertions") or []:
            if not _is_passed(a):
                msg = a.get("message") or ""
                break
        out[name] = msg
    return out
