"""
Tests for coverage.py — "what end-to-end journeys is the QA agent
actually validating today?"

Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.

build_coverage(runs) walks recent runs, collects PASSING scenarios,
groups them by their `surfaces_covered` tuple, and emits one row per
distinct end-to-end journey.

The output answers "what business journeys does the QA agent verify
work today" — it's the positive counterpart to surface health and
the resolved-issues card.
"""

from __future__ import annotations

import pytest


# ---- Helpers ---------------------------------------------------------------


def _scen(scenario_id, surfaces, *, passed=True, verified_at="2026-05-04T04:00Z"):
    return {
        "scenario_id": scenario_id,
        "passed": passed,
        "surfaces_covered": list(surfaces),
        "started_at": verified_at,
    }


def _run(run_id, scenarios, *, started_at="2026-05-04T04:00:00+00:00"):
    return {
        "run_id": run_id,
        "started_at": started_at,
        "scenarios": scenarios,
    }


# ---- build_coverage --------------------------------------------------------


class TestBuildCoverage:
    def test_returns_top_level_shape(self):
        import coverage
        result = coverage.build_coverage([])
        assert "journeys" in result
        assert "total_journeys" in result
        assert isinstance(result["journeys"], list)

    def test_groups_passing_scenarios_by_surfaces_tuple(self):
        """Two scenarios touching the same surfaces collapse into one
        journey; their scenario_ids both appear in the journey's list."""
        import coverage
        runs = [
            _run("r1", [
                _scen("junior_spring_5school", ["profile", "college_list", "roadmap"]),
                _scen("senior_fall_application_crunch", ["profile", "college_list", "roadmap"]),
            ]),
        ]
        result = coverage.build_coverage(runs)
        assert result["total_journeys"] == 1
        journey = result["journeys"][0]
        assert journey["surfaces"] == ["college_list", "profile", "roadmap"]  # sorted
        ids = [s["id"] for s in journey["scenarios"]]
        assert "junior_spring_5school" in ids
        assert "senior_fall_application_crunch" in ids

    def test_distinct_surfaces_make_distinct_journeys(self):
        """Two scenarios touching DIFFERENT surface sets produce TWO
        journeys."""
        import coverage
        runs = [
            _run("r1", [
                _scen("a", ["profile", "college_list"]),
                _scen("b", ["profile", "roadmap"]),
            ]),
        ]
        result = coverage.build_coverage(runs)
        assert result["total_journeys"] == 2
        surfaces_seen = sorted(j["surfaces"] for j in result["journeys"])
        assert surfaces_seen == [
            ["college_list", "profile"],
            ["profile", "roadmap"],
        ]

    def test_failing_scenarios_excluded(self):
        """A failing scenario should NOT appear in the validated-coverage
        list — coverage is the GOOD-news view. (Failures show up in
        the resolved-issues card if they're later fixed.)"""
        import coverage
        runs = [
            _run("r1", [
                _scen("good", ["profile"], passed=True),
                _scen("bad", ["roadmap"], passed=False),
            ]),
        ]
        result = coverage.build_coverage(runs)
        # Only the profile-only journey should appear (from the good scenario).
        assert result["total_journeys"] == 1
        assert result["journeys"][0]["surfaces"] == ["profile"]

    def test_verified_count_aggregates_across_runs(self):
        """Same scenario in 5 runs → verified_count == 5 for that journey
        (not 5 separate journeys)."""
        import coverage
        runs = [
            _run(f"r{i}", [_scen("a", ["profile"])])
            for i in range(5)
        ]
        result = coverage.build_coverage(runs)
        assert result["total_journeys"] == 1
        assert result["journeys"][0]["verified_count"] == 5

    def test_scenarios_listed_with_most_recent_verified_at(self):
        """When the same scenario appears in multiple runs, the journey
        keeps the MOST RECENT verified_at so the dashboard can show
        'last verified 5 min ago'."""
        import coverage
        runs = [
            _run("r1", [_scen("a", ["profile"])],
                 started_at="2026-05-04T04:00:00+00:00"),
            _run("r2", [_scen("a", ["profile"])],
                 started_at="2026-05-04T05:00:00+00:00"),
        ]
        result = coverage.build_coverage(runs)
        scen = result["journeys"][0]["scenarios"][0]
        assert scen["id"] == "a"
        assert "05:00" in scen["verified_at"]  # most recent

    def test_journey_has_human_summary(self):
        """Each journey should carry a short plain-English summary so
        the dashboard doesn't have to render bare surface names."""
        import coverage
        runs = [_run("r1", [_scen("a", ["profile", "college_list", "roadmap"])])]
        result = coverage.build_coverage(runs)
        summary = result["journeys"][0]["summary"]
        assert isinstance(summary, str) and summary
        # Should mention something recognisable.
        assert "profile" in summary.lower() or "college" in summary.lower() or "roadmap" in summary.lower()

    def test_journey_id_is_stable_across_runs(self):
        """The journey id should be a deterministic function of the
        surfaces tuple — important so the frontend can keyByID + the
        backend can reference it later without leaking implementation."""
        import coverage
        runs1 = [_run("r1", [_scen("a", ["profile", "college_list"])])]
        runs2 = [_run("r2", [_scen("b", ["college_list", "profile"])])]  # reordered
        j1 = coverage.build_coverage(runs1)["journeys"][0]
        j2 = coverage.build_coverage(runs2)["journeys"][0]
        assert j1["id"] == j2["id"]

    def test_empty_runs_returns_empty_journeys(self):
        import coverage
        result = coverage.build_coverage([])
        assert result["total_journeys"] == 0
        assert result["journeys"] == []

    def test_runs_with_no_surfaces_covered_skipped(self):
        """Legacy runs without `surfaces_covered` on scenarios should
        not crash — they just don't contribute to coverage."""
        import coverage
        runs = [
            _run("r1", [
                {"scenario_id": "legacy", "passed": True},  # no surfaces_covered
                _scen("modern", ["profile"]),
            ]),
        ]
        result = coverage.build_coverage(runs)
        assert result["total_journeys"] == 1
        assert result["journeys"][0]["surfaces"] == ["profile"]

    def test_journey_caps_listed_scenarios(self):
        """A journey covered by 50 distinct scenarios shouldn't dump all
        50 in the response — cap at a sensible number for the UI."""
        import coverage
        runs = []
        for i in range(50):
            runs.append(_run(f"r{i}", [_scen(f"scen_{i}", ["profile"])]))
        result = coverage.build_coverage(runs)
        scenarios_listed = result["journeys"][0]["scenarios"]
        assert len(scenarios_listed) <= 10
        # verified_count still reflects ALL runs even when scenarios is capped.
        assert result["journeys"][0]["verified_count"] == 50

    def test_journeys_sorted_by_verified_count_desc(self):
        """Most-validated journeys appear first."""
        import coverage
        runs = (
            [_run(f"r_a_{i}", [_scen("a", ["profile"])]) for i in range(5)]
            + [_run("r_b_1", [_scen("b", ["roadmap"])])]
        )
        result = coverage.build_coverage(runs)
        assert result["journeys"][0]["verified_count"] >= result["journeys"][1]["verified_count"]


# ---- validated_features ---------------------------------------------------
#
# In addition to journey-level grouping, the dashboard wants a
# feature-level breakdown: every distinct "tests" bullet across recent
# passing scenarios, with a count of how many times the QA agent has
# verified that specific behavior.
#
# Each scenario carries a `tests` field — 3-5 plain-English bullets like
# "Resolver picks junior_spring template" or "UC group task covers all
# UCs". Aggregating these gives "the full list of features verified
# successfully" the user is asking for.


def _scen_with_tests(scenario_id, surfaces, tests, *, passed=True,
                     verified_at="2026-05-04T04:00Z"):
    s = _scen(scenario_id, surfaces, passed=passed, verified_at=verified_at)
    s["tests"] = list(tests)
    return s


class TestValidatedFeatures:
    def test_top_level_includes_validated_features_key(self):
        import coverage
        result = coverage.build_coverage([])
        assert "validated_features" in result
        assert "total_features" in result
        assert isinstance(result["validated_features"], list)

    def test_aggregates_test_bullets_across_passing_scenarios(self):
        import coverage
        runs = [
            _run("r1", [
                _scen_with_tests("scen_a", ["profile"], [
                    "Resolver picks junior_spring template",
                    "5 colleges added cleanly",
                ]),
            ]),
            _run("r2", [
                _scen_with_tests("scen_b", ["roadmap"], [
                    "Resolver picks junior_spring template",  # repeat
                    "UC group task covers all UCs",
                ]),
            ]),
        ]
        result = coverage.build_coverage(runs)
        # 3 unique features in total
        assert result["total_features"] == 3
        # The repeated bullet has count 2; others count 1.
        by_text = {f["text"]: f["count"] for f in result["validated_features"]}
        assert by_text.get("Resolver picks junior_spring template") == 2
        assert by_text.get("5 colleges added cleanly") == 1
        assert by_text.get("UC group task covers all UCs") == 1

    def test_excludes_features_from_failing_scenarios(self):
        """A failing scenario's `tests` bullets aren't validated — leave
        them out so the dashboard doesn't claim things work that don't."""
        import coverage
        runs = [
            _run("r1", [
                _scen_with_tests("good", ["profile"], ["A works", "B works"]),
                _scen_with_tests("bad", ["roadmap"], ["C breaks"], passed=False),
            ]),
        ]
        result = coverage.build_coverage(runs)
        feature_texts = {f["text"] for f in result["validated_features"]}
        assert "A works" in feature_texts
        assert "B works" in feature_texts
        assert "C breaks" not in feature_texts

    def test_features_sorted_by_count_desc(self):
        import coverage
        runs = (
            [_run(f"r{i}", [_scen_with_tests("a", ["p"], ["heavy_feature"])])
             for i in range(5)]
            + [_run("r_x", [_scen_with_tests("b", ["p"], ["light_feature"])])]
        )
        result = coverage.build_coverage(runs)
        first = result["validated_features"][0]
        assert first["text"] == "heavy_feature"
        assert first["count"] == 5

    def test_caps_features_for_dashboard_size(self):
        """A long tail of features shouldn't dump 100 entries — cap at
        a sensible number for the UI."""
        import coverage
        runs = []
        for i in range(40):
            runs.append(_run(f"r{i}", [
                _scen_with_tests(f"s{i}", ["p"], [f"feature_{i}"]),
            ]))
        result = coverage.build_coverage(runs)
        # All 40 are in total_features, but the rendered list is capped.
        assert result["total_features"] == 40
        assert len(result["validated_features"]) <= 20

    def test_empty_when_no_passing_scenarios_have_tests(self):
        import coverage
        runs = [_run("r1", [_scen("a", ["profile"])])]  # no tests bullets
        result = coverage.build_coverage(runs)
        assert result["validated_features"] == []
        assert result["total_features"] == 0

    def test_normalizes_whitespace_when_aggregating(self):
        """'Foo bar.' and ' foo bar. ' should count as the same feature
        — otherwise minor LLM-output inconsistencies fragment the list."""
        import coverage
        runs = [
            _run("r1", [
                _scen_with_tests("a", ["p"], ["Resolver picks junior_spring"]),
            ]),
            _run("r2", [
                _scen_with_tests("b", ["p"], ["  Resolver picks junior_spring  "]),
            ]),
        ]
        result = coverage.build_coverage(runs)
        assert result["total_features"] == 1
        assert result["validated_features"][0]["count"] == 2


# ---- universities_tested + universities_untested -------------------------
# User feedback: "We should be able to track the exact universities we
# are using in these scenarios". Aggregation walks every passing
# scenario's `colleges_template` field so the chat + the new
# UniversitiesCard can answer "which schools have been tested?".


def _scen_with_colleges(scenario_id, surfaces, colleges, *, passed=True,
                        verified_at="2026-05-04T04:00:00+00:00"):
    s = _scen(scenario_id, surfaces, passed=passed, verified_at=verified_at)
    s["colleges_template"] = list(colleges)
    return s


class TestUniversitiesTested:
    def test_top_level_keys_present(self):
        import coverage
        result = coverage.build_coverage([])
        assert "universities_tested" in result
        assert "total_universities_tested" in result
        # universities_untested + allowlist_size are populated when
        # an allowlist is loadable; on the test path that may be empty.
        assert "universities_untested" in result

    def test_aggregates_colleges_across_passing_scenarios(self):
        import coverage
        runs = [
            _run("r1", [
                _scen_with_colleges("a", ["profile"], ["mit", "stanford"]),
            ]),
            _run("r2", [
                _scen_with_colleges("a", ["profile"], ["mit", "stanford"]),
                _scen_with_colleges("b", ["roadmap"], ["uc_berkeley"]),
            ]),
        ]
        result = coverage.build_coverage(runs)
        # 3 unique universities
        assert result["total_universities_tested"] == 3
        by_id = {u["id"]: u["count"] for u in result["universities_tested"]}
        assert by_id == {"mit": 2, "stanford": 2, "uc_berkeley": 1}

    def test_excludes_failing_scenarios(self):
        import coverage
        runs = [
            _run("r1", [
                _scen_with_colleges("good", ["profile"], ["mit"]),
                _scen_with_colleges("bad", ["roadmap"], ["yale"], passed=False),
            ]),
        ]
        result = coverage.build_coverage(runs)
        ids = {u["id"] for u in result["universities_tested"]}
        assert "mit" in ids
        assert "yale" not in ids

    def test_sorts_by_count_desc(self):
        import coverage
        runs = (
            [_run(f"r{i}", [_scen_with_colleges("a", ["p"], ["mit"])]) for i in range(5)]
            + [_run("r_x", [_scen_with_colleges("b", ["p"], ["yale"])])]
        )
        result = coverage.build_coverage(runs)
        assert result["universities_tested"][0]["id"] == "mit"
        assert result["universities_tested"][0]["count"] == 5

    def test_records_last_tested_at_per_university(self):
        """Most recent test timestamp per university wins so the
        dashboard can show 'last tested 5m ago'."""
        import coverage
        runs = [
            _run("r1", [_scen_with_colleges("a", ["p"], ["mit"])],
                 started_at="2026-05-04T04:00:00+00:00"),
            _run("r2", [_scen_with_colleges("a", ["p"], ["mit"])],
                 started_at="2026-05-04T05:00:00+00:00"),
        ]
        result = coverage.build_coverage(runs)
        mit = next(u for u in result["universities_tested"] if u["id"] == "mit")
        assert "05:00" in mit["last_tested_at"]

    def test_universities_untested_when_allowlist_provided(self):
        """The set difference between the allowlist and tested set is
        what the dashboard renders as 'next to test' candidates."""
        import coverage
        runs = [_run("r1", [_scen_with_colleges("a", ["p"], ["mit"])])]
        allowlist = ["mit", "stanford", "yale", "princeton"]
        result = coverage.build_coverage(runs, colleges_allowlist=allowlist)
        assert result["allowlist_size"] == 4
        assert result["total_universities_tested"] == 1
        # untested = allowlist - tested
        untested = set(result["universities_untested"])
        assert untested == {"stanford", "yale", "princeton"}

    def test_universities_untested_capped(self):
        """Don't dump 100 untested ids into the response."""
        import coverage
        allowlist = [f"uni_{i}" for i in range(50)]
        runs = []  # nothing tested
        result = coverage.build_coverage(runs, colleges_allowlist=allowlist)
        assert result["allowlist_size"] == 50
        # Cap the rendered list — total still shows the real count.
        assert len(result["universities_untested"]) <= 25

    def test_handles_legacy_scenarios_without_colleges_template(self):
        """Old runs that don't carry colleges_template shouldn't crash."""
        import coverage
        runs = [_run("r1", [
            {"scenario_id": "legacy", "passed": True,
             "surfaces_covered": ["profile"]},  # no colleges_template
            _scen_with_colleges("modern", ["profile"], ["mit"]),
        ])]
        result = coverage.build_coverage(runs)
        # Only the modern scenario contributes.
        assert result["total_universities_tested"] == 1
        assert result["universities_tested"][0]["id"] == "mit"
