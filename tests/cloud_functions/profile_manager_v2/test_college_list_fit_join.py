"""get_college_list joins the student's PERSONALIZED fit_category (from
college_fits) onto each list item — distinct from the population-level
soft_fit_category — so the balance ring / agent see real reach-target-safety.
Read-only (cached fits; no recompute, no credits). KB enrichment is patched to
fail so the test exercises the join in isolation."""

from unittest.mock import patch

import college_list


class _FakeDB:
    def __init__(self, items, fits):
        self._items, self._fits = items, fits

    def get_college_list(self, uid):
        return self._items

    def get_all_fits(self, uid):
        return self._fits


def _run(items, fits):
    db = _FakeDB(items, fits)
    with patch.object(college_list, 'get_db', return_value=db), \
         patch.object(college_list.requests, 'post', side_effect=Exception('no KB in test')):
        return college_list.get_college_list('s@test.com')


def test_joins_personalized_fit_distinct_from_soft():
    out = _run(
        items=[
            {'university_id': 'umich', 'university_name': 'Michigan', 'soft_fit_category': 'REACH'},
            {'university_id': 'msu', 'university_name': 'Michigan State', 'soft_fit_category': 'SAFETY'},
        ],
        fits=[{'university_id': 'umich', 'fit_category': 'TARGET', 'match_percentage': 72}],
    )
    by_id = {c['university_id']: c for c in out}
    # Personalized fit wins as fit_category; the population soft band is preserved.
    assert by_id['umich']['fit_category'] == 'TARGET'
    assert by_id['umich']['match_percentage'] == 72
    assert by_id['umich']['soft_fit_category'] == 'REACH'
    # No personalized fit → fit_category None (caller treats as an estimate).
    assert by_id['msu']['fit_category'] is None
    assert by_id['msu']['soft_fit_category'] == 'SAFETY'


def test_no_fits_leaves_fit_category_none():
    out = _run(items=[{'university_id': 'x', 'university_name': 'X'}], fits=[])
    assert out[0]['fit_category'] is None and out[0]['match_percentage'] is None


def test_legacy_match_score_backfills_match_percentage():
    out = _run(items=[{'university_id': 'x', 'university_name': 'X'}],
               fits=[{'university_id': 'x', 'fit_category': 'SAFETY', 'match_score': 88}])
    assert out[0]['match_percentage'] == 88


def test_fit_load_failure_degrades_gracefully():
    # get_all_fits raising must not break the list (items still returned, no fit).
    class _BoomDB(_FakeDB):
        def get_all_fits(self, uid):
            raise RuntimeError('fits backend down')
    with patch.object(college_list, 'get_db', return_value=_BoomDB([{'university_id': 'x', 'university_name': 'X'}], [])), \
         patch.object(college_list.requests, 'post', side_effect=Exception('no KB')):
        out = college_list.get_college_list('s@test.com')
    assert out[0]['university_id'] == 'x' and out[0]['fit_category'] is None
