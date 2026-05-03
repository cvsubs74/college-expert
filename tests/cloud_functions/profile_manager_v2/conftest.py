"""
Shared test setup for profile_manager_v2 unit tests.

Two responsibilities:

1. Put the function source dir on sys.path so tests can `import firestore_db`
   etc. without packaging the cloud function as a real Python package.
2. Stub google.cloud.firestore (and friends) before any test triggers an
   import of firestore_db, so tests run fast and CI doesn't need to install
   google-cloud-firestore (which is large).
"""

import sys
import types
from pathlib import Path

# Source dir → sys.path. ROOT/cloud_functions/profile_manager_v2/
SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'profile_manager_v2'
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mod.__path__ = []
    return mod


# Stub the firestore client. firestore_db only uses .Client() and .Query at
# module scope; everything else flows through the instance attribute (db.db),
# which tests inject directly.
_google = _ensure_module('google')
_cloud = _ensure_module('google.cloud')
_firestore = _ensure_module('google.cloud.firestore')


class _StubFirestoreClient:
    """Constructed only at module-init time of firestore_db. Tests bypass
    this by directly setting db.db on FirestoreDB instances they build via
    __new__()."""
    def __init__(self, *args, **kwargs):
        pass


_firestore.Client = _StubFirestoreClient


class _StubQuery:
    DESCENDING = 'DESCENDING'
    ASCENDING = 'ASCENDING'


_firestore.Query = _StubQuery


# google.cloud.firestore_v1.base_query.FieldFilter — used in queries.
_firestore_v1 = _ensure_module('google.cloud.firestore_v1')
_base_query = _ensure_module('google.cloud.firestore_v1.base_query')


class _StubFieldFilter:
    def __init__(self, *args, **kwargs):
        pass


_base_query.FieldFilter = _StubFieldFilter
