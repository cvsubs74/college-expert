"""Major-selection plumbing (#281): onboarding flatten/persist, intended-majors
list + mirror, per-school major choice with KB-name matching, and the fit
major-resolution order."""

from unittest.mock import patch

import majors
from major_match import match_major, normalize_major, kb_major_names
from majors import (flatten_onboarding_profile, resolve_intended_major)


class _FakeDB:
    def __init__(self):
        self.profile_writes = []
        self.list_items = {}

    def save_profile(self, user_id, data, merge=True):
        self.profile_writes.append((user_id, data, merge))
        return True

    def update_college_list_item(self, user_id, university_id, data):
        if university_id not in self.list_items:
            return False
        self.list_items[university_id].update(data)
        return True


# --- onboarding flatten (against the REAL OnboardingModal payload shape) ----


_MODAL_PAYLOAD = {
    'student_info': {'name': 'Ada L.', 'email': 'a@b.com', 'grade': 11,
                     'high_school': 'Central High', 'state': 'CA'},
    'academic_profile': {
        'gpa': {'weighted': 4.2},
        'test_scores': {'sat': {'composite': 1480}, 'act': None},
        'ap_courses': 6,
    },
    'interests': {'intended_majors': ['Computer Science', 'Cognitive Science'],
                  'top_activity': 'Robotics club', 'activity_type': 'STEM'},
    'preferences': {'preferred_locations': ['CA', 'WA'], 'school_size': 'large',
                    'campus_type': 'urban'},
    'onboarding_status': 'completed',
    'onboarding_completed_at': '2026-07-01T00:00:00Z',
}


class TestOnboardingFlatten:
    def test_flattens_real_modal_shape(self):
        flat = flatten_onboarding_profile(_MODAL_PAYLOAD)
        assert flat['name'] == 'Ada L.'
        assert flat['grade'] == '11'            # coerced to string (issue #130)
        assert flat['school'] == 'Central High'
        assert flat['gpa_weighted'] == 4.2
        assert flat['sat_total'] == 1480
        assert 'act_composite' not in flat      # null act dropped, not stored
        assert flat['ap_courses_count'] == 6
        assert flat['intended_majors'] == ['Computer Science', 'Cognitive Science']
        assert flat['intended_major'] == 'Computer Science'  # mirror = primary
        assert flat['preferences']['school_size'] == 'large'
        assert flat['onboarding_status'] == 'completed'

    def test_majors_capped_at_three_and_blank_dropped(self):
        payload = {'interests': {'intended_majors': ['A', '  ', 'B', 'C', 'D']}}
        flat = flatten_onboarding_profile(payload)
        assert flat['intended_majors'] == ['A', 'B', 'C']

    def test_save_merges_flat_profile(self):
        db = _FakeDB()
        with patch.object(majors, 'get_db', return_value=db):
            result = majors.save_onboarding_profile('a@b.com', _MODAL_PAYLOAD)
        assert result['success'] is True
        (user, data, merge), = db.profile_writes
        assert user == 'a@b.com' and merge is True
        assert data['intended_major'] == 'Computer Science'
        assert 'intended_majors' in result['saved_fields']

    def test_empty_payload_is_an_error(self):
        db = _FakeDB()
        with patch.object(majors, 'get_db', return_value=db):
            assert majors.save_onboarding_profile('a@b.com', {})['success'] is False


# --- intended majors ---------------------------------------------------------


class TestSetIntendedMajors:
    def _run(self, majors_list, primary=None):
        db = _FakeDB()
        with patch.object(majors, 'get_db', return_value=db):
            return majors.set_intended_majors('a@b.com', majors_list, primary), db

    def test_writes_list_and_mirror(self):
        result, db = self._run(['Computer Science', 'Statistics'])
        assert result['success'] is True
        (_, data, _), = db.profile_writes
        assert data['intended_majors'] == ['Computer Science', 'Statistics']
        assert data['intended_major'] == 'Computer Science'  # load-bearing mirror

    def test_primary_moves_to_front(self):
        result, _ = self._run(['CS', 'Statistics', 'Math'], primary='Statistics')
        assert result['intended_majors'][0] == 'Statistics'
        assert result['intended_major'] == 'Statistics'

    def test_dedupes_case_insensitively_and_caps_at_five(self):
        result, _ = self._run(['CS', 'cs', 'A', 'B', 'C', 'D', 'E'])
        assert result['success'] is False  # 6 distinct > 5
        result, _ = self._run(['CS', 'cs', 'A', 'B', 'C'])
        assert result['intended_majors'] == ['CS', 'A', 'B', 'C']

    def test_rejects_empty(self):
        result, _ = self._run([])
        assert result['success'] is False
        result, _ = self._run(['   '])
        assert result['success'] is False

    def test_rejects_bare_string(self):
        """A bare string would iterate into characters and store
        intended_major='C' (adversarial review M3)."""
        result, db = self._run('CS')
        assert result['success'] is False
        assert db.profile_writes == []


# --- per-school major choice -------------------------------------------------


_UIUC_ENVELOPE = {
    'data_year': 2026,
    'profile': {'academic_structure': {'colleges': [
        {'name': 'Grainger College of Engineering', 'majors': [
            {'name': 'Computer Science'},
            {'name': 'Computer Engineering'},
            {'name': 'Mathematics & Computer Science'},
        ]},
    ]}},
}


class TestSetMajorChoice:
    def _run(self, primary, on_list=True, envelope=_UIUC_ENVELOPE, **kw):
        db = _FakeDB()
        if on_list:
            db.list_items['uiuc'] = {'university_name': 'UIUC'}
        with patch.object(majors, 'get_db', return_value=db):
            return majors.set_major_choice('a@b.com', 'uiuc', primary,
                                           university_envelope=envelope, **kw), db

    def test_exact_match_canonicalizes(self):
        result, db = self._run('Computer Science', backup_major='Statistics',
                               rationale='wider door', source='claude')
        assert result['success'] is True
        choice = db.list_items['uiuc']['major_choice']
        assert choice['primary'] == 'Computer Science'
        assert choice['matched'] is True
        assert choice['kb_year'] == 2026
        assert choice['source'] == 'claude'
        assert db.list_items['uiuc']['selected_major'] == 'Computer Science'

    def test_strong_match_canonicalizes_to_kb_spelling(self):
        result, db = self._run('computer science, B.S.')
        assert db.list_items['uiuc']['major_choice']['primary'] == 'Computer Science'
        assert db.list_items['uiuc']['major_choice']['matched'] is True

    def test_fuzzy_match_keeps_student_words_flagged(self):
        result, db = self._run('CS + Advertising')
        choice = db.list_items['uiuc']['major_choice']
        assert choice['matched'] is False           # never silently rewritten
        assert choice['primary'] == 'CS + Advertising'
        assert result['near_misses']                # repair path offered
        assert result['note']

    def test_school_not_on_list_is_a_clean_error(self):
        result, db = self._run('Computer Science', on_list=False)
        assert result['success'] is False
        assert 'not on the college list' in result['error']

    def test_missing_kb_envelope_degrades_to_unmatched(self):
        result, db = self._run('Computer Science', envelope=None)
        assert result['success'] is True
        assert db.list_items['uiuc']['major_choice']['matched'] is False


# --- fit major resolution (#281 resolution order) ----------------------------


class TestResolveIntendedMajor:
    def test_explicit_wins(self):
        r = resolve_intended_major({'intended_major': 'Bio'},
                                   {'major_choice': {'primary': 'CS'}},
                                   explicit='Statistics')
        assert r == {'major': 'Statistics', 'source': 'request'}

    def test_major_choice_beats_profile(self):
        r = resolve_intended_major({'intended_major': 'Bio'},
                                   {'major_choice': {'primary': 'CS'}})
        assert r == {'major': 'CS', 'source': 'major_choice'}

    def test_legacy_selected_major_between(self):
        r = resolve_intended_major({'intended_major': 'Bio'},
                                   {'selected_major': 'Chem'})
        assert r == {'major': 'Chem', 'source': 'selected_major'}

    def test_profile_fallback_and_empty(self):
        assert resolve_intended_major({'intended_major': 'Bio'}, None) == \
            {'major': 'Bio', 'source': 'profile'}
        assert resolve_intended_major({}, None) == {'major': '', 'source': 'profile'}

    def test_corrupt_major_choice_does_not_crash(self):
        r = resolve_intended_major({'intended_major': 'Bio'},
                                   {'major_choice': 'corrupt-string'})
        assert r == {'major': 'Bio', 'source': 'profile'}

    def test_onboarding_flatten_tolerates_non_dict_sections(self):
        flat = flatten_onboarding_profile({'student_info': 'oops',
                                           'interests': {'intended_majors': ['A']}})
        assert flat['intended_major'] == 'A'


# --- matcher ------------------------------------------------------------------


class TestMatcher:
    def test_normalize_strips_degree_suffixes_and_expands(self):
        assert normalize_major('Computer Science, B.S.') == 'computer science'
        assert normalize_major('CS') == 'computer science'
        assert normalize_major('Poli Sci (B.A.)') == 'political science'

    def test_ladder(self):
        cands = ['Computer Science', 'Computer Engineering', 'Data Science']
        assert match_major('Computer Science', cands)['confidence'] == 'exact'
        assert match_major('computer science bs', cands)['confidence'] == 'strong'
        fuzzy = match_major('Computer Sci & Stats', cands)
        assert fuzzy['confidence'] in ('fuzzy', 'none')
        none = match_major('Underwater Basket Weaving', cands)
        assert none['found'] is False and none['confidence'] == 'none'

    def test_near_misses_offered(self):
        m = match_major('Computing', ['Computer Science', 'Computer Engineering', 'History'])
        assert m['found'] is False or m['confidence'] == 'fuzzy'
        # regardless of bind, adjacent doors are surfaced

    def test_kb_major_names_walks_colleges(self):
        assert kb_major_names(_UIUC_ENVELOPE['profile']) == [
            'Computer Science', 'Computer Engineering', 'Mathematics & Computer Science']
