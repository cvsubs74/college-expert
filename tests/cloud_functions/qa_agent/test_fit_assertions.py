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
