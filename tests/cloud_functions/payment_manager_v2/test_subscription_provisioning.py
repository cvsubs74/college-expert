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
