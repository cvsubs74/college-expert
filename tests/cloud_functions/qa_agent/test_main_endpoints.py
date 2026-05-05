"""
Unit tests for the qa_agent's HTTP entry point — focused on the
non-/run paths added for the admin dashboard:

  GET  /scenarios          — public, archetype list
  POST /suggest-cause      — LLM analysis (dedup'd; falls back if no key)
  POST /github-issue       — pre-filled issue URL builder

Plus the dual-auth gate: X-Admin-Token vs Firebase ID token + email
allowlist.

Heavy deps (firestore client, firebase_admin) are stubbed in conftest;
these tests exercise the dispatcher and helper logic in main.py.
"""

from __future__ import annotations

import importlib
import json
import urllib.parse

import pytest


@pytest.fixture
def qa_main(monkeypatch):
    """Import main fresh per test, with a known env baseline."""
    monkeypatch.setenv("QA_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("QA_ADMIN_EMAILS", "admin@example.com,qa@example.com")
    monkeypatch.setenv("QA_TEST_USER_EMAIL", "duser8531@gmail.com")
    monkeypatch.setenv("QA_TEST_USER_UID", "test-uid")
    monkeypatch.setenv("QA_GITHUB_REPO", "cvsubs74/college-expert")
    # Placeholder backend URLs so RunConfig construction in /run doesn't
    # blow up on .rstrip() of None.
    monkeypatch.setenv("PROFILE_MANAGER_URL", "https://pm.test")
    monkeypatch.setenv("COUNSELOR_AGENT_URL", "https://ca.test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("FIREBASE_WEB_API_KEY", raising=False)

    import main as qa_main_mod  # noqa: WPS433
    importlib.reload(qa_main_mod)
    # Reset the in-memory suggest cache between tests.
    qa_main_mod._SUGGESTION_CACHE.clear()
    return qa_main_mod


# ---- Fake Flask request ----------------------------------------------------


class _FakeRequest:
    def __init__(self, *, method="POST", path="/", headers=None, body=None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self._body = body or {}
        self.args = {}

    def get_json(self, silent=False):
        return self._body


def _resp_payload(resp):
    """Decode the Flask response object qa_main returns into (status, json)."""
    return resp.status_code, json.loads(resp.get_data(as_text=True))


# ---- /scenarios -------------------------------------------------------------


class TestScenariosEndpoint:
    def test_lists_every_registered_archetype(self, qa_main):
        resp = qa_main.qa_agent(_FakeRequest(method="GET", path="/scenarios"))
        status, body = _resp_payload(resp)
        assert status == 200
        assert body["success"] is True
        ids = [s["id"] for s in body["scenarios"]]
        # The 8 launch archetypes — if any are renamed, update this set.
        assert "junior_spring_5school" in ids
        assert "all_uc_only" in ids
        assert len(ids) >= 8

    def test_does_not_require_auth(self, qa_main):
        # No X-Admin-Token, no Authorization header — should still succeed.
        resp = qa_main.qa_agent(_FakeRequest(method="GET", path="/scenarios"))
        assert resp.status_code == 200


# ---- Dual auth -------------------------------------------------------------


class TestDualAuth:
    def test_admin_token_path_passes(self, qa_main):
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "nope", "scenario_id": "nope"},
        )
        resp = qa_main.qa_agent(req)
        # Auth passed; the request is served. We don't assert on the
        # body shape — that's the suggest-cause test's job.
        assert resp.status_code != 401

    def test_wrong_admin_token_returns_401(self, qa_main):
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "wrong"},
            body={},
        )
        resp = qa_main.qa_agent(req)
        assert resp.status_code == 401

    def test_no_auth_returns_401_for_protected_paths(self, qa_main):
        for path in ("/run", "/suggest-cause", "/github-issue"):
            resp = qa_main.qa_agent(_FakeRequest(method="POST", path=path, body={}))
            assert resp.status_code == 401, f"unauthenticated {path} should 401"

    def test_id_token_path_passes_when_email_allowlisted(self, qa_main, monkeypatch):
        from firebase_admin import auth as _fa
        monkeypatch.setattr(
            _fa,
            "verify_id_token",
            lambda _t: {"email": "admin@example.com"},
            raising=False,
        )
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"Authorization": "Bearer fake-id-token"},
            body={"run_id": "nope", "scenario_id": "nope"},
        )
        resp = qa_main.qa_agent(req)
        assert resp.status_code != 401

    def test_id_token_with_non_admin_email_returns_401(self, qa_main, monkeypatch):
        from firebase_admin import auth as _fa
        monkeypatch.setattr(
            _fa,
            "verify_id_token",
            lambda _t: {"email": "random@example.com"},
            raising=False,
        )
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"Authorization": "Bearer fake-id-token"},
            body={"run_id": "x", "scenario_id": "x"},
        )
        resp = qa_main.qa_agent(req)
        assert resp.status_code == 401

    def test_id_token_invalid_returns_401(self, qa_main, monkeypatch):
        from firebase_admin import auth as _fa
        def _raise(*_a, **_k):
            raise ValueError("expired token")
        monkeypatch.setattr(_fa, "verify_id_token", _raise, raising=False)
        req = _FakeRequest(
            method="POST",
            path="/run",
            headers={"Authorization": "Bearer junk"},
            body={},
        )
        resp = qa_main.qa_agent(req)
        assert resp.status_code == 401

    def test_id_token_path_initializes_firebase_admin_before_verify(
        self, qa_main, monkeypatch,
    ):
        """Regression for the prod bug observed on 2026-05-04:

        `_check_auth` imported `firebase_admin.auth` directly and called
        `verify_id_token` without first ensuring `firebase_admin.initialize_app()`
        had run. In production this caused every Bearer-token call to fail
        with `The default Firebase app does not exist` — admins clicking
        through stratiaadmissions.com/qa-runs all saw 'unauthorized'.

        The fix routes through `auth._firebase_admin()` (which lazily inits
        and is shared with the rest of the auth module). This test simulates
        prod-like state — `_apps` empty until `initialize_app` runs — and
        asserts the auth path successfully verifies the token.
        """
        import firebase_admin
        from firebase_admin import auth as _fa

        # Clear any state leaked from earlier tests (the conftest stub mutates
        # this module-level dict whenever lazy init runs).
        firebase_admin._apps.clear()

        def _verify(_t):
            if not firebase_admin._apps:
                raise ValueError(
                    "The default Firebase app does not exist. "
                    "Make sure to initialize the SDK by calling initialize_app()."
                )
            return {"email": "admin@example.com"}

        monkeypatch.setattr(_fa, "verify_id_token", _verify, raising=False)

        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"Authorization": "Bearer fake-id-token"},
            body={"run_id": "nope", "scenario_id": "nope"},
        )
        resp = qa_main.qa_agent(req)
        assert resp.status_code != 401, (
            "_check_auth must call firebase_admin.initialize_app() (via "
            "auth._firebase_admin()) before verify_id_token, otherwise prod "
            "Bearer-token auth fails with 'default Firebase app does not exist'"
        )
        # Belt-and-braces: confirm initialize_app ran as a side effect.
        assert firebase_admin._apps, "initialize_app should have been called"


# ---- /suggest-cause --------------------------------------------------------


class TestSuggestCauseEndpoint:
    def test_returns_400_on_missing_args(self, qa_main):
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "test-admin-token"},
            body={},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200  # endpoint returns success=False; status remains 200
        assert body["success"] is False
        assert "required" in body["error"]

    def test_returns_404_when_run_missing(self, qa_main, monkeypatch):
        import firestore_store
        monkeypatch.setattr(firestore_store, "read_report", lambda *_a, **_k: None)
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "missing", "scenario_id": "x"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert body["success"] is False
        assert "not found" in body["error"]

    def test_returns_heuristic_suggestion_when_no_llm_key(
        self, qa_main, monkeypatch
    ):
        import firestore_store
        report = {
            "run_id": "r1",
            "scenarios": [{
                "scenario_id": "junior_spring_5school",
                "description": "demo",
                "variation": {},
                "steps": [
                    {
                        "name": "roadmap_generate",
                        "status_code": 500,
                        "endpoint": "https://x/roadmap",
                        "elapsed_ms": 1234,
                        "passed": False,
                        "assertions": [
                            {"name": "status=2xx", "passed": False, "message": "got 500"},
                        ],
                        "response_excerpt": '{"error":"kaboom"}',
                    },
                ],
            }],
        }
        monkeypatch.setattr(firestore_store, "read_report", lambda *_a, **_k: report)
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "r1", "scenario_id": "junior_spring_5school"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert body["success"] is True
        # No GEMINI_API_KEY → heuristic fallback path.
        assert "Heuristic" in body["suggestion"]
        assert "roadmap_generate" in body["suggestion"]
        assert body["cached"] is False

    def test_dedup_returns_cached_on_repeat(self, qa_main, monkeypatch):
        import firestore_store
        report = {
            "scenarios": [{
                "scenario_id": "s1",
                "steps": [{"name": "x", "passed": False, "assertions": []}],
            }],
        }
        monkeypatch.setattr(firestore_store, "read_report", lambda *_a, **_k: report)
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "r1", "scenario_id": "s1"},
        )

        first = _resp_payload(qa_main.qa_agent(req))[1]
        assert first["cached"] is False
        second = _resp_payload(qa_main.qa_agent(req))[1]
        assert second["cached"] is True
        assert second["suggestion"] == first["suggestion"]

    def test_returns_clean_message_when_scenario_passed(
        self, qa_main, monkeypatch
    ):
        import firestore_store
        report = {
            "scenarios": [{
                "scenario_id": "s1",
                "steps": [{"name": "x", "passed": True, "assertions": []}],
            }],
        }
        monkeypatch.setattr(firestore_store, "read_report", lambda *_a, **_k: report)
        req = _FakeRequest(
            method="POST",
            path="/suggest-cause",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "r1", "scenario_id": "s1"},
        )
        body = _resp_payload(qa_main.qa_agent(req))[1]
        assert body["success"] is True
        assert "passed" in body["suggestion"]


# ---- /github-issue ---------------------------------------------------------


class TestGithubIssueEndpoint:
    def _basic_report(self):
        return {
            "run_id": "run_demo",
            "trigger": "manual",
            "actor": "admin@example.com",
            "started_at": "2026-05-03T18:00:00+00:00",
            "summary": {"total": 4, "pass": 3, "fail": 1},
            "scenarios": [{
                "scenario_id": "junior_spring_5school",
                "description": "demo",
                "variation": {"student_name": "Sam Chen"},
                "steps": [
                    {
                        "name": "roadmap_generate",
                        "status_code": 500,
                        "endpoint": "https://x/roadmap",
                        "elapsed_ms": 4321,
                        "passed": False,
                        "request": {"user_email": "duser8531@gmail.com"},
                        "response_excerpt": "kaboom",
                        "assertions": [
                            {"name": "status=2xx", "passed": False, "message": "got 500"},
                        ],
                    },
                ],
            }],
        }

    def test_builds_pre_filled_url(self, qa_main, monkeypatch):
        import firestore_store
        monkeypatch.setattr(
            firestore_store, "read_report", lambda *_a, **_k: self._basic_report()
        )
        req = _FakeRequest(
            method="POST",
            path="/github-issue",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "run_demo", "scenario_id": "junior_spring_5school"},
        )
        body = _resp_payload(qa_main.qa_agent(req))[1]
        assert body["success"] is True
        assert body["issue_url"].startswith(
            "https://github.com/cvsubs74/college-expert/issues/new?"
        )
        # Title appears (URL-encoded) in the URL.
        assert "junior_spring_5school" in urllib.parse.unquote(body["issue_url"])
        # Body contains the failing step's name + assertion.
        assert "roadmap_generate" in body["issue_body"]
        assert "status=2xx" in body["issue_body"]
        # And the run id, scenario id are present.
        assert "run_demo" in body["issue_body"]

    def test_truncates_url_when_body_huge(self, qa_main, monkeypatch):
        # Build a report with a giant response excerpt to push past 8KB.
        report = self._basic_report()
        report["scenarios"][0]["steps"][0]["response_excerpt"] = "X" * 12000
        import firestore_store
        monkeypatch.setattr(firestore_store, "read_report", lambda *_a, **_k: report)
        req = _FakeRequest(
            method="POST",
            path="/github-issue",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"run_id": "run_demo", "scenario_id": "junior_spring_5school"},
        )
        body = _resp_payload(qa_main.qa_agent(req))[1]
        assert body["success"] is True
        assert len(body["issue_url"]) <= 7800

    def test_returns_400_on_missing_args(self, qa_main):
        req = _FakeRequest(
            method="POST",
            path="/github-issue",
            headers={"X-Admin-Token": "test-admin-token"},
            body={},
        )
        body = _resp_payload(qa_main.qa_agent(req))[1]
        assert body["success"] is False
        assert "required" in body["error"]


# ---- /schedule endpoint ----------------------------------------------------


class TestScheduleEndpoint:
    """GET /schedule returns current config; POST /schedule writes new
    config. Both gated by admin auth."""

    def test_get_schedule_returns_current(self, qa_main, monkeypatch):
        import schedule
        monkeypatch.setattr(schedule, "load_schedule", lambda *_a, **_k: {
            "frequency": "daily",
            "times": ["06:00"],
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "timezone": "America/Los_Angeles",
        })
        req = _FakeRequest(
            method="GET",
            path="/schedule",
            headers={"X-Admin-Token": "test-admin-token"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        assert body["success"] is True
        assert body["schedule"]["frequency"] == "daily"
        assert "06:00" in body["schedule"]["times"]

    def test_get_schedule_requires_auth(self, qa_main):
        req = _FakeRequest(method="GET", path="/schedule")
        resp = qa_main.qa_agent(req)
        assert resp.status_code == 401

    def test_post_schedule_saves(self, qa_main, monkeypatch):
        import schedule
        captured = {}

        def fake_save(new_sched, actor=None, db=None):
            captured["sched"] = new_sched
            captured["actor"] = actor

        monkeypatch.setattr(schedule, "save_schedule", fake_save)
        req = _FakeRequest(
            method="POST",
            path="/schedule",
            headers={"X-Admin-Token": "test-admin-token"},
            body={
                "frequency": "twice_daily",
                "times": ["08:00", "16:00"],
                "days": ["mon", "tue", "wed", "thu", "fri"],
                "timezone": "America/Los_Angeles",
            },
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        assert body["success"] is True
        assert captured["sched"]["frequency"] == "twice_daily"

    def test_post_schedule_validates_frequency(self, qa_main):
        req = _FakeRequest(
            method="POST",
            path="/schedule",
            headers={"X-Admin-Token": "test-admin-token"},
            body={
                "frequency": "every_5_seconds",
                "times": ["00:00"],
                "days": [],
                "timezone": "America/Los_Angeles",
            },
        )
        body = _resp_payload(qa_main.qa_agent(req))[1]
        assert body["success"] is False
        assert "frequency" in body["error"]


# ---- /summary endpoint -----------------------------------------------------


class TestSummaryEndpoint:
    def test_returns_executive_summary(self, qa_main, monkeypatch):
        import firestore_store
        import narratives

        def fake_list(limit=30, db=None):
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            return [
                {
                    "run_id": f"r{i}",
                    "started_at": (now - timedelta(days=i)).isoformat(),
                    "summary": {"total": 4, "pass": 4, "fail": 0},
                    "scenarios": [],
                }
                for i in range(5)
            ]

        monkeypatch.setattr(firestore_store, "list_recent_runs", fake_list)
        monkeypatch.setattr(narratives, "build_summary", lambda runs, **k: {
            "narrative": "All systems green for 5 days running.",
            "pass_rate_7d": 100,
            "pass_rate_30d": 100,
            "trend": "steady",
            "surfaces": {},
        })
        req = _FakeRequest(
            method="GET",
            path="/summary",
            headers={"X-Admin-Token": "test-admin-token"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        assert body["success"] is True
        assert "All systems green" in body["summary"]["narrative"]
        assert body["summary"]["pass_rate_7d"] == 100

    def test_summary_requires_auth(self, qa_main):
        req = _FakeRequest(method="GET", path="/summary")
        assert qa_main.qa_agent(req).status_code == 401


# ---- trigger=schedule_check ------------------------------------------------


class TestScheduleCheckTrigger:
    """The hourly Cloud Scheduler poll fires /run with
    trigger=schedule_check. The agent calls schedule.should_run_now(),
    no-ops if it doesn't match."""

    def test_no_ops_when_schedule_does_not_match(self, qa_main, monkeypatch):
        import schedule
        monkeypatch.setattr(schedule, "load_schedule", lambda *_a, **_k: {
            "frequency": "daily",
            "times": ["06:00"],
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "timezone": "America/Los_Angeles",
        })
        monkeypatch.setattr(schedule, "should_run_now", lambda *_a, **_k: False)
        req = _FakeRequest(
            method="POST",
            path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"trigger": "schedule_check"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        assert body.get("skipped") is True

    def test_runs_when_schedule_matches(self, qa_main, monkeypatch):
        # Stub everything downstream so we can verify the dispatcher
        # does NOT skip when should_run_now returns True.
        import schedule, corpus, firestore_store, auth, runner, narratives

        monkeypatch.setattr(schedule, "should_run_now", lambda *_a, **_k: True)
        monkeypatch.setattr(corpus, "load_archetypes", lambda: [{
            "id": "test_archetype",
            "description": "test",
            "profile_template": {},
            "colleges_template": [],
            "tests": [],
            "surfaces_covered": ["profile"],
        }])
        monkeypatch.setattr(corpus, "select_scenarios", lambda *a, **k: a[0])
        monkeypatch.setattr(corpus, "generate_variation", lambda *a, **k: {
            "student_name": "Test", "intended_major": "X",
            "extra_interest": "", "gpa_delta": 0.0,
        })
        monkeypatch.setattr(corpus, "apply_variation", lambda a, _v: a)
        monkeypatch.setattr(firestore_store, "load_history", lambda *a, **k: {})
        monkeypatch.setattr(firestore_store, "update_history", lambda *a, **k: None)
        monkeypatch.setattr(firestore_store, "write_report", lambda *a, **k: None)
        monkeypatch.setattr(auth, "get_id_token", lambda *a, **k: "fake-id-token")
        monkeypatch.setattr(runner, "run_scenario", lambda *a, **k: {
            "scenario_id": "test_archetype", "passed": True,
            "duration_ms": 100, "steps": [],
        })
        monkeypatch.setattr(narratives, "build_plan", lambda *a, **k: {
            "narrative": "plan", "rationale": "rotation", "coverage": {},
        })
        monkeypatch.setattr(narratives, "build_outcome", lambda *a, **k: {
            "narrative": "outcome", "verdict": "all_pass", "first_look_at": [],
        })

        req = _FakeRequest(
            method="POST",
            path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"trigger": "schedule_check"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        assert body.get("skipped") is not True
        assert body.get("success") is True


# ---- _propagate_archetype_metadata ----------------------------------------
# Bug repro: business_rationale lives on the scenario JSON archetype but
# the runner only sees the materialized profile/colleges, so without
# explicit propagation the field never lands on the run-time scenario
# record (and the dashboard can't render the "Why this matters" callout).
# This helper copies the metadata over after each run completes.


class TestPropagateArchetypeMetadata:
    def test_always_sets_tests_and_surfaces_keys(self, qa_main):
        """Downstream code relies on these keys existing — default to
        empty containers when archetype omits them."""
        result = {"scenario_id": "x", "passed": True}
        qa_main._propagate_archetype_metadata(result, {})
        assert result["tests"] == []
        assert result["surfaces_covered"] == []

    def test_propagates_tests_and_surfaces(self, qa_main):
        result = {"scenario_id": "x", "passed": True}
        archetype = {
            "tests": ["a", "b"],
            "surfaces_covered": ["profile", "roadmap"],
        }
        qa_main._propagate_archetype_metadata(result, archetype)
        assert result["tests"] == ["a", "b"]
        assert result["surfaces_covered"] == ["profile", "roadmap"]

    def test_propagates_business_rationale_when_present(self, qa_main):
        result = {"scenario_id": "x", "passed": True}
        archetype = {
            "business_rationale": "Validates the most common journey for our highest-engagement users.",
        }
        qa_main._propagate_archetype_metadata(result, archetype)
        assert "business_rationale" in result
        assert "highest-engagement" in result["business_rationale"]

    def test_omits_business_rationale_when_absent(self, qa_main):
        """Legacy archetypes without rationale shouldn't litter the
        scenario record with null/empty fields."""
        result = {"scenario_id": "x", "passed": True}
        qa_main._propagate_archetype_metadata(result, {})
        assert "business_rationale" not in result

    def test_propagates_synthesized_marker_and_rationale(self, qa_main):
        """LLM-synthesized scenarios carry these so the SynthesizedBadge
        renders for them on the dashboard."""
        result = {"scenario_id": "synth_x", "passed": True}
        archetype = {
            "synthesized": True,
            "synthesis_rationale": "Targets an under-tested freshman summer fallback.",
        }
        qa_main._propagate_archetype_metadata(result, archetype)
        assert result["synthesized"] is True
        assert "freshman summer" in result["synthesis_rationale"]

    def test_does_not_overwrite_runner_assigned_fields(self, qa_main):
        """The runner already sets scenario_id/passed/duration_ms/etc. —
        propagation must NOT clobber those even if archetype has the
        same key (e.g., scenario_id matches archetype['id']). The helper
        only touches the propagation list, not the runner's outputs."""
        result = {
            "scenario_id": "runner_assigned",
            "passed": True,
            "steps": ["step1"],
        }
        archetype = {
            "scenario_id": "should_not_win",  # not in propagation list
            "tests": ["t1"],
        }
        qa_main._propagate_archetype_metadata(result, archetype)
        assert result["scenario_id"] == "runner_assigned"
        assert result["passed"] is True
        assert result["steps"] == ["step1"]
        assert result["tests"] == ["t1"]

    def test_propagates_colleges_template(self, qa_main):
        """Universities tested per scenario need to land on the run-time
        record so the chat backend + universities aggregator can see
        them. Without this propagation, the chat falls back to guessing
        from scenario IDs and the dashboard can't show what's covered.
        See docs/prd/qa-universities-tracking.md."""
        result = {"scenario_id": "x", "passed": True}
        archetype = {
            "colleges_template": ["mit", "stanford_university",
                                  "university_of_california_berkeley"],
        }
        qa_main._propagate_archetype_metadata(result, archetype)
        assert result["colleges_template"] == [
            "mit", "stanford_university",
            "university_of_california_berkeley",
        ]

    def test_omits_colleges_template_when_archetype_lacks_it(self, qa_main):
        """No empty/null pollution on legacy archetypes."""
        result = {"scenario_id": "x", "passed": True}
        qa_main._propagate_archetype_metadata(result, {})
        assert "colleges_template" not in result


# ---- /run/preview ---------------------------------------------------------


class TestRunPreviewEndpoint:
    def test_returns_picked_scenarios_without_running(self, qa_main, monkeypatch):
        import corpus, firestore_store, runner
        monkeypatch.setattr(corpus, "load_archetypes", lambda *a, **k: [
            {"id": "scen_a", "description": "Scenario A",
             "business_rationale": "Validates A.",
             "surfaces_covered": ["profile"]},
            {"id": "scen_b", "description": "Scenario B",
             "surfaces_covered": ["roadmap"]},
        ])
        monkeypatch.setattr(corpus, "select_scenarios",
                            lambda archetypes, history, n: archetypes[:n])
        monkeypatch.setattr(firestore_store, "load_history", lambda *a, **k: {})

        # Sentinels — these must NOT be invoked by /run/preview.
        def _boom(*_a, **_k):
            raise AssertionError(
                "/run/preview must not run scenarios or write Firestore"
            )
        monkeypatch.setattr(runner, "run_scenario", _boom)
        monkeypatch.setattr(firestore_store, "write_report", _boom)
        monkeypatch.setattr(firestore_store, "update_history", _boom)

        req = _FakeRequest(
            method="POST",
            path="/run/preview",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"count": 2},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        assert body["success"] is True
        picked = body["picked"]
        assert len(picked) == 2
        ids = [p["id"] for p in picked]
        assert "scen_a" in ids
        a = next(p for p in picked if p["id"] == "scen_a")
        assert a["description"] == "Scenario A"
        assert a["business_rationale"] == "Validates A."
        assert a["surfaces_covered"] == ["profile"]
        assert "synth_count" in body
        assert "static_count" in body

    def test_requires_auth(self, qa_main):
        req = _FakeRequest(method="POST", path="/run/preview", body={})
        resp = qa_main.qa_agent(req)
        assert resp.status_code == 401


# ---- /run writes a 'running' Firestore doc at start ----------------------


class TestRunHandlerRunningDoc:
    def _stub_everything(self, qa_main, monkeypatch, captured_writes):
        import auth, corpus, firestore_store, runner, narratives, synthesizer
        monkeypatch.setattr(corpus, "load_archetypes", lambda *a, **k: [
            {"id": "scen_a", "description": "A",
             "surfaces_covered": ["profile"], "tests": ["t1"]},
        ])
        monkeypatch.setattr(corpus, "select_scenarios",
                            lambda archetypes, history, n: archetypes[:n])
        monkeypatch.setattr(corpus, "generate_variation", lambda a, **k: {})
        monkeypatch.setattr(corpus, "apply_variation", lambda a, v: a)
        monkeypatch.setattr(firestore_store, "load_history", lambda *a, **k: {})
        monkeypatch.setattr(firestore_store, "list_recent_runs", lambda *a, **k: [])
        monkeypatch.setattr(firestore_store, "update_history", lambda *a, **k: None)
        monkeypatch.setattr(firestore_store, "write_report",
                            lambda run_id, payload: captured_writes.append(
                                {"run_id": run_id, "payload": payload}))
        monkeypatch.setattr(synthesizer, "synthesize_scenarios", lambda **k: [])
        monkeypatch.setattr(auth, "get_id_token", lambda *a, **k: "fake-id-token")
        monkeypatch.setattr(runner, "run_scenario", lambda *a, **k: {
            "scenario_id": "scen_a", "passed": True,
            "duration_ms": 100, "steps": [],
        })
        monkeypatch.setattr(narratives, "build_plan", lambda *a, **k: {
            "narrative": "p", "rationale": "rotation", "coverage": {}})
        monkeypatch.setattr(narratives, "build_outcome", lambda *a, **k: {
            "narrative": "o", "verdict": "all_pass", "first_look_at": []})

    def test_writes_running_doc_before_executing(self, qa_main, monkeypatch):
        captured = []
        self._stub_everything(qa_main, monkeypatch, captured)
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"count": 1, "trigger": "manual"},
        )
        status, body = _resp_payload(qa_main.qa_agent(req))
        assert status == 200
        # Three writes after PR #89's mutex fix:
        #   1) lock claim (status=running, scenarios=[]) — written
        #      EARLY before _pick_scenarios so concurrent /run calls
        #      see the lock immediately
        #   2) full running stub (status=running, scenarios=[...]) —
        #      after pick + planner complete
        #   3) final report (status=complete)
        assert len(captured) >= 3, (
            f"expected >=3 write_report calls (lock + running + "
            f"complete), got {len(captured)}"
        )
        # Lock claim — empty scenarios.
        lock = captured[0]
        assert lock["payload"]["status"] == "running"
        assert lock["payload"]["scenarios"] == []
        # Full running stub — scenarios populated.
        running = captured[1]
        assert running["payload"]["status"] == "running"
        scenarios = running["payload"]["scenarios"]
        assert len(scenarios) == 1
        assert scenarios[0]["scenario_id"] == "scen_a"
        assert scenarios[0]["status"] == "pending"
        assert scenarios[0]["passed"] is None

    def test_final_doc_has_status_complete(self, qa_main, monkeypatch):
        captured = []
        self._stub_everything(qa_main, monkeypatch, captured)
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"count": 1, "trigger": "manual"},
        )
        qa_main.qa_agent(req)
        final = captured[-1]
        assert final["payload"]["status"] == "complete"
        assert final["run_id"] == captured[0]["run_id"]

    def test_running_doc_carries_business_rationale(self, qa_main, monkeypatch):
        captured = []
        self._stub_everything(qa_main, monkeypatch, captured)
        import corpus
        monkeypatch.setattr(corpus, "load_archetypes", lambda *a, **k: [{
            "id": "scen_a", "description": "A scenario",
            "surfaces_covered": ["profile"],
            "tests": ["t1"],
            "business_rationale": "Why A matters.",
        }])
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={"count": 1, "trigger": "manual"},
        )
        qa_main.qa_agent(req)
        # captured[0] is the early lock claim (empty scenarios);
        # captured[1] is the full running stub with scenarios populated.
        running = captured[1]["payload"]["scenarios"][0]
        assert running["business_rationale"] == "Why A matters."
        assert running["surfaces_covered"] == ["profile"]


# ---- Feedback id collection -----------------------------------------------
#
# Bug repro: synthesizer LLM occasionally emits feedback_id as a JSON
# array (e.g. ["fb_a", "fb_b"]) when a single scenario addresses multiple
# admin-feedback items. The previous collection loop appended the raw
# value, then mark_applied() called set([["fb_a","fb_b"]]) — TypeError
# (unhashable list) — silently swallowed by the outer except. Net effect:
# multi-feedback scenarios never got credited.


class TestCollectFeedbackIds:
    def test_collects_single_string_ids(self, qa_main):
        scenarios = [
            {"scenario_id": "a", "feedback_id": "fb_1"},
            {"scenario_id": "b", "feedback_id": "fb_2"},
        ]
        assert qa_main._collect_feedback_ids(scenarios) == ["fb_1", "fb_2"]

    def test_flattens_list_form_into_individual_ids(self, qa_main):
        scenarios = [
            {"scenario_id": "a", "feedback_id": ["fb_a", "fb_b"]},
        ]
        assert qa_main._collect_feedback_ids(scenarios) == ["fb_a", "fb_b"]

    def test_handles_mixed_list_and_string_across_scenarios(self, qa_main):
        scenarios = [
            {"scenario_id": "a", "feedback_id": "fb_1"},
            {"scenario_id": "b", "feedback_id": ["fb_2", "fb_3"]},
            {"scenario_id": "c", "feedback_id": "fb_4"},
        ]
        assert qa_main._collect_feedback_ids(scenarios) == [
            "fb_1", "fb_2", "fb_3", "fb_4",
        ]

    def test_dedupes_repeats_across_scenarios(self, qa_main):
        scenarios = [
            {"scenario_id": "a", "feedback_id": "fb_1"},
            {"scenario_id": "b", "feedback_id": ["fb_1", "fb_2"]},
            {"scenario_id": "c", "feedback_id": "fb_2"},
        ]
        assert qa_main._collect_feedback_ids(scenarios) == ["fb_1", "fb_2"]

    def test_skips_missing_and_falsy(self, qa_main):
        scenarios = [
            {"scenario_id": "a"},                       # no key
            {"scenario_id": "b", "feedback_id": None},  # null
            {"scenario_id": "c", "feedback_id": ""},    # empty string
            {"scenario_id": "d", "feedback_id": []},    # empty list
            {"scenario_id": "e", "feedback_id": "fb_real"},
        ]
        assert qa_main._collect_feedback_ids(scenarios) == ["fb_real"]

    def test_drops_non_string_entries_inside_lists(self, qa_main):
        """An LLM occasionally emits {feedback_id: ["fb_a", null, 42]};
        keep the strings, drop the rest — never raise."""
        scenarios = [
            {"scenario_id": "a", "feedback_id": ["fb_a", None, 42, "fb_b", ""]},
        ]
        assert qa_main._collect_feedback_ids(scenarios) == ["fb_a", "fb_b"]

    def test_empty_input_returns_empty_list(self, qa_main):
        assert qa_main._collect_feedback_ids([]) == []


# ---- Concurrent /run mutex ----------------------------------------------
# Bug surfaced 2026-05-04 by run_20260504T210036Z_ee9985: two /run
# calls 19s apart on the shared test user produced indeterminate state
# (verify_college_list_symmetry failed with orphans from the OTHER
# run's colleges). The mutex blocks the second /run with HTTP 429
# until the first completes (or goes stale after 10 min).


class TestRunInProgressCheck:
    def _now_minus(self, minutes):
        from datetime import datetime, timedelta, timezone
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()

    def test_returns_none_when_no_runs(self, qa_main, monkeypatch):
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [])
        assert qa_main._check_run_in_progress() is None

    def test_returns_none_when_only_complete_runs(self, qa_main, monkeypatch):
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [
            {"run_id": "r1", "status": "complete",
             "started_at": self._now_minus(2)},
            {"run_id": "r2", "status": "complete",
             "started_at": self._now_minus(5)},
        ])
        assert qa_main._check_run_in_progress() is None

    def test_returns_run_when_running_and_recent(self, qa_main, monkeypatch):
        """Canonical busy case — a run started 1 minute ago, still
        in flight. Mutex must report it."""
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [
            {"run_id": "in_flight", "status": "running",
             "started_at": self._now_minus(1)},
        ])
        result = qa_main._check_run_in_progress()
        assert result is not None
        assert result["run_id"] == "in_flight"

    def test_treats_stale_running_as_not_busy(self, qa_main, monkeypatch):
        """A 'running' doc older than the stale threshold is presumed
        dead (cloud function crash, OOM); allow new runs to proceed."""
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [
            {"run_id": "zombie", "status": "running",
             "started_at": self._now_minus(15)},  # > 10 min stale threshold
        ])
        assert qa_main._check_run_in_progress() is None

    def test_handles_malformed_started_at(self, qa_main, monkeypatch):
        """Garbage timestamp shouldn't crash; treat as not-busy
        (fail-open over fail-closed for a non-critical guard)."""
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [
            {"run_id": "bad_ts", "status": "running",
             "started_at": "not-a-date"},
        ])
        assert qa_main._check_run_in_progress() is None

    def test_handles_missing_started_at(self, qa_main, monkeypatch):
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [
            {"run_id": "no_ts", "status": "running"},
        ])
        assert qa_main._check_run_in_progress() is None

    def test_swallows_firestore_errors(self, qa_main, monkeypatch):
        """If the lookup itself fails, allow the run rather than
        block on a transient Firestore hiccup. Fail-open."""
        def _boom(*_a, **_k):
            raise RuntimeError("firestore unavailable")
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs", _boom)
        assert qa_main._check_run_in_progress() is None


class TestHandleRunMutex:
    """Integration: /run returns 429 when another run is active,
    and runs normally when the path is clear."""

    def _busy_recent_runs(self):
        from datetime import datetime, timedelta, timezone
        recent_iso = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        return [{
            "run_id": "currently_running_xyz",
            "status": "running",
            "started_at": recent_iso,
        }]

    def test_returns_429_when_run_in_progress(self, qa_main, monkeypatch):
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: self._busy_recent_runs())
        # The dispatcher receives a tuple from _handle_run and routes
        # the status code through _cors. Call the http entry point
        # directly to verify both layers.
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={},
        )
        resp = qa_main.qa_agent(req)
        status, body = _resp_payload(resp)
        assert status == 429
        assert body["success"] is False
        assert "in flight" in body["error"]
        assert body.get("in_flight_run_id") == "currently_running_xyz"

    def test_proceeds_when_no_run_in_progress(self, qa_main, monkeypatch):
        """When the busy check returns None, /run continues into the
        normal pick + execute path. We stub the heavy bits so the
        test stays fast — what we're checking is that the mutex
        DIDN'T block."""
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [])
        monkeypatch.setattr(qa_main.firestore_store, "write_report",
                            lambda *a, **kw: None)
        # If _pick_scenarios is called, the mutex didn't block. We
        # short-circuit there to avoid running real scenarios.
        called = {"pick": False}
        def _stub_pick(*a, **kw):
            called["pick"] = True
            return {"ok": False, "error": "stubbed early"}
        monkeypatch.setattr(qa_main, "_pick_scenarios", _stub_pick)
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={},
        )
        qa_main.qa_agent(req)
        assert called["pick"], "mutex must not block when no run is in flight"

    def test_lock_claimed_before_pick_scenarios(self, qa_main, monkeypatch):
        """Critical for the race fix: the lock doc must be written
        BEFORE _pick_scenarios runs (which can take several seconds
        of Gemini calls). Otherwise two near-concurrent /run requests
        both pass the mutex check and write their stubs in parallel —
        the original race PR #89 was designed to fix."""
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [])
        # Capture every write_report call to verify the order.
        writes = []
        def _capture_write(run_id, payload):
            writes.append({"when": "before_pick" if not pick_called[0] else "after_pick",
                           "status": payload.get("status"),
                           "scenario_count": len(payload.get("scenarios", []))})
        monkeypatch.setattr(qa_main.firestore_store, "write_report",
                            _capture_write)
        pick_called = [False]
        def _stub_pick(*a, **kw):
            pick_called[0] = True
            return {"ok": False, "error": "stubbed"}
        monkeypatch.setattr(qa_main, "_pick_scenarios", _stub_pick)
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={},
        )
        qa_main.qa_agent(req)
        # First write must be the running stub, BEFORE _pick_scenarios
        # ran. Otherwise the race window is open.
        assert writes, "expected at least one write_report call"
        assert writes[0]["when"] == "before_pick", (
            f"Lock must be claimed before _pick_scenarios. Writes: {writes}"
        )
        assert writes[0]["status"] == "running"

    def test_releases_lock_when_pick_fails(self, qa_main, monkeypatch):
        """If _pick_scenarios fails AFTER the lock is claimed, the
        stale 'running' stub would block all future runs for 10 min.
        The early-lock path must release the lock by writing a
        'complete' doc on every error branch."""
        monkeypatch.setattr(qa_main.firestore_store, "list_recent_runs",
                            lambda limit=10: [])
        writes = []
        monkeypatch.setattr(qa_main.firestore_store, "write_report",
                            lambda run_id, payload: writes.append(payload))
        monkeypatch.setattr(qa_main, "_pick_scenarios",
                            lambda *a, **kw: {"ok": False, "error": "no archetypes"})
        req = _FakeRequest(
            method="POST", path="/run",
            headers={"X-Admin-Token": "test-admin-token"},
            body={},
        )
        qa_main.qa_agent(req)
        # Two writes expected: 1) lock claim (status=running),
        # 2) lock release (status=complete with error).
        assert len(writes) == 2, f"expected lock + release, got {writes}"
        assert writes[0]["status"] == "running"
        assert writes[1]["status"] == "complete"
        assert "no archetypes" in (writes[1].get("error") or "")
