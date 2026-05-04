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


# ---- College ID canonicalization at archetype-write time -----------------
#
# The synthesizer's allowlist no longer contains "mit" or "ucla" (PR #67),
# so the LLM can't emit them. But a defense-in-depth layer at archetype-
# write time means: even if a static scenario JSON file or a future code
# path reintroduces an alias, the canonical id ends up in the run record.
# This is the layer requested in the spawned-task chip on 2026-05-04.


class TestCanonicalizeCollegeId:
    def test_mit_alias_folds_to_canonical(self):
        import synthesizer
        assert (synthesizer.canonicalize_college_id("mit")
                == "massachusetts_institute_of_technology")

    def test_ucla_alias_folds_to_canonical(self):
        import synthesizer
        assert (synthesizer.canonicalize_college_id("ucla")
                == "university_of_california_los_angeles")

    def test_already_canonical_passes_through(self):
        import synthesizer
        assert (synthesizer.canonicalize_college_id("stanford_university")
                == "stanford_university")
        assert (synthesizer.canonicalize_college_id(
                    "massachusetts_institute_of_technology")
                == "massachusetts_institute_of_technology")

    def test_unknown_id_passes_through_unchanged(self):
        """The map is opt-in by entry — a brand-new school id we
        haven't catalogued yet should not be silently dropped."""
        import synthesizer
        assert (synthesizer.canonicalize_college_id("brand_new_school_xyz")
                == "brand_new_school_xyz")

    def test_non_string_input_returns_unchanged(self):
        """None / int / dict shouldn't crash the helper."""
        import synthesizer
        assert synthesizer.canonicalize_college_id(None) is None
        assert synthesizer.canonicalize_college_id(42) == 42


class TestCanonicalizeArchetype:
    def test_mit_in_colleges_template_gets_canonicalized(self):
        import synthesizer
        archetype = {
            "id": "x",
            "colleges_template": ["mit", "stanford_university"],
        }
        synthesizer.canonicalize_archetype(archetype)
        assert archetype["colleges_template"] == [
            "massachusetts_institute_of_technology",
            "stanford_university",
        ]

    def test_ucla_in_colleges_template_gets_canonicalized(self):
        import synthesizer
        archetype = {
            "id": "x",
            "colleges_template": ["university_of_michigan", "ucla"],
        }
        synthesizer.canonicalize_archetype(archetype)
        assert archetype["colleges_template"] == [
            "university_of_michigan",
            "university_of_california_los_angeles",
        ]

    def test_dedups_when_alias_and_canonical_both_present(self):
        """If a single archetype contains BOTH "mit" and the canonical
        form, the result must be one entry, not two — otherwise we just
        moved the dup from coverage layer to the archetype layer."""
        import synthesizer
        archetype = {
            "colleges_template": [
                "mit",
                "massachusetts_institute_of_technology",
                "stanford_university",
            ],
        }
        synthesizer.canonicalize_archetype(archetype)
        assert archetype["colleges_template"] == [
            "massachusetts_institute_of_technology",
            "stanford_university",
        ]

    def test_preserves_order_of_first_occurrence(self):
        import synthesizer
        archetype = {
            "colleges_template": ["stanford_university", "mit", "harvard_university"],
        }
        synthesizer.canonicalize_archetype(archetype)
        # Stanford was first; MIT (canonicalized) keeps its position;
        # Harvard third.
        assert archetype["colleges_template"] == [
            "stanford_university",
            "massachusetts_institute_of_technology",
            "harvard_university",
        ]

    def test_idempotent(self):
        """Calling canonicalize_archetype twice must not change the
        already-canonical result."""
        import synthesizer
        archetype = {"colleges_template": ["mit", "ucla"]}
        synthesizer.canonicalize_archetype(archetype)
        first = list(archetype["colleges_template"])
        synthesizer.canonicalize_archetype(archetype)
        assert archetype["colleges_template"] == first

    def test_no_op_when_archetype_lacks_colleges_template(self):
        """Pre-completion stubs or legacy data shouldn't crash."""
        import synthesizer
        archetype = {"id": "no_colleges"}
        synthesizer.canonicalize_archetype(archetype)
        assert "colleges_template" not in archetype  # untouched

    def test_skips_non_string_entries_silently(self):
        """Defensive: a malformed colleges_template shouldn't take down
        the run."""
        import synthesizer
        archetype = {
            "colleges_template": ["mit", None, 42, "stanford_university", ""],
        }
        synthesizer.canonicalize_archetype(archetype)
        assert archetype["colleges_template"] == [
            "massachusetts_institute_of_technology",
            "stanford_university",
        ]

    def test_handles_non_dict_input_gracefully(self):
        """Caller may pass a partial result; don't raise."""
        import synthesizer
        # No raise = pass.
        synthesizer.canonicalize_archetype(None)
        synthesizer.canonicalize_archetype("not a dict")
        synthesizer.canonicalize_archetype(123)


# ---- Phase 3: synthesizer can produce fit-focused archetypes ------------
# The synthesizer LLM can now include fit_target_college (string) or
# fit_target_colleges (list) on a generated archetype to trigger the
# runner's compute_fit step. Validation enforces:
#   - fit_target_college must be a string in the colleges_allowlist
#   - fit_target_college must also appear in colleges_template
#   - same rules per entry for fit_target_colleges
# These checks prevent the LLM from inventing fit targets the runner
# can't actually exercise.


_FIT_ARCHETYPE_BASE = {
    "id": "synth_fit_x",
    "synthesized": True,
    "synthesis_rationale": "Targets a fit-coverage gap.",
    "description": "Senior, no scores, vs accessible school",
    "tests": ["fit invariants hold"],
    "default_student_name": "Test User",
    "profile_template": {
        "grade_level": "12th Grade",
        "graduation_year": 2026,
        "gpa": 3.8,
        "intended_major": "Computer Science",
        "interests": ["robotics"],
    },
    "colleges_template": ["mit", "stanford_university"],
    "expected_template_used": "senior_fall",
    "surfaces_covered": ["profile", "college_list", "roadmap", "fit"],
}


class TestFitArchetypeValidation:
    def test_fit_target_college_in_allowlist_passes(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["fit_target_college"] = "mit"
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert ok, err

    def test_fit_target_college_must_be_string(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["fit_target_college"] = ["mit"]  # wrong type
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert not ok
        assert "fit_target_college" in err

    def test_fit_target_college_not_in_allowlist_fails(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["fit_target_college"] = "school_that_doesnt_exist"
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert not ok
        assert "school_that_doesnt_exist" in err

    def test_fit_target_college_must_appear_in_colleges_template(self):
        """The runner adds colleges from colleges_template via
        /add-to-list before calling /compute-single-fit. If the fit
        target isn't on that list, the fit call would target a school
        the test user hasn't added — invalid scenario."""
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["colleges_template"] = ["stanford_university"]  # no mit
        archetype["fit_target_college"] = "mit"  # not in template
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert not ok
        assert "colleges_template" in err

    def test_fit_target_colleges_list_passes(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["fit_target_colleges"] = ["mit", "stanford_university"]
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert ok, err

    def test_fit_target_colleges_must_be_a_list(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["fit_target_colleges"] = "mit"  # string, not list
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert not ok
        assert "fit_target_colleges" in err

    def test_fit_target_colleges_entries_must_be_in_allowlist(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["fit_target_colleges"] = ["mit", "fake_university"]
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert not ok
        assert "fake_university" in err

    def test_fit_target_colleges_entries_must_be_in_template(self):
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        archetype["colleges_template"] = ["mit"]  # only mit
        archetype["fit_target_colleges"] = ["mit", "stanford_university"]
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert not ok
        assert "stanford_university" in err

    def test_archetype_without_any_fit_field_still_passes(self):
        """Phase 3 is additive — non-fit archetypes are unchanged.
        This is the existing happy path that must keep working."""
        import synthesizer
        archetype = dict(_FIT_ARCHETYPE_BASE)
        # No fit_target_college, no fit_target_colleges
        ok, err = synthesizer.validate_archetype(
            archetype, COLLEGES_ALLOWLIST,
        )
        assert ok, err
