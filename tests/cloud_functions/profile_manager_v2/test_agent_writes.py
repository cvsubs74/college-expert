"""Agent-write trust re-application (#310) — THE critical correctness surface.

An agent can save a fit / major-chances for FREE, but it must NOT be able to
write fabricated or malformed data. These tests pin that the server RE-APPLIES
the exact in-app trust machinery on the agent-save path, so an agent-saved
artifact is indistinguishable in trust from a Stratia-generated one:

  - save-external-fit: an inflated category for a hyper-selective school is
    FLOORED, match% is clamped, and acceptance_rate + KB provenance come from
    the KB (never the agent's numbers); invalid shape → 400.
  - save-external-major-chances: fabricated %/GPA in rationales are STRIPPED,
    entry_path/entry_risk come from the KB not the agent, off-catalog majors are
    dropped, tiers coerced; a KB-majors miss → 400.

Also unit-tests the extracted post_process_fit directly.
"""

from unittest.mock import patch

import agent_writes as aw
from fit_computation import post_process_fit


# KB action=majors payload (CS is capped_door with a reported 7% rate; CE is standard).
KB_FACTS = {
    'success': True, 'university_id': 'uw', 'official_name': 'UW',
    'data_year': 2026, 'verification_status': 'legacy', 'richness_tier': 2,
    'colleges': [{
        'name': 'College of Engineering',
        'admissions_model': 'Direct to College',
        'is_restricted_or_capped': True,
        'acceptance_rate_estimate': {'value': '25%', 'basis': 'kb_reported'},
        'majors': [
            {'name': 'Computer Science',
             'entry_path': {'value': 'direct_admit', 'raw': 'Direct admission only.', 'basis': 'kb_reported'},
             'entry_risk': 'capped_door',
             'is_impacted': {'value': False, 'basis': 'kb_reported'},
             'door_policy': {'direct_admit_only': True, 'internal_transfer_allowed': False,
                             'internal_transfer_gpa': None, 'basis': 'kb_reported'},
             'prerequisite_courses': [],
             'reported_stats': {'acceptance_rate': 7, 'basis': 'kb_reported'}},
            {'name': 'Computer Engineering',
             'entry_path': {'value': 'direct_admit', 'raw': None, 'basis': None},
             'entry_risk': 'standard',
             'is_impacted': {'value': None, 'basis': None},
             'door_policy': {'direct_admit_only': None, 'internal_transfer_allowed': True,
                             'internal_transfer_gpa': 3.5, 'basis': 'kb_reported'},
             'prerequisite_courses': [], 'reported_stats': None},
        ],
    }],
    'data_notes': [],
}


class FakeDB:
    def __init__(self, profile=None, ranking=None):
        self.profile = profile if profile is not None else {}
        self.ranking = ranking
        self.saved_ranking = None
        self.archives = []

    def get_profile(self, user_id):
        return self.profile

    def get_college_major_chances(self, user_id, university_id):
        return self.ranking

    def save_college_major_chances(self, user_id, university_id, doc):
        self.saved_ranking = doc
        return True

    def archive_college_major_chances(self, user_id, university_id, doc, key):
        self.archives.append((university_id, key, doc))
        return True


# ---------------------------------------------------------------------------
# post_process_fit (the extracted, shared deterministic post-processor)
# ---------------------------------------------------------------------------

class TestPostProcessFit:
    def test_hyper_selective_floors_safety_to_super_reach(self):
        fit = {'fit_category': 'SAFETY', 'match_percentage': 95}
        post_process_fit(fit, acceptance_rate=4, profile={})
        assert fit['fit_category'] == 'SUPER_REACH'
        assert fit['match_percentage'] <= 34

    def test_highly_selective_floors_to_reach(self):
        fit = {'fit_category': 'SAFETY', 'match_percentage': 90}
        post_process_fit(fit, acceptance_rate=12, profile={})
        assert fit['fit_category'] == 'REACH'
        assert 35 <= fit['match_percentage'] <= 54

    def test_accessible_ceiling_raises_reach_to_safety(self):
        fit = {'fit_category': 'REACH', 'match_percentage': 40}
        post_process_fit(fit, acceptance_rate=60, profile={})
        assert fit['fit_category'] == 'SAFETY'
        assert fit['match_percentage'] >= 75

    def test_factor_scores_clamped_to_bounds(self):
        fit = {'fit_category': 'TARGET', 'match_percentage': 65,
               'factors': [{'name': 'Major Fit', 'score': 99, 'max': 15}]}
        post_process_fit(fit, acceptance_rate=30, profile={})
        assert fit['factors'][0]['score'] == 15

    def test_no_scores_forces_dont_submit(self):
        fit = {'fit_category': 'TARGET', 'match_percentage': 65,
               'test_strategy': {'recommendation': 'Submit'}}
        post_process_fit(fit, acceptance_rate=30, profile={'grade': '12'})
        assert fit['test_strategy']['recommendation'] == "Don't Submit"


# ---------------------------------------------------------------------------
# POST /save-external-fit
# ---------------------------------------------------------------------------

def _run_fit(fit_analysis, *, university_data=None, profile=None, source='claude'):
    university_data = ({'acceptance_rate': 4, 'data_year': 2026}
                       if university_data is None else university_data)
    saved = {}

    def fake_save(user_email, university_id, fit):
        saved['fit'] = fit
        return {'success': True}

    with patch.object(aw, 'get_db') as p_db, \
         patch.object(aw, 'fetch_university_profile', return_value=university_data), \
         patch.object(aw, 'save_fit_analysis', side_effect=fake_save):
        p_db.return_value.get_profile.return_value = profile or {}
        payload, status = aw.run_save_external_fit('s@x.com', 'uw', fit_analysis, source)
    return payload, status, saved


class TestSaveExternalFit:
    def test_inflated_category_for_hyper_selective_school_is_floored(self):
        # The agent claims SAFETY/95% AND lies about acceptance_rate — the KB's
        # 4% wins and floors the category to SUPER_REACH.
        payload, status, saved = _run_fit(
            {'fit_category': 'SAFETY', 'match_percentage': 95,
             'explanation': 'Great fit!', 'acceptance_rate': 60})
        assert status == 200 and payload['success'] is True
        fit = saved['fit']
        assert fit['fit_category'] == 'SUPER_REACH'      # floored, not SAFETY
        assert fit['match_percentage'] <= 34             # clamped into the band
        assert fit['acceptance_rate'] == 4               # from the KB, not the agent

    def test_stamps_source_basis_and_kb_provenance(self):
        payload, status, saved = _run_fit(
            {'fit_category': 'REACH', 'match_percentage': 45, 'explanation': 'x'},
            source='chatgpt')
        fit = saved['fit']
        assert fit['source'] == 'chatgpt'
        assert fit['basis'] == 'inference'
        assert fit['kb_data_year'] == 2026               # stamped from the KB doc

    def test_invalid_shape_is_400_with_field_errors(self):
        payload, status, _ = _run_fit(
            {'match_percentage': 200})  # missing category+explanation, bad %
        assert status == 400
        assert payload['error'] == 'invalid fit_analysis'
        assert any('fit_category' in e for e in payload['field_errors'])
        assert any('explanation' in e for e in payload['field_errors'])

    def test_test_strategy_forced_off_submit_when_no_scores(self):
        payload, status, saved = _run_fit(
            {'fit_category': 'TARGET', 'match_percentage': 65, 'explanation': 'x',
             'test_strategy': {'recommendation': 'Submit'}},
            university_data={'acceptance_rate': 30, 'data_year': 2026},
            profile={'grade': '12'})
        assert saved['fit']['test_strategy']['recommendation'] == "Don't Submit"

    def test_injected_extra_fields_are_dropped_or_overridden(self):
        # An agent stuffs the payload with keys it shouldn't control: a render-sink
        # logo_url, a fake verified flag, a fake KB year, a spoofed source/basis,
        # and a mismatched university_id. All must be dropped (not in the content
        # allow-list) or overridden server-side (#314 review F: no passthrough).
        payload, status, saved = _run_fit(
            {'fit_category': 'REACH', 'match_percentage': 45, 'explanation': 'x',
             'logo_url': 'https://evil.example/track.gif',
             'verified': True, 'kb_data_year': 1999, 'kb_verified': True,
             'source': 'stratia', 'basis': 'kb_verified',
             'university_id': 'not-uw', 'acceptance_rate': 60,
             'selectivity_tier': 'accessible', 'match_score': 99},
            university_data={'acceptance_rate': 4, 'data_year': 2026},
            source='claude')
        fit = saved['fit']
        assert 'verified' not in fit and 'kb_verified' not in fit  # junk dropped
        assert fit.get('logo_url', '').find('evil') == -1          # no render-sink logo
        assert fit['kb_data_year'] == 2026                         # from KB, not 1999
        assert fit['source'] == 'claude'                           # connector-attributed
        assert fit['basis'] == 'inference'                         # never kb_verified
        assert fit['university_id'] == 'uw'                        # from the arg, not payload
        assert fit['acceptance_rate'] == 4                         # KB, not agent's 60

    def test_logo_url_comes_from_kb_not_the_agent(self):
        payload, status, saved = _run_fit(
            {'fit_category': 'REACH', 'match_percentage': 45, 'explanation': 'x',
             'logo_url': 'https://evil.example/x.gif'},
            university_data={'acceptance_rate': 4, 'data_year': 2026,
                             'official_name': 'UW', 'logo_url': 'https://cdn/uw.png'})
        assert saved['fit']['logo_url'] == 'https://cdn/uw.png'
        assert saved['fit']['university_name'] == 'UW'

    def test_kb_miss_is_400_and_agent_rate_never_used(self):
        # School not in the KB → 400 (the selectivity floor can't be enforced), and
        # the agent's acceptance_rate is NEVER used as a floor fallback (no save).
        saved = {}

        def fake_save(user_email, university_id, fit):
            saved['fit'] = fit
            return {'success': True}

        with patch.object(aw, 'get_db') as p_db, \
             patch.object(aw, 'fetch_university_profile', return_value=None), \
             patch.object(aw, 'save_fit_analysis', side_effect=fake_save):
            p_db.return_value.get_profile.return_value = {}
            payload, status = aw.run_save_external_fit(
                's@x.com', 'ghost-u',
                {'fit_category': 'SAFETY', 'match_percentage': 95,
                 'explanation': 'x', 'acceptance_rate': 90}, 'claude')
        assert status == 400
        assert payload['success'] is False
        assert 'saved' not in saved  # never persisted


# ---------------------------------------------------------------------------
# POST /save-external-major-chances
# ---------------------------------------------------------------------------

def _run_chances(ranking, *, facts=KB_FACTS, profile=None, source='claude'):
    db = FakeDB(profile=profile or {})
    with patch.object(aw, 'get_db', return_value=db), \
         patch.object(aw, 'fetch_university_majors', return_value=facts):
        payload, status = aw.run_save_external_major_chances(
            's@x.com', 'uw', ranking, source)
    return payload, status, db


def _all_majors(doc):
    return [m for tier in doc['tiers'].values() for m in tier]


class TestSaveExternalMajorChances:
    def test_entry_path_and_risk_come_from_kb_not_the_agent(self):
        # The agent lies about entry_path/entry_risk; the KB row is authoritative.
        payload, status, db = _run_chances({'majors': [
            {'name': 'Computer Science', 'tier': 'strong',
             'entry_path': 'open_declaration', 'entry_risk': 'standard',
             'rationale': 'A strong match.'}]})
        assert status == 200 and payload['success'] is True
        cs = [m for m in _all_majors(db.saved_ranking) if m['name'] == 'Computer Science'][0]
        assert cs['entry_path'] == 'direct_admit'    # from KB
        assert cs['entry_risk'] == 'capped_door'     # from KB
        assert cs.get('door_lock') is True

    def test_fabricated_percentage_and_gpa_are_stripped_from_rationale(self):
        payload, status, db = _run_chances({'majors': [
            {'name': 'Computer Engineering', 'tier': 'possible',
             'rationale': 'A realistic match. Only 2% get in and you need a 3.9 GPA.'}]})
        ce = [m for m in _all_majors(db.saved_ranking) if m['name'] == 'Computer Engineering'][0]
        assert '2%' not in ce['rationale']
        assert '3.9' not in ce['rationale']
        assert any('2%' in n or '3.9' in n for n in db.saved_ranking['data_notes'])

    def test_off_catalog_major_is_dropped(self):
        payload, status, db = _run_chances({'majors': [
            {'name': 'Underwater Basket Weaving', 'tier': 'strong', 'rationale': 'x'},
            {'name': 'Computer Science', 'tier': 'reach', 'rationale': 'y'}]})
        names = {m['name'] for m in _all_majors(db.saved_ranking)}
        assert names == {'Computer Science'}         # the fake major is dropped

    def test_stamps_source_and_basis(self):
        payload, status, db = _run_chances(
            {'majors': [{'name': 'Computer Science', 'tier': 'reach', 'rationale': 'x'}]},
            source='chatgpt')
        assert db.saved_ranking['source'] == 'chatgpt'
        assert db.saved_ranking['basis'] == 'inference'
        assert db.saved_ranking['kb_data_year'] == 2026

    def test_invalid_shape_is_400_with_field_errors(self):
        payload, status, _ = _run_chances({'majors': [
            {'name': 'Computer Science', 'tier': 'bogus_tier', 'rationale': 'x'}]})
        assert status == 400
        assert payload['error'] == 'invalid ranking'
        assert any('tier' in e for e in payload['field_errors'])

    def test_kb_miss_is_400(self):
        payload, status, _ = _run_chances(
            {'majors': [{'name': 'CS', 'tier': 'reach', 'rationale': 'x'}]},
            facts={'success': False, 'error': 'not found'})
        assert status == 400

    def test_kb_transport_failure_is_502(self):
        payload, status, _ = _run_chances(
            {'majors': [{'name': 'CS', 'tier': 'reach', 'rationale': 'x'}]},
            facts=None)
        assert status == 502

    def test_school_with_zero_kb_majors_is_400(self):
        payload, status, _ = _run_chances(
            {'majors': [{'name': 'CS', 'tier': 'reach', 'rationale': 'x'}]},
            facts={'success': True, 'colleges': [], 'data_year': 2026})
        assert status == 400
