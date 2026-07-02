"""Stratia Admissions — Claude connector (remote MCP server).

A FastMCP Streamable-HTTP server that exposes a student's Stratia data (college
list, fit analyses, deadlines, profile) and a few safe write actions to Claude.
Sign-in is Google OAuth (federated); the verified email is the Stratia user.

Run (Cloud Run / local):  uvicorn server:app --host 0.0.0.0 --port $PORT
MCP endpoint:             <PUBLIC_BASE_URL>/mcp   (add this URL in Claude)
"""
import logging
from typing import Literal

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
        "If the student shares a document (transcript, résumé, brag sheet, Common App "
        "activities list), read it and call update_student_profile once with the "
        "extracted fields to build or enrich their profile. "
        "When you produce analysis worth keeping — a college comparison, an "
        "application timeline, essay angles, a scholarship plan, a school deep-dive, "
        "or an overall strategy — offer to save it with save_research so it lands in "
        "the student's Research Notebook in the app, linked to the relevant colleges; "
        "list_research / get_research let you revisit and build on earlier work. "
        "University knowledge-base data is year-versioned by admission cycle: "
        "get_university(year=...) reads a specific cycle's snapshot, "
        "get_university(sections=[...]) keeps large profiles lean, and "
        "get_university_history answers 'what changed at this school' with per-year "
        "data — for cross-school comparisons call it once per school and synthesize. "
        "For major-selection strategy ('what major should I list at X?'): explore the "
        "student's genuine interests from get_profile FIRST, then call "
        "get_university_majors per school and reason from the labeled facts (hedge "
        "kb_reported values; null = not published; entry_risk 'capped_door' means the "
        "door locks behind you — warn, never recommend an apply-easier-then-transfer "
        "play there, and remind the student their essays must cohere with the listed "
        "major). Persist agreed decisions with set_intended_majors and "
        "set_major_choice, recompute fits that changed major (recompute_fit(major=...), "
        "1 credit each), and save the narrative with save_research (kind 'strategy', "
        "tag 'majors'). "
        "In-app major artifacts: get_major_map / get_major_strategy read the "
        "student's saved Major Map and per-school strategy for free (in-app users "
        "can also generate these via the app); generate_major_map / "
        "generate_major_strategy create them at 1 credit each — confirm with the "
        "student and check get_credits first, PREFER reasoning over "
        "get_university_majors facts yourself, and reserve generate_major_strategy "
        "for when the student wants the app-persisted artifact. A "
        "{strategy: null, gaps} response means the KB doesn't know — the student "
        "was NOT charged; relay that honestly and never invent a strategy. "
        "For 'what are my chances across a school's majors?': rank_college_majors "
        "(1 credit) ranks the FIT majors a school offers into likelihood TIERS "
        "(strong/possible/reach/long_shot with a rationale each — never a "
        "fabricated percentage); get_college_major_chances reads the saved "
        "ranking free. A {ranking: null, gaps} response is the same unbilled KB "
        "miss — relay it honestly. "
        "SAVE THE STUDENT A CREDIT: the in-app Generate costs 1 credit, but YOU "
        "(the agent) can compute the fit and/or the major chances yourself and "
        "save them for FREE via save_fit_analysis / save_major_chances — your "
        "subscription bears the LLM cost. Call get_analysis_schema(kind) first "
        "for the exact shape; compute honestly from get_profile + get_university "
        "(+ get_university_majors for chances); the server re-derives KB-sourced "
        "fields (fit category is floored by the school's selectivity, "
        "entry_path/entry_risk come from the KB, off-catalog majors are dropped) "
        "and REJECTS fabricated numbers, relaying field errors so you can fix and "
        "retry. Reserve the 1-credit in-app Generate for when the student "
        "specifically wants Stratia to run it. "
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
        # The protected resource is the MCP endpoint (…/mcp), NOT the origin. The
        # SDK publishes this as the `resource` in /.well-known/oauth-protected-
        # resource (path-appended per RFC 9728 §3.1) and in the 401
        # WWW-Authenticate header. It MUST equal the URL the client connected to
        # (…/mcp) or strict clients (e.g. Gemini CLI) abort with "Protected
        # resource … does not match expected …/mcp". (matches settings.mcp_resource()
        # / the RFC 8707 audience the provider already binds tokens to.)
        resource_server_url=AnyHttpUrl(settings.mcp_resource()),
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


# Map a calling MCP client (by its DCR-registered client_name) to a stable
# (source, model) attribution. Substring match, case-insensitive; order matters
# (more specific first — Claude Code before Claude). #233.
_CLIENT_ATTRIBUTION = (
    (("chatgpt", "openai"), ("chatgpt", "ChatGPT")),
    (("claude code", "claude-code", "claude_code"), ("claude_code", "Claude Code")),
    (("claude", "anthropic"), ("claude", "Claude")),
    (("cursor",), ("cursor", "Cursor")),
    (("windsurf",), ("windsurf", "Windsurf")),
    (("cline",), ("cline", "Cline")),
    (("goose",), ("goose", "Goose")),
    (("gemini",), ("gemini", "Gemini")),
    (("vscode", "vs code", "visual studio code"), ("vscode", "VS Code")),
)


def _client_attribution() -> tuple[str, str]:
    """(source, model) for the MCP client behind the current request, derived
    from its OAuth registration. Best-effort and honest: an unrecognized client
    keeps its registered name (or a neutral agent label) — it is never
    mislabeled as Claude. (Server is stateless_http, so the initialize-time
    clientInfo isn't available here; the token's client_id is.)"""
    name = ""
    at = get_access_token()
    client_id = getattr(at, "client_id", None) if at else None
    if client_id:
        try:
            rec = store.get_client(client_id) or {}
            name = (rec.get("client_name") or "").strip()
        except Exception:  # noqa: BLE001 — attribution must never block a save
            logger.warning("client attribution lookup failed", exc_info=True)
    low = name.lower()
    for needles, attribution in _CLIENT_ATTRIBUTION:
        if any(n in low for n in needles):
            return attribution
    if name:
        logger.info("save_research: unmapped MCP client_name=%r", name)
        return "mcp", name
    logger.info("save_research: no client_name on token; generic agent attribution")
    return "mcp", "an AI agent"


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


# Valid top-level profile sections, enum-typed so the section names land in
# the tool JSON schema (discoverable with zero calls). The backend stays
# permissive — a schema/server drift can't hard-fail.
_Section = Literal[
    "metadata", "strategic_profile", "admissions_data", "academic_structure",
    "application_process", "application_strategy", "financials",
    "credit_policies", "student_insights", "outcomes", "student_retention",
]


@mcp.tool(annotations=ToolAnnotations(title="Get university details", readOnlyHint=True, openWorldHint=True))
def get_university(university_id: str, year: int | None = None,
                   sections: list[_Section] | None = None) -> dict:
    """Full Stratia knowledge-base profile for one university: identity + every
    section — admissions data (acceptance/test policy, admitted-student
    profile), academic structure & majors, application process & deadlines,
    application strategy, financials & cost of attendance, scholarships,
    credit policies, student insights, outcomes, strategic profile.
    Full profiles are large (50-150KB): when you need specific facts, pass
    sections=[...] to fetch just those top-level sections. year=N returns the
    cycle-N snapshot ('2026' = the 2026-27 application cycle, enrolling fall
    2027); read data_year / available_years from the response to see what
    exists — do not derive the current cycle from the calendar date. For
    multi-year 'what changed' questions use get_university_history."""
    return sc.get_university(university_id, year=year, sections=sections)


@mcp.tool(annotations=ToolAnnotations(title="Get university history", readOnlyHint=True, openWorldHint=True))
def get_university_history(university_id: str,
                           sections: list[_Section] | None = None,
                           years: list[int] | None = None) -> dict:
    """Year-by-year view of one university — THE tool for 'what changed / is
    it getting harder' questions. Default: compact per-cycle rows under
    `snapshots` (acceptance rates, class size, test policy, SAT/ACT middle-50,
    early-plan stats, in/out-of-state costs, rank, deadlines; newest first)
    plus `reported_trends`, the school's own multi-year series from the
    current profile. The two lists use DIFFERENT year conventions and trust
    levels: snapshots are Stratia KB captures keyed by application-cycle year
    (verified collections; vintage_estimated:true marks rows whose year is a
    best guess), while reported_trends rows are school-reported and unverified
    (verified:false) — attribute numbers accordingly, never merge the two
    axes into one timeline, and never infer a trend from a single row (many
    schools have only one snapshot so far). Pass sections=[...] for raw
    per-year sections and years=[...] to bound the payload — oldest years are
    dropped first when oversized (see truncated_years). For one year's full
    detail use get_university(year=N)."""
    return sc.get_university_history(university_id, sections=sections, years=years)


@mcp.tool(annotations=ToolAnnotations(title="Get a university's majors & entry paths", readOnlyHint=True, openWorldHint=True))
def get_university_majors(university_id: str, college: str | None = None,
                          query: str | None = None) -> dict:
    """How ONE university admits students into majors — trust-labeled facts
    for major-selection strategy: each college's admissions model, every
    listed major's entry_path (direct_admit / pre_major /
    secondary_application / open_declaration — 'unclear' carries the school's
    verbatim wording, never a guessed badge), a structural `entry_risk`
    signal ('capped_door' = if you're not admitted directly you can't switch
    in later — warn the student; never recommend an apply-easier-then-
    transfer play there), door policy (direct-admit-only, internal-transfer
    allowed/GPA bar), prerequisites, and hedged legacy stats. Every value
    carries a `basis` label — 'kb_verified' cite plainly, 'kb_reported' hedge
    as unverified, 'opinion' present as counselor take; null means the school
    doesn't publish it (never estimate). IMPORTANT: is_impacted:false does
    NOT mean easy to enter (use entry_risk), and at schools that admit by
    university rather than by major, say the listed major barely affects
    admission instead of over-strategizing. `college`/`query` filter by
    college or major-name substring (use for big schools). Free — no credit."""
    return sc.get_university_majors(university_id, college=college, query=query)


@mcp.tool(annotations=ToolAnnotations(title="List the major catalog", readOnlyHint=True, openWorldHint=True))
def list_major_catalog(query: str | None = None, limit: int = 200) -> dict:
    """The catalog of majors that actually exist across Stratia's whole
    university knowledge base — every distinct major with how many schools
    offer it (offered_count), most-offered first. Use it to ground
    major suggestions in real, offered programs (not invented names), or to
    see how common/rare a major is. `query` filters by name; free, no credit."""
    return sc.list_major_catalog(query=query, limit=limit)


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
def recompute_fit(university_id: str, major: str | None = None) -> dict:
    """Recompute the student's college-fit analysis for one university against
    the latest knowledge-base data. Pass `major` to compute the fit for a
    specific major at this school; otherwise the saved per-school
    major_choice applies, then the profile's intended_major. The fit doc
    records intended_major_used. Costs 1 Stratia credit, deducted by the
    server on success (fails clearly when the balance is 0). Budget before
    spending: get_credits shows the balance; check_fit_recomputation shows
    which fits are stale and worth recomputing."""
    email = _email()
    # Tighter limit — this spends a credit and calls the LLM.
    _rate_guard(email, "recompute", settings.RATE_RECOMPUTE_PER_HOUR, 3600)
    return sc.recompute_fit(email, university_id, major=major)


@mcp.tool(annotations=ToolAnnotations(
    title="Set my intended majors", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def set_intended_majors(majors: list[str], primary: str | None = None) -> dict:
    """Persist the student's ranked candidate majors (max 5, deduped).
    `primary` (default: the first item) becomes the profile's intended_major
    and drives fit computation. Use after agreeing the candidate set with the
    student — e.g. at the end of a major-discovery conversation."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.set_intended_majors(email, majors, primary=primary)


@mcp.tool(annotations=ToolAnnotations(
    title="Set my major choice at a school", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def set_major_choice(university_id: str, primary_major: str,
                     backup_major: str | None = None,
                     rationale: str | None = None) -> dict:
    """Record which major the student will LIST at one school (plus an
    on-campus backup and a one-line why). Pass the school's exact major name
    from get_university_majors; only exact/strong matches auto-canonicalize —
    an unmatched name is stored flagged matched:false with near_misses
    returned, so confirm fuzzy names with the student before relying on them.
    Shown on the Launchpad card and used the next time this school's fit is
    recomputed. The school must already be on the college list."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    source, _model = _client_attribution()
    return sc.set_major_choice(email, university_id, primary_major,
                               backup_major=backup_major, rationale=rationale,
                               source=source)


@mcp.tool(annotations=ToolAnnotations(
    title="Get my Major Map", readOnlyHint=True, openWorldHint=True))
def get_major_map() -> dict:
    """The student's saved Major Map: 3-6 career-theme clusters built from
    their OWN record (courses/APs/activities/awards cited as evidence), each
    listing candidate majors tagged core / adjacent / strategic_alternative
    with a generic watch_out, plus questions_to_explore. This is counselor
    INFERENCE, not school facts — never present it as data about any
    university. stale:true means the profile changed since generation (see
    stale_reasons); mention it, but only regenerate (generate_major_map,
    1 credit) if the student wants a refresh. Free — no credit."""
    return sc.get_major_map(_email())


@mcp.tool(annotations=ToolAnnotations(
    title="Generate my Major Map (uses 1 credit)", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def generate_major_map(force: bool = False) -> dict:
    """Generate (or refresh) the student's Major Map from their profile —
    persisted in the app's Profile page. Costs 1 Stratia credit, deducted by
    the server on success: CONFIRM with the student first and check
    get_credits. An unchanged profile returns the saved map free
    (force=true regenerates anyway). Requires grade plus at least two of
    courses/activities/GPA on the profile — otherwise it fails clearly,
    unbilled (build the profile first via update_student_profile). The map is
    pure counselor inference citing the student's own record; it never makes
    school-specific claims or states numbers absent from the profile — keep
    that discipline when you discuss it."""
    email = _email()
    # Tighter limit — this spends a credit and calls the LLM.
    _rate_guard(email, "recompute", settings.RATE_RECOMPUTE_PER_HOUR, 3600)
    return sc.generate_major_map(email, force=force)


@mcp.tool(annotations=ToolAnnotations(
    title="Get my major strategy for a school", readOnlyHint=True, openWorldHint=True))
def get_major_strategy(university_id: str) -> dict:
    """The student's saved per-school major strategy: the trust-labeled KB
    fact extract it was built on (facts), Stratia's read (synthesis:
    primary_call, second_choice_play, backup_rationale, undeclared_tactic,
    essay_implication, what_to_verify_yourself), and data_notes (including
    any numeric claims the anti-fabrication validator stripped). The
    synthesis is counselor judgment over labeled facts — hedge anything
    [REPORTED], treat [MISSING] as 'the school doesn't publish this', and
    relay data_notes as caveats. stale:true = the KB now has newer data than
    this strategy was built on. Free — no credit."""
    return sc.get_major_strategy(_email(), university_id)


@mcp.tool(annotations=ToolAnnotations(
    title="Generate major strategy for a school (uses 1 credit)", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def generate_major_strategy(university_id: str,
                            majors: list[str] | None = None) -> dict:
    """Generate the app-persisted major strategy for ONE school. Costs 1
    Stratia credit on success — CONFIRM with the student and check
    get_credits first. PREFER reasoning over get_university_majors facts
    yourself in conversation; reserve this tool for when the student wants
    the artifact saved in the app (it renders on their Fit Analysis Majors
    tab). `majors` (max 4) overrides the default set (the school's saved
    major_choice + the profile's intended majors). When the KB has no
    entry-path data for those majors the response is {strategy: null,
    gaps: [...]} and the student is NOT charged — relay that honestly (the
    gap is queued for collection); never invent a strategy to fill it. The
    synthesis warns on capped_door majors (the door locks — no
    apply-easier-then-transfer plays) and a server-side validator strips any
    number the KB extract doesn't contain."""
    email = _email()
    # Tighter limit — this spends a credit and calls the LLM.
    _rate_guard(email, "recompute", settings.RATE_RECOMPUTE_PER_HOUR, 3600)
    return sc.generate_major_strategy(email, university_id, majors=majors)


@mcp.tool(annotations=ToolAnnotations(
    title="Get my Major Chances for a school", readOnlyHint=True, openWorldHint=True))
def get_college_major_chances(university_id: str) -> dict:
    """The student's saved per-college Major Chances: the majors THIS school
    actually offers that fit them, ranked into likelihood TIERS (ranking.tiers:
    strong / possible / reach / long_shot) with a rationale each, plus
    entry_path / entry_risk per major and any reported (unverified) rate the KB
    holds. These are counselor-judgment tiers over the school's real offered
    catalog — NOT fabricated admit percentages, and never invent one. stale:true
    = the KB now has newer data than this ranking was built on. Free — no
    credit."""
    return sc.get_college_major_chances(_email(), university_id)


@mcp.tool(annotations=ToolAnnotations(
    title="Rank my chances across a school's majors (uses 1 credit)", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def rank_college_majors(university_id: str) -> dict:
    """Rank the majors ONE school actually offers that fit the student into
    likelihood TIERS (strong / possible / reach / long_shot) with a rationale
    each — persisted in the app's Major Chances view. Costs 1 Stratia credit on
    success — CONFIRM with the student and check get_credits first. The ranking
    scans the school's FULL offered catalog (so strategic/adjacent doors surface)
    but shows only the majors that fit; likelihood is a TIER, never a fabricated
    percentage. When the KB has no major data for the school the response is
    {ranking: null, gaps: [...]} and the student is NOT charged — relay that
    honestly (the gap is queued for collection); never invent a ranking. A
    server-side validator strips any number the KB extract doesn't contain, and
    capped_door majors are ranked honestly (reach/long_shot) with the door-lock
    caveat."""
    email = _email()
    # Tighter limit — this spends a credit and calls the LLM.
    _rate_guard(email, "recompute", settings.RATE_RECOMPUTE_PER_HOUR, 3600)
    return sc.rank_college_majors(email, university_id)


@mcp.tool(annotations=ToolAnnotations(
    title="Get the analysis save-schema", readOnlyHint=True, openWorldHint=True))
def get_analysis_schema(kind: Literal["fit", "major_chances"]) -> dict:
    """The exact shape + trust_rules for an analysis you compute yourself and
    save for FREE (vs the in-app Generate at 1 credit each). Call this BEFORE
    save_fit_analysis / save_major_chances so your payload matches and you
    understand which fields the server RE-DERIVES server-side (and therefore
    ignores from you): for 'fit' the category is floored by the school's KB
    selectivity and match% is clamped; for 'major_chances' entry_path/entry_risk
    come from the KB, off-catalog names are dropped, fabricated numbers are
    stripped. Free — no credit."""
    return sc.get_analysis_schema(kind)


@mcp.tool(annotations=ToolAnnotations(
    title="Save a fit analysis I computed (free)", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def save_fit_analysis(university_id: str, fit_analysis: dict) -> dict:
    """Save a college-fit analysis YOU computed into the student's app — FREE
    (0 credits), the credit-saving alternative to the in-app Generate (1 credit).
    Compute it honestly from get_profile + get_university, then save it here.
    Call get_analysis_schema('fit') first for the exact shape. The server
    re-applies the selectivity floor/ceiling and match%/factor clamps and sources
    acceptance_rate + KB provenance from the knowledge base — so a category that
    violates the school's selectivity is corrected, and fabricated numbers are
    rejected. Validation errors are relayed field-by-field so you can fix and
    retry."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    source, _model = _client_attribution()
    return sc.save_fit_analysis(email, university_id, fit_analysis, source=source)


@mcp.tool(annotations=ToolAnnotations(
    title="Save major chances I computed (free)", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def save_major_chances(university_id: str, ranking: dict) -> dict:
    """Save a per-college major-chances ranking YOU computed into the student's
    app — FREE (0 credits), the credit-saving alternative to the in-app Generate
    (rank_college_majors, 1 credit). Scan the school's real offered catalog
    (get_university_majors), select the majors that fit the student, and rank
    each into a likelihood tier. `ranking` is
    {"majors": [{"name", "tier": strong|possible|reach|long_shot, "rationale"}]}
    — call get_analysis_schema('major_chances') first for the exact shape. The
    server re-derives entry_path/entry_risk from the KB, DROPS any major the
    school doesn't offer, strips any %/GPA the KB doesn't contain, applies the
    capped_door door-lock, and coerces tiers — so a saved ranking is
    trust-identical to the in-app one. A school with no KB majors is rejected."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    source, _model = _client_attribution()
    return sc.save_major_chances(email, university_id, ranking, source=source)


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


@mcp.tool(annotations=ToolAnnotations(
    title="Build/update my student profile", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def update_student_profile(profile: dict, source: str = "agent-import",
                           source_text: str | None = None) -> dict:
    """Create or update the student's Stratia profile in ONE call by passing a
    structured `profile` object. Use this to build a profile from a document the
    student shared (transcript, résumé, brag sheet, Common App activities, etc.):
    read the document, extract every field present, and pass them here. It MERGES
    into any existing profile (new non-null values win; list items are
    de-duplicated) — safe to call repeatedly and to enrich over time.

    `profile` fields (include only what you found; use null/omit when unknown):
      name, school, location: strings
      grade: "9"|"10"|"11"|"12"; graduation_year: int; intended_major: string
      gpa_weighted, gpa_unweighted, gpa_uc: float; class_rank: "15/400"
      sat_total, sat_math, sat_reading, act_composite: int
      ap_exams: [{subject, score (1-5)}]
      courses: [{name, type: AP|Honors|IB|Regular, grade_level (9-12),
                 semester1_grade, semester2_grade}]
      extracurriculars: [{name, role, description, grades (e.g. "9-12"),
                          hours_per_week, achievements: [str]}]
      leadership_roles: [str]
      special_programs: [{name, description, grade}]
      awards: [{name, grade, description}]
      work_experience: [{employer, role, grades, hours_per_week, description}]

    `source` is a short label for where the data came from (e.g. the file name);
    pass the document's plain text as `source_text` to keep it on record.
    Returns the merged profile. Extract thoroughly — don't summarize."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    if not isinstance(profile, dict) or not profile:
        raise ValueError("profile must be a non-empty object of profile fields")
    return sc.update_student_profile(email, profile, source=source, source_text=source_text)


@mcp.tool(annotations=ToolAnnotations(
    title="Record an admission decision", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def set_application_status(university_id: str, decision: str | None = None,
                           status: str | None = None) -> dict:
    """Record the real-world OUTCOME (and/or process status) for a college on the
    student's list. This powers the Decision Ledger, which grades Stratia's fit
    predictions against what actually happened.

    `decision` = the admission outcome: 'accepted', 'waitlisted', 'denied',
    'deferred', or 'enrolled' (synonyms like 'admitted'/'rejected' are accepted;
    pass an empty string to clear). `status` = the optional application PROCESS
    state ('planning', 'in_progress', 'submitted', 'decision_pending') — kept
    SEPARATE from the decision. Provide at least one. The college must already be
    on the student's list (use add_college first if needed)."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.set_application_status(email, university_id, decision=decision, status=status)


@mcp.tool(annotations=ToolAnnotations(
    title="Decision Ledger (predicted vs actual)", readOnlyHint=True, openWorldHint=True))
def get_outcome_calibration() -> dict:
    """How Stratia's fit predictions compare to real admission decisions. Returns
    each college with its predicted fit category and the recorded decision, plus
    counts — so you can tell the student how calibrated their list was (e.g.
    "Stratia called Michigan a Target and you got in; Cornell was a Reach and you
    were waitlisted"). Read-only."""
    email = _email()
    return sc.get_outcome_calibration(email)


# ---------------------------------------------------------------------------
# Research notebook — save the analysis you do here back into the student's app
# so it's tracked, linked to their colleges, and readable in a later session.
# ---------------------------------------------------------------------------

@mcp.tool(annotations=ToolAnnotations(
    title="Save research to my notebook", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def save_research(title: str, body_markdown: str, kind: str = "note",
                  summary: str = "", university_ids: list[str] | None = None,
                  tags: list[str] | None = None, kb_year: int | None = None,
                  source_prompt: str | None = None,
                  workflow: list[dict] | None = None) -> dict:
    """Save a piece of research/analysis to the student's Stratia Research
    Notebook so it persists in the app. Use this whenever you produce something
    worth keeping — a college comparison, an application timeline, essay angles,
    a scholarship plan, a school deep-dive, or an overall strategy.

    - `kind`: one of comparison | timeline | essay_angle | scholarship |
      school_deep_dive | strategy | weekly_plan | note (defaults to note). Use
      `weekly_plan` for a short "what to do this week" note (<=3 next actions
      from the student's deadlines + roadmap) — the app pins the newest one to
      the top of the Research Notebook as a "This week" card.
    - `body_markdown`: the full analysis in Markdown.
    - `summary`: a one-line TL;DR shown in the notebook feed.
    - `university_ids`: ids of the colleges this is about, to link it to their
      cards (use ids from get_college_list / search_universities).
    - `kb_year`: the knowledge-base admission cycle your analysis was based on
      (e.g. 2026) so the app can flag the note if newer data arrives later.

    ALSO capture how you produced this, so the student can repeat it later:
    - `source_prompt`: the student's original request in their own voice
      (e.g. "Compare Duke and UCSD for CS and tell me which is more realistic").
    - `workflow`: the ordered steps you ran, each as
      {"tool": "<tool name>", "label": "<short human description>"} — e.g.
      [{"tool":"get_profile","label":"Pulled my profile"},
       {"tool":"get_fit_analysis","label":"Got Duke & UCSD fit"}]. Keep labels
      short and PII-free (describe the step, don't dump data).

    Returns the new research_id and the stored record."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    source, model = _client_attribution()
    return sc.save_research(email, title, body_markdown, kind=kind, summary=summary,
                            university_ids=university_ids, tags=tags, kb_year=kb_year,
                            source=source, model=model,
                            source_prompt=source_prompt, workflow=workflow)


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


# --- Research notebook: analysis over the whole notebook (#236) -----------------

@mcp.tool(annotations=ToolAnnotations(
    title="Search my research notes", readOnlyHint=True, openWorldHint=True))
def search_research(query: str, kind: str | None = None,
                    university_id: str | None = None, limit: int = 10) -> dict:
    """Keyword-search the student's saved research notes by relevance (title,
    summary, body, tags) and return the best matches with a snippet. Use this to
    recall and build on earlier analysis BEFORE producing new work — e.g. search
    "Duke essay" or "scholarship" to find what's already been done. Optionally
    filter by `kind` or a linked `university_id`."""
    return sc.search_research(_email(), query, kind=kind,
                              university_id=university_id, limit=limit)


@mcp.tool(annotations=ToolAnnotations(
    title="Get all my research", readOnlyHint=True, openWorldHint=True))
def get_all_research(full: bool = True, offset: int = 0, limit: int = 20) -> dict:
    """The whole Research Notebook in one call, for cross-note analysis or
    synthesis (e.g. "pull everything into one application strategy"). Bodies are
    trimmed and results paginated — when `has_more` is true, call again with a
    higher `offset`. `full=false` returns metadata only (lighter)."""
    return sc.get_all_research(_email(), full=full, offset=offset, limit=limit)


@mcp.tool(annotations=ToolAnnotations(
    title="Research notebook overview", readOnlyHint=True, openWorldHint=True))
def research_overview() -> dict:
    """A bird's-eye view of the notebook: total notes, counts by kind and by
    college, how many are stale, how many pinned, which kinds are missing, and
    when it was last updated. Use to orient yourself and suggest what to research
    next (e.g. "you have deep-dives but no application timeline")."""
    return sc.research_overview(_email())


@mcp.tool(annotations=ToolAnnotations(
    title="List stale research", readOnlyHint=True, openWorldHint=True))
def list_stale_research() -> dict:
    """Research notes based on an OLDER admissions-data cycle than the current
    one — candidates to refresh against current data. Use to offer the student a
    refresh of outdated analysis."""
    return sc.list_stale_research(_email())


@mcp.tool(annotations=ToolAnnotations(
    title="Pin a research note", readOnlyHint=False,
    destructiveHint=False, idempotentHint=True, openWorldHint=True))
def pin_research(research_id: str, pinned: bool = True) -> dict:
    """Pin (or unpin, with pinned=false) a research note so it surfaces first in
    the notebook and as your primary context — e.g. pin the master strategy."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.pin_research(email, research_id, pinned=pinned)


@mcp.tool(annotations=ToolAnnotations(
    title="Turn research into roadmap tasks", readOnlyHint=False,
    destructiveHint=False, idempotentHint=False, openWorldHint=True))
def research_to_tasks(research_id: str, tasks: list[dict]) -> dict:
    """Create roadmap tasks from a research note's recommendations so research
    becomes action. Read the note (get_research), derive the concrete next steps,
    and pass them as `tasks` — each item needs a `title` and may include
    `description`, `university_id`, `due_date` (YYYY-MM-DD). Each task is added to
    the student's roadmap linked back to the note via `source_research_id`."""
    email = _email()
    _rate_guard(email, "write", settings.RATE_WRITES_PER_MIN, 60)
    return sc.research_to_tasks(email, research_id, tasks)


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


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_root(_request: Request):
    """Back-compat: the canonical protected-resource metadata lives at
    /.well-known/oauth-protected-resource/mcp (path-appended per RFC 9728 §3.1,
    which the SDK serves once resource_server_url carries the /mcp path). Some
    clients still probe the bare well-known — serve the SAME doc here so none
    regress. `resource` is the canonical …/mcp URL either way, so a client that
    discovered metadata at this path still finds a matching resource."""
    return JSONResponse({
        "resource": settings.mcp_resource(),
        # Normalize exactly as the SDK's canonical /mcp-path doc does (AnyHttpUrl
        # adds the trailing slash) so the two well-knowns are byte-consistent.
        "authorization_servers": [str(AnyHttpUrl(settings.PUBLIC_BASE_URL))],
        "scopes_supported": [settings.MCP_SCOPE],
        "bearer_methods_supported": ["header"],
    })


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
