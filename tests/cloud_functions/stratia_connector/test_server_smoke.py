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
    "search_universities", "get_university", "get_college_list", "get_fit_analysis",
    "get_deadlines", "get_profile", "add_college", "remove_college",
    "recompute_fit", "update_profile_field",
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
