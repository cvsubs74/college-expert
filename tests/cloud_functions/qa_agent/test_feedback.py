"""
Tests for feedback.py — admin-authored notes that steer the next
scheduled run's synthesizer.

Spec: docs/prd/qa-feedback-loop.md, docs/design/qa-feedback-loop.md.

Each item:
  {id, text, status, created_at, created_by, applied_count,
   max_applies, last_applied_run_id, last_applied_at}

Heavy deps (firestore) are stubbed in conftest. These tests exercise
load/add/dismiss/active_items/mark_applied logic.
"""

from __future__ import annotations

import pytest


# ---- Stub Firestore helpers ------------------------------------------------


class _FakeDoc:
    """Holds the doc state in-memory; supports get() / set()."""
    def __init__(self):
        self._data = None

    def get(self):
        class _Snap:
            def __init__(self, data):
                self._data = data
                self.exists = data is not None
            def to_dict(self):
                return self._data
        return _Snap(self._data)

    def set(self, payload, merge=False):
        if merge and self._data:
            self._data.update(payload)
        else:
            self._data = dict(payload)


def _db_with(initial=None):
    """Build a fake firestore client with an optional initial doc state."""
    doc = _FakeDoc()
    doc._data = initial

    class _Coll:
        def document(self, _id):
            return doc

    class _DB:
        def collection(self, _name):
            return _Coll()

    return _DB(), doc


# ---- load -----------------------------------------------------------------


class TestLoad:
    def test_returns_empty_when_no_doc(self):
        import feedback
        db, _ = _db_with(None)
        result = feedback.load(db=db)
        assert result == {"items": []}

    def test_returns_stored_payload(self):
        import feedback
        stored = {
            "items": [
                {"id": "fb_1", "text": "test essay tracker", "status": "active",
                 "applied_count": 0, "max_applies": 5},
            ],
        }
        db, _ = _db_with(stored)
        result = feedback.load(db=db)
        assert result["items"][0]["id"] == "fb_1"
        assert result["items"][0]["text"] == "test essay tracker"


# ---- validate_text --------------------------------------------------------


class TestValidateText:
    @pytest.mark.parametrize("good", [
        "Focus on essay tracker",
        "Verify UC fix landed " * 5,  # ~135 chars, under 500
    ])
    def test_accepts_meaningful_strings(self, good):
        import feedback
        assert feedback.validate_text(good) is None

    @pytest.mark.parametrize("bad", [
        "",
        "   ",
        None,
        "x",  # too short
        "abcd",  # 4 chars, under 5-char minimum
        123,
        "x" * 501,
    ])
    def test_rejects_bad_inputs(self, bad):
        import feedback
        err = feedback.validate_text(bad)
        assert err is not None
        assert isinstance(err, str)


# ---- add_item -------------------------------------------------------------


class TestAddItem:
    def test_creates_active_item_with_metadata(self):
        import feedback
        db, doc = _db_with(None)
        item = feedback.add_item(
            "Focus on essay tracker",
            actor="admin@example.com",
            db=db,
        )
        assert item["status"] == "active"
        assert item["text"] == "Focus on essay tracker"
        assert item["created_by"] == "admin@example.com"
        assert item["applied_count"] == 0
        assert item["max_applies"] == 5
        assert item["id"].startswith("fb_")
        # And the doc was written.
        assert doc._data["items"][0]["id"] == item["id"]

    def test_appends_to_existing_items(self):
        import feedback
        existing = {"items": [{"id": "fb_old", "text": "old", "status": "active",
                               "applied_count": 0, "max_applies": 5,
                               "created_at": "2026-05-04T01:00:00Z",
                               "created_by": "x"}]}
        db, doc = _db_with(existing)
        feedback.add_item("new feedback item", actor="admin@example.com", db=db)
        assert len(doc._data["items"]) == 2

    def test_rejects_invalid_text(self):
        import feedback
        db, _ = _db_with(None)
        with pytest.raises(ValueError):
            feedback.add_item("x", actor="admin@example.com", db=db)

    def test_caps_active_items_at_10(self):
        """11th active item should be rejected to prevent prompt bloat."""
        import feedback
        existing_items = [
            {"id": f"fb_{i}", "text": f"item {i}" * 5, "status": "active",
             "applied_count": 0, "max_applies": 5,
             "created_at": "2026-05-04T01:00:00Z", "created_by": "x"}
            for i in range(10)
        ]
        db, _ = _db_with({"items": existing_items})
        with pytest.raises(ValueError, match="10 active"):
            feedback.add_item("eleventh item should be rejected",
                              actor="admin@example.com", db=db)

    def test_dismissed_items_dont_count_toward_cap(self):
        """A dismissed item shouldn't block adding new active ones."""
        import feedback
        items = [
            {"id": f"fb_a_{i}", "text": f"active {i}" * 3, "status": "active",
             "applied_count": 0, "max_applies": 5,
             "created_at": "x", "created_by": "x"}
            for i in range(9)
        ]
        items.append({
            "id": "fb_dismissed", "text": "dismissed item", "status": "dismissed",
            "applied_count": 5, "max_applies": 5, "created_at": "x", "created_by": "x",
        })
        db, _ = _db_with({"items": items})
        # 10th active is still allowed (1 dismissed doesn't count).
        feedback.add_item("new active item", actor="admin@example.com", db=db)

    def test_persists_caller_supplied_max_applies(self):
        """The dashboard's per-item selector lets the operator pick how
        many runs an item drives before auto-retiring. The chosen value
        round-trips into the stored item."""
        import feedback
        db, _ = _db_with(None)
        item = feedback.add_item(
            "Focus on essay tracker",
            actor="admin@example.com",
            max_applies=10,
            db=db,
        )
        assert item["max_applies"] == 10

    def test_clamps_max_applies_to_upper_bound(self):
        """Out-of-bound values are clamped, not rejected — the dashboard
        sends "Never" as 99 today, but the bound is the source of truth."""
        import feedback
        db, _ = _db_with(None)
        # Try to set a value above the bound.
        item = feedback.add_item(
            "persistent steer",
            actor="admin@example.com",
            max_applies=feedback.MAX_APPLIES_BOUND + 50,
            db=db,
        )
        assert item["max_applies"] == feedback.MAX_APPLIES_BOUND

    def test_clamps_max_applies_to_at_least_one(self):
        """A 0 or negative value would never auto-dismiss — meaningless;
        clamp to 1."""
        import feedback
        db, _ = _db_with(None)
        item = feedback.add_item(
            "one-shot steer",
            actor="admin@example.com",
            max_applies=0,
            db=db,
        )
        assert item["max_applies"] == 1

    def test_max_applies_bound_at_least_99(self):
        """The 'Never' affordance in the UI maps to 99; the bound must
        admit that round-trip without truncating."""
        import feedback
        assert feedback.MAX_APPLIES_BOUND >= 99


# ---- dismiss --------------------------------------------------------------


class TestDismiss:
    def test_marks_item_dismissed(self):
        import feedback
        items = [{
            "id": "fb_1", "text": "test essay tracker thoroughly",
            "status": "active", "applied_count": 1, "max_applies": 5,
            "created_at": "x", "created_by": "x",
        }]
        db, doc = _db_with({"items": items})
        ok = feedback.dismiss("fb_1", db=db)
        assert ok is True
        assert doc._data["items"][0]["status"] == "dismissed"

    def test_returns_false_for_missing_id(self):
        import feedback
        db, _ = _db_with({"items": []})
        assert feedback.dismiss("fb_nonexistent", db=db) is False


# ---- active_items ---------------------------------------------------------


class TestActiveItems:
    def test_returns_only_active(self):
        import feedback
        items = [
            {"id": "a", "text": "x", "status": "active",
             "applied_count": 0, "max_applies": 5, "created_at": "x", "created_by": "x"},
            {"id": "b", "text": "y", "status": "dismissed",
             "applied_count": 5, "max_applies": 5, "created_at": "x", "created_by": "x"},
            {"id": "c", "text": "z", "status": "active",
             "applied_count": 1, "max_applies": 5, "created_at": "x", "created_by": "x"},
        ]
        db, _ = _db_with({"items": items})
        result = feedback.active_items(db=db)
        ids = [it["id"] for it in result]
        assert ids == ["a", "c"]

    def test_caps_at_10(self):
        """active_items must not return more than 10 even if storage
        somehow has more — defensive guard for prompt size."""
        import feedback
        items = [
            {"id": f"fb_{i}", "text": "x" * 10, "status": "active",
             "applied_count": 0, "max_applies": 5,
             "created_at": "x", "created_by": "x"}
            for i in range(15)
        ]
        db, _ = _db_with({"items": items})
        result = feedback.active_items(db=db)
        assert len(result) <= 10


# ---- mark_applied ---------------------------------------------------------


class TestMarkApplied:
    def test_increments_applied_count_and_records_run_id(self):
        import feedback
        items = [{
            "id": "fb_1", "text": "Focus on essay tracker", "status": "active",
            "applied_count": 0, "max_applies": 5,
            "created_at": "x", "created_by": "x",
        }]
        db, doc = _db_with({"items": items})
        feedback.mark_applied(["fb_1"], run_id="run_abc", db=db)
        item = doc._data["items"][0]
        assert item["applied_count"] == 1
        assert item["last_applied_run_id"] == "run_abc"
        assert "last_applied_at" in item
        assert item["status"] == "active"  # not yet at max

    def test_auto_dismisses_when_reaching_max_applies(self):
        import feedback
        items = [{
            "id": "fb_1", "text": "Focus on essay tracker", "status": "active",
            "applied_count": 4, "max_applies": 5,
            "created_at": "x", "created_by": "x",
        }]
        db, doc = _db_with({"items": items})
        feedback.mark_applied(["fb_1"], run_id="run_xyz", db=db)
        item = doc._data["items"][0]
        assert item["applied_count"] == 5
        assert item["status"] == "dismissed"

    def test_marks_multiple_items_atomically(self):
        import feedback
        items = [
            {"id": "fb_1", "text": "x" * 10, "status": "active",
             "applied_count": 0, "max_applies": 5,
             "created_at": "x", "created_by": "x"},
            {"id": "fb_2", "text": "y" * 10, "status": "active",
             "applied_count": 1, "max_applies": 5,
             "created_at": "x", "created_by": "x"},
        ]
        db, doc = _db_with({"items": items})
        feedback.mark_applied(["fb_1", "fb_2"], run_id="run_abc", db=db)
        assert doc._data["items"][0]["applied_count"] == 1
        assert doc._data["items"][1]["applied_count"] == 2

    def test_tolerates_unknown_ids(self):
        """An item id that's already dismissed or doesn't exist should
        be a no-op, not an error."""
        import feedback
        items = [{
            "id": "fb_1", "text": "x" * 10, "status": "active",
            "applied_count": 0, "max_applies": 5,
            "created_at": "x", "created_by": "x",
        }]
        db, doc = _db_with({"items": items})
        feedback.mark_applied(
            ["fb_1", "fb_does_not_exist"], run_id="run_abc", db=db,
        )
        assert doc._data["items"][0]["applied_count"] == 1


# ---- Recently-dismissed visibility ---------------------------------------
# Bug repro 2026-05-04: an operator's note hit max_applies=5 and was
# auto-flipped to "dismissed" — disappeared from the Steer panel even
# though it had successfully driven 5 runs. Add a dedicated reader so
# the dashboard can render a "Retired" subsection.


class TestRecentlyDismissedItems:
    def test_returns_dismissed_only(self):
        import feedback
        items = [
            {"id": "fb_a", "text": "active item", "status": "active",
             "applied_count": 1, "max_applies": 5,
             "created_at": "2026-05-04T10:00:00+00:00", "created_by": "x"},
            {"id": "fb_b", "text": "retired item", "status": "dismissed",
             "applied_count": 5, "max_applies": 5,
             "last_applied_at": "2026-05-04T13:00:00+00:00",
             "last_applied_run_id": "run_xyz",
             "created_at": "2026-05-03T18:00:00+00:00", "created_by": "x"},
        ]
        db, _ = _db_with({"items": items})
        out = feedback.recently_dismissed_items(db=db)
        ids = [it["id"] for it in out]
        assert ids == ["fb_b"]

    def test_sorted_by_last_applied_at_desc(self):
        """The most-recently-retired item shows first so the operator
        sees the latest retirement at the top."""
        import feedback
        items = [
            {"id": "fb_old", "text": "retired earlier", "status": "dismissed",
             "applied_count": 5, "max_applies": 5,
             "last_applied_at": "2026-05-02T12:00:00+00:00",
             "created_at": "2026-05-01T00:00:00+00:00", "created_by": "x"},
            {"id": "fb_new", "text": "retired most recently", "status": "dismissed",
             "applied_count": 5, "max_applies": 5,
             "last_applied_at": "2026-05-04T13:00:00+00:00",
             "created_at": "2026-05-03T00:00:00+00:00", "created_by": "x"},
        ]
        db, _ = _db_with({"items": items})
        out = feedback.recently_dismissed_items(db=db)
        assert [it["id"] for it in out] == ["fb_new", "fb_old"]

    def test_falls_back_to_created_at_when_last_applied_missing(self):
        """A manually-dismissed item without last_applied_at still
        sorts deterministically by its created_at."""
        import feedback
        items = [
            {"id": "fb_manual", "text": "manually dismissed",
             "status": "dismissed",
             "applied_count": 0, "max_applies": 5,
             "created_at": "2026-05-04T08:00:00+00:00", "created_by": "x"},
            {"id": "fb_auto", "text": "auto retired",
             "status": "dismissed",
             "applied_count": 5, "max_applies": 5,
             "last_applied_at": "2026-05-04T12:00:00+00:00",
             "created_at": "2026-05-03T00:00:00+00:00", "created_by": "x"},
        ]
        db, _ = _db_with({"items": items})
        out = feedback.recently_dismissed_items(db=db)
        # fb_auto has last_applied_at=12:00; fb_manual falls back to
        # created_at=08:00 — so fb_auto comes first.
        assert [it["id"] for it in out] == ["fb_auto", "fb_manual"]

    def test_capped_at_default_limit(self):
        """A long history shouldn't dump everything onto the panel."""
        import feedback
        items = [
            {"id": f"fb_{i}", "text": f"retired {i}", "status": "dismissed",
             "applied_count": 5, "max_applies": 5,
             "last_applied_at": f"2026-04-{i:02d}T12:00:00+00:00",
             "created_at": f"2026-04-{i:02d}T00:00:00+00:00", "created_by": "x"}
            for i in range(1, 26)  # 25 retired items
        ]
        db, _ = _db_with({"items": items})
        out = feedback.recently_dismissed_items(db=db)
        # Default limit is 10.
        assert len(out) == 10

    def test_respects_explicit_limit(self):
        import feedback
        items = [
            {"id": f"fb_{i}", "text": f"retired {i}", "status": "dismissed",
             "applied_count": 5, "max_applies": 5,
             "last_applied_at": f"2026-04-{i:02d}T12:00:00+00:00",
             "created_at": f"2026-04-{i:02d}T00:00:00+00:00", "created_by": "x"}
            for i in range(1, 11)
        ]
        db, _ = _db_with({"items": items})
        out = feedback.recently_dismissed_items(limit=3, db=db)
        assert len(out) == 3

    def test_empty_when_nothing_dismissed(self):
        import feedback
        items = [
            {"id": "fb_a", "text": "active", "status": "active",
             "applied_count": 0, "max_applies": 5,
             "created_at": "2026-05-04T10:00:00+00:00", "created_by": "x"},
        ]
        db, _ = _db_with({"items": items})
        assert feedback.recently_dismissed_items(db=db) == []
