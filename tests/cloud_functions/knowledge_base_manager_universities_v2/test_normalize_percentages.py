"""
Fraction-style percent normalization (versioning.normalize_percentages).

Research passes sometimes return 0.459 for 45.9%; no US university has a
sub-1% acceptance/yield/retention figure, so 0 < v < 1 on a percent-like
key unambiguously means a fraction. Found live: 98/191 universities in the
2026 refresh had fraction-style acceptance rates, miscategorizing e.g.
Auburn (45.9% → SAFETY) as SUPER_REACH.
"""

import kbv2_versioning as v  # registered in sys.modules by conftest.py


class TestNormalizePercentages:
    def test_fraction_acceptance_rate_converted(self):
        p = {'admissions_data': {'current_status': {'overall_acceptance_rate': 0.459}}}
        assert v.normalize_percentages(p) == 1
        assert p['admissions_data']['current_status']['overall_acceptance_rate'] == 45.9

    def test_percent_values_left_alone(self):
        p = {'admissions_data': {'current_status': {'overall_acceptance_rate': 4.62}}}
        assert v.normalize_percentages(p) == 0
        assert p['admissions_data']['current_status']['overall_acceptance_rate'] == 4.62

    def test_nested_lists_handled(self):
        p = {'admissions_data': {
            'current_status': {'early_admission_stats': [
                {'plan_type': 'ED', 'acceptance_rate': 0.105},
            ]},
            'longitudinal_trends': [
                {'year': 2025, 'acceptance_rate_overall': 0.0361, 'yield_rate': 0.84},
                {'year': 2024, 'acceptance_rate_overall': 3.9},
            ],
        }}
        assert v.normalize_percentages(p) == 3
        assert p['admissions_data']['current_status']['early_admission_stats'][0]['acceptance_rate'] == 10.5
        assert p['admissions_data']['longitudinal_trends'][0]['acceptance_rate_overall'] == 3.61
        assert p['admissions_data']['longitudinal_trends'][0]['yield_rate'] == 84.0
        assert p['admissions_data']['longitudinal_trends'][1]['acceptance_rate_overall'] == 3.9

    def test_retention_and_aid_fields_covered(self):
        p = {
            'student_retention': {'freshman_retention_rate': 0.97, 'graduation_rate_4_year': 0.88},
            'financials': {'percent_receiving_aid': 0.61},
            'admissions_data': {'admitted_student_profile': {'demographics': {
                'first_gen_percentage': 0.17,
                'geographic_breakdown': [{'region': 'Northeast', 'percentage': 0.42}],
            }}},
        }
        assert v.normalize_percentages(p) == 5
        assert p['student_retention']['freshman_retention_rate'] == 97.0
        assert p['financials']['percent_receiving_aid'] == 61.0
        assert p['admissions_data']['admitted_student_profile']['demographics']['geographic_breakdown'][0]['percentage'] == 42.0

    def test_loan_default_rate_excluded(self):
        # Sub-1% loan default rates are real — must not be inflated.
        p = {'outcomes': {'loan_default_rate': 0.5}}
        assert v.normalize_percentages(p) == 0
        assert p['outcomes']['loan_default_rate'] == 0.5

    def test_non_percent_keys_untouched(self):
        p = {'gpa': 0.9, 'score': 0.5, 'metadata': {'last_updated': '2026-06-12'}}
        assert v.normalize_percentages(p) == 0
        assert p['gpa'] == 0.9

    def test_zero_and_one_left_alone(self):
        # 0 is "no data"; exactly 1.0 is ambiguous — don't guess.
        p = {'admissions_data': {'current_status': {'overall_acceptance_rate': 1.0}},
             'student_retention': {'freshman_retention_rate': 0.0}}
        assert v.normalize_percentages(p) == 0
