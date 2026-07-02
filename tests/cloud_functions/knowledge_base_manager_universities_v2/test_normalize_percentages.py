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
        # #289: demographic slice fields (first_gen_percentage, geographic
        # 'percentage') are now EXCLUDED — genuine sub-1% slices exist, so a
        # sub-1 value there is ambiguous and must not be transformed.
        # Retention/aid keep normalizing (no legitimate sub-1% values).
        p = {
            'student_retention': {'freshman_retention_rate': 0.97, 'graduation_rate_4_year': 0.88},
            'financials': {'percent_receiving_aid': 0.61},
            'admissions_data': {'admitted_student_profile': {'demographics': {
                'first_gen_percentage': 0.17,
                'geographic_breakdown': [{'region': 'Northeast', 'percentage': 0.42}],
            }}},
        }
        assert v.normalize_percentages(p) == 3
        assert p['student_retention']['freshman_retention_rate'] == 97.0
        assert p['financials']['percent_receiving_aid'] == 61.0
        demo = p['admissions_data']['admitted_student_profile']['demographics']
        assert demo['first_gen_percentage'] == 0.17
        assert demo['geographic_breakdown'][0]['percentage'] == 0.42

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


class TestSub1PercentFieldsNotCorrupted:
    """#289: rare-event rates and small population slices have GENUINE sub-1%
    values — the fraction heuristic must never touch them. All three shapes
    below are real corpus data that the old rule corrupted."""

    def test_harvard_transfer_rate_stays_sub_1pct(self):
        p = {'admissions_data': {'current_status': {
            'overall_acceptance_rate': 3.4,       # safe family, untouched (>1)
            'transfer_acceptance_rate': 0.8,      # a REAL 0.8% — was becoming 80.0
        }}}
        assert v.normalize_percentages(p) == 0
        assert p['admissions_data']['current_status']['transfer_acceptance_rate'] == 0.8

    def test_cmu_waitlist_series_not_mixed_unit(self):
        p = {'admissions_data': {'longitudinal_trends': [
            {'year': y, 'waitlist_stats': {'waitlist_admit_rate': r}}
            for y, r in [(2025, 1.5), (2024, 0.9), (2023, 8.3), (2022, 0.4)]
        ]}}
        assert v.normalize_percentages(p) == 0
        rates = [t['waitlist_stats']['waitlist_admit_rate']
                 for t in p['admissions_data']['longitudinal_trends']]
        assert rates == [1.5, 0.9, 8.3, 0.4]      # same-unit series preserved

    def test_clemson_demographic_slices_untouched(self):
        p = {'admissions_data': {'admitted_student_profile': {'demographics': {
            'international_percentage': 0.84,     # a real 0.84% slice
            'first_gen_percentage': 0.5,
            'legacy_percentage': 0.9,
            'geographic_breakdown': [
                {'region': 'Alaska', 'percentage': 0.2},
            ],
        }}}}
        assert v.normalize_percentages(p) == 0
        demo = p['admissions_data']['admitted_student_profile']['demographics']
        assert demo['international_percentage'] == 0.84
        assert demo['geographic_breakdown'][0]['percentage'] == 0.2

    def test_safe_family_still_normalizes(self):
        """The fix must not weaken the original regression: overall
        acceptance/yield fractions still convert."""
        p = {'admissions_data': {
            'current_status': {'overall_acceptance_rate': 0.459},
            'longitudinal_trends': [{'year': 2025, 'yield_rate': 0.84}],
        }}
        assert v.normalize_percentages(p) == 2
        assert p['admissions_data']['current_status']['overall_acceptance_rate'] == 45.9

    def test_share_groups_summing_to_one_are_provable_fractions(self):
        """#289: a geographic breakdown whose slices sum to ~1.0 is arithmetic
        proof of fraction storage (USF: [0.8, 0.13, 0.07]) — convert the whole
        group. Groups NOT summing to ~1 stay untouched (ambiguous)."""
        p = {'admissions_data': {'admitted_student_profile': {'demographics': {
            'geographic_breakdown': [
                {'region': 'FL', 'percentage': 0.8},
                {'region': 'Southeast', 'percentage': 0.13},
                {'region': 'Other', 'percentage': 0.07},
            ]}}}}
        assert v.normalize_percentages(p) == 3
        gb = p['admissions_data']['admitted_student_profile']['demographics']['geographic_breakdown']
        assert [g['percentage'] for g in gb] == [80.0, 13.0, 7.0]

        q = {'demographics': {'geographic_breakdown': [
            {'region': 'Alaska', 'percentage': 0.2},
            {'region': 'Hawaii', 'percentage': 0.3},
        ]}}
        assert v.normalize_percentages(q) == 0   # sums to 0.5 — not provable
        assert q['demographics']['geographic_breakdown'][0]['percentage'] == 0.2

    def test_share_group_conversion_is_idempotent(self):
        p = {'geographic_breakdown': [
            {'region': 'A', 'percentage': 0.6}, {'region': 'B', 'percentage': 0.4}]}
        assert v.normalize_percentages(p) == 2
        assert v.normalize_percentages(p) == 0   # second pass: already percents
