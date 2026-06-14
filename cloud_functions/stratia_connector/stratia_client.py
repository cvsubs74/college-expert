"""Thin HTTP client over the Stratia backend services (counselor_agent,
profile_manager_v2, knowledge_base_manager_universities_v2).

Uses `requests` (already a repo/runtime dep). Every per-user call is made on
behalf of a verified `email` — the connector supplies it; the backends trust it.

Design: the backends already return rich data. Rather than allow-listing a few
fields (which lost most of it), each tool returns EVERYTHING via `_prune`
(drops internal/embedding/housekeeping keys, caps runaway lists/strings) and a
final `_cap_size` guard so results stay under Claude's ~150k-char tool limit.
"""
import json

import requests

from settings import settings


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


def _get(url, params=None, timeout=30):
    try:
        r = requests.get(url, params=params, timeout=timeout,
                         headers={"X-User-Email": (params or {}).get("user_email", "")})
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise StratiaError(f"request to {url} failed: {e}") from e


def _post(url, body, timeout=30, email=None):
    try:
        r = requests.post(url, json=body, timeout=timeout,
                         headers={"X-User-Email": email or body.get("user_email", "")})
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise StratiaError(f"request to {url} failed: {e}") from e


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


def get_university(university_id):
    """Full KB profile — all sections (admissions, academics, financials,
    application process, outcomes, student life, strategic profile, ...)."""
    data = _get(settings.KNOWLEDGE_BASE_UNIVERSITIES_URL, {"university_id": university_id})
    if not data.get("success") or not data.get("university"):
        raise StratiaError(f"university '{university_id}' not found")
    u = data["university"]
    out = {
        "university_id": u.get("university_id"),
        "name": u.get("official_name"),
        "location": u.get("location"),
        "acceptance_rate": u.get("acceptance_rate"),
        "us_news_rank": u.get("us_news_rank"),
        "market_position": u.get("market_position"),
        "data_year": u.get("data_year"),
        "available_years": u.get("available_years"),
    }
    # Merge the full profile (every KB section), pruned + list-capped.
    out.update(_prune(u.get("profile") or {}, list_caps={
        "scholarships": 40, "majors": 60, "application_deadlines": 30,
        "supplemental_requirements": 30, "longitudinal_trends": 8,
    }))
    # KB docs are large; drop the bulkiest low-value sections only if over cap.
    return _cap_size(out, droppable=(
        "longitudinal_trends", "admitted_student_profile", "student_insights", "outcomes",
    ))


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
            "fit_category": fa.get("fit_category"),
            "match_percentage": fa.get("match_percentage") or fa.get("match_score"),
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


def recompute_fit(email, university_id):
    # The recompute calls the LLM; allow more time (Claude.ai tool limit is 300s).
    data = _post(_pm("compute-single-fit"),
                {"user_email": email, "university_id": university_id},
                timeout=120, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "recompute_fit failed")
    fit = data.get("fit_analysis") or {}
    fit.setdefault("university_id", university_id)
    return _prune(fit, list_caps={"recommendations": 15, "essay_angles": 15,
                                  "scholarship_matches": 30, "factors": 12},
                 text_caps={"explanation": 6000}, deny={"computed_at"})


def update_profile_field(email, field_path, value, operation="set"):
    data = _post(_pm("update-structured-field"),
                {"user_email": email, "field_path": field_path,
                 "value": value, "operation": operation}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "update_profile_field failed")
    return {"updated": field_path}
