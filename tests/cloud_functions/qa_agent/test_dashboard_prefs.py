"""
Tests for dashboard_prefs.py — admin-configurable dashboard preferences
stored at qa_config/dashboard_prefs.

The only setting today is `recent_n` (size of the most-recent-runs
window the System Health pill summarizes), but the doc shape is
extensible. Defaults: recent_n=20.

Heavy deps (firestore) are stubbed in conftest; these tests exercise
the load/save/validate logic.
"""

from __future__ import annotations

import pytest


# ---- Stub Firestore client used across tests ------------------------------


class _StubSnap:
    def __init__(self, exists, data):
        self.exists = exists
        self._data = data

    def to_dict(self):
        return self._data


class _StubDoc:
    def __init__(self, snap, on_set=None):
        self._snap = snap
        self._on_set = on_set

    def get(self):
        return self._snap

    def set(self, data, merge=False):
        if self._on_set:
            self._on_set(data, merge)


def _db(snap, on_set=None):
    """Return a fake firestore client whose collection().document()
    returns `snap`. Captures `set()` calls via on_set if provided."""
    class _Coll:
        def document(self, _id):
            return _StubDoc(snap, on_set)

    class _DB:
        def collection(self, _name):
            return _Coll()

    return _DB()


# ---- load_prefs -----------------------------------------------------------


class TestLoadPrefs:
    def test_returns_defaults_when_no_doc(self):
        import dashboard_prefs
        result = dashboard_prefs.load_prefs(db=_db(_StubSnap(False, None)))
        assert result["recent_n"] == 20

    def test_returns_stored_value(self):
        import dashboard_prefs
        result = dashboard_prefs.load_prefs(
            db=_db(_StubSnap(True, {"recent_n": 50})),
        )
        assert result["recent_n"] == 50

    def test_falls_back_to_default_when_field_missing(self):
        """Partial doc without recent_n → still returns the default."""
        import dashboard_prefs
        result = dashboard_prefs.load_prefs(
            db=_db(_StubSnap(True, {"some_other_field": "x"})),
        )
        assert result["recent_n"] == 20


# ---- save_prefs -----------------------------------------------------------


class TestSavePrefs:
    def test_writes_to_correct_doc_with_metadata(self):
        import dashboard_prefs
        captured = {}

        def _on_set(data, merge):
            captured["data"] = data
            captured["merge"] = merge

        dashboard_prefs.save_prefs(
            {"recent_n": 30},
            actor="admin@example.com",
            db=_db(_StubSnap(False, None), on_set=_on_set),
        )
        assert captured["data"]["recent_n"] == 30
        assert captured["data"]["updated_by"] == "admin@example.com"
        assert "updated_at" in captured["data"]


# ---- validate_prefs -------------------------------------------------------


class TestValidatePrefs:
    def test_accepts_valid_recent_n(self):
        import dashboard_prefs
        assert dashboard_prefs.validate_prefs({"recent_n": 20}) is None

    @pytest.mark.parametrize("n", [5, 20, 100])
    def test_accepts_recent_n_at_bounds(self, n):
        import dashboard_prefs
        assert dashboard_prefs.validate_prefs({"recent_n": n}) is None

    @pytest.mark.parametrize("bad_n", [0, -1, 4, 101, 1000, 1.5, "20", None, True])
    def test_rejects_out_of_range_or_wrong_type(self, bad_n):
        import dashboard_prefs
        err = dashboard_prefs.validate_prefs({"recent_n": bad_n})
        assert err is not None
        assert "recent_n" in err

    def test_missing_recent_n_treated_as_default(self):
        """An empty prefs payload should validate clean — load_prefs
        will just return defaults at read time."""
        import dashboard_prefs
        assert dashboard_prefs.validate_prefs({}) is None
