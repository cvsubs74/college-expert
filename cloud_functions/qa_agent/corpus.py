"""
Scenario corpus: archetypes, selection policy, and LLM-driven variation.

The corpus is the agent's library of test scenarios. Each archetype is a
hand-curated profile + college list + assertion set that exercises a
specific shape of student. Per-run selection picks a few archetypes,
then a small LLM step generates a *variation* (different name, slightly
different specifics) so the agent doesn't replay identical traffic
every day.

Selection policy (in priority order):
  1. Archetypes that haven't run in > 7 days
  2. Archetypes with a recent failure (last 7 days)
  3. Random rotation across the rest

The bias serves two goals: maximize coverage of the corpus over time,
and re-test recently-broken paths so we know whether they're still
broken.
"""

from __future__ import annotations

import json
import logging
import os
import random
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Archetype JSON files live alongside this module so they ship with the
# function deploy. Adding an archetype = drop a file in scenarios/.
SCENARIOS_DIR = Path(__file__).parent / "scenarios"


# ---- Archetype loading -------------------------------------------------------


def load_archetypes() -> List[dict]:
    """Read every JSON file in scenarios/ as an archetype.

    Each file is a self-contained scenario definition; see scenarios/
    README for the schema."""
    archetypes = []
    if not SCENARIOS_DIR.exists():
        return archetypes
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        try:
            with path.open() as f:
                archetypes.append(json.load(f))
        except Exception as exc:  # noqa: BLE001
            logger.warning("qa_agent: failed to load archetype %s: %s", path.name, exc)
    return archetypes


# ---- Selection ---------------------------------------------------------------


def _days_since(ts_iso: Optional[str], now: Optional[datetime] = None) -> float:
    """How many days since `ts_iso`? Returns infinity if missing."""
    if not ts_iso:
        return float("inf")
    try:
        ts = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except ValueError:
        return float("inf")
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def select_scenarios(
    archetypes: List[dict],
    history: Dict[str, dict],
    *,
    n: int = 4,
    untried_threshold_days: float = 7.0,
    rng: Optional[random.Random] = None,
    now: Optional[datetime] = None,
) -> List[dict]:
    """Pick `n` archetypes for this run.

    `history` maps archetype id → its most-recent record (last_run_at,
    failures_last_30d). Missing entries are treated as "never run." The
    function returns a deep-copy list so callers can mutate freely
    without polluting the loaded archetype set.
    """
    rng = rng or random.Random()
    now = now or datetime.now(timezone.utc)

    untried, recent_failures, rest = [], [], []
    for a in archetypes:
        h = history.get(a["id"], {})
        days = _days_since(h.get("last_run_at"), now)
        if days >= untried_threshold_days:
            untried.append(a)
        if h.get("failures_last_30d", 0) > 0 and days <= untried_threshold_days:
            recent_failures.append(a)
        rest.append(a)

    chosen: List[dict] = []
    seen_ids: set = set()

    def _add(a):
        if a["id"] in seen_ids:
            return
        chosen.append(a)
        seen_ids.add(a["id"])

    rng.shuffle(untried)
    for a in untried[:max(0, n - 1)]:
        _add(a)

    rng.shuffle(recent_failures)
    for a in recent_failures[:1]:
        _add(a)

    rng.shuffle(rest)
    for a in rest:
        if len(chosen) >= n:
            break
        _add(a)

    return [deepcopy(a) for a in chosen[:n]]


# ---- LLM variation -----------------------------------------------------------


_VARIATION_PROMPT = """You are generating a synthetic student profile for QA testing of a college admissions app. Produce one variation of the archetype below.

The variation must keep the archetype's INTENT intact (same grade, same number of schools, same broad academic profile) but vary surface details so the test traffic isn't identical to yesterday's run.

Archetype description: {description}
Base profile: {profile_template}

Return STRICT JSON with this shape — no markdown, no commentary, no code fences:
{{
  "student_name": "<random first + last>",
  "intended_major": "<a major from the same broad field as the base>",
  "extra_interest": "<one short interest tag>",
  "gpa_delta": <a number between -0.2 and +0.2>
}}
"""


def generate_variation(
    archetype: dict,
    *,
    api_key: Optional[str] = None,
    model: str = "gemini-1.5-flash",
) -> dict:
    """Ask Gemini to produce a variation. On any failure, returns the
    archetype's defaults — i.e., the static fallback. Missing/invalid
    GEMINI_API_KEY also produces the static fallback so unit tests run
    without external calls."""
    fallback = {
        "student_name": archetype.get("default_student_name", "QA Test User"),
        "intended_major": archetype["profile_template"].get("intended_major", "Undecided"),
        "extra_interest": "",
        "gpa_delta": 0.0,
    }

    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("qa_agent: GEMINI_API_KEY missing, using static variation")
        return fallback

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        gen_model = genai.GenerativeModel(model)
        prompt = _VARIATION_PROMPT.format(
            description=archetype.get("description", ""),
            profile_template=json.dumps(archetype.get("profile_template", {})),
        )
        resp = gen_model.generate_content(prompt)
        raw = (resp.text or "").strip()
        # Strip optional code fences the model sometimes ignores instructions about.
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[len("json"):].lstrip()
            raw = raw.rstrip("`").strip()
        parsed = json.loads(raw)
        return _validate_variation(parsed, fallback)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent: LLM variation failed (%s); using fallback", exc)
        return fallback


def _validate_variation(parsed: dict, fallback: dict) -> dict:
    """Coerce model output to the expected shape, pulling fallback values
    where the model omitted or mis-typed a field."""
    out = dict(fallback)
    if isinstance(parsed.get("student_name"), str) and parsed["student_name"].strip():
        out["student_name"] = parsed["student_name"].strip()
    if isinstance(parsed.get("intended_major"), str) and parsed["intended_major"].strip():
        out["intended_major"] = parsed["intended_major"].strip()
    if isinstance(parsed.get("extra_interest"), str):
        out["extra_interest"] = parsed["extra_interest"].strip()
    delta = parsed.get("gpa_delta")
    if isinstance(delta, (int, float)) and -0.2 <= float(delta) <= 0.2:
        out["gpa_delta"] = float(delta)
    return out


# ---- Materializing a runnable scenario --------------------------------------


def apply_variation(archetype: dict, variation: dict) -> dict:
    """Combine an archetype + a variation into a concrete scenario the
    runner can execute. Returns a new dict; archetype is not mutated."""
    scenario = deepcopy(archetype)
    profile = scenario.setdefault("profile_template", {})

    if "student_name" in variation:
        profile["full_name"] = variation["student_name"]
    if "intended_major" in variation:
        profile["intended_major"] = variation["intended_major"]
    if variation.get("extra_interest"):
        existing = list(profile.get("interests", []))
        if variation["extra_interest"] not in existing:
            existing.append(variation["extra_interest"])
        profile["interests"] = existing
    if "gpa_delta" in variation and "gpa" in profile:
        try:
            profile["gpa"] = round(float(profile["gpa"]) + float(variation["gpa_delta"]), 2)
        except (TypeError, ValueError):
            pass

    scenario["_variation"] = variation
    return scenario
