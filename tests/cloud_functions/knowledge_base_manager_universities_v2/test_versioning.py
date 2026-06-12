"""
Cycle-year derivation + ingest-boundary validation (versioning.py).
Pure functions — no Firestore involved.
"""

from datetime import datetime, timezone

import pytest

import kbv2_versioning as v  # registered in sys.modules by conftest.py


class TestCurrentCycleYear:
    @pytest.mark.parametrize('today,expected', [
        (datetime(2026, 6, 12, tzinfo=timezone.utc), 2026),   # collection season
        (datetime(2026, 4, 1, tzinfo=timezone.utc), 2026),    # rollover boundary
        (datetime(2026, 3, 31, tzinfo=timezone.utc), 2025),   # RD season tail
        (datetime(2027, 1, 5, tzinfo=timezone.utc), 2026),    # RD deadlines = prior cycle
        (datetime(2026, 11, 1, tzinfo=timezone.utc), 2026),   # ED season
    ])
    def test_cycle_year_boundaries(self, today, expected):
        assert v.current_cycle_year(today) == expected

    def test_defaults_to_now(self):
        assert v.current_cycle_year() in (datetime.now(timezone.utc).year,
                                          datetime.now(timezone.utc).year - 1)


class TestCoerceYear:
    def test_explicit_int_passes_through(self):
        assert v.coerce_year(2025) == 2025

    def test_numeric_string_is_parsed(self):
        assert v.coerce_year('2026') == 2026

    def test_none_falls_back_to_default(self):
        assert v.coerce_year(None, default=2024) == 2024

    def test_none_without_default_uses_current_cycle(self):
        assert v.coerce_year(None) == v.current_cycle_year()

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            v.coerce_year('next-year')

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            v.coerce_year(1999)
        with pytest.raises(ValueError):
            v.coerce_year(3000)


class TestValidateProfile:
    def test_valid_profile_no_errors(self, make_profile):
        errors, warnings = v.validate_profile(make_profile(), 2026)
        assert errors == []
        assert warnings == []

    def test_missing_id_is_error(self, make_profile):
        p = make_profile()
        del p['_id']
        errors, _ = v.validate_profile(p, 2026)
        assert any('_id' in e for e in errors)

    def test_missing_official_name_is_error(self, make_profile):
        p = make_profile()
        p['metadata'] = {}
        errors, _ = v.validate_profile(p, 2026)
        assert any('official_name' in e for e in errors)

    def test_non_dict_profile_is_error(self):
        errors, _ = v.validate_profile('not a dict', 2026)
        assert errors

    @pytest.mark.parametrize('rate', [0, -5, 150, 'high'])
    def test_bad_acceptance_rate_is_error(self, make_profile, rate):
        errors, _ = v.validate_profile(make_profile(acceptance_rate=rate), 2026)
        assert any('overall_acceptance_rate' in e for e in errors)

    def test_missing_acceptance_rate_is_warning_not_error(self, make_profile):
        p = make_profile()
        p['admissions_data']['current_status']['overall_acceptance_rate'] = None
        errors, warnings = v.validate_profile(p, 2026)
        assert errors == []
        assert any('acceptance_rate' in w for w in warnings)

    def test_no_deadlines_is_warning(self, make_profile):
        errors, warnings = v.validate_profile(make_profile(deadlines=[]), 2026)
        assert errors == []
        assert any('application_deadlines' in w for w in warnings)

    def test_unparseable_deadline_is_warning(self, make_profile):
        p = make_profile(deadlines=[{'plan_type': 'RD', 'date': 'Rolling'}])
        errors, warnings = v.validate_profile(p, 2026)
        assert errors == []
        assert any('Rolling' in w for w in warnings)

    def test_deadline_outside_cycle_window_is_warning(self, make_profile):
        # 2021 deadline filed as cycle-2026 data → stale data warning
        p = make_profile(deadlines=[{'plan_type': 'RD', 'date': '2021-01-05'}])
        errors, warnings = v.validate_profile(p, 2026)
        assert errors == []
        assert any('outside the cycle-2026 window' in w for w in warnings)

    def test_deadline_within_cycle_window_is_clean(self, make_profile):
        # RD in Jan of year+1 is normal for a fall cycle
        p = make_profile(deadlines=[{'plan_type': 'RD', 'date': '2027-01-05'}])
        errors, warnings = v.validate_profile(p, 2026)
        assert errors == []
        assert warnings == []
