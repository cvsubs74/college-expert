"""
Test setup for the QA agent.

Stubs the heavy Google libraries (firestore, firebase-admin, genai)
so the agent's logic can be unit-tested without provisioning credentials,
network, or actual Cloud SDKs.

The qa_agent module imports its way down through firestore_store →
google.cloud.firestore, auth → firebase_admin, and corpus / synthesizer
/ narratives / main → google.genai. We stub each at the module level
before any test imports the qa_agent package.
"""

import sys
import types
from pathlib import Path

# Source on sys.path so `import auth, corpus, runner` etc. work as if
# we were inside the function bundle.
SOURCE_DIR = Path(__file__).resolve().parents[3] / 'cloud_functions' / 'qa_agent'
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))


def _ensure_module(name):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    mod.__path__ = []
    return mod


# --- Stub google.cloud.firestore ---------------------------------------------
_firestore = _ensure_module('google.cloud.firestore')


class _Query:
    DESCENDING = 'desc'


_firestore.Query = _Query


class _StubClient:
    """A bare-minimum Firestore client stub. Tests that exercise
    firestore_store inject their own fake; this exists so the import
    works."""

    def collection(self, *_a, **_k):
        return _StubCollection()


class _StubCollection:
    def document(self, *_a, **_k):
        return _StubDoc()

    def order_by(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def stream(self):
        return iter(())


class _StubDoc:
    def get(self):
        class _Snap:
            exists = False
            def to_dict(self):
                return None
        return _Snap()

    def set(self, *_a, **_k):
        return None

    @property
    def reference(self):
        return self

    def delete(self):
        return None


_firestore.Client = _StubClient


# --- Stub firebase_admin -----------------------------------------------------
_fa = _ensure_module('firebase_admin')
_fa._apps = {}


def _initialize_app():
    _fa._apps['DEFAULT'] = object()


_fa.initialize_app = _initialize_app


_fa_auth = _ensure_module('firebase_admin.auth')


def _create_custom_token(uid):
    # Returns bytes — that's what the real SDK does.
    return f'custom-token-for-{uid}'.encode('utf-8')


_fa_auth.create_custom_token = _create_custom_token

# `from firebase_admin import credentials` — used by auth.py's lazy init.
_ensure_module('firebase_admin.credentials')


# --- Stub google.genai -------------------------------------------------------
# We register a fake `google.genai` module in sys.modules without touching
# the parent `google` namespace — google-cloud-firestore (already installed
# in test envs) provides the real `google` package, and shadowing it would
# break `from google.cloud import firestore`.
_genai = _ensure_module('google.genai')


class _StubModels:
    def generate_content(self, *_a, **_k):
        return types.SimpleNamespace(text='')


class _StubGenaiClient:
    def __init__(self, *_a, **_k):
        self.models = _StubModels()


_genai.Client = _StubGenaiClient


# --- Stub functions_framework -----------------------------------------------
# main.py decorates qa_agent with @functions_framework.http; the decorator
# is a no-op for our test purposes — it just needs to exist at import time.
_ff = _ensure_module('functions_framework')
_ff.http = lambda fn: fn


# --- Stub flask --------------------------------------------------------------
# qa_agent/main.py imports `jsonify` from flask. Tests don't need a real
# Flask response — just something with .status_code, .headers (dict), and
# .get_data().
_flask = _ensure_module('flask')


class _StubResponse:
    def __init__(self, payload):
        import json as _json
        self._payload = payload
        self._body = _json.dumps(payload)
        self.status_code = 200
        self.headers = {}

    def get_data(self, as_text=False):
        return self._body if as_text else self._body.encode('utf-8')


def _jsonify(payload):
    return _StubResponse(payload)


_flask.jsonify = _jsonify


# --- Add a verify_id_token method to firebase_admin.auth --------------------
# Tests monkeypatch this; default returns no email so the dual-auth gate
# rejects (which is what we want by default — explicit tests opt in).
def _verify_id_token(_token):
    raise ValueError("test stub: verify_id_token not configured")


_fa_auth.verify_id_token = _verify_id_token
