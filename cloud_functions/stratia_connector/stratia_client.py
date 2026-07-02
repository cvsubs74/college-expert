"""Thin HTTP client over the Stratia backend services (counselor_agent,
profile_manager_v2, knowledge_base_manager_universities_v2).

Uses `requests` (already a repo/runtime dep). Every per-user call is made on
behalf of a verified `email` — the connector supplies it; the backends trust it.

Design: the backends already return rich data. Rather than allow-listing a few
fields (which lost most of it), each tool returns EVERYTHING via `_prune`
(drops internal/embedding/housekeeping keys, caps runaway lists/strings) and a
final `_cap_size` guard so results stay under Claude's ~150k-char tool limit.
"""
import datetime as _dt
import json
import logging
import time

import requests

from settings import settings

logger = logging.getLogger("stratia_connector.client")


class StratiaError(RuntimeError):
    """A backend call failed or returned an error payload."""


# Keys stripped from every payload: vector embeddings, staleness internals,
# Firestore/profile housekeeping, and raw document blobs.
_DENY = {
    "embedding", "vector", "input_snapshot", "deadlines_hash",
    "needs_fit_recomputation", "last_change_reason", "chunk_id",
    "user_id", "_id",
}

_RESULT_CAP = 120_000  # chars; safety net under Claude.ai's ~150k tool-result cap


def _prune(obj, list_caps=None, text_caps=None, deny=None, _key=None):
    """Recursively drop deny-listed / `_`-prefixed / `*_embedding` keys and
    apply per-key list and string caps. Returns a clean, bounded copy."""
    list_caps = list_caps or {}
    text_caps = text_caps or {}
    deny = _DENY | (deny or set())

    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in deny or k.startswith("_") or k.endswith("_embedding"):
                continue
            out[k] = _prune(v, list_caps, text_caps, deny, _key=k)
        return out
    if isinstance(obj, list):
        cap = list_caps.get(_key)
        items = obj[:cap] if cap else obj
        return [_prune(x, list_caps, text_caps, deny) for x in items]
    if isinstance(obj, str):
        cap = text_caps.get(_key)
        return obj[:cap] if (cap and len(obj) > cap) else obj
    return obj


def _cap_size(d, droppable=(), limit=_RESULT_CAP):
    """If the serialized dict exceeds `limit`, drop the largest `droppable`
    top-level sections (in order) until it fits, recording what was dropped."""
    if len(json.dumps(d, default=str)) <= limit:
        return d
    dropped = []
    for key in droppable:
        if key in d:
            d.pop(key, None)
            dropped.append(key)
            if len(json.dumps(d, default=str)) <= limit:
                break
    if dropped:
        d["_truncated"] = dropped
    return d


# ---- outbound service identity (#223) --------------------------------------
# The backends verify callers now: this connector attaches a Google OIDC ID
# token minted by its Cloud Run runtime service account, audience-bound to
# the backend it is calling. The backends recognize the runtime SA
# (TRUSTED_SERVICE_EMAILS) and then honor the X-User-Email this connector
# forwards — the human was already verified here via Google OAuth.
_SVC_TOKEN_TTL_SECONDS = 55 * 60  # tokens live 1h; refresh with slack
_svc_token_cache = {}  # audience -> (token, fetched_at_monotonic)


def _audience_for(url):
    """The configured base URL of the service this url belongs to — the
    audience the backend expects (never a bare host: Cloud Functions URLs
    include the function path)."""
    for base in (settings.PROFILE_MANAGER_V2_URL,
                 settings.COUNSELOR_AGENT_URL,
                 settings.KNOWLEDGE_BASE_UNIVERSITIES_URL):
        base = (base or '').rstrip('/')
        if base and url.startswith(base):
            return base
    return None


def _svc_auth_headers(url):
    """{'Authorization': 'Bearer <oidc>'} for backend calls, {} when no
    runtime credentials exist (local dev/tests). Never raises — the
    backend's AUTH_MODE decides what a missing credential means."""
    audience = _audience_for(url)
    if not audience:
        return {}
    cached = _svc_token_cache.get(audience)
    now = time.monotonic()
    if cached and now - cached[1] < _SVC_TOKEN_TTL_SECONDS:
        return {"Authorization": f"Bearer {cached[0]}"}
    try:
        # Lazy import: full-suite test runs stub the `google` package.
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
        token = google_id_token.fetch_id_token(google_requests.Request(), audience)
        _svc_token_cache[audience] = (token, now)
        return {"Authorization": f"Bearer {token}"}
    except Exception as e:  # noqa: BLE001 — metadata server absent locally
        logger.info(f"no service identity token available for {audience}: {e}")
        return {}


def _get(url, params=None, timeout=30):
    try:
        r = requests.get(url, params=params, timeout=timeout,
                         headers={"X-User-Email": (params or {}).get("user_email", ""),
                                  **_svc_auth_headers(url)})
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise StratiaError(f"request to {url} failed: {e}") from e


def _post(url, body, timeout=30, email=None):
    try:
        r = requests.post(url, json=body, timeout=timeout,
                         headers={"X-User-Email": email or body.get("user_email", ""),
                                  **_svc_auth_headers(url)})
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        err = StratiaError(f"request to {url} failed: {e}")
        # Attach the HTTP status + parsed body (when available) so callers can
        # react to specific statuses — recompute_fit reads 402
        # insufficient_credits (#285) — without changing the exception type
        # every other caller already catches.
        resp = getattr(e, "response", None)
        err.status_code = getattr(resp, "status_code", None)
        try:
            err.body = resp.json() if resp is not None else None
        except Exception:
            err.body = None
        raise err from e


def _pm(path):
    return f"{settings.PROFILE_MANAGER_V2_URL}/{path}"


# ----------------------------------------------------------------------------
# Knowledge base (no user identity required)
# ----------------------------------------------------------------------------

def search_universities(query, limit=10, max_acceptance_rate=None, state=None):
    # KB keyword search is the GET ?search= endpoint (POST {query} is the
    # offline semantic variant). Kept lean — a list view; use get_university for depth.
    params = {"search": query, "limit": int(limit)}
    if max_acceptance_rate is not None:
        params["max_acceptance"] = max_acceptance_rate
    if state:
        params["state"] = state
    data = _get(settings.KNOWLEDGE_BASE_UNIVERSITIES_URL, params)
    out = []
    for u in (data.get("universities") or [])[:limit]:
        out.append({
            "university_id": u.get("university_id"),
            "name": u.get("official_name") or u.get("name"),
            "location": u.get("location"),
            "acceptance_rate": u.get("acceptance_rate"),
            "us_news_rank": u.get("us_news_rank"),
            "soft_fit_category": u.get("soft_fit_category"),
            "summary": (u.get("summary") or "")[:600],
        })
    return out


# Per-key list caps applied to KB profile payloads (shared by get_university
# and the sections mode of get_university_history — _prune caps match by key
# name at any depth, so they hold inside per-year maps too).
_KB_PROFILE_LIST_CAPS = {
    "scholarships": 40, "majors": 60, "application_deadlines": 30,
    "supplemental_requirements": 30, "longitudinal_trends": 8,
}


def get_university(university_id, year=None, sections=None):
    """Full KB profile — all sections (admissions, academics, financials,
    application process, outcomes, student life, strategic profile, ...).
    `year` reads that cycle's snapshot; `sections` projects the profile
    server-side to just those top-level sections."""
    params = {"university_id": university_id}
    if year is not None:
        params["year"] = int(year)
    if sections:
        params["sections"] = ",".join(sections)
    data = _get(settings.KNOWLEDGE_BASE_UNIVERSITIES_URL, params)
    if not data.get("success") or not data.get("university"):
        # Surface the backend's own message — it names a missing year and
        # lists the available ones, so the agent can self-correct in one step.
        raise StratiaError(data.get("error") or f"university '{university_id}' not found")
    u = data["university"]
    out = {
        "university_id": u.get("university_id"),
        "name": u.get("official_name"),
        "location": u.get("location"),
        "acceptance_rate": u.get("acceptance_rate"),
        "us_news_rank": u.get("us_news_rank"),
        "soft_fit_category": u.get("soft_fit_category"),
        "market_position": u.get("market_position"),
        "data_year": u.get("data_year"),
        "available_years": u.get("available_years"),
    }
    # Projection metadata (present only when sections were requested) lets
    # the agent distinguish "school lacks this section" from a typo.
    for k in ("sections_returned", "sections_available", "unknown_sections"):
        if u.get(k) is not None:
            out[k] = u[k]
    # Merge the full profile (every KB section), pruned + list-capped.
    out.update(_prune(u.get("profile") or {}, list_caps=_KB_PROFILE_LIST_CAPS))
    # KB docs are large; drop the bulkiest low-value sections only if over cap.
    return _cap_size(out, droppable=(
        "longitudinal_trends", "admitted_student_profile", "student_insights", "outcomes",
    ))


def get_university_majors(university_id, college=None, query=None, year=None):
    """Trust-labeled per-major entry facts (KB action=majors): entry_path enum
    (+ verbatim wording when unclear), structural entry_risk, door policy,
    hedged legacy stats, richness_tier, data_notes. Deterministic and free."""
    params = {"university_id": university_id, "action": "majors"}
    if college:
        params["college"] = college
    if query:
        params["q"] = query
    if year is not None:
        params["year"] = int(year)
    data = _get(settings.KNOWLEDGE_BASE_UNIVERSITIES_URL, params)
    if not data.get("success"):
        raise StratiaError(data.get("error") or f"majors unavailable for '{university_id}'")
    if "colleges" not in data:
        # Deploy skew: an older KB ignores unknown actions and returns a full
        # profile with success:true — refuse to mis-parse it.
        raise StratiaError(
            "the knowledge base does not support action=majors yet — "
            "use get_university(sections=['academic_structure','application_strategy'])"
        )
    out = {k: data.get(k) for k in (
        "university_id", "official_name", "data_year", "verification_status",
        "richness_tier", "structure_type", "colleges", "strategy_notes", "data_notes")}
    out = _prune(out, list_caps={"majors": 80, "colleges": 25,
                                 "prerequisite_courses": 10,
                                 "major_selection_tactics": 10})
    out["guidance"] = (
        "basis 'kb_verified' = quote-backed official data; 'kb_reported' = "
        "unverified legacy data — hedge it ('students report…'); 'opinion' = "
        "counselor take, present as judgment. Absent/null = the school doesn't "
        "publish it — never estimate. is_impacted:false does NOT mean easy to "
        "enter — use entry_risk ('capped_door' means the door locks behind you: "
        "warn the student, never recommend an apply-easier-transfer-later play "
        "there). At schools whose colleges admit by university (not by major), "
        "the listed major barely affects admission — say so instead of "
        "over-strategizing; the application and essays must cohere with "
        "whatever major is listed."
    )
    return _cap_size(out, droppable=("strategy_notes",))


def get_university_history(university_id, sections=None, years=None):
    """Year-by-year view of one university. Compact per-cycle rows plus the
    school's own reported trend series by default; raw per-year sections when
    `sections` is passed (oldest years evicted first if oversized)."""
    params = {"university_id": university_id, "action": "history"}
    if sections:
        params["sections"] = ",".join(sections)
    if years:
        params["years"] = ",".join(str(int(y)) for y in years)
    data = _get(settings.KNOWLEDGE_BASE_UNIVERSITIES_URL, params)
    if not data.get("success"):
        raise StratiaError(data.get("error") or f"history unavailable for '{university_id}'")
    if "snapshots" not in data and "years" not in data:
        # Deploy skew / rollback: an older KB ignores unknown actions and
        # returns a full profile with success:true. Never mis-parse that.
        raise StratiaError(
            "the knowledge base does not support action=history yet — "
            "use get_university(year=...) instead"
        )
    out = {
        "university_id": university_id,
        "name": data.get("official_name"),
        "available_years": data.get("available_years"),
        "notes": data.get("notes") or [],
    }
    if "years" in data:  # sections mode
        year_map = {y: _prune(secs, list_caps=_KB_PROFILE_LIST_CAPS)
                    for y, secs in (data.get("years") or {}).items()}
        out["years"] = year_map

        def _as_int(y):
            try:
                return int(y)
            except (TypeError, ValueError):
                return -1

        # Evict oldest years first until under cap; never drop the newest.
        truncated = []
        while (len(json.dumps(out, default=str)) > _RESULT_CAP and len(year_map) > 1):
            oldest = min(year_map, key=_as_int)
            year_map.pop(oldest)
            truncated.append(oldest)
        if truncated:
            out["truncated_years"] = sorted(truncated)
        # A single remaining year can still exceed the cap (one broad-section
        # year of a 150KB profile) — drop its largest sections until it fits,
        # recording them so the agent can re-request narrower sections.
        if len(json.dumps(out, default=str)) > _RESULT_CAP and year_map:
            (year, secs), = year_map.items()
            dropped = []
            while len(json.dumps(out, default=str)) > _RESULT_CAP and len(secs) > 1:
                largest = max(secs, key=lambda k: len(json.dumps(secs[k], default=str)))
                secs.pop(largest)
                dropped.append(largest)
            if dropped:
                out["truncated_sections"] = {year: sorted(dropped)}
        return out

    out["snapshots"] = _prune(data.get("snapshots") or [],
                              list_caps={"deadlines": 20, "early_admission": 8})
    out["reported_trends"] = _prune(data.get("reported_trends") or [])[:12]
    return _cap_size(out, droppable=("reported_trends",))


# ----------------------------------------------------------------------------
# Per-user reads
# ----------------------------------------------------------------------------

def get_college_list(email):
    data = _get(_pm("get-college-list"), {"user_email": email})
    out = []
    for c in (data.get("college_list") or []):
        fa = c.get("fit_analysis") or {}
        out.append({
            "university_id": c.get("university_id"),
            "name": c.get("university_name"),
            "status": c.get("status"),
            "application_status": c.get("application_status"),
            "category": c.get("category"),
            "soft_fit_category": c.get("soft_fit_category"),
            # Personalized band now comes top-level from the enriched endpoint;
            # fall back to a nested fit_analysis for older response shapes.
            "fit_category": c.get("fit_category") or fa.get("fit_category"),
            "match_percentage": (c.get("match_percentage")
                                 or fa.get("match_percentage") or fa.get("match_score")),
            "selected_major": c.get("selected_major"),
            "notes": c.get("notes"),
            "location": c.get("location"),
            "acceptance_rate": c.get("acceptance_rate") or fa.get("acceptance_rate"),
            "us_news_rank": c.get("us_news_rank") or fa.get("us_news_rank"),
            "added_at": c.get("added_at"),
        })
    return out


def get_fit_analysis(email, university_id):
    """The COMPLETE fit analysis — everything the UI's tabs render."""
    data = _get(_pm("get-fit-analysis"), {"user_email": email, "university_id": university_id}) or {}
    # The single get-fit-analysis endpoint returns the fit dict DIRECTLY; some
    # paths wrap it as {fit_analysis: ...}. Accept either.
    fit = data.get("fit_analysis") if isinstance(data, dict) and "fit_analysis" in data else data
    if not isinstance(fit, dict) or not fit.get("fit_category"):
        raise StratiaError(f"no fit analysis for '{university_id}' — try recompute_fit")
    fit.setdefault("university_id", university_id)
    return _prune(
        fit,
        list_caps={"recommendations": 15, "essay_angles": 15,
                   "scholarship_matches": 30, "factors": 12},
        text_caps={"explanation": 6000},
        deny={"computed_at"},  # keep calculated_at / kb_* provenance; drop the alias
    )


def get_fit_history(email, university_id):
    """Prior-cycle fit analyses for one university (how the score evolved)."""
    data = _get(_pm("get-fit-history"), {"user_email": email, "university_id": university_id})
    hist = _prune(data.get("history") or [], list_caps={"history": 20})
    return {"university_id": university_id, "history": hist[:20]}


def get_deadlines(email):
    data = _post(f"{settings.COUNSELOR_AGENT_URL}/deadlines", {"user_email": email}, email=email)
    return [
        {"university": d.get("university_name") or d.get("university_id"),
         "university_id": d.get("university_id"),
         "deadline_type": d.get("deadline_type"), "date": d.get("date"),
         "is_binding": d.get("is_binding")}
        for d in (data.get("deadlines") or [])
    ]


def get_profile(email):
    """The student's full academic profile (everything except raw blobs)."""
    data = _get(_pm("get-profile"), {"user_email": email})
    p = data.get("profile") or {}
    return _prune(p, deny={"raw_content", "content", "indexed_at", "filename"},
                 list_caps={"courses": 80, "extracurriculars": 40, "awards": 40,
                            "ap_exam_scores": 40, "work_experience": 30,
                            "leadership_roles": 30, "special_programs": 30})


def get_roadmap(email, status=None, university_id=None):
    """The student's roadmap tasks (what to do next)."""
    params = {"user_email": email}
    if status:
        params["status"] = status
    if university_id:
        params["university_id"] = university_id
    data = _get(_pm("get-roadmap-tasks"), params)
    return {"tasks": _prune(data.get("tasks") or [], list_caps={"tasks": 60})[:60],
            "count": data.get("count")}


def get_essays(email, university_id=None):
    """The student's essay tracker — prompts, status, drafts, word counts."""
    params = {"user_email": email}
    if university_id:
        params["university_id"] = university_id
    data = _get(_pm("get-essay-tracker"), params)
    essays = _prune(data.get("essays") or [], list_caps={"essays": 25},
                   text_caps={"content": 3000, "draft": 3000, "latest_draft": 3000})
    return {"essays": essays[:25]}


def get_aid_packages(email):
    """Saved financial-aid packages per university (net cost comparison)."""
    data = _get(_pm("get-aid-packages"), {"user_email": email})
    return {"packages": _prune(data.get("packages") or [], list_caps={"packages": 50})[:50]}


def get_scholarships(email):
    """The student's scholarship tracker (eligibility + status)."""
    data = _get(_pm("get-scholarship-tracker"), {"user_email": email})
    schol = _prune(data.get("scholarships") or [], list_caps={"scholarships": 50})
    return {"scholarships": schol[:50]}


def get_credits(email):
    """Credit balance + subscription tier (recompute_fit spends a credit)."""
    return _prune(_get(_pm("get-credits"), {"user_email": email}),
                 list_caps={"credit_history": 20, "history": 20})


def check_fit_recomputation(email):
    """Which fits are stale (profile/KB changes) and worth recomputing."""
    data = _get(_pm("check-fit-recomputation"), {"user_email": email})
    return _prune(data, list_caps={"changes": 30, "kb_updates": 40})


# ----------------------------------------------------------------------------
# Per-user safe writes
# ----------------------------------------------------------------------------

def add_college(email, university_id, name):
    data = _post(_pm("update-college-list"),
                {"user_email": email, "action": "add",
                 "university": {"id": university_id, "name": name}}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "add_college failed")
    return {"added": university_id}


def remove_college(email, university_id, name=""):
    data = _post(_pm("update-college-list"),
                {"user_email": email, "action": "remove",
                 "university": {"id": university_id, "name": name}}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "remove_college failed")
    return {"removed": university_id}


def _insufficient_credits(e, action, tip=""):
    """Shared 402 → clear budget-error shape (#285/#296): every billed tool
    (recompute_fit, generate_major_map, generate_major_strategy) surfaces the
    same honest message with the remaining balance."""
    remaining = (getattr(e, "body", None) or {}).get("credits_remaining", 0)
    return StratiaError(
        f"insufficient credits — the student has {remaining} remaining; "
        f"{action} costs 1." + (f" {tip}" if tip else "")
    )


def recompute_fit(email, university_id, major=None):
    # The recompute calls the LLM; allow more time (Claude.ai tool limit is 300s).
    # force_recompute is explicit: this tool's purpose IS recomputation, and the
    # server (#285) returns the cached fit for an explicit false. A real compute
    # costs 1 credit, deducted server-side on success.
    body = {"user_email": email, "university_id": university_id,
            "force_recompute": True}
    if isinstance(major, str) and major.strip():
        body["intended_major"] = major.strip()
    try:
        data = _post(_pm("compute-single-fit"), body, timeout=120, email=email)
    except StratiaError as e:
        if getattr(e, "status_code", None) == 402:
            raise _insufficient_credits(
                e, "recompute_fit",
                "Use get_credits for the balance and check_fit_recomputation "
                "to see which recomputes are worth it.") from e
        raise
    if not data.get("success"):
        raise StratiaError(data.get("error") or "recompute_fit failed")
    fit = data.get("fit_analysis") or {}
    fit.setdefault("university_id", university_id)
    return _prune(fit, list_caps={"recommendations": 15, "essay_angles": 15,
                                  "scholarship_matches": 30, "factors": 12},
                 text_caps={"explanation": 6000}, deny={"computed_at"})


def set_intended_majors(email, majors, primary=None):
    body = {"user_email": email, "majors": majors}
    if primary:
        body["primary"] = primary
    data = _post(_pm("set-intended-majors"), body, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "set_intended_majors failed")
    return {"intended_majors": data.get("intended_majors"),
            "primary": data.get("intended_major")}


def set_major_choice(email, university_id, primary_major, backup_major=None,
                     rationale=None, source=None):
    body = {"user_email": email, "university_id": university_id,
            "primary_major": primary_major}
    if backup_major:
        body["backup_major"] = backup_major
    if rationale:
        body["rationale"] = rationale
    if source:
        body["source"] = source
    data = _post(_pm("set-major-choice"), body, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "set_major_choice failed")
    return _prune({
        "university_id": data.get("university_id"),
        "major_choice": data.get("major_choice"),
        "near_misses": data.get("near_misses") or [],
        "note": data.get("note"),
    }, list_caps={"near_misses": 5})


# ----------------------------------------------------------------------------
# Major Map + per-school Major Strategy (#284) — billed LLM artifacts
# ----------------------------------------------------------------------------

_MAP_LIST_CAPS = {"clusters": 8, "majors": 12, "evidence": 10,
                  "questions_to_explore": 10, "stale_reasons": 8}


def get_major_map(email):
    """The student's saved Major Map + fingerprint staleness. Free."""
    data = _get(_pm("get-major-map"), {"user_email": email})
    return _prune({
        "map": data.get("map"),
        "stale": bool(data.get("stale")),
        "stale_reasons": data.get("stale_reasons") or [],
    }, list_caps=_MAP_LIST_CAPS)


def generate_major_map(email, force=False):
    """Generate (or refresh) the Major Map — 1 credit, deducted server-side on
    success. 422 profile_incomplete and 402 insufficient_credits surface as
    clear, unbilled errors; an unchanged profile returns the cached map free."""
    body = {"user_email": email, "force": bool(force)}
    try:
        data = _post(_pm("generate-major-map"), body, timeout=120, email=email)
    except StratiaError as e:
        status = getattr(e, "status_code", None)
        if status == 402:
            raise _insufficient_credits(
                e, "generate_major_map",
                "Use get_credits for the balance and confirm with the student "
                "before spending.") from e
        if status == 422:
            missing = (getattr(e, "body", None) or {}).get("missing") or []
            raise StratiaError(
                "the student's profile isn't complete enough for a Major Map — "
                f"missing: {', '.join(missing) or 'profile data'}. Add courses/"
                "activities/GPA via update_student_profile first. Nothing was charged."
            ) from e
        raise
    if not data.get("success"):
        raise StratiaError(data.get("error") or "generate_major_map failed")
    return _prune({
        "map": data.get("map"),
        "from_cache": bool(data.get("from_cache")),
        "credits_remaining": data.get("credits_remaining"),
    }, list_caps=_MAP_LIST_CAPS)


def get_major_strategy(email, university_id):
    """The student's saved per-school major strategy + KB-vintage staleness.
    Free."""
    data = _get(_pm("get-major-strategy"),
                {"user_email": email, "university_id": university_id})
    out = {
        "university_id": university_id,
        "strategy": data.get("strategy"),
        "stale": bool(data.get("stale")),
        "current_kb_year": data.get("current_kb_year"),
    }
    out = _prune(out, list_caps={"matched": 8, "related": 8, "gaps": 8,
                                 "data_notes": 12, "what_to_verify_yourself": 10},
                 text_caps={"extract": 12000})
    return _cap_size(out, droppable=())


# Per-college Major Chances (#302): the ranking's tiers are keyed lists.
_RANKING_LIST_CAPS = {"strong": 25, "possible": 25, "reach": 25,
                      "long_shot": 25, "data_notes": 12, "gaps": 12}


def get_college_major_chances(email, university_id):
    """The student's saved per-college Major Chances ranking + KB-vintage
    staleness. Free — no credit."""
    data = _get(_pm("get-college-major-chances"),
                {"user_email": email, "university_id": university_id})
    out = {
        "university_id": university_id,
        "ranking": data.get("ranking"),
        "stale": bool(data.get("stale")),
        "current_kb_year": data.get("current_kb_year"),
    }
    out = _prune(out, list_caps=_RANKING_LIST_CAPS)
    return _cap_size(out, droppable=())


def rank_college_majors(email, university_id):
    """Rank the majors ONE school actually offers that fit the student, into
    likelihood TIERS (strong/possible/reach/long_shot) with a rationale each —
    1 credit on success. A KB miss (school absent, or no majors stored) returns
    {ranking: null, gaps} UNCHARGED (the gap is logged for collection) — relay
    that honestly, never invent a ranking to fill it."""
    body = {"user_email": email, "university_id": university_id}
    try:
        data = _post(_pm("rank-college-majors"), body, timeout=120, email=email)
    except StratiaError as e:
        if getattr(e, "status_code", None) == 402:
            raise _insufficient_credits(
                e, "rank_college_majors",
                "Use get_credits for the balance and confirm with the student "
                "before spending. (A KB miss would have been free — this school "
                "HAS major data.)") from e
        raise
    if not data.get("success"):
        raise StratiaError(data.get("error") or "rank_college_majors failed")
    if data.get("ranking") is None:
        # Never-charged miss: make the honesty explicit so agents relay it.
        return {
            "university_id": university_id,
            "ranking": None,
            "gaps": data.get("gaps") or [],
            "charged": False,
            "note": data.get("note") or (
                "the knowledge base has no major data for this school — the "
                "student was NOT charged, and the gap was logged for collection. "
                "Do not invent a ranking to fill it."),
        }
    out = {
        "university_id": university_id,
        "ranking": data.get("ranking"),
        "gaps": data.get("gaps") or [],
        "charged": True,
        "credits_remaining": data.get("credits_remaining"),
    }
    out = _prune(out, list_caps=_RANKING_LIST_CAPS)
    return _cap_size(out, droppable=())


def generate_major_strategy(email, university_id, majors=None):
    """Generate the app-persisted major strategy for one school — 1 credit on
    success. A KB miss returns {strategy: null, gaps} UNCHARGED (the gap is
    logged for collection) — relay that honestly, never fill it in."""
    body = {"user_email": email, "university_id": university_id}
    if majors:
        body["majors"] = [str(m) for m in majors][:4]
    try:
        data = _post(_pm("generate-major-strategy"), body, timeout=120, email=email)
    except StratiaError as e:
        if getattr(e, "status_code", None) == 402:
            raise _insufficient_credits(
                e, "generate_major_strategy",
                "Use get_credits for the balance and confirm with the student "
                "before spending. (A KB miss would have been free — this school "
                "HAS data for these majors.)") from e
        raise
    if not data.get("success"):
        raise StratiaError(data.get("error") or "generate_major_strategy failed")
    if data.get("strategy") is None:
        # Never-charged miss: make the honesty explicit so agents relay it.
        return {
            "university_id": university_id,
            "strategy": None,
            "gaps": data.get("gaps") or [],
            "charged": False,
            "note": data.get("note") or (
                "the knowledge base has no entry-path data for these majors at "
                "this school — the student was NOT charged, and the gap was "
                "logged for collection. Do not invent a strategy to fill it."),
        }
    out = {
        "university_id": university_id,
        "strategy": data.get("strategy"),
        "gaps": data.get("gaps") or [],
        "charged": True,
        "credits_remaining": data.get("credits_remaining"),
    }
    out = _prune(out, list_caps={"matched": 8, "related": 8, "gaps": 8,
                                 "data_notes": 12, "what_to_verify_yourself": 10},
                 text_caps={"extract": 12000})
    return _cap_size(out, droppable=())


def update_profile_field(email, field_path, value, operation="set"):
    data = _post(_pm("update-structured-field"),
                {"user_email": email, "field_path": field_path,
                 "value": value, "operation": operation}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "update_profile_field failed")
    return {"updated": field_path}


# Canonical admission outcomes for the Decision Ledger. Agent-supplied synonyms
# are normalized so "admitted"/"rejected" land in the same bucket as
# "accepted"/"denied"; unknown values pass through lowercased.
_DECISION_CANON = {
    "accepted": "accepted", "accept": "accepted", "admit": "accepted",
    "admitted": "accepted", "in": "accepted",
    "waitlisted": "waitlisted", "waitlist": "waitlisted",
    "wait-listed": "waitlisted", "wl": "waitlisted",
    "denied": "denied", "deny": "denied", "reject": "denied", "rejected": "denied",
    "deferred": "deferred", "defer": "deferred",
    "enrolled": "enrolled", "committed": "enrolled", "attending": "enrolled",
}


def _normalize_decision(value):
    """Canonical decision key, or None for empty/unknown — symmetric with the
    frontend's normalizeDecision so a value one side accepts the other doesn't
    silently render blank."""
    if value is None:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    return _DECISION_CANON.get(key)


def set_application_status(email, university_id, decision=None, status=None):
    """Record an admission OUTCOME (decision) and/or process status for a college
    already on the student's list. The decision is kept separate from status.
    An empty-string decision clears it; an unrecognized one is rejected (rather
    than stored as junk that the app can't render)."""
    body = {"user_email": email, "university_id": university_id}
    if decision is not None:
        norm = _normalize_decision(decision)
        if str(decision).strip() and norm is None:
            raise StratiaError(
                f"unknown decision '{decision}' — use accepted, waitlisted, "
                "denied, deferred, or enrolled (or '' to clear)")
        body["decision"] = norm or ""   # store '' to clear, matching the app's clear path
    if status is not None:
        body["status"] = status
    if "decision" not in body and "status" not in body:
        raise StratiaError("provide a decision or a status to set")
    data = _post(_pm("update-application-status"), body, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "set_application_status failed")
    return {"updated": university_id,
            "decision": body.get("decision"), "status": body.get("status")}


def get_outcome_calibration(email):
    """Predicted (fit) vs actual (decision) for every college on the list."""
    data = _get(_pm("get-outcome-calibration"), {"user_email": email}) or {}
    return {
        "outcomes": data.get("outcomes") or [],
        "decided_count": data.get("decided_count") or 0,
        "total": data.get("total") or 0,
    }


def update_student_profile(email, profile_data, source="agent-import", source_text=None):
    """Merge a whole structured profile (scalars + arrays) into the student's
    Stratia profile in one call (create-or-update). Returns the merged profile."""
    body = {"user_email": email, "profile_data": profile_data, "source": source}
    if source_text:
        body["source_text"] = source_text
    data = _post(_pm("update-structured-profile"), body, email=email, timeout=60)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "update_student_profile failed")
    return _prune(
        data.get("profile") or {},
        deny={"raw_content", "field_sources", "indexed_at", "uploaded_files", "original_filename"},
        list_caps={"courses": 80, "extracurriculars": 40, "awards": 40,
                   "ap_exams": 40, "work_experience": 30, "leadership_roles": 30,
                   "special_programs": 30},
    )


# ----------------------------------------------------------------------------
# Research notebook — save Claude's analysis back into the app (and read it
# back so a later session can build on it).
# ----------------------------------------------------------------------------

def save_research(email, title, body_markdown, kind="note", summary="",
                  university_ids=None, tags=None, kb_year=None, research_id=None,
                  source="mcp", model="an AI agent", source_prompt=None, workflow=None):
    """Persist a research artifact to the student's Stratia notebook.

    `source`/`model` identify the MCP client that produced this — passed in by
    the server from the authenticated client's OAuth registration (#233), not
    hardcoded, so ChatGPT/Cursor/etc. saves aren't mislabeled as Claude.

    `source_prompt`/`workflow` capture how the research was produced (the user's
    original ask + the ordered steps run), powering the app's 'Repeat this
    workflow' affordance — no server-side instrumentation needed."""
    body = {
        "user_email": email, "title": title, "body_markdown": body_markdown,
        "kind": kind, "summary": summary,
        "university_ids": university_ids or [], "tags": tags or [],
        "source": source, "model": model,
    }
    if kb_year is not None:
        body["kb_year"] = kb_year
    if research_id:
        body["research_id"] = research_id
    if source_prompt:
        body["source_prompt"] = source_prompt
    if workflow:
        body["workflow"] = workflow
    data = _post(_pm("save-research"), body, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "save_research failed")
    return {"saved": data.get("research_id"), "research": _prune(data.get("research") or {})}


def list_research(email, kind=None, university_id=None):
    """The student's saved research notes (newest first), id + metadata only —
    use get_research for a note's full body."""
    params = {"user_email": email}
    if kind:
        params["kind"] = kind
    if university_id:
        params["university_id"] = university_id
    data = _get(_pm("get-research"), params)
    out = []
    for r in (data.get("research") or [])[:50]:
        out.append({
            "research_id": r.get("research_id"),
            "title": r.get("title"),
            "kind": r.get("kind"),
            "summary": r.get("summary"),
            "university_ids": r.get("university_ids"),
            "tags": r.get("tags"),
            "created_at": r.get("created_at"),
        })
    return {"research": out, "count": len(out)}


def get_research(email, research_id):
    """One research note in full (title, body, links, provenance)."""
    data = _get(_pm("get-research"), {"user_email": email, "research_id": research_id})
    r = data.get("research")
    if not r:
        raise StratiaError(f"research '{research_id}' not found")
    return _prune(r, text_caps={"body_markdown": 12000})


def update_research(email, research_id, title=None, body_markdown=None, kind=None,
                    summary=None, university_ids=None, tags=None):
    """Update fields of an existing research note (only provided fields change)."""
    body = {"user_email": email, "research_id": research_id}
    for key, val in (("title", title), ("body_markdown", body_markdown),
                     ("kind", kind), ("summary", summary),
                     ("university_ids", university_ids), ("tags", tags)):
        if val is not None:
            body[key] = val
    data = _post(_pm("update-research"), body, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "update_research failed")
    return {"updated": research_id}


def delete_research(email, research_id):
    """Delete a research note from the student's notebook."""
    data = _post(_pm("delete-research"), {"user_email": email, "research_id": research_id}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "delete_research failed")
    return {"deleted": research_id}


# ----------------------------------------------------------------------------
# Research notebook — analysis helpers over the saved notes (#236).
# The get-research list endpoint already returns FULL docs (body + provenance);
# search / get-all / overview / stale all work client-side over that one call,
# so none of these need a new backend endpoint.
# ----------------------------------------------------------------------------

_RESEARCH_KINDS = ("comparison", "timeline", "essay_angle", "scholarship",
                   "school_deep_dive", "strategy", "note")


def _all_research_docs(email):
    """Every saved note as a full doc, newest first."""
    data = _get(_pm("get-research"), {"user_email": email})
    docs = data.get("research") or []
    if isinstance(docs, dict):  # defensive: single-doc shape
        docs = [docs]
    docs.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return docs


def _current_cycle_year(now=None):
    # Mirrors frontend kbVintage.currentCycleYear: the new cycle's data lands
    # ~August, so roll forward then (month index 7 = August).
    now = now or _dt.datetime.utcnow()
    return now.year + 1 if now.month >= 8 else now.year


def _cycle_label(year):
    y = _safe_int(year)
    if y is None or y < 2000 or y > 2100:
        return None
    return f"{y}–{(y + 1) % 100:02d}"


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _kb_year(doc):
    prov = doc.get("provenance") or {}
    return prov.get("kb_year") if prov.get("kb_year") is not None else doc.get("kb_year")


def _snippet(text, terms, width=240):
    text = text or ""
    low = text.lower()
    pos = -1
    for t in terms:
        i = low.find(t)
        if i != -1 and (pos == -1 or i < pos):
            pos = i
    if pos == -1:
        return text[:width]
    start = max(0, pos - width // 3)
    end = start + width
    return ("…" if start > 0 else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def search_research(email, query, kind=None, university_id=None, limit=10):
    """Keyword-rank the student's saved notes by `query` over title/summary/
    body/tags; returns the best matches with a snippet. Use this to recall and
    build on prior analysis before producing new work."""
    terms = [t for t in (query or "").lower().split() if t]
    if not terms:
        raise StratiaError("query is required")
    scored = []
    for d in _all_research_docs(email):
        if kind and d.get("kind") != kind:
            continue
        if university_id and university_id not in (d.get("university_ids") or []):
            continue
        title = (d.get("title") or "").lower()
        summary = (d.get("summary") or "").lower()
        body = (d.get("body_markdown") or "").lower()
        tags = " ".join(d.get("tags") or []).lower()
        score = sum(5 * title.count(t) + 3 * summary.count(t) + 2 * tags.count(t) + body.count(t)
                    for t in terms)
        if score:
            scored.append((score, d))
    scored.sort(key=lambda s: s[0], reverse=True)
    matches = [{
        "research_id": d.get("research_id"), "title": d.get("title"), "kind": d.get("kind"),
        "summary": d.get("summary"), "university_ids": d.get("university_ids"),
        "tags": d.get("tags"), "created_at": d.get("created_at"), "score": score,
        "snippet": _snippet(d.get("body_markdown") or d.get("summary") or "", terms),
    } for score, d in scored[:max(1, _safe_int(limit) or 10)]]
    return {"query": query, "count": len(matches), "matches": matches}


def get_all_research(email, full=True, offset=0, limit=20):
    """The whole notebook in one call for cross-note analysis. Bodies are
    trimmed and results paginated (offset/limit + has_more) to stay under the
    tool-result size cap; full=False returns metadata only."""
    docs = _all_research_docs(email)
    total = len(docs)
    offset = max(0, _safe_int(offset) or 0)
    # Cap at 25 so even a full page of trimmed bodies (25 × 2500 ≈ 62k chars)
    # stays well under the ~120k tool-result limit; agents paginate for more.
    limit = max(1, min(_safe_int(limit) or 20, 25))
    out = []
    for d in docs[offset:offset + limit]:
        item = {
            "research_id": d.get("research_id"), "title": d.get("title"), "kind": d.get("kind"),
            "summary": d.get("summary"), "university_ids": d.get("university_ids"),
            "tags": d.get("tags"), "created_at": d.get("created_at"), "pinned": bool(d.get("pinned")),
        }
        if full:
            body = d.get("body_markdown") or ""
            item["body_markdown"] = body[:2500]
            item["body_truncated"] = len(body) > 2500
        out.append(item)
    return {"total": total, "offset": offset, "limit": limit,
            "has_more": offset + limit < total, "research": out}


def research_overview(email, now=None):
    """A bird's-eye view of the notebook: totals, coverage by kind and college,
    how much is stale, what's pinned, and which kinds are missing — use to
    orient and suggest what to research next."""
    docs = _all_research_docs(email)
    cur = _current_cycle_year(now)
    by_kind, by_college = {}, {}
    stale = pinned = 0
    last_updated = ""
    for d in docs:
        by_kind[d.get("kind") or "note"] = by_kind.get(d.get("kind") or "note", 0) + 1
        for u in (d.get("university_ids") or []):
            by_college[u] = by_college.get(u, 0) + 1
        ky = _safe_int(_kb_year(d))
        if ky is not None and ky < cur and _cycle_label(ky):
            stale += 1
        if d.get("pinned"):
            pinned += 1
        upd = d.get("updated_at") or d.get("created_at") or ""
        if upd > last_updated:
            last_updated = upd
    return {
        "total": len(docs), "by_kind": by_kind, "by_college": by_college,
        "kinds_present": [k for k in _RESEARCH_KINDS if k in by_kind],
        "kinds_absent": [k for k in _RESEARCH_KINDS if k not in by_kind],
        "stale_count": stale, "pinned_count": pinned,
        "current_cycle": _cycle_label(cur), "last_updated": last_updated,
    }


def list_stale_research(email, now=None):
    """Notes based on an older KB data cycle than the current one — candidates
    to refresh against current data."""
    cur = _current_cycle_year(now)
    out = []
    for d in _all_research_docs(email):
        ky = _safe_int(_kb_year(d))
        if ky is not None and ky < cur and _cycle_label(ky):
            out.append({
                "research_id": d.get("research_id"), "title": d.get("title"), "kind": d.get("kind"),
                "summary": d.get("summary"), "university_ids": d.get("university_ids"),
                "kb_year": ky, "cycle": _cycle_label(ky),
            })
    return {"current_cycle": _cycle_label(cur), "count": len(out), "stale": out}


def pin_research(email, research_id, pinned=True):
    """Pin (or unpin) a note so it surfaces first in the notebook and as the
    agent's primary context."""
    data = _post(_pm("update-research"),
                 {"user_email": email, "research_id": research_id, "pinned": bool(pinned)},
                 email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "pin_research failed")
    return {"research_id": research_id, "pinned": bool(pinned)}


def research_to_tasks(email, research_id, tasks):
    """Create roadmap tasks from a research note's recommendations. Pass the
    tasks you derived from the note (each at least a `title`; optional
    `description`, `university_id`, `due_date`); each is created in the roadmap
    linked back to the note via `source_research_id`."""
    if not tasks:
        raise StratiaError("tasks is required (a list of {title, ...})")
    note = _get(_pm("get-research"), {"user_email": email, "research_id": research_id}).get("research")
    if not note:
        raise StratiaError(f"research '{research_id}' not found")
    base = _dt.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    created = []
    for i, t in enumerate(tasks):
        t = t if isinstance(t, dict) else {"title": str(t)}
        title = (t.get("title") or "").strip()
        if not title:
            continue
        task_id = f"tsk_{base}_{i}"
        task_data = {
            "title": title,
            "description": t.get("description") or "",
            "status": "pending",
            "university_id": t.get("university_id"),
            # due_date must be present — get-roadmap-tasks orders by it and
            # Firestore excludes docs missing the ordered field.
            "due_date": t.get("due_date") or "",
            "category": "research",
            "source_research_id": research_id,
        }
        resp = _post(_pm("save-roadmap-task"),
                     {"user_email": email, "task_id": task_id, "task_data": task_data}, email=email)
        if resp.get("success"):
            created.append(task_id)
    return {"research_id": research_id, "created": created, "count": len(created)}
