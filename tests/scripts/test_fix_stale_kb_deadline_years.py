"""Unit tests for scripts/fix_stale_kb_deadline_years.py (KB-wide year sweep)."""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import fix_stale_kb_deadline_years as m  # noqa: E402


@pytest.mark.parametrize("month,dy,expected", [
    (11, 2026, 2025),  # fall → prior calendar year
    (12, 2026, 2025),
    (8, 2026, 2025),
    (1, 2026, 2026),   # winter/spring → cycle year
    (7, 2026, 2026),
    (1, 2027, 2027),   # relative to the doc's own cycle
])
def test_cycle_year(month, dy, expected):
    assert m.cycle_year(month, dy) == expected


class TestFixIsoYear:
    def test_stale_fall_deadline_shifts_back(self):
        assert m.fix_iso_year("2024-11-30", 2026) == "2025-11-30"

    def test_stale_winter_deadline_shifts_to_cycle_year(self):
        assert m.fix_iso_year("2025-01-15", 2026) == "2026-01-15"

    def test_future_overshoot_is_normalized_into_cycle(self):
        # A Nov date stored as 2026 in a 2026 cycle belongs to 2025.
        assert m.fix_iso_year("2026-11-01", 2026) == "2025-11-01"

    def test_already_correct_returns_none(self):
        assert m.fix_iso_year("2025-11-30", 2026) is None
        assert m.fix_iso_year("2026-01-15", 2026) is None

    @pytest.mark.parametrize("bad", [None, "", "2026", "Varies", 12345, ["2026-01-01"]])
    def test_unparseable_returns_none(self, bad):
        assert m.fix_iso_year(bad, 2026) is None

    def test_annotated_or_multidate_string_is_left_untouched(self):
        # Truncating these to the first date would lose data — never touch them.
        assert m.fix_iso_year("2024-11-08 (Single-Choice Early Action), 2025-01-09 (RD)", 2026) is None
        assert m.fix_iso_year("2024-11-01 (priority)", 2026) is None

    def test_leap_day_falls_back_to_feb_28(self):
        assert m.fix_iso_year("2024-02-29", 2027) == "2027-02-28"


def _doc(year=2026):
    return {
        "data_year": year,
        "profile": {
            "application_process": {"application_deadlines": [
                {"plan_type": "EA", "date": "2024-11-01"},   # stale
                {"plan_type": "RD", "date": "2026-01-02"},   # correct
            ]},
            "financials": {"scholarships": [
                {"name": "Sep", "amount": "$5k", "deadline_date": "2024-12-01"},  # stale
                {"name": "Auto", "deadline_date": None},                          # nothing to fix
            ]},
        },
    }


def _doc_with_supplementals():
    return {
        "data_year": 2026,
        "profile": {"application_process": {"supplemental_requirements": [
            {"type": "Portfolio", "deadline": "2024-12-01"},          # clean ISO, stale
            {"type": "Audition", "deadline": "2024-11-08 (EA), 2025-01-09 (RD)"},  # annotated
            {"type": "None", "deadline": None},
        ]}},
    }


def test_normalize_doc_fixes_clean_supplemental_deadline_only():
    new_doc, changes = m.normalize_doc(_doc_with_supplementals())
    srs = new_doc["profile"]["application_process"]["supplemental_requirements"]
    assert srs[0]["deadline"] == "2025-12-01"                              # clean ISO shifted
    assert srs[1]["deadline"] == "2024-11-08 (EA), 2025-01-09 (RD)"        # annotated left intact
    assert len(changes) == 1


def test_normalize_doc_fixes_stale_years_only():
    new_doc, changes = m.normalize_doc(_doc())
    dls = new_doc["profile"]["application_process"]["application_deadlines"]
    assert dls[0]["date"] == "2025-11-01"  # EA fixed
    assert dls[1]["date"] == "2026-01-02"  # RD untouched
    sch = new_doc["profile"]["financials"]["scholarships"]
    assert sch[0]["deadline_date"] == "2025-12-01"  # fixed
    assert sch[0]["amount"] == "$5k"                 # other fields preserved
    assert sch[1]["deadline_date"] is None
    assert len(changes) == 2


def test_normalize_doc_tolerates_string_entries():
    # Real data sometimes stores supplemental_requirements as plain strings.
    doc = {
        "data_year": 2026,
        "profile": {"application_process": {
            "supplemental_requirements": ["Portfolio required", {"type": "P", "deadline": "2024-11-15"}],
            "application_deadlines": ["see website", {"plan_type": "RD", "date": "2024-11-30"}],
        }},
    }
    new_doc, changes = m.normalize_doc(doc)
    assert len(changes) == 2  # the two dict entries fixed; strings ignored
    srs = new_doc["profile"]["application_process"]["supplemental_requirements"]
    assert srs[0] == "Portfolio required"
    assert srs[1]["deadline"] == "2025-11-15"


def test_normalize_doc_skips_unversioned():
    doc = _doc()
    doc.pop("data_year")
    _, changes = m.normalize_doc(doc)
    assert changes == []


def test_normalize_doc_is_idempotent_and_pure():
    src = _doc()
    once, _ = m.normalize_doc(src)
    twice, changes2 = m.normalize_doc(once)
    assert changes2 == []
    assert twice == once
    # input untouched
    assert src["profile"]["application_process"]["application_deadlines"][0]["date"] == "2024-11-01"
