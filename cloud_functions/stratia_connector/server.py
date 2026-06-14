"""Stratia Admissions — Claude connector (remote MCP server).

A FastMCP Streamable-HTTP server that exposes a student's Stratia data (college
list, fit analyses, deadlines, profile) and a few safe write actions to Claude.
Sign-in is Google OAuth (federated); the verified email is the Stratia user.

Run (Cloud Run / local):  uvicorn server:app --host 0.0.0.0 --port $PORT
MCP endpoint:             <PUBLIC_BASE_URL>/mcp   (add this URL in Claude)
"""
import logging

from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions
from mcp.server.auth.middleware.auth_context import get_access_token

import stratia_client as sc
from auth_provider import GoogleOAuthProvider
from settings import settings
from store import OAuthStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stratia_connector")

store = OAuthStore(use_firestore=settings.USE_FIRESTORE, project=settings.FIRESTORE_PROJECT)
provider = GoogleOAuthProvider(store)

mcp = FastMCP(
    "Stratia Admissions",
    instructions=(
        "Access the signed-in student's Stratia Admissions data: their college "
        "list, college-fit analyses, upcoming application/scholarship deadlines, "
        "and academic profile. You can also search the university knowledge base "
        "and make safe changes (add/remove a college, recompute a fit, update a "
        "profile field). All per-student data is scoped to the authenticated user."
    ),
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    # As the authorization server, FastMCP derives token verification from the
    # provider (load_access_token) — passing token_verifier too is rejected.
    auth_server_provider=provider,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(settings.PUBLIC_BASE_URL),
        resource_server_url=AnyHttpUrl(settings.PUBLIC_BASE_URL),
        required_scopes=[settings.MCP_SCOPE],
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=[settings.MCP_SCOPE],
            default_scopes=[settings.MCP_SCOPE],
        ),
    ),
)


def _email() -> str:
    """The Stratia email behind the current request's bearer token."""
    at = get_access_token()
    email = provider.email_for_token(at.token) if at else None
    if not email:
        raise ValueError("not authenticated")
    return email


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_universities(query: str, limit: int = 10,
                        max_acceptance_rate: float | None = None,
                        state: str | None = None) -> list:
    """Search the Stratia university knowledge base by name/keywords.
    Optionally filter by max acceptance rate (percent) or US state code.
    Returns up to `limit` matches with id, name, location, acceptance rate."""
    return sc.search_universities(query, limit, max_acceptance_rate, state)


@mcp.tool()
def get_university(university_id: str) -> dict:
    """Full Stratia knowledge-base profile for one university by id:
    location, acceptance rate, application deadlines, and scholarships."""
    return sc.get_university(university_id)


@mcp.tool()
def get_college_list() -> list:
    """The signed-in student's saved college list (id, name, application
    status, and current fit category for each)."""
    return sc.get_college_list(_email())


@mcp.tool()
def get_fit_analysis(university_id: str) -> dict:
    """The student's college-fit analysis for one university: fit category,
    match percentage, the KB data year it used, explanation, recommendations."""
    return sc.get_fit_analysis(_email(), university_id)


@mcp.tool()
def get_deadlines() -> list:
    """Upcoming application deadlines across the student's college list,
    as a flat list of {university, deadline_type, date}."""
    return sc.get_deadlines(_email())


@mcp.tool()
def get_profile() -> dict:
    """A summary of the student's academic profile (intended major, grade,
    GPA, test scores, graduation year, activities)."""
    return sc.get_profile(_email())


# ---------------------------------------------------------------------------
# Safe write tools
# ---------------------------------------------------------------------------

@mcp.tool()
def add_college(university_id: str, name: str) -> dict:
    """Add a university (by id and display name) to the student's college list."""
    return sc.add_college(_email(), university_id, name)


@mcp.tool()
def remove_college(university_id: str, name: str = "") -> dict:
    """Remove a university (by id) from the student's college list."""
    return sc.remove_college(_email(), university_id, name)


@mcp.tool()
def recompute_fit(university_id: str) -> dict:
    """Recompute the student's college-fit analysis for one university against
    the latest knowledge-base data. Note: this consumes 1 Stratia credit."""
    return sc.recompute_fit(_email(), university_id)


@mcp.tool()
def update_profile_field(field_path: str, value: str, operation: str = "set") -> dict:
    """Update one field of the student's profile. `field_path` is dotted
    (e.g. 'intended_major'); `operation` is 'set' (default), 'append', or
    'remove'."""
    return sc.update_profile_field(_email(), field_path, value, operation)


# ---------------------------------------------------------------------------
# Custom HTTP routes (unauthenticated): Google OAuth callback + health
# ---------------------------------------------------------------------------

@mcp.custom_route(settings.GOOGLE_REDIRECT_PATH, methods=["GET"])
async def google_callback(request: Request):
    err = request.query_params.get("error")
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if err:
        return HTMLResponse(f"Google sign-in was cancelled or failed: {err}", status_code=400)
    if not code or not state:
        return HTMLResponse("Missing authorization code or state.", status_code=400)
    try:
        redirect_url = provider.complete_google_login(code, state)
    except PermissionError as e:
        return HTMLResponse(f"Access denied: {e}", status_code=403)
    except Exception as e:  # noqa: BLE001 - surface a friendly page, log the detail
        logger.exception("Google callback failed")
        return HTMLResponse(f"Sign-in error: {e}", status_code=400)
    return RedirectResponse(redirect_url, status_code=302)


@mcp.custom_route("/health", methods=["GET"])
async def health(_request: Request):
    return JSONResponse({"status": "ok", "service": "stratia-connector"})


# ASGI app for uvicorn (Procfile: `web: uvicorn main:app ...`).
app = mcp.streamable_http_app()
