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
    captured["_get_payload"] = {"universities": [
        {"university_id": "duke_university", "official_name": "Duke", "acceptance_rate": 5,
         "summary": "x" * 1000, "extra": "dropped"},
    ]}
    out = sc.search_universities("duke", limit=5, max_acceptance_rate=10, state="NC")
    assert out[0]["university_id"] == "duke_university"
    assert out[0]["name"] == "Duke"
    assert len(out[0]["summary"]) == 600          # list-view summary cap
    assert "extra" not in out[0]
    # Uses the KB GET ?search= keyword endpoint (not the offline POST semantic one).
    assert captured["get"]["params"] == {"search": "duke", "limit": 5, "max_acceptance": 10, "state": "NC"}


def test_get_university_merges_full_profile(captured):
    captured["_get_payload"] = {"success": True, "university": {
        "university_id": "duke_university", "official_name": "Duke", "data_year": 2026,
        "profile": {
            "application_process": {"application_deadlines": [{"plan_type": "RD", "date": "2026-01-02"}]},
            "financials": {"scholarships": [{"name": "S", "amount": "$1", "deadline_date": "2026-01-15"}]},
        }}}
    out = sc.get_university("duke_university")
    assert out["data_year"] == 2026
    # profile sections are merged at the top level (not hand-picked)
    assert out["application_process"]["application_deadlines"][0]["date"] == "2026-01-02"
    assert out["financials"]["scholarships"][0]["deadline_date"] == "2026-01-15"


def test_get_university_not_found_raises(captured):
    captured["_get_payload"] = {"success": False}
    with pytest.raises(sc.StratiaError):
        sc.get_university("nope")


def test_get_deadlines_maps_rows(captured):
    captured["_post_payload"] = {"success": True, "deadlines": [
        {"university_name": "UCSD", "deadline_type": "RD", "date": "2025-11-30"}]}
    out = sc.get_deadlines("a@b.com")
    assert out[0]["university"] == "UCSD" and out[0]["deadline_type"] == "RD" and out[0]["date"] == "2025-11-30"
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


# --- comprehensiveness: prune helper + full passthrough --------------------

def test_prune_drops_internal_keys_and_caps_lists_and_text():
    obj = {
        "keep": "ok", "_private": 1, "embedding": [0.1], "name_embedding": [0.2],
        "input_snapshot": {"deadlines_hash": "x"},
        "items": list(range(100)),
        "blurb": "y" * 5000,
        "nested": {"user_id": "drop", "good": [1, 2, 3]},
    }
    out = sc._prune(obj, list_caps={"items": 5}, text_caps={"blurb": 100})
    assert out["keep"] == "ok"
    assert "_private" not in out and "embedding" not in out and "name_embedding" not in out
    assert "input_snapshot" not in out
    assert out["items"] == list(range(5))           # list capped
    assert len(out["blurb"]) == 100                  # text capped
    assert "user_id" not in out["nested"] and out["nested"]["good"] == [1, 2, 3]


def test_get_fit_analysis_returns_full_object(captured):
    captured["_get_payload"] = {"fit_analysis": {
        "fit_category": "SUPER_REACH", "match_percentage": 34,
        "explanation": "why " * 10,
        "factors": [{"name": "Academics", "score": 8, "max": 10, "detail": "strong"}],
        "gap_analysis": {"primary_gap": "rigor", "student_strengths": ["robotics"]},
        "recommendations": [{"action": "retake SAT", "impact": "high"}],
        "test_strategy": {"recommendation": "submit", "student_sat": 1500},
        "major_strategy": {"intended_major": "CS", "is_impacted": True},
        "essay_angles": [{"angle": "founder story"}],
        "application_timeline": {"recommended_plan": "RD", "deadline": "2026-01-02"},
        "scholarship_matches": [{"name": "Merit", "amount": "$5k"}],
        "input_snapshot": {"deadlines_hash": "abc"},   # internal → dropped
    }}
    out = sc.get_fit_analysis("a@b.com", "duke")
    # every UI-tab field flows through
    for k in ("factors", "gap_analysis", "recommendations", "test_strategy",
              "major_strategy", "essay_angles", "application_timeline", "scholarship_matches"):
        assert k in out, k
    assert out["gap_analysis"]["student_strengths"] == ["robotics"]
    assert "input_snapshot" not in out               # internal stripped
    assert out["university_id"] == "duke"


def test_get_university_returns_all_sections(captured):
    captured["_get_payload"] = {"success": True, "university": {
        "university_id": "duke", "official_name": "Duke", "data_year": 2026,
        "profile": {
            "admissions_data": {"current_status": {"overall_acceptance_rate": 6}},
            "academic_structure": {"colleges": [{"name": "Trinity"}]},
            "financials": {"cost_of_attendance_breakdown": {"out_of_state": {"total_coa": 85000}}},
            "outcomes": {"retention": 0.97},
            "application_process": {"application_deadlines": [{"plan_type": "RD", "date": "2026-01-02"}]},
        }}}
    out = sc.get_university("duke")
    for section in ("admissions_data", "academic_structure", "financials",
                    "outcomes", "application_process"):
        assert section in out, section
    assert out["name"] == "Duke"


def test_get_roadmap_and_credits_wrappers(captured):
    captured["_get_payload"] = {"success": True, "tasks": [{"task_id": "t1", "title": "Draft essay"}], "count": 1}
    rm = sc.get_roadmap("a@b.com", status="pending")
    assert rm["tasks"][0]["title"] == "Draft essay"
    assert captured["get"]["params"]["status"] == "pending"

    captured["_get_payload"] = {"credits_balance": 12, "subscription_tier": "pro"}
    cr = sc.get_credits("a@b.com")
    assert cr["credits_balance"] == 12 and cr["subscription_tier"] == "pro"


# --- research notebook --------------------------------------------------------

def test_save_research_posts_structured_payload(captured):
    captured["_post_payload"] = {"success": True, "research_id": "rsh_1",
                                 "research": {"title": "Duke vs UCSD", "kind": "comparison"}}
    out = sc.save_research("a@b.com", "Duke vs UCSD", "## body", kind="comparison",
                           summary="tl;dr", university_ids=["duke_university"], kb_year=2026)
    assert out["saved"] == "rsh_1"
    body = captured["post"]["json"]
    assert body["title"] == "Duke vs UCSD" and body["body_markdown"] == "## body"
    assert body["kind"] == "comparison" and body["source"] == "claude_mcp"
    assert body["university_ids"] == ["duke_university"] and body["kb_year"] == 2026
    assert captured["post"]["headers"]["X-User-Email"] == "a@b.com"


def test_save_research_failure_raises(captured):
    captured["_post_payload"] = {"success": False, "error": "boom"}
    with pytest.raises(sc.StratiaError) as e:
        sc.save_research("a@b.com", "t", "b")
    assert "boom" in str(e.value)


def test_list_research_maps_rows(captured):
    captured["_get_payload"] = {"success": True, "research": [
        {"research_id": "rsh_1", "title": "T", "kind": "timeline", "summary": "s",
         "university_ids": ["x"], "tags": ["a"], "created_at": "2026-06-14", "body_markdown": "dropped"}]}
    out = sc.list_research("a@b.com", kind="timeline")
    assert out["count"] == 1
    row = out["research"][0]
    assert row["research_id"] == "rsh_1" and row["kind"] == "timeline"
    assert "body_markdown" not in row  # list view is metadata-only
    assert captured["get"]["params"]["kind"] == "timeline"


def test_get_research_returns_full_body(captured):
    captured["_get_payload"] = {"success": True, "research": {
        "research_id": "rsh_1", "title": "T", "body_markdown": "x" * 100,
        "provenance": {"kb_year": 2026}}}
    out = sc.get_research("a@b.com", "rsh_1")
    assert out["body_markdown"].startswith("x")
    assert out["provenance"]["kb_year"] == 2026


def test_get_research_not_found_raises(captured):
    captured["_get_payload"] = {"success": True, "research": None}
    with pytest.raises(sc.StratiaError):
        sc.get_research("a@b.com", "nope")


def test_update_research_sends_only_provided_fields(captured):
    captured["_post_payload"] = {"success": True}
    sc.update_research("a@b.com", "rsh_1", body_markdown="new", summary="s2")
    body = captured["post"]["json"]
    assert body["research_id"] == "rsh_1" and body["body_markdown"] == "new" and body["summary"] == "s2"
    assert "title" not in body and "kind" not in body  # untouched fields omitted


def test_delete_research(captured):
    captured["_post_payload"] = {"success": True, "research_id": "rsh_1"}
    assert sc.delete_research("a@b.com", "rsh_1") == {"deleted": "rsh_1"}
