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
