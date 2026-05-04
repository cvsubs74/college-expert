"""
Sanity tests pinning the contract that every static scenario JSON
ships with a `business_rationale` field readable by a non-engineer.

The QA dashboard renders this field as the primary "why does this test
matter" explanation. Without it the dashboard falls back to the short
`description`, but that's not great UX — so we lock the requirement in
a test rather than relying on review discipline.

Spec: docs/prd/qa-dashboard-insights.md (Feature B), PR-I.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


SCENARIOS_DIR = (
    Path(__file__).resolve().parents[3]
    / "cloud_functions" / "qa_agent" / "scenarios"
)


def _scenario_files():
    """Return all scenario JSON files (excludes colleges_allowlist.json
    which is a config doc, not a scenario)."""
    out = []
    for p in sorted(SCENARIOS_DIR.glob("*.json")):
        if p.name == "colleges_allowlist.json":
            continue
        out.append(p)
    return out


class TestScenariosHaveBusinessRationale:
    @pytest.mark.parametrize("path", _scenario_files(), ids=lambda p: p.name)
    def test_field_present(self, path):
        data = json.loads(path.read_text())
        assert "business_rationale" in data, (
            f"{path.name} is missing the `business_rationale` field. "
            f"Add a 1-2 sentence plain-English explanation of what this "
            f"scenario validates and why it matters."
        )

    @pytest.mark.parametrize("path", _scenario_files(), ids=lambda p: p.name)
    def test_field_is_meaningful_string(self, path):
        data = json.loads(path.read_text())
        rationale = data.get("business_rationale")
        assert isinstance(rationale, str), f"{path.name}: rationale must be a string"
        assert len(rationale) >= 30, (
            f"{path.name}: rationale should be at least 30 chars "
            f"(a real sentence). Got {len(rationale)} chars: {rationale!r}"
        )
        assert len(rationale) <= 500, (
            f"{path.name}: rationale should be 1-2 sentences "
            f"(under 500 chars), got {len(rationale)} chars"
        )

    @pytest.mark.parametrize("path", _scenario_files(), ids=lambda p: p.name)
    def test_does_not_repeat_description_verbatim(self, path):
        """The rationale should add value over the bare description —
        if they're identical, the field isn't earning its keep."""
        data = json.loads(path.read_text())
        description = data.get("description", "")
        rationale = data.get("business_rationale", "")
        if description and rationale:
            assert description.strip() != rationale.strip(), (
                f"{path.name}: business_rationale is identical to description; "
                f"it should explain WHY the test matters, not just WHAT it does."
            )
