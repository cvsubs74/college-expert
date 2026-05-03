"""
Unit tests for FirestoreDB.clear_test_data — the helper the qa_agent
calls between scenarios to wipe the test user's subcollections.

The endpoint-level email + token gates live in main.py and are
orthogonal to this helper. Here we just verify the helper iterates
every subcollection and returns the count of deleted docs.
"""

import pytest
from firestore_db import FirestoreDB


# ---- Stub Firestore plumbing -----------------------------------------------


class _DocRef:
    def __init__(self):
        self.deleted = False

    def delete(self):
        self.deleted = True


class _DocSnapshot:
    def __init__(self, doc_id):
        self.id = doc_id
        self.reference = _DocRef()


class _Subcoll:
    def __init__(self, doc_ids):
        self._docs = [_DocSnapshot(d) for d in doc_ids]

    def stream(self):
        return iter(self._docs)


class _UserDoc:
    """Acts as `users/{email}`. Has a fixed map of subcollection → docs."""

    def __init__(self, sub_map):
        self._sub_map = sub_map
        self.calls = []  # which subcollections were asked for

    def collection(self, name):
        self.calls.append(name)
        return _Subcoll(self._sub_map.get(name, []))


class _Root:
    def __init__(self, user_doc):
        self._user_doc = user_doc

    def collection(self, _name):
        # 'users'
        class _UsersColl:
            def __init__(self, user_doc): self._user = user_doc
            def document(self, _id): return self._user
        return _UsersColl(self._user_doc)


def _make_db(sub_map):
    db = FirestoreDB.__new__(FirestoreDB)
    user_doc = _UserDoc(sub_map)
    db.db = _Root(user_doc)
    return db, user_doc


# ---- Tests ------------------------------------------------------------------


class TestClearTestData:
    def test_deletes_documents_in_each_subcollection(self):
        sub_map = {
            'profile':              ['data'],
            'roadmap_tasks':        ['t1', 't2', 't3'],
            'essay_tracker':        ['e1', 'e2'],
            'scholarship_tracker':  [],
            'college_list':         ['mit', 'stanford'],
            'aid_packages':         [],
            'tasks':                [],
        }
        db, user_doc = _make_db(sub_map)

        result = db.clear_test_data('duser8531@gmail.com')

        assert result['ok'] is True
        deleted = result['deleted']
        # Empty collections should NOT be in the deleted map (we only
        # report what was actually wiped).
        assert deleted == {
            'profile': 1,
            'roadmap_tasks': 3,
            'essay_tracker': 2,
            'college_list': 2,
        }

    def test_iterates_every_known_subcollection(self):
        """Each known subcollection should be enumerated even if empty —
        otherwise a future doc would slip through."""
        db, user_doc = _make_db({})
        db.clear_test_data('duser8531@gmail.com')
        # The expected enumeration set; if a new collection is added to
        # the helper, update this test consciously.
        expected = {
            'profile', 'roadmap_tasks', 'essay_tracker',
            'scholarship_tracker', 'college_list', 'aid_packages', 'tasks',
        }
        assert set(user_doc.calls) == expected

    def test_handles_empty_user_returns_ok(self):
        db, _ = _make_db({})
        result = db.clear_test_data('duser8531@gmail.com')
        assert result == {'ok': True, 'deleted': {}}

    def test_returns_error_on_exception(self):
        # Simulate a broken Firestore client.
        class _BrokenRoot:
            def collection(self, *_a):
                raise RuntimeError('firestore exploded')

        db = FirestoreDB.__new__(FirestoreDB)
        db.db = _BrokenRoot()
        result = db.clear_test_data('duser8531@gmail.com')
        assert result['ok'] is False
        assert result['reason'] == 'error'
        assert 'firestore exploded' in result['message']
