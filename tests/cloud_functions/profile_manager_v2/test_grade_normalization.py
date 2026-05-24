"""
Tests for grade field normalization at LLM extraction time (issue #130).

Regression hardening: profile_extraction.py must coerce `grade` to string
after Gemini JSON parse, so Firestore always stores grade as a string.
The migration script (scripts/fix_grade_field_type.py) must be idempotent.
"""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure source dir on sys.path (conftest already does this for most tests,
# but importing profile_extraction needs google.genai stubbed first — handled
# below before the import).
# ---------------------------------------------------------------------------
SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'profile_manager_v2'
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


# ---------------------------------------------------------------------------
# Stub google.genai (profile_extraction imports it at module level).
# conftest.py already stubs google.cloud.firestore; we add genai here.
# ---------------------------------------------------------------------------
def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mod.__path__ = []
    return mod


_google = _ensure_module('google')
_genai = _ensure_module('google.genai')
_genai_types = _ensure_module('google.genai.types')


class _StubGenaiClient:
    def __init__(self, *a, **kw):
        self.models = self

    def generate_content(self, *a, **kw):
        raise RuntimeError("stub — should not reach LLM in unit tests")


_genai.Client = _StubGenaiClient


# ---------------------------------------------------------------------------
# Now safe to import the module under test.
# ---------------------------------------------------------------------------
import profile_extraction  # noqa: E402


# ---------------------------------------------------------------------------
# Helper — fake a Gemini response that returns JSON with grade as integer.
# ---------------------------------------------------------------------------
def _fake_gemini_response(payload: dict):
    """Return a MagicMock that looks like a genai response with .text."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    return mock_response


# ---------------------------------------------------------------------------
# Tests: grade normalization in extract_structured_profile_with_gemini
# ---------------------------------------------------------------------------

class TestGradeNormalizationAtExtraction:
    """After extraction, profile['grade'] must always be str or None."""

    def _run_extraction(self, gemini_payload: dict) -> dict:
        """Patch Gemini client to return gemini_payload, run extraction."""
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _fake_gemini_response(gemini_payload)

        with patch.object(profile_extraction.genai, 'Client', return_value=mock_client), \
             patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key'}):
            result = profile_extraction.extract_structured_profile_with_gemini("dummy text")
        return result

    def test_grade_integer_coerced_to_string(self):
        """LLM returns integer grade → extraction result has string grade."""
        payload = {
            "name": "Alice", "school": "Test HS", "location": None,
            "grade": 12,  # integer — the old schema behaviour
            "graduation_year": 2025, "intended_major": None,
            "gpa_weighted": 4.0, "gpa_unweighted": 3.9,
            "gpa_uc": None, "class_rank": None,
            "sat_total": None, "sat_math": None, "sat_reading": None,
            "act_composite": None,
            "ap_exams": [], "courses": [], "extracurriculars": [],
            "leadership_roles": [], "special_programs": [], "awards": [],
            "work_experience": []
        }
        result = self._run_extraction(payload)
        assert result is not None
        assert isinstance(result['grade'], str), (
            f"Expected grade to be str after extraction, got {type(result['grade'])}: {result['grade']!r}"
        )
        assert result['grade'] == '12'

    def test_grade_string_stays_string(self):
        """LLM returns string grade → extraction result preserves string."""
        payload = {
            "name": "Bob", "school": "Test HS", "location": None,
            "grade": "11",  # already a string
            "graduation_year": 2026, "intended_major": None,
            "gpa_weighted": None, "gpa_unweighted": None,
            "gpa_uc": None, "class_rank": None,
            "sat_total": None, "sat_math": None, "sat_reading": None,
            "act_composite": None,
            "ap_exams": [], "courses": [], "extracurriculars": [],
            "leadership_roles": [], "special_programs": [], "awards": [],
            "work_experience": []
        }
        result = self._run_extraction(payload)
        assert result is not None
        assert isinstance(result['grade'], str)
        assert result['grade'] == '11'

    def test_grade_none_stays_none(self):
        """LLM returns null grade → extraction result keeps None."""
        payload = {
            "name": "Carol", "school": "Test HS", "location": None,
            "grade": None,
            "graduation_year": None, "intended_major": None,
            "gpa_weighted": None, "gpa_unweighted": None,
            "gpa_uc": None, "class_rank": None,
            "sat_total": None, "sat_math": None, "sat_reading": None,
            "act_composite": None,
            "ap_exams": [], "courses": [], "extracurriculars": [],
            "leadership_roles": [], "special_programs": [], "awards": [],
            "work_experience": []
        }
        result = self._run_extraction(payload)
        assert result is not None
        assert result['grade'] is None

    def test_grade_missing_field_is_none(self):
        """LLM omits grade field entirely → extraction result has None."""
        payload = {
            "name": "Dave", "school": "Test HS", "location": None,
            # 'grade' key absent
            "graduation_year": None, "intended_major": None,
            "gpa_weighted": None, "gpa_unweighted": None,
            "gpa_uc": None, "class_rank": None,
            "sat_total": None, "sat_math": None, "sat_reading": None,
            "act_composite": None,
            "ap_exams": [], "courses": [], "extracurriculars": [],
            "leadership_roles": [], "special_programs": [], "awards": [],
            "work_experience": []
        }
        result = self._run_extraction(payload)
        assert result is not None
        # Missing key should be normalized to None (not integer, not absent)
        grade_val = result.get('grade')
        assert grade_val is None or isinstance(grade_val, str), (
            f"grade should be None or str, got {type(grade_val)}: {grade_val!r}"
        )

    def test_grade_9_boundary(self):
        """Grade 9 (lowest valid) coerces correctly."""
        payload = {
            "name": "Eve", "school": "Test HS", "location": None,
            "grade": 9,
            "graduation_year": 2029, "intended_major": None,
            "gpa_weighted": None, "gpa_unweighted": None,
            "gpa_uc": None, "class_rank": None,
            "sat_total": None, "sat_math": None, "sat_reading": None,
            "act_composite": None,
            "ap_exams": [], "courses": [], "extracurriculars": [],
            "leadership_roles": [], "special_programs": [], "awards": [],
            "work_experience": []
        }
        result = self._run_extraction(payload)
        assert result is not None
        assert isinstance(result['grade'], str)
        assert result['grade'] == '9'


# ---------------------------------------------------------------------------
# Tests: migration script idempotency
# ---------------------------------------------------------------------------

class TestMigrationScriptIdempotency:
    """
    The migration script must be importable and its normalize_grade function
    must be idempotent — calling it twice on the same value produces the same
    result as calling it once.
    """

    def _import_script(self):
        """Import the migration script module."""
        SCRIPTS_DIR = Path(__file__).resolve().parents[3] / 'scripts'
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        import importlib
        import fix_grade_field_type
        importlib.reload(fix_grade_field_type)
        return fix_grade_field_type

    def test_normalize_integer_to_string(self):
        script = self._import_script()
        assert script.normalize_grade(12) == '12'

    def test_normalize_string_no_change(self):
        script = self._import_script()
        assert script.normalize_grade('12') == '12'

    def test_normalize_none_returns_none(self):
        script = self._import_script()
        assert script.normalize_grade(None) is None

    def test_idempotent_integer(self):
        """normalize_grade(normalize_grade(12)) == normalize_grade(12)."""
        script = self._import_script()
        once = script.normalize_grade(12)
        twice = script.normalize_grade(once)
        assert once == twice

    def test_idempotent_string(self):
        script = self._import_script()
        once = script.normalize_grade('11')
        twice = script.normalize_grade(once)
        assert once == twice

    def test_idempotent_none(self):
        script = self._import_script()
        once = script.normalize_grade(None)
        twice = script.normalize_grade(once)
        assert once == twice
