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
import data_assertions
import fit_assertions
import ground_truth as ground_truth_mod

logger = logging.getLogger(__name__)


# ---- Date-aware expected template ------------------------------------------
# Mirrors counselor_agent/planner.py::resolve_template_key (the
# graduation_year + today path). Used by the runner to derive what
# template_used the resolver SHOULD return for a given scenario, so
# the assertion stays correct as the calendar advances.
#
# Why duplicate planner.py instead of calling it? Cross-function calls add
# latency to every scenario run, and this mapping is small + stable
# (locked in tests/cloud_functions/counselor_agent/test_planner.py).
# If planner's grade/semester logic ever changes, update this too — the
# tests in test_runner.py::TestExpectedTemplateForProfile pin the contract.

# Templates that exist in planner.py's TEMPLATES dict. Summer falls back
# to spring for grades that don't have a dedicated summer template.
_TEMPLATE_KEYS = {
    'freshman_fall', 'freshman_spring',
    'sophomore_fall', 'sophomore_spring',
    'junior_fall', 'junior_spring', 'junior_summer',
    'senior_fall', 'senior_spring',
}


def _semester_from_month(month: int) -> str:
    if 8 <= month <= 12:
        return 'fall'
    if 1 <= month <= 5:
        return 'spring'
    return 'summer'  # June, July


def _grade_from_grad_year(grad_year: int, today: datetime) -> str:
    """Mirrors planner.grade_name_from_graduation_year exactly.

    Rule: each year out from graduation, the grade steps down by one — but
    in the fall semester, students are already "in" their next grade level,
    so fall maps to the higher grade. Caps at senior (no one is past senior
    in this app).
    """
    years_until_grad = grad_year - today.year
    semester = _semester_from_month(today.month)
    if years_until_grad <= 0:
        return 'senior'
    if years_until_grad == 1:
        return 'senior' if semester == 'fall' else 'junior'
    if years_until_grad == 2:
        return 'junior' if semester == 'fall' else 'sophomore'
    if years_until_grad == 3:
        return 'sophomore' if semester == 'fall' else 'freshman'
    return 'freshman'


def _expected_template_for(profile: dict, today: Optional[datetime] = None) -> Optional[str]:
    """Compute the template the resolver should return for this profile,
    given the current date. Returns None when graduation_year is missing
    or unparseable — caller skips the assertion in that case.
    """
    if today is None:
        today = datetime.now(timezone.utc)
    raw = (profile or {}).get('graduation_year')
    try:
        grad_year = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    if grad_year is None:
        return None

    grade = _grade_from_grad_year(grad_year, today)
    semester = _semester_from_month(today.month)

    # Direct match if template exists; else summer falls back to spring
    # (matches planner._compose_template_key fallback table).
    candidate = f'{grade}_{semester}'
    if candidate in _TEMPLATE_KEYS:
        return candidate
    if semester == 'summer':
        spring_fallback = f'{grade}_spring'
        if spring_fallback in _TEMPLATE_KEYS:
            return spring_fallback
    return None


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


def _xref_step(
    name: str,
    http_ctx: dict,
    truth_bag: dict,
    asserts: list,
) -> dict:
    """Step record for cross-reference assertions. Threads `truth_bag`
    into the assertion ctx so data_assertions.* can compare response
    values against the ground truth gathered earlier."""
    ctx = dict(http_ctx)
    ctx["truth_bag"] = truth_bag
    results = data_assertions.run_all(asserts, ctx)
    passed = data_assertions.all_passed(results)
    return {
        "name": name,
        "endpoint": http_ctx.get("url"),
        "status_code": http_ctx.get("status_code"),
        "elapsed_ms": http_ctx.get("elapsed_ms"),
        "request": _redact(http_ctx.get("request_body")),
        "response_excerpt": (http_ctx.get("response_excerpt") or "")[:1500],
        "assertions": [r.to_dict() for r in results],
        "passed": passed,
    }


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
        knowledge_base_url: str = "",
    ):
        self.profile_manager_url = profile_manager_url.rstrip("/")
        self.counselor_agent_url = counselor_agent_url.rstrip("/")
        self.admin_token = admin_token
        self.id_token = id_token
        self.test_user_email = test_user_email
        # KB URL is optional — when absent, the runner skips ground truth
        # gathering and cross-reference assertions mark themselves SKIP.
        self.knowledge_base_url = knowledge_base_url.rstrip("/") if knowledge_base_url else ""


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

    # ----- Step 1.5: gather ground truth ---------------------------------
    # Pull canonical KB records for every college this scenario will add.
    # Cross-reference assertions later compare runtime API responses
    # against this snapshot. KB misses become empty records — assertions
    # that depend on them will mark themselves SKIP rather than fail.
    college_ids_to_add = list(scenario.get("colleges_template", []))
    truth_bag = {}
    truth_step_assertions = []
    truth_started = time.time()
    if college_ids_to_add and cfg.knowledge_base_url:
        try:
            truth_bag = ground_truth_mod.fetch_ground_truth(
                college_ids_to_add,
                kb_url=cfg.knowledge_base_url,
            )
        except Exception as exc:  # noqa: BLE001
            truth_step_assertions.append({
                "name": "ground truth fetched",
                "passed": False,
                "message": f"{type(exc).__name__}: {exc}",
            })
    truth_step_assertions.append({
        "name": "truth bag populated",
        "passed": bool(truth_bag),
        "message": "kb miss for every college" if not truth_bag else "",
    })
    steps.append({
        "name": "gather_ground_truth",
        "endpoint": cfg.knowledge_base_url or "(skipped — no kb_url)",
        "status_code": 200 if truth_bag else 0,
        "elapsed_ms": int((time.time() - truth_started) * 1000),
        "request": {"colleges": college_ids_to_add},
        "response_excerpt": (
            "Truth records: " + ", ".join(
                f"{cid}={'KB hit' if rec else 'KB miss'}"
                for cid, rec in truth_bag.items()
            )
        )[:1500],
        "assertions": truth_step_assertions,
        # Truth gathering is best-effort. Even with a KB miss per college,
        # the scenario can still run — downstream cross-ref assertions
        # mark themselves SKIP, not FAIL.
        "passed": True,
    })

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

    # ----- Step 3.5: college list symmetry --------------------------------
    # Pull /get-college-list back and verify writes-set == reads-set.
    # Catches "API returned 200 on add but the read endpoint doesn't see
    # the entry" — a real failure mode the shape-only checks would miss.
    if college_ids_to_add:
        list_ctx = poster(
            f"{pm}/get-college-list",
            {"user_email": cfg.test_user_email},
            id_token=cfg.id_token,
        )
        # Per-college deadline cross-ref: for each college in the truth
        # bag, assert the KB's deadline appears on the corresponding
        # college_list entry. We can't address by index reliably, so we
        # use list_matches_truth_set for the symmetry check + a
        # generated set of value_equals_truth checks per college via
        # response_path indexing into the actual returned list.
        symmetry_assertions = [
            data_assertions.list_matches_truth_set(
                "college_list", id_key="university_id",
                expected_ids=college_ids_to_add,
            ),
        ]
        steps.append(_xref_step(
            "verify_college_list_symmetry", list_ctx, truth_bag, symmetry_assertions,
        ))

    # ----- Step 4: roadmap generation -------------------------------------
    roadmap_ctx = poster(
        f"{ca}/roadmap",
        {"user_email": cfg.test_user_email},
        id_token=cfg.id_token,
    )
    # Compute the expected template from (graduation_year, today) instead
    # of trusting the scenario's static `expected_template_used` field.
    # The static field is wrong any time the calendar season differs from
    # what the scenario was originally named for (e.g., a "junior_fall"
    # scenario run in May correctly resolves to "junior_spring").
    # See _expected_template_for above + tests/.../test_runner.py.
    expected_template = _expected_template_for(scenario.get("profile_template", {}))
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

    # ----- Step 4.5: roadmap deep-link integrity --------------------------
    # Walk every artifact_ref in the roadmap response. Every
    # university_id referenced must be in the college list we built.
    # Catches "the roadmap is referencing schools we never added"
    # — broken or stale deep links. Skipped when no colleges added.
    if college_ids_to_add and roadmap_ctx.get("status_code", 0) < 400:
        deep_link_assertions = [
            data_assertions.deep_link_resolves(
                list_path="roadmap.phases[*].tasks[*]",
                id_path="artifact_ref.university_id",
                valid_ids=college_ids_to_add,
            ),
        ]
        steps.append(_xref_step(
            "roadmap_deep_link_integrity",
            roadmap_ctx, truth_bag, deep_link_assertions,
        ))

    # ----- Step 4.7: college fit (optional, single OR multi) --------------
    # Fit-focused archetypes set either `fit_target_college` (string)
    # for single-school scenarios or `fit_target_colleges` (list) for
    # multi-school scenarios that also exercise cross-school category
    # ordering. We POST to profile_manager_v2 /compute-single-fit per
    # target and run the invariant assertions from fit_assertions.py.
    # Spec: docs/prd/qa-fit-testing.md.
    multi_targets = scenario.get("fit_target_colleges") or []
    if isinstance(multi_targets, str):  # defensive: scalar in list-typed field
        multi_targets = [multi_targets]
    single_target = scenario.get("fit_target_college")
    fit_targets = list(multi_targets) if multi_targets else (
        [single_target] if single_target else []
    )

    # Track each fit response so we can run cross-school assertions
    # after every per-school step has run.
    collected_fit_responses: List[tuple] = []

    for fit_target in fit_targets:
        # /compute-single-fit makes an LLM call AND profile_manager_v2
        # sometimes cold-starts (it scales to zero). Observed in PR #76
        # post-deploy verification: a cold-start path took ~40s
        # end-to-end, blowing the runner's default 30s timeout and
        # producing a "status 0" assertion failure for an otherwise
        # healthy endpoint. 90s gives comfortable headroom for the
        # cold-start case while still being aggressive enough to flag
        # a real hang.
        fit_ctx = poster(
            f"{pm}/compute-single-fit",
            {
                "user_email": cfg.test_user_email,
                "university_id": fit_target,
            },
            admin_token=cfg.admin_token,
            timeout=90,
        )
        fit_asserts: List[assertions.AssertionFn] = [
            assertions.status_is_2xx(),
            assertions.key_equals("success", True),
            # Phase 1 invariants. None require external truth — all
            # come from the response itself.
            fit_assertions.category_in_valid_set(),
            fit_assertions.match_percentage_in_range(),
            fit_assertions.match_percentage_aligns_with_category(),
            fit_assertions.selectivity_floor_respected(),
            fit_assertions.selectivity_ceiling_respected(),
            fit_assertions.factor_bounds_respected(),
            fit_assertions.required_advisory_blocks_present(),
            # Mirrors the timeout above: the fit endpoint is allowed
            # up to 60s before we flag latency-degradation. The
            # request itself can run up to 90s — gap is intentional
            # so we surface "slow but OK" before hard-fail.
            assertions.latency_under(60000),
        ]
        # If the archetype declared an expected category, pin that too —
        # gives us a tighter signal than the invariants alone for the
        # canonical "ultra-selective stays SUPER_REACH" scenario.
        # Only meaningful for single-target scenarios; the same pin
        # would be wrong across multiple schools at different tiers.
        expected_cat = scenario.get("fit_expected_category")
        if expected_cat and len(fit_targets) == 1:
            fit_asserts.append(
                assertions.key_equals(
                    "fit_analysis.fit_category", expected_cat,
                )
            )
        # Phase 2c-2: when the archetype declares its profile carries no
        # SAT/ACT scores, the algorithm must not recommend "Submit".
        if scenario.get("fit_no_test_scores"):
            fit_asserts.append(
                fit_assertions.test_strategy_not_submit_when_no_scores()
            )
        steps.append(_step(f"compute_fit:{fit_target}", fit_ctx, fit_asserts))
        collected_fit_responses.append((fit_target, fit_ctx))

    # ----- Step 4.8: cross-school category-rank ordering (multi only) -----
    # When the archetype exercises 2+ schools, walk the collected fit
    # responses and assert category-rank is monotonically non-decreasing
    # as acceptance_rate increases. This catches the one bug class that
    # per-school invariants don't: the algorithm being internally
    # inconsistent across schools (e.g., the same student getting a
    # WORSE category at a less-selective school).
    if len(collected_fit_responses) >= 2:
        ordering_results = (
            fit_assertions.check_category_rank_monotonic_with_selectivity(
                collected_fit_responses,
            )
        )
        steps.append({
            "name": "fit_relative_ordering",
            "endpoint": f"{pm}/compute-single-fit (×{len(collected_fit_responses)})",
            "status_code": 0,  # synthetic step; not an HTTP call of its own
            "elapsed_ms": 0,
            "request": {
                "schools": [u for u, _ in collected_fit_responses],
            },
            "response_excerpt": "; ".join(
                f"{u}={(c.get('response_json') or {}).get('fit_analysis', {}).get('fit_category', '?')}"
                for u, c in collected_fit_responses
            )[:1500],
            "assertions": [r.to_dict() for r in ordering_results],
            "passed": all(r.passed for r in ordering_results),
        })

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

    # ----- Step 5.5: essay tracker alignment ------------------------------
    # Pull the essay tracker back. For each college we added, verify
    # the tracker entries reference real college_ids (no orphans) AND
    # the per-college essay count is at least the KB's required count.
    if college_ids_to_add:
        essay_ctx = poster(
            f"{pm}/get-essay-tracker",
            method="GET",
            params={"user_email": cfg.test_user_email},
            id_token=cfg.id_token,
        )
        # The essay tracker may return entries under various keys
        # depending on the response shape. Check both common shapes.
        essay_assertions = [
            data_assertions.deep_link_resolves(
                list_path="essays",
                id_path="university_id",
                valid_ids=college_ids_to_add,
            ),
            data_assertions.per_university_count_matches(
                list_path="essays",
                id_key="university_id",
                truth_count_path="essays_required",
                comparison="gte",
            ),
        ]
        steps.append(_xref_step(
            "essay_tracker_alignment", essay_ctx, truth_bag, essay_assertions,
        ))

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

    # ----- Step 6.4: tasks lifecycle (optional, mark + read-back) ---------
    # Gated behind `test_mark_task` on the archetype. Exercises the
    # POST /mark-task → GET /get-tasks round-trip. Synthetic task ids
    # (qa_smoke_*) get cleaned up by the final teardown's clear-test-data
    # call. This catches:
    #   - /mark-task returning 500 (every "complete" click would silently fail)
    #   - schema regressions on /get-tasks
    #   - the mark not actually persisting (integration bug between
    #     counselor_agent → profile_manager_v2 update-structured-field)
    if scenario.get("test_mark_task"):
        smoke_task_id = "qa_smoke_mark_task_1"
        mark_ctx = poster(
            f"{ca}/mark-task",
            {
                "user_email": cfg.test_user_email,
                "task_id": smoke_task_id,
                "completed": True,
            },
            id_token=cfg.id_token,
            timeout=15,
        )
        steps.append(_step("mark_task", mark_ctx, [
            assertions.status_is_2xx(),
            assertions.key_equals("success", True),
            assertions.key_equals("task_id", smoke_task_id),
            assertions.key_equals("completed", True),
            assertions.latency_under(10000),
        ]))

        # Read-back: /get-tasks (forwards to profile_manager_v2
        # /get-roadmap-tasks). Asserts the field is fetchable; doesn't
        # require the synthetic task to be there (the response shape
        # is what we care about here — a regression that returned 500
        # for every roadmap-tab load would be the failure mode).
        get_tasks_ctx = poster(
            f"{ca}/get-tasks",
            method="GET",
            params={"user_email": cfg.test_user_email},
            id_token=cfg.id_token,
            timeout=15,
        )
        steps.append(_step("get_tasks", get_tasks_ctx, [
            assertions.status_is_2xx(),
            assertions.key_equals("success", True),
            assertions.has_key("tasks"),
            assertions.latency_under(8000),
        ]))

    # ----- Step 6.5: counselor chat (optional) ----------------------------
    # Gated behind `chat_question` on the archetype, mirroring the
    # `fit_target_college` pattern. The runner exercises counselor_agent
    # /chat with the canned question; assertions verify the response
    # shape + non-empty reply + reasonable latency. Real-world impact:
    # the chat is the highest-stakes user-facing AI surface — a regression
    # that broke /chat would silently degrade every user's main
    # interaction with the counselor.
    chat_question = scenario.get("chat_question")
    if chat_question:
        chat_ctx = poster(
            f"{ca}/chat",
            {
                "user_email": cfg.test_user_email,
                "message": chat_question,
                "history": [],
            },
            id_token=cfg.id_token,
            timeout=60,  # LLM call; cold-start headroom
        )
        steps.append(_step("counselor_chat", chat_ctx, [
            assertions.status_is_2xx(),
            assertions.key_equals("success", True),
            # Stricter than has_key: catches reply="" / null / whitespace
            # — a regression where the LLM call succeeds structurally but
            # the user sees a blank chat bubble.
            assertions.key_non_empty_string("reply"),
            assertions.has_key("suggested_actions"),
            assertions.latency_under(45000),
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
