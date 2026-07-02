"""Stratia API client wrapper — request building + response trimming + errors.
Monkeypatches `requests`; CI-safe (requests is in requirements-test.txt)."""
from datetime import datetime

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
            # Real requests attaches the response — _post reads status/body
            # off it to enrich StratiaError (#285).
            raise requests.HTTPError(f"{self.status_code}", response=self)


@pytest.fixture
def captured(monkeypatch):
    calls = {}

    def fake_get(url, params=None, timeout=None, headers=None):
        calls["get"] = {"url": url, "params": params, "timeout": timeout, "headers": headers}
        return _Resp(calls["_get_payload"])

    def fake_post(url, json=None, timeout=None, headers=None):
        calls["post"] = {"url": url, "json": json, "timeout": timeout, "headers": headers}
        return _Resp(calls["_post_payload"], calls.get("_post_status", 200))

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


def test_recompute_fit_sends_force_recompute_true(captured):
    # The tool's purpose is recomputation — an explicit false would get the
    # cached fit under the server's #285 semantics, so it must always be true.
    captured["_post_payload"] = {"success": True, "fit_analysis": {"fit_category": "REACH", "match_percentage": 30}}
    sc.recompute_fit("a@b.com", "duke_university")
    assert captured["post"]["json"]["force_recompute"] is True


def test_recompute_fit_402_surfaces_clear_credit_error(captured):
    captured["_post_payload"] = {"success": False, "error": "insufficient_credits",
                                 "credits_remaining": 2}
    captured["_post_status"] = 402
    with pytest.raises(sc.StratiaError) as e:
        sc.recompute_fit("a@b.com", "duke_university")
    msg = str(e.value)
    assert "insufficient credits" in msg
    assert "2 remaining" in msg
    assert "costs 1" in msg
    # Budgeting conventions are pointed to by name.
    assert "get_credits" in msg and "check_fit_recomputation" in msg


def test_post_non_402_http_error_still_raises_generic_stratia_error(captured):
    # _post's #285 enrichment (status_code/body on StratiaError) must not
    # change what other callers see on unrelated HTTP failures.
    captured["_post_payload"] = {"error": "boom"}
    captured["_post_status"] = 500
    with pytest.raises(sc.StratiaError) as e:
        sc.add_college("a@b.com", "x", "X")
    assert "failed" in str(e.value)
    assert getattr(e.value, "status_code", None) == 500


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


# --- #279: year-versioned KB access ------------------------------------------

def test_get_university_forwards_year_and_sections(captured):
    captured["_get_payload"] = {"success": True, "university": {
        "university_id": "duke", "official_name": "Duke", "data_year": 2025,
        "available_years": [2025, 2026],
        "sections_returned": ["admissions_data"],
        "sections_available": ["admissions_data", "financials"],
        "profile": {"admissions_data": {"current_status": {"overall_acceptance_rate": 6}}}}}
    out = sc.get_university("duke", year=2025, sections=["admissions_data"])
    params = captured["get"]["params"]
    assert params["year"] == 2025
    assert params["sections"] == "admissions_data"
    assert out["data_year"] == 2025
    assert out["sections_returned"] == ["admissions_data"]
    assert out["sections_available"] == ["admissions_data", "financials"]
    assert "admissions_data" in out


def test_get_university_year_miss_surfaces_backend_error(captured):
    # The backend names the missing year AND lists what exists — the agent
    # must see that verbatim, not a generic "not found".
    captured["_get_payload"] = {
        "success": False,
        "error": "University duke has no data for cycle year 2020; available years: [2025, 2026]",
        "available_years": [2025, 2026]}
    with pytest.raises(sc.StratiaError) as e:
        sc.get_university("duke", year=2020)
    assert "2020" in str(e.value) and "2025" in str(e.value)


def test_get_university_history_compact_mode(captured):
    captured["_get_payload"] = {
        "success": True, "official_name": "Duke", "available_years": [2025, 2026],
        "snapshots": [
            {"year": 2026, "source": "kb_snapshot", "acceptance_rate": 5.1},
            {"year": 2025, "source": "kb_snapshot", "acceptance_rate": 6.0},
        ],
        "reported_trends": [
            {"year": 2024, "source": "profile_trend", "verified": False,
             "acceptance_rate_overall": 6.3}],
        "notes": []}
    out = sc.get_university_history("duke")
    assert captured["get"]["params"]["action"] == "history"
    assert [s["year"] for s in out["snapshots"]] == [2026, 2025]
    assert out["reported_trends"][0]["verified"] is False
    assert out["available_years"] == [2025, 2026]


def test_get_university_history_forwards_sections_and_years(captured):
    captured["_get_payload"] = {"success": True, "official_name": "Duke",
                                "available_years": [2025, 2026],
                                "years": {"2026": {"admissions_data": {}}}, "notes": []}
    sc.get_university_history("duke", sections=["admissions_data", "financials"],
                              years=[2025, 2026])
    params = captured["get"]["params"]
    assert params["sections"] == "admissions_data,financials"
    assert params["years"] == "2025,2026"


def test_get_university_history_rejects_old_backend_shape(captured):
    # Deploy skew: an older KB ignores action=history and returns a full
    # profile with success:true — the wrapper must refuse to mis-parse it.
    captured["_get_payload"] = {"success": True, "university": {
        "university_id": "duke", "profile": {"admissions_data": {}}}}
    with pytest.raises(sc.StratiaError) as e:
        sc.get_university_history("duke")
    assert "does not support" in str(e.value)


def test_get_university_history_evicts_oldest_years_when_oversized(captured):
    big = {"admissions_data": {"blob": "x" * 70_000}}
    captured["_get_payload"] = {
        "success": True, "official_name": "Duke", "available_years": [2024, 2025, 2026],
        "years": {"2024": big, "2025": big, "2026": big}, "notes": []}
    out = sc.get_university_history("duke", sections=["admissions_data"])
    assert "2026" in out["years"]                      # newest always survives
    assert "2024" in out["truncated_years"]            # oldest dropped first
    assert set(out["truncated_years"]) | set(out["years"]) == {"2024", "2025", "2026"}
    import json as _json
    assert len(_json.dumps(out, default=str)) <= sc._RESULT_CAP


def test_get_university_history_single_oversized_year_drops_sections(captured):
    # One remaining year can alone exceed the cap — its largest sections are
    # dropped (recorded) instead of returning an over-cap payload the platform
    # would hard-truncate mid-JSON.
    captured["_get_payload"] = {
        "success": True, "official_name": "Duke", "available_years": [2026],
        "years": {"2026": {"student_insights": {"blob": "x" * 200_000},
                           "admissions_data": {"rate": 6.0}}},
        "notes": []}
    out = sc.get_university_history("duke", sections=["student_insights", "admissions_data"])
    assert out["years"]["2026"] == {"admissions_data": {"rate": 6.0}}
    assert out["truncated_sections"] == {"2026": ["student_insights"]}
    import json as _json
    assert len(_json.dumps(out, default=str)) <= sc._RESULT_CAP


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
                           summary="tl;dr", university_ids=["duke_university"], kb_year=2026,
                           source="chatgpt", model="ChatGPT")
    assert out["saved"] == "rsh_1"
    body = captured["post"]["json"]
    assert body["title"] == "Duke vs UCSD" and body["body_markdown"] == "## body"
    assert body["kind"] == "comparison"
    # #233: the real calling client is stamped through, not hardcoded to Claude.
    assert body["source"] == "chatgpt" and body["model"] == "ChatGPT"
    assert body["university_ids"] == ["duke_university"] and body["kb_year"] == 2026
    assert captured["post"]["headers"]["X-User-Email"] == "a@b.com"


def test_save_research_defaults_to_neutral_source_not_claude(captured):
    # When the server can't identify the client it must not default to Claude.
    captured["_post_payload"] = {"success": True, "research_id": "rsh_2", "research": {}}
    sc.save_research("a@b.com", "t", "b")
    body = captured["post"]["json"]
    assert body["source"] == "mcp" and body["source"] != "claude_mcp"


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


# --- #236: research-notebook analysis tools ------------------------------------

def test_search_research_ranks_by_query(captured):
    captured["_get_payload"] = {"research": [
        {"research_id": "r1", "title": "Duke essay angles", "summary": "essay strategy",
         "body_markdown": "essay essay essay", "kind": "essay_angle", "tags": ["essays"],
         "university_ids": ["duke_university"], "created_at": "2026-06-01"},
        {"research_id": "r2", "title": "UC timeline", "summary": "deadlines",
         "body_markdown": "no match here", "kind": "timeline", "tags": [],
         "university_ids": ["uc"], "created_at": "2026-06-02"},
    ]}
    out = sc.search_research("a@b.com", "essay")
    assert out["count"] == 1
    assert out["matches"][0]["research_id"] == "r1"
    assert out["matches"][0]["snippet"]


def test_search_research_requires_query(captured):
    captured["_get_payload"] = {"research": []}
    with pytest.raises(sc.StratiaError):
        sc.search_research("a@b.com", "   ")


def test_search_research_filters_by_college(captured):
    captured["_get_payload"] = {"research": [
        {"research_id": "r1", "title": "scholarship plan", "body_markdown": "scholarship",
         "university_ids": ["duke"], "tags": [], "summary": ""},
        {"research_id": "r2", "title": "scholarship plan", "body_markdown": "scholarship",
         "university_ids": ["uc"], "tags": [], "summary": ""},
    ]}
    out = sc.search_research("a@b.com", "scholarship", university_id="duke")
    assert out["count"] == 1 and out["matches"][0]["research_id"] == "r1"


def test_get_all_research_paginates_and_trims(captured):
    docs = [{"research_id": f"r{i}", "title": f"t{i}", "kind": "note",
             "body_markdown": "x" * 5000, "created_at": f"2026-06-{i:02d}"} for i in range(1, 6)]
    captured["_get_payload"] = {"research": docs}
    out = sc.get_all_research("a@b.com", full=True, offset=0, limit=2)
    assert out["total"] == 5 and out["has_more"] is True and len(out["research"]) == 2
    assert out["research"][0]["research_id"] == "r5"   # newest first
    assert len(out["research"][0]["body_markdown"]) == 2500
    assert out["research"][0]["body_truncated"] is True
    meta = sc.get_all_research("a@b.com", full=False)
    assert "body_markdown" not in meta["research"][0] and meta["has_more"] is False


def test_research_overview_aggregates(captured):
    captured["_get_payload"] = {"research": [
        {"research_id": "r1", "kind": "comparison", "university_ids": ["duke", "uc"],
         "provenance": {"kb_year": 2020}, "pinned": True, "updated_at": "2026-06-02"},
        {"research_id": "r2", "kind": "comparison", "university_ids": ["duke"],
         "provenance": {"kb_year": 2026}, "updated_at": "2026-06-01"},
    ]}
    out = sc.research_overview("a@b.com", now=datetime(2026, 6, 1))
    assert out["total"] == 2 and out["by_kind"]["comparison"] == 2
    assert out["by_college"]["duke"] == 2 and out["by_college"]["uc"] == 1
    assert out["pinned_count"] == 1 and out["stale_count"] == 1
    assert "comparison" in out["kinds_present"] and "timeline" in out["kinds_absent"]
    assert out["last_updated"] == "2026-06-02"


def test_list_stale_research_flags_old_cycle(captured):
    captured["_get_payload"] = {"research": [
        {"research_id": "r1", "title": "old", "provenance": {"kb_year": 2024}},
        {"research_id": "r2", "title": "current", "provenance": {"kb_year": 2026}},
        {"research_id": "r3", "title": "none"},
    ]}
    out = sc.list_stale_research("a@b.com", now=datetime(2026, 6, 1))
    assert out["count"] == 1 and out["stale"][0]["research_id"] == "r1"
    assert out["stale"][0]["cycle"] == "2024–25"


def test_pin_research_posts_pinned(captured):
    captured["_post_payload"] = {"success": True}
    out = sc.pin_research("a@b.com", "r1", pinned=True)
    assert out == {"research_id": "r1", "pinned": True}
    assert captured["post"]["json"]["pinned"] is True
    assert captured["post"]["json"]["research_id"] == "r1"


def test_research_to_tasks_creates_linked_tasks(captured):
    captured["_get_payload"] = {"research": {"research_id": "r1", "title": "Strategy"}}
    captured["_post_payload"] = {"success": True}
    out = sc.research_to_tasks("a@b.com", "r1", [
        {"title": "Draft Duke essay", "university_id": "duke", "due_date": "2026-10-01"},
        {"title": "Finalize college list"},
    ])
    assert out["count"] == 2 and len(out["created"]) == 2
    td = captured["post"]["json"]["task_data"]   # last task created
    assert td["source_research_id"] == "r1" and td["status"] == "pending"
    assert td["category"] == "research" and td["due_date"] == ""


def test_research_to_tasks_missing_note_raises(captured):
    captured["_get_payload"] = {"research": None}
    with pytest.raises(sc.StratiaError):
        sc.research_to_tasks("a@b.com", "nope", [{"title": "x"}])


# --- build/update student profile -------------------------------------------

def test_update_student_profile_posts_profile_and_returns_merged(captured):
    captured["_post_payload"] = {"success": True, "profile": {
        "name": "Ada", "intended_major": "CS", "sat_total": 1500,
        "courses": [{"name": "AP CS", "type": "AP"}],
        "raw_content": "DROP big blob", "field_sources": {"name": ["t.pdf"]},
        "name_embedding": [0.1],
    }}
    prof = {"name": "Ada", "intended_major": "CS", "sat_total": 1500,
            "courses": [{"name": "AP CS", "type": "AP"}]}
    out = sc.update_student_profile("a@b.com", prof, source="transcript.pdf", source_text="raw text")
    body = captured["post"]["json"]
    assert body["profile_data"] == prof
    assert body["source"] == "transcript.pdf" and body["source_text"] == "raw text"
    assert captured["post"]["headers"]["X-User-Email"] == "a@b.com"
    # merged profile returned; internal/bulky keys stripped
    assert out["name"] == "Ada" and out["intended_major"] == "CS"
    assert out["courses"][0]["name"] == "AP CS"
    assert "raw_content" not in out and "field_sources" not in out and "name_embedding" not in out


def test_update_student_profile_omits_source_text_when_absent(captured):
    captured["_post_payload"] = {"success": True, "profile": {"name": "Bo"}}
    sc.update_student_profile("a@b.com", {"name": "Bo"})
    body = captured["post"]["json"]
    assert "source_text" not in body and body["source"] == "agent-import"


def test_update_student_profile_failure_raises(captured):
    captured["_post_payload"] = {"success": False, "error": "bad profile"}
    with pytest.raises(sc.StratiaError) as e:
        sc.update_student_profile("a@b.com", {"name": "x"})
    assert "bad profile" in str(e.value)


def test_save_research_sends_workflow_and_source_prompt(captured):
    captured["_post_payload"] = {"success": True, "research_id": "rsh_2", "research": {"title": "T"}}
    sc.save_research("a@b.com", "Duke vs UCSD", "## body", kind="comparison",
                     source_prompt="compare duke and ucsd",
                     workflow=[{"tool": "get_profile", "label": "Pulled profile"},
                               {"tool": "get_fit_analysis", "label": "Got fit"}])
    body = captured["post"]["json"]
    assert body["source_prompt"] == "compare duke and ucsd"
    assert body["workflow"][0]["tool"] == "get_profile"
    assert len(body["workflow"]) == 2


def test_save_research_omits_workflow_when_absent(captured):
    captured["_post_payload"] = {"success": True, "research_id": "rsh_3", "research": {}}
    sc.save_research("a@b.com", "T", "b")
    body = captured["post"]["json"]
    assert "workflow" not in body and "source_prompt" not in body


# --- decision ledger: set_application_status + get_outcome_calibration --------

def test_normalize_decision_canonicalizes_synonyms():
    assert sc._normalize_decision("Admitted") == "accepted"
    assert sc._normalize_decision("REJECTED") == "denied"
    assert sc._normalize_decision("wait-listed") == "waitlisted"
    assert sc._normalize_decision("enrolled") == "enrolled"
    assert sc._normalize_decision(None) is None


def test_set_application_status_normalizes_and_posts_decision(captured):
    captured["_post_payload"] = {"success": True}
    out = sc.set_application_status("a@b.com", "umich", decision="admitted")
    assert out["updated"] == "umich" and out["decision"] == "accepted"
    body = captured["post"]["json"]
    assert body["university_id"] == "umich" and body["decision"] == "accepted"
    assert captured["post"]["headers"]["X-User-Email"] == "a@b.com"


def test_set_application_status_requires_a_field(captured):
    with pytest.raises(sc.StratiaError):
        sc.set_application_status("a@b.com", "umich")  # neither decision nor status


def test_set_application_status_rejects_unknown_decision(captured):
    with pytest.raises(sc.StratiaError) as e:
        sc.set_application_status("a@b.com", "umich", decision="gap year")
    assert "unknown decision" in str(e.value)


def test_set_application_status_clears_with_empty_string(captured):
    captured["_post_payload"] = {"success": True}
    sc.set_application_status("a@b.com", "umich", decision="")
    assert captured["post"]["json"]["decision"] == ""   # cleared, not junk


def test_set_application_status_failure_raises(captured):
    captured["_post_payload"] = {"success": False, "error": "not on list"}
    with pytest.raises(sc.StratiaError) as e:
        sc.set_application_status("a@b.com", "x", decision="accepted")
    assert "not on list" in str(e.value)


def test_get_college_list_reads_top_level_fit_category(captured):
    # The enriched endpoint returns personalized fit_category top-level (#250).
    captured["_get_payload"] = {"college_list": [
        {"university_id": "umich", "university_name": "Michigan",
         "soft_fit_category": "REACH", "fit_category": "TARGET", "match_percentage": 72},
        {"university_id": "msu", "university_name": "Michigan State", "soft_fit_category": "SAFETY"},
    ]}
    out = sc.get_college_list("a@b.com")
    by_id = {c["university_id"]: c for c in out}
    assert by_id["umich"]["fit_category"] == "TARGET" and by_id["umich"]["match_percentage"] == 72
    assert by_id["umich"]["soft_fit_category"] == "REACH"
    assert by_id["msu"]["fit_category"] is None and by_id["msu"]["soft_fit_category"] == "SAFETY"


def test_get_college_list_falls_back_to_nested_fit_analysis(captured):
    # Older response shape: fit nested under fit_analysis still works.
    captured["_get_payload"] = {"college_list": [
        {"university_id": "duke", "university_name": "Duke",
         "fit_analysis": {"fit_category": "SUPER_REACH", "match_score": 34}},
    ]}
    out = sc.get_college_list("a@b.com")
    assert out[0]["fit_category"] == "SUPER_REACH" and out[0]["match_percentage"] == 34


def test_get_outcome_calibration_passes_through(captured):
    captured["_get_payload"] = {"success": True, "decided_count": 2, "total": 3, "outcomes": [
        {"university_id": "umich", "predicted": "TARGET", "decision": "accepted"}]}
    out = sc.get_outcome_calibration("a@b.com")
    assert out["decided_count"] == 2 and out["total"] == 3
    assert out["outcomes"][0]["university_id"] == "umich"
    assert captured["get"]["params"]["user_email"] == "a@b.com"


# --- #281/#282: major-selection tools ------------------------------------------

def test_get_university_majors_maps_and_guides(captured):
    captured["_get_payload"] = {
        "success": True, "university_id": "uiuc", "official_name": "UIUC",
        "data_year": 2026, "verification_status": "verified", "richness_tier": 1,
        "structure_type": "Decentralized",
        "colleges": [{"name": "Grainger", "majors": [
            {"name": "Computer Science", "entry_risk": "capped_door",
             "entry_path": {"value": "direct_admit", "basis": "kb_verified"}}]}],
        "strategy_notes": {}, "data_notes": []}
    out = sc.get_university_majors("uiuc", college="grainger", query="computer")
    params = captured["get"]["params"]
    assert params["action"] == "majors"
    assert params["college"] == "grainger" and params["q"] == "computer"
    assert out["colleges"][0]["majors"][0]["entry_risk"] == "capped_door"
    assert "capped_door" in out["guidance"]          # trust discipline rides along
    assert "is_impacted:false does NOT" in out["guidance"]


def test_get_university_majors_rejects_old_backend_shape(captured):
    captured["_get_payload"] = {"success": True, "university": {"profile": {}}}
    with pytest.raises(sc.StratiaError) as e:
        sc.get_university_majors("uiuc")
    assert "does not support" in str(e.value)


def test_set_intended_majors_posts_and_maps(captured):
    captured["_post_payload"] = {"success": True,
                                 "intended_majors": ["Statistics", "CS"],
                                 "intended_major": "Statistics"}
    out = sc.set_intended_majors("a@b.com", ["CS", "Statistics"], primary="Statistics")
    body = captured["post"]["json"]
    assert body["majors"] == ["CS", "Statistics"] and body["primary"] == "Statistics"
    assert out == {"intended_majors": ["Statistics", "CS"], "primary": "Statistics"}


def test_set_major_choice_posts_and_surfaces_near_misses(captured):
    captured["_post_payload"] = {
        "success": True, "university_id": "uiuc",
        "major_choice": {"primary": "CS + Advertising", "matched": False,
                         "match_confidence": "none", "kb_year": 2026},
        "near_misses": ["Computer Science"],
        "note": "couldn't be matched"}
    out = sc.set_major_choice("a@b.com", "uiuc", "CS + Advertising",
                              backup_major="Statistics", rationale="why",
                              source="claude")
    body = captured["post"]["json"]
    assert body["primary_major"] == "CS + Advertising"
    assert body["backup_major"] == "Statistics" and body["source"] == "claude"
    assert out["major_choice"]["matched"] is False
    assert out["near_misses"] == ["Computer Science"]


def test_set_major_choice_failure_raises(captured):
    captured["_post_payload"] = {"success": False, "error": "not on the college list"}
    with pytest.raises(sc.StratiaError) as e:
        sc.set_major_choice("a@b.com", "x", "CS")
    assert "not on the college list" in str(e.value)


def test_recompute_fit_forwards_major(captured):
    captured["_post_payload"] = {"success": True, "fit_analysis": {
        "fit_category": "REACH", "match_percentage": 40}}
    sc.recompute_fit("a@b.com", "uiuc", major="Mathematics & Computer Science")
    assert captured["post"]["json"]["intended_major"] == "Mathematics & Computer Science"
    captured["_post_payload"] = {"success": True, "fit_analysis": {
        "fit_category": "REACH", "match_percentage": 40}}
    sc.recompute_fit("a@b.com", "uiuc")
    assert "intended_major" not in captured["post"]["json"]
