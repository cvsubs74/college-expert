"""
LLM scenario synthesizer.

Given system_knowledge (a curated markdown doc) + recent run history,
asks Gemini Flash to produce N fresh test scenarios that target gaps
and risks the agent observes in the evidence. Validates each scenario
against schema + value bounds + colleges allowlist + the resolver
contract; rejects (NOT crashes on) malformed output.

Returns a list of validated synthesized archetypes — exactly the same
shape as static archetypes from `corpus.load_archetypes()`, with two
extra fields:

  synthesized: True            (marker the dashboard renders as a badge)
  synthesis_rationale: "…"     (LLM-authored explanation: WHY this scenario)

If the LLM is unavailable, output is malformed, or every candidate fails
validation, returns an empty list — caller falls back to static.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


VALID_GRADE_LEVELS = {"9th Grade", "10th Grade", "11th Grade", "12th Grade"}

# Set of templates the resolver will actually pick. Mirrors what
# counselor_agent/planner.py emits. If the LLM proposes a template
# outside this set, the synthesizer rejects the scenario (template
# hallucination guard).
DEFAULT_VALID_TEMPLATES = {
    "freshman_fall", "freshman_spring",
    "sophomore_fall", "sophomore_spring",
    "junior_fall", "junior_spring", "junior_summer",
    "senior_fall", "senior_spring",
}


# ---- Validation -----------------------------------------------------------


def validate_archetype(
    archetype: dict,
    colleges_allowlist: List[str],
    *,
    valid_templates: Optional[Set[str]] = None,
    max_colleges: int = 8,
) -> Tuple[bool, str]:
    """Returns (ok, error_message). On success, error_message is "".

    Hard checks:
      - synthesis_rationale present and non-empty
      - profile.grade_level in VALID_GRADE_LEVELS
      - profile.gpa numeric in [0.0, 4.0]
      - colleges_template entries all in colleges_allowlist
      - colleges_template length within max_colleges
      - expected_template_used (if present) in valid_templates
      - tests is a list of strings
    """
    valid_templates = valid_templates or DEFAULT_VALID_TEMPLATES

    if not isinstance(archetype, dict):
        return False, "archetype is not a dict"

    rationale = archetype.get("synthesis_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        return False, "missing or empty synthesis_rationale"

    profile = archetype.get("profile_template") or {}
    if not isinstance(profile, dict):
        return False, "profile_template is not a dict"
    grade = profile.get("grade_level")
    if grade not in VALID_GRADE_LEVELS:
        return False, f"invalid grade_level {grade!r}"
    gpa = profile.get("gpa")
    try:
        gpa_f = float(gpa)
    except (TypeError, ValueError):
        return False, f"gpa not numeric: {gpa!r}"
    if not (0.0 <= gpa_f <= 4.0):
        return False, f"gpa out of range [0.0, 4.0]: {gpa_f}"

    colleges = archetype.get("colleges_template") or []
    if not isinstance(colleges, list):
        return False, "colleges_template is not a list"
    if len(colleges) > max_colleges:
        return False, f"too many colleges ({len(colleges)} > {max_colleges})"
    bad_ids = [c for c in colleges if c not in colleges_allowlist]
    if bad_ids:
        return False, f"college ids not in allowlist: {bad_ids}"

    expected_template = archetype.get("expected_template_used")
    if expected_template is not None and expected_template not in valid_templates:
        return False, (
            f"expected_template_used {expected_template!r} not a real "
            f"template (template hallucination)"
        )

    tests = archetype.get("tests")
    if tests is not None:
        if not isinstance(tests, list) or not all(isinstance(t, str) for t in tests):
            return False, "tests must be a list of strings"

    return True, ""


# ---- History summary (what the LLM sees) ----------------------------------


def summarize_history(runs: List[dict], *, days: int = 14) -> dict:
    """Boil down recent runs into structured signals the LLM can read in
    its prompt.

    Returns:
      {
        "surface_coverage": {surface: count_of_runs_touching_it},
        "recent_failures": [{run_id, scenario_id, surfaces}],
        "scenarios_seen": [{id: run_count}],
        "gpa_buckets": {bucket: count}
      }
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    recent = []
    for r in runs:
        ts = r.get("started_at")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= cutoff:
            recent.append(r)

    surface_coverage: Dict[str, int] = {}
    scenarios_seen: Dict[str, int] = {}
    recent_failures: List[dict] = []
    gpa_buckets: Dict[str, int] = {
        "0-2.5": 0, "2.5-3.0": 0, "3.0-3.5": 0, "3.5-4.0": 0,
    }

    for run in recent:
        for scenario in run.get("scenarios") or []:
            sid = scenario.get("scenario_id")
            if sid:
                scenarios_seen[sid] = scenarios_seen.get(sid, 0) + 1
            for surf in scenario.get("surfaces_covered") or []:
                surface_coverage[surf] = surface_coverage.get(surf, 0) + 1
            if not scenario.get("passed", True):
                recent_failures.append({
                    "run_id": run.get("run_id"),
                    "scenario_id": sid,
                    "surfaces": scenario.get("surfaces_covered") or [],
                })
            # GPA bucket from variation if present
            variation = scenario.get("variation") or {}
            gpa_delta = variation.get("gpa_delta", 0.0)
            # We don't have base gpa here, but gpa_delta + an assumed
            # base of 3.7 gives a rough bucket. Improve once we
            # capture full profile in the report.
            approx = 3.7 + (gpa_delta or 0.0)
            if approx < 2.5:
                gpa_buckets["0-2.5"] += 1
            elif approx < 3.0:
                gpa_buckets["2.5-3.0"] += 1
            elif approx < 3.5:
                gpa_buckets["3.0-3.5"] += 1
            else:
                gpa_buckets["3.5-4.0"] += 1

    return {
        "surface_coverage": surface_coverage,
        "recent_failures": recent_failures[:10],
        "scenarios_seen": scenarios_seen,
        "gpa_buckets": gpa_buckets,
        "runs_in_window": len(recent),
    }


# ---- Main entry: synthesize -----------------------------------------------


def synthesize_scenarios(
    *,
    n: int,
    history: List[dict],
    system_knowledge: str,
    colleges_allowlist: List[str],
    feedback_items: Optional[List[dict]] = None,
    valid_templates: Optional[Set[str]] = None,
    max_colleges: int = 8,
    gemini_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
) -> List[dict]:
    """Returns up to `n` validated synthesized archetypes. Empty list on
    any failure (no key, malformed output, all candidates invalid).
    Caller fills the slack with static archetypes.

    `feedback_items` (PR-N): admin-authored notes that steer scenario
    design — prioritized in the prompt with their stable IDs so the LLM
    can stamp generated scenarios with `feedback_id` for credit
    tracking.
    """
    if not gemini_key or n <= 0:
        return []

    history_summary = summarize_history(history)

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        gen_model = genai.GenerativeModel(model)
        prompt = _build_prompt(
            n, system_knowledge, history_summary, colleges_allowlist,
            feedback_items=feedback_items,
        )
        resp = gen_model.generate_content(prompt)
        raw = (resp.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("synthesizer: LLM call failed: %s", exc)
        return []

    payload = _parse_json(raw)
    if not payload:
        logger.warning("synthesizer: LLM returned malformed JSON")
        return []

    candidates = payload.get("scenarios") or []
    if not isinstance(candidates, list):
        return []

    valid: List[dict] = []
    for i, scenario in enumerate(candidates):
        if not isinstance(scenario, dict):
            continue
        # Stamp the synthesized marker if the model omitted it.
        scenario.setdefault("synthesized", True)
        scenario.setdefault("id", f"synth_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        ok, err = validate_archetype(
            scenario, colleges_allowlist,
            valid_templates=valid_templates, max_colleges=max_colleges,
        )
        if ok:
            valid.append(scenario)
        else:
            logger.info("synthesizer: rejected scenario %s — %s", scenario.get("id"), err)

    return valid[:n]


# ---- Prompt + parsing -----------------------------------------------------


def _build_prompt(n, system_knowledge, history_summary, colleges_allowlist,
                  *, feedback_items=None) -> str:
    feedback_section = _format_feedback_section(feedback_items or [])
    feedback_instruction = (
        "\n7. If a scenario was designed to address an item from the ADMIN FEEDBACK "
        "section above, include the matching `feedback_id` in the scenario JSON "
        '(e.g., "feedback_id": "fb_abc123") so the dashboard can credit it as applied.'
        if feedback_items
        else ""
    )
    return f"""You are a senior QA engineer planning the next test pass for a college admissions app. Your job is to synthesize {n} test scenarios that target gaps and risks observed in recent test history.
{feedback_section}
# System you're testing
{system_knowledge}

# Recent run history summary (last 14 days)
- Runs: {history_summary.get('runs_in_window', 0)}
- Surface coverage: {history_summary.get('surface_coverage', {})}
- Scenarios seen + counts: {history_summary.get('scenarios_seen', {})}
- Recent failures: {history_summary.get('recent_failures', [])}
- GPA bucket distribution: {history_summary.get('gpa_buckets', {})}

# Valid college IDs (use ONLY these — don't invent new ones)
{json.dumps(colleges_allowlist)}

# Your task
Generate exactly {n} test scenarios in JSON. Each scenario MUST:
1. Target a specific gap or risk you observe in the history (under-tested surface, under-represented persona, or recently-failed shape).
2. Stay within valid input ranges:
   - grade_level: "9th Grade" | "10th Grade" | "11th Grade" | "12th Grade"
   - graduation_year: integer between 2026 and 2030
   - gpa: float in [0.0, 4.0]
   - colleges_template: 1 to 6 ids, all from the allowlist above
3. Include a `synthesis_rationale` field of 2-3 sentences explaining what gap or risk this scenario targets and why.
4. Include a `business_rationale` field — 1-2 sentences in plain language a non-engineer (e.g., a PM or designer) would understand, explaining what user need or business risk this scenario validates. Focus on WHY the test matters, not just WHAT it does.
   Good example: "Confirms that brand-new 9th graders get a useful, age-appropriate roadmap right away — the first impression for our youngest cohort and a common drop-off point if the dashboard feels empty."
   Bad example: "Tests freshman_fall template resolution." (technical, no business framing)
5. Include a `tests` field — 3-5 plain-English bullets describing what the scenario verifies.
6. Use a valid `expected_template_used`: one of [freshman_fall, freshman_spring, sophomore_fall, sophomore_spring, junior_fall, junior_spring, junior_summer, senior_fall, senior_spring].{feedback_instruction}

Return STRICT JSON ONLY (no markdown, no commentary):
{{
  "scenarios": [
    {{
      "id": "synth_<short_label>",
      "synthesized": true,
      "synthesis_rationale": "...",
      "description": "...",
      "business_rationale": "1-2 sentences a non-engineer would understand, framing the user need or business risk this validates",
      "tests": ["...", "..."],
      "default_student_name": "...",
      "profile_template": {{
        "grade_level": "...",
        "graduation_year": 2027,
        "gpa": 3.5,
        "intended_major": "...",
        "interests": ["..."]
      }},
      "colleges_template": ["...", "..."],
      "expected_template_used": "...",
      "surfaces_covered": ["profile", "college_list", "roadmap"]
    }}
  ]
}}
"""


def _format_feedback_section(items) -> str:
    """Render active admin feedback as a prompt section. Returns empty
    string when there are no items so the prompt looks clean."""
    if not items:
        return ""
    lines = [
        "",
        "# ADMIN FEEDBACK (steers scenario design — prioritize addressing these)",
        "Use the IDs below as `feedback_id` in any scenario you design to address an item.",
        "",
    ]
    for it in items:
        applied = it.get("applied_count", 0)
        max_a = it.get("max_applies", 5)
        lines.append(
            f"- {it.get('id', '<no-id>')}: {it.get('text', '')} "
            f"(applied {applied}/{max_a})"
        )
    lines.append("")
    return "\n".join(lines)


def _parse_json(raw: str) -> Optional[dict]:
    """Tolerant JSON parse — strips code fences if the model added them."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[len("json"):].lstrip()
        text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except (ValueError, json.JSONDecodeError):
        return None
