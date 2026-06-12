"""
End-to-end (in-process) tests of the ingest → store → read path in main.py,
exercising the same functions the HTTP routes dispatch to.
"""


class TestIngestUniversity:
    def test_ingest_returns_year_and_promotion(self, kb, make_profile):
        result = kb.main.ingest_university(make_profile(), year=2026)
        assert result['success'] is True
        assert result['year'] == 2026
        assert result['promoted_to_current'] is True
        assert result['available_years'] == [2026]
        assert result['validation_warnings'] == []

    def test_ingest_defaults_year_to_current_cycle(self, kb, make_profile):
        result = kb.main.ingest_university(make_profile())
        assert result['success'] is True
        assert result['year'] == kb.versioning.current_cycle_year()

    def test_ingest_rejects_invalid_profile(self, kb):
        result = kb.main.ingest_university({'metadata': {}}, year=2026)
        assert result['success'] is False
        assert result['validation_errors']
        # nothing written
        assert kb.db.get_university('testu') is None

    def test_ingest_surfaces_warnings_but_saves(self, kb, make_profile):
        profile = make_profile(deadlines=[{'plan_type': 'RD', 'date': 'Rolling'}])
        result = kb.main.ingest_university(profile, year=2026)
        assert result['success'] is True
        assert any('Rolling' in w for w in result['validation_warnings'])
        assert kb.db.get_university('testu') is not None

    def test_yearly_refresh_preserves_prior_year(self, kb, make_profile):
        """The headline use case: refresh the KB every cycle without
        destroying last cycle's data."""
        p2025 = make_profile(deadlines=[{'plan_type': 'RD', 'date': '2026-01-05'}])
        p2026 = make_profile(deadlines=[{'plan_type': 'RD', 'date': '2027-01-05'}])
        kb.main.ingest_university(p2025, year=2025)
        kb.main.ingest_university(p2026, year=2026)

        current = kb.main.get_university('testu')
        assert current['success'] is True
        assert current['university']['data_year'] == 2026
        assert current['university']['available_years'] == [2025, 2026]
        assert (current['university']['profile']['application_process']
                ['application_deadlines'][0]['date']) == '2027-01-05'

        archived = kb.main.get_university('testu', year=2025)
        assert archived['success'] is True
        assert archived['university']['data_year'] == 2025
        assert (archived['university']['profile']['application_process']
                ['application_deadlines'][0]['date']) == '2026-01-05'


class TestGetUniversity:
    def test_response_shape_is_backward_compatible(self, kb, make_profile):
        """counselor_agent reads response['university']['profile'];
        the hybrid agent and frontend read the same envelope. Versioning
        must not move or rename any pre-existing key."""
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu')

        assert result['success'] is True
        uni = result['university']
        for legacy_key in ('university_id', 'official_name', 'location',
                           'acceptance_rate', 'market_position', 'profile',
                           'indexed_at', 'last_updated'):
            assert legacy_key in uni, f"legacy consumer key {legacy_key} missing"
        assert uni['profile']['_id'] == 'testu'

    def test_missing_university(self, kb):
        result = kb.main.get_university('ghost')
        assert result['success'] is False

    def test_missing_year_names_the_year(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.get_university('testu', year=2020)
        assert result['success'] is False
        assert '2020' in result['error']


class TestListVersionsEndpoint:
    def test_lists_versions(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2025)
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.list_university_versions('testu')
        assert result['success'] is True
        assert [v['year'] for v in result['versions']] == [2026, 2025]

    def test_unknown_university(self, kb):
        result = kb.main.list_university_versions('ghost')
        assert result['success'] is False


class TestDeleteEndpoint:
    def test_delete_single_year(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2025)
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.delete_university('testu', year=2025)
        assert result['success'] is True
        assert kb.main.get_university('testu', year=2025)['success'] is False
        assert kb.main.get_university('testu')['success'] is True

    def test_delete_all(self, kb, make_profile):
        kb.main.ingest_university(make_profile(), year=2025)
        kb.main.ingest_university(make_profile(), year=2026)
        result = kb.main.delete_university('testu')
        assert result['success'] is True
        assert kb.main.get_university('testu')['success'] is False


class TestSearchStillWorksOnCurrentDocs:
    def test_search_sees_only_promoted_data(self, kb, make_profile):
        kb.main.ingest_university(
            make_profile(uid='mit', name='Massachusetts Institute of Technology'),
            year=2026,
        )
        kb.main.ingest_university(
            make_profile(uid='stanford_university', name='Stanford University'),
            year=2026,
        )
        result = kb.main.search_universities('stanford', limit=5)
        assert result['success'] is True
        ids = [r['university_id'] for r in result['results']]
        assert 'stanford_university' in ids
        # versions subcollection docs must NOT leak into search results
        assert all(not str(i).isdigit() for i in ids)
