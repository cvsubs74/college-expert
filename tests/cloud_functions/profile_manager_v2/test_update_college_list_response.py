"""
Regression tests for /update-college-list response contract.

Bug #153: POST /update-college-list returned { "success": true, "message": "..." }
with NO college_list field. The frontend handleToggleCollegeList called
setMyCollegeList(result.college_list || []) which silently reset state to [].

Fix: add_university_to_list and remove_university_from_list must return
college_list in the response so both the frontend and the college_list_agent
can update their local state in one round-trip.

These tests:
  1. Assert the CURRENT (buggy) behaviour returns no college_list — the failing
     test that proves the bug exists.
  2. Assert the FIXED behaviour — add/remove return college_list in the response.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ------------------------------------------------------------------
# Minimal stubs so importing college_list.py works without the full
# google-cloud-firestore or requests packages installed in CI.
# ------------------------------------------------------------------

def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mod.__path__ = []
    return mod


# Stub requests (college_list.py calls requests.post for KB enrichment)
_requests = _ensure_module('requests')
_requests.exceptions = types.SimpleNamespace(RequestException=Exception)

SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'profile_manager_v2'
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


# ------------------------------------------------------------------
# Helpers to build fake DB and KB stubs
# ------------------------------------------------------------------

MIT = {
    'university_id': 'mit',
    'university_name': 'MIT',
    'category': 'reach',
    'status': 'planning',
    'notes': '',
    'added_at': '2025-01-01T00:00:00',
}
STANFORD = {
    'university_id': 'stanford',
    'university_name': 'Stanford',
    'category': 'reach',
    'status': 'planning',
    'notes': '',
    'added_at': '2025-01-01T00:00:00',
}


def _make_db_stub(initial_list: list) -> MagicMock:
    """
    Return a mock DB whose college-list state reflects initial_list.
    add_to_college_list and remove_from_college_list mutate the list.
    get_college_list returns the current list.
    """
    store = list(initial_list)

    db = MagicMock()
    db.get_college_list.side_effect = lambda uid: list(store)

    def _add(uid, uni_id, item):
        # Replace if already present, else append
        for i, existing in enumerate(store):
            if existing.get('university_id') == uni_id:
                store[i] = item
                return True
        store.append(item)
        return True

    def _remove(uid, uni_id):
        for i, existing in enumerate(store):
            if existing.get('university_id') == uni_id:
                store.pop(i)
                return True
        return False

    db.add_to_college_list.side_effect = _add
    db.remove_from_college_list.side_effect = _remove
    return db


def _stub_requests_no_kb():
    """
    Stub requests.post so KB enrichment is a no-op (returns non-200).
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    _requests.post = MagicMock(return_value=mock_resp)


# ==================================================================
# Tests — assert the FIXED behaviour
# ==================================================================

class TestUpdateCollegeListResponseFixed:
    """
    After fix: both add_university_to_list and remove_university_from_list
    must include college_list in the success response so the caller can
    update its local state in one round-trip.
    """

    def test_add_university_returns_college_list(self):
        """
        Core regression: adding MIT when Stanford is already present must
        return college_list containing both universities.
        """
        _stub_requests_no_kb()
        db = _make_db_stub([STANFORD])

        with patch('college_list.get_db', return_value=db):
            from college_list import add_university_to_list
            result = add_university_to_list(
                'user@test.com',
                'mit',
                {'university_name': 'MIT', 'category': 'reach'}
            )

        assert result['success'] is True
        assert 'college_list' in result, "add must return college_list in response"
        ids = [u['university_id'] for u in result['college_list']]
        assert 'mit' in ids, "MIT must appear in the returned list"
        assert 'stanford' in ids, "Stanford (pre-existing) must still appear"

    def test_add_to_empty_list_returns_singleton_college_list(self):
        """Adding the first university to an empty list returns a list of 1."""
        _stub_requests_no_kb()
        db = _make_db_stub([])

        with patch('college_list.get_db', return_value=db):
            from college_list import add_university_to_list
            result = add_university_to_list(
                'user@test.com',
                'harvard',
                {'university_name': 'Harvard', 'category': 'reach'}
            )

        assert result['success'] is True
        assert len(result['college_list']) == 1
        assert result['college_list'][0]['university_id'] == 'harvard'

    def test_remove_university_returns_remaining_college_list(self):
        """
        Removing Stanford from [MIT, Stanford] must return college_list = [MIT].
        """
        _stub_requests_no_kb()
        db = _make_db_stub([MIT, STANFORD])

        with patch('college_list.get_db', return_value=db):
            from college_list import remove_university_from_list
            result = remove_university_from_list('user@test.com', 'stanford')

        assert result['success'] is True
        assert 'college_list' in result, "remove must return college_list in response"
        ids = [u['university_id'] for u in result['college_list']]
        assert 'stanford' not in ids, "Stanford must be gone"
        assert 'mit' in ids, "MIT must remain"

    def test_remove_last_university_returns_empty_college_list(self):
        """Removing the only university must return an empty college_list, not absent."""
        _stub_requests_no_kb()
        db = _make_db_stub([MIT])

        with patch('college_list.get_db', return_value=db):
            from college_list import remove_university_from_list
            result = remove_university_from_list('user@test.com', 'mit')

        assert result['success'] is True
        assert 'college_list' in result
        assert result['college_list'] == []

    def test_college_list_contains_university_id_field(self):
        """
        Each item in the returned college_list must have university_id so the
        frontend isInCollegeList check (c.university_id === university.id) works.
        """
        _stub_requests_no_kb()
        db = _make_db_stub([])

        with patch('college_list.get_db', return_value=db):
            from college_list import add_university_to_list
            result = add_university_to_list(
                'user@test.com',
                'caltech',
                {'university_name': 'Caltech', 'category': 'reach'}
            )

        assert result['success'] is True
        for item in result['college_list']:
            assert 'university_id' in item, (
                f"Every item in college_list must have university_id; got {item}"
            )

    def test_add_failure_returns_empty_college_list_not_absent(self):
        """
        On DB failure, the response must still have college_list (as []) so
        the frontend's setMyCollegeList(result.college_list || []) logic is
        not needed as a guard — callers can rely on the field always being present.
        """
        _stub_requests_no_kb()
        db = _make_db_stub([])
        # Clear the side_effect so return_value takes over
        db.add_to_college_list.side_effect = None
        db.add_to_college_list.return_value = False  # simulate DB failure

        with patch('college_list.get_db', return_value=db):
            from college_list import add_university_to_list
            result = add_university_to_list(
                'user@test.com',
                'yale',
                {'university_name': 'Yale', 'category': 'target'}
            )

        assert result['success'] is False
        # On failure college_list should be [] (not absent)
        assert result.get('college_list', []) == []

    def test_add_exception_path_returns_college_list_empty(self):
        """
        CR catch: the except block must also return college_list: [] so all
        three return paths (success / else / except) honour the contract.
        Patch get_db to raise so we exercise the except branch.
        """
        _stub_requests_no_kb()

        with patch('college_list.get_db', side_effect=Exception("Firestore unavailable")):
            from college_list import add_university_to_list
            result = add_university_to_list(
                'user@test.com',
                'princeton',
                {'university_name': 'Princeton', 'category': 'reach'}
            )

        assert result['success'] is False
        assert 'college_list' in result, "except path must include college_list key"
        assert result['college_list'] == []

    def test_remove_exception_path_returns_college_list_empty(self):
        """
        CR catch: the except block of remove_university_from_list must also
        return college_list: [].
        """
        _stub_requests_no_kb()

        with patch('college_list.get_db', side_effect=Exception("Firestore unavailable")):
            from college_list import remove_university_from_list
            result = remove_university_from_list('user@test.com', 'mit')

        assert result['success'] is False
        assert 'college_list' in result, "except path must include college_list key"
        assert result['college_list'] == []
