"""Trust-labeled majors extract (#281): entry-path classifier with an honest
'unclear' bucket, structural entry_risk, basis labels, richness tiers, and
the action=majors surface in main.py."""


# --- classifier ---------------------------------------------------------------


class TestClassifyEntryPath:
    def test_direct_admit_phrasings(self, kb):
        c = kb.major_facts.classify_entry_path
        assert c('Direct Admit') == 'direct_admit'
        assert c('Students are admitted directly to the major') == 'direct_admit'
        assert c(None, direct_admit_only=True) == 'direct_admit'

    def test_pre_major_and_composite(self, kb):
        c = kb.major_facts.classify_entry_path
        assert c('Pre-Major System') == 'pre_major'
        # pre-major + a later competitive application = the pre-major system:
        # classify by the gate the APPLICANT faces first.
        assert c('Admitted as pre-business; competitive application to the '
                 'major after two semesters') == 'pre_major'

    def test_secondary_application(self, kb):
        c = kb.major_facts.classify_entry_path
        assert c('Apply as Sophomore') == 'secondary_application'
        assert c('Internal application after enrollment') == 'secondary_application'

    def test_open_declaration(self, kb):
        c = kb.major_facts.classify_entry_path
        assert c('Chosen after enrolling; concentration declared in spring of '
                 'sophomore year') == 'open_declaration'

    def test_unclear_on_conflict_or_no_match(self, kb):
        c = kb.major_facts.classify_entry_path
        assert c('') == 'unclear'
        assert c(None) == 'unclear'
        assert c('Admission handled by the registrar') == 'unclear'
        # direct-admit AND open-declaration phrasing in one string → unclear,
        # never a guessed badge.
        assert c('Direct admit to pre-major status, majors declared after '
                 'enrolling via open enrollment') == 'unclear'


# --- entry risk ---------------------------------------------------------------


class TestEntryRisk:
    def test_capped_door_beats_everything(self, kb):
        r = kb.major_facts.derive_entry_risk(
            {'direct_admit_only': True, 'is_impacted': False}, {}, 'direct_admit')
        assert r == 'capped_door'
        r = kb.major_facts.derive_entry_risk(
            {'internal_transfer_allowed': False}, {}, 'unclear')
        assert r == 'capped_door'

    def test_uiuc_cs_trap(self, kb):
        """Verified UIUC CS: is_impacted=false (no official designation) but
        direct-admit-only with transfers not permitted — the honest signal is
        capped_door, never 'not competitive'."""
        major = {'name': 'Computer Science', 'is_impacted': False,
                 'direct_admit_only': True, 'internal_transfer_allowed': False}
        assert kb.major_facts.derive_entry_risk(major, {}, 'direct_admit') == 'capped_door'

    def test_elevated_paths(self, kb):
        d = kb.major_facts.derive_entry_risk
        assert d({'is_impacted': True}, {}, 'direct_admit') == 'elevated'
        assert d({}, {'is_restricted_or_capped': True}, 'direct_admit') == 'elevated'
        assert d({'internal_transfer_gpa': 3.67}, {}, 'pre_major') == 'elevated'
        assert d({'internal_transfer_gpa': '3.8 GPA required'}, {}, 'pre_major') == 'elevated'
        assert d({}, {}, 'secondary_application') == 'elevated'

    def test_standard_and_unknown(self, kb):
        d = kb.major_facts.derive_entry_risk
        assert d({'internal_transfer_gpa': 2.5}, {}, 'open_declaration') == 'standard'
        assert d({}, {}, 'unclear') == 'unknown'          # nothing known → say so
        assert d({'is_impacted': False}, {}, 'unclear') == 'standard'


# --- extract ------------------------------------------------------------------


def _verified_profile():
    return {
        'metadata': {'official_name': 'UIUC', 'verification_status': 'verified'},
        'academic_structure': {
            'structure_type': 'Decentralized colleges',
            'colleges': [{
                'name': 'Grainger College of Engineering',
                'admissions_model': 'Direct Admit',
                'is_restricted_or_capped': True,
                'majors': [
                    {'name': 'Computer Science', 'degree_type': 'BS',
                     'is_impacted': False, 'direct_admit_only': True,
                     'internal_transfer_allowed': False,
                     'admissions_pathway': 'Direct admit only; on-campus transfer '
                                           'into Grainger CS not permitted'},
                    {'name': 'Civil Engineering', 'degree_type': 'BS',
                     'is_impacted': False,
                     'admissions_pathway': 'Direct admit',
                     'internal_transfer_gpa': 3.0},
                ]}]},
        'application_strategy': {'major_selection_tactics': ['Use CS+X as a backup'],
                                 'alternate_major_strategy': 'Pick a second choice in LAS'},
    }


def _legacy_profile():
    return {
        'metadata': {'official_name': 'UCI'},
        'academic_structure': {'colleges': [{
            'name': 'Donald Bren School of ICS',
            'majors': [
                {'name': 'Computer Science', 'is_impacted': True,
                 'acceptance_rate': 21.3, 'average_gpa_admitted': 4.1,
                 'admissions_pathway': 'Direct Admit',
                 'minimum_gpa_to_declare': 3.0},
                {'name': 'Informatics', 'admissions_pathway': None},
            ]}]},
        'application_strategy': {},
    }


class TestExtractMajorFacts:
    def test_verified_profile_basis_and_risk(self, kb):
        facts = kb.major_facts.extract_major_facts(_verified_profile())
        assert facts['verification_status'] == 'verified'
        assert facts['richness_tier'] == 1
        cs, civil = facts['colleges'][0]['majors']
        assert cs['entry_path']['value'] == 'direct_admit'
        assert cs['entry_path']['basis'] == 'kb_verified'
        assert cs['entry_risk'] == 'capped_door'
        assert cs['is_impacted']['value'] is False
        assert 'does NOT mean' in cs['is_impacted']['note']   # the UIUC trap
        assert cs['reported_stats'] is None                    # verified data has none
        assert civil['entry_risk'] == 'elevated'               # capped college

    def test_legacy_profile_hedged(self, kb):
        facts = kb.major_facts.extract_major_facts(_legacy_profile())
        assert facts['verification_status'] == 'legacy'
        cs = facts['colleges'][0]['majors'][0]
        assert cs['entry_path']['basis'] == 'kb_reported'
        assert cs['reported_stats']['acceptance_rate'] == 21.3
        assert cs['reported_stats']['basis'] == 'kb_reported'  # ALWAYS hedged
        assert any('not yet' in n for n in facts['data_notes'])
        informatics = facts['colleges'][0]['majors'][1]
        assert informatics['entry_path']['value'] == 'unclear'
        assert informatics['entry_path']['basis'] is None      # nothing to label

    def test_query_and_college_filters(self, kb):
        facts = kb.major_facts.extract_major_facts(_legacy_profile(), query='inform')
        majors = facts['colleges'][0]['majors']
        assert [m['name'] for m in majors] == ['Informatics']
        facts = kb.major_facts.extract_major_facts(_verified_profile(), college='grainger')
        assert len(facts['colleges']) == 1
        facts = kb.major_facts.extract_major_facts(_verified_profile(), college='nursing')
        assert facts['colleges'] == []

    def test_strategy_notes_are_opinion(self, kb):
        facts = kb.major_facts.extract_major_facts(_verified_profile())
        assert facts['strategy_notes']['major_selection_tactics']['basis'] == 'opinion'
        assert facts['strategy_notes']['alternate_major_strategy']['text'] == \
            'Pick a second choice in LAS'

    def test_empty_profile_tier_4(self, kb):
        facts = kb.major_facts.extract_major_facts({})
        assert facts['richness_tier'] == 4
        assert facts['colleges'] == []
        assert any('No majors' in n for n in facts['data_notes'])


class TestMajorsAction:
    def test_end_to_end_through_main(self, kb, make_profile):
        profile = make_profile(academic_structure=_legacy_profile()['academic_structure'])
        kb.main.ingest_university(profile, year=2026)
        result = kb.main.get_university_majors('testu')
        assert result['success'] is True
        assert result['data_year'] == 2026
        assert result['colleges'][0]['majors'][0]['name'] == 'Computer Science'

    def test_query_filter_through_main(self, kb, make_profile):
        profile = make_profile(academic_structure=_legacy_profile()['academic_structure'])
        kb.main.ingest_university(profile, year=2026)
        result = kb.main.get_university_majors('testu', query='informatics')
        assert [m['name'] for c in result['colleges'] for m in c['majors']] == ['Informatics']

    def test_unknown_school(self, kb):
        result = kb.main.get_university_majors('ghost')
        assert result['success'] is False

    def test_year_miss_names_available_years(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university_majors('testu', year=2020)
        assert result['success'] is False
        assert '2026' in result['error']
