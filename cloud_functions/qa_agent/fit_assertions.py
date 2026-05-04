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


# ---- Cross-college category-rank ordering ---------------------------------
#
# When a single scenario exercises N >= 2 schools (the runner gets a
# `fit_target_colleges` list), the same student's category-rank should
# be monotonically non-decreasing as acceptance_rate increases. Equivalently:
# a less-selective school can never have a *worse* category than a more-
# selective one for the same student. We don't police within-band match-%
# ordering — that's noisy and would generate flaky failures.

_CATEGORY_RANK = {"SUPER_REACH": 0, "REACH": 1, "TARGET": 2, "SAFETY": 3}


def check_category_rank_monotonic_with_selectivity(
    fit_responses: list,
) -> "list[AssertionResult]":
    """Walk a list of (uni_id, http_ctx) tuples and check that the
    fit categories rank monotonically with acceptance_rate.

    Returns a list of AssertionResult — one per consecutive pair —
    suitable for the runner to splice into a step record. Returns a
    single skip-shaped pass when there are fewer than 2 valid fits
    (so the step still has a record but doesn't false-positive).
    """
    extracted = []
    for uni_id, ctx in fit_responses or []:
        body = (ctx or {}).get("response_json") or {}
        fa = body.get("fit_analysis") or {}
        cat = fa.get("fit_category")
        ar = fa.get("acceptance_rate")
        if cat not in _CATEGORY_RANK or ar is None:
            continue
        try:
            ar_num = float(ar)
        except (TypeError, ValueError):
            continue
        extracted.append((uni_id, ar_num, cat, _CATEGORY_RANK[cat]))

    if len(extracted) < 2:
        return [AssertionResult(
            name="match% monotonic with selectivity",
            passed=True,
            message=(
                "(skipped — fewer than 2 valid fits to compare)"
            ),
        )]

    # Sort by acceptance_rate ascending: most-selective first.
    extracted.sort(key=lambda x: x[1])

    results = []
    for i in range(1, len(extracted)):
        prev_uni, prev_ar, prev_cat, prev_rank = extracted[i - 1]
        cur_uni, cur_ar, cur_cat, cur_rank = extracted[i]
        ok = cur_rank >= prev_rank
        msg = "" if ok else (
            f"{cur_uni} (acc={cur_ar}%) is {cur_cat} but "
            f"{prev_uni} (acc={prev_ar}%) is {prev_cat}; the same "
            f"student should never get a WORSE fit category at a "
            f"less-selective school"
        )
        results.append(AssertionResult(
            name=f"category rank monotonic: {cur_uni} vs {prev_uni}",
            passed=ok,
            message=msg,
        ))
    return results


def test_strategy_not_submit_when_no_scores(
    path: str = "fit_analysis.test_strategy.recommendation",
) -> AssertionFn:
    """When the student profile carries no SAT/ACT scores, the
    algorithm's test_strategy.recommendation must not be "Submit" —
    there's nothing to submit. Valid recommendations in this case:
    "Don't Submit" (no scores → don't submit) or "Consider Submitting"
    (the student should think about taking a test).

    Catches a flaw observed in production 2026-05-04: the LLM
    defaulted to "Submit" for some schools (MIT, UF) even when the
    student profile carried no scores. The post-processor in
    fit_computation.py now overrides "Submit" → "Don't Submit" when
    student_profile_json indicates no scores; this assertion is the
    monitoring guarantee that override stays in place.
    """
    def _check(ctx):
        present, value = _get(ctx, path)
        if not present:
            return AssertionResult(
                name="test_strategy not Submit when no scores",
                passed=False,
                message=f"missing key '{path}'",
            )
        ok = value != "Submit"
        return AssertionResult(
            name="test_strategy not Submit when no scores",
            passed=ok,
            message=(
                f"got {value!r} but the student profile has no SAT or "
                f"ACT scores — the algorithm should recommend "
                f"\"Don't Submit\" or \"Consider Submitting\""
                if not ok else ""
            ),
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
