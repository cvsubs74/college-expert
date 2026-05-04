"""
Fit-analysis structural + invariant assertions.

The college-fit algorithm in profile_manager_v2/fit_computation.py
applies deterministic post-processing after the LLM call:

  - Selectivity floor:  acceptance_rate < 8%   →  must be SUPER_REACH
                        acceptance_rate < 15%  →  must be REACH or worse
  - Selectivity ceiling:acceptance_rate >= 50% →  must be SAFETY
                        acceptance_rate >= 25% →  cannot be REACH/SUPER_REACH
  - Match-% range:      SAFETY 75-100, TARGET 55-74, REACH 35-54,
                        SUPER_REACH 0-34
  - Category whitelist: {SAFETY, TARGET, REACH, SUPER_REACH}
  - Factor bounds:      Academic 0-40, Holistic 0-30, Major Fit 0-15,
                        Selectivity -15 to +5

These assertions catch regression of any of those rules. Each
assertion is a small function returning AssertionResult and slots
into the same `assertions.run_all()` plumbing the runner already uses.

Spec: docs/prd/qa-fit-testing.md + docs/design/qa-fit-testing.md.
"""

from __future__ import annotations

from typing import Any, Optional

from assertions import AssertionFn, AssertionResult, _walk


# Bounds mirror fit_computation.py's selectivity-tier gating.
VALID_CATEGORIES = ("SAFETY", "TARGET", "REACH", "SUPER_REACH")

# Match-% range per category, after post-processor alignment.
_CATEGORY_MATCH_RANGES = {
    "SAFETY":      (75, 100),
    "TARGET":      (55, 74),
    "REACH":       (35, 54),
    "SUPER_REACH": (0, 34),
}

# Per-factor (score_min, score_max). Selectivity is the only factor
# that goes negative (it's an adjustment, not a strict score).
_EXPECTED_FACTORS = {
    "Academic":    (0, 40),
    "Holistic":    (0, 30),
    "Major Fit":   (0, 15),
    "Selectivity": (-15, 5),
}

# The 8 advisory blocks the fit prompt requires. Phase 1 just asserts
# they're present + non-empty; content quality is a Phase 4 concern.
_REQUIRED_BLOCKS = (
    "explanation",
    "essay_angles",
    "application_timeline",
    "scholarship_matches",
    "test_strategy",
    "major_strategy",
    "demonstrated_interest_tips",
    "red_flags_to_avoid",
    "recommendations",
)


# ---- Helpers ---------------------------------------------------------------


def _get(ctx: dict, dotted: str) -> tuple[bool, Any]:
    body = ctx.get("response_json") or {}
    return _walk(body, dotted)


# ---- Public assertions -----------------------------------------------------


def category_in_valid_set(
    path: str = "fit_analysis.fit_category",
) -> AssertionFn:
    """Category must be one of {SAFETY, TARGET, REACH, SUPER_REACH}."""
    def _check(ctx):
        present, value = _get(ctx, path)
        if not present:
            return AssertionResult(
                name="fit category present + valid",
                passed=False,
                message=f"missing key '{path}'",
            )
        if value not in VALID_CATEGORIES:
            return AssertionResult(
                name="fit category present + valid",
                passed=False,
                message=f"got {value!r}; expected one of {list(VALID_CATEGORIES)}",
            )
        return AssertionResult(
            name="fit category present + valid",
            passed=True,
        )
    return _check


def match_percentage_in_range(
    path: str = "fit_analysis.match_percentage",
) -> AssertionFn:
    """match_percentage must be a number in [0, 100]."""
    def _check(ctx):
        present, value = _get(ctx, path)
        if not present:
            return AssertionResult(
                name="match_percentage in [0, 100]",
                passed=False,
                message=f"missing key '{path}'",
            )
        try:
            num = float(value)
        except (TypeError, ValueError):
            return AssertionResult(
                name="match_percentage in [0, 100]",
                passed=False,
                message=f"got non-numeric {value!r}",
            )
        if num < 0 or num > 100:
            return AssertionResult(
                name="match_percentage in [0, 100]",
                passed=False,
                message=f"got {num} — outside [0, 100]",
            )
        return AssertionResult(
            name="match_percentage in [0, 100]",
            passed=True,
        )
    return _check


def match_percentage_aligns_with_category(
    pct_path: str = "fit_analysis.match_percentage",
    cat_path: str = "fit_analysis.fit_category",
) -> AssertionFn:
    """Match-% must fall in the band declared for its category.

    Catches both LLM drift (model returns 50% for a SUPER_REACH) and
    post-processor regression (range alignment broke).
    """
    def _check(ctx):
        cat_present, cat = _get(ctx, cat_path)
        pct_present, pct = _get(ctx, pct_path)
        if not cat_present or not pct_present:
            return AssertionResult(
                name="match_percentage in category band",
                passed=False,
                message="missing fit_category or match_percentage",
            )
        try:
            pct_num = float(pct)
        except (TypeError, ValueError):
            return AssertionResult(
                name="match_percentage in category band",
                passed=False,
                message=f"non-numeric match_percentage {pct!r}",
            )
        band = _CATEGORY_MATCH_RANGES.get(cat)
        if band is None:
            return AssertionResult(
                name="match_percentage in category band",
                passed=False,
                message=f"unknown category {cat!r}",
            )
        lo, hi = band
        if not (lo <= pct_num <= hi):
            return AssertionResult(
                name="match_percentage in category band",
                passed=False,
                message=(
                    f"{cat} requires match_percentage in [{lo}, {hi}], "
                    f"got {pct_num}"
                ),
            )
        return AssertionResult(
            name="match_percentage in category band",
            passed=True,
        )
    return _check


def selectivity_floor_respected(
    cat_path: str = "fit_analysis.fit_category",
    rate_path: str = "fit_analysis.acceptance_rate",
) -> AssertionFn:
    """If acceptance_rate < 8%, category MUST be SUPER_REACH.
    If 8 <= acceptance_rate < 15%, category MUST be SUPER_REACH or
    REACH. The production code's hard guarantee — a strong profile
    cannot promote an Ivy out of REACH/SUPER_REACH territory."""
    def _check(ctx):
        cat_present, cat = _get(ctx, cat_path)
        rate_present, rate = _get(ctx, rate_path)
        if not cat_present or not rate_present:
            return AssertionResult(
                name="selectivity floor respected",
                passed=False,
                message="missing fit_category or acceptance_rate",
            )
        try:
            rate_num = float(rate)
        except (TypeError, ValueError):
            return AssertionResult(
                name="selectivity floor respected",
                passed=False,
                message=f"non-numeric acceptance_rate {rate!r}",
            )
        if rate_num < 8 and cat != "SUPER_REACH":
            return AssertionResult(
                name="selectivity floor respected",
                passed=False,
                message=(
                    f"acceptance_rate {rate_num}% (<8%) must be "
                    f"SUPER_REACH, got {cat}"
                ),
            )
        if 8 <= rate_num < 15 and cat not in ("SUPER_REACH", "REACH"):
            return AssertionResult(
                name="selectivity floor respected",
                passed=False,
                message=(
                    f"acceptance_rate {rate_num}% (8-15%) must be "
                    f"REACH or SUPER_REACH, got {cat}"
                ),
            )
        return AssertionResult(
            name="selectivity floor respected",
            passed=True,
        )
    return _check


def selectivity_ceiling_respected(
    cat_path: str = "fit_analysis.fit_category",
    rate_path: str = "fit_analysis.acceptance_rate",
) -> AssertionFn:
    """If acceptance_rate >= 50%, category MUST be SAFETY.
    If acceptance_rate >= 25%, category cannot be REACH or SUPER_REACH
    (must be SAFETY or TARGET)."""
    def _check(ctx):
        cat_present, cat = _get(ctx, cat_path)
        rate_present, rate = _get(ctx, rate_path)
        if not cat_present or not rate_present:
            return AssertionResult(
                name="selectivity ceiling respected",
                passed=False,
                message="missing fit_category or acceptance_rate",
            )
        try:
            rate_num = float(rate)
        except (TypeError, ValueError):
            return AssertionResult(
                name="selectivity ceiling respected",
                passed=False,
                message=f"non-numeric acceptance_rate {rate!r}",
            )
        if rate_num >= 50 and cat != "SAFETY":
            return AssertionResult(
                name="selectivity ceiling respected",
                passed=False,
                message=(
                    f"acceptance_rate {rate_num}% (>=50%) must be "
                    f"SAFETY, got {cat}"
                ),
            )
        if rate_num >= 25 and cat in ("REACH", "SUPER_REACH"):
            return AssertionResult(
                name="selectivity ceiling respected",
                passed=False,
                message=(
                    f"acceptance_rate {rate_num}% (>=25%) cannot be "
                    f"REACH or SUPER_REACH, got {cat}"
                ),
            )
        return AssertionResult(
            name="selectivity ceiling respected",
            passed=True,
        )
    return _check


def factor_bounds_respected(
    path: str = "fit_analysis.factors",
) -> AssertionFn:
    """The four factors {Academic, Holistic, Major Fit, Selectivity}
    must all be present, and each score must be in its bounds.
    Catches the classic LLM bug where score > max."""
    def _check(ctx):
        present, factors = _get(ctx, path)
        if not present or not isinstance(factors, list):
            return AssertionResult(
                name="factor bounds respected",
                passed=False,
                message=f"missing or non-list '{path}'",
            )
        names_seen = {f.get("name") for f in factors if isinstance(f, dict)}
        for expected_name in _EXPECTED_FACTORS:
            if expected_name not in names_seen:
                return AssertionResult(
                    name="factor bounds respected",
                    passed=False,
                    message=(
                        f"missing factor {expected_name!r}; "
                        f"got 4 expected, saw {sorted(n for n in names_seen if n)}"
                    ),
                )
        for f in factors:
            if not isinstance(f, dict):
                continue
            name = f.get("name")
            score = f.get("score")
            bounds = _EXPECTED_FACTORS.get(name)
            if bounds is None:
                continue  # extra factors are fine; we only police known ones
            try:
                score_num = float(score)
            except (TypeError, ValueError):
                return AssertionResult(
                    name="factor bounds respected",
                    passed=False,
                    message=f"factor {name!r} non-numeric score {score!r}",
                )
            lo, hi = bounds
            if not (lo <= score_num <= hi):
                return AssertionResult(
                    name="factor bounds respected",
                    passed=False,
                    message=(
                        f"factor {name!r} score {score_num} out of "
                        f"bounds [{lo}, {hi}]"
                    ),
                )
        return AssertionResult(
            name="factor bounds respected",
            passed=True,
        )
    return _check


def required_advisory_blocks_present(
    base_path: str = "fit_analysis",
) -> AssertionFn:
    """All 8 advisory blocks (explanation, essay_angles, …,
    recommendations) must be present and non-empty.

    Phase 1 doesn't judge content quality; just asserts the LLM didn't
    drop a section. An empty `recommendations` list is treated as a
    regression — the prompt explicitly asks for 3 entries.
    """
    def _check(ctx):
        present, body = _get(ctx, base_path)
        if not present or not isinstance(body, dict):
            return AssertionResult(
                name="required advisory blocks present",
                passed=False,
                message=f"missing or non-dict '{base_path}'",
            )
        for block in _REQUIRED_BLOCKS:
            v = body.get(block)
            if v is None:
                return AssertionResult(
                    name="required advisory blocks present",
                    passed=False,
                    message=f"missing block {block!r}",
                )
            if isinstance(v, (list, dict, str)) and len(v) == 0:
                return AssertionResult(
                    name="required advisory blocks present",
                    passed=False,
                    message=f"block {block!r} is empty",
                )
        return AssertionResult(
            name="required advisory blocks present",
            passed=True,
        )
    return _check
