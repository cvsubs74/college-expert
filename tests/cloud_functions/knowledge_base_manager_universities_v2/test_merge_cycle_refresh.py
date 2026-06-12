"""
Yearly-refresh merge (versioning.merge_cycle_refresh): a fresh, possibly
thinner collection refreshes cycle-sensitive facts without degrading the
durable rich sections of the current profile.
"""

import kbv2_versioning as v  # registered in sys.modules by conftest.py


def _base():
    return {
        '_id': 'testu',
        'metadata': {'official_name': 'Test University', 'last_updated': '2025-03-01'},
        'admissions_data': {
            'current_status': {'overall_acceptance_rate': 4.4, 'is_test_optional': True},
            'longitudinal_trends': [
                {'year': 2024, 'cycle_name': 'Class of 2028', 'acceptance_rate_overall': 4.4},
                {'year': 2023, 'cycle_name': 'Class of 2027', 'acceptance_rate_overall': 4.5},
            ],
            'admitted_student_profile': {'gpa': {'unweighted_middle_50': '3.9-4.0'}},
        },
        'academic_structure': {
            'colleges': [{'name': 'Engineering', 'majors': [{'name': 'CS'}, {'name': 'MechE'}]}],
        },
        'application_process': {
            'application_deadlines': [{'plan_type': 'EA', 'date': '2024-11-01'}],
            'holistic_factors': {'essay_importance': 'Critical'},
        },
        'strategic_profile': {'us_news_rank': 2, 'market_position': 'Elite Private'},
        'student_insights': {'essay_tips': ['Be specific', 'Show fit']},
        'financials': {
            'aid_philosophy': '100% Need Met',
            'cost_of_attendance_breakdown': {'academic_year': '2024-2025'},
        },
    }


def _fresh():
    # Thinner pass: new cycle facts, but missing the rich durable sections.
    return {
        '_id': 'testu',
        'metadata': {'official_name': 'Test University', 'last_updated': '2026-06-12'},
        'admissions_data': {
            'current_status': {'overall_acceptance_rate': 4.62, 'is_test_optional': False},
            'longitudinal_trends': [
                {'year': 2025, 'cycle_name': 'Class of 2029', 'acceptance_rate_overall': 4.62},
                {'year': 2024, 'cycle_name': 'Class of 2028', 'acceptance_rate_overall': 4.46},
            ],
        },
        'application_process': {
            'application_deadlines': [
                {'plan_type': 'EA', 'date': '2025-11-01'},
                {'plan_type': 'RD', 'date': '2026-01-01'},
            ],
        },
        'strategic_profile': {'us_news_rank': 1},
        'financials': {'cost_of_attendance_breakdown': {'academic_year': '2025-2026'}},
        'outcomes': {'median_earnings_10yr': 110000},
    }


class TestMergeCycleRefresh:
    def test_cycle_sensitive_sections_come_from_fresh(self):
        m = v.merge_cycle_refresh(_base(), _fresh())
        assert m['admissions_data']['current_status']['overall_acceptance_rate'] == 4.62
        assert m['admissions_data']['current_status']['is_test_optional'] is False
        assert m['strategic_profile']['us_news_rank'] == 1
        assert m['metadata']['last_updated'] == '2026-06-12'
        assert [d['plan_type'] for d in m['application_process']['application_deadlines']] == ['EA', 'RD']
        assert m['financials']['cost_of_attendance_breakdown']['academic_year'] == '2025-2026'

    def test_durable_rich_sections_kept_from_base(self):
        m = v.merge_cycle_refresh(_base(), _fresh())
        assert m['academic_structure'] == _base()['academic_structure']
        assert m['student_insights'] == _base()['student_insights']
        assert m['application_process']['holistic_factors'] == {'essay_importance': 'Critical'}
        assert m['admissions_data']['admitted_student_profile']['gpa']['unweighted_middle_50'] == '3.9-4.0'
        assert m['strategic_profile']['market_position'] == 'Elite Private'
        assert m['financials']['aid_philosophy'] == '100% Need Met'

    def test_trends_unioned_by_year_fresh_wins_collision(self):
        m = v.merge_cycle_refresh(_base(), _fresh())
        trends = m['admissions_data']['longitudinal_trends']
        assert [t['year'] for t in trends] == [2025, 2024, 2023]
        # 2024 collision: fresh value (4.46) replaces base (4.4)
        t2024 = next(t for t in trends if t['year'] == 2024)
        assert t2024['acceptance_rate_overall'] == 4.46

    def test_fresh_only_sections_are_added(self):
        m = v.merge_cycle_refresh(_base(), _fresh())
        assert m['outcomes']['median_earnings_10yr'] == 110000

    def test_empty_fresh_section_does_not_clobber_base(self):
        fresh = _fresh()
        fresh['application_process']['application_deadlines'] = []
        m = v.merge_cycle_refresh(_base(), fresh)
        assert m['application_process']['application_deadlines'] == \
            _base()['application_process']['application_deadlines']

    def test_inputs_not_mutated(self):
        base, fresh = _base(), _fresh()
        import copy
        base_copy, fresh_copy = copy.deepcopy(base), copy.deepcopy(fresh)
        v.merge_cycle_refresh(base, fresh)
        assert base == base_copy
        assert fresh == fresh_copy

    def test_merge_with_empty_base_returns_fresh_content(self):
        m = v.merge_cycle_refresh({}, _fresh())
        assert m['admissions_data']['current_status']['overall_acceptance_rate'] == 4.62
        assert m['strategic_profile']['us_news_rank'] == 1
