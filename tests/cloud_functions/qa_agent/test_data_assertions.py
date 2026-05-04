"""
Tests for data_assertions.py — the cross-reference assertion library.

Cross-reference assertions compare a response against a "ground truth"
bag the runner has populated before the scenario runs (typically from
the knowledge base). They power the user's ask: "validate every bit of
information being fetched, make sure they are accurate."

Each assertion returns an AssertionResult that carries `expected` and
`actual` fields — so when an assertion fails, the dashboard renders a
two-column diff showing what we expected vs what we got.

Tests written before implementation per the workflow rule.
"""

from __future__ import annotations

import pytest


# ---- value_equals_truth ----------------------------------------------------


class TestValueEqualsTruth:
    def test_pass_when_response_matches_truth(self):
        import data_assertions
        ctx = {
            "response_json": {"college": {"deadline": "2027-01-05"}},
            "truth_bag": {"mit": {"application_deadline": "2027-01-05"}},
        }
        fn = data_assertions.value_equals_truth(
            "college.deadline", "mit.application_deadline"
        )
        result = fn(ctx)
        assert result.passed is True
        assert result.expected == "2027-01-05"
        assert result.actual == "2027-01-05"

    def test_fail_records_both_values(self):
        import data_assertions
        ctx = {
            "response_json": {"college": {"deadline": "2027-01-15"}},
            "truth_bag": {"mit": {"application_deadline": "2027-01-05"}},
        }
        fn = data_assertions.value_equals_truth(
            "college.deadline", "mit.application_deadline"
        )
        result = fn(ctx)
        assert result.passed is False
        assert result.expected == "2027-01-05"
        assert result.actual == "2027-01-15"

    def test_skip_when_truth_missing(self):
        """If the KB didn't have a record for the college, mark the
        assertion SKIP rather than fail. The runner shouldn't penalize
        tests for missing-from-KB data."""
        import data_assertions
        ctx = {
            "response_json": {"college": {"deadline": "2027-01-05"}},
            "truth_bag": {},
        }
        fn = data_assertions.value_equals_truth(
            "college.deadline", "missing.application_deadline"
        )
        result = fn(ctx)
        assert result.skipped is True


# ---- list_matches_truth_set -----------------------------------------------


class TestListMatchesTruthSet:
    def test_pass_when_sets_equal_regardless_of_order(self):
        import data_assertions
        ctx = {
            "response_json": {"college_list": [
                {"university_id": "stanford"},
                {"university_id": "mit"},
            ]},
        }
        fn = data_assertions.list_matches_truth_set(
            "college_list", id_key="university_id",
            expected_ids=["mit", "stanford"],
        )
        result = fn(ctx)
        assert result.passed is True

    def test_fail_when_sets_differ(self):
        import data_assertions
        ctx = {
            "response_json": {"college_list": [
                {"university_id": "stanford"},
                # missing MIT
            ]},
        }
        fn = data_assertions.list_matches_truth_set(
            "college_list", id_key="university_id",
            expected_ids=["mit", "stanford"],
        )
        result = fn(ctx)
        assert result.passed is False
        assert "mit" in (result.message or "")

    def test_fail_when_orphans_present(self):
        """A college appearing in the response that wasn't expected
        should fail (orphan / leak)."""
        import data_assertions
        ctx = {
            "response_json": {"college_list": [
                {"university_id": "mit"},
                {"university_id": "stanford"},
                {"university_id": "harvard"},  # orphan
            ]},
        }
        fn = data_assertions.list_matches_truth_set(
            "college_list", id_key="university_id",
            expected_ids=["mit", "stanford"],
        )
        result = fn(ctx)
        assert result.passed is False


# ---- per_university_count_matches -----------------------------------------


class TestPerUniversityCountMatches:
    def test_counts_match(self):
        import data_assertions
        ctx = {
            "response_json": {"essays": [
                {"university_id": "mit"},
                {"university_id": "mit"},
                {"university_id": "stanford"},
            ]},
            "truth_bag": {
                "mit": {"essays_required": 2},
                "stanford": {"essays_required": 1},
            },
        }
        fn = data_assertions.per_university_count_matches(
            list_path="essays", id_key="university_id",
            truth_count_path="essays_required",
        )
        result = fn(ctx)
        assert result.passed is True

    def test_fail_when_count_short(self):
        import data_assertions
        ctx = {
            "response_json": {"essays": [
                {"university_id": "mit"},
                # MIT requires 2, only 1 in tracker
            ]},
            "truth_bag": {
                "mit": {"essays_required": 2},
            },
        }
        fn = data_assertions.per_university_count_matches(
            list_path="essays", id_key="university_id",
            truth_count_path="essays_required",
        )
        result = fn(ctx)
        assert result.passed is False


# ---- deep_link_resolves ---------------------------------------------------


class TestDeepLinkResolves:
    def test_pass_when_all_links_in_set(self):
        import data_assertions
        ctx = {
            "response_json": {"phases": [
                {"tasks": [
                    {"artifact_ref": {"university_id": "mit"}},
                    {"artifact_ref": {"university_id": "stanford"}},
                ]},
            ]},
        }
        fn = data_assertions.deep_link_resolves(
            list_path="phases[*].tasks[*]",
            id_path="artifact_ref.university_id",
            valid_ids=["mit", "stanford", "harvard"],
        )
        result = fn(ctx)
        assert result.passed is True

    def test_fail_on_orphan_link(self):
        import data_assertions
        ctx = {
            "response_json": {"phases": [
                {"tasks": [
                    {"artifact_ref": {"university_id": "mit"}},
                    {"artifact_ref": {"university_id": "fake_school"}},  # orphan
                ]},
            ]},
        }
        fn = data_assertions.deep_link_resolves(
            list_path="phases[*].tasks[*]",
            id_path="artifact_ref.university_id",
            valid_ids=["mit", "stanford"],
        )
        result = fn(ctx)
        assert result.passed is False
        assert "fake_school" in (result.message or "")

    def test_pass_when_no_artifact_refs_present(self):
        """Tasks without artifact_ref are fine — they just don't
        contribute to the check."""
        import data_assertions
        ctx = {
            "response_json": {"phases": [
                {"tasks": [
                    {"title": "no link"},
                    {"artifact_ref": {"university_id": "mit"}},
                ]},
            ]},
        }
        fn = data_assertions.deep_link_resolves(
            list_path="phases[*].tasks[*]",
            id_path="artifact_ref.university_id",
            valid_ids=["mit"],
        )
        result = fn(ctx)
        assert result.passed is True
