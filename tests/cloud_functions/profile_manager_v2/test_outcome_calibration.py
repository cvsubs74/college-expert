"""Decision Ledger join: get_outcome_calibration pairs each college's recorded
admission decision (college_list) with the fit category Stratia predicted
(college_fits). Pure join over two reader methods — stubbed here directly."""

from firestore_db import FirestoreDB


def _db(college_list, fits):
    db = FirestoreDB.__new__(FirestoreDB)
    db.get_college_list = lambda uid: college_list
    db.get_all_fits = lambda uid: fits
    return db


def test_joins_decision_with_predicted_fit_and_counts():
    db = _db(
        college_list=[
            {'university_id': 'umich', 'university_name': 'Michigan',
             'decision': 'accepted', 'status_updated_at': '2026-03-28'},
            {'university_id': 'cornell', 'university_name': 'Cornell',
             'decision': 'waitlisted', 'status_updated_at': '2026-03-30'},
            {'university_id': 'msu', 'university_name': 'Michigan State',
             'soft_fit_category': 'SAFETY'},  # no decision, no personalized fit
        ],
        fits=[
            {'university_id': 'umich', 'fit_category': 'TARGET', 'match_percentage': 72},
            {'university_id': 'cornell', 'fit_category': 'REACH', 'match_percentage': 41},
        ],
    )
    res = db.get_outcome_calibration('s@test.com')
    assert res['total'] == 3 and res['decided_count'] == 2
    by_id = {o['university_id']: o for o in res['outcomes']}
    assert by_id['umich']['predicted'] == 'TARGET' and by_id['umich']['decision'] == 'accepted'
    assert by_id['cornell']['predicted'] == 'REACH' and by_id['cornell']['decision'] == 'waitlisted'
    # No personalized fit → falls back to the population (soft) category, not blank.
    assert by_id['msu']['predicted'] == 'SAFETY' and by_id['msu']['decision'] is None


def test_orders_decided_newest_first_then_undecided_by_name():
    db = _db(
        college_list=[
            {'university_id': 'b', 'university_name': 'Bravo', 'decision': 'accepted', 'status_updated_at': '2026-03-01'},
            {'university_id': 'a', 'university_name': 'Alpha'},
            {'university_id': 'c', 'university_name': 'Charlie', 'decision': 'denied', 'status_updated_at': '2026-03-15'},
        ],
        fits=[],
    )
    order = [o['university_id'] for o in db.get_outcome_calibration('s@test.com')['outcomes']]
    assert order == ['c', 'b', 'a']  # decided newest-first, then undecided


def test_empty_decision_string_is_not_counted():
    db = _db(college_list=[{'university_id': 'x', 'university_name': 'X', 'decision': ''}], fits=[])
    res = db.get_outcome_calibration('s@test.com')
    assert res['decided_count'] == 0 and res['outcomes'][0]['decision'] is None
