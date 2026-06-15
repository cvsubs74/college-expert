"""index_student_profile is the merge-upsert behind POST /update-structured-profile
(the bulk profile write used by AI agents building a profile from a document).
Validates create + smart scalar/array merge with an injected fake DB."""

import sys
import types

# profile_operations pulls in heavy siblings (file_processing→fitz, profile_extraction,
# gcs_storage) that index_student_profile never uses — stub them so the import is
# CI-safe (the firestore client is already stubbed in conftest).
for _name, _attrs in {
    "file_processing": ["extract_text_from_file_content"],
    "profile_extraction": ["extract_profile_content", "evaluate_profile_changes"],
    "gcs_storage": ["upload_file_to_gcs", "delete_file_from_gcs"],
}.items():
    _mod = sys.modules.get(_name) or types.ModuleType(_name)
    for _a in _attrs:
        if not hasattr(_mod, _a):
            setattr(_mod, _a, lambda *a, **k: None)
    sys.modules[_name] = _mod

import profile_operations as po  # noqa: E402


class _FakeDB:
    def __init__(self, existing=None):
        self.existing = existing
        self.saved = None

    def get_profile(self, _uid):
        return self.existing

    def save_profile(self, _uid, document, merge=True):
        self.saved = document
        # reflect the write so a subsequent get_profile would see it
        self.existing = {**(self.existing or {}), **document}
        return True

    def save_file_metadata(self, *a, **k):
        return True


def _patch_db(monkeypatch, fake):
    monkeypatch.setattr(po, "get_db", lambda: fake)


U = "stu@example.com"


def test_creates_profile_from_scratch(monkeypatch):
    fake = _FakeDB(existing=None)
    _patch_db(monkeypatch, fake)
    profile = {
        "name": "Ada Lovelace", "intended_major": "CS", "sat_total": 1500,
        "courses": [{"name": "AP CS A", "type": "AP"}],
        "ap_exams": [{"subject": "Computer Science A", "score": 5}],
        "leadership_roles": ["Robotics Captain"],
    }
    res = po.index_student_profile(U, filename="transcript.pdf", content_markdown="", profile_data=profile)
    assert res["success"] is True
    doc = fake.saved
    assert doc["name"] == "Ada Lovelace" and doc["intended_major"] == "CS" and doc["sat_total"] == 1500
    assert doc["courses"][0]["name"] == "AP CS A"
    assert doc["ap_exams"][0]["score"] == 5
    assert doc["leadership_roles"] == ["Robotics Captain"]
    # provenance: the source filename is tracked
    assert "transcript.pdf" in doc["uploaded_files"]
    assert doc["field_sources"]["name"] == ["transcript.pdf"]


def test_merges_into_existing_profile(monkeypatch):
    existing = {
        "name": "Ada", "gpa_weighted": 4.2,
        "courses": [{"name": "AP CS A", "type": "AP"}],
        "uploaded_files": ["old.pdf"],
        "field_sources": {"name": ["old.pdf"]},
    }
    fake = _FakeDB(existing=existing)
    _patch_db(monkeypatch, fake)
    incoming = {
        "intended_major": "CS",                              # new scalar
        "name": None,                                        # null must not clobber existing
        "courses": [{"name": "AP Calc BC", "type": "AP"},    # new course
                    {"name": "AP CS A", "type": "AP"}],      # dup → deduped
    }
    res = po.index_student_profile(U, filename="resume.pdf", content_markdown="", profile_data=incoming)
    assert res["success"] is True
    doc = fake.saved
    assert doc["name"] == "Ada"               # preserved (incoming null ignored)
    assert doc["gpa_weighted"] == 4.2         # untouched existing scalar preserved
    assert doc["intended_major"] == "CS"      # new scalar applied
    course_names = sorted(c["name"] for c in doc["courses"])
    assert course_names == ["AP CS A", "AP Calc BC"]   # merged + deduped
