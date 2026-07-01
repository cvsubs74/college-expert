"""Unit tests for year_history (sections projection + two-axis history) and
the main.py surfaces that expose them (#279)."""

import pytest


# --- project_profile_sections (pure) ---------------------------------------


class TestSectionProjection:
    def test_projects_requested_sections_only(self, kb):
        profile = {'metadata': {'a': 1}, 'financials': {'b': 2}, 'outcomes': {'c': 3}}
        projected, returned, unknown = kb.year_history.project_profile_sections(
            profile, ['financials', 'metadata'])
        assert projected == {'metadata': {'a': 1}, 'financials': {'b': 2}}
        assert sorted(returned) == ['financials', 'metadata']
        assert unknown == []

    def test_valid_but_absent_section_is_neither_returned_nor_unknown(self, kb):
        projected, returned, unknown = kb.year_history.project_profile_sections(
            {'metadata': {}}, ['metadata', 'student_retention'])
        assert returned == ['metadata']
        assert unknown == []
        assert 'student_retention' not in projected

    def test_typo_lands_in_unknown(self, kb):
        _, returned, unknown = kb.year_history.project_profile_sections(
            {'metadata': {}}, ['metadata', 'admissions'])
        assert returned == ['metadata']
        assert unknown == ['admissions']


class TestGetUniversitySections:
    def test_sections_param_projects_profile(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu', sections=['admissions_data'])
        assert result['success'] is True
        uni = result['university']
        assert list(uni['profile'].keys()) == ['admissions_data']
        assert uni['sections_returned'] == ['admissions_data']
        assert 'admissions_data' in uni['sections_available']
        assert 'unknown_sections' not in uni

    def test_all_unknown_sections_is_an_error(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu', sections=['admissions', 'financial'])
        assert result['success'] is False
        assert result['invalid_sections'] is True
        assert 'admissions_data' in result['error']  # lists valid names

    def test_partial_typo_reports_unknown_sections(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu', sections=['outcomes', 'financial'])
        assert result['success'] is True
        assert result['university']['sections_returned'] == ['outcomes']
        assert result['university']['unknown_sections'] == ['financial']

    def test_no_sections_param_leaves_response_shape_alone(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        uni = kb.main.get_university('testu')['university']
        assert 'sections_returned' not in uni
        assert 'sections_available' not in uni
        assert 'unknown_sections' not in uni
        assert uni['profile']['_id'] == 'testu'  # full profile intact

    def test_envelope_gains_rank_and_fit_category(self, kb, make_profile):
        """search_universities returns us_news_rank; get_university previously
        dropped it, so the connector's field read was always null."""
        kb.main.ingest_university(make_profile(), year=2026)
        uni = kb.main.get_university('testu')['university']
        assert uni['us_news_rank'] == 42
        assert uni['soft_fit_category'] == 'TARGET'


class TestYearReadSelfDescribes:
    def test_year_snapshot_read_backfills_available_years(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2025)
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu', year=2025)
        assert result['success'] is True
        assert result['university']['available_years'] == [2025, 2026]

    def test_year_miss_lists_available_years(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu', year=2020)
        assert result['success'] is False
        assert '2020' in result['error']
        assert '2026' in result['error']
        assert result['available_years'] == [2026]


# --- extract_year_summary (pure, defensive) ---------------------------------


class TestExtractYearSummary:
    def test_full_snapshot_row(self, kb):
        doc = {
            'data_year': 2026,
            'indexed_at': '2026-06-12T00:00:00+00:00',
            'profile': {
                'admissions_data': {
                    'current_status': {
                        'overall_acceptance_rate': 5.9,
                        'in_state_acceptance_rate': 12.0,
                        'is_test_optional': False,
                        'test_policy_details': 'Test Required',
                        'admits_class_size': 1650,
                        'early_admission_stats': [
                            {'plan_type': 'ED', 'acceptance_rate': 14.2,
                             'class_fill_percentage': 48.0},
                        ],
                    },
                    'admitted_student_profile': {
                        'gpa': {'weighted_middle_50': '4.1-4.5'},
                        'testing': {'sat_composite_middle_50': '1510-1560',
                                    'act_composite_middle_50': '34-36'},
                    },
                },
                'financials': {'cost_of_attendance_breakdown': {
                    'in_state': {'tuition': 17000.0, 'total_coa': 34000.0},
                    'out_of_state': {'tuition': 52000.0, 'total_coa': 69000.0},
                }},
                'strategic_profile': {'us_news_rank': 21},
                'application_process': {'application_deadlines': [
                    {'plan_type': 'ED', 'date': '2026-11-01', 'is_binding': True},
                ]},
            },
        }
        row = kb.year_history.extract_year_summary(doc)
        assert row['year'] == 2026
        assert row['cycle_label'] == '2026–27'
        assert row['source'] == 'kb_snapshot'
        assert row['vintage_estimated'] is False
        assert row['acceptance_rate'] == 5.9
        assert row['is_test_optional'] is False
        assert row['admits_class_size'] == 1650
        assert row['early_admission'] == [{'plan_type': 'ED', 'acceptance_rate': 14.2,
                                           'class_fill_percentage': 48.0}]
        assert row['sat_middle_50'] == '1510-1560'
        assert row['tuition_out_of_state'] == 52000.0
        assert row['total_coa_in_state'] == 34000.0
        assert row['us_news_rank'] == 21
        assert row['deadlines'] == [{'plan': 'ED', 'date': '2026-11-01', 'is_binding': True}]

    def test_fraction_style_rates_normalized(self, kb):
        """Pre-normalization snapshots carry 0.459 meaning 45.9%."""
        doc = {'data_year': 2024, 'profile': {'admissions_data': {'current_status': {
            'overall_acceptance_rate': 0.459}}}}
        row = kb.year_history.extract_year_summary(doc)
        assert row['acceptance_rate'] == 45.9

    def test_dual_deadline_key_spellings(self, kb):
        doc = {'data_year': 2025, 'profile': {'application_process': {
            'application_deadlines': [{'type': 'RD', 'deadline': '2026-01-05'}]}}}
        row = kb.year_history.extract_year_summary(doc)
        assert row['deadlines'] == [{'plan': 'RD', 'date': '2026-01-05', 'is_binding': None}]

    def test_empty_doc_yields_nulls_not_errors(self, kb):
        row = kb.year_history.extract_year_summary({})
        assert row['year'] is None
        assert row['cycle_label'] is None
        assert row['acceptance_rate'] is None
        assert row['deadlines'] == []

    def test_vintage_estimated_flag_propagates(self, kb):
        row = kb.year_history.extract_year_summary(
            {'data_year': 2025, 'vintage_estimated': True, 'profile': {}})
        assert row['vintage_estimated'] is True


# --- build_history / get_university_history ---------------------------------


def _trends():
    # Fresh copies per test — ingest normalizes percentages in place.
    return [
        {'year': 2024, 'cycle_name': 'Class of 2028', 'applications_total': 40000,
         'admits_total': 2400, 'acceptance_rate_overall': 6.0, 'yield_rate': 0.70},
        {'year': 2023, 'cycle_name': 'Class of 2027', 'applications_total': 38000,
         'admits_total': 2500, 'acceptance_rate_overall': 6.6},
    ]


class TestHistory:
    def test_multi_version_school(self, kb, make_profile):
        kb.main.ingest_university(make_profile(acceptance_rate=30.0), year=2025)
        kb.main.ingest_university(
            make_profile(acceptance_rate=25.0, longitudinal_trends=_trends()), year=2026)
        result = kb.main.get_university_history('testu')
        assert result['success'] is True
        assert result['available_years'] == [2025, 2026]
        years = [s['year'] for s in result['snapshots']]
        assert years == [2026, 2025]  # newest first
        assert result['snapshots'][0]['acceptance_rate'] == 25.0
        assert result['snapshots'][1]['acceptance_rate'] == 30.0
        # Trend rows are a SEPARATE structure, labeled unverified —
        # never merged into the snapshot timeline (different year axes).
        trend_years = [t['year'] for t in result['reported_trends']]
        assert trend_years == [2024, 2023]
        assert all(t['verified'] is False for t in result['reported_trends'])
        assert all(t['source'] == 'profile_trend' for t in result['reported_trends'])
        assert result['reported_trends'][0]['yield_rate'] == 70.0  # fraction normalized

    def test_years_filter(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2024)
        kb.main.ingest_university(make_profile(), year=2025)
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university_history('testu', years=[2024, 2026])
        assert [s['year'] for s in result['snapshots']] == [2026, 2024]
        assert result['available_years'] == [2024, 2025, 2026]  # coverage still full

    def test_zero_version_legacy_school(self, kb, make_profile):
        """The dominant prod shape today: a main doc that was never
        re-ingested under versioning — history degrades honestly."""
        doc = {'official_name': 'Legacy U',
               'profile': make_profile(uid='legacy', name='Legacy U',
                                       longitudinal_trends=_trends())}
        kb.db.collection.document('legacy').set(doc)
        result = kb.main.get_university_history('legacy')
        assert result['success'] is True
        assert len(result['snapshots']) == 1
        assert result['snapshots'][0]['source'] == 'kb_current'
        assert result['snapshots'][0]['year'] is None  # never guessed
        assert len(result['reported_trends']) == 2
        assert any('No versioned snapshots' in n for n in result['notes'])

    def test_auto_archived_snapshot_marked_estimated(self, kb, make_profile):
        """A legacy main doc auto-archived on first versioned ingest gets a
        guessed year — history must say so."""
        kb.db.collection.document('testu').set(
            {'official_name': 'Test University', 'profile': make_profile()})
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university_history('testu')
        estimated = [s for s in result['snapshots'] if s['vintage_estimated']]
        assert len(estimated) == 1
        assert estimated[0]['year'] == 2025  # ingest_year - 1 guess
        assert any('vintage_estimated' in n for n in result['notes'])

    def test_sections_mode(self, kb, make_profile):
        kb.main.ingest_university(make_profile(acceptance_rate=30.0), year=2025)
        kb.main.ingest_university(make_profile(acceptance_rate=25.0), year=2026)
        result = kb.main.get_university_history('testu', sections=['admissions_data'])
        assert result['success'] is True
        assert set(result['years'].keys()) == {'2025', '2026'}
        assert (result['years']['2026']['admissions_data']['current_status']
                ['overall_acceptance_rate']) == 25.0
        assert list(result['years']['2026'].keys()) == ['admissions_data']

    def test_sections_mode_all_unknown_is_error(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university_history('testu', sections=['bogus'])
        assert result['success'] is False
        assert result['invalid_sections'] is True

    def test_unknown_university(self, kb):
        result = kb.main.get_university_history('ghost')
        assert result['success'] is False
        assert 'not found' in result['error']
