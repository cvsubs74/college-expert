"""
Tests for chat.py — admin Q&A over recent QA runs.

Spec: docs/prd/qa-agent-chat.md + docs/design/qa-agent-chat.md.

The handler:
  1. Validates {question, history}
  2. Loads N recent run summaries from Firestore
  3. Builds a prompt grounded in those summaries
  4. Calls Gemini and returns the answer text

Heavy deps (firestore, google-genai) are stubbed in conftest. These
tests focus on the input/output contract and the run-context formatting
that grounds the model in real data.
"""

from __future__ import annotations

import pytest


# ---- Fixtures --------------------------------------------------------------


def _run(run_id, summary, scenarios=None, started_at="2026-05-04T01:00:00+00:00",
         trigger="agent_loop"):
    return {
        "run_id": run_id,
        "started_at": started_at,
        "trigger": trigger,
        "summary": summary,
        "scenarios": scenarios or [],
    }


def _scen(scenario_id, passed, failing_steps=None):
    s = {"scenario_id": scenario_id, "passed": passed, "steps": []}
    for step_name, assertion_msg in (failing_steps or []):
        s["steps"].append({
            "name": step_name,
            "passed": False,
            "assertions": [{"name": "x", "passed": False, "message": assertion_msg}],
        })
    return s


# ---- _format_run_context ---------------------------------------------------


class TestFormatRunContext:
    def test_includes_run_id_and_summary(self):
        import chat
        runs = [_run("run_a", {"pass": 5, "fail": 0, "total": 5})]
        out = chat._format_run_context(runs)
        assert "run_a" in out
        assert "5/5" in out or "5 pass" in out

    def test_lists_failing_scenarios_with_step_name(self):
        import chat
        runs = [_run(
            "run_b",
            {"pass": 1, "fail": 1, "total": 2},
            scenarios=[
                _scen("scen_a", True),
                _scen("scen_b", False, [
                    ("roadmap_generate", "metadata.template_used=='junior_fall': got 'junior_spring'")
                ]),
            ],
        )]
        out = chat._format_run_context(runs)
        assert "scen_b" in out, "should mention failing scenario"
        assert "roadmap_generate" in out, "should mention failing step"
        # Don't require the full assertion message — just enough to ground
        # the LLM. But the failing assertion summary should appear.
        assert "junior_fall" in out or "template_used" in out

    def test_passes_scenarios_dont_include_step_breakdown(self):
        import chat
        runs = [_run(
            "run_c",
            {"pass": 1, "fail": 0, "total": 1},
            scenarios=[_scen("happy_scen", True)],
        )]
        out = chat._format_run_context(runs)
        # The format budget matters — pass-only scenarios shouldn't dump
        # all their step names. Absence of "PASS" details is fine.
        assert "run_c" in out
        assert "1/1" in out or "1 pass" in out

    def test_empty_runs_returns_explicit_empty_message(self):
        import chat
        out = chat._format_run_context([])
        # Caller relies on this being non-empty so the prompt explains
        # the situation to the LLM rather than sending blank context.
        assert len(out.strip()) > 0
        # Plain English; no JSON braces.
        assert "no" in out.lower() or "empty" in out.lower() or "0 runs" in out.lower()

    def test_truncates_to_token_budget(self):
        """A 60-run history shouldn't blow the prompt budget. The
        formatter must cap output length even if given many runs."""
        import chat
        runs = [
            _run(
                f"run_{i}",
                {"pass": 8, "fail": 0, "total": 8},
                scenarios=[_scen(f"scen_{i}_{j}", True) for j in range(8)],
            )
            for i in range(60)
        ]
        out = chat._format_run_context(runs)
        # Soft upper bound: under 30k chars (~7-8k tokens), well within
        # Gemini Flash's 1M-token window with room for system + history.
        assert len(out) < 30000, f"context too large: {len(out)} chars"


# ---- _system_prompt --------------------------------------------------------


class TestSystemPrompt:
    def test_includes_grounding_rule(self):
        """The system prompt must instruct the model not to invent runs."""
        import chat
        sp = chat._system_prompt()
        # Grounding rule keywords (case-insensitive); match either of two
        # standard phrasings so we don't lock in exact wording.
        sp_lower = sp.lower()
        assert "ground" in sp_lower or "do not invent" in sp_lower or "never invent" in sp_lower
        # Should mention the specific data source it has.
        assert "run" in sp_lower

    def test_non_empty(self):
        import chat
        assert chat._system_prompt().strip()


# ---- handle_chat -----------------------------------------------------------


class TestHandleChat:
    def _cfg(self):
        return {"GEMINI_API_KEY": "fake-key"}

    def test_returns_400_on_empty_question(self, monkeypatch):
        import chat
        resp, status = chat.handle_chat({"question": ""}, self._cfg())
        assert status == 400
        assert resp["success"] is False
        assert "question" in resp.get("error", "").lower()

    def test_returns_400_on_missing_question_key(self, monkeypatch):
        import chat
        resp, status = chat.handle_chat({}, self._cfg())
        assert status == 400

    def test_returns_400_on_bad_history_type(self, monkeypatch):
        import chat
        resp, status = chat.handle_chat(
            {"question": "ok", "history": "not a list"}, self._cfg(),
        )
        assert status == 400
        assert "history" in resp.get("error", "").lower()

    def test_returns_400_when_no_runs_loaded(self, monkeypatch):
        import chat
        monkeypatch.setattr(chat, "_load_recent_run_summaries", lambda limit=30: [])
        resp, status = chat.handle_chat({"question": "anything"}, self._cfg())
        assert status == 400
        assert resp["success"] is False
        assert "run" in resp.get("error", "").lower()

    def test_happy_path_returns_answer(self, monkeypatch):
        import chat
        monkeypatch.setattr(chat, "_load_recent_run_summaries",
                            lambda limit=30: [_run("run_a", {"pass": 8, "fail": 0, "total": 8})])
        monkeypatch.setattr(chat, "_call_gemini",
                            lambda system, prompt, key: "Health is good — 8/8 pass.")
        resp, status = chat.handle_chat(
            {"question": "How's health?", "history": []}, self._cfg(),
        )
        assert status == 200
        assert resp["success"] is True
        assert "8/8" in resp["answer"] or "good" in resp["answer"].lower()
        assert resp["context_run_count"] == 1

    def test_history_is_passed_to_prompt(self, monkeypatch):
        """A multi-turn conversation must round-trip prior messages so the
        model can answer follow-ups (e.g., 'and the one before that?')."""
        import chat
        captured_prompts = []
        monkeypatch.setattr(chat, "_load_recent_run_summaries",
                            lambda limit=30: [_run("run_a", {"pass": 1, "fail": 0, "total": 1})])
        def _spy(system, prompt, key):
            captured_prompts.append(prompt)
            return "ack"
        monkeypatch.setattr(chat, "_call_gemini", _spy)

        history = [
            {"role": "user", "content": "What's the worst scenario?"},
            {"role": "assistant", "content": "freshman_fall_starter"},
        ]
        chat.handle_chat(
            {"question": "and the one before?", "history": history}, self._cfg(),
        )
        assert captured_prompts, "Gemini should have been called"
        prompt = captured_prompts[0]
        # The prompt should reference the prior turn so follow-up resolves.
        assert "What's the worst scenario?" in prompt
        assert "freshman_fall_starter" in prompt

    def test_gemini_error_falls_back_gracefully(self, monkeypatch):
        """If Gemini call fails (network, quota, etc.), return a 200-ish
        response with a friendly error message — don't 500."""
        import chat
        monkeypatch.setattr(chat, "_load_recent_run_summaries",
                            lambda limit=30: [_run("run_a", {"pass": 1, "fail": 0, "total": 1})])
        def _boom(*_a, **_k):
            raise RuntimeError("gemini timeout")
        monkeypatch.setattr(chat, "_call_gemini", _boom)

        resp, status = chat.handle_chat({"question": "anything"}, self._cfg())
        # Either a structured 503-ish or a 200 with success=False — but
        # NOT an unhandled 500.
        assert status in (200, 503)
        assert resp["success"] is False
        assert "error" in resp


# ---- Integration with main.py /chat route ---------------------------------


class TestChatRouteWiring:
    """Smoke test that main.py dispatches POST /chat to handle_chat with
    the expected body."""

    def test_chat_route_calls_handle_chat(self, monkeypatch):
        # Importing main with the qa_main fixture infrastructure is heavy;
        # this is a lightweight check that the route exists. We import
        # main fresh and assert the dispatcher recognizes the path.
        import importlib
        monkeypatch.setenv("QA_ADMIN_TOKEN", "test-admin-token")
        monkeypatch.setenv("QA_ADMIN_EMAILS", "admin@example.com")
        monkeypatch.setenv("QA_TEST_USER_EMAIL", "duser8531@gmail.com")
        monkeypatch.setenv("PROFILE_MANAGER_URL", "https://pm.test")
        monkeypatch.setenv("COUNSELOR_AGENT_URL", "https://ca.test")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        import main as qa_main_mod  # noqa: WPS433
        importlib.reload(qa_main_mod)

        # Stub the chat handler so we don't actually call the LLM.
        called = {}
        import chat
        def _stub_handle(body, cfg):
            called["body"] = body
            return {"success": True, "answer": "stub"}, 200
        monkeypatch.setattr(chat, "handle_chat", _stub_handle)

        # Build a minimal request stub.
        class _Req:
            method = "POST"
            path = "/chat"
            headers = {"X-Admin-Token": "test-admin-token"}
            args = {}
            def get_json(self, silent=False):
                return {"question": "hi", "history": []}

        resp = qa_main_mod.qa_agent(_Req())
        # The route should have dispatched to handle_chat.
        assert called.get("body", {}).get("question") == "hi"
        assert resp.status_code == 200


# ---- Chat context includes per-run universities --------------------------
# Bug repro: asked "what universities have been covered", chat answered
# vaguely from the scenario IDs because run records didn't carry
# colleges_template in the prompt. Fix: format_run_context now adds a
# "colleges:" line per run.


class TestChatContextIncludesColleges:
    def test_format_run_context_includes_colleges_per_run(self):
        import chat
        run = {
            "run_id": "run_x",
            "started_at": "2026-05-04T01:00:00+00:00",
            "trigger": "manual",
            "summary": {"pass": 2, "fail": 0, "total": 2},
            "scenarios": [
                {"scenario_id": "a", "passed": True,
                 "colleges_template": ["mit", "stanford_university"]},
                {"scenario_id": "b", "passed": True,
                 "colleges_template": ["university_of_california_berkeley"]},
            ],
        }
        out = chat._format_run_context([run])
        assert "mit" in out
        assert "stanford_university" in out
        assert "university_of_california_berkeley" in out
        assert "colleges:" in out.lower() or "universities:" in out.lower()

    def test_dedupes_colleges_within_a_run(self):
        import chat
        run = {
            "run_id": "run_dup",
            "started_at": "2026-05-04T01:00:00+00:00",
            "summary": {"pass": 2, "fail": 0, "total": 2},
            "scenarios": [
                {"scenario_id": "a", "passed": True,
                 "colleges_template": ["mit"]},
                {"scenario_id": "b", "passed": True,
                 "colleges_template": ["mit", "stanford"]},
            ],
        }
        out = chat._format_run_context([run])
        # The colleges line should not list mit twice.
        assert "mit, mit" not in out

    def test_no_colleges_line_when_scenarios_have_none(self):
        """Legacy runs without colleges_template don't render an empty
        'colleges:' line."""
        import chat
        run = {
            "run_id": "run_legacy",
            "started_at": "2026-05-04T01:00:00+00:00",
            "summary": {"pass": 1, "fail": 0, "total": 1},
            "scenarios": [{"scenario_id": "a", "passed": True}],
        }
        out = chat._format_run_context([run])
        assert "colleges:" not in out.lower()


# ---- Feedback context grounding ------------------------------------------
# Spec: docs/prd/qa-chat-feedback-context.md.
# Bug repro: chat saw `feedback_id: fb_xyz` stamped on synthesized
# scenarios but had no way to map that ID back to the operator's note
# text. Adding a feedback section to the prompt closes the loop.


class TestFormatFeedbackContext:
    def test_renders_active_items_with_id_and_text(self):
        import chat
        active = [{
            "id": "fb_active",
            "text": "Focus on UC group treatment",
            "status": "active",
            "applied_count": 2,
            "max_applies": 5,
            "last_applied_run_id": "run_xyz",
        }]
        out = chat._format_feedback_context(active, [])
        assert "fb_active" in out
        assert "Focus on UC group treatment" in out
        assert "2/5" in out or "applied 2" in out
        # The header tells the LLM what this section is.
        assert "feedback" in out.lower()

    def test_renders_retired_items_with_final_count(self):
        import chat
        dismissed = [{
            "id": "fb_retired",
            "text": "Cover every single university",
            "status": "dismissed",
            "applied_count": 5,
            "max_applies": 5,
            "last_applied_run_id": "run_final",
        }]
        out = chat._format_feedback_context([], dismissed)
        assert "fb_retired" in out
        assert "Cover every single university" in out
        # An LLM reading the prompt should be able to tell active
        # apart from retired (case-insensitive match on either form).
        assert "retired" in out.lower() or "dismissed" in out.lower()

    def test_handles_both_active_and_retired_in_one_pass(self):
        import chat
        active = [{
            "id": "fb_a", "text": "active note", "status": "active",
            "applied_count": 1, "max_applies": 5,
        }]
        dismissed = [{
            "id": "fb_b", "text": "retired note", "status": "dismissed",
            "applied_count": 5, "max_applies": 5,
        }]
        out = chat._format_feedback_context(active, dismissed)
        assert "fb_a" in out
        assert "fb_b" in out
        assert "active note" in out
        assert "retired note" in out

    def test_returns_explicit_empty_message_when_no_feedback(self):
        """Caller relies on this being non-empty so the prompt never
        carries a malformed/empty section."""
        import chat
        out = chat._format_feedback_context([], [])
        assert len(out.strip()) > 0
        # Plain English "no feedback" fallback so the LLM doesn't
        # confabulate operator notes.
        lowered = out.lower()
        assert "no" in lowered or "none" in lowered or "empty" in lowered

    def test_truncates_to_token_budget(self):
        """Don't dump 100 retired items into the prompt; cap so chat
        stays under budget on a long-running setup."""
        import chat
        big = [
            {"id": f"fb_{i}", "text": f"item {i}" * 5, "status": "dismissed",
             "applied_count": 5, "max_applies": 5}
            for i in range(50)
        ]
        out = chat._format_feedback_context([], big)
        # Soft cap — under 4000 chars (~1000 tokens) for the feedback
        # section alone leaves plenty of room for run context.
        assert len(out) < 4000


class TestLoadFeedbackContext:
    def test_swallows_feedback_load_errors(self, monkeypatch):
        """A feedback-store outage must not take down the chat
        endpoint. _load_feedback_context returns empty lists on any
        exception."""
        import chat
        # Stub the feedback module to blow up on load.
        import sys, types
        fb_stub = types.ModuleType("feedback")

        def _boom(*_a, **_k):
            raise RuntimeError("firestore unhealthy")

        fb_stub.active_items = _boom
        fb_stub.recently_dismissed_items = _boom
        monkeypatch.setitem(sys.modules, "feedback", fb_stub)

        result = chat._load_feedback_context()
        assert result == {"active": [], "dismissed": []}


class TestHandleChatPassesFeedback:
    def _runs(self):
        return [{
            "run_id": "run_a",
            "started_at": "2026-05-04T01:00:00+00:00",
            "trigger": "agent_loop",
            "summary": {"pass": 8, "fail": 0, "total": 8},
            "scenarios": [],
        }]

    def test_prompt_carries_active_feedback_text(self, monkeypatch):
        import chat
        monkeypatch.setattr(chat, "_load_recent_run_summaries",
                            lambda limit=30: self._runs())
        monkeypatch.setattr(chat, "_load_feedback_context",
                            lambda: {
                                "active": [{
                                    "id": "fb_xyz",
                                    "text": "Focus on UC group treatment",
                                    "status": "active",
                                    "applied_count": 1, "max_applies": 5,
                                }],
                                "dismissed": [],
                            })
        captured = {}
        def _spy(system, prompt, key):
            captured["prompt"] = prompt
            return "ok"
        monkeypatch.setattr(chat, "_call_gemini", _spy)
        chat.handle_chat(
            {"question": "what's been steering the runs?", "history": []},
            {"GEMINI_API_KEY": "fake"},
        )
        assert "fb_xyz" in captured["prompt"]
        assert "UC group treatment" in captured["prompt"]

    def test_prompt_carries_retired_feedback(self, monkeypatch):
        import chat
        monkeypatch.setattr(chat, "_load_recent_run_summaries",
                            lambda limit=30: self._runs())
        monkeypatch.setattr(chat, "_load_feedback_context",
                            lambda: {
                                "active": [],
                                "dismissed": [{
                                    "id": "fb_done",
                                    "text": "Cover every single university",
                                    "status": "dismissed",
                                    "applied_count": 5, "max_applies": 5,
                                    "last_applied_run_id": "run_final",
                                }],
                            })
        captured = {}
        monkeypatch.setattr(chat, "_call_gemini",
                            lambda s, p, k: captured.setdefault("prompt", p) or "ok")
        chat.handle_chat(
            {"question": "did any operator notes drive recent runs?", "history": []},
            {"GEMINI_API_KEY": "fake"},
        )
        assert "fb_done" in captured["prompt"]
        assert "Cover every single university" in captured["prompt"]
