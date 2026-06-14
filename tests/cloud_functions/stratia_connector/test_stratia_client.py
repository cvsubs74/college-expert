"""Stratia API client wrapper — request building + response trimming + errors.
Monkeypatches `requests`; CI-safe (requests is in requirements-test.txt)."""
import pytest

import stratia_client as sc


class _Resp:
    def __init__(self, payload, status=200):
        self._p = payload
        self.status_code = status

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}")


@pytest.fixture
def captured(monkeypatch):
    calls = {}

    def fake_get(url, params=None, timeout=None, headers=None):
        calls["get"] = {"url": url, "params": params, "timeout": timeout, "headers": headers}
        return _Resp(calls["_get_payload"])

    def fake_post(url, json=None, timeout=None, headers=None):
        calls["post"] = {"url": url, "json": json, "timeout": timeout, "headers": headers}
        return _Resp(calls["_post_payload"])

    monkeypatch.setattr(sc.requests, "get", fake_get)
    monkeypatch.setattr(sc.requests, "post", fake_post)
    return calls


def test_search_universities_trims_and_limits(captured):
    captured["_post_payload"] = {"universities": [
        {"university_id": "duke_university", "official_name": "Duke", "acceptance_rate": 5,
         "summary": "x" * 1000, "extra": "dropped"},
    ]}
    out = sc.search_universities("duke", limit=5, max_acceptance_rate=10, state="NC")
    assert out[0]["university_id"] == "duke_university"
    assert out[0]["name"] == "Duke"
    assert len(out[0]["summary"]) == 400          # trimmed
    assert "extra" not in out[0]
    assert captured["post"]["json"]["filters"] == {"max_acceptance_rate": 10, "state": "NC"}


def test_get_university_shape(captured):
    captured["_get_payload"] = {"success": True, "university": {
        "university_id": "duke_university", "official_name": "Duke", "data_year": 2026,
        "profile": {
            "application_process": {"application_deadlines": [
                {"plan_type": "RD", "date": "2026-01-02", "junk": 1}, "a-string"]},
            "financials": {"scholarships": [{"name": "S", "amount": "$1", "deadline_date": "2026-01-15"}]},
        }}}
    out = sc.get_university("duke_university")
    assert out["data_year"] == 2026
    assert out["application_deadlines"] == [{"plan_type": "RD", "date": "2026-01-02"}]  # string entry skipped
    assert out["scholarships"][0]["deadline_date"] == "2026-01-15"


def test_get_university_not_found_raises(captured):
    captured["_get_payload"] = {"success": False}
    with pytest.raises(sc.StratiaError):
        sc.get_university("nope")


def test_get_deadlines_maps_rows(captured):
    captured["_post_payload"] = {"success": True, "deadlines": [
        {"university_name": "UCSD", "deadline_type": "RD", "date": "2025-11-30"}]}
    out = sc.get_deadlines("a@b.com")
    assert out == [{"university": "UCSD", "deadline_type": "RD", "date": "2025-11-30"}]
    assert captured["post"]["headers"]["X-User-Email"] == "a@b.com"


def test_add_college_payload_and_success(captured):
    captured["_post_payload"] = {"success": True}
    out = sc.add_college("a@b.com", "duke_university", "Duke")
    assert out == {"added": "duke_university"}
    body = captured["post"]["json"]
    assert body["action"] == "add" and body["university"] == {"id": "duke_university", "name": "Duke"}


def test_write_failure_raises_stratia_error(captured):
    captured["_post_payload"] = {"success": False, "error": "nope"}
    with pytest.raises(sc.StratiaError) as e:
        sc.add_college("a@b.com", "x", "X")
    assert "nope" in str(e.value)


def test_recompute_fit_uses_longer_timeout(captured):
    captured["_post_payload"] = {"success": True, "fit_analysis": {"fit_category": "REACH", "match_percentage": 30}}
    out = sc.recompute_fit("a@b.com", "duke_university")
    assert out["match_percentage"] == 30
    assert captured["post"]["timeout"] == 120
