"""
Tests for synthesizer.py — the LLM-driven scenario generator.

The synthesizer reads system_knowledge.md + recent run history, asks
Gemini Flash for N fresh scenarios, validates each (schema + value
bounds + colleges allowlist + resolver pre-check), and falls back to
static archetypes when the LLM is unavailable or output is malformed.

These tests cover the validation layer + fallback paths. They pass
without ever calling a real LLM (Gemini stubbed in conftest).
"""

from __future__ import annotations

import json
import pytest


COLLEGES_ALLOWLIST = [
    "mit", "stanford_university", "harvard_university",
    "university_of_california_berkeley", "university_of_california_los_angeles",
]


# ---- validate_archetype --------------------------------------------------


class TestValidateArchetype:
    def _good(self):
        return {
            "id": "synth_x",
            "synthesized": True,
            "synthesis_rationale": "Tests low-GPA + reach school combo.",
            "description": "Junior with 3.1 GPA and 2 reach schools",
            "tests": ["Resolver picks junior_spring", "2 colleges added cleanly"],
            "default_student_name": "Sam Chen",
            "profile_template": {
                "grade_level": "11th Grade",
                "graduation_year": 2027,
                "gpa": 3.1,
                "intended_major": "Computer Science",
                "interests": ["robotics"],
            },
            "colleges_template": ["mit", "stanford_university"],
            "expected_template_used": "junior_spring",
            "surfaces_covered": ["profile", "college_list", "roadmap"],
        }

    def test_good_scenario_validates(self):
        import synthesizer
        ok, err = synthesizer.validate_archetype(self._good(), COLLEGES_ALLOWLIST)
        assert ok, err

    def test_rejects_invalid_college_id(self):
        import synthesizer
        bad = self._good()
        bad["colleges_template"] = ["mit", "school_that_doesnt_exist"]
        ok, err = synthesizer.validate_archetype(bad, COLLEGES_ALLOWLIST)
        assert not ok
        assert "school_that_doesnt_exist" in err

    def test_rejects_out_of_range_gpa(self):
        import synthesizer
        bad = self._good()
        bad["profile_template"]["gpa"] = 5.0
        ok, err = synthesizer.validate_archetype(bad, COLLEGES_ALLOWLIST)
        assert not ok
        assert "gpa" in err.lower()

    def test_rejects_negative_gpa(self):
        import synthesizer
        bad = self._good()
        bad["profile_template"]["gpa"] = -0.5
        ok, err = synthesizer.validate_archetype(bad, COLLEGES_ALLOWLIST)
        assert not ok

    def test_rejects_invalid_grade_level(self):
        import synthesizer
        bad = self._good()
        bad["profile_template"]["grade_level"] = "13th Grade"
        ok, err = synthesizer.validate_archetype(bad, COLLEGES_ALLOWLIST)
        assert not ok

    def test_rejects_too_many_colleges(self):
        """Synthesized scenarios cap college count to keep run latency
        bounded."""
        import synthesizer
        bad = self._good()
        bad["colleges_template"] = list(COLLEGES_ALLOWLIST) * 3  # 15 colleges
        ok, err = synthesizer.validate_archetype(bad, COLLEGES_ALLOWLIST,
                                                 max_colleges=8)
        assert not ok

    def test_rejects_template_hallucination(self):
        """expected_template_used must match what the resolver would
        compute from the synthesized profile + today's semester."""
        import synthesizer
        bad = self._good()
        bad["expected_template_used"] = "senior_winter"  # not a real template
        ok, err = synthesizer.validate_archetype(
            bad, COLLEGES_ALLOWLIST, valid_templates={
                "freshman_fall", "freshman_spring",
                "sophomore_fall", "sophomore_spring",
                "junior_fall", "junior_spring", "junior_summer",
                "senior_fall", "senior_spring",
            },
        )
        assert not ok

    def test_rejects_missing_synthesis_rationale(self):
        """Synthesized scenarios MUST carry a rationale (the user can't
        review the agent's intent without it)."""
        import synthesizer
        bad = self._good()
        del bad["synthesis_rationale"]
        ok, err = synthesizer.validate_archetype(bad, COLLEGES_ALLOWLIST)
        assert not ok


# ---- synthesize_scenarios ------------------------------------------------


class TestSynthesizeScenarios:
    def _hist(self):
        return [
            {
                "run_id": "r1",
                "started_at": "2026-05-02T06:00:00+00:00",
                "summary": {"total": 4, "pass": 4, "fail": 0},
                "scenarios": [{"scenario_id": "junior_spring_5school", "passed": True,
                               "surfaces_covered": ["profile", "roadmap"]}],
            },
        ]

    def _kb(self):
        return "# Stub system knowledge"

    def test_falls_back_when_no_api_key(self, monkeypatch):
        import synthesizer
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        result = synthesizer.synthesize_scenarios(
            n=2,
            history=self._hist(),
            system_knowledge=self._kb(),
            colleges_allowlist=COLLEGES_ALLOWLIST,
            valid_templates={"junior_spring", "senior_fall"},
            gemini_key=None,
        )
        # No key → returns empty list (caller fills with static).
        assert result == []

    def test_falls_back_on_malformed_json(self, monkeypatch):
        import synthesizer
        import google.generativeai as genai

        class _Model:
            def __init__(self, *_a, **_k):
                pass

            def generate_content(self, *_a, **_k):
                class R:
                    text = "totally not json"
                return R()

        monkeypatch.setattr(genai, "GenerativeModel", _Model)
        result = synthesizer.synthesize_scenarios(
            n=2,
            history=self._hist(),
            system_knowledge=self._kb(),
            colleges_allowlist=COLLEGES_ALLOWLIST,
            valid_templates={"junior_spring"},
            gemini_key="fake-key",
        )
        assert result == []

    def test_returns_only_valid_scenarios(self, monkeypatch):
        """LLM returns 2 scenarios, 1 has bad college id — only 1
        scenario returned."""
        import synthesizer
        import google.generativeai as genai

        good_scenario = {
            "id": "synth_a",
            "synthesized": True,
            "synthesis_rationale": "Targets low-GPA gap.",
            "description": "Low GPA, 2 reaches",
            "tests": ["X"],
            "default_student_name": "Test",
            "profile_template": {
                "grade_level": "11th Grade",
                "graduation_year": 2027,
                "gpa": 3.1,
                "intended_major": "CS",
                "interests": ["robotics"],
            },
            "colleges_template": ["mit"],
            "expected_template_used": "junior_spring",
            "surfaces_covered": ["profile", "college_list", "roadmap"],
        }
        bad_scenario = dict(good_scenario)
        bad_scenario["id"] = "synth_b"
        bad_scenario["colleges_template"] = ["unknown_school"]

        payload = json.dumps({"scenarios": [good_scenario, bad_scenario]})

        class _Model:
            def __init__(self, *_a, **_k): pass
            def generate_content(self, *_a, **_k):
                class R:
                    text = payload
                return R()

        monkeypatch.setattr(genai, "GenerativeModel", _Model)
        result = synthesizer.synthesize_scenarios(
            n=2,
            history=self._hist(),
            system_knowledge=self._kb(),
            colleges_allowlist=COLLEGES_ALLOWLIST,
            valid_templates={"junior_spring"},
            gemini_key="fake-key",
        )
        assert len(result) == 1
        assert result[0]["id"] == "synth_a"


# ---- summarize_history ----------------------------------------------------


class TestHistorySummary:
    def test_includes_surface_coverage(self):
        import synthesizer
        runs = [
            {
                "run_id": "r1",
                "started_at": "2026-05-02T06:00:00+00:00",
                "summary": {"pass": 4, "fail": 0, "total": 4},
                "scenarios": [
                    {"scenario_id": "a", "passed": True,
                     "surfaces_covered": ["profile", "roadmap"]},
                ],
            },
            {
                "run_id": "r2",
                "started_at": "2026-05-01T06:00:00+00:00",
                "summary": {"pass": 4, "fail": 0, "total": 4},
                "scenarios": [
                    {"scenario_id": "b", "passed": True,
                     "surfaces_covered": ["college_list"]},
                ],
            },
        ]
        summary = synthesizer.summarize_history(runs)
        # Surface coverage should report counts per surface
        assert "surface_coverage" in summary
        assert summary["surface_coverage"]["profile"] == 1
        assert summary["surface_coverage"]["roadmap"] == 1
        assert summary["surface_coverage"]["college_list"] == 1

    def test_flags_recent_failures(self):
        import synthesizer
        runs = [
            {
                "run_id": "r1",
                "started_at": "2026-05-02T06:00:00+00:00",
                "summary": {"pass": 3, "fail": 1, "total": 4},
                "scenarios": [
                    {"scenario_id": "broken", "passed": False, "surfaces_covered": []},
                    {"scenario_id": "fine", "passed": True, "surfaces_covered": []},
                ],
            },
        ]
        summary = synthesizer.summarize_history(runs)
        assert "broken" in str(summary.get("recent_failures", []))


# ---- Feedback in the synthesizer prompt -----------------------------------
# PR-N: admin-authored notes get formatted into the prompt with their
# stable IDs so the LLM can stamp generated scenarios with feedback_id.


class TestFeedbackInPrompt:
    def _bare_history(self):
        return {"runs_in_window": 0, "surface_coverage": {},
                "scenarios_seen": {}, "recent_failures": [],
                "gpa_buckets": {}}

    def test_omits_feedback_section_when_no_items(self):
        import synthesizer
        prompt = synthesizer._build_prompt(
            2, "(stub)", self._bare_history(), ["mit"],
            feedback_items=None,
        )
        assert "ADMIN FEEDBACK" not in prompt

    def test_omits_feedback_section_when_empty_list(self):
        import synthesizer
        prompt = synthesizer._build_prompt(
            2, "(stub)", self._bare_history(), ["mit"],
            feedback_items=[],
        )
        assert "ADMIN FEEDBACK" not in prompt

    def test_includes_feedback_section_when_items_present(self):
        import synthesizer
        prompt = synthesizer._build_prompt(
            2, "(stub)", self._bare_history(), ["mit"],
            feedback_items=[
                {"id": "fb_abc", "text": "Focus on essay tracker",
                 "applied_count": 1, "max_applies": 5},
                {"id": "fb_xyz", "text": "Verify UC group fix",
                 "applied_count": 0, "max_applies": 5},
            ],
        )
        assert "ADMIN FEEDBACK" in prompt
        assert "fb_abc" in prompt
        assert "Focus on essay tracker" in prompt
        assert "fb_xyz" in prompt
        # Prompt must instruct the LLM to stamp scenarios with
        # feedback_id so applied_count can be credited.
        assert "feedback_id" in prompt

    def test_synthesize_scenarios_passes_feedback_through(self, monkeypatch):
        """End-to-end: synthesize_scenarios receives feedback_items and
        the prompt fed to Gemini contains them."""
        import synthesizer
        import google.generativeai as genai
        captured = {}

        class _Model:
            def __init__(self, *_a, **_k):
                pass
            def generate_content(self, prompt, *_a, **_k):
                captured["prompt"] = prompt
                class R:
                    text = '{"scenarios": []}'
                return R()
        monkeypatch.setattr(genai, "GenerativeModel", _Model)

        synthesizer.synthesize_scenarios(
            n=1,
            history=[],
            system_knowledge="(stub)",
            colleges_allowlist=["mit"],
            feedback_items=[{"id": "fb_xyz", "text": "Test essay tracker",
                             "applied_count": 0, "max_applies": 5}],
            gemini_key="fake-key",
        )
        assert "ADMIN FEEDBACK" in captured["prompt"]
        assert "fb_xyz" in captured["prompt"]
        assert "essay tracker" in captured["prompt"].lower()
