"""
Unit tests for the Research Notebook data layer in firestore_db.py
(save_research / get_research / get_research_list / delete_research).

The Firestore client is stubbed in conftest.py; here we inject a small
in-memory fake `db.db` (one user's `research` subcollection) so we can
exercise create → list → filter → get → update-merge → delete end to end.
"""

import pytest

from firestore_db import FirestoreDB


# --- in-memory fake Firestore (users/{uid}/research/{id}) --------------------

class _Snap:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, store, doc_id):
        self._store = store
        self._id = doc_id

    def get(self):
        return _Snap(self._id, self._store.get(self._id))

    def set(self, data, merge=False):
        if merge and self._id in self._store:
            self._store[self._id] = {**self._store[self._id], **data}
        else:
            self._store[self._id] = dict(data)

    def delete(self):
        self._store.pop(self._id, None)


class _CollRef:
    def __init__(self, store):
        self._store = store

    def document(self, doc_id):
        return _DocRef(self._store, doc_id)

    def stream(self):
        return [_Snap(k, v) for k, v in self._store.items()]


class _Root:
    """.collection('users').document(uid).collection('research') → _CollRef."""
    def __init__(self, store):
        self._store = store

    def collection(self, _name):
        store = self._store

        class _Users:
            def document(self, _uid):
                class _UserDoc:
                    def collection(self, name):
                        assert name == 'research'
                        return _CollRef(store)
                return _UserDoc()
        return _Users()


def _make_db():
    db = FirestoreDB.__new__(FirestoreDB)
    db.db = _Root({})
    return db


U = 'stu@example.com'


def _note(**over):
    base = {
        'title': 'Duke vs UCSD', 'summary': 's', 'body_markdown': '## body',
        'kind': 'comparison', 'university_ids': ['duke_university'], 'tags': ['cs'],
        'source': 'claude_mcp', 'provenance': {'kb_year': 2026},
    }
    base.update(over)
    return base


class TestSaveAndGet:
    def test_save_stamps_timestamps_and_get_returns_with_id(self):
        db = _make_db()
        assert db.save_research(U, 'rsh_1', _note()) is True
        got = db.get_research(U, 'rsh_1')
        assert got['research_id'] == 'rsh_1'
        assert got['title'] == 'Duke vs UCSD'
        assert got['created_at'] and got['updated_at']

    def test_get_missing_returns_none(self):
        assert _make_db().get_research(U, 'nope') is None

    def test_update_merges_and_preserves_created_at(self):
        db = _make_db()
        db.save_research(U, 'rsh_1', _note())
        created = db.get_research(U, 'rsh_1')['created_at']
        # partial update (what /update-research sends)
        assert db.save_research(U, 'rsh_1', {'summary': 'new summary'}) is True
        got = db.get_research(U, 'rsh_1')
        assert got['summary'] == 'new summary'
        assert got['title'] == 'Duke vs UCSD'        # untouched field preserved
        assert got['created_at'] == created          # created_at not reset on update


class TestListAndFilter:
    def test_lists_newest_first(self):
        db = _make_db()
        db.save_research(U, 'a', _note(created_at='2026-01-01T00:00:00'))
        db.save_research(U, 'b', _note(created_at='2026-06-01T00:00:00'))
        ids = [r['research_id'] for r in db.get_research_list(U)]
        assert ids == ['b', 'a']

    def test_filter_by_kind(self):
        db = _make_db()
        db.save_research(U, 'a', _note(kind='comparison'))
        db.save_research(U, 'b', _note(kind='timeline'))
        out = db.get_research_list(U, kind='timeline')
        assert [r['research_id'] for r in out] == ['b']

    def test_filter_by_university(self):
        db = _make_db()
        db.save_research(U, 'a', _note(university_ids=['duke_university']))
        db.save_research(U, 'b', _note(university_ids=['uc_san_diego']))
        out = db.get_research_list(U, university_id='uc_san_diego')
        assert [r['research_id'] for r in out] == ['b']


class TestDelete:
    def test_delete_removes_note(self):
        db = _make_db()
        db.save_research(U, 'rsh_1', _note())
        assert db.delete_research(U, 'rsh_1') is True
        assert db.get_research(U, 'rsh_1') is None
        assert db.get_research_list(U) == []
