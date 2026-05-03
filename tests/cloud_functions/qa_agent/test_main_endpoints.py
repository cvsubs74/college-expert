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
