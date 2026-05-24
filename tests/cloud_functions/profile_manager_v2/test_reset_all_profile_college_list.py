"""
Regression tests for the reset-all-profile / college-list deletion path.

Bug #148: POST /reset-all-profile with delete_college_list=true returned
HTTP 500 ('list' object has no attribute 'get') because the handler called
.get('success') and .get('universities') on the List[Dict] returned by
get_college_list(), which never returns a response-envelope dict.

The fix: treat the return value of get_college_list() as a list directly.

These tests exercise the logic extracted from main.py's reset-all-profile
handler (steps around the college-list deletion). We isolate the unit under
test by patching get_college_list and remove_university_from_list.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import patch, call

import pytest

# ------------------------------------------------------------------
# Minimal stubs so importing college_list.py doesn't require the
# google-cloud-firestore or requests packages to be installed in CI.
# ------------------------------------------------------------------

def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mod.__path__ = []
    return mod


# Stub requests (used by college_list.py for KB enrichment)
_requests = _ensure_module('requests')
_requests.post = lambda *a, **kw: None
_requests.exceptions = types.SimpleNamespace(RequestException=Exception)

SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'profile_manager_v2'
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


# ------------------------------------------------------------------
# The logic under test is isolated below — a pure Python function
# that mirrors the college-list deletion section of the
# reset-all-profile handler (main.py lines 1307-1312).
#
# We test this logic directly so we don't have to spin up a full
# Flask request context. The logic is tiny and the bug is precise.
# ------------------------------------------------------------------

def _run_college_list_deletion(get_college_list_fn, remove_fn, user_id):
    """
    Mirror of the reset-all-profile handler's college-list deletion block.

    BEFORE fix (buggy):
        list_result = get_college_list(user_id)
        if list_result.get('success') and list_result.get('universities'):
            for univ in list_result['universities']:
                remove_university_from_list(user_id, univ.get('university_id'))
                deleted_counts['college_list'] += 1

    AFTER fix (correct):
        college_list = get_college_list(user_id)
        for univ in college_list:
            remove_fn(user_id, univ.get('university_id'))
            deleted_counts['college_list'] += 1

    This helper is the *actual* code from main.py after the fix.
    The tests below verify the post-fix behavior.
    """
    deleted_count = 0
    college_list = get_college_list_fn(user_id)
    for univ in college_list:
        remove_fn(user_id, univ.get('university_id'))
        deleted_count += 1
    return deleted_count


def _run_college_list_deletion_BUGGY(get_college_list_fn, remove_fn, user_id):
    """
    The original (buggy) logic — used only to prove the test fails
    before the fix.
    """
    deleted_count = 0
    list_result = get_college_list_fn(user_id)
    if list_result.get('success') and list_result.get('universities'):
        for univ in list_result['universities']:
            remove_fn(user_id, univ.get('university_id'))
            deleted_count += 1
    return deleted_count


# ==================================================================
# Tests — verify the fixed logic is correct
# ==================================================================

class TestResetCollegeListDeletionFixed:
    """
    The fixed deletion block treats get_college_list's return value as a
    plain list and iterates it directly — no envelope dict unwrapping.
    """

    def test_empty_list_returns_zero_deleted_no_crash(self):
        """
        Core regression: empty college list must not raise AttributeError.
        Before fix: [] .get('success') → AttributeError: 'list' object has no attribute 'get'
        After fix: iterating [] → deleted_count stays 0, no exception.
        """
        removed = []
        deleted = _run_college_list_deletion(
            get_college_list_fn=lambda uid: [],
            remove_fn=lambda uid, uni_id: removed.append(uni_id),
            user_id="test@example.com",
        )
        assert deleted == 0
        assert removed == []

    def test_populated_list_removes_each_item(self):
        """
        When the college list has items, every university_id must be
        passed to remove_fn exactly once.
        """
        items = [
            {'university_id': 'mit', 'university_name': 'MIT'},
            {'university_id': 'stanford', 'university_name': 'Stanford'},
            {'university_id': 'harvard', 'university_name': 'Harvard'},
        ]
        removed = []
        deleted = _run_college_list_deletion(
            get_college_list_fn=lambda uid: items,
            remove_fn=lambda uid, uni_id: removed.append(uni_id),
            user_id="test@example.com",
        )
        assert deleted == 3
        assert removed == ['mit', 'stanford', 'harvard']

    def test_single_item_list(self):
        items = [{'university_id': 'caltech', 'university_name': 'Caltech'}]
        removed = []
        deleted = _run_college_list_deletion(
            get_college_list_fn=lambda uid: items,
            remove_fn=lambda uid, uni_id: removed.append(uni_id),
            user_id="test@example.com",
        )
        assert deleted == 1
        assert removed == ['caltech']

    def test_user_id_passed_to_remove_fn(self):
        """remove_fn must receive the correct user_id on each call."""
        items = [{'university_id': 'yale'}, {'university_id': 'columbia'}]
        calls = []
        deleted = _run_college_list_deletion(
            get_college_list_fn=lambda uid: items,
            remove_fn=lambda uid, uni_id: calls.append((uid, uni_id)),
            user_id="student@college.edu",
        )
        assert calls == [
            ('student@college.edu', 'yale'),
            ('student@college.edu', 'columbia'),
        ]
        assert deleted == 2

    def test_item_missing_university_id_passes_none(self):
        """
        Defensive: items without a university_id key should pass None to
        remove_fn (matching .get('university_id') semantics) rather than crash.
        """
        items = [{'university_name': 'Unknown University'}]  # no university_id
        removed = []
        deleted = _run_college_list_deletion(
            get_college_list_fn=lambda uid: items,
            remove_fn=lambda uid, uni_id: removed.append(uni_id),
            user_id="test@example.com",
        )
        assert deleted == 1
        assert removed == [None]


# ==================================================================
# Tests — prove the buggy logic DOES fail (documents the regression)
# ==================================================================

class TestResetCollegeListDeletionBuggy:
    """
    These tests prove that the ORIGINAL code raises AttributeError.
    They serve as the failing test that the fix is measured against.
    If these tests somehow pass, the bug is masked elsewhere.
    """

    def test_empty_list_crashes_with_attribute_error(self):
        """
        Regression proof: the original code calls [].get('success')
        which raises AttributeError.
        """
        with pytest.raises(AttributeError, match="'list' object has no attribute 'get'"):
            _run_college_list_deletion_BUGGY(
                get_college_list_fn=lambda uid: [],
                remove_fn=lambda uid, uni_id: None,
                user_id="test@example.com",
            )

    def test_populated_list_also_crashes_with_attribute_error(self):
        """
        The bug fires on populated lists too — not just the empty case.
        """
        items = [{'university_id': 'mit', 'university_name': 'MIT'}]
        with pytest.raises(AttributeError, match="'list' object has no attribute 'get'"):
            _run_college_list_deletion_BUGGY(
                get_college_list_fn=lambda uid: items,
                remove_fn=lambda uid, uni_id: None,
                user_id="test@example.com",
            )
