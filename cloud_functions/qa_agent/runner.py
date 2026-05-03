"""
Scenario runner.

Given a materialized scenario (archetype + variation applied), the runner:
  1. Calls /clear-test-data to start clean
  2. Posts the synthetic profile via profile_manager_v2
  3. Adds each college from the scenario's college list
  4. Calls counselor_agent /roadmap and asserts the response shape
  5. Optionally runs a fit-analysis step
  6. Calls /clear-test-data again to leave the test account empty
  7. Returns a structured result the caller writes to Firestore

The runner never raises — every failure becomes a structured assertion
result. The scenario's overall pass status is `all step assertions
passed AND the run reached teardown`.
"""

from __future__ import annotations

import logging
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import requests

import assertions

logger = logging.getLogger(__name__)


# ---- HTTP helper -----------------------------------------------------------


def _post(
    url: str,
    body: Optional[dict] = None,
    *,
    method: str = "POST",
    params: Optional[dict] = None,
    id_token: Optional[str] = None,
    admin_token: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """One HTTP request, with timing. Supports GET (params) and POST
    (json body). Returns a context dict suitable for assertion checks.
    Network errors become status_code=0 with an error message."""
    headers = {"Content-Type": "application/json"}
    if id_token:
        headers["Authorization"] = f"Bearer {id_token}"
    if admin_token:
        headers["X-Admin-Token"] = admin_token

    start = time.time()
    status = 0
    body_json: Optional[dict] = None
    body_text = ""
    error: Optional[str] = None

    try:
        if method.upper() == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        else:
            resp = requests.post(url, json=body, params=params, headers=headers, timeout=timeout)
        status = resp.status_code
        body_text = resp.text[:8000]
        try:
            body_json = resp.json()
        except ValueError:
            body_json = None
    except requests.RequestException as exc:
        error = f"{type(exc).__name__}: {exc}"

    elapsed_ms = int((time.time() - start) * 1000)
    return {
        "url": url,
        "method": method.upper(),
        # Redaction happens at report-build time (in _step); leaving the
        # raw body here lets assertion fns inspect it if they ever need to.
        "request_body": body if body is not None else (params or {}),
        "status_code": status,
        "response_json": body_json,
        "response_excerpt": body_text,
        "elapsed_ms": elapsed_ms,
        "network_error": error,
    }


def _redact(body):
    """Strip obvious PII from request bodies before they hit the report.

    The test user's email is left in (we need it for debugging) but
    full names from LLM variations get redacted to first initial. Walks
    nested dicts because the synthetic profile lives under
    `body['profile']['full_name']`, not at the top level.
    """
    if isinstance(body, dict):
        out = {}
        for k, v in body.items():
            if k in ("full_name", "name", "student_name") and isinstance(v, str) and " " in v:
                first, *_ = v.split(" ")
                out[k] = first[:1] + "."
            else:
                out[k] = _redact(v)
        return out
    if isinstance(body, list):
        return [_redact(item) for item in body]
    return body


# ---- Step types -------------------------------------------------------------


def _step(name: str, http_ctx: dict, asserts: List[assertions.AssertionFn]) -> dict:
    """Wrap an HTTP context + assertion list into a step record."""
    results = assertions.run_all(asserts, http_ctx)
    if http_ctx.get("network_error"):
        results.append(assertions.AssertionResult(
            name="no network error",
            passed=False,
            message=http_ctx["network_error"],
        ))
    return {
        "name": name,
        "endpoint": http_ctx.get("url"),
        "status_code": http_ctx.get("status_code"),
        "elapsed_ms": http_ctx.get("elapsed_ms"),
        # Redact PII before the body lands in the persisted report.
        "request": _redact(http_ctx.get("request_body")),
        "response_excerpt": (http_ctx.get("response_excerpt") or "")[:1500],
        "assertions": [r.to_dict() for r in results],
        "passed": assertions.all_passed(results),
    }


# ---- Configuration --------------------------------------------------------


class RunConfig:
    """Bag of URLs + tokens the runner needs. Built by main.py from env
    vars and passed into run_scenario."""

    def __init__(
        self,
        *,
        profile_manager_url: str,
        counselor_agent_url: str,
        admin_token: str,
        id_token: str,
        test_user_email: str,
    ):
        self.profile_manager_url = profile_manager_url.rstrip("/")
        self.counselor_agent_url = counselor_agent_url.rstrip("/")
        self.admin_token = admin_token
        self.id_token = id_token
        self.test_user_email = test_user_email


# ---- Scenario execution ----------------------------------------------------


def run_scenario(
    scenario: dict,
    cfg: RunConfig,
    *,
    poster: Callable[..., Dict[str, Any]] = _post,
) -> dict:
    """Execute one scenario end-to-end. Returns a step-by-step record.

    `poster` is the HTTP function (defaults to the real one). Tests
    inject a fake to drive the assertion logic without real HTTP."""
    started = datetime.now(timezone.utc)
    started_at_iso = started.isoformat()
    steps: List[dict] = []

    pm = cfg.profile_manager_url
    ca = cfg.counselor_agent_url

    # ----- Step 1: setup teardown ------------------------------------------
    setup_ctx = poster(
        f"{pm}/clear-test-data",
        {"user_email": cfg.test_user_email},
        admin_token=cfg.admin_token,
    )
    steps.append(_step("setup_teardown", setup_ctx, [
        assertions.status_is_2xx(),
        assertions.key_equals("ok", True),
    ]))

    # ----- Step 2: profile build ------------------------------------------
    # profile_manager_v2 doesn't expose a "save the whole profile in one
    # call" endpoint — frontend onboarding hits /update-structured-field
    # one field at a time. Mirror that here so the QA agent exercises the
    # same code path real onboarding does.
    fields_to_set = list(scenario.get("profile_template", {}).items())
    field_results = []
    for field_path, value in fields_to_set:
        field_ctx = poster(
            f"{pm}/update-structured-field",
            {
                "user_email": cfg.test_user_email,
                "field_path": field_path,
                "value": value,
                "operation": "set",
            },
            id_token=cfg.id_token,
        )
        field_results.append(field_ctx)
    # Roll up the per-field results into one step record. Step passes if
    # every field succeeded.
    profile_pass = all(
        200 <= ctx.get("status_code", 0) < 300 for ctx in field_results
    )
    steps.append({
        "name": "profile_build",
        "endpoint": f"{pm}/update-structured-field (×{len(field_results)})",
        "status_code": field_results[-1]["status_code"] if field_results else None,
        "elapsed_ms": sum(ctx.get("elapsed_ms", 0) for ctx in field_results),
        "request": {"fields": [k for k, _ in fields_to_set]},
        "response_excerpt": "; ".join(
            (ctx.get("response_excerpt") or "")[:200]
            for ctx in field_results[:3]
        )[:1500],
        "assertions": [
            {"name": f"field {k!r} 2xx",
             "passed": 200 <= field_results[i]["status_code"] < 300,
             "message": f"got {field_results[i]['status_code']}"
             if not (200 <= field_results[i]["status_code"] < 300) else ""}
            for i, (k, _) in enumerate(fields_to_set)
        ],
        "passed": profile_pass,
    })

    # ----- Step 3: add colleges -------------------------------------------
    for college_id in scenario.get("colleges_template", []):
        # The endpoint is /add-to-list (not /add-to-college-list). It
        # takes {user_email, university_id} and returns success-shaped
        # response.
        college_ctx = poster(
            f"{pm}/add-to-list",
            {
                "user_email": cfg.test_user_email,
                "university_id": college_id,
                "university_name": college_id.replace("_", " ").title(),
            },
            id_token=cfg.id_token,
        )
        steps.append(_step(f"add_college:{college_id}", college_ctx, [
            assertions.status_is_2xx(),
        ]))

    # ----- Step 4: roadmap generation -------------------------------------
    roadmap_ctx = poster(
        f"{ca}/roadmap",
        {"user_email": cfg.test_user_email},
        id_token=cfg.id_token,
    )
    expected_template = scenario.get("expected_template_used")
    roadmap_asserts: List[assertions.AssertionFn] = [
        assertions.status_is_2xx(),
        assertions.key_equals("success", True),
        assertions.has_key("metadata.template_used"),
        assertions.has_key("metadata.resolution_source"),
        assertions.list_non_empty("roadmap.phases"),
        assertions.latency_under(15000),
    ]
    if expected_template:
        roadmap_asserts.append(
            assertions.key_equals("metadata.template_used", expected_template)
        )
    steps.append(_step("roadmap_generate", roadmap_ctx, roadmap_asserts))

    # ----- Step 5: work feed ----------------------------------------------
    # /work-feed is GET with query params, not POST.
    work_feed_ctx = poster(
        f"{ca}/work-feed",
        method="GET",
        params={"user_email": cfg.test_user_email, "limit": 8},
        id_token=cfg.id_token,
    )
    steps.append(_step("work_feed", work_feed_ctx, [
        assertions.status_is_2xx(),
        assertions.key_equals("success", True),
        assertions.has_key("items"),
        assertions.latency_under(8000),
    ]))

    # ----- Step 6: deadlines ----------------------------------------------
    deadlines_ctx = poster(
        f"{ca}/deadlines",
        {"user_email": cfg.test_user_email},
        id_token=cfg.id_token,
    )
    steps.append(_step("deadlines", deadlines_ctx, [
        assertions.status_is_2xx(),
        assertions.key_equals("success", True),
    ]))

    # ----- Step 7: final teardown -----------------------------------------
    teardown_ctx = poster(
        f"{pm}/clear-test-data",
        {"user_email": cfg.test_user_email},
        admin_token=cfg.admin_token,
    )
    steps.append(_step("final_teardown", teardown_ctx, [
        assertions.status_is_2xx(),
        assertions.key_equals("ok", True),
    ]))

    ended = datetime.now(timezone.utc)
    overall_pass = all(s["passed"] for s in steps)

    return {
        "scenario_id": scenario.get("id"),
        "description": scenario.get("description"),
        "variation": scenario.get("_variation", {}),
        "started_at": started_at_iso,
        "ended_at": ended.isoformat(),
        "duration_ms": int((ended - started).total_seconds() * 1000),
        "steps": steps,
        "passed": overall_pass,
    }
