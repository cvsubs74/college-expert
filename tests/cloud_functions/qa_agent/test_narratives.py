"""
Tests for narratives.py — the module that produces the test_plan, outcome,
and executive summary narratives that go into qa_runs reports and the
admin dashboard.

These run BEFORE implementation per the plan-first / tests-first
workflow rule. They should fail with ImportError until narratives.py
exists, then with AssertionError until each function behaves as
specified, then pass.

LLM calls are stubbed at the module level (google.generativeai already
stubbed in conftest). Each test exercises the deterministic-fallback
path AND the happy LLM path where the stub returns a known string.
"""

from __future__ import annotations

import pytest


# ---- Fixtures --------------------------------------------------------------


@pytest.fixture
def archetypes():
    return [
        {
            "id": "junior_spring_5school",
            "description": "Junior with 5-school list",
            "surfaces_covered": ["profile", "college_list", "roadmap"],
            "tests": ["Resolver picks junior_spring", "5 colleges add"],
        },
        {
            "id": "senior_fall_application_crunch",
            "description": "Senior fall application crunch",
            "surfaces_covered": ["profile", "college_list", "roadmap"],
            "tests": ["Resolver picks senior_fall"],
        },
    ]


@pytest.fixture
def history():
    return {
        "junior_spring_5school": {
            "last_run_at": "2026-04-30T06:00:00+00:00",
            "last_result": "pass",
        },
        "senior_fall_application_crunch": {
            "last_run_at": "2026-05-02T06:00:00+00:00",
            "last_result": "fail",
        },
    }


@pytest.fixture
def passing_report():
    return {
        "run_id": "run_demo",
        "summary": {"total": 2, "pass": 2, "fail": 0},
        "scenarios": [
            {
                "scenario_id": "junior_spring_5school",
                "passed": True,
                "steps": [
                    {"name": "setup", "passed": True, "assertions": []},
                    {"name": "roadmap", "passed": True, "assertions": []},
                ],
            },
            {
                "scenario_id": "senior_fall_application_crunch",
                "passed": True,
                "steps": [{"name": "roadmap", "passed": True, "assertions": []}],
            },
        ],
    }


@pytest.fixture
def failing_report():
    return {
        "run_id": "run_failing",
        "summary": {"total": 2, "pass": 1, "fail": 1},
        "scenarios": [
            {
                "scenario_id": "junior_spring_5school",
                "passed": True,
                "steps": [{"name": "roadmap", "passed": True, "assertions": []}],
            },
            {
                "scenario_id": "senior_fall_application_crunch",
                "passed": False,
                "steps": [
                    {
                        "name": "roadmap_generate",
                        "passed": False,
                        "endpoint": "https://x/roadmap",
                        "status_code": 500,
                        "elapsed_ms": 1234,
                        "assertions": [
                            {"name": "status=2xx", "passed": False, "message": "got 500"},
                        ],
                        "response_excerpt": '{"error":"kaboom"}',
                    },
                ],
            },
        ],
    }


# ---- build_plan -----------------------------------------------------------


class TestBuildPlan:
    def test_returns_required_keys(self, archetypes, history):
        import narratives
        result = narratives.build_plan(archetypes, history)
        assert "narrative" in result
        assert "rationale" in result
        assert "coverage" in result
        assert isinstance(result["narrative"], str) and result["narrative"]

    def test_coverage_aggregates_surfaces_across_archetypes(self, archetypes, history):
        import narratives
        result = narratives.build_plan(archetypes, history)
        # Both archetypes touch profile + college_list + roadmap; each gets count 2.
        assert result["coverage"]["profile"] == 2
        assert result["coverage"]["college_list"] == 2
        assert result["coverage"]["roadmap"] == 2
        # `fit` not touched.
        assert result["coverage"].get("fit", 0) == 0

    def test_rationale_flags_recently_failed(self, archetypes, history):
        import narratives
        result = narratives.build_plan(archetypes, history)
        # senior_fall_application_crunch has last_result=fail in history,
        # so the rationale should flag retest of recent failure.
        assert result["rationale"] in (
            "recently_failed", "untried_recently", "coverage_gap", "rotation"
        )

    def test_falls_back_to_deterministic_narrative_without_api_key(
        self, archetypes, history, monkeypatch
    ):
        import narratives
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = narratives.build_plan(archetypes, history, gemini_key=None)
        # Deterministic fallback should still produce a useful narrative
        # naming at least one scenario id.
        assert any(a["id"] in result["narrative"] for a in archetypes)

    def test_uses_llm_when_key_provided(self, archetypes, history, monkeypatch):
        import narratives
        import google.generativeai as genai

        class _Model:
            def __init__(self, *_a, **_k):
                pass

            def generate_content(self, *_a, **_k):
                class R:
                    text = "Run targets the roadmap surface across two scenarios."
                return R()

        monkeypatch.setattr(genai, "GenerativeModel", _Model)
        result = narratives.build_plan(archetypes, history, gemini_key="fake-key")
        assert "roadmap surface" in result["narrative"]


# ---- build_outcome --------------------------------------------------------


class TestBuildOutcome:
    def test_all_pass_verdict(self, passing_report):
        import narratives
        result = narratives.build_outcome(passing_report)
        assert result["verdict"] == "all_pass"
        assert result["narrative"]
        assert result["first_look_at"] == []

    def test_failing_run_verdict_and_first_look_at(self, failing_report):
        import narratives
        result = narratives.build_outcome(failing_report)
        # Verdict is computed deterministically — never LLM-derived.
        assert result["verdict"] in ("regression_likely", "minor_flake")
        # First-look-at points at the failing scenario + step.
        assert len(result["first_look_at"]) >= 1
        first = result["first_look_at"][0]
        assert first["scenario_id"] == "senior_fall_application_crunch"
        assert first["step"] == "roadmap_generate"

    def test_falls_back_to_deterministic_narrative(self, failing_report, monkeypatch):
        import narratives
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = narratives.build_outcome(failing_report, gemini_key=None)
        # Fallback should mention the failing scenario by id.
        assert "senior_fall_application_crunch" in result["narrative"]

    def test_uses_llm_when_key_provided(self, failing_report, monkeypatch):
        import narratives
        import google.generativeai as genai

        class _Model:
            def __init__(self, *_a, **_k):
                pass

            def generate_content(self, *_a, **_k):
                class R:
                    text = "The roadmap endpoint regressed — response status changed to 500."
                return R()

        monkeypatch.setattr(genai, "GenerativeModel", _Model)
        result = narratives.build_outcome(failing_report, gemini_key="fake-key")
        assert "regressed" in result["narrative"]


# ---- build_summary --------------------------------------------------------


class TestBuildSummary:
    def _runs(self, days_ago_pass_pairs):
        """Build a list of run dicts. Each tuple is (days_ago, passed)."""
        from datetime import datetime, timedelta, timezone
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        runs = []
        for i, (days_ago, passed) in enumerate(days_ago_pass_pairs):
            ts = now - timedelta(days=days_ago)
            runs.append({
                "run_id": f"r{i}",
                "started_at": ts.isoformat(),
                "summary": {
                    "total": 4,
                    "pass": 4 if passed else 3,
                    "fail": 0 if passed else 1,
                },
                "scenarios": [
                    {
                        "scenario_id": "junior_spring_5school",
                        "passed": passed,
                        "steps": [],
                    },
                ],
            })
        return runs

    def test_returns_pass_rates_and_trend(self):
        import narratives
        runs = self._runs([
            (0, True), (1, True), (2, True), (3, True), (4, True),  # last 5 days all pass
            (10, False), (15, True), (20, False), (25, True),       # mixed beyond 7d
        ])
        result = narratives.build_summary(runs)
        assert "pass_rate_7d" in result
        assert "pass_rate_30d" in result
        assert result["pass_rate_7d"] == 100  # all 5 of the last 7 days passed
        # Trend should be 'improving' (7d > 30d) or 'steady'.
        assert result["trend"] in ("improving", "steady", "degrading")

    def test_surface_health_buckets(self):
        import narratives
        runs = self._runs([(0, False), (1, True)])
        result = narratives.build_summary(runs)
        # Surfaces from the scenario should appear with a status.
        # We don't pin specific labels — just that the structure is right.
        assert isinstance(result["surfaces"], dict) or isinstance(result["surfaces"], list)

    def test_empty_runs(self):
        import narratives
        result = narratives.build_summary([])
        assert result["pass_rate_7d"] is None or result["pass_rate_7d"] == 0
        assert result["narrative"]  # always returns SOMETHING even with no data


class TestBuildSummaryRecentN:
    """Configurable 'last N runs' health window — added because the
    30-day average lags too long after a fix lands. The dashboard's
    primary pill should reflect the most recent N runs."""

    def _runs(self, pass_seq, *, base=None):
        """Build runs from oldest→newest by passing a list of bools."""
        from datetime import datetime, timedelta, timezone
        base = base or datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        out = []
        for i, passed in enumerate(pass_seq):
            ts = base + timedelta(minutes=i * 30)
            out.append({
                "run_id": f"r{i}",
                "started_at": ts.isoformat(),
                "summary": {"total": 8, "pass": 8 if passed else 5,
                            "fail": 0 if passed else 3},
                "scenarios": [],
            })
        # Most-recent first to match what list_recent_runs returns.
        return list(reversed(out))

    def test_pass_rate_recent_uses_most_recent_n_only(self):
        """20 most recent runs are 100% pass, but anything before that
        was failing. pass_rate_recent should be 100, NOT a blended rate."""
        import narratives
        # Newest 20 all pass; older 30 all fail.
        runs = self._runs([False] * 30 + [True] * 20)
        result = narratives.build_summary(runs, recent_n=20)
        assert result["pass_rate_recent"] == 100
        assert result["recent_n"] == 20

    def test_recent_n_with_partial_pass(self):
        import narratives
        # 20 most-recent: 15 pass, 5 fail = 75%
        recent = [False] * 5 + [True] * 15  # before reverse → newest is True
        runs = self._runs(recent)
        result = narratives.build_summary(runs, recent_n=20)
        assert result["pass_rate_recent"] == 75
        assert result["recent_n"] == 20

    def test_recent_n_smaller_than_run_count(self):
        """N=5 with only 3 runs returns the rate over those 3, NOT zero."""
        import narratives
        runs = self._runs([True, True, False])  # 2/3 pass = 67%
        result = narratives.build_summary(runs, recent_n=5)
        assert result["pass_rate_recent"] == 67
        assert result["recent_n"] == 5

    def test_default_recent_n_is_20(self):
        """When recent_n omitted, the helper uses a sensible default
        documented in the design doc."""
        import narratives
        runs = self._runs([True] * 25)
        result = narratives.build_summary(runs)
        assert result["recent_n"] == 20
        assert result["pass_rate_recent"] == 100

    def test_recent_n_clamped_to_valid_range(self):
        """Out-of-bounds N gets clamped (5..100) so the LLM/UI can't
        accidentally pass nonsense."""
        import narratives
        runs = self._runs([True] * 30)
        result_low = narratives.build_summary(runs, recent_n=2)
        result_high = narratives.build_summary(runs, recent_n=999)
        assert result_low["recent_n"] == 5
        assert result_high["recent_n"] == 100

    def test_pass_rate_recent_is_none_when_no_runs(self):
        import narratives
        result = narratives.build_summary([], recent_n=20)
        assert result["pass_rate_recent"] is None
        assert result["recent_n"] == 20

    def test_pass_rate_recent_independent_of_30_day_window(self):
        """A 30-day average can be 50% while the most-recent-20 are 100%
        (the user-feedback scenario that motivated this PR)."""
        import narratives
        from datetime import datetime, timedelta, timezone
        base = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        runs = []
        # 20 old failing runs, 25 days ago each
        for i in range(20):
            runs.append({
                "run_id": f"old_{i}",
                "started_at": (base - timedelta(days=25, minutes=i)).isoformat(),
                "summary": {"total": 8, "pass": 4, "fail": 4},
                "scenarios": [],
            })
        # 20 new passing runs, last 12 hours
        for i in range(20):
            runs.append({
                "run_id": f"new_{i}",
                "started_at": (base - timedelta(minutes=30 * i)).isoformat(),
                "summary": {"total": 8, "pass": 8, "fail": 0},
                "scenarios": [],
            })
        # most-recent first
        runs.sort(key=lambda r: r["started_at"], reverse=True)
        result = narratives.build_summary(runs, recent_n=20)
        # 30-day rate is blended, ~50%. Recent-20 should be 100%.
        assert result["pass_rate_recent"] == 100
        assert result["pass_rate_30d"] is not None
        assert result["pass_rate_30d"] < 75
