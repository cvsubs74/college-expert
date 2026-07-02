"""Global major catalog (#303): normalization, union build, idempotent
re-ingest, and the action=majors-catalog view."""


# --- normalizer ---------------------------------------------------------------


class TestNormalize:
    def test_strips_degree_and_program_suffixes(self, kb):
        n = kb.major_catalog.normalize_major
        assert n('Computer Science, B.S.') == 'computer science'
        assert n('Biology (B.A.)') == 'biology'
        assert n('Data Science Program') == 'data science'
        assert n('Nursing Track') == 'nursing'

    def test_expands_abbreviations(self, kb):
        n = kb.major_catalog.normalize_major
        assert n('CS') == 'computer science'
        assert n('Poli Sci') == 'political science'
        assert n('EE') == 'electrical engineering'

    def test_unusable_input_is_empty(self, kb):
        n = kb.major_catalog.normalize_major
        assert n('') == '' and n(None) == '' and n('   ') == ''


# --- build / add_school -------------------------------------------------------


def _prof(*colleges):
    return {'academic_structure': {'colleges': [
        {'name': cn, 'majors': [{'name': m} for m in majors]} for cn, majors in colleges]}}


class TestBuildAndUnion:
    def test_union_across_schools_with_dedup(self, kb):
        pairs = [
            ('a', _prof(('Eng', ['Computer Science', 'Mechanical Engineering']))),
            ('b', _prof(('SEAS', ['CS', 'Biology']))),   # 'CS' normalizes to computer science
        ]
        cat = kb.major_catalog.build_catalog(pairs)
        view = kb.major_catalog.catalog_view(cat)
        by = {r['normalized']: r['offered_count'] for r in view['majors']}
        assert by['computer science'] == 2          # a + b, deduped across spellings
        assert by['mechanical engineering'] == 1
        assert by['biology'] == 1
        assert view['university_count'] == 2

    def test_display_prefers_shortest_raw(self, kb):
        cat = kb.major_catalog.build_catalog([
            ('a', _prof(('X', ['Computer Science, B.S.']))),
            ('b', _prof(('Y', ['Computer Science']))),
        ])
        row = kb.major_catalog.catalog_view(cat)['majors'][0]
        assert row['name'] == 'Computer Science'    # shorter representative wins

    def test_reingest_same_school_is_idempotent(self, kb):
        cat = kb.major_catalog.add_school(None, 'a', _prof(('E', ['Computer Science'])))
        cat = kb.major_catalog.add_school(cat, 'b', _prof(('E', ['Computer Science'])))
        again = kb.major_catalog.add_school(cat, 'a', _prof(('E', ['Computer Science'])))
        by = {r['normalized']: r['offered_count'] for r in kb.major_catalog.catalog_view(again)['majors']}
        assert by['computer science'] == 2          # not 3 — 'a' re-added, not double-counted
        assert again['university_count'] == 2

    def test_reingest_with_changed_majors_drops_stale(self, kb):
        cat = kb.major_catalog.add_school(None, 'a', _prof(('E', ['Computer Science', 'Physics'])))
        # School 'a' re-collected: dropped Physics, added Statistics.
        cat = kb.major_catalog.add_school(cat, 'a', _prof(('E', ['Computer Science', 'Statistics'])))
        by = {r['normalized']: r['offered_count'] for r in kb.major_catalog.catalog_view(cat)['majors']}
        assert 'physics' not in by                  # stale contribution removed
        assert by['computer science'] == 1 and by['statistics'] == 1


class TestCatalogView:
    def _cat(self, kb):
        return kb.major_catalog.build_catalog([
            ('a', _prof(('E', ['Computer Science', 'Nursing']))),
            ('b', _prof(('E', ['Computer Science', 'Underwater Basket Weaving']))),
            ('c', _prof(('E', ['Computer Science']))),
        ])

    def test_sorted_by_offered_count_desc(self, kb):
        rows = kb.major_catalog.catalog_view(self._cat(kb))['majors']
        assert rows[0]['normalized'] == 'computer science' and rows[0]['offered_count'] == 3

    def test_min_schools_filter(self, kb):
        rows = kb.major_catalog.catalog_view(self._cat(kb), min_schools=2)['majors']
        assert [r['normalized'] for r in rows] == ['computer science']

    def test_query_filter_and_limit(self, kb):
        v = kb.major_catalog.catalog_view(self._cat(kb), query='nursing')
        assert [r['normalized'] for r in v['majors']] == ['nursing']
        assert v['total'] == 1
        limited = kb.major_catalog.catalog_view(self._cat(kb), limit=1)
        assert len(limited['majors']) == 1 and limited['total'] == 3   # total is pre-limit

    def test_never_exposes_raw_id_lists(self, kb):
        rows = kb.major_catalog.catalog_view(self._cat(kb))['majors']
        assert all(set(r.keys()) == {'name', 'normalized', 'offered_count'} for r in rows)


# --- endpoint + ingest hook (through main.py) ---------------------------------


class TestCatalogEndpointAndHook:
    def test_ingest_populates_catalog_then_endpoint_reads_it(self, kb, make_profile):
        profile = make_profile(academic_structure={'colleges': [
            {'name': 'E', 'majors': [{'name': 'Computer Science'}, {'name': 'Biology'}]}]})
        kb.main.ingest_university(profile, year=2026)
        result = kb.main.get_majors_catalog()
        assert result['success'] is True
        names = {r['normalized'] for r in result['majors']}
        assert {'computer science', 'biology'} <= names
        assert result['university_count'] == 1

    def test_endpoint_query_and_min_schools(self, kb, make_profile):
        kb.main.ingest_university(
            make_profile(uid='u1', academic_structure={'colleges': [
                {'name': 'E', 'majors': [{'name': 'Computer Science'}]}]}), year=2026)
        kb.main.ingest_university(
            make_profile(uid='u2', academic_structure={'colleges': [
                {'name': 'E', 'majors': [{'name': 'Computer Science'}, {'name': 'Art History'}]}]}), year=2026)
        assert kb.main.get_majors_catalog(min_schools=2)['majors'][0]['offered_count'] == 2
        q = kb.main.get_majors_catalog(query='art')
        assert [r['normalized'] for r in q['majors']] == ['art history']

    def test_empty_catalog_is_clean(self, kb):
        result = kb.main.get_majors_catalog()
        assert result['success'] is True and result['majors'] == [] and result['total'] == 0

    def test_ingest_still_succeeds_if_catalog_update_raises(self, kb, make_profile, monkeypatch):
        # A catalog failure must NEVER fail the ingest.
        monkeypatch.setattr(kb.db, 'update_major_catalog_for_school',
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom')))
        # get_db returns the same db the fixture patched; the hook swallows via db method,
        # but here we force the method itself to raise → ingest must still report success
        # because the hook is best-effort. If it propagates, this test fails loudly.
        try:
            result = kb.main.ingest_university(make_profile(), year=2026)
        except RuntimeError:
            raise AssertionError("catalog failure propagated and broke the ingest")
        assert result['success'] is True
