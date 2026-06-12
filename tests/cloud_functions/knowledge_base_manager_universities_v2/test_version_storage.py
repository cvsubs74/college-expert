"""
Version-aware Firestore layer (firestore_db.py) against the in-memory fake.

Covers the ADR 0002 storage rules: snapshot-per-year, promotion only for
the newest year, idempotent same-year refresh, version listing, and the
delete/promote semantics.
"""


def _doc(uid='testu', name='Test University', year_marker=None):
    d = {
        'university_id': uid,
        'official_name': name,
        'location': {'city': 'Testville', 'state': 'CA', 'type': 'Private'},
        'acceptance_rate': 25.0,
        'profile': {'_id': uid},
        'indexed_at': '2026-06-12T00:00:00+00:00',
    }
    if year_marker:
        # distinguishes per-year content in assertions
        d['summary'] = f'data from {year_marker}'
    return d


class TestSaveUniversity:
    def test_first_ingest_writes_version_and_promotes(self, db):
        result = db.save_university('testu', _doc(), year=2026)
        assert result['saved'] is True
        assert result['promoted'] is True
        assert result['available_years'] == [2026]

        main = db.get_university('testu')
        assert main['data_year'] == 2026
        assert main['available_years'] == [2026]

        snapshot = db.get_university('testu', year=2026)
        assert snapshot['data_year'] == 2026
        assert snapshot['official_name'] == 'Test University'

    def test_newer_year_promotes_main_doc(self, db):
        db.save_university('testu', _doc(year_marker='2025'), year=2025)
        result = db.save_university('testu', _doc(year_marker='2026'), year=2026)

        assert result['promoted'] is True
        main = db.get_university('testu')
        assert main['data_year'] == 2026
        assert main['summary'] == 'data from 2026'
        assert main['available_years'] == [2025, 2026]
        # 2025 snapshot is intact
        assert db.get_university('testu', year=2025)['summary'] == 'data from 2025'

    def test_older_year_does_not_clobber_current(self, db):
        db.save_university('testu', _doc(year_marker='2026'), year=2026)
        result = db.save_university('testu', _doc(year_marker='2024'), year=2024)

        assert result['saved'] is True
        assert result['promoted'] is False
        main = db.get_university('testu')
        assert main['data_year'] == 2026
        assert main['summary'] == 'data from 2026'
        # but the historical snapshot exists and is listed
        assert main['available_years'] == [2024, 2026]
        assert db.get_university('testu', year=2024)['summary'] == 'data from 2024'

    def test_same_year_reingest_is_idempotent_refresh(self, db):
        db.save_university('testu', _doc(year_marker='first run'), year=2026)
        result = db.save_university('testu', _doc(year_marker='second run'), year=2026)

        assert result['promoted'] is True
        assert result['available_years'] == [2026]
        assert db.get_university('testu')['summary'] == 'data from second run'
        assert db.get_university('testu', year=2026)['summary'] == 'data from second run'

    def test_legacy_main_doc_without_data_year_is_taken_over(self, db):
        # Simulate a pre-versioning doc written by the old save path.
        db.collection.document('testu').set(_doc(year_marker='legacy'))
        result = db.save_university('testu', _doc(year_marker='2026'), year=2026)

        assert result['promoted'] is True
        main = db.get_university('testu')
        assert main['data_year'] == 2026
        assert main['summary'] == 'data from 2026'

    def test_legacy_main_doc_is_auto_archived_before_takeover(self, db):
        """A pre-versioning doc must not be lost on the first versioned
        ingest — it gets snapshotted under year-1 (vintage unknown)."""
        db.collection.document('testu').set(_doc(year_marker='legacy'))
        result = db.save_university('testu', _doc(year_marker='2026'), year=2026)

        legacy = db.get_university('testu', year=2025)
        assert legacy is not None
        assert legacy['summary'] == 'data from legacy'
        assert legacy['data_year'] == 2025
        assert sorted(result['available_years']) == [2025, 2026]

    def test_auto_archive_never_overwrites_existing_snapshot(self, db):
        """If versions/{year-1} already exists (operator archived properly),
        the legacy doc must not clobber it."""
        db.save_university('testu', _doc(year_marker='real 2025'), year=2025)
        # Simulate the main doc losing data_year (legacy state).
        main_raw = db.collection.document('testu').get().to_dict()
        main_raw.pop('data_year')
        main_raw['summary'] = 'data from drifted legacy'
        db.collection.document('testu').set(main_raw)

        db.save_university('testu', _doc(year_marker='2026'), year=2026)
        assert db.get_university('testu', year=2025)['summary'] == 'data from real 2025'


class TestGetUniversity:
    def test_get_missing_returns_none(self, db):
        assert db.get_university('ghost') is None

    def test_get_missing_year_returns_none(self, db):
        db.save_university('testu', _doc(), year=2026)
        assert db.get_university('testu', year=2019) is None

    def test_university_id_is_set_on_both_paths(self, db):
        db.save_university('testu', _doc(), year=2026)
        assert db.get_university('testu')['university_id'] == 'testu'
        assert db.get_university('testu', year=2026)['university_id'] == 'testu'


class TestListVersions:
    def test_lists_years_newest_first(self, db):
        db.save_university('testu', _doc(), year=2024)
        db.save_university('testu', _doc(), year=2026)
        db.save_university('testu', _doc(), year=2025)

        versions = db.list_university_versions('testu')
        assert [v['year'] for v in versions] == [2026, 2025, 2024]
        assert all(v['official_name'] == 'Test University' for v in versions)

    def test_empty_for_unknown_university(self, db):
        assert db.list_university_versions('ghost') == []


class TestDeleteUniversity:
    def test_full_delete_removes_main_and_all_versions(self, db):
        db.save_university('testu', _doc(), year=2025)
        db.save_university('testu', _doc(), year=2026)

        assert db.delete_university('testu') is True
        assert db.get_university('testu') is None
        assert db.get_university('testu', year=2025) is None
        assert db.get_university('testu', year=2026) is None
        assert db.list_university_versions('testu') == []

    def test_delete_noncurrent_year_keeps_main(self, db):
        db.save_university('testu', _doc(year_marker='2025'), year=2025)
        db.save_university('testu', _doc(year_marker='2026'), year=2026)

        assert db.delete_university('testu', year=2025) is True
        main = db.get_university('testu')
        assert main['data_year'] == 2026
        assert main['available_years'] == [2026]
        assert db.get_university('testu', year=2025) is None

    def test_delete_current_year_promotes_latest_remaining(self, db):
        db.save_university('testu', _doc(year_marker='2025'), year=2025)
        db.save_university('testu', _doc(year_marker='2026'), year=2026)

        assert db.delete_university('testu', year=2026) is True
        main = db.get_university('testu')
        assert main['data_year'] == 2025
        assert main['summary'] == 'data from 2025'
        assert main['available_years'] == [2025]

    def test_delete_last_version_removes_main_doc(self, db):
        db.save_university('testu', _doc(), year=2026)

        assert db.delete_university('testu', year=2026) is True
        assert db.get_university('testu') is None
        assert db.list_university_versions('testu') == []
