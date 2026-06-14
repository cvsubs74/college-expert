"""Subscription provisioning + email normalization (the 'charged but Free' fix).

Covers: plan detection by billing interval (incl. the annual case the old
renewal handler silently dropped — the indentation bug), the Stratia-only gate,
and email normalization for Firestore doc keys."""
import importlib.util
import sys
from pathlib import Path

import stripe  # stubbed by conftest

SRC = Path(__file__).resolve().parents[3] / "cloud_functions" / "payment_manager_v2"


def _load(unique_name, filename):
    """Load a payment module under a UNIQUE name by file path, with SRC first +
    a temporary bare alias so the module's own `from firestore_db import ...`
    resolves to the payment copy during exec."""
    saved_path = list(sys.path)
    sys.path.insert(0, str(SRC))
    spec = importlib.util.spec_from_file_location(unique_name, SRC / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    sys.modules[filename[:-3]] = mod  # bare alias for sibling imports during exec
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = saved_path
    return mod


firestore_db = _load("pay_firestore_db", "firestore_db.py")
main = _load("pay_main", "main.py")
# Strip the bare aliases so profile_manager_v2 imports its OWN main/firestore_db.
for _bare in ("main", "firestore_db", "email_service"):
    sys.modules.pop(_bare, None)


def _sub(interval, product_name, sub_id="sub_1", cust="cus_1", period_end=1893456000):
    # register the product the helper will retrieve
    prod_id = f"prod_{product_name.replace(' ', '')}"
    stripe.Product._store[prod_id] = {"name": product_name}
    return {
        "id": sub_id, "customer": cust, "status": "active",
        "current_period_end": period_end,
        "items": {"data": [{"price": {"product": prod_id, "recurring": {"interval": interval}}}]},
    }


class _V15Obj:
    """Mimics stripe-python v12+ StripeObject: subscriptable + attribute access
    for existing keys, but NO .get() — `obj.get('x')` raises AttributeError('get'),
    exactly like the real object that silently broke every webhook ('charged but
    Free'). Plain dicts have .get(); this is what the old code wrongly assumed."""
    def __init__(self, data):
        self._data = {
            k: (_V15Obj(v) if isinstance(v, dict)
                else [_V15Obj(i) if isinstance(i, dict) else i for i in v] if isinstance(v, list)
                else v)
            for k, v in data.items()
        }

    def __getitem__(self, k):
        return self._data[k]

    def __contains__(self, k):
        return k in self._data

    def __bool__(self):
        return bool(self._data)

    def __getattr__(self, k):
        # match StripeObject.__getattr__: missing key surfaces as AttributeError(key)
        try:
            return object.__getattribute__(self, "_data")[k]
        except KeyError:
            raise AttributeError(k)

    def __str__(self):
        def enc(o):
            if isinstance(o, _V15Obj):
                return {k: enc(v) for k, v in o._data.items()}
            if isinstance(o, list):
                return [enc(i) for i in o]
            return o
        import json as _json
        return _json.dumps(enc(self))


class TestStripeObjectV15Compat:
    """Regression guard for the stripe-python v12+ break: StripeObject has no
    .get(), so the dict-style handler code threw AttributeError('get') on the
    first access and provisioned nobody."""

    def test_v15_object_has_no_get(self):
        obj = _V15Obj({"customer": "cus_x"})
        import pytest
        with pytest.raises(AttributeError):
            obj.get("customer")          # proves the fake reproduces the v15 break

    def test_as_dict_converts_v15_object(self):
        d = main._as_dict(_V15Obj({"customer": "cus_x", "items": {"data": [{"id": "si_1"}]}}))
        assert isinstance(d, dict)
        assert d.get("customer") == "cus_x"                       # .get() works now
        assert d["items"]["data"][0]["id"] == "si_1"             # nested converted too

    def test_as_dict_passthrough_dict_and_none(self):
        src = {"a": 1}
        assert main._as_dict(src) is src                          # no-op for real dicts
        assert main._as_dict(None) == {}

    def test_period_end_falls_back_to_item_level(self):
        # newer API: current_period_end is None on the sub, set on the line item
        sub = {"current_period_end": None,
               "items": {"data": [{"current_period_end": 1893456000}]}}
        assert main._subscription_period_end_iso(sub).startswith("2030-")

    def test_provision_accepts_v15_subscription_object(self, monkeypatch):
        # the headline regression: a real-shaped StripeObject (no .get) must still provision
        calls = {}
        monkeypatch.setattr(main, "update_user_purchases",
                            lambda email, grants, details: calls.update(email=email, grants=grants, plan=details["plan"]) or True)
        stripe.Customer._store["cus_v15"] = {"email": "v15@example.com"}
        sub = _V15Obj(_sub("month", "Stratia Admissions Monthly", cust="cus_v15"))
        assert main.provision_subscription(sub, source="test") is True
        assert calls["email"] == "v15@example.com"
        assert calls["grants"]["fit_analysis"] == 20 and calls["plan"] == "monthly"

    def test_lifecycle_updated_self_heals_v15_event(self, monkeypatch):
        # end-to-end: a customer.subscription.updated event delivered as StripeObjects,
        # user not yet active in Firestore → handler self-heals and writes premium credits
        saved = {}

        class FakeDB:
            def get_purchases(self, e): return {}                 # not active → self-heal
            def save_purchases(self, e, d): saved[("purchases", e)] = d; return True
            def get_credits(self, e): return {}
            def save_credits(self, e, d): saved[("credits", e)] = d; return True
            def add_purchase_record(self, e, d): return True

        monkeypatch.setattr(main, "get_payment_db", lambda: FakeDB())
        stripe.Customer._store["cus_v15b"] = {"email": "stu@example.com"}
        event = _V15Obj({"type": "customer.subscription.updated",
                         "data": {"object": _sub("month", "Stratia Admissions Monthly", cust="cus_v15b")}})
        main.handle_subscription_lifecycle_webhooks(event)        # must not raise
        cred = saved[("credits", "stu@example.com")]
        assert cred["subscription_active"] is True and cred["tier"] == "monthly"
        assert cred["credits_remaining"] == 20


class TestNormalizeEmail:
    def test_lowercases_and_trims(self):
        assert firestore_db._norm("  Pradeepthi@Gmail.com ") == "pradeepthi@gmail.com"
        assert firestore_db._norm(None) == ""


class TestStratiaSubscriptionGrants:
    def test_annual_grants_150_season_pass(self):
        grants, details, plan = main._stratia_subscription_grants(_sub("year", "Stratia Admissions Season Pass"))
        assert plan == "annual"
        assert grants["fit_analysis"] == 150 and grants["access_full"] is True
        assert details["plan"] == "annual" and details["stripe_subscription_id"] == "sub_1"

    def test_monthly_grants_20(self):
        grants, _, plan = main._stratia_subscription_grants(_sub("month", "Stratia Admissions Monthly"))
        assert plan == "monthly" and grants["fit_analysis"] == 20

    def test_non_stratia_product_skipped(self):
        assert main._stratia_subscription_grants(_sub("month", "GuruShishya Premium Unlimited")) is None

    def test_non_recurring_skipped(self):
        sub = {"id": "s", "customer": "c", "items": {"data": [{"price": {"product": "p", "recurring": None}}]}}
        assert main._stratia_subscription_grants(sub) is None


class TestProvisionSubscription:
    def test_annual_provisions_via_update_user_purchases(self, monkeypatch):
        # the headline fix: an ANNUAL sub must grant credits (old code wrote nothing)
        calls = {}
        monkeypatch.setattr(main, "update_user_purchases",
                           lambda email, grants, details: calls.update(email=email, grants=grants, details=details) or True)
        stripe.Customer._store["cus_1"] = {"email": "Stu@Example.com"}
        ok = main.provision_subscription(_sub("year", "Stratia Admissions Season Pass"), source="test")
        assert ok is True
        assert calls["email"] == "Stu@Example.com"          # normalization happens in the DB layer
        assert calls["grants"]["fit_analysis"] == 150
        assert calls["details"]["plan"] == "annual"

    def test_non_stratia_is_noop(self, monkeypatch):
        called = {"n": 0}
        monkeypatch.setattr(main, "update_user_purchases", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or True)
        assert main.provision_subscription(_sub("month", "GuruShishya Premium Unlimited")) is False
        assert called["n"] == 0

    def test_no_email_is_noop(self, monkeypatch):
        monkeypatch.setattr(main, "update_user_purchases", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not be called")))
        stripe.Customer._store.pop("cus_noemail", None)  # retrieve → {} → no email
        assert main.provision_subscription(_sub("month", "Stratia Admissions Monthly", cust="cus_noemail")) is False
