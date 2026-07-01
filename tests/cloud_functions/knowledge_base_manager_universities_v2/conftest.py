"""
Shared test setup for knowledge_base_manager_universities_v2 unit tests.

Differs from the other cloud-function conftests in one important way:
profile_manager_v2's tests already `import firestore_db` (and `main`) by
plain name, and two modules can't share one sys.modules slot in a single
pytest process. So this suite loads the KB modules under unique aliases
(kbv2_*) via importlib, aliasing the plain names only for the instant
main.py's own `from firestore_db import ...` lines execute, then restoring
sys.modules. Tests reach the modules through the `kb` fixture.

Heavy Google deps (functions_framework, flask, google.genai,
google.cloud.firestore) are stubbed before load — attrs are only added if
missing so we never clobber another suite's stubs.
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'knowledge_base_manager_universities_v2'


def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mod.__path__ = []
    return mod


def _setdefault_attr(mod, name, value):
    if not hasattr(mod, name):
        setattr(mod, name, value)


# --- Stub functions_framework (decorator passthrough) ---
_ff = _ensure_module('functions_framework')
_setdefault_attr(_ff, 'http', lambda fn: fn)

# --- Stub flask.request (module-level import in main.py) ---
_flask = _ensure_module('flask')
_setdefault_attr(_flask, 'request', None)

# --- Stub google.genai (chat feature; not exercised in these tests) ---
_google = _ensure_module('google')
_genai = _ensure_module('google.genai')
_setdefault_attr(_genai, 'Client', lambda *a, **k: None)
_genai_types = _ensure_module('google.genai.types')
_setdefault_attr(_genai_types, 'Content', lambda *a, **k: None)
_setdefault_attr(_genai_types, 'Part', lambda *a, **k: None)
_setdefault_attr(_genai, 'types', _genai_types)
_setdefault_attr(_google, 'genai', _genai)

# --- Stub google.cloud.firestore (import-time name only; the db fixture
# patches the binding inside kbv2_firestore_db with the in-memory fake) ---
_gcloud = _ensure_module('google.cloud')
_gcf = _ensure_module('google.cloud.firestore')
_setdefault_attr(_gcf, 'Client', lambda *a, **k: None)
_setdefault_attr(_gcloud, 'firestore', _gcf)


def _load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, SOURCE_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


kb_versioning = _load('versioning.py', 'kbv2_versioning')
kb_firestore_db = _load('firestore_db.py', 'kbv2_firestore_db')
kb_year_history = _load('year_history.py', 'kbv2_year_history')
kb_gemini_fallback = _load('gemini_fallback.py', 'kbv2_gemini_fallback')

# main.py does `from firestore_db import get_db` / `from versioning import …`
# — alias the plain names just long enough for those imports to bind to OUR
# modules, then restore whatever was there (or nothing). gemini_fallback is
# aliased too so this suite runs in isolation (previously it only resolved
# because counselor_agent's conftest happened to put ITS copy on sys.path).
_saved = {n: sys.modules.get(n)
          for n in ('firestore_db', 'versioning', 'year_history', 'gemini_fallback')}
sys.modules['firestore_db'] = kb_firestore_db
sys.modules['versioning'] = kb_versioning
sys.modules['year_history'] = kb_year_history
sys.modules['gemini_fallback'] = kb_gemini_fallback
try:
    kb_main = _load('main.py', 'kbv2_main')
finally:
    for _name, _old in _saved.items():
        if _old is None:
            sys.modules.pop(_name, None)
        else:
            sys.modules[_name] = _old


# --- In-memory Firestore double -------------------------------------------


class FakeDocSnapshot:
    def __init__(self, doc_id, data, reference=None):
        self.id = doc_id
        self._data = data
        self.reference = reference

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        import copy
        return copy.deepcopy(self._data) if self._data is not None else None


class FakeDocRef:
    """store maps path tuples → doc dicts; subcollection docs extend the
    parent doc's path, e.g. ('universities', 'mit', 'versions', '2026')."""

    def __init__(self, store, path):
        self._store = store
        self._path = path

    def get(self, field_paths=None):
        data = self._store.get(self._path)
        if data is not None and field_paths:
            wanted = set(field_paths)
            data = {k: v for k, v in data.items() if k in wanted}
        return FakeDocSnapshot(self._path[-1], data, reference=self)

    def set(self, data):
        import copy
        self._store[self._path] = copy.deepcopy(data)

    def update(self, fields):
        if self._path not in self._store:
            raise KeyError(f"update on missing doc {self._path}")
        self._store[self._path].update(fields)

    def delete(self):
        self._store.pop(self._path, None)

    def collection(self, name):
        return FakeCollectionRef(self._store, self._path + (name,))


class FakeCollectionRef:
    def __init__(self, store, path):
        self._store = store
        self._path = path

    def document(self, doc_id):
        return FakeDocRef(self._store, self._path + (str(doc_id),))

    def stream(self):
        for path in sorted(self._store.keys()):
            if len(path) == len(self._path) + 1 and path[:len(self._path)] == self._path:
                yield FakeDocRef(self._store, path).get()

    def limit(self, n):
        return self

    def where(self, *a, **k):
        return self


class FakeFirestoreClient:
    def __init__(self):
        self.store = {}

    def collection(self, name):
        return FakeCollectionRef(self.store, (name,))


@pytest.fixture
def db(monkeypatch):
    """A fresh FirestoreDB backed by the in-memory fake, singleton reset.

    Patches the firestore binding inside kbv2_firestore_db only (reverted by
    monkeypatch), so other suites' google.cloud.firestore stubs are untouched.
    """
    monkeypatch.setattr(
        kb_firestore_db, 'firestore',
        types.SimpleNamespace(Client=FakeFirestoreClient),
    )
    kb_firestore_db._db_instance = None
    yield kb_firestore_db.get_db()
    kb_firestore_db._db_instance = None


@pytest.fixture
def kb(db):
    """The KB modules + live fake db, bundled for tests."""
    return types.SimpleNamespace(
        main=kb_main,
        firestore_db=kb_firestore_db,
        versioning=kb_versioning,
        year_history=kb_year_history,
        db=db,
    )


def _make_profile(uid='testu', name='Test University', acceptance_rate=25.0,
                  deadlines=None, longitudinal_trends=None, **overrides):
    profile = {
        '_id': uid,
        'metadata': {
            'official_name': name,
            'location': {'city': 'Testville', 'state': 'CA', 'type': 'Private'},
        },
        'admissions_data': {
            'current_status': {
                'overall_acceptance_rate': acceptance_rate,
                'test_policy_details': 'Test optional',
            },
            **({'longitudinal_trends': longitudinal_trends}
               if longitudinal_trends is not None else {}),
        },
        'strategic_profile': {'market_position': 'Test Tier', 'us_news_rank': 42},
        'application_process': {
            'application_deadlines': deadlines if deadlines is not None else [
                {'plan_type': 'Early Decision', 'date': '2026-11-01', 'is_binding': True},
                {'plan_type': 'Regular Decision', 'date': '2027-01-05', 'is_binding': False},
            ],
        },
        'outcomes': {'median_earnings_10yr': 80000},
    }
    profile.update(overrides)
    return profile


@pytest.fixture
def make_profile():
    """Factory for a minimal valid collector profile."""
    return _make_profile
