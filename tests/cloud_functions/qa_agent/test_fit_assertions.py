"""
Unit tests for fit_assertions — the structural+invariant assertion
library used by the QA agent's compute_fit step.

Spec: docs/prd/qa-fit-testing.md + docs/design/qa-fit-testing.md.

The fit algorithm in profile_manager_v2/fit_computation.py applies
deterministic post-processing rules (selectivity floor + ceiling,
match-% range alignment, factor max bounds, category whitelist).
These assertions catch regression of any of those rules.

Tests use plain dict fixtures shaped like a real /compute-single-fit
response — no network.
"""

from __future__ import annotations


def _ctx(fit_analysis: dict, status: int = 200) -> dict:
    """Minimal HTTP context shape the runner produces, with the fit
    response under fit_analysis. Mirrors runner._http: status_code +
    response_json + response_excerpt + elapsed_ms."""
    return {
        "status_code": status,
        "response_excerpt": "",
        "elapsed_ms": 100,
        "response_json": {"success": True, "fit_analysis": fit_analysis},
    }


def _good_fit(**overrides) -> dict:
    """A well-formed fit response. Tests override specific fields to
    flip individual assertions."""
    base = {
        "fit_category": "REACH",
        "match_percentage": 45,
        "acceptance_rate": 12.0,
        "factors": [
            {"name": "Academic", "score": 30, "max": 40, "detail": "x"},
            {"name": "Holistic", "score": 22, "max": 30, "detail": "x"},
            {"name": "Major Fit", "score": 11, "max": 15, "detail": "x"},
            {"name": "Selectivity", "score": -10, "max": 5, "detail": "x"},
        ],
        "explanation": "5-6 sentence analysis here.",
        "essay_angles": [{"essay_prompt": "Why us", "angle": "x"}],
        "application_timeline": {"recommended_plan": "RD", "deadline": "2027-01-01"},
        "scholarship_matches": [{"name": "Merit", "amount": "$1k"}],
        "test_strategy": {"recommendation": "Submit"},
        "major_strategy": {"intended_major": "CS", "is_available": True},
        "demonstrated_interest_tips": ["visit campus"],
        "red_flags_to_avoid": ["typos"],
        "recommendations": [{"action": "improve essays"}],
    }
    base.update(overrides)
    return base


# ---- category_in_valid_set ------------------------------------------------


class TestCategoryInValidSet:
    def test_passes_for_each_valid_category(self):
        import fit_assertions
        check = fit_assertions.category_in_valid_set()
        for cat in ("SAFETY", "TARGET", "REACH", "SUPER_REACH"):
            r = check(_ctx(_good_fit(fit_category=cat)))
            assert r.passed, f"{cat} should pass: {r.message}"

    def test_fails_on_unknown_category(self):
        import fit_assertions
        check = fit_assertions.category_in_valid_set()
        r = check(_ctx(_good_fit(fit_category="MAYBE")))
        assert not r.passed
        assert "MAYBE" in (r.message or "")

    def test_fails_when_missing(self):
        import fit_assertions
        check = fit_assertions.category_in_valid_set()
        bad = _good_fit()
        del bad["fit_category"]
        r = check(_ctx(bad))
        assert not r.passed


# ---- match_percentage_in_range --------------------------------------------


class TestMatchPercentageInRange:
    def test_passes_on_valid_values(self):
        import fit_assertions
        check = fit_assertions.match_percentage_in_range()
        for v in (0, 1, 50, 99, 100):
            r = check(_ctx(_good_fit(match_percentage=v)))
            assert r.passed, f"{v} should pass"

    def test_fails_below_zero(self):
        import fit_assertions
        check = fit_assertions.match_percentage_in_range()
        r = check(_ctx(_good_fit(match_percentage=-1)))
        assert not r.passed

    def test_fails_above_hundred(self):
        import fit_assertions
        check = fit_assertions.match_percentage_in_range()
        r = check(_ctx(_good_fit(match_percentage=101)))
        assert not r.passed

    def test_fails_on_non_numeric(self):
        import fit_assertions
        check = fit_assertions.match_percentage_in_range()
        r = check(_ctx(_good_fit(match_percentage="high")))
        assert not r.passed


# ---- match_percentage_aligns_with_category --------------------------------
# This is the most valuable invariant: post-processing should align
# match% with category (SAFETY 75-100, TARGET 55-74, REACH 35-54,
# SUPER_REACH 0-34). Catches LLM drift + post-processor regression.


class TestMatchPercentageAlignsWithCategory:
    def test_safety_75_passes(self):
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        r = check(_ctx(_good_fit(fit_category="SAFETY", match_percentage=80)))
        assert r.passed

    def test_safety_below_75_fails(self):
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        r = check(_ctx(_good_fit(fit_category="SAFETY", match_percentage=70)))
        assert not r.passed
        assert "SAFETY" in (r.message or "")

    def test_target_55_to_74_passes(self):
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        for v in (55, 60, 74):
            r = check(_ctx(_good_fit(fit_category="TARGET", match_percentage=v)))
            assert r.passed, f"TARGET at {v}% should pass"

    def test_target_outside_band_fails(self):
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        r1 = check(_ctx(_good_fit(fit_category="TARGET", match_percentage=54)))
        r2 = check(_ctx(_good_fit(fit_category="TARGET", match_percentage=75)))
        assert not r1.passed
        assert not r2.passed

    def test_reach_35_to_54_passes(self):
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        for v in (35, 45, 54):
            r = check(_ctx(_good_fit(fit_category="REACH", match_percentage=v)))
            assert r.passed, f"REACH at {v}% should pass"

    def test_super_reach_0_to_34_passes(self):
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        for v in (0, 15, 34):
            r = check(_ctx(_good_fit(fit_category="SUPER_REACH",
                                     match_percentage=v)))
            assert r.passed, f"SUPER_REACH at {v}% should pass"

    def test_super_reach_above_34_fails(self):
        """Catches the bug where post-processor drifts and returns
        SUPER_REACH at 50%."""
        import fit_assertions
        check = fit_assertions.match_percentage_aligns_with_category()
        r = check(_ctx(_good_fit(fit_category="SUPER_REACH",
                                 match_percentage=50)))
        assert not r.passed


# ---- selectivity_floor_respected ------------------------------------------


class TestSelectivityFloorRespected:
    def test_under_8_pct_must_be_super_reach(self):
        import fit_assertions
        check = fit_assertions.selectivity_floor_respected()
        r = check(_ctx(_good_fit(fit_category="SUPER_REACH",
                                 acceptance_rate=4.0,
                                 match_percentage=20)))
        assert r.passed
        # The floor regression: a 4%-acceptance school flagged TARGET
        # is the canonical bug we're guarding against.
        r2 = check(_ctx(_good_fit(fit_category="TARGET",
                                  acceptance_rate=4.0,
                                  match_percentage=60)))
        assert not r2.passed
        assert "4" in (r2.message or "") or "8" in (r2.message or "")

    def test_under_15_pct_must_be_reach_or_super_reach(self):
        import fit_assertions
        check = fit_assertions.selectivity_floor_respected()
        r1 = check(_ctx(_good_fit(fit_category="REACH",
                                  acceptance_rate=10.0,
                                  match_percentage=40)))
        assert r1.passed
        r2 = check(_ctx(_good_fit(fit_category="SUPER_REACH",
                                  acceptance_rate=10.0,
                                  match_percentage=20)))
        assert r2.passed
        r3 = check(_ctx(_good_fit(fit_category="TARGET",
                                  acceptance_rate=10.0,
                                  match_percentage=60)))
        assert not r3.passed
        r4 = check(_ctx(_good_fit(fit_category="SAFETY",
                                  acceptance_rate=10.0,
                                  match_percentage=80)))
        assert not r4.passed

    def test_above_15_pct_no_floor_constraint(self):
        import fit_assertions
        check = fit_assertions.selectivity_floor_respected()
        # 20% acceptance — the floor doesn't constrain; any category
        # should pass this assertion (the ceiling assertion handles
        # the upper bound).
        for cat, pct in (("SAFETY", 80), ("TARGET", 60),
                         ("REACH", 45), ("SUPER_REACH", 20)):
            r = check(_ctx(_good_fit(fit_category=cat,
                                     acceptance_rate=20.0,
                                     match_percentage=pct)))
            assert r.passed, f"At 20% acc, {cat} should not violate floor"


# ---- selectivity_ceiling_respected ----------------------------------------


class TestSelectivityCeilingRespected:
    def test_50_pct_or_more_must_be_safety(self):
        import fit_assertions
        check = fit_assertions.selectivity_ceiling_respected()
        r = check(_ctx(_good_fit(fit_category="SAFETY",
                                 acceptance_rate=60.0,
                                 match_percentage=85)))
        assert r.passed
        r2 = check(_ctx(_good_fit(fit_category="REACH",
                                  acceptance_rate=60.0,
                                  match_percentage=45)))
        assert not r2.passed

    def test_25_pct_or_more_cannot_be_super_reach(self):
        import fit_assertions
        check = fit_assertions.selectivity_ceiling_respected()
        r = check(_ctx(_good_fit(fit_category="SUPER_REACH",
                                 acceptance_rate=30.0,
                                 match_percentage=20)))
        assert not r.passed

    def test_below_25_pct_no_ceiling_constraint(self):
        import fit_assertions
        check = fit_assertions.selectivity_ceiling_respected()
        for cat, pct in (("REACH", 45), ("SUPER_REACH", 20)):
            r = check(_ctx(_good_fit(fit_category=cat,
                                     acceptance_rate=10.0,
                                     match_percentage=pct)))
            assert r.passed


# ---- factor_bounds_respected ---------------------------------------------


class TestFactorBoundsRespected:
    def test_passes_when_all_factors_within_bounds(self):
        import fit_assertions
        check = fit_assertions.factor_bounds_respected()
        r = check(_ctx(_good_fit()))
        assert r.passed

    def test_fails_when_score_above_max(self):
        import fit_assertions
        check = fit_assertions.factor_bounds_respected()
        bad = _good_fit()
        bad["factors"][0]["score"] = 50  # Academic max=40
        r = check(_ctx(bad))
        assert not r.passed
        assert "Academic" in (r.message or "")

    def test_fails_when_factor_missing(self):
        """The four expected factors must all be present."""
        import fit_assertions
        check = fit_assertions.factor_bounds_respected()
        bad = _good_fit()
        bad["factors"] = bad["factors"][:3]  # drop Selectivity
        r = check(_ctx(bad))
        assert not r.passed
        assert "Selectivity" in (r.message or "") or "4" in (r.message or "")

    def test_selectivity_score_range_negative_allowed(self):
        """Selectivity is the only factor that can go negative
        (-15 to +5 per the spec). The assertion should accept that."""
        import fit_assertions
        check = fit_assertions.factor_bounds_respected()
        bad = _good_fit()
        bad["factors"][3]["score"] = -15
        r = check(_ctx(bad))
        assert r.passed, f"Selectivity at -15 should pass: {r.message}"

    def test_selectivity_score_below_minus_15_fails(self):
        import fit_assertions
        check = fit_assertions.factor_bounds_respected()
        bad = _good_fit()
        bad["factors"][3]["score"] = -20
        r = check(_ctx(bad))
        assert not r.passed


# ---- required_advisory_blocks_present ------------------------------------


class TestRequiredAdvisoryBlocksPresent:
    def test_passes_when_all_blocks_present(self):
        import fit_assertions
        check = fit_assertions.required_advisory_blocks_present()
        r = check(_ctx(_good_fit()))
        assert r.passed

    def test_fails_when_essay_angles_missing(self):
        import fit_assertions
        check = fit_assertions.required_advisory_blocks_present()
        bad = _good_fit()
        del bad["essay_angles"]
        r = check(_ctx(bad))
        assert not r.passed
        assert "essay" in (r.message or "").lower()

    def test_fails_when_block_is_empty_array(self):
        """Empty arrays mean the LLM produced no recommendations —
        that's a regression worth catching."""
        import fit_assertions
        check = fit_assertions.required_advisory_blocks_present()
        bad = _good_fit()
        bad["recommendations"] = []
        r = check(_ctx(bad))
        assert not r.passed
        assert "recommendations" in (r.message or "")


# ---- Cross-college category-rank ordering --------------------------------
# Phase 2b: when the runner exercises N >= 2 schools in one scenario,
# the same student's category-rank must be monotonically non-decreasing
# as acceptance_rate increases (i.e. less selective → equal or higher
# rank). Walks the previously-collected fit responses and returns a
# list of AssertionResult so the runner can roll them into a step
# record.
#
# Why category-rank, not raw match_percentage? Match-% noise within a
# single category band would generate flaky failures on tied
# selectivity tiers. Category-rank is the post-processor's
# canonicalised view and is the right level of strictness.


_CATEGORY_RANK = {"SUPER_REACH": 0, "REACH": 1, "TARGET": 2, "SAFETY": 3}


def _fit_response(uni_id, *, category, match_pct, acc_rate):
    """Helper to build a (uni_id, ctx) tuple shaped like what the
    runner accumulates from compute_fit steps."""
    return (uni_id, _ctx({
        "fit_category": category,
        "match_percentage": match_pct,
        "acceptance_rate": acc_rate,
        "factors": [],
        "essay_angles": [], "application_timeline": {},
        "scholarship_matches": [], "test_strategy": {},
        "major_strategy": {}, "demonstrated_interest_tips": [],
        "red_flags_to_avoid": [], "recommendations": [],
        "explanation": "x",
    }))


class TestCategoryRankMonotonicWithSelectivity:
    def test_passes_on_correct_ordering(self):
        """MIT (4%, SUPER_REACH) → Berkeley (11%, REACH) → Ohio State
        (60%, SAFETY) — the canonical "strong student gets safer
        schools as selectivity drops" shape we observed in production."""
        import fit_assertions
        responses = [
            _fit_response("mit", category="SUPER_REACH",
                          match_pct=32, acc_rate=4.6),
            _fit_response("ucb", category="REACH",
                          match_pct=54, acc_rate=11.0),
            _fit_response("osu", category="SAFETY",
                          match_pct=78, acc_rate=60.6),
        ]
        results = fit_assertions.check_category_rank_monotonic_with_selectivity(
            responses,
        )
        assert all(r.passed for r in results), [
            (r.name, r.message) for r in results if not r.passed
        ]

    def test_fails_when_more_selective_school_ranks_higher(self):
        """The canonical regression: same student lands SAFETY at
        MIT (4%) but TARGET at Ohio State (60%). Ordering broken."""
        import fit_assertions
        responses = [
            _fit_response("mit", category="SAFETY",  # ← bug
                          match_pct=80, acc_rate=4.6),
            _fit_response("osu", category="TARGET",  # ← bug
                          match_pct=60, acc_rate=60.6),
        ]
        results = fit_assertions.check_category_rank_monotonic_with_selectivity(
            responses,
        )
        assert any(not r.passed for r in results), (
            f"Expected at least one failure: {[(r.name, r.passed) for r in results]}"
        )

    def test_passes_on_same_category_across_schools(self):
        """Two SUPER_REACH schools with different match% within band
        should still pass (we don't police within-band ordering — too
        noisy)."""
        import fit_assertions
        responses = [
            _fit_response("mit", category="SUPER_REACH",
                          match_pct=32, acc_rate=4.6),
            _fit_response("stanford", category="SUPER_REACH",
                          match_pct=30, acc_rate=4.0),
        ]
        results = fit_assertions.check_category_rank_monotonic_with_selectivity(
            responses,
        )
        assert all(r.passed for r in results)

    def test_returns_skip_when_fewer_than_two_responses(self):
        """A scenario with one (or zero) fit calls can't be checked
        for ordering — return a single skip-shaped result so the
        step still has a record but doesn't fail."""
        import fit_assertions
        results = fit_assertions.check_category_rank_monotonic_with_selectivity([])
        assert len(results) == 1
        assert results[0].passed
        assert "skip" in results[0].message.lower() or "fewer" in results[0].message.lower()

        results = fit_assertions.check_category_rank_monotonic_with_selectivity([
            _fit_response("mit", category="SUPER_REACH",
                          match_pct=32, acc_rate=4.6),
        ])
        assert len(results) == 1
        assert results[0].passed

    def test_skips_responses_missing_acceptance_rate_or_category(self):
        """Defensive — if a fit response is malformed, skip that entry
        rather than crash. The other responses are still checked."""
        import fit_assertions
        responses = [
            _fit_response("mit", category="SUPER_REACH",
                          match_pct=32, acc_rate=4.6),
            ("malformed", _ctx({"fit_category": None, "acceptance_rate": None})),
            _fit_response("osu", category="SAFETY",
                          match_pct=78, acc_rate=60.6),
        ]
        results = fit_assertions.check_category_rank_monotonic_with_selectivity(
            responses,
        )
        # mit (rank 0) and osu (rank 3) should still be compared and pass.
        assert all(r.passed for r in results)
        # And there must be at least one comparison made (not all skipped).
        assert any("monotonic" in r.name.lower() for r in results)


# ---- test_strategy invariant when student has no scores -----------------
# Spec: docs/prd/qa-fit-testing.md (Phase 2c-2).
# Bug surfaced 2026-05-04: probe of saved fit responses showed MIT and
# UF recommending "Submit" when the student profile carried no SAT/ACT
# scores. There's nothing to submit. Phase 2c-2 catches this.


class TestTestStrategyNotSubmitWhenNoScores:
    def test_passes_on_dont_submit(self):
        import fit_assertions
        check = fit_assertions.test_strategy_not_submit_when_no_scores()
        fit = _good_fit()
        fit["test_strategy"] = {"recommendation": "Don't Submit"}
        r = check(_ctx(fit))
        assert r.passed

    def test_passes_on_consider_submitting(self):
        """'Consider Submitting' is also valid — student should think
        about taking a test."""
        import fit_assertions
        check = fit_assertions.test_strategy_not_submit_when_no_scores()
        fit = _good_fit()
        fit["test_strategy"] = {"recommendation": "Consider Submitting"}
        r = check(_ctx(fit))
        assert r.passed

    def test_fails_on_submit(self):
        """The canonical regression: profile has no scores but the
        algorithm still says 'Submit'."""
        import fit_assertions
        check = fit_assertions.test_strategy_not_submit_when_no_scores()
        fit = _good_fit()
        fit["test_strategy"] = {"recommendation": "Submit"}
        r = check(_ctx(fit))
        assert not r.passed
        assert "Submit" in (r.message or "")
        assert "no SAT" in (r.message or "") or "no ACT" in (r.message or "")

    def test_fails_when_path_missing(self):
        import fit_assertions
        check = fit_assertions.test_strategy_not_submit_when_no_scores()
        fit = _good_fit()
        fit["test_strategy"] = {}
        r = check(_ctx(fit))
        assert not r.passed
