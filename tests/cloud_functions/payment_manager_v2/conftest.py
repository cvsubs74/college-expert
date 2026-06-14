"""Stubs for payment_manager_v2 heavy deps (stripe, flask, functions_framework,
google cloud libs) so the handler modules import without those packages.

NOTE: deliberately does NOT put the source dir on sys.path — payment_manager_v2
and profile_manager_v2 both define `main`/`firestore_db`, so the test loads its
modules in isolation by file path (see test_subscription_provisioning.py)."""
import sys
import types


def _ensure(name):
    m = sys.modules.get(name)
    if m is None:
        m = types.ModuleType(name)
        m.__path__ = []
        sys.modules[name] = m
    return m


# stripe -------------------------------------------------------------------
stripe = _ensure("stripe")
if not hasattr(stripe, "api_key"):
    stripe.api_key = "sk_test_placeholder"

    class _StripeError(Exception):
        pass

    err = _ensure("stripe.error")
    err.StripeError = _StripeError
    err.SignatureVerificationError = type("SignatureVerificationError", (_StripeError,), {})
    stripe.error = err

    class _Retrievable:
        _store = {}
        @classmethod
        def retrieve(cls, _id, *a, **k):
            return cls._store.get(_id, {})
        @classmethod
        def modify(cls, *a, **k):
            return {}

    stripe.Product = type("Product", (_Retrievable,), {"_store": {}})
    stripe.Customer = type("Customer", (_Retrievable,), {"_store": {}})
    stripe.Subscription = type("Subscription", (_Retrievable,), {"_store": {}})
    stripe.Webhook = types.SimpleNamespace(construct_event=lambda *a, **k: {})
    stripe.checkout = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **k: types.SimpleNamespace(url="x", id="x")))
    stripe.billing_portal = types.SimpleNamespace(Session=types.SimpleNamespace(create=lambda **k: types.SimpleNamespace(url="x", id="x")))

# flask / functions_framework ---------------------------------------------
_f = _ensure("flask")
if not hasattr(_f, "jsonify"):
    _f.jsonify = lambda x: x
    _f.request = None
_ff = _ensure("functions_framework")
if not hasattr(_ff, "http"):
    _ff.http = lambda fn: fn

# google.cloud.firestore + secretmanager (reuse if already stubbed) --------
_ensure("google")
_ensure("google.cloud")
_fs = _ensure("google.cloud.firestore")
if not hasattr(_fs, "Client"):
    _fs.Client = lambda *a, **k: types.SimpleNamespace()
if not hasattr(_fs, "Query"):
    _fs.Query = type("Query", (), {"DESCENDING": "DESCENDING", "ASCENDING": "ASCENDING"})
_sm = _ensure("google.cloud.secretmanager")
if not hasattr(_sm, "SecretManagerServiceClient"):
    _sm.SecretManagerServiceClient = lambda *a, **k: types.SimpleNamespace()
