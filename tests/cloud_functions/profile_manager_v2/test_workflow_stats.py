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


class _StatDoc:
    def __init__(self, store, sid):
        self.store, self.sid = store, sid

    def set(self, data, merge=False):
        cur = dict(self.store.get(self.sid, {})) if merge else {}
        for k, v in data.items():
            if isinstance(v, tuple) and v and v[0] == "INC":
                cur[k] = cur.get(k, 0) + v[1]
            else:
                cur[k] = v
        self.store[self.sid] = cur


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
