"""Shared analysis schema (#310): the SINGLE source for the agent-facing
describe surface and agent-write validation. Pins the describe shape (fields,
enums, trust_rules) and validate_against's shape/type/enum/required checks."""

from analysis_schema import (
    CHANCES_TIERS,
    FIT_CATEGORIES,
    get_schema,
    validate_against,
)


class TestDescribeShape:
    def test_fit_schema_shape(self):
        s = get_schema('fit')
        assert s['kind'] == 'fit'
        assert set(s['fields']['fit_category']['enum']) == set(FIT_CATEGORIES)
        assert s['fields']['fit_category']['required'] is True
        assert s['fields']['match_percentage']['required'] is True
        assert s['fields']['explanation']['required'] is True
        # trust_rules must state the KB re-derivation contract.
        tr = s['trust_rules'].lower()
        assert 'floor' in tr and 'acceptance' in tr

    def test_major_chances_schema_shape(self):
        s = get_schema('major_chances')
        assert s['kind'] == 'major_chances'
        item = s['fields']['majors']['item_fields']
        assert item['name']['required'] is True
        assert set(item['tier']['enum']) == set(CHANCES_TIERS)
        tr = s['trust_rules'].lower()
        assert 'entry_path' in tr and 'dropped' in tr

    def test_unknown_kind_returns_none(self):
        assert get_schema('nope') is None


class TestValidateFit:
    def test_valid_fit_passes(self):
        ok, errors = validate_against('fit', {
            'fit_category': 'REACH', 'match_percentage': 45, 'explanation': 'x'})
        assert ok is True and errors == []

    def test_missing_required_fields_fail(self):
        ok, errors = validate_against('fit', {'match_percentage': 50})
        assert ok is False
        assert any('fit_category' in e for e in errors)
        assert any('explanation' in e for e in errors)

    def test_bad_category_enum_fails(self):
        ok, errors = validate_against('fit', {
            'fit_category': 'AMAZING', 'match_percentage': 50, 'explanation': 'x'})
        assert ok is False and any('fit_category' in e for e in errors)

    def test_out_of_range_percentage_fails(self):
        ok, errors = validate_against('fit', {
            'fit_category': 'TARGET', 'match_percentage': 200, 'explanation': 'x'})
        assert ok is False and any('match_percentage' in e for e in errors)

    def test_boolean_percentage_is_not_a_number(self):
        ok, errors = validate_against('fit', {
            'fit_category': 'TARGET', 'match_percentage': True, 'explanation': 'x'})
        assert ok is False


class TestValidateMajorChances:
    def test_valid_ranking_passes(self):
        ok, errors = validate_against('major_chances', {'majors': [
            {'name': 'Computer Science', 'tier': 'reach', 'rationale': 'x'}]})
        assert ok is True and errors == []

    def test_tier_is_case_insensitive(self):
        ok, _ = validate_against('major_chances', {'majors': [
            {'name': 'CS', 'tier': 'Strong'}]})
        assert ok is True

    def test_empty_majors_list_fails(self):
        ok, errors = validate_against('major_chances', {'majors': []})
        assert ok is False and any('majors' in e for e in errors)

    def test_bad_tier_fails(self):
        ok, errors = validate_against('major_chances', {'majors': [
            {'name': 'CS', 'tier': 'safety'}]})
        assert ok is False and any('tier' in e for e in errors)

    def test_missing_name_fails(self):
        ok, errors = validate_against('major_chances', {'majors': [
            {'tier': 'reach'}]})
        assert ok is False and any('name' in e for e in errors)

    def test_oversized_majors_list_is_rejected(self):
        # No school offers 300 majors — reject at the shape gate before doing the
        # per-major KB normalize + catalog match (#314 review: cap size).
        big = [{'name': f'Major {i}', 'tier': 'reach'} for i in range(300)]
        ok, errors = validate_against('major_chances', {'majors': big})
        assert ok is False and any('max' in e for e in errors)


def test_unknown_kind_is_invalid():
    ok, errors = validate_against('bogus', {})
    assert ok is False and errors


def test_non_object_payload_is_invalid():
    ok, errors = validate_against('fit', ['not', 'a', 'dict'])
    assert ok is False
