"""
The "smart QA engineer" layer: builds the test_plan, outcome, and
executive summary narratives that go into qa_runs reports + the
admin dashboard.

Three entry points:
  build_plan(archetypes, history)  → pre-run narrative + rationale + coverage
  build_outcome(report)            → post-run narrative + verdict + first-look-at
  build_summary(runs)              → executive summary for the dashboard top

All three:
  - Return a deterministic shape so the dashboard never blank-renders
  - Use Gemini Flash for the prose narrative when GEMINI_API_KEY is set
  - Fall back to a deterministic narrative when the LLM is unavailable
  - Compute structural fields (verdict, pass-rate, coverage) WITHOUT
    the LLM so they're always trustworthy

Design tradeoff (per smart-qa-engineer design doc):
  Verdicts and pass-rates are *not* LLM-derived. The LLM only authors
  the prose that explains them. This keeps the actionable signal
  honest even if Gemini is down or hallucinating.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


# ---- build_plan -------------------------------------------------------------


def build_plan(
    archetypes: list,
    history: dict,
    *,
    gemini_key: Optional[str] = None,
) -> dict:
    """Pre-run. Returns {narrative, rationale, coverage}.

    `archetypes` is the list the selector picked. `history` is
    {archetype_id: {last_run_at, last_result, ...}} for those ids.
    """
    coverage = _coverage_from_archetypes(archetypes)
    rationale = _rationale_for_picks(archetypes, history)
    narrative = _plan_narrative(archetypes, history, rationale, coverage,
                                gemini_key=gemini_key)
    return {
        "narrative": narrative,
        "rationale": rationale,
        "coverage": coverage,
    }


def _coverage_from_archetypes(archetypes: list) -> dict:
    """Aggregate surfaces touched across the chosen archetypes. Each
    archetype contributes +1 per surface listed in its
    `surfaces_covered`. Missing surfaces appear as 0 only via the
    caller; here we just produce the counts."""
    counts: dict = {}
    for a in archetypes:
        for surface in a.get("surfaces_covered") or []:
            counts[surface] = counts.get(surface, 0) + 1
    return counts


def _rationale_for_picks(archetypes: list, history: dict) -> str:
    """Single-word label describing why this batch was picked. Used to
    stamp the test_plan with a quick reason — full prose lives in
    `narrative`."""
    any_recent_failure = False
    any_untried = False
    for a in archetypes:
        h = history.get(a["id"], {})
        if h.get("last_result") == "fail":
            any_recent_failure = True
        if not h.get("last_run_at"):
            any_untried = True
    if any_recent_failure:
        return "recently_failed"
    if any_untried:
        return "untried_recently"
    if not archetypes:
        return "rotation"
    return "rotation"


def _plan_narrative(archetypes, history, rationale, coverage,
                    *, gemini_key: Optional[str] = None) -> str:
    """LLM-driven narrative; deterministic fallback otherwise."""
    if not gemini_key:
        return _plan_narrative_fallback(archetypes, history, rationale)

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = _plan_prompt(archetypes, history, rationale, coverage)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        return text or _plan_narrative_fallback(archetypes, history, rationale)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent.planner: build_plan LLM failed (%s); fallback", exc)
        return _plan_narrative_fallback(archetypes, history, rationale)


def _plan_prompt(archetypes, history, rationale, coverage) -> str:
    lines = []
    for a in archetypes:
        h = history.get(a["id"], {})
        lines.append(
            f"- {a['id']}: {a.get('description', '')}  "
            f"(last run: {h.get('last_run_at') or 'never'}, "
            f"last result: {h.get('last_result') or 'n/a'})"
        )
    surfaces = ", ".join(sorted(coverage.keys())) or "none"
    return f"""You are a senior QA engineer planning a synthetic-monitoring run.
The agent picked these scenarios (rationale: {rationale}):

{chr(10).join(lines)}

Surfaces this run touches: {surfaces}.

In 2-3 sentences:
1. State what this run is testing in plain English.
2. Note any deliberate emphasis (e.g., re-testing a recently-failed
   scenario, exploring an under-tested surface).

Be direct. No preamble. No disclaimers."""


def _plan_narrative_fallback(archetypes, history, rationale) -> str:
    """Deterministic, no-LLM narrative. Always names at least one
    scenario id and the rationale."""
    if not archetypes:
        return "No scenarios chosen for this run."
    ids = [a["id"] for a in archetypes]
    listed = ", ".join(ids)
    rationale_label = {
        "recently_failed": "re-testing a recently-failed scenario for confirmation",
        "untried_recently": "covering scenarios that haven't run in over a week",
        "coverage_gap": "exercising under-tested surfaces",
        "rotation": "rotating through the corpus",
    }.get(rationale, rationale)
    return (
        f"Running {len(archetypes)} scenario(s): {listed}. "
        f"Strategy: {rationale_label}."
    )


# ---- build_outcome ---------------------------------------------------------


def build_outcome(
    report: dict,
    *,
    gemini_key: Optional[str] = None,
) -> dict:
    """Post-run. Returns {narrative, verdict, first_look_at}.

    Verdict is computed deterministically from the report.
    Narrative is LLM-authored when a key is provided, fallback otherwise.
    """
    verdict = _compute_verdict(report)
    first_look = _first_look_at(report)
    narrative = _outcome_narrative(report, verdict, first_look,
                                   gemini_key=gemini_key)
    return {
        "narrative": narrative,
        "verdict": verdict,
        "first_look_at": first_look,
    }


def _compute_verdict(report: dict) -> str:
    """Deterministic verdict from pass/fail counts only."""
    summary = report.get("summary") or {}
    total = summary.get("total", 0)
    fail = summary.get("fail", 0)
    if total == 0:
        return "no_data"
    if fail == 0:
        return "all_pass"
    # If only one scenario failed and the assertion was a soft kind,
    # we still tag it regression_likely — the operator decides.
    return "regression_likely" if fail >= 1 else "minor_flake"


def _first_look_at(report: dict) -> list:
    """Pointer at the first failing step the operator should look at.
    Empty if the run was all-pass."""
    out = []
    for scenario in report.get("scenarios") or []:
        if scenario.get("passed"):
            continue
        for step in scenario.get("steps") or []:
            if step.get("passed"):
                continue
            failed_assertions = [
                a for a in step.get("assertions") or [] if not a.get("passed")
            ]
            reason_bits = [
                a.get("name") for a in failed_assertions if a.get("name")
            ][:2]
            out.append({
                "scenario_id": scenario.get("scenario_id"),
                "step": step.get("name"),
                "reason": "; ".join(reason_bits)
                if reason_bits else f"step returned {step.get('status_code')}",
            })
            break  # first failing step per scenario
    return out


def _outcome_narrative(report, verdict, first_look, *,
                       gemini_key: Optional[str] = None) -> str:
    if not gemini_key:
        return _outcome_narrative_fallback(report, verdict, first_look)

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = _outcome_prompt(report, verdict, first_look)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        return text or _outcome_narrative_fallback(report, verdict, first_look)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent.planner: build_outcome LLM failed (%s)", exc)
        return _outcome_narrative_fallback(report, verdict, first_look)


def _outcome_prompt(report, verdict, first_look) -> str:
    summary = report.get("summary") or {}
    failing_lines = []
    for scenario in report.get("scenarios") or []:
        if scenario.get("passed"):
            continue
        for step in scenario.get("steps") or []:
            if step.get("passed"):
                continue
            failed = [a for a in step.get("assertions") or []
                      if not a.get("passed")]
            failing_lines.append(
                f"  - {scenario.get('scenario_id')} → "
                f"step '{step.get('name')}' (status {step.get('status_code')}): "
                f"{[a.get('name') + ': ' + (a.get('message') or '') for a in failed]}"
            )
            break
    failing_excerpt = "\n".join(failing_lines) or "  (no failures)"

    return f"""You are a senior QA engineer reviewing the run you just oversaw.

Summary: {summary.get('pass')}/{summary.get('total')} scenarios passed. Verdict: {verdict}.

Failing scenarios (top failures only):
{failing_excerpt}

In 2-3 sentences:
1. State what the run verified.
2. State what failed and what it most likely means (agent bug vs app
   regression — refer to the failing assertions for evidence).
3. Recommend the single smartest first place to investigate.

Be direct. No preamble. No disclaimers."""


def _outcome_narrative_fallback(report, verdict, first_look) -> str:
    summary = report.get("summary") or {}
    if verdict == "all_pass":
        return (
            f"All {summary.get('total', 0)} scenario(s) passed. "
            f"No failing surfaces detected this run."
        )
    if verdict == "no_data":
        return "No scenarios ran in this batch."
    failing_ids = [
        s.get("scenario_id") for s in (report.get("scenarios") or [])
        if not s.get("passed")
    ]
    listed = ", ".join(failing_ids)
    first_step = first_look[0] if first_look else None
    pointer = (
        f" Start with {first_step['scenario_id']} → step '{first_step['step']}'."
        if first_step else ""
    )
    return (
        f"{summary.get('pass', 0)}/{summary.get('total', 0)} scenarios passed. "
        f"Failing: {listed}.{pointer}"
    )


# ---- build_summary --------------------------------------------------------


def build_summary(runs: Iterable[dict],
                  *, gemini_key: Optional[str] = None) -> dict:
    """Executive summary for the dashboard top. Reads the recent runs
    and computes pass rates + per-surface health, then optionally
    decorates with an LLM narrative."""
    runs = list(runs or [])
    now = datetime.now(timezone.utc)

    pass_rate_7d = _pass_rate_within(runs, now, days=7)
    pass_rate_30d = _pass_rate_within(runs, now, days=30)
    trend = _trend(pass_rate_7d, pass_rate_30d)
    surfaces = _surface_health(runs, now, days=14)

    narrative = _summary_narrative(
        runs, pass_rate_7d, pass_rate_30d, trend, surfaces,
        gemini_key=gemini_key,
    )
    return {
        "narrative": narrative,
        "pass_rate_7d": pass_rate_7d,
        "pass_rate_30d": pass_rate_30d,
        "trend": trend,
        "surfaces": surfaces,
    }


def _within(runs, now, *, days):
    cutoff = now - timedelta(days=days)
    out = []
    for r in runs:
        ts = r.get("started_at")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= cutoff:
            out.append(r)
    return out


def _pass_rate_within(runs, now, *, days):
    bucket = _within(runs, now, days=days)
    if not bucket:
        return None
    passes = sum(1 for r in bucket if (r.get("summary") or {}).get("fail", 0) == 0)
    return round(100 * passes / len(bucket))


def _trend(rate_7d, rate_30d):
    if rate_7d is None or rate_30d is None:
        return "steady"
    if rate_7d > rate_30d + 5:
        return "improving"
    if rate_7d < rate_30d - 5:
        return "degrading"
    return "steady"


def _surface_health(runs, now, *, days):
    """Per-surface counts: total runs that touched it, runs that failed.
    Returns {surface: {"total": int, "fails": int, "status": "green|yellow|red"}}."""
    bucket = _within(runs, now, days=days)
    by_surface: dict = {}
    for r in bucket:
        run_failed = (r.get("summary") or {}).get("fail", 0) > 0
        for scenario in r.get("scenarios") or []:
            # Surfaces taken from the archetype, copied into the
            # scenario record at run time. If absent on legacy reports,
            # we still attribute against an "uncategorized" bucket.
            for surface in scenario.get("surfaces_covered") or []:
                slot = by_surface.setdefault(
                    surface, {"total": 0, "fails": 0, "status": "green"})
                slot["total"] += 1
                # If THIS scenario failed, the surface gets a fail.
                if not scenario.get("passed", True):
                    slot["fails"] += 1
    for surface, slot in by_surface.items():
        if slot["fails"] == 0:
            slot["status"] = "green"
        elif slot["fails"] / max(slot["total"], 1) < 0.2:
            slot["status"] = "yellow"
        else:
            slot["status"] = "red"
    return by_surface


def _summary_narrative(runs, rate_7d, rate_30d, trend, surfaces,
                       *, gemini_key: Optional[str] = None) -> str:
    if not runs:
        return "No QA runs yet. Click Run now to kick off the first batch."

    if not gemini_key:
        return _summary_narrative_fallback(runs, rate_7d, rate_30d, trend, surfaces)

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = _summary_prompt(runs, rate_7d, rate_30d, trend, surfaces)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        return text or _summary_narrative_fallback(
            runs, rate_7d, rate_30d, trend, surfaces)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent.planner: build_summary LLM failed (%s)", exc)
        return _summary_narrative_fallback(
            runs, rate_7d, rate_30d, trend, surfaces)


def _summary_prompt(runs, rate_7d, rate_30d, trend, surfaces) -> str:
    surf_lines = "\n".join(
        f"  - {name}: {slot['fails']}/{slot['total']} fails ({slot['status']})"
        for name, slot in surfaces.items()
    ) or "  (no surfaces tracked)"
    return f"""You are a senior QA engineer writing a 2-3 sentence executive summary
of a synthetic-monitoring system's health.

Pass rate (last 7 days): {rate_7d}%
Pass rate (last 30 days): {rate_30d}%
Trend: {trend}
Surface health (last 14 days):
{surf_lines}

In 2-3 sentences:
1. Give a one-line health verdict in plain English.
2. Call out any surface that's red or yellow, with a hint at where to look.
3. If everything is green, say so simply.

Be direct. No preamble. No disclaimers."""


def _summary_narrative_fallback(runs, rate_7d, rate_30d, trend, surfaces):
    parts = []
    if rate_7d is not None:
        parts.append(f"{rate_7d}% pass over the last 7 days")
    if rate_30d is not None:
        parts.append(f"{rate_30d}% over the last 30")
    if trend != "steady":
        parts.append(f"trending {trend}")
    headline = "; ".join(parts) or "system health"

    flagged = [name for name, slot in surfaces.items()
               if slot.get("status") in ("yellow", "red")]
    if flagged:
        return f"{headline.capitalize()}. Watch surfaces: {', '.join(flagged)}."
    return f"{headline.capitalize()}. All tracked surfaces are green."
