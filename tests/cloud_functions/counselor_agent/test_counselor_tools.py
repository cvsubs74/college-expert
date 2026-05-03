"""
Unit tests for cloud_functions/counselor_agent/counselor_tools.py.

Focuses on the deadline aggregation pipeline that powers /work-feed,
/deadlines, and /roadmap college-context translations:
  - extract_deadlines: KB profile JSON → normalized list, with the
    summer/spring filter from commit 7fb9e730
  - fetch_aggregated_deadlines: orchestrates college list + per-uni KB
    lookups. Stubs the HTTP calls.
"""

from unittest.mock import patch

import pytest

import counselor_tools as ct


# ---------------------------------------------------------------------------
# extract_deadlines — pure logic, no I/O
# ---------------------------------------------------------------------------

class TestExtractDeadlines:
    def test_normalizes_to_canonical_shape(self):
        uni_data = {
            'application_process': {
                'application_deadlines': [
                    {'plan_type': 'Regular Decision', 'date': '2027-01-05', 'notes': 'firm'},
                ],
            }
        }
        out = ct.extract_deadlines(uni_data)
        assert out == [{'type': 'Regular Decision', 'date': '2027-01-05', 'notes': 'firm'}]

    def test_falls_back_to_type_when_plan_type_missing(self):
        uni_data = {
            'application_process': {
                'application_deadlines': [{'type': 'Early Action', 'date': '2026-11-01'}],
            }
        }
        out = ct.extract_deadlines(uni_data)
        assert out[0]['type'] == 'Early Action'

    def test_default_type_when_neither_field_present(self):
        uni_data = {
            'application_process': {
                'application_deadlines': [{'date': '2026-11-01'}],
            }
        }
        out = ct.extract_deadlines(uni_data)
        assert out[0]['type'] == 'Regular Decision'

    def test_falls_back_to_deadline_field_when_date_missing(self):
        uni_data = {
            'application_process': {
                'application_deadlines': [{'deadline': '2026-11-01', 'plan_type': 'EA'}],
            }
        }
        out = ct.extract_deadlines(uni_data)
        assert out[0]['date'] == '2026-11-01'

    @pytest.mark.parametrize('excluded_type', [
        'summer semester', 'spring semester',
        'summer session', 'spring session',
        'SUMMER SEMESTER',                                    # case-insensitive
        'Spring Session',
    ])
    def test_summer_and_spring_semester_filtered_out(self, excluded_type):
        uni_data = {
            'application_process': {
                'application_deadlines': [
                    {'plan_type': excluded_type, 'date': '2026-08-01'},
                    {'plan_type': 'Regular Decision', 'date': '2027-01-05'},
                ],
            }
        }
        out = ct.extract_deadlines(uni_data)
        assert len(out) == 1
        assert out[0]['type'] == 'Regular Decision'

    def test_skips_entries_without_date(self):
        uni_data = {
            'application_process': {
                'application_deadlines': [
                    {'plan_type': 'TBD'},                     # no date
                    {'plan_type': 'RD', 'date': '2027-01-05'},
                ],
            }
        }
        out = ct.extract_deadlines(uni_data)
        assert len(out) == 1

    @pytest.mark.parametrize('input_data', [None, {}, {'application_process': {}}])
    def test_empty_or_missing_returns_empty(self, input_data):
        assert ct.extract_deadlines(input_data) == []


# ---------------------------------------------------------------------------
# fetch_aggregated_deadlines — composes get_college_list + get_university_data
# ---------------------------------------------------------------------------

class TestFetchAggregatedDeadlines:
    def test_returns_per_school_deadlines_sorted_by_date(self):
        college_list = [
            {'university_id': 'mit', 'university_name': 'MIT'},
            {'university_id': 'stanford', 'university_name': 'Stanford'},
        ]
        kb_data = {
            'mit': {
                'application_process': {
                    'application_deadlines': [
                        {'plan_type': 'Regular Decision', 'date': '2027-01-05'},
                    ],
                }
            },
            'stanford': {
                'application_process': {
                    'application_deadlines': [
                        {'plan_type': 'Restrictive Early Action', 'date': '2026-11-01'},
                    ],
                }
            },
        }

        with patch.object(ct, 'get_college_list', return_value=college_list), \
             patch.object(ct, 'get_university_data', side_effect=lambda uid: kb_data.get(uid)):
            result = ct.fetch_aggregated_deadlines('u@x.com')

        # Stanford EA (Nov 1) should sort before MIT RD (Jan 5).
        assert [d['university_name'] for d in result] == ['Stanford', 'MIT']
        assert result[0]['deadline_type'] == 'Restrictive Early Action'
        assert result[0]['date'] == '2026-11-01'

    def test_handles_missing_kb_data_gracefully(self):
        # College in list but KB lookup returns None → that school contributes
        # nothing to the aggregated list, but other schools still come through.
        college_list = [
            {'university_id': 'mit', 'university_name': 'MIT'},
            {'university_id': 'stanford', 'university_name': 'Stanford'},
        ]
        kb_data = {
            'mit': {
                'application_process': {
                    'application_deadlines': [
                        {'plan_type': 'Regular Decision', 'date': '2027-01-05'},
                    ],
                }
            },
            # stanford absent → get_university_data returns None
        }

        with patch.object(ct, 'get_college_list', return_value=college_list), \
             patch.object(ct, 'get_university_data', side_effect=lambda uid: kb_data.get(uid)):
            result = ct.fetch_aggregated_deadlines('u@x.com')

        assert len(result) == 1
        assert result[0]['university_name'] == 'MIT'

    def test_empty_college_list_returns_empty(self):
        with patch.object(ct, 'get_college_list', return_value=[]):
            assert ct.fetch_aggregated_deadlines('u@x.com') == []

    def test_non_iso_dates_pushed_to_end(self):
        # E.g., "Varies" — kept by extract_deadlines but should sort last.
        college_list = [
            {'university_id': 'a', 'university_name': 'A'},
            {'university_id': 'b', 'university_name': 'B'},
        ]
        kb_data = {
            'a': {
                'application_process': {
                    'application_deadlines': [{'plan_type': 'Rolling', 'date': 'Varies'}],
                }
            },
            'b': {
                'application_process': {
                    'application_deadlines': [{'plan_type': 'RD', 'date': '2027-01-05'}],
                }
            },
        }

        with patch.object(ct, 'get_college_list', return_value=college_list), \
             patch.object(ct, 'get_university_data', side_effect=lambda uid: kb_data.get(uid)):
            result = ct.fetch_aggregated_deadlines('u@x.com')

        # Real iso date sorts before "Varies".
        assert result[0]['date'] == '2027-01-05'
        assert result[-1]['date'] == 'Varies'


# ---------------------------------------------------------------------------
# HTTP-level helpers — best-effort; failures yield empty rather than raising.
# ---------------------------------------------------------------------------

class TestHttpHelpers:
    def test_get_college_list_returns_list_on_200(self):
        class _R:
            status_code = 200
            def json(self):
                return {'college_list': [{'university_id': 'mit'}]}
        with patch.object(ct.requests, 'get', return_value=_R()):
            assert ct.get_college_list('u@x.com') == [{'university_id': 'mit'}]

    def test_get_college_list_empty_on_non_200(self):
        class _R:
            status_code = 500
            text = 'oops'
        with patch.object(ct.requests, 'get', return_value=_R()):
            assert ct.get_college_list('u@x.com') == []

    def test_get_college_list_empty_on_exception(self):
        with patch.object(ct.requests, 'get', side_effect=ConnectionError('down')):
            assert ct.get_college_list('u@x.com') == []

    def test_get_university_data_returns_profile_on_200(self):
        class _R:
            status_code = 200
            def json(self):
                return {'university': {'profile': {'name': 'MIT'}}}
        with patch.object(ct.requests, 'get', return_value=_R()):
            assert ct.get_university_data('mit') == {'name': 'MIT'}

    def test_get_university_data_returns_none_on_non_200(self):
        class _R:
            status_code = 404
            text = 'not found'
        with patch.object(ct.requests, 'get', return_value=_R()):
            assert ct.get_university_data('mit') is None
