"""
Regression tests for fit_computation.py's fallback path.

Bug surfaced 2026-05-04 by the QA agent's fit_assertions:
when Gemini returns 503 UNAVAILABLE, fit_computation falls back to
a hardcoded {"fit_category": ..., "match_percentage": 50} response.
But for fit_category=TARGET (the band a 25-40% acceptance school
falls into), the algorithm's own contract requires match_percentage
in [55, 74] — so the fallback's (TARGET, 50) pair is internally
inconsistent and trips the QA agent's match_percentage_aligns_with_category
assertion.

Production logs:
  [FIT_COMP_ERROR] University of Washington: 503 UNAVAILABLE
  [FIT_COMP_ERROR] University of Florida: 503 UNAVAILABLE
  → both returned as TARGET @ 50%, violating the TARGET band [55, 74]

Fix: the fallback's match_percentage must align with whichever
category it picks. Test that contract here.
"""

from __future__ import annotations

import pytest


# Algorithm's own contract — must mirror fit_computation.py's
# post-processing match-% range alignment, otherwise the fallback
# violates what the system enforces for LLM-returned responses.
_BANDS = {
    "SUPER_REACH": (0, 34),
    "REACH":       (35, 54),
    "TARGET":      (55, 74),
    "SAFETY":      (75, 100),
}


class TestFallbackMatchPercentageAlignsWithCategory:
    """For every selectivity tier, the fallback response's
    match_percentage must fall inside the band declared for the
    fallback category. This is the QA agent's
    match_percentage_aligns_with_category invariant — the system
    must satisfy its own contract on the fallback path too."""

    @pytest.mark.parametrize("acceptance_rate, expected_category", [
        (4.0,   "SUPER_REACH"),  # <8% bucket
        (10.0,  "REACH"),        # 8-15% bucket
        (24.2,  "TARGET"),       # 15-40% bucket (UF case)
        (39.15, "TARGET"),       # 25-40% bucket (UW case)
        (60.6,  "SAFETY"),       # >=40% bucket (Ohio State case)
    ])
    def test_match_pct_in_category_band(self, acceptance_rate, expected_category):
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=acceptance_rate,
            selectivity_tier="TEST_TIER",
            university_data={"metadata": {"official_name": "Test U"}},
        )
        assert result["fit_category"] == expected_category, (
            f"acceptance_rate={acceptance_rate}% expected category "
            f"{expected_category}, got {result['fit_category']}"
        )
        lo, hi = _BANDS[expected_category]
        mp = result["match_percentage"]
        assert lo <= mp <= hi, (
            f"{expected_category} requires match_percentage in [{lo}, {hi}], "
            f"got {mp}"
        )

    def test_returns_full_response_shape(self):
        """The fallback must produce the same top-level keys a
        successful LLM call produces, so callers don't have to
        special-case the fallback path."""
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=24.2,
            selectivity_tier="VERY_SELECTIVE",
            university_data={"metadata": {"official_name": "UF"}},
        )
        for key in ("fit_category", "match_percentage", "explanation",
                    "factors", "recommendations", "university_name",
                    "calculated_at", "selectivity_tier",
                    "acceptance_rate"):
            assert key in result, f"missing key {key!r}"

    def test_factors_have_correct_max_bounds(self):
        """The fallback's placeholder factors should still respect the
        production max bounds so the QA agent's factor_bounds_respected
        invariant doesn't trip on them."""
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=24.2,
            selectivity_tier="VERY_SELECTIVE",
            university_data={},
        )
        factors_by_name = {f["name"]: f for f in result["factors"]}
        assert factors_by_name["Academic"]["max"] == 40
        assert factors_by_name["Holistic"]["max"] == 30
        assert factors_by_name["Major Fit"]["max"] == 15
        assert factors_by_name["Selectivity"]["max"] == 5
        # And each score within bounds.
        for name, f in factors_by_name.items():
            assert 0 <= f["score"] <= f["max"], (
                f"{name}: score {f['score']} out of bounds [0, {f['max']}]"
            )

    def test_handles_missing_university_metadata(self):
        """Defensive: a university record without metadata shouldn't
        crash the fallback (the LLM-call failure path is hit precisely
        when something is wrong with the inputs)."""
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=24.2,
            selectivity_tier="VERY_SELECTIVE",
            university_data=None,
        )
        # Doesn't raise; produces a sensible default name.
        assert isinstance(result["university_name"], str)
        assert result["fit_category"] == "TARGET"


# ---- _student_has_no_scores ---------------------------------------------
# Phase 2c-2: the test_strategy override only fires when the student
# profile genuinely has no SAT/ACT, so this predicate has to be right.


class TestStudentHasNoScores:
    def test_true_for_empty_profile(self):
        from fit_computation import _student_has_no_scores
        assert _student_has_no_scores({})

    def test_true_when_score_keys_are_none_or_empty(self):
        from fit_computation import _student_has_no_scores
        assert _student_has_no_scores({
            "sat_composite": None, "sat_total": None,
            "act_composite": None, "act_score": "",
            "gpa": 3.85,
        })

    def test_false_when_sat_composite_present(self):
        from fit_computation import _student_has_no_scores
        assert not _student_has_no_scores({"sat_composite": 1450})

    def test_false_when_sat_total_present(self):
        from fit_computation import _student_has_no_scores
        assert not _student_has_no_scores({"sat_total": 1500})

    def test_false_when_act_composite_present(self):
        from fit_computation import _student_has_no_scores
        assert not _student_has_no_scores({"act_composite": 33})

    def test_false_when_only_one_score_field_set(self):
        """Even one score is enough to rule out the override."""
        from fit_computation import _student_has_no_scores
        assert not _student_has_no_scores({
            "sat_composite": None,
            "sat_total": None,
            "act_composite": 32,  # ← present
        })

    def test_false_for_non_dict_input(self):
        """Conservative: when we can't introspect the profile, don't
        apply the override (let the LLM's recommendation stand)."""
        from fit_computation import _student_has_no_scores
        assert not _student_has_no_scores(None)
        assert not _student_has_no_scores("not a dict")
        assert not _student_has_no_scores([])

    def test_zero_score_values_treated_as_no_score(self):
        """0 / "0" mean placeholder, not a real score."""
        from fit_computation import _student_has_no_scores
        assert _student_has_no_scores({
            "sat_composite": 0,
            "act_composite": "0",
        })


# ---- Fallback advisory blocks -------------------------------------------
# Bug surfaced 2026-05-04 (post-PR-#82): a fallback fit response was
# missing every advisory block the QA agent's
# required_advisory_blocks_present invariant requires. Phase 2c-2 fix
# extended the fallback to include placeholder versions of all 8
# blocks so response shape stays stable across success/fail paths.

_REQUIRED_BLOCKS = (
    "explanation", "essay_angles", "application_timeline",
    "scholarship_matches", "test_strategy", "major_strategy",
    "demonstrated_interest_tips", "red_flags_to_avoid",
    "recommendations",
)


class TestFallbackIncludesAllAdvisoryBlocks:
    @pytest.mark.parametrize("acceptance_rate", [4.0, 10.0, 24.2, 60.6])
    def test_every_required_block_present_and_non_empty(self, acceptance_rate):
        """The QA agent's required_advisory_blocks_present invariant
        checks each block exists AND is non-empty — applies to fallback
        responses too."""
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=acceptance_rate,
            selectivity_tier="TEST",
            university_data={},
        )
        for block in _REQUIRED_BLOCKS:
            assert block in result, (
                f"acceptance_rate={acceptance_rate}: missing block {block!r}"
            )
            v = result[block]
            assert v not in (None, "", [], {}), (
                f"acceptance_rate={acceptance_rate}: block {block!r} "
                f"is empty (would trip required_advisory_blocks_present)"
            )

    def test_fallback_test_strategy_is_safe_default(self):
        """The fallback's default test_strategy.recommendation should
        not be 'Submit' — Phase 2c-2's no-scores override would catch
        that for scoreless profiles, but the fallback is more
        conservative and never recommends Submit blindly."""
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=24.2,
            selectivity_tier="VERY_SELECTIVE",
            university_data={},
        )
        assert result["test_strategy"]["recommendation"] != "Submit"

    def test_fallback_essay_angles_is_a_list_of_dicts(self):
        """Frontend rendering expects essay_angles to be iterable of
        dicts — protect that shape."""
        from fit_computation import _build_fallback_fit
        result = _build_fallback_fit(
            acceptance_rate=24.2,
            selectivity_tier="VERY_SELECTIVE",
            university_data={},
        )
        assert isinstance(result["essay_angles"], list)
        assert len(result["essay_angles"]) >= 1
        for angle in result["essay_angles"]:
            assert isinstance(angle, dict)
