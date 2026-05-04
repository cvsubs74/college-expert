"""
Tests for resolved_issues.py — "what bugs did the QA agent catch and
when were they fixed?"

Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.

build_resolved_issues(runs) walks runs in chronological order; for each
(scenario_id, step_name) pair, it tracks the most recent failure and
emits one entry whenever the next run shows that pair PASSING. This
gives the dashboard a "value story" — bugs the agent caught that were
later fixed.
"""

from __future__ import annotations


def _scen(scenario_id, *, passed, failing_steps=None):
    """Build a scenario record. failing_steps is [(step_name, msg)] for
    failed runs; ignored when passed=True."""
    s = {"scenario_id": scenario_id, "passed": passed, "steps": []}
    for name, msg in (failing_steps or []):
        s["steps"].append({
            "name": name,
            "passed": False,
            "assertions": [{"name": "x", "passed": False, "message": msg}],
        })
    return s


def _run(run_id, scenarios, *, started_at):
    return {
        "run_id": run_id,
        "started_at": started_at,
        "scenarios": scenarios,
    }


# ---- build_resolved_issues -------------------------------------------------


class TestBuildResolvedIssues:
    def test_returns_top_level_shape(self):
        import resolved_issues
        result = resolved_issues.build_resolved_issues([])
        assert "fixes" in result
        assert "total_fixes" in result
        assert "lookback_runs" in result

    def test_detects_fail_to_pass_transition(self):
        """A scenario that failed in run A and passed in the next run B
        produces ONE fix entry pointing at B as the fix run."""
        import resolved_issues
        runs = [
            # Most-recent first (matches firestore_store.list_recent_runs).
            _run("rB", [_scen("scen_a", passed=True)],
                 started_at="2026-05-04T05:00:00+00:00"),
            _run("rA", [_scen("scen_a", passed=False, failing_steps=[
                ("roadmap_generate", "got 'sophomore_spring'")
            ])], started_at="2026-05-04T04:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        assert result["total_fixes"] == 1
        fix = result["fixes"][0]
        assert fix["scenario_id"] == "scen_a"
        assert fix["step_name"] == "roadmap_generate"
        assert "sophomore_spring" in fix["failing_message"]
        assert fix["failed_at_run"] == "rA"
        assert fix["fixed_at_run"] == "rB"

    def test_no_fix_when_scenario_was_never_failing(self):
        """A scenario that passed in run A and run B is NOT a fix —
        it never failed in the first place."""
        import resolved_issues
        runs = [
            _run("rB", [_scen("scen_a", passed=True)],
                 started_at="2026-05-04T05:00:00+00:00"),
            _run("rA", [_scen("scen_a", passed=True)],
                 started_at="2026-05-04T04:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        assert result["total_fixes"] == 0

    def test_no_fix_when_still_failing(self):
        """A scenario that failed in two consecutive runs is not a fix —
        nothing's resolved yet."""
        import resolved_issues
        runs = [
            _run("rB", [_scen("scen_a", passed=False, failing_steps=[
                ("step_x", "still broken"),
            ])], started_at="2026-05-04T05:00:00+00:00"),
            _run("rA", [_scen("scen_a", passed=False, failing_steps=[
                ("step_x", "broken"),
            ])], started_at="2026-05-04T04:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        assert result["total_fixes"] == 0

    def test_multiple_fixes_in_history(self):
        """Two distinct scenarios both transition fail → pass; both
        appear in the fixes list."""
        import resolved_issues
        runs = [
            _run("r3", [
                _scen("scen_a", passed=True),
                _scen("scen_b", passed=True),
            ], started_at="2026-05-04T05:00:00+00:00"),
            _run("r2", [
                _scen("scen_a", passed=False, failing_steps=[("s1", "e1")]),
                _scen("scen_b", passed=False, failing_steps=[("s2", "e2")]),
            ], started_at="2026-05-04T04:00:00+00:00"),
            _run("r1", [
                _scen("scen_a", passed=False, failing_steps=[("s1", "e1")]),
            ], started_at="2026-05-04T03:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        assert result["total_fixes"] == 2
        scen_ids = {f["scenario_id"] for f in result["fixes"]}
        assert scen_ids == {"scen_a", "scen_b"}

    def test_fixes_sorted_most_recent_first(self):
        """Most recently fixed bug appears first."""
        import resolved_issues
        runs = [
            _run("r4", [_scen("scen_a", passed=True)],
                 started_at="2026-05-04T07:00:00+00:00"),
            _run("r3", [
                _scen("scen_a", passed=False, failing_steps=[("s", "e")]),
                _scen("scen_b", passed=True),
            ], started_at="2026-05-04T06:00:00+00:00"),
            _run("r2", [_scen("scen_b", passed=False, failing_steps=[("s", "e")])],
                 started_at="2026-05-04T05:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        # scen_a was fixed in r4 (newer); scen_b in r3 (older).
        assert result["fixes"][0]["scenario_id"] == "scen_a"
        assert result["fixes"][1]["scenario_id"] == "scen_b"

    def test_fix_carries_failing_assertion_message(self):
        """The fix entry preserves the LAST failing assertion message
        before the fix as evidence of what was broken."""
        import resolved_issues
        runs = [
            _run("r2", [_scen("scen_a", passed=True)],
                 started_at="2026-05-04T05:00:00+00:00"),
            _run("r1", [_scen("scen_a", passed=False, failing_steps=[
                ("roadmap_generate",
                 "metadata.template_used=='junior_fall': got 'sophomore_spring'"),
            ])], started_at="2026-05-04T04:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        msg = result["fixes"][0]["failing_message"]
        assert "junior_fall" in msg
        assert "sophomore_spring" in msg

    def test_capped_at_recent_fixes(self):
        """A long stream of fixes shouldn't dump 100 entries — cap at 10
        so the dashboard stays tight."""
        import resolved_issues
        runs = []
        # 15 alternating fix transitions for 15 distinct scenarios.
        # Build oldest-first then reverse so most-recent is first.
        for i in range(15):
            runs.append(_run(f"pass_{i}", [_scen(f"scen_{i}", passed=True)],
                             started_at=f"2026-05-04T{i:02d}:30:00+00:00"))
            runs.append(_run(f"fail_{i}", [_scen(f"scen_{i}", passed=False,
                             failing_steps=[("s", "e")])],
                             started_at=f"2026-05-04T{i:02d}:00:00+00:00"))
        runs = list(reversed(runs))  # most-recent first
        result = resolved_issues.build_resolved_issues(runs)
        # 15 fixes happened; we cap at 10.
        assert result["total_fixes"] >= 10
        assert len(result["fixes"]) <= 10

    def test_only_counts_fix_for_same_step_pair(self):
        """If a scenario had step_x failing previously and now step_y is
        failing (different bug), and step_x is now passing, that's still
        a fix for step_x — not 'no transition'."""
        import resolved_issues
        runs = [
            _run("r2", [_scen("scen_a", passed=False, failing_steps=[
                ("step_y", "different bug")
            ])], started_at="2026-05-04T05:00:00+00:00"),
            _run("r1", [_scen("scen_a", passed=False, failing_steps=[
                ("step_x", "old bug")
            ])], started_at="2026-05-04T04:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        # step_x is no longer failing — that's a fix for step_x.
        assert result["total_fixes"] == 1
        fix = result["fixes"][0]
        assert fix["step_name"] == "step_x"
        assert "old bug" in fix["failing_message"]

    def test_empty_runs(self):
        import resolved_issues
        result = resolved_issues.build_resolved_issues([])
        assert result["total_fixes"] == 0
        assert result["fixes"] == []

    def test_fixed_at_time_matches_run_started_at(self):
        """The fix's `fixed_at_time` should match the passing run's
        started_at — that's when the operator can claim the fix landed."""
        import resolved_issues
        runs = [
            _run("rB", [_scen("scen_a", passed=True)],
                 started_at="2026-05-04T05:00:00+00:00"),
            _run("rA", [_scen("scen_a", passed=False, failing_steps=[
                ("step", "msg")
            ])], started_at="2026-05-04T04:00:00+00:00"),
        ]
        result = resolved_issues.build_resolved_issues(runs)
        assert result["fixes"][0]["fixed_at_time"] == "2026-05-04T05:00:00+00:00"
