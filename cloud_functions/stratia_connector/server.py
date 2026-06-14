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
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

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
        "Access the signed-in student's Stratia Admissions data: college list, "
        "complete college-fit analyses (scores, gap analysis, strategy, timeline, "
        "scholarships, essay angles), fit history, the full university knowledge "
        "base, the student's academic profile, roadmap tasks, essays, financial-aid "
        "packages, scholarship tracker, and credit balance. You can also make safe "
        "changes (add/remove a college, recompute a fit, update a profile field). "
        "When you produce analysis worth keeping — a college comparison, an "
        "application timeline, essay angles, a scholarship plan, a school deep-dive, "
        "or an overall strategy — offer to save it with save_research so it lands in "
        "the student's Research Notebook in the app, linked to the relevant colleges; "
        "list_research / get_research let you revisit and build on earlier work. "
        "All per-student data is scoped to the authenticated user."
    ),
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    # Validate Host/Origin (MCP transport G2) to block DNS-rebinding.
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=settings.ENABLE_DNS_REBINDING_PROTECTION,
        allowed_hosts=settings.allowed_hosts(),
        allowed_origins=settings.allowed_origins(),
    ),
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
    # `subject` is stamped on the AccessToken by the provider; fall back to a
    # store lookup for robustness.
    email = (getattr(at, "subject", None) or provider.email_for_token(at.token)) if at else None
    if not email:
        raise ValueError("not authenticated")
    return email


def _rate_guard(email: str, action: str, limit: int, window: int):
    """Raise (→ surfaced as a tool error) when `email` exceeds `limit` per
    `window` seconds for `action`."""
    if not store.rate_allow(f"{action}:{email}", limit, window):
        raise ValueError(
            f"Rate limit reached for '{action}'. Please wait and try again."
        )


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------

# Read tools are marked readOnlyHint so the host knows they never mutate.
# openWorldHint=True: they reach an external system (the Stratia backends).

@mcp.tool(annotations=ToolAnnotations(title="Search universities", readOnlyHint=True, openWorldHint=True))
def search_universities(query: str, limit: int = 10,
                        max_acceptance_rate: float | None = None,
                        state: str | None = None) -> list:
    """Search the Stratia university knowledge base by name/keywords.
    Optionally filter by max acceptance rate (percent) or US state code.
    Returns up to `limit` matches with id, name, location, acceptance rate."""
    return sc.search_universities(query, limit, max_acceptance_rate, state)


@mcp.tool(annotations=ToolAnnotations(title="Get university details", readOnlyHint=True, openWorldHint=True))
def get_university(university_id: str) -> dict:
    """Full Stratia knowledge-base profile for one university: identity + every
    section — admissions data (acceptance/test policy, longitudinal trends,
    admitted-student profile), academic structure & majors, application process
    & deadlines, application strategy, financials & cost of attendance,
    scholarships, credit policies, student insights, outcomes, strategic
    profile."""
    return sc.get_university(university_id)


@mcp.tool(annotations=ToolAnnotations(title="Get my college list", readOnlyHint=True, openWorldHint=True))
def get_college_list() -> list:
    """The signed-in student's saved college list (id, name, application
    status, and current fit category for each)."""
    return sc.get_college_list(_email())


@mcp.tool(annotations=ToolAnnotations(title="Get fit analysis", readOnlyHint=True, openWorldHint=True))
def get_fit_analysis(university_id: str) -> dict:
    """The student's COMPLETE college-fit analysis for one university — every
    detail the app shows across its tabs: fit category & match %, scored factors,
    gap analysis, full explanation, prioritized recommendations, test strategy,
    major strategy, essay angles, application timeline, scholarship matches,
    demonstrated-interest tips and red flags, plus KB-data provenance."""
    return sc.get_fit_analysis(_email(), university_id)


@mcp.tool(annotations=ToolAnnotations(title="Get fit history", readOnlyHint=True, openWorldHint=True))
def get_fit_history(university_id: str) -> dict:
    """Prior-cycle fit analyses for one university — how the student's fit
    category and match percentage have evolved across admission cycles."""
    return sc.get_fit_history(_email(), university_id)


@mcp.tool(annotations=ToolAnnotations(title="Get upcoming deadlines", readOnlyHint=True, openWorldHint=True))
def get_deadlines() -> list:
    """Upcoming application deadlines across the student's college list,
    as a flat list of {university, deadline_type, date}."""
    return sc.get_deadlines(_email())


@mcp.tool(annotations=ToolAnnotations(title="Get my profile", readOnlyHint=True, openWorldHint=True))
def get_profile() -> dict:
    """The student's FULL academic profile: personal info, intended major,
    GPA & academics, test scores, course history (with grades), AP/IB scores,
    extracurriculars & achievements, leadership roles, special programs, awards,
    and work experience."""
    return sc.get_profile(_email())


@mcp.tool(annotations=ToolAnnotations(title="Get my roadmap tasks", readOnlyHint=True, openWorldHint=True))
def get_roadmap(status: str | None = None, university_id: str | None = None) -> dict:
    """The student's roadmap tasks (what to do next): titles, due dates, status,
    and the university each relates to. Optionally filter by status or university."""
    return sc.get_roadmap(_email(), status, university_id)


@mcp.tool(annotations=ToolAnnotations(title="Get my essays", readOnlyHint=True, openWorldHint=True))
def get_essays(university_id: str | None = None) -> dict:
    """The student's essay tracker: prompts, word limits, status, word counts,
    and latest drafts. Optionally scope to one university."""
    return sc.get_essays(_email(), university_id)


@mcp.tool(annotations=ToolAnnotations(title="Get financial-aid packages", readOnlyHint=True, openWorldHint=True))
def get_aid_packages() -> dict:
    """The student's saved financial-aid packages per university: cost of
    attendance, grants/scholarships, loans, work-study, and net cost."""
    return sc.get_aid_packages(_email())


@mcp.tool(annotations=ToolAnnotations(title="Get my scholarship tracker", readOnlyHint=True, openWorldHint=True))
def get_scholarships() -> dict:
    """The student's tracked scholarships: name, amount, deadline, eligibility
    match, and status."""
    return sc.get_scholarships(_email())


@mcp.tool(annotations=ToolAnnotations(title="Get my credit balance", readOnlyHint=True, openWorldHint=True))
def get_credits() -> dict:
    """The student's Stratia credit balance and subscription tier. (recompute_fit
    spends 1 credit.)"""
    return sc.get_credits(_email())


@mcp.tool(annotations=ToolAnnotations(title="Check for stale fits", readOnlyHint=True, openWorldHint=True))
def check_fit_recomputation() -> dict:
    """Which saved fits are stale (profile changes or newer KB data) and worth
    recomputing — so you know when spending a credit on recompute_fit pays off."""
    return sc.check_fit_recomputation(_email())


# ---------------------------------------------------------------------------
# Safe write tools — annotated so the host can prompt for confirmation.
# ---------------------------------------------------------------------------

@mcp.tool(annotations=ToolAnnotations(
    title="Add a college to my list", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def add_college(university_id: str, name: str) -> dict:
    """Add a university (by id and display name) to the student's college list."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.add_college(email, university_id, name)


@mcp.tool(annotations=ToolAnnotations(
    title="Remove a college from my list", readOnlyHint=False,
    destructiveHint=True, idempotentHint=True, openWorldHint=True))
def remove_college(university_id: str, name: str = "") -> dict:
    """Remove a university (by id) from the student's college list."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.remove_college(email, university_id, name)


@mcp.tool(annotations=ToolAnnotations(
    title="Recompute fit (uses 1 credit)", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def recompute_fit(university_id: str) -> dict:
    """Recompute the student's college-fit analysis for one university against
    the latest knowledge-base data. Note: this consumes 1 Stratia credit."""
    email = _email()
    # Tighter limit — this spends a credit and calls the LLM.
    _rate_guard(email, "recompute", settings.RATE_RECOMPUTE_PER_HOUR, 3600)
    return sc.recompute_fit(email, university_id)


@mcp.tool(annotations=ToolAnnotations(
    title="Update a profile field", readOnlyHint=False,
    destructiveHint=True, idempotentHint=False, openWorldHint=True))
def update_profile_field(field_path: str, value: str, operation: str = "set") -> dict:
    """Update one field of the student's profile. `field_path` is dotted
    (e.g. 'intended_major'); `operation` is 'set' (default), 'append', or
    'remove' (remove can delete data)."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.update_profile_field(email, field_path, value, operation)


# ---------------------------------------------------------------------------
# Research notebook — save the analysis you do here back into the student's app
# so it's tracked, linked to their colleges, and readable in a later session.
# ---------------------------------------------------------------------------

@mcp.tool(annotations=ToolAnnotations(
    title="Save research to my notebook", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def save_research(title: str, body_markdown: str, kind: str = "note",
                  summary: str = "", university_ids: list[str] | None = None,
                  tags: list[str] | None = None, kb_year: int | None = None) -> dict:
    """Save a piece of research/analysis to the student's Stratia Research
    Notebook so it persists in the app. Use this whenever you produce something
    worth keeping — a college comparison, an application timeline, essay angles,
    a scholarship plan, a school deep-dive, or an overall strategy.

    - `kind`: one of comparison | timeline | essay_angle | scholarship |
      school_deep_dive | strategy | note (defaults to note).
    - `body_markdown`: the full analysis in Markdown.
    - `summary`: a one-line TL;DR shown in the notebook feed.
    - `university_ids`: ids of the colleges this is about, to link it to their
      cards (use ids from get_college_list / search_universities).
    - `kb_year`: the knowledge-base admission cycle your analysis was based on
      (e.g. 2026) so the app can flag the note if newer data arrives later.

    Returns the new research_id and the stored record."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.save_research(email, title, body_markdown, kind=kind, summary=summary,
                            university_ids=university_ids, tags=tags, kb_year=kb_year)


@mcp.tool(annotations=ToolAnnotations(title="List my research notes", readOnlyHint=True, openWorldHint=True))
def list_research(kind: str | None = None, university_id: str | None = None) -> dict:
    """List the student's saved research notes (newest first) — id, title, kind,
    summary, linked colleges, and date. Optionally filter by kind or a linked
    university_id. Use get_research for a note's full body."""
    return sc.list_research(_email(), kind=kind, university_id=university_id)


@mcp.tool(annotations=ToolAnnotations(title="Get a research note", readOnlyHint=True, openWorldHint=True))
def get_research(research_id: str) -> dict:
    """Get one saved research note in full — title, Markdown body, linked
    colleges, tags, and provenance (source/model/KB cycle). Use this to build on
    or revise earlier work."""
    return sc.get_research(_email(), research_id)


@mcp.tool(annotations=ToolAnnotations(
    title="Update a research note", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def update_research(research_id: str, title: str | None = None,
                    body_markdown: str | None = None, kind: str | None = None,
                    summary: str | None = None, university_ids: list[str] | None = None,
                    tags: list[str] | None = None) -> dict:
    """Update an existing research note. Only the fields you pass are changed —
    e.g. revise body_markdown after recomputing a fit, or add university_ids."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.update_research(email, research_id, title=title, body_markdown=body_markdown,
                              kind=kind, summary=summary, university_ids=university_ids, tags=tags)


@mcp.tool(annotations=ToolAnnotations(
    title="Delete a research note", readOnlyHint=False,
    destructiveHint=True, idempotentHint=True, openWorldHint=True))
def delete_research(research_id: str) -> dict:
    """Delete a research note from the student's notebook (cannot be undone)."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.delete_research(email, research_id)


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


# ASGI app for uvicorn (Procfile: `web: uvicorn server:app ...`).
app = mcp.streamable_http_app()

# Kill switch: when CONNECTOR_ENABLED is false, 404 everything except /health
# (and forward lifespan/websocket scopes so the session manager still starts).
# Lets the connector be disabled via env without a redeploy. See settings.py.
if not settings.CONNECTOR_ENABLED:
    from starlette.responses import PlainTextResponse

    _inner = app

    async def app(scope, receive, send):  # noqa: F811 - intentional ASGI wrapper
        if scope.get("type") == "http" and scope.get("path") != "/health":
            await PlainTextResponse("connector disabled", status_code=404)(scope, receive, send)
            return
        await _inner(scope, receive, send)

    logger.warning("CONNECTOR_ENABLED=false — serving 404 for all routes except /health")
