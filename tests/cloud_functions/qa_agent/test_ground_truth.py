"""
Tests for ground_truth.py — the runner's pre-scenario data fetcher.

For each college being added in a scenario, ground_truth.fetch_ground_truth()
queries knowledge_base_manager_universities_v2 and returns a dict keyed
by college_id with the canonical record (name, deadline, mascot,
essays_required, etc.). Cross-reference assertions later compare
runtime API responses against this snapshot.

A KB miss for a given college returns an empty record for that key
(NOT raising) — assertions depending on missing fields will mark
themselves SKIP.
"""

from __future__ import annotations

import pytest


class TestFetchGroundTruth:
    def test_fetches_record_per_college(self):
        import ground_truth

        # Fake "kb client" — pluggable so tests don't need real HTTP.
        canned = {
            "mit": {
                "id": "mit",
                "name": "MIT",
                "application_deadline": "2027-01-05",
                "deadline_type": "Regular Decision",
                "mascot": "Tim the Beaver",
                "supplemental_essays": [
                    {"prompt": "Why MIT?", "word_limit": 250, "required": True},
                    {"prompt": "Maker's portfolio", "word_limit": 200, "required": False},
                ],
            },
            "stanford_university": {
                "id": "stanford_university",
                "name": "Stanford University",
                "application_deadline": "2027-01-02",
                "supplemental_essays": [
                    {"prompt": "What matters to you?", "required": True},
                ],
            },
        }

        def fake_kb(college_id):
            return canned.get(college_id)

        truth = ground_truth.fetch_ground_truth(
            ["mit", "stanford_university"],
            kb_client=fake_kb,
        )
        assert "mit" in truth
        assert truth["mit"]["name"] == "MIT"
        assert truth["mit"]["application_deadline"] == "2027-01-05"
        # essays_required is computed: count of required=True
        assert truth["mit"]["essays_required"] == 1
        assert truth["stanford_university"]["essays_required"] == 1

    def test_kb_miss_returns_empty_record(self):
        import ground_truth

        def fake_kb(college_id):
            return None  # always a miss

        truth = ground_truth.fetch_ground_truth(
            ["unknown_school"],
            kb_client=fake_kb,
        )
        # Key still present (so assertions can find it), but record empty.
        assert "unknown_school" in truth
        assert truth["unknown_school"] == {}

    def test_handles_kb_partial_response(self):
        """The KB record might lack supplemental_essays — handle without
        crashing."""
        import ground_truth

        def fake_kb(college_id):
            return {"id": "x", "name": "X University"}

        truth = ground_truth.fetch_ground_truth(["x"], kb_client=fake_kb)
        assert truth["x"]["name"] == "X University"
        # essays_required defaults to 0 when supplemental_essays missing.
        assert truth["x"].get("essays_required", 0) == 0

    def test_kb_client_exception_is_treated_as_miss(self):
        """If the KB client raises, treat it as a miss for that college
        (don't crash the whole truth gather)."""
        import ground_truth

        def fake_kb(college_id):
            if college_id == "broken":
                raise RuntimeError("kb timeout")
            return {"id": college_id, "name": "OK"}

        truth = ground_truth.fetch_ground_truth(
            ["broken", "ok"], kb_client=fake_kb,
        )
        assert truth["broken"] == {}
        assert truth["ok"]["name"] == "OK"
