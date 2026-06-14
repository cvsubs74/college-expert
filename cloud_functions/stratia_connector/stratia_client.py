"""Thin HTTP client over the Stratia backend services (counselor_agent,
profile_manager_v2, knowledge_base_manager_universities_v2).

Uses `requests` (already a repo/runtime dep). Every call is made on behalf of a
verified `email` — the connector is the trusted layer that supplies it; the
backends themselves still just trust the email (no change needed for v1).

Responses are trimmed to keep tool results well under Claude's limits.
"""
import requests

from settings import settings


class StratiaError(RuntimeError):
    """A backend call failed or returned an error payload."""


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


# ----------------------------------------------------------------------------
# Knowledge base (no user identity required)
# ----------------------------------------------------------------------------

def search_universities(query, limit=10, max_acceptance_rate=None, state=None):
    # The KB's keyword search is the GET ?search= endpoint (the POST {query}
    # variant is semantic/offline and returns nothing).
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
            "soft_fit_category": u.get("soft_fit_category"),
            "summary": (u.get("summary") or "")[:400],
        })
    return out


def get_university(university_id):
    data = _get(settings.KNOWLEDGE_BASE_UNIVERSITIES_URL, {"university_id": university_id})
    if not data.get("success") or not data.get("university"):
        raise StratiaError(f"university '{university_id}' not found")
    u = data["university"]
    p = u.get("profile") or {}
    ap = p.get("application_process") or {}
    return {
        "university_id": u.get("university_id"),
        "name": u.get("official_name"),
        "location": u.get("location"),
        "acceptance_rate": u.get("acceptance_rate"),
        "data_year": u.get("data_year"),
        "application_deadlines": [
            {"plan_type": d.get("plan_type"), "date": d.get("date")}
            for d in (ap.get("application_deadlines") or []) if isinstance(d, dict)
        ],
        "scholarships": [
            {"name": s.get("name"), "amount": s.get("amount"),
             "deadline": s.get("deadline"), "deadline_date": s.get("deadline_date")}
            for s in ((p.get("financials") or {}).get("scholarships") or []) if isinstance(s, dict)
        ][:12],
    }


# ----------------------------------------------------------------------------
# Per-user reads
# ----------------------------------------------------------------------------

def get_college_list(email):
    data = _get(f"{settings.PROFILE_MANAGER_V2_URL}/get-college-list", {"user_email": email})
    return [
        {"university_id": c.get("university_id"), "name": c.get("university_name"),
         "status": c.get("status"), "fit_category": (c.get("fit_analysis") or {}).get("fit_category")}
        for c in (data.get("college_list") or [])
    ]


def get_fit_analysis(email, university_id):
    data = _get(f"{settings.PROFILE_MANAGER_V2_URL}/get-fit-analysis",
               {"user_email": email, "university_id": university_id})
    fit = data.get("fit_analysis") or {}
    if not fit:
        raise StratiaError(f"no fit analysis for '{university_id}' — try recompute_fit")
    return {
        "university_id": university_id,
        "fit_category": fit.get("fit_category"),
        "match_percentage": fit.get("match_percentage") or fit.get("match_score"),
        "kb_data_year": fit.get("kb_data_year"),
        "explanation": (fit.get("explanation") or "")[:1500],
        "recommendations": (fit.get("recommendations") or [])[:6],
    }


def get_deadlines(email):
    data = _post(f"{settings.COUNSELOR_AGENT_URL}/deadlines", {"user_email": email}, email=email)
    return [
        {"university": d.get("university_name") or d.get("university_id"),
         "deadline_type": d.get("deadline_type"), "date": d.get("date")}
        for d in (data.get("deadlines") or [])
    ]


def get_profile(email):
    data = _get(f"{settings.PROFILE_MANAGER_V2_URL}/get-profile", {"user_email": email})
    p = data.get("profile") or {}
    keep = ("intended_major", "grade_level", "gpa", "sat_score", "act_score",
            "graduation_year", "extracurriculars", "demographics")
    return {k: p[k] for k in keep if k in p}


# ----------------------------------------------------------------------------
# Per-user safe writes
# ----------------------------------------------------------------------------

def add_college(email, university_id, name):
    data = _post(f"{settings.PROFILE_MANAGER_V2_URL}/update-college-list",
                {"user_email": email, "action": "add",
                 "university": {"id": university_id, "name": name}}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "add_college failed")
    return {"added": university_id}


def remove_college(email, university_id, name=""):
    data = _post(f"{settings.PROFILE_MANAGER_V2_URL}/update-college-list",
                {"user_email": email, "action": "remove",
                 "university": {"id": university_id, "name": name}}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "remove_college failed")
    return {"removed": university_id}


def recompute_fit(email, university_id):
    # The recompute calls the LLM; allow more time (Claude.ai tool limit is 300s).
    data = _post(f"{settings.PROFILE_MANAGER_V2_URL}/compute-single-fit",
                {"user_email": email, "university_id": university_id},
                timeout=120, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "recompute_fit failed")
    fit = data.get("fit_analysis") or {}
    return {
        "university_id": university_id,
        "fit_category": fit.get("fit_category"),
        "match_percentage": fit.get("match_percentage") or fit.get("match_score"),
        "kb_data_year": fit.get("kb_data_year"),
    }


def update_profile_field(email, field_path, value, operation="set"):
    data = _post(f"{settings.PROFILE_MANAGER_V2_URL}/update-structured-field",
                {"user_email": email, "field_path": field_path,
                 "value": value, "operation": operation}, email=email)
    if not data.get("success"):
        raise StratiaError(data.get("error") or "update_profile_field failed")
    return {"updated": field_path}
