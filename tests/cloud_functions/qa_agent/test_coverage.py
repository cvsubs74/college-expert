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
