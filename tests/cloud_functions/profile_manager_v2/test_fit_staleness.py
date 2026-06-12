"""
KB provenance stamping + staleness classification (#204).

Pure-unit: classify_kb_changes / build_kb_provenance are deterministic and
network-free; get_kb_updates takes an injected batch fetcher.
"""

import fit_staleness as fs


def _uni(data_year=2026, rate=35.2, policy='Test optional',
         deadlines=None, coa=86000, name='Northeastern University'):
    return {
        'university_id': 'northeastern',
        'official_name': name,
        'data_year': data_year,
        'last_updated': '2026-06-12T20:00:00+00:00',
        'profile': {
            'admissions_data': {'current_status': {
                'overall_acceptance_rate': rate,
                'test_policy_details': policy,
            }},
            'application_process': {'application_deadlines': deadlines if deadlines is not None else [
                {'plan_type': 'ED', 'date': '2026-11-01'},
                {'plan_type': 'RD', 'date': '2027-01-15'},
            ]},
            'financials': {'cost_of_attendance_breakdown': {
                'out_of_state': {'total_coa': coa},
            }},
        },
    }


def _fit(kb_year=2025, rate=44.0, policy='Test optional',
         deadlines_uni=None, coa=82000, category='SAFETY'):
    snapshot_source = _uni(data_year=kb_year, rate=rate, policy=policy,
                           deadlines=deadlines_uni, coa=coa)
    fit = {
        'university_id': 'northeastern',
        'university_name': 'Northeastern University',
        'fit_category': category,
        'match_percentage': 82,
    }
    fit.update(fs.build_kb_provenance(snapshot_source))
    return fit


class TestBuildKbProvenance:
    def test_stamps_year_timestamp_and_inputs(self):
        prov = fs.build_kb_provenance(_uni())
        assert prov['kb_data_year'] == 2026
        assert prov['kb_last_updated'] == '2026-06-12T20:00:00+00:00'
        snap = prov['input_snapshot']
        assert snap['acceptance_rate'] == 35.2
        assert snap['test_policy'] == 'Test optional'
        assert snap['total_coa'] == 86000
        assert isinstance(snap['deadlines_hash'], str) and len(snap['deadlines_hash']) == 40

    def test_deadlines_hash_is_order_insensitive(self):
        a = _uni(deadlines=[{'plan_type': 'ED', 'date': '2026-11-01'},
                            {'plan_type': 'RD', 'date': '2027-01-15'}])
        b = _uni(deadlines=[{'plan_type': 'RD', 'date': '2027-01-15'},
                            {'plan_type': 'ED', 'date': '2026-11-01'}])
        assert (fs.build_kb_provenance(a)['input_snapshot']['deadlines_hash']
                == fs.build_kb_provenance(b)['input_snapshot']['deadlines_hash'])


class TestSelectivityRules:
    def test_tiers_pin_fit_computation_thresholds(self):
        assert fs.selectivity_tier(4) == 'ULTRA_SELECTIVE'
        assert fs.selectivity_tier(8) == 'HIGHLY_SELECTIVE'
        assert fs.selectivity_tier(15) == 'VERY_SELECTIVE'
        assert fs.selectivity_tier(25) == 'SELECTIVE'
        assert fs.selectivity_tier(40) == 'ACCESSIBLE'

    def test_floors(self):
        assert fs.category_floor(4) == 'SUPER_REACH'
        assert fs.category_floor(10) == 'REACH'
        assert fs.category_floor(20) is None


class TestClassifyKbChanges:
    def test_current_fit_returns_none(self):
        fit = _fit(kb_year=2026, rate=35.2)
        assert fs.classify_kb_changes(fit, _uni(data_year=2026)) is None

    def test_tier_crossing_rate_change_is_material(self):
        # 44% (ACCESSIBLE) → 35.2% (SELECTIVE): tier crossed
        entry = fs.classify_kb_changes(_fit(rate=44.0), _uni(rate=35.2))
        rate_change = next(c for c in entry['changes'] if c['field'] == 'acceptance_rate')
        assert rate_change['severity'] == 'material'
        assert rate_change['old'] == 44.0 and rate_change['new'] == 35.2

    def test_big_move_within_no_tier_is_material(self):
        # 50 → 43: both ACCESSIBLE, but >5 points
        entry = fs.classify_kb_changes(_fit(rate=50.0), _uni(rate=43.0))
        rate_change = next(c for c in entry['changes'] if c['field'] == 'acceptance_rate')
        assert rate_change['severity'] == 'material'

    def test_small_within_tier_drift_is_minor(self):
        entry = fs.classify_kb_changes(_fit(rate=44.0), _uni(rate=46.0))
        rate_change = next(c for c in entry['changes'] if c['field'] == 'acceptance_rate')
        assert rate_change['severity'] == 'minor'

    def test_deadline_change_is_material(self):
        entry = fs.classify_kb_changes(
            _fit(),
            _uni(deadlines=[{'plan_type': 'ED', 'date': '2026-10-15'},
                            {'plan_type': 'RD', 'date': '2027-01-15'}]),
        )
        assert any(c['field'] == 'application_deadlines' and c['severity'] == 'material'
                   for c in entry['changes'])

    def test_test_policy_change_is_material(self):
        entry = fs.classify_kb_changes(_fit(policy='Test optional'),
                                       _uni(policy='Test required'))
        pc = next(c for c in entry['changes'] if c['field'] == 'test_policy')
        assert pc['severity'] == 'material'

    def test_coa_drift_under_10pct_is_minor_over_is_material(self):
        minor = fs.classify_kb_changes(_fit(coa=82000), _uni(coa=86000))
        assert next(c for c in minor['changes'] if c['field'] == 'total_coa')['severity'] == 'minor'
        material = fs.classify_kb_changes(_fit(coa=82000), _uni(coa=95000))
        assert next(c for c in material['changes'] if c['field'] == 'total_coa')['severity'] == 'material'

    def test_projected_shift_from_category_floor(self):
        # Student sees SAFETY; new rate 7% forces floor SUPER_REACH.
        entry = fs.classify_kb_changes(_fit(rate=44.0, category='SAFETY'),
                                       _uni(rate=7.0))
        assert entry['projected_category_shift'] == 'SAFETY → SUPER_REACH'

    def test_no_projected_shift_when_floor_not_stricter(self):
        entry = fs.classify_kb_changes(_fit(rate=44.0, category='SAFETY'),
                                       _uni(rate=35.2))  # no floor at 35%
        assert entry['projected_category_shift'] is None

    def test_legacy_fit_without_provenance_is_unknown(self):
        legacy = {'university_id': 'northeastern', 'fit_category': 'SAFETY'}
        entry = fs.classify_kb_changes(legacy, _uni(data_year=2026))
        assert entry['fit_kb_year'] is None
        assert entry['changes'][0]['severity'] == 'unknown'

    def test_legacy_fit_against_unversioned_kb_is_silent(self):
        legacy = {'university_id': 'northeastern'}
        assert fs.classify_kb_changes(legacy, {'university_id': 'northeastern',
                                               'profile': {}}) is None

    def test_stale_year_with_no_input_changes_reports_minor(self):
        fit = _fit(kb_year=2025, rate=35.2, coa=86000)  # same inputs as current
        entry = fs.classify_kb_changes(fit, _uni(data_year=2026, rate=35.2))
        assert len(entry['changes']) == 1
        assert entry['changes'][0]['field'] == 'kb_data_year'
        assert entry['changes'][0]['severity'] == 'minor'


class TestGetKbUpdates:
    def test_batches_and_classifies(self):
        fits = [_fit(rate=44.0), {'university_id': 'ghost_university'}]
        batch = {'northeastern': _uni(rate=35.2)}
        updates = fs.get_kb_updates(fits, fetch_batch=lambda ids: batch)
        assert len(updates) == 1  # ghost skipped (no current data)
        assert updates[0]['university_id'] == 'northeastern'

    def test_empty_fits_returns_empty(self):
        called = []
        updates = fs.get_kb_updates([], fetch_batch=lambda ids: called.append(ids) or {})
        assert updates == []
        assert called == [[]]  # fetcher sees an empty id list, returns nothing
