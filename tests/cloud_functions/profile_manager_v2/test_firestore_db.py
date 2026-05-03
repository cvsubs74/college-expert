"""
Unit tests for cloud_functions/profile_manager_v2/firestore_db.py.

Focuses on update_notes — the critical write path for the consolidated
Roadmap notes affordance — and the NOTES_COLLECTIONS whitelist that
prevents arbitrary writes via the /update-notes HTTP endpoint.

The Firestore client is stubbed in conftest.py; each test injects its
own fake `db.db` via FirestoreDB.__new__() so we don't run __init__
(which would build a real Firestore client).
"""

import pytest

from firestore_db import FirestoreDB, NOTES_COLLECTIONS


# ---------------------------------------------------------------------------
# Whitelist contents — must match what the /update-notes dispatcher checks.
# ---------------------------------------------------------------------------

class TestNotesCollections:
    def test_contains_all_user_owned_notes_bearing_collections(self):
        # The list is small and stable; lock it in literally so accidental
        # additions/removals show up as test failures.
        assert NOTES_COLLECTIONS == frozenset({
            'roadmap_tasks',
            'essay_tracker',
            'scholarship_tracker',
            'college_list',
            'aid_packages',
        })

    def test_is_immutable(self):
        # frozenset → can't be mutated. Belt-and-suspenders against drift.
        assert isinstance(NOTES_COLLECTIONS, frozenset)


# ---------------------------------------------------------------------------
# FirestoreDB.update_notes — the helper backing /update-notes.
# ---------------------------------------------------------------------------

class _FinalDoc:
    """Stub for a Firestore DocumentReference. Tracks update() calls."""
    def __init__(self, exists, error_on_get=False):
        self._exists = exists
        self._error_on_get = error_on_get
        self.update_call = None                                # records the dict passed

    def get(self):
        if self._error_on_get:
            raise RuntimeError('firestore down')

        class _Snap:
            def __init__(self, exists):
                self.exists = exists
        return _Snap(self._exists)

    def update(self, data):
        self.update_call = data


class _Coll:
    def __init__(self, final_doc):
        self._doc = final_doc

    def document(self, _id):
        return self._doc


class _UserDoc:
    def __init__(self, final_doc):
        self._final = final_doc

    def collection(self, _name):
        return _Coll(self._final)


class _Root:
    """Root client stub. .collection() → .document() → .collection() → .document()."""
    def __init__(self, final_doc):
        self._final = final_doc

    def collection(self, _name):
        class _UsersColl:
            def __init__(self, final): self._final = final
            def document(self, _uid): return _UserDoc(self._final)
        return _UsersColl(self._final)


def _make_db(exists, error_on_get=False):
    """Build a FirestoreDB without invoking __init__ (no real client).
    Returns (db, doc) so tests can assert on the doc's recorded calls."""
    db = FirestoreDB.__new__(FirestoreDB)
    final = _FinalDoc(exists=exists, error_on_get=error_on_get)
    db.db = _Root(final)
    return db, final


class TestUpdateNotesSuccess:
    def test_writes_notes_and_updated_at(self):
        db, doc = _make_db(exists=True)
        result = db.update_notes('u@x.com', 'roadmap_tasks', 't1', 'hello world')

        assert result['ok'] is True
        assert 'updated_at' in result
        assert doc.update_call == {
            'notes': 'hello world',
            'updated_at': result['updated_at'],
        }

    def test_empty_string_clears_notes(self):
        # Empty string is a valid value — clears existing notes.
        db, doc = _make_db(exists=True)
        result = db.update_notes('u@x.com', 'essay_tracker', 'e1', '')

        assert result['ok'] is True
        assert doc.update_call.get('notes') == ''

    @pytest.mark.parametrize('collection', sorted(NOTES_COLLECTIONS))
    def test_works_for_each_whitelisted_collection(self, collection):
        # Sanity-check that each whitelisted collection is reachable. The
        # stubbed Firestore doesn't differentiate by collection name; this
        # just exercises the code path so we'd catch a future refactor that
        # accidentally hardcodes a single collection.
        db, _ = _make_db(exists=True)
        result = db.update_notes('u@x.com', collection, 'item_1', 'note text')
        assert result['ok'] is True


class TestUpdateNotesNotFound:
    def test_missing_doc_returns_not_found_reason(self):
        db, doc = _make_db(exists=False)
        result = db.update_notes('u@x.com', 'roadmap_tasks', 'never-existed', 'x')
        assert result == {'ok': False, 'reason': 'not_found'}
        # Importantly, no write was attempted.
        assert doc.update_call is None


class TestUpdateNotesError:
    def test_firestore_exception_returns_error_reason(self):
        db, _ = _make_db(exists=True, error_on_get=True)
        result = db.update_notes('u@x.com', 'roadmap_tasks', 't1', 'x')
        assert result['ok'] is False
        assert result['reason'] == 'error'
        assert 'firestore down' in result['message']
