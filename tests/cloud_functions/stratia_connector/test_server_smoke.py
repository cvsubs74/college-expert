"""Boots the FastMCP app and checks wiring: tools registered, OAuth discovery
metadata served, and the MCP endpoint requires auth. Needs mcp + starlette
testclient (httpx); skipped in the lightweight CI image."""
import asyncio
import os

import pytest

pytest.importorskip("mcp")
pytest.importorskip("httpx")  # starlette TestClient backend
# google.auth is real here, but a full-suite run may have a fake `google`
# package stubbed by another conftest — skip rather than error in that case.
pytest.importorskip("google.auth")

# Configure before importing the app (settings reads env at import).
os.environ.setdefault("OAUTH_USE_FIRESTORE", "false")
os.environ.setdefault("GOOGLE_CLIENT_ID", "dummy.apps.googleusercontent.com")
os.environ.setdefault("PUBLIC_BASE_URL", "http://localhost:8080")
# TestClient sends Host: testserver — allow it past DNS-rebinding protection.
os.environ.setdefault("ALLOWED_HOSTS", "testserver,localhost")

import server  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

EXPECTED_TOOLS = {
    # reads
    "search_universities", "get_university", "get_university_history",
    "get_university_majors",
    "get_college_list", "get_fit_analysis",
    "get_fit_history", "get_deadlines", "get_profile", "get_roadmap", "get_essays",
    "get_aid_packages", "get_scholarships", "get_credits", "check_fit_recomputation",
    # safe writes
    "add_college", "remove_college", "recompute_fit", "update_profile_field",
    "set_intended_majors", "set_major_choice",
    # major strategy phase 2 (#284)
    "get_major_map", "generate_major_map",
    "get_major_strategy", "generate_major_strategy",
    # per-college major chances (#302)
    "get_college_major_chances", "rank_college_majors",
}


@pytest.fixture(scope="module")
def client():
    # One client for the module — the streamable session manager lifespan may
    # only run once per app instance.
    with TestClient(server.app) as c:
        yield c


def test_all_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert EXPECTED_TOOLS <= names
    assert len(names) >= 17


def test_year_access_tools_registered():
    # #279: year-versioned KB access for agents.
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    assert tools["get_university_history"].annotations.readOnlyHint is True
    # Section names are enum-typed so agents discover them from the schema alone.
    uni_schema = tools["get_university"].inputSchema
    assert "year" in uni_schema["properties"]
    assert "sections" in uni_schema["properties"]
    hist_schema = tools["get_university_history"].inputSchema
    assert "years" in hist_schema["properties"]
    schema_text = str(uni_schema)
    assert "admissions_data" in schema_text and "academic_structure" in schema_text


def test_major_tools_registered():
    # #281/#282: major-selection tools.
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    assert tools["get_university_majors"].annotations.readOnlyHint is True
    assert tools["set_intended_majors"].annotations.readOnlyHint is False
    assert tools["set_intended_majors"].annotations.idempotentHint is True
    assert tools["set_major_choice"].annotations.idempotentHint is True
    assert "major" in tools["recompute_fit"].inputSchema["properties"]


def test_major_p2_tools_registered():
    # #284: Major Map + per-school strategy — reads free, generates billed.
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    assert tools["get_major_map"].annotations.readOnlyHint is True
    assert tools["get_major_strategy"].annotations.readOnlyHint is True
    for gen in ("generate_major_map", "generate_major_strategy"):
        assert tools[gen].annotations.readOnlyHint is False
        assert tools[gen].annotations.idempotentHint is False
        # Docstrings must carry the credit-cost + confirm-first discipline.
        assert "1" in tools[gen].description and "credit" in tools[gen].description
        assert "get_credits" in tools[gen].description
    # The miss case must be documented so agents relay it honestly.
    assert "NOT charged" in tools["generate_major_strategy"].description
    assert "majors" in tools["generate_major_strategy"].inputSchema["properties"]


def test_major_chances_tools_registered():
    # #302: per-college Major Chances — read free, rank billed.
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    assert tools["get_college_major_chances"].annotations.readOnlyHint is True
    rank = tools["rank_college_majors"]
    assert rank.annotations.readOnlyHint is False
    assert rank.annotations.idempotentHint is False
    # Credit-cost + confirm-first + honest-miss discipline in the docstring.
    assert "1" in rank.description and "credit" in rank.description
    assert "get_credits" in rank.description
    assert "NOT charged" in rank.description
    assert "university_id" in rank.inputSchema["properties"]


def test_research_notebook_tools_registered():
    # #236: analysis tools over the saved-notes notebook.
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    assert {"search_research", "get_all_research", "research_overview",
            "list_stale_research", "pin_research", "research_to_tasks"} <= set(tools)
    # Reads are readOnly; pin is an idempotent write; to-tasks a non-idempotent write.
    for r in ("search_research", "get_all_research", "research_overview", "list_stale_research"):
        assert tools[r].annotations.readOnlyHint is True
    assert tools["pin_research"].annotations.readOnlyHint is False
    assert tools["pin_research"].annotations.idempotentHint is True
    assert tools["research_to_tasks"].annotations.readOnlyHint is False
    assert tools["research_to_tasks"].annotations.idempotentHint is False


def test_tools_have_safety_annotations():
    tools = {t.name: t for t in asyncio.run(server.mcp.list_tools())}
    # Reads are readOnly; writes are not; destructive ops flagged.
    assert tools["search_universities"].annotations.readOnlyHint is True
    assert tools["get_college_list"].annotations.readOnlyHint is True
    assert tools["add_college"].annotations.readOnlyHint is False
    assert tools["remove_college"].annotations.destructiveHint is True
    assert tools["update_profile_field"].annotations.destructiveHint is True
    assert tools["recompute_fit"].annotations.idempotentHint is False


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_oauth_authorization_server_metadata(client):
    r = client.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    meta = r.json()
    for key in ("authorization_endpoint", "token_endpoint", "registration_endpoint"):
        assert key in meta


def test_protected_resource_metadata(client):
    r = client.get("/.well-known/oauth-protected-resource")
    assert r.status_code == 200


def test_mcp_endpoint_requires_auth(client):
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401


# --- #233: per-client research attribution -------------------------------------

@pytest.mark.parametrize("client_name,expected", [
    ("ChatGPT", ("chatgpt", "ChatGPT")),
    ("openai-mcp", ("chatgpt", "ChatGPT")),
    ("Claude", ("claude", "Claude")),
    ("claude-ai", ("claude", "Claude")),
    ("Claude Code", ("claude_code", "Claude Code")),  # more specific than "Claude"
    ("Cursor (VS Code)", ("cursor", "Cursor")),
    ("Some New Agent", ("mcp", "Some New Agent")),     # unknown → keep its real name
    ("", ("mcp", "an AI agent")),                       # nameless → neutral, never Claude
])
def test_client_attribution_maps_the_calling_client(monkeypatch, client_name, expected):
    class _Token:
        client_id = "cid-1"

    monkeypatch.setattr(server, "get_access_token", lambda: _Token())
    monkeypatch.setattr(server.store, "get_client", lambda cid: {"client_name": client_name})
    assert server._client_attribution() == expected


def test_client_attribution_without_a_token_is_generic_not_claude(monkeypatch):
    monkeypatch.setattr(server, "get_access_token", lambda: None)
    source, model = server._client_attribution()
    assert (source, model) == ("mcp", "an AI agent")
    assert source != "claude" and model != "Claude"
