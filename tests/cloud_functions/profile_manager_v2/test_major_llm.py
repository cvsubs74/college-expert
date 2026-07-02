"""Major Strategy phase 2 (#284): major_llm's contracts.

Everything the issue's acceptance criteria hinge on is pinned here:
- readiness 422 (unbilled) for generate-major-map
- cache-unless-force / archive-on-regenerate / fingerprint staleness (map)
- never-charge-on-miss + kb_gaps increment (strategy)
- the deterministic numeric-claim validator (no unextracted %/GPA survives)
- the deterministic capped_door door-lock warning append
- 402/deduct-once/never-on-failure for BOTH endpoints
- door_flags derivation for the Launchpad callout

The LLM is monkeypatched at the _llm_json seam — no live calls."""

import logging
from unittest.mock import patch

import generation_billing
import major_llm
from major_llm import (
    build_full_catalog_rows,
    build_labeled_extract,
    check_map_readiness,
    derive_door_flags,
    ensure_door_lock_warning,
    ensure_major_door_lock_rationale,
    filter_facts_to_majors,
    get_college_major_chances_payload,
    get_major_map_payload,
    get_major_strategy_payload,
    normalize_college_major_ranking,
    profile_fingerprint,
    resolve_strategy_majors,
    run_generate_major_map,
    run_generate_major_strategy,
    run_rank_college_majors,
    validate_numeric_claims,
)


# ---------------------------------------------------------------------------
# Fixtures & fakes
# ---------------------------------------------------------------------------

READY_PROFILE = {
    'grade': '11',
    'gpa_weighted': 4.2,
    'courses': [{'name': 'AP Computer Science A'}, {'name': 'AP Calculus BC'}],
    'extracurriculars': [{'name': 'Robotics Club', 'role': 'Captain'}],
    'intended_majors': ['Computer Science', 'Statistics'],
    'intended_major': 'Computer Science',
}

MAP_LLM_RESPONSE = {
    'clusters': [
        {'theme': 'Building intelligent systems',
         'why_you': 'AP Computer Science A and Robotics Club captaincy show sustained making.',
         'evidence': ['AP Computer Science A', 'Robotics Club'],
         'majors': [
             {'name': 'Computer Science', 'relation': 'core',
              'why': 'the direct door', 'watch_out': 'capped at many public flagships'},
             {'name': 'Computer Engineering', 'relation': 'adjacent',
              'why': 'hardware + software', 'watch_out': 'heavier physics load'},
             {'name': 'Data Science', 'relation': 'strategic_alternative',
              'why': 'same outcomes, different door', 'watch_out': 'newer programs vary'},
         ]},
        {'theme': 'Quantitative reasoning',
         'why_you': 'AP Calculus BC.',
         'evidence': ['AP Calculus BC'],
         'majors': [{'name': 'Statistics', 'relation': 'core', 'why': 'x', 'watch_out': 'y'}]},
        {'theme': 'Leading technical teams',
         'why_you': 'Robotics captain.',
         'evidence': ['Robotics Club'],
         'majors': [{'name': 'Industrial Engineering', 'relation': 'adjacent',
                     'why': 'x', 'watch_out': 'y'}]},
    ],
    'questions_to_explore': ['Do you prefer building or analyzing?'],
}

# KB action=majors payload (matches major_facts.py's output shape).
KB_FACTS = {
    'success': True,
    'university_id': 'uw',
    'official_name': 'University of Washington',
    'data_year': 2026,
    'verification_status': 'legacy',
    'richness_tier': 2,
    'structure_type': 'colleges',
    'colleges': [
        {
            'name': 'College of Engineering',
            'admissions_model': 'Direct to College',
            'is_restricted_or_capped': True,
            'acceptance_rate_estimate': {'value': '25%', 'basis': 'kb_reported'},
            'strategic_fit_advice': {'text': 'Apply direct if engineering is the goal.',
                                     'basis': 'opinion'},
            'majors': [
                {'name': 'Computer Science', 'degree_type': 'BS',
                 'entry_path': {'value': 'direct_admit',
                                'raw': 'Direct admission only.', 'basis': 'kb_reported'},
                 'entry_risk': 'capped_door',
                 'is_impacted': {'value': False, 'basis': 'kb_reported', 'note': None},
                 'door_policy': {'direct_admit_only': True,
                                 'internal_transfer_allowed': False,
                                 'internal_transfer_gpa': None, 'basis': 'kb_reported'},
                 'prerequisite_courses': [],
                 'reported_stats': {'acceptance_rate': 7, 'basis': 'kb_reported'}},
                {'name': 'Computer Engineering', 'degree_type': 'BS',
                 'entry_path': {'value': 'direct_admit', 'raw': None, 'basis': None},
                 'entry_risk': 'standard',
                 'is_impacted': {'value': None, 'basis': None, 'note': None},
                 'door_policy': {'direct_admit_only': None,
                                 'internal_transfer_allowed': True,
                                 'internal_transfer_gpa': 3.5, 'basis': 'kb_reported'},
                 'prerequisite_courses': [],
                 'reported_stats': None},
            ],
        },
    ],
    'strategy_notes': {
        'major_selection_tactics': {'items': ['List the genuine first choice.'],
                                    'basis': 'opinion'},
        'alternate_major_strategy': {'text': None, 'basis': 'opinion'},
    },
    'data_notes': ['Major-level facts for this school are reported but not yet re-verified.'],
}

STRATEGY_LLM_RESPONSE = {
    'primary_call': 'My read: list Computer Science and mean it.',
    'second_choice_play': 'A second choice inside engineering keeps the file coherent.',
    'backup_rationale': 'Computer Engineering is the on-campus backup worth naming.',
    'undeclared_tactic': 'Undeclared is not a real path into this college.',
    'essay_implication': 'Your essays must argue the CS story specifically.',
    'what_to_verify_yourself': ['Confirm the direct-admit policy on the official CS admissions page.'],
}


class FakeDB:
    def __init__(self, profile=None, list_items=None, major_map=None,
                 strategies=None, rankings=None):
        self.profile = profile
        self.list_items = list_items or {}
        self.major_map = major_map
        self.strategies = strategies or {}
        self.rankings = rankings or {}
        self.map_archives = []
        self.strategy_archives = []
        self.ranking_archives = []
        self.kb_gap_calls = []
        self.save_map_ok = True
        self.save_strategy_ok = True
        self.save_ranking_ok = True

    def get_profile(self, user_id):
        return self.profile

    def get_college_list_item(self, user_id, university_id):
        return self.list_items.get(university_id)

    def update_college_list_item(self, user_id, university_id, data):
        if university_id not in self.list_items:
            return False
        self.list_items[university_id].update(data)
        return True

    def get_major_map(self, user_id):
        return self.major_map

    def save_major_map(self, user_id, map_data):
        if not self.save_map_ok:
            return False
        self.major_map = map_data
        return True

    def archive_major_map(self, user_id, map_data):
        self.map_archives.append(map_data)
        return True

    def get_major_strategy(self, user_id, university_id):
        return self.strategies.get(university_id)

    def save_major_strategy(self, user_id, university_id, strategy):
        if not self.save_strategy_ok:
            return False
        self.strategies[university_id] = strategy
        return True

    def archive_major_strategy(self, user_id, university_id, strategy, history_key):
        self.strategy_archives.append((university_id, history_key, strategy))
        return True

    def increment_kb_gap(self, university_id, major_names):
        self.kb_gap_calls.append((university_id, list(major_names)))
        return True

    def get_college_major_chances(self, user_id, university_id):
        return self.rankings.get(university_id)

    def save_college_major_chances(self, user_id, university_id, ranking):
        if not self.save_ranking_ok:
            return False
        self.rankings[university_id] = ranking
        return True

    def archive_college_major_chances(self, user_id, university_id, ranking, history_key):
        self.ranking_archives.append((university_id, history_key, ranking))
        return True


MAP_CATALOG = [
    {'name': 'Computer Science', 'normalized': 'computer science', 'offered_count': 133},
    {'name': 'Computer Engineering', 'normalized': 'computer engineering', 'offered_count': 40},
    {'name': 'Data Science', 'normalized': 'data science', 'offered_count': 30},
    {'name': 'Statistics', 'normalized': 'statistics', 'offered_count': 25},
    # Industrial Engineering deliberately absent → exercises in_catalog:false.
]


def _billing_seams(has_credits=True, remaining=5):
    """Patch generation_billing's credit seams; returns the calls recorder."""
    calls = {'check': 0, 'deduct': 0}

    def fake_check(user_email, needed):
        calls['check'] += 1
        return {'has_credits': has_credits, 'credits_remaining': remaining}

    def fake_deduct(user_email, count, reason):
        calls['deduct'] += 1
        calls['deduct_args'] = (user_email, count, reason)
        return {'success': True, 'credits_remaining': remaining - count}

    return calls, patch.object(generation_billing, 'check_credits_available',
                               side_effect=fake_check), \
        patch.object(generation_billing, 'deduct_credit', side_effect=fake_deduct)


def _run_map(db, body=None, llm=MAP_LLM_RESPONSE, has_credits=True, catalog=MAP_CATALOG):
    body = body or {'user_email': 's@x.com'}
    calls, p_check, p_deduct = _billing_seams(has_credits=has_credits)
    with patch.object(major_llm, 'get_db', return_value=db), \
         patch.object(major_llm, '_llm_json', return_value=llm) as p_llm, \
         patch.object(major_llm, 'fetch_major_catalog', return_value=catalog), \
         p_check, p_deduct:
        payload, status = run_generate_major_map(body)
    calls['llm'] = p_llm.call_count
    return payload, status, calls


def _run_strategy(db, body=None, llm=STRATEGY_LLM_RESPONSE, facts=KB_FACTS,
                  has_credits=True):
    body = body or {'user_email': 's@x.com', 'university_id': 'uw'}
    calls, p_check, p_deduct = _billing_seams(has_credits=has_credits)
    with patch.object(major_llm, 'get_db', return_value=db), \
         patch.object(major_llm, '_llm_json', return_value=llm) as p_llm, \
         patch.object(major_llm, 'fetch_university_majors', return_value=facts), \
         p_check, p_deduct:
        payload, status = run_generate_major_strategy(body)
    calls['llm'] = p_llm.call_count
    return payload, status, calls


# ---------------------------------------------------------------------------
# Readiness guard (422, unbilled)
# ---------------------------------------------------------------------------

class TestMapReadiness:
    def test_ready_profile_has_no_missing(self):
        assert check_map_readiness(READY_PROFILE) == []

    def test_missing_grade(self):
        p = {k: v for k, v in READY_PROFILE.items() if k != 'grade'}
        assert 'grade' in check_map_readiness(p)

    def test_needs_two_of_three_signals(self):
        p = {'grade': '11', 'courses': [{'name': 'AP Bio'}]}
        missing = check_map_readiness(p)
        assert 'grade' not in missing
        assert set(missing) == {'extracurriculars', 'gpa'}

    def test_gpa_counts_any_gpa_star_field(self):
        p = {'grade': '10', 'gpa_uc': 3.9, 'extracurriculars': [{'name': 'Debate'}]}
        assert check_map_readiness(p) == []

    def test_incomplete_profile_is_422_and_never_touches_credits(self):
        db = FakeDB(profile={'grade': '11'})
        payload, status, calls = _run_map(db)
        assert status == 422
        assert payload['success'] is False
        assert payload['error'] == 'profile_incomplete'
        assert set(payload['missing']) == {'courses', 'extracurriculars', 'gpa'}
        assert calls['check'] == 0 and calls['deduct'] == 0 and calls['llm'] == 0

    def test_no_profile_at_all_is_422(self):
        db = FakeDB(profile=None)
        payload, status, calls = _run_map(db)
        assert status == 422 and payload['error'] == 'profile_incomplete'
        assert calls['deduct'] == 0


# ---------------------------------------------------------------------------
# Major Map: billing + cache + archive
# ---------------------------------------------------------------------------

class TestGenerateMajorMap:
    def test_insufficient_credits_402_never_generates(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_map(db, has_credits=False)
        assert status == 402
        assert payload['error'] == 'insufficient_credits'
        assert calls['llm'] == 0 and calls['deduct'] == 0

    def test_success_deducts_once_and_persists(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_map(db)
        assert status == 200 and payload['success'] is True
        assert calls['deduct'] == 1
        assert calls['deduct_args'] == ('s@x.com', 1, 'major_map')
        assert payload['credits_remaining'] == 4
        saved = db.major_map
        assert saved is not None
        assert saved['basis'] == 'inference'
        assert saved['intended_majors_at_generation'] == ['Computer Science', 'Statistics']
        assert saved['profile_fingerprint']['sha1']
        assert len(saved['clusters']) == 3
        assert saved['clusters'][0]['majors'][0]['relation'] == 'core'

    def test_llm_failure_is_500_and_never_deducts(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_map(db, llm=None)
        assert status == 500 and payload['success'] is False
        assert calls['deduct'] == 0
        assert db.major_map is None

    def test_save_failure_is_500_and_never_deducts(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        db.save_map_ok = False
        payload, status, calls = _run_map(db)
        assert status == 500 and calls['deduct'] == 0

    def test_unforced_regenerate_with_unchanged_profile_returns_cache_free(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)  # first (charged) generation
        payload, status, calls = _run_map(db)  # same profile, no force
        assert status == 200 and payload['from_cache'] is True
        assert calls['check'] == 0 and calls['deduct'] == 0 and calls['llm'] == 0

    def test_force_regenerates_and_archives_the_prior_map(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)
        first = db.major_map
        payload, status, calls = _run_map(db, body={'user_email': 's@x.com', 'force': True})
        assert status == 200 and payload['from_cache'] is False
        assert calls['deduct'] == 1
        # Archive-on-regenerate: the prior artifact survives, never destroyed.
        assert db.map_archives == [first]

    def test_profile_change_bypasses_cache(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)
        db.profile = {**READY_PROFILE,
                      'courses': READY_PROFILE['courses'] + [{'name': 'AP Physics C'}]}
        payload, status, calls = _run_map(db)
        assert payload['from_cache'] is False and calls['deduct'] == 1


class TestGetMajorMap:
    def _get(self, db):
        with patch.object(major_llm, 'get_db', return_value=db):
            return get_major_map_payload('s@x.com')

    def test_no_map_yet(self):
        payload, status = self._get(FakeDB(profile=dict(READY_PROFILE)))
        assert status == 200
        assert payload == {'success': True, 'map': None, 'stale': False,
                           'stale_reasons': []}

    def test_fresh_map_is_not_stale(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)
        payload, _ = self._get(db)
        assert payload['stale'] is False and payload['stale_reasons'] == []

    def test_fingerprint_mismatch_is_stale_with_named_reasons(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)
        db.profile = {**READY_PROFILE, 'grade': '12',
                      'extracurriculars': [{'name': 'Debate Team'}]}
        payload, _ = self._get(db)
        assert payload['stale'] is True
        joined = ' '.join(payload['stale_reasons'])
        assert 'grade' in joined and 'extracurriculars' in joined
        assert not any('courses' in r for r in payload['stale_reasons'])


class TestProfileFingerprint:
    def test_stable_across_ordering(self):
        a = profile_fingerprint({'intended_majors': ['CS', 'Math'],
                                 'courses': [{'name': 'A'}, {'name': 'B'}], 'grade': '11'})
        b = profile_fingerprint({'intended_majors': ['Math', 'CS'],
                                 'courses': [{'name': 'B'}, {'name': 'A'}], 'grade': '11'})
        assert a['sha1'] == b['sha1']

    def test_changes_when_a_relevant_field_changes(self):
        base = profile_fingerprint(READY_PROFILE)
        changed = profile_fingerprint({**READY_PROFILE, 'grade': '12'})
        assert base['sha1'] != changed['sha1']
        assert base['parts']['courses'] == changed['parts']['courses']
        assert base['parts']['grade'] != changed['parts']['grade']

    def test_ignores_irrelevant_fields(self):
        base = profile_fingerprint(READY_PROFILE)
        noisy = profile_fingerprint({**READY_PROFILE, 'sat_total': 1550})
        assert base['sha1'] == noisy['sha1']


# ---------------------------------------------------------------------------
# Strategy: major resolution + fact filtering
# ---------------------------------------------------------------------------

class TestResolveStrategyMajors:
    def test_request_majors_win_and_dedupe(self):
        majors, err = resolve_strategy_majors(
            {'majors': ['CS', 'cs ', 'Statistics']}, READY_PROFILE, None)
        assert err is None and majors == ['CS', 'Statistics']

    def test_more_than_four_requested_is_an_error(self):
        majors, err = resolve_strategy_majors(
            {'majors': ['A', 'B', 'C', 'D', 'E']}, READY_PROFILE, None)
        assert majors == [] and 'at most 4' in err

    def test_default_is_choice_primary_union_intended_capped_at_four(self):
        item = {'major_choice': {'primary': 'Computer Engineering'}}
        profile = {'intended_majors': ['Computer Science', 'Statistics',
                                       'Mathematics', 'Physics']}
        majors, err = resolve_strategy_majors({}, profile, item)
        assert err is None
        assert majors == ['Computer Engineering', 'Computer Science',
                          'Statistics', 'Mathematics']

    def test_choice_primary_dedupes_against_intended(self):
        item = {'major_choice': {'primary': 'Computer Science'}}
        majors, _ = resolve_strategy_majors({}, READY_PROFILE, item)
        assert majors == ['Computer Science', 'Statistics']


class TestFilterFacts:
    def test_exact_and_strong_bind_fuzzy_becomes_gap(self):
        matched, related, gaps = filter_facts_to_majors(
            KB_FACTS, ['Computer Science', 'Underwater Basket Weaving'])
        assert [m['name'] for m in matched] == ['Computer Science']
        assert matched[0]['college'] == 'College of Engineering'
        assert gaps == ['Underwater Basket Weaving']

    def test_near_misses_surface_as_related_backups_from_same_college(self):
        matched, related, gaps = filter_facts_to_majors(KB_FACTS, ['Computer Science'])
        assert any(r['name'] == 'Computer Engineering' for r in related)
        assert all(r.get('related') for r in related)


# ---------------------------------------------------------------------------
# Never-charge-on-miss + kb_gaps (hard AC)
# ---------------------------------------------------------------------------

class TestNeverChargeOnMiss:
    def test_zero_matched_majors_is_200_null_strategy_unbilled(self):
        db = FakeDB(profile={'intended_majors': ['Underwater Basket Weaving']})
        payload, status, calls = _run_strategy(
            db, body={'user_email': 's@x.com', 'university_id': 'uw'})
        assert status == 200
        assert payload['success'] is True and payload['strategy'] is None
        assert payload['gaps'] == ['Underwater Basket Weaving']
        # NO billing surface is touched at all — not even the credit check.
        assert calls['check'] == 0 and calls['deduct'] == 0 and calls['llm'] == 0

    def test_miss_increments_kb_gaps_demand_signal(self):
        db = FakeDB(profile={'intended_majors': ['Underwater Basket Weaving']})
        _run_strategy(db, body={'user_email': 's@x.com', 'university_id': 'uw'})
        assert db.kb_gap_calls == [('uw', ['Underwater Basket Weaving'])]

    def test_miss_works_even_with_zero_credits(self):
        # A student with an empty balance still gets the honest "we don't
        # know" for free — never a 402 for nothing.
        db = FakeDB(profile={'intended_majors': ['Underwater Basket Weaving']})
        payload, status, calls = _run_strategy(
            db, body={'user_email': 's@x.com', 'university_id': 'uw'},
            has_credits=False)
        assert status == 200 and payload['strategy'] is None

    def test_successful_generation_never_touches_kb_gaps(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_strategy(db)
        assert db.kb_gap_calls == []


# ---------------------------------------------------------------------------
# Strategy generation: billing + persistence + archive
# ---------------------------------------------------------------------------

class TestGenerateMajorStrategy:
    def test_insufficient_credits_402_never_generates(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_strategy(db, has_credits=False)
        assert status == 402 and payload['error'] == 'insufficient_credits'
        assert calls['llm'] == 0 and calls['deduct'] == 0

    def test_success_deducts_once_and_persists_the_doc(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_strategy(db)
        assert status == 200 and payload['success'] is True
        assert calls['deduct'] == 1
        assert calls['deduct_args'] == ('s@x.com', 1, 'major_strategy')
        doc = db.strategies['uw']
        assert doc['kb_data_year'] == 2026
        assert doc['verification_status'] == 'legacy'
        assert doc['majors_considered'] == ['Computer Science', 'Statistics']
        assert doc['synthesis']['essay_implication']
        assert doc['facts']['matched'][0]['name'] == 'Computer Science'
        assert '[REPORTED]' in doc['facts']['extract']

    def test_llm_failure_is_500_never_deducts(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_strategy(db, llm=None)
        assert status == 500 and calls['deduct'] == 0
        assert 'uw' not in db.strategies

    def test_kb_transport_failure_is_502_unbilled(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_strategy(db, facts=None)
        assert status == 502 and calls['check'] == 0 and calls['deduct'] == 0

    def test_unknown_university_is_404_unbilled(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_strategy(
            db, facts={'success': False, 'error': 'University uw not found'})
        assert status == 404 and calls['deduct'] == 0

    def test_regeneration_archives_the_prior_strategy_by_kb_year(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_strategy(db)
        prior = db.strategies['uw']
        newer_facts = {**KB_FACTS, 'data_year': 2027}
        _run_strategy(db, facts=newer_facts)
        assert db.strategy_archives == [('uw', '2026', prior)]
        assert db.strategies['uw']['kb_data_year'] == 2027


class TestGetMajorStrategy:
    def _get(self, db, facts=KB_FACTS):
        with patch.object(major_llm, 'get_db', return_value=db), \
             patch.object(major_llm, 'fetch_university_majors', return_value=facts):
            return get_major_strategy_payload('s@x.com', 'uw')

    def test_no_strategy_yet(self):
        payload, status = self._get(FakeDB())
        assert status == 200
        assert payload == {'success': True, 'strategy': None, 'stale': False}

    def test_current_strategy_is_not_stale(self):
        db = FakeDB(strategies={'uw': {'kb_data_year': 2026}})
        payload, _ = self._get(db)
        assert payload['stale'] is False and payload['current_kb_year'] == 2026

    def test_older_kb_year_is_stale(self):
        db = FakeDB(strategies={'uw': {'kb_data_year': 2025}})
        payload, _ = self._get(db)
        assert payload['stale'] is True

    def test_kb_check_failure_degrades_to_not_stale(self):
        db = FakeDB(strategies={'uw': {'kb_data_year': 2025}})
        payload, _ = self._get(db, facts=None)
        assert payload['stale'] is False and payload['current_kb_year'] is None


# ---------------------------------------------------------------------------
# Numeric-claim validator (hard AC — thorough)
# ---------------------------------------------------------------------------

EXTRACT = ("MAJOR: Computer Science\n"
           "  [REPORTED] acceptance_rate: 7 (unverified legacy data — hedge)\n"
           "  [REPORTED] internal transfer GPA bar: 3.5\n"
           "  [REPORTED] college acceptance estimate: 25% (unverified)")


class TestNumericClaimValidator:
    def test_numbers_present_in_extract_survive(self):
        synthesis = {'primary_call': 'Students report roughly 7% admit for CS. '
                                     'The transfer bar is reportedly 3.5.'}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert cleaned['primary_call'] == synthesis['primary_call']
        assert notes == []

    def test_hallucinated_percentage_sentence_is_stripped_into_notes(self):
        synthesis = {'primary_call': 'List CS as your genuine first choice. '
                                     'Admit rate here is 4.2% for this major.'}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert cleaned['primary_call'] == 'List CS as your genuine first choice.'
        assert len(notes) == 1 and '4.2%' in notes[0]

    def test_hallucinated_gpa_sentence_is_stripped(self):
        synthesis = {'backup_rationale': 'You need a 3.9 to transfer in. '
                                         'The published bar is 3.5.'}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert cleaned['backup_rationale'] == 'The published bar is 3.5.'
        assert len(notes) == 1

    def test_plain_integers_are_never_false_stripped(self):
        synthesis = {'primary_call': 'This is a top 3 program nationally and '
                                     'you should list 2 backups.'}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert cleaned['primary_call'] == synthesis['primary_call']
        assert notes == []

    def test_percent_equivalence_tolerates_trailing_zero_forms(self):
        synthesis = {'primary_call': 'Reported at about 7.0% by students.'}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert notes == []

    def test_list_fields_are_cleaned_and_emptied_items_dropped(self):
        synthesis = {'what_to_verify_yourself': [
            'Confirm the 3.5 transfer bar on the official page.',
            'Verify the 12% school-of-arts admit rate.',
        ]}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert cleaned['what_to_verify_yourself'] == [
            'Confirm the 3.5 transfer bar on the official page.']
        assert len(notes) == 1

    def test_mixed_sentence_with_one_bad_number_is_removed_whole(self):
        synthesis = {'primary_call': 'The bar is 3.5 but admit runs 2% these days. '
                                     'List CS first.'}
        cleaned, notes = validate_numeric_claims(synthesis, EXTRACT)
        assert cleaned['primary_call'] == 'List CS first.'

    def test_validator_logs_a_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            validate_numeric_claims({'primary_call': 'Admit is 1.5% here.'}, EXTRACT)
        assert any('unverifiable numeric claim' in r.message for r in caplog.records)

    def test_end_to_end_no_unextracted_number_survives_generation(self):
        # The AC verbatim: no unextracted numbers survive to output.
        db = FakeDB(profile=dict(READY_PROFILE))
        lying_llm = {**STRATEGY_LLM_RESPONSE,
                     'primary_call': 'My read: list CS. CS admits only 4% of applicants.'}
        payload, status, _ = _run_strategy(db, llm=lying_llm)
        assert status == 200
        doc = db.strategies['uw']
        assert '4%' not in doc['synthesis']['primary_call']
        assert any('4%' in n for n in doc['data_notes'])


# ---------------------------------------------------------------------------
# Deterministic capped_door door-lock warning (hard AC)
# ---------------------------------------------------------------------------

class TestDoorLockWarning:
    def test_appends_when_llm_omits_the_warning(self):
        synthesis = {'primary_call': 'List CS.', 'essay_implication': 'Tell the CS story.'}
        out, appended = ensure_door_lock_warning(synthesis, ['Computer Science'])
        assert appended is True
        assert "can't switch in later" in out['primary_call']
        assert 'apply-easier-then-transfer' in out['primary_call']

    def test_no_append_when_llm_already_warns(self):
        synthesis = {'primary_call': 'List CS — if not admitted directly you '
                                     "can't switch in later, so commit."}
        out, appended = ensure_door_lock_warning(dict(synthesis), ['Computer Science'])
        assert appended is False
        assert out['primary_call'] == synthesis['primary_call']

    def test_no_append_without_capped_majors(self):
        synthesis = {'primary_call': 'List Statistics.'}
        out, appended = ensure_door_lock_warning(dict(synthesis), [])
        assert appended is False and out == synthesis

    def test_warning_detected_in_any_field_including_lists(self):
        synthesis = {'primary_call': 'List CS.',
                     'what_to_verify_yourself': ['Note the door locks behind you.']}
        out, appended = ensure_door_lock_warning(synthesis, ['Computer Science'])
        assert appended is False

    def test_end_to_end_capped_door_synthesis_always_carries_warning(self):
        # KB_FACTS marks CS capped_door; an LLM response with no warning must
        # come out warned anyway (testable without an LLM — the AC's point).
        db = FakeDB(profile=dict(READY_PROFILE))
        bland_llm = {**STRATEGY_LLM_RESPONSE,
                     'primary_call': 'My read: list Computer Science.',
                     'second_choice_play': 'x', 'backup_rationale': 'y',
                     'undeclared_tactic': 'z', 'essay_implication': 'w',
                     'what_to_verify_yourself': []}
        _, status, _ = _run_strategy(db, llm=bland_llm)
        assert status == 200
        doc = db.strategies['uw']
        assert doc['door_lock_warning_appended'] is True
        assert "can't switch in later" in doc['synthesis']['primary_call']


# ---------------------------------------------------------------------------
# Labeled extract construction
# ---------------------------------------------------------------------------

class TestLabeledExtract:
    def test_tags_and_missing_lines(self):
        matched, related, _ = filter_facts_to_majors(KB_FACTS, ['Computer Science'])
        extract = build_labeled_extract(KB_FACTS, matched, related)
        assert '[REPORTED] entry_path: direct_admit' in extract
        assert 'capped_door' in extract and 'CANNOT switch' in extract
        assert '[REPORTED] acceptance_rate: 7' in extract
        assert '[OPINION] counselor note' in extract
        assert '[MISSING]' in extract  # computer engineering's unpublished fields
        assert 'does NOT mean easy entry' in extract  # is_impacted:false trap

    def test_verified_school_tags_verified(self):
        facts = {**KB_FACTS, 'verification_status': 'verified'}
        matched, related, _ = filter_facts_to_majors(facts, ['Computer Science'])
        extract = build_labeled_extract(facts, matched, related)
        assert '[VERIFIED] entry_risk: capped_door' in extract


# ---------------------------------------------------------------------------
# door_flags (Launchpad callout, #284)
# ---------------------------------------------------------------------------

class TestDoorFlags:
    def test_exact_match_yields_flags(self):
        flags = derive_door_flags(KB_FACTS, 'Computer Science')
        assert flags == {'entry_path': 'direct_admit', 'entry_risk': 'capped_door'}

    def test_fuzzy_match_yields_nothing(self):
        # A wrong door flag is worse than no flag — fuzzy never stamps.
        assert derive_door_flags(KB_FACTS, 'Computing & Society') is None

    def test_empty_payload_yields_nothing(self):
        assert derive_door_flags(None, 'Computer Science') is None
        assert derive_door_flags({'colleges': []}, 'Computer Science') is None

    def test_stamp_updates_the_list_item_best_effort(self):
        db = FakeDB(list_items={'uw': {'major_choice': {'primary': 'Computer Science'}}})
        with patch.object(major_llm, 'get_db', return_value=db), \
             patch.object(major_llm, 'fetch_university_majors', return_value=KB_FACTS):
            flags = major_llm.stamp_door_flags(
                's@x.com', 'uw', {'primary': 'Computer Science'})
        assert flags == {'entry_path': 'direct_admit', 'entry_risk': 'capped_door'}
        assert db.list_items['uw']['major_choice']['door_flags'] == flags

    def test_stamp_fetch_failure_never_blocks(self):
        db = FakeDB(list_items={'uw': {}})
        with patch.object(major_llm, 'get_db', return_value=db), \
             patch.object(major_llm, 'fetch_university_majors', return_value=None):
            assert major_llm.stamp_door_flags(
                's@x.com', 'uw', {'primary': 'Computer Science'}) is None


class TestValidatorHardening:
    """Review F2/F4: pool separation + percent-form coverage."""

    _EXTRACT = (
        "SCHOOL: UIUC\n"
        "KB data year: 2026; verification: legacy; richness tier 2\n"
        "MAJOR: Computer Science (in Grainger)\n"
        "  [REPORTED] acceptance_rate: 7.0 (unverified legacy data — hedge)\n"
        "  [REPORTED] internal transfer GPA bar: 3.5\n"
    )

    def _clean(self, text):
        import major_llm
        synthesis, notes = major_llm.validate_numeric_claims(
            {'primary_call': text}, self._EXTRACT)
        return synthesis['primary_call'], notes

    def test_metadata_numbers_do_not_legitimize_claims(self):
        # 'richness tier 2' must not whitelist a fabricated '2%'.
        out, notes = self._clean('Only 2% of transfer applicants make it in.')
        assert out == '' and notes

    def test_gpa_fact_does_not_legitimize_percent_claim(self):
        out, notes = self._clean('Historically 3.5% of applicants are admitted.')
        assert out == '' and notes

    def test_percent_fact_supports_percent_claim(self):
        out, notes = self._clean('The reported rate is about 7.0% — hedge it.')
        assert '7.0%' in out and not notes

    def test_gpa_fact_supports_gpa_claim(self):
        out, notes = self._clean('Transferring in needs a 3.5 GPA (reported).')
        assert '3.5' in out and not notes

    def test_word_and_fullwidth_percent_forms_are_policed(self):
        out, _ = self._clean('Roughly 4 percent of applicants get in.')
        assert out == ''
        out, _ = self._clean('Rate is 9％ here.')
        assert out == ''

    def test_fabricated_gpa_stripped(self):
        out, notes = self._clean('You need a 2.0 GPA to transfer.')
        assert out == '' and notes


class TestDoorLockMarkerHardening:
    """Review F3: a backdoor RECOMMENDATION must not suppress the warning."""

    def test_neutral_switch_into_does_not_count_as_warning(self):
        import major_llm
        synthesis = {'primary_call': 'Apply to Pre-Sciences and switch into '
                                     'Computer Science after year one — many do.'}
        out, appended = major_llm.ensure_door_lock_warning(
            dict(synthesis), ['Computer Science'])
        assert appended is True                 # the deterministic warning fires
        assert "can't switch" in out['primary_call'].lower() or \
               'cannot switch' in out['primary_call'].lower() or \
               'lock' in out['primary_call'].lower()

    def test_genuine_negated_warning_suppresses_append(self):
        import major_llm
        synthesis = {'primary_call': 'CS is direct admit only here — if not '
                                     'admitted directly you cannot switch in.'}
        out, appended = major_llm.ensure_door_lock_warning(
            dict(synthesis), ['Computer Science'])
        assert appended is False


# ---------------------------------------------------------------------------
# Per-college Major Chances ranking (#302) — sibling of the strategy generator
# ---------------------------------------------------------------------------

RANKING_LLM_RESPONSE = {
    'majors': [
        {'name': 'Computer Science', 'college': 'College of Engineering',
         'tier': 'reach',
         'rationale': "A strong record, but CS here is direct-admit only."},
        {'name': 'Computer Engineering', 'college': 'College of Engineering',
         'tier': 'possible',
         'rationale': "Your robotics work maps well; a realistic match."},
    ],
}


def _run_ranking(db, body=None, llm=RANKING_LLM_RESPONSE, facts=KB_FACTS,
                 has_credits=True):
    body = body or {'user_email': 's@x.com', 'university_id': 'uw'}
    calls, p_check, p_deduct = _billing_seams(has_credits=has_credits)
    with patch.object(major_llm, 'get_db', return_value=db), \
         patch.object(major_llm, '_llm_json', return_value=llm) as p_llm, \
         patch.object(major_llm, 'fetch_university_majors', return_value=facts), \
         p_check, p_deduct:
        payload, status = run_rank_college_majors(body)
    calls['llm'] = p_llm.call_count
    return payload, status, calls


class TestBuildFullCatalogRows:
    def test_every_major_bound_with_college_and_context(self):
        rows = build_full_catalog_rows(KB_FACTS)
        assert [r['name'] for r in rows] == ['Computer Science', 'Computer Engineering']
        assert all(r['college'] == 'College of Engineering' for r in rows)
        assert rows[0]['college_context']['admissions_model'] == 'Direct to College'
        assert rows[0]['college_context']['is_restricted_or_capped'] is True

    def test_respects_the_cap(self):
        rows = build_full_catalog_rows(KB_FACTS, cap=1)
        assert len(rows) == 1

    def test_empty_when_no_colleges(self):
        assert build_full_catalog_rows({'colleges': []}) == []


class TestRankNeverChargeOnMiss:
    def test_zero_majors_in_kb_is_200_null_ranking_unbilled(self):
        db = FakeDB(profile={'intended_majors': ['Computer Science']})
        empty_facts = {**KB_FACTS, 'colleges': []}
        payload, status, calls = _run_ranking(db, facts=empty_facts)
        assert status == 200
        assert payload['success'] is True and payload['ranking'] is None
        assert payload['gaps'] == ['Computer Science']
        # No billing surface touched at all — not even the credit check.
        assert calls['check'] == 0 and calls['deduct'] == 0 and calls['llm'] == 0

    def test_miss_increments_kb_gaps_demand_signal(self):
        db = FakeDB(profile={'intended_majors': ['Computer Science']})
        empty_facts = {**KB_FACTS, 'colleges': []}
        _run_ranking(db, facts=empty_facts)
        assert db.kb_gap_calls == [('uw', ['Computer Science'])]

    def test_miss_with_no_intended_majors_still_records_a_gap(self):
        db = FakeDB(profile={})
        empty_facts = {**KB_FACTS, 'colleges': []}
        payload, status, _ = _run_ranking(db, facts=empty_facts)
        assert status == 200 and payload['ranking'] is None
        assert db.kb_gap_calls == [('uw', ['(whole catalog)'])]

    def test_miss_works_even_with_zero_credits(self):
        db = FakeDB(profile={'intended_majors': ['Computer Science']})
        empty_facts = {**KB_FACTS, 'colleges': []}
        payload, status, calls = _run_ranking(db, facts=empty_facts, has_credits=False)
        assert status == 200 and payload['ranking'] is None

    def test_transport_failure_is_502_unbilled(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_ranking(db, facts=None)
        assert status == 502 and calls['check'] == 0 and calls['deduct'] == 0

    def test_unknown_university_is_404_unbilled(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_ranking(
            db, facts={'success': False, 'error': 'University uw not found'})
        assert status == 404 and calls['deduct'] == 0


class TestRankBillingAndPersistence:
    def test_insufficient_credits_402_never_generates(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_ranking(db, has_credits=False)
        assert status == 402 and payload['error'] == 'insufficient_credits'
        assert calls['llm'] == 0 and calls['deduct'] == 0

    def test_success_deducts_once_and_persists_tiers(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_ranking(db)
        assert status == 200 and payload['success'] is True
        assert calls['deduct'] == 1
        assert calls['deduct_args'] == ('s@x.com', 1, 'major_chances')
        doc = db.rankings['uw']
        assert doc['kb_data_year'] == 2026
        assert doc['verification_status'] == 'legacy'
        assert doc['basis'] == 'inference'
        # tiers keyed by exactly the four canonical tiers
        assert set(doc['tiers']) == {'strong', 'possible', 'reach', 'long_shot'}
        names = {m['name'] for tier in doc['tiers'].values() for m in tier}
        assert names == {'Computer Science', 'Computer Engineering'}

    def test_entry_path_and_risk_come_from_the_kb_not_the_llm(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        # LLM lies about the fields — the KB row is authoritative.
        lying = {'majors': [
            {'name': 'Computer Science', 'tier': 'strong',
             'entry_path': 'open_declaration', 'entry_risk': 'standard',
             'rationale': 'x'}]}
        _run_ranking(db, llm=lying)
        cs = db.rankings['uw']['tiers']['reach'] + db.rankings['uw']['tiers']['strong']
        cs = [m for m in cs if m['name'] == 'Computer Science'][0]
        assert cs['entry_path'] == 'direct_admit'   # from KB, not the LLM
        assert cs['entry_risk'] == 'capped_door'     # from KB, not the LLM

    def test_llm_failure_is_500_never_deducts(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_ranking(db, llm=None)
        assert status == 500 and calls['deduct'] == 0
        assert 'uw' not in db.rankings

    def test_save_failure_is_500_never_deducts(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        db.save_ranking_ok = False
        payload, status, calls = _run_ranking(db)
        assert status == 500 and calls['deduct'] == 0

    def test_regeneration_archives_the_prior_ranking_by_kb_year(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_ranking(db)
        prior = db.rankings['uw']
        newer_facts = {**KB_FACTS, 'data_year': 2027}
        _run_ranking(db, facts=newer_facts)
        assert db.ranking_archives == [('uw', '2026', prior)]
        assert db.rankings['uw']['kb_data_year'] == 2027

    def test_empty_fit_selection_is_still_billed_with_a_note(self):
        # A real generation that binds NO catalog majors (rare) — billed, but
        # distinguished from the unbilled KB miss by an explicit note + empty tiers.
        db = FakeDB(profile=dict(READY_PROFILE))
        no_fit = {'majors': [{'name': 'Basket Weaving', 'tier': 'reach', 'rationale': 'x'}]}
        payload, status, calls = _run_ranking(db, llm=no_fit)
        assert status == 200 and payload['success'] is True
        assert calls['deduct'] == 1                     # real generation → billed
        doc = db.rankings['uw']
        assert sum(len(v) for v in doc['tiers'].values()) == 0
        assert doc['note']


class TestRankTrustDiscipline:
    def test_capped_door_major_gets_door_lock_appended_when_missing(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        bland = {'majors': [
            {'name': 'Computer Science', 'tier': 'reach',
             'rationale': 'A stretch given how competitive it is.'}]}
        _run_ranking(db, llm=bland)
        cs = db.rankings['uw']['tiers']['reach'][0]
        assert "can't switch in later" in cs['rationale']

    def test_fabricated_percentage_stripped_from_rationale(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        lying = {'majors': [
            {'name': 'Computer Engineering', 'tier': 'possible',
             'rationale': 'A realistic match. Only 3% get in though.'}]}
        _run_ranking(db, llm=lying)
        ce = db.rankings['uw']['tiers']['possible'][0]
        assert '3%' not in ce['rationale']
        assert any('3%' in n for n in db.rankings['uw']['data_notes'])

    def test_reported_rate_rides_along_only_where_kb_has_one(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_ranking(db)
        by_name = {m['name']: m for tier in db.rankings['uw']['tiers'].values() for m in tier}
        # CS has reported_stats.acceptance_rate 7 in KB_FACTS; CE has none.
        assert by_name['Computer Science']['reported_rate']['value'] == 7
        assert by_name['Computer Science']['reported_rate']['label'] == 'reported (unverified)'
        assert 'reported_rate' not in by_name['Computer Engineering']

    def test_major_not_in_catalog_is_dropped(self):
        rows = build_full_catalog_rows(KB_FACTS)
        parsed = {'majors': [
            {'name': 'Underwater Basket Weaving', 'tier': 'strong', 'rationale': 'x'},
            {'name': 'Computer Science', 'tier': 'reach', 'rationale': 'y'}]}
        tiers, _ = normalize_college_major_ranking(parsed, rows, KB_FACTS)
        names = {m['name'] for t in tiers.values() for m in t}
        assert names == {'Computer Science'}    # invented major dropped

    def test_unknown_tier_coerces_to_reach(self):
        rows = build_full_catalog_rows(KB_FACTS)
        parsed = {'majors': [{'name': 'Computer Engineering',
                              'tier': 'definitely-in', 'rationale': 'x'}]}
        tiers, _ = normalize_college_major_ranking(parsed, rows, KB_FACTS)
        assert [m['name'] for m in tiers['reach']] == ['Computer Engineering']

    def test_capped_door_carries_flag_and_caveat_in_any_tier(self):
        # #305 review F1: tier is the admission-chance read; a capped_door
        # major may legitimately be 'strong' (a strong direct-admit candidate),
        # but it ALWAYS gets door_lock=True + the door-lock caveat so a
        # "Strong match" chip can never hide a locked door.
        db = FakeDB(profile=dict(READY_PROFILE))
        strong_capped = {'majors': [
            {'name': 'Computer Science', 'tier': 'strong',
             'rationale': "You're a strong candidate here."}]}
        _run_ranking(db, llm=strong_capped)
        cs = db.rankings['uw']['tiers']['strong'][0]
        assert cs['entry_risk'] == 'capped_door'
        assert cs['door_lock'] is True
        assert "can't switch in later" in cs['rationale']

    def test_cross_major_number_attribution_is_stripped(self):
        # #305 review F2: CS has a real 7% in the KB; CE has none. A rationale
        # for CE claiming "7%" must be stripped — a real rate for one major
        # cannot legitimize the same figure on another (per-major validation).
        db = FakeDB(profile=dict(READY_PROFILE))
        cross = {'majors': [
            {'name': 'Computer Engineering', 'tier': 'possible',
             'rationale': 'A realistic match — about 7% get in.'}]}
        _run_ranking(db, llm=cross)
        ce = db.rankings['uw']['tiers']['possible'][0]
        assert '7%' not in ce['rationale']
        assert any('7%' in n for n in db.rankings['uw']['data_notes'])

    def test_tiers_dict_shape_is_also_accepted(self):
        rows = build_full_catalog_rows(KB_FACTS)
        parsed = {'tiers': {'possible': [
            {'name': 'Computer Engineering', 'rationale': 'x'}]}}
        tiers, _ = normalize_college_major_ranking(parsed, rows, KB_FACTS)
        assert [m['name'] for m in tiers['possible']] == ['Computer Engineering']


class TestEnsureMajorDoorLock:
    def test_appends_when_missing(self):
        out = ensure_major_door_lock_rationale('A stretch.', 'Computer Science')
        assert "can't switch in later" in out
        assert 'Computer Science' in out

    def test_no_append_when_already_warned(self):
        r = "Direct admit only — you cannot switch in later, so commit."
        assert ensure_major_door_lock_rationale(r, 'Computer Science') == r


class TestGetCollegeMajorChances:
    def _get(self, db, facts=KB_FACTS):
        with patch.object(major_llm, 'get_db', return_value=db), \
             patch.object(major_llm, 'fetch_university_majors', return_value=facts):
            return get_college_major_chances_payload('s@x.com', 'uw')

    def test_no_ranking_yet(self):
        payload, status = self._get(FakeDB())
        assert status == 200
        assert payload == {'success': True, 'ranking': None, 'stale': False}

    def test_current_ranking_is_not_stale(self):
        db = FakeDB(rankings={'uw': {'kb_data_year': 2026}})
        payload, _ = self._get(db)
        assert payload['stale'] is False and payload['current_kb_year'] == 2026

    def test_older_kb_year_is_stale(self):
        db = FakeDB(rankings={'uw': {'kb_data_year': 2025}})
        payload, _ = self._get(db)
        assert payload['stale'] is True

    def test_kb_check_failure_degrades_to_not_stale(self):
        db = FakeDB(rankings={'uw': {'kb_data_year': 2025}})
        payload, _ = self._get(db, facts=None)
        assert payload['stale'] is False and payload['current_kb_year'] is None


class TestMajorMapCatalogGrounding:
    """#306: the Major Map is grounded in the global catalog — real offered
    majors, not free-form names."""

    def test_catalog_injected_into_prompt(self):
        from major_llm import build_major_map_prompt
        prompt = build_major_map_prompt(dict(READY_PROFILE), catalog=MAP_CATALOG)
        assert 'MAJOR CATALOG' in prompt
        assert 'Computer Science' in prompt and 'Data Science' in prompt

    def test_no_catalog_block_when_unavailable(self):
        from major_llm import build_major_map_prompt
        prompt = build_major_map_prompt(dict(READY_PROFILE), catalog=None)
        assert 'MAJOR CATALOG' not in prompt

    def test_matched_majors_carry_offered_count_and_flag(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)
        by_name = {m['name']: m
                   for c in db.major_map['clusters'] for m in c['majors']}
        assert by_name['Computer Science']['in_catalog'] is True
        assert by_name['Computer Science']['offered_count'] == 133

    def test_off_catalog_major_is_flagged_not_silently_offered(self):
        # Industrial Engineering isn't in MAP_CATALOG → flagged in_catalog:false,
        # kept (map is exploratory) but never presented as offered.
        db = FakeDB(profile=dict(READY_PROFILE))
        _run_map(db)
        by_name = {m['name']: m
                   for c in db.major_map['clusters'] for m in c['majors']}
        assert by_name['Industrial Engineering']['in_catalog'] is False
        assert 'offered_count' not in by_name['Industrial Engineering']
        assert db.major_map['catalog_grounded'] is True

    def test_catalog_fetch_failure_degrades_gracefully(self):
        # Catalog unavailable → still generates (billed), flags not-grounded +
        # a data note, rather than failing the map the student paid for.
        db = FakeDB(profile=dict(READY_PROFILE))
        payload, status, calls = _run_map(db, catalog=None)
        assert status == 200 and payload['success'] is True
        assert calls['deduct'] == 1
        assert db.major_map['catalog_grounded'] is False
        assert any('catalog was unavailable' in n.lower()
                   for n in db.major_map['data_notes'])
        # majors are NOT annotated with in_catalog when there's no catalog
        m = db.major_map['clusters'][0]['majors'][0]
        assert 'in_catalog' not in m


class TestNormalizerParity:
    """#304/#306 review: major_match and the KB catalog normalizer must agree
    on the display-name transforms grounding relies on."""

    def test_program_track_concentration_suffixes_stripped(self):
        from major_match import normalize_major
        assert normalize_major('Data Science Program') == 'data science'
        assert normalize_major('Nursing Track') == 'nursing'
        assert normalize_major('Biology Concentration') == 'biology'


class TestMapGeneratorVersionStaleness:
    """#308: a Major Map generated before catalog grounding (#307) must be
    flagged stale so the regenerate CTA fires — a code improvement has to
    reach students still holding a cached map."""

    def test_pre_grounding_map_is_stale_with_upgrade_reason(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        # A map from before #307: no catalog_grounded, profile unchanged.
        fp = major_llm.profile_fingerprint(READY_PROFILE)
        db.major_map = {'clusters': [{'theme': 't', 'majors': [{'name': 'CS'}]}],
                        'profile_fingerprint': fp}   # catalog_grounded absent
        with patch.object(major_llm, 'get_db', return_value=db):
            payload, status = major_llm.get_major_map_payload('s@x.com')
        assert status == 200 and payload['stale'] is True
        assert any('grounded' in r for r in payload['stale_reasons'])

    def test_grounded_map_unchanged_profile_is_not_stale(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        fp = major_llm.profile_fingerprint(READY_PROFILE)
        db.major_map = {'clusters': [{'theme': 't', 'majors': [{'name': 'Computer Science'}]}],
                        'profile_fingerprint': fp, 'catalog_grounded': True}
        with patch.object(major_llm, 'get_db', return_value=db):
            payload, status = major_llm.get_major_map_payload('s@x.com')
        assert payload['stale'] is False and payload['stale_reasons'] == []

    def test_both_reasons_compose(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        # pre-grounding AND profile changed since generation
        db.major_map = {'clusters': [{'theme': 't', 'majors': [{'name': 'CS'}]}],
                        'profile_fingerprint': {'sha1': 'OLD', 'parts': {'grade': 'x'}}}
        with patch.object(major_llm, 'get_db', return_value=db):
            payload, _ = major_llm.get_major_map_payload('s@x.com')
        assert payload['stale'] is True
        assert any('grounded' in r for r in payload['stale_reasons'])
        assert len(payload['stale_reasons']) >= 2

    def test_non_force_generate_regenerates_a_pre_grounding_map(self):
        db = FakeDB(profile=dict(READY_PROFILE))
        fp = major_llm.profile_fingerprint(READY_PROFILE)
        db.major_map = {'clusters': [{'theme': 'old'}], 'profile_fingerprint': fp}
        # No force, profile unchanged — but the cached map is ungrounded, so it
        # must regenerate (billed) rather than serve the stale cache.
        payload, status, calls = _run_map(db)   # _run_map patches catalog + llm
        assert status == 200 and payload.get('from_cache') is not True
        assert calls['deduct'] == 1
        assert db.major_map['catalog_grounded'] is True
