"""workflow_stats: the cross-user Popular Workflows aggregate. Atomic count
increment per save + top-N-by-count read. Firestore is stubbed in conftest; a
small in-memory fake models the root collection, Increment, and order_by."""

import google.cloud.firestore as _fs

# conftest stubs the firestore module; give it an Increment marker our fake applies.
_fs.Increment = lambda n: ("INC", n)
if not hasattr(_fs, "Query"):
    _fs.Query = type("Query", (), {"DESCENDING": "DESCENDING"})
else:
    _fs.Query.DESCENDING = "DESCENDING"

from firestore_db import FirestoreDB  # noqa: E402


class _Snap:
    def __init__(self, d):
        self._d = d

    def to_dict(self):
        return dict(self._d)


def _apply(cur, data):
    """Mirror Firestore set(merge=True): apply Increment sentinels and merge
    nested maps (so weeks['YYYY-Www']: INC accrues into the existing map)."""
    for k, v in data.items():
        if isinstance(v, tuple) and v and v[0] == "INC":
            cur[k] = cur.get(k, 0) + v[1]
        elif isinstance(v, dict):
            sub = dict(cur.get(k) or {})
            _apply(sub, v)
            cur[k] = sub
        else:
            cur[k] = v
    return cur


class _StatDoc:
    def __init__(self, store, sid):
        self.store, self.sid = store, sid

    def set(self, data, merge=False):
        cur = dict(self.store.get(self.sid, {})) if merge else {}
        self.store[self.sid] = _apply(cur, data)


class _StatColl:
    def __init__(self, store):
        self.store = store
        self._field = None
        self._desc = False
        self._n = None

    def document(self, sid):
        return _StatDoc(self.store, sid)

    def order_by(self, field, direction=None):
        self._field = field
        # Compare against whatever firestore_db's firestore.Query.DESCENDING
        # resolves to (the same stubbed module), not a hardcoded string — other
        # test packages stub google.cloud.firestore with a different value.
        self._desc = direction == getattr(getattr(_fs, "Query", None), "DESCENDING", "DESCENDING")
        return self

    def limit(self, n):
        self._n = n
        return self

    def stream(self):
        items = sorted(self.store.values(), key=lambda d: d.get(self._field, 0), reverse=self._desc)
        return [_Snap(d) for d in items[: self._n if self._n else len(items)]]


class _Root:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        assert name == "workflow_stats"
        return _StatColl(self.store)


def _db():
    db = FirestoreDB.__new__(FirestoreDB)
    db.db = _Root()
    return db


def test_upsert_increments_count_and_keeps_metadata():
    db = _db()
    sig = "get_profile>get_fit_analysis"
    assert db.upsert_workflow_stat(sig, ["get_profile", "get_fit_analysis"], "comparison") is True
    db.upsert_workflow_stat(sig, ["get_profile", "get_fit_analysis"], "comparison")
    rec = db.db.store[sig]
    assert rec["count"] == 2                       # atomic increment accrues
    assert rec["tools"] == ["get_profile", "get_fit_analysis"]
    assert rec["kind"] == "comparison" and rec["signature"] == sig


def test_get_popular_returns_top_by_count_desc():
    db = _db()
    for _ in range(3):
        db.upsert_workflow_stat("a>b", ["a", "b"], "comparison")
    db.upsert_workflow_stat("c>d", ["c", "d"], "timeline")
    top = db.get_popular_workflows(limit=10)
    assert [w["signature"] for w in top] == ["a>b", "c>d"]   # most-run first
    assert top[0]["count"] == 3


def test_upsert_accrues_current_week_bucket():
    db = _db()
    sig = "get_profile>get_fit_analysis"
    db.upsert_workflow_stat(sig, ["get_profile", "get_fit_analysis"], "comparison")
    db.upsert_workflow_stat(sig, ["get_profile", "get_fit_analysis"], "comparison")
    weeks = db.db.store[sig]["weeks"]
    # Both runs land in (whatever) the current ISO week — one bucket, count 2.
    assert len(weeks) == 1
    assert sum(weeks.values()) == 2
    # Bucket key is the same 'YYYY-Www' shape the frontend computes.
    (key,) = weeks.keys()
    assert key.startswith("20") and "-W" in key


def test_get_popular_trims_weeks_to_recent_window():
    db = _db()
    # Seed a doc that has been popular for a year (52 week buckets).
    weeks = {f"2025-W{w:02d}": w for w in range(1, 53)}
    db.db.store["x>y"] = {
        "signature": "x>y", "tools": ["x", "y"], "kind": "note",
        "count": sum(weeks.values()), "weeks": dict(weeks), "updated_at": "2025-12-31",
    }
    top = db.get_popular_workflows(limit=10)
    trimmed = top[0]["weeks"]
    assert len(trimmed) == 8                                  # bounded payload
    assert set(trimmed) == {f"2025-W{w:02d}" for w in range(45, 53)}  # newest kept
    assert db.db.store["x>y"]["count"] == sum(weeks.values())  # read doesn't mutate the count
