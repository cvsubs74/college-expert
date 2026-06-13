"""Scholarship.deadline_date round-trips and defaults to None (#191)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "agents" / "university_profile_collector"))

import model  # noqa: E402


def test_deadline_date_defaults_to_none():
    s = model.Scholarship(name="Regents Scholarship")
    assert s.deadline_date is None
    assert "deadline_date" in s.model_dump()


def test_deadline_date_round_trips():
    s = model.Scholarship(name="X", deadline="February 1, 2026", deadline_date="2026-02-01")
    dumped = s.model_dump()
    assert dumped["deadline_date"] == "2026-02-01"
    assert dumped["deadline"] == "February 1, 2026"  # free text retained alongside
    assert model.Scholarship(**dumped).deadline_date == "2026-02-01"
