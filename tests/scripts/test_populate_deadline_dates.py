"""Unit tests for scripts/populate_deadline_dates.py (#191).

apply_to_doc is pure (no Firestore); migrate() is exercised against a fake DB.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import populate_deadline_dates as m  # noqa: E402


def _doc():
    return {
        "data_year": 2026,
        "university_id": "x",
        "available_years": [2025, 2026],
        "profile": {
            "application_process": {
                "application_deadlines": [
                    {"plan_type": "EA", "date": "2024-11-01"},
                    {"plan_type": "RD", "date": "2026-01-02"},
                ]
            },
            "financials": {
                "scholarships": [
                    {"name": "Sep App", "deadline": "Jan 15", "amount": "$5k",
                     "application_method": "Separate Application"},
                    {"name": "Auto", "deadline": "Automatic", "amount": "$1k"},
                ]
            },
        },
    }


MAP = {
    "application_deadlines": {"2024-11-01": "2025-11-01"},
    "scholarships": {"Sep App": "2026-01-15", "Auto": None},
}


def _scholar(doc, name):
    for s in doc["profile"]["financials"]["scholarships"]:
        if s["name"] == name:
            return s
    raise AssertionError(name)


def test_sets_scholarship_deadline_date_by_name():
    new_doc, changes = m.apply_to_doc(_doc(), MAP)
    assert _scholar(new_doc, "Sep App")["deadline_date"] == "2026-01-15"
    auto = _scholar(new_doc, "Auto")
    assert "deadline_date" in auto and auto["deadline_date"] is None
    assert any("Sep App" in c for c in changes)


def test_refreshes_application_deadline_by_existing_value():
    new_doc, _ = m.apply_to_doc(_doc(), MAP)
    dls = new_doc["profile"]["application_process"]["application_deadlines"]
    assert dls[0]["date"] == "2025-11-01"   # EA refreshed
    assert dls[1]["date"] == "2026-01-02"   # RD untouched (not in map)


def test_preserves_other_fields_and_does_not_mutate_input():
    src = _doc()
    new_doc, _ = m.apply_to_doc(src, MAP)
    assert _scholar(new_doc, "Sep App")["amount"] == "$5k"
    assert _scholar(new_doc, "Sep App")["application_method"] == "Separate Application"
    assert new_doc["available_years"] == [2025, 2026]
    # input untouched (deep copy)
    assert "deadline_date" not in _scholar(src, "Sep App")


def test_idempotent_second_pass_has_no_material_changes():
    once, _ = m.apply_to_doc(_doc(), MAP)
    twice, changes = m.apply_to_doc(once, MAP)
    material = [c for c in changes if not c.startswith("WARNING")]
    assert material == []
    assert twice == once


def test_unknown_scholarship_name_warns_not_crashes():
    _, changes = m.apply_to_doc(_doc(), {"scholarships": {"Nope": "2026-01-01"}})
    assert any(c.startswith("WARNING") and "Nope" in c for c in changes)


class _FakeDB:
    def __init__(self, docs):
        self.docs = docs
        self.saved = []

    def get_university(self, uid):
        return self.docs.get(uid)

    def save_university(self, uid, data, year):
        self.saved.append((uid, data, year))
        return {"saved": True, "promoted": True, "available_years": [year]}


@pytest.fixture
def _pilot(monkeypatch):
    monkeypatch.setattr(m, "PILOT", {"x": MAP})


def test_migrate_dry_run_writes_nothing(_pilot):
    db = _FakeDB({"x": _doc()})
    n = m.migrate(db, dry_run=True)
    assert n > 0            # changes detected
    assert db.saved == []   # but nothing written


def test_migrate_apply_writes_with_current_year(_pilot):
    db = _FakeDB({"x": _doc()})
    m.migrate(db, dry_run=False)
    assert len(db.saved) == 1
    uid, data, year = db.saved[0]
    assert uid == "x" and year == 2026
    assert _scholar(data, "Sep App")["deadline_date"] == "2026-01-15"


def test_migrate_skips_unversioned_or_missing(_pilot):
    db = _FakeDB({"x": {"profile": {}}})  # no data_year
    m.migrate(db, dry_run=False)
    assert db.saved == []
