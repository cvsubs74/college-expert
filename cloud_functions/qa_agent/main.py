"""
QA Agent — Cloud Function entry point.

Endpoints:
  GET  /                      → liveness ping (also the smoke-test target
                                 for auto-deploy CI: a comment-only edit to
                                 this file produces a fresh revision via
                                 cloudbuild-main.yaml — see
                                 docs/prd/auto-deploy-on-main.md.
                                 First successful auto-deploy was the merge
                                 of fix/cicd-detect-targets-fetch-parent
                                 once shallow-clone diff worked.)
  GET  /health                → liveness ping
  GET  /scenarios             → list of registered archetypes (id + description)
  POST /run                   → run a fresh batch
  POST /run?scenario=<id>     → run one specific archetype
  POST /suggest-cause         → LLM analysis of a failing scenario
  POST /github-issue          → build a pre-filled GitHub issue URL

Trigger sources:
  - Cloud Scheduler (daily) — sends X-Admin-Token
  - Admin browser dashboard — sends Authorization: Bearer <Firebase ID token>
  - curl from a developer laptop — sends X-Admin-Token

Auth: dual gate. Either:
  1. X-Admin-Token: <token>  matches QA_ADMIN_TOKEN secret, OR
  2. Authorization: Bearer <id_token>  AND the verified email is in
     QA_ADMIN_EMAILS (default: cvsubs@gmail.com).

Both auth paths are equivalent at the endpoint level. Token check
happens first; ID-token verification only if token is absent. The
Firestore security rules are the actual data-side gate, so even an
auth bypass at this layer can't expose run reports to non-admins.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone

import functions_framework
from flask import jsonify

import auth
import corpus
import firestore_store
import narratives
import runner
import schedule
import synthesizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- Configuration ---------------------------------------------------------


def _config():
    """Pulled fresh per request so unit tests can override env."""
    return {
        "PROFILE_MANAGER_URL": os.getenv("PROFILE_MANAGER_URL"),
        "COUNSELOR_AGENT_URL": os.getenv("COUNSELOR_AGENT_URL"),
        # Knowledge base URL is needed for ground-truth gathering
        # (cross-reference assertions). Default to the live v2 URL.
        "KNOWLEDGE_BASE_URL": os.getenv(
            "KNOWLEDGE_BASE_UNIVERSITIES_URL",
            "https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app",
        ),
        "ADMIN_TOKEN": os.getenv("QA_ADMIN_TOKEN"),
        "ADMIN_EMAILS": [
            e.strip().lower() for e in
            os.getenv("QA_ADMIN_EMAILS", "cvsubs@gmail.com").split(",")
            if e.strip()
        ],
        "TEST_USER_EMAIL": os.getenv("QA_TEST_USER_EMAIL", "duser8531@gmail.com"),
        "TEST_USER_UID": os.getenv("QA_TEST_USER_UID", ""),
        "FIREBASE_API_KEY": os.getenv("FIREBASE_WEB_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "DEFAULT_SCENARIO_COUNT": int(os.getenv("QA_SCENARIO_COUNT", "4")),
        # How many of the per-run scenarios should be LLM-synthesized.
        # Default 0 — flip to 2 once the prompt is stable in prod.
        "SYNTHESIS_COUNT": int(os.getenv("QA_SYNTHESIS_COUNT", "0")),
        "GITHUB_REPO": os.getenv("QA_GITHUB_REPO", "cvsubs74/college-expert"),
    }


# ---- CORS helper -----------------------------------------------------------


def _cors(payload, status=200):
    resp = jsonify(payload) if isinstance(payload, dict) else payload
    resp.status_code = status
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = (
        "Content-Type, X-Admin-Token, Authorization"
    )
    return resp


# ---- Auth -------------------------------------------------------------------


def _check_auth(request, cfg) -> dict:
    """Returns {ok: bool, actor: str|None}.

    Two acceptable proofs of admin identity:
      1. X-Admin-Token matches QA_ADMIN_TOKEN (constant-time compare).
      2. Authorization: Bearer <Firebase ID token> AND the verified email
         is in QA_ADMIN_EMAILS.
    """
    expected_token = cfg.get("ADMIN_TOKEN")
    admin_emails = cfg.get("ADMIN_EMAILS", [])

    # Path 1: admin token
    provided_token = request.headers.get("X-Admin-Token", "")
    if expected_token and provided_token and secrets.compare_digest(
        provided_token, expected_token
    ):
        return {"ok": True, "actor": "token"}

    # Path 2: Firebase ID token + email allowlist
    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        id_token = auth_hdr[len("Bearer "):].strip()
        try:
            # Route through auth._firebase_admin() instead of importing
            # firebase_admin.auth directly. The helper does the lazy
            # `initialize_app()` on first call — without it, every prod
            # Bearer-token verify fails with "The default Firebase app does
            # not exist" and admins on stratiaadmissions.com/qa-runs see
            # 'unauthorized' even though they're correctly logged in.
            # Caught in prod 2026-05-04; regression test in
            # tests/cloud_functions/qa_agent/test_main_endpoints.py.
            import auth as _qa_auth  # noqa: WPS433
            _fa = _qa_auth._firebase_admin()
            decoded = _fa.verify_id_token(id_token)
            email = (decoded.get("email") or "").lower()
            if email and email in admin_emails:
                return {"ok": True, "actor": email}
            logger.warning(
                "qa_agent: ID token verified but email %r not in admin allowlist",
                email,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("qa_agent: ID token verify failed: %s", exc)

    return {"ok": False, "actor": None}


# ---- Entry point -----------------------------------------------------------


@functions_framework.http
def qa_agent(request):
    if request.method == "OPTIONS":
        return _cors({"status": "ok"})

    cfg = _config()
    path = request.path.strip("/")

    # Public liveness — no auth.
    if path in ("", "health"):
        return _cors({"status": "ok", "test_user": cfg["TEST_USER_EMAIL"]})

    # /scenarios is non-sensitive metadata — exposed without auth so the
    # admin dashboard's single-scenario picker can populate before the
    # user signs in. (Even so, the list is dropped on the floor by the
    # frontend's AdminGate if the user isn't an admin.)
    if path == "scenarios" and request.method == "GET":
        return _cors(_handle_scenarios())

    # Every other endpoint requires admin auth.
    auth_result = _check_auth(request, cfg)
    if not auth_result["ok"]:
        return _cors({"success": False, "error": "unauthorized"}, 401)

    body = request.get_json(silent=True) or {}
    actor = body.get("actor") or auth_result["actor"]

    if path == "run" and request.method == "POST":
        body.setdefault("actor", actor)
        result = _handle_run(body, cfg)
        # _handle_run returns either a dict (status implicit 200) or
        # a (dict, int) tuple for explicit status codes (e.g., 429
        # when another run is in flight).
        if isinstance(result, tuple):
            return _cors(result[0], result[1])
        return _cors(result)

    if path == "run/preview" and request.method == "POST":
        # Picks scenarios the same way /run would, but doesn't execute
        # them. Lets the dashboard show a confirmation modal before the
        # user commits 2-3 minutes of test-user state churn.
        return _cors(_handle_run_preview(body, cfg))

    if path == "suggest-cause" and request.method == "POST":
        return _cors(_handle_suggest_cause(body, cfg))

    if path == "github-issue" and request.method == "POST":
        return _cors(_handle_github_issue(body, cfg))

    if path == "schedule" and request.method == "GET":
        return _cors(_handle_get_schedule())

    if path == "schedule" and request.method == "POST":
        return _cors(_handle_post_schedule(body, actor))

    if path == "summary" and request.method == "GET":
        return _cors(_handle_summary(cfg, request=request))

    if path == "dashboard-prefs" and request.method == "GET":
        return _cors(_handle_get_dashboard_prefs())

    if path == "dashboard-prefs" and request.method == "POST":
        return _cors(_handle_post_dashboard_prefs(body, actor))

    if path == "chat" and request.method == "POST":
        # Admin Q&A grounded in recent run reports. Spec:
        # docs/prd/qa-agent-chat.md + docs/design/qa-agent-chat.md.
        import chat  # noqa: WPS433 — lazy so unrelated requests skip the import
        result, status = chat.handle_chat(body, cfg)
        return _cors(result, status)

    # /feedback — admin notes that steer the next scheduled run.
    # Spec: docs/prd/qa-feedback-loop.md + docs/design/qa-feedback-loop.md.
    if path == "feedback" and request.method == "GET":
        return _cors(_handle_get_feedback())
    if path == "feedback" and request.method == "POST":
        return _cors(_handle_post_feedback(body, actor))
    if path.startswith("feedback/") and request.method == "DELETE":
        item_id = path[len("feedback/"):]
        return _cors(_handle_delete_feedback(item_id))

    return _cors({"success": False, "error": f"unknown path: {path}"}, 404)


# ---- /scenarios ------------------------------------------------------------


def _handle_scenarios() -> dict:
    archetypes = corpus.load_archetypes()
    return {
        "success": True,
        "scenarios": [
            {
                "id": a["id"],
                "description": a.get("description", ""),
                "surfaces_covered": a.get("surfaces_covered", []),
            }
            for a in archetypes
        ],
    }


# ---- /run ------------------------------------------------------------------


# Fields the runner doesn't see (because they live on the archetype, not
# in the materialized profile/colleges) but the dashboard needs. Copied
# from archetype → scenario record after each run completes.
#
# `tests` and `surfaces_covered`: dashboard renders bullets + uses these
#   for surface-health aggregation in /summary.
# `business_rationale` (PR-I): plain-English "why this matters" copy
#   the dashboard renders in a callout above the test bullets. Optional
#   — falls back to `description` on legacy data.
# `synthesized` / `synthesis_rationale`: the LLM-generated marker + its
#   own rationale, drives the SynthesizedBadge.
_PROPAGATED_FIELDS = (
    "tests",
    "surfaces_covered",
    "business_rationale",
    "synthesized",
    "synthesis_rationale",
    "feedback_id",
    "colleges_template",
)


def _propagate_archetype_metadata(scenario_result: dict, archetype: dict) -> None:
    """Copy archetype-level fields onto the run-time scenario record.

    Mutates scenario_result in place. Always sets `tests` and
    `surfaces_covered` (defaulting to empty containers) so downstream
    code can rely on the keys existing. Other fields are only copied
    when present so legacy reports without them aren't littered with
    nulls.
    """
    scenario_result["tests"] = archetype.get("tests", [])
    scenario_result["surfaces_covered"] = archetype.get("surfaces_covered", [])
    for field in ("business_rationale", "synthesized", "synthesis_rationale",
                  "feedback_id", "colleges_template"):
        value = archetype.get(field)
        if value:
            scenario_result[field] = value


def _collect_feedback_ids(scenarios) -> list:
    """Flatten scenario.feedback_id values into a deduped list of strings.

    The synthesizer LLM emits `feedback_id` either as a single string or
    — when one scenario addresses multiple admin-feedback items — as a
    JSON array of strings. Either form must end up as a flat list of
    string ids so feedback.mark_applied can credit each one. Non-string
    entries (None, ints, dicts) are silently skipped rather than crashing
    the run.

    Order preserves first-seen so the credit log is deterministic.
    """
    seen: list = []
    for scen in scenarios or []:
        fid = scen.get("feedback_id") if isinstance(scen, dict) else None
        if isinstance(fid, str):
            if fid and fid not in seen:
                seen.append(fid)
        elif isinstance(fid, list):
            for entry in fid:
                if isinstance(entry, str) and entry and entry not in seen:
                    seen.append(entry)
        # Anything else (None, int, dict, …) → skip silently.
    return seen


def _pick_scenarios(cfg: dict, n: int, scenario_id_filter):
    """Pick the scenarios for a run without executing them. Shared by
    /run (which then runs them) and /run/preview (which just shows
    them to the user before they confirm).

    Returns a dict:
      {
        "ok": bool,
        "error": str | None,            # set when ok=False
        "archetypes": list,             # filtered archetype list
        "history": dict,                # firestore_store.load_history result
        "chosen": list,                 # synthesized + static
        "synthesized": list,            # synth picks only
        "static_picks": list,           # static picks only
        "active_feedback": list,
      }
    """
    archetypes = corpus.load_archetypes()
    if not archetypes:
        return {"ok": False, "error": "no archetypes loaded"}

    if scenario_id_filter:
        archetypes = [a for a in archetypes if a["id"] == scenario_id_filter]
        if not archetypes:
            return {
                "ok": False,
                "error": f"scenario not found: {scenario_id_filter}",
            }

    history = firestore_store.load_history([a["id"] for a in archetypes])

    # Hybrid select: synthesize some scenarios via LLM (when enabled),
    # fill the rest from the static corpus. Falls back to all-static
    # when QA_SYNTHESIS_COUNT=0 or LLM is unavailable.
    synth_n = 0 if scenario_id_filter else cfg["SYNTHESIS_COUNT"]
    synthesized: list = []
    # Feedback the admin left on the dashboard — passed into the
    # synthesizer prompt so it can target items the operator cares about.
    active_feedback: list = []
    try:
        import feedback as feedback_mod  # noqa: WPS433
        active_feedback = feedback_mod.active_items()
    except Exception as exc:  # noqa: BLE001 — non-critical
        logger.warning("qa_agent: load feedback failed (%s); proceeding without", exc)
        active_feedback = []

    if synth_n > 0:
        try:
            recent_runs = firestore_store.list_recent_runs(limit=20)
            system_knowledge = _load_system_knowledge()
            allowlist = _load_colleges_allowlist()
            synthesized = synthesizer.synthesize_scenarios(
                n=synth_n,
                history=recent_runs,
                system_knowledge=system_knowledge,
                colleges_allowlist=allowlist,
                feedback_items=active_feedback,
                gemini_key=cfg["GEMINI_API_KEY"],
            )
            logger.info(
                "qa_agent: synthesizer produced %d/%d valid scenarios",
                len(synthesized), synth_n,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("qa_agent: synthesis failed (%s); using static only", exc)
            synthesized = []

    # Top up: if the synthesizer produced fewer than requested, take
    # the slack from static so we still get `n` scenarios total.
    static_n = max(1, n - len(synthesized))
    static_picks = corpus.select_scenarios(archetypes, history, n=static_n)
    chosen = synthesized + static_picks

    # Defense-in-depth (PR #67 + this fix): normalize every archetype's
    # colleges_template to canonical ids *before* the run record is
    # written. Synthesized archetypes already validated against the
    # cleaned allowlist (so this is a no-op for them in the happy
    # path), but static archetypes don't go through validate_archetype
    # — and a future regression (alias added back to a JSON file, or
    # to the allowlist) would otherwise silently slip aliases into the
    # run record. See docs/design/qa-college-id-canonicalization.md.
    for a in chosen:
        synthesizer.canonicalize_archetype(a)

    return {
        "ok": True,
        "error": None,
        "archetypes": archetypes,
        "history": history,
        "chosen": chosen,
        "synthesized": synthesized,
        "static_picks": static_picks,
        "active_feedback": active_feedback,
    }


def _pending_scenario_stub(archetype: dict) -> dict:
    """Build the placeholder scenario record written into the
    status='running' qa_runs doc. Mirrors the final-record shape so
    the frontend's existing scenario-card rendering mostly Just Works
    while results are pending."""
    return {
        "scenario_id": archetype.get("id"),
        "status": "pending",
        "passed": None,
        "description": archetype.get("description"),
        "business_rationale": archetype.get("business_rationale"),
        "surfaces_covered": archetype.get("surfaces_covered", []),
        "tests": archetype.get("tests", []),
        "synthesized": archetype.get("synthesized", False),
        "synthesis_rationale": archetype.get("synthesis_rationale"),
        "feedback_id": archetype.get("feedback_id"),
        "colleges_template": archetype.get("colleges_template", []),
        "steps": [],
    }


def _handle_run_preview(body: dict, cfg: dict) -> dict:
    """Pick scenarios for a hypothetical /run without executing them.

    Used by the dashboard's "Run now" button to show a confirmation
    modal — the user sees what's about to be tested before committing
    2-3 minutes of test-user state churn.

    Spec: docs/prd/qa-run-preview-and-running-state.md.
    """
    scenario_id_filter = body.get("scenario") or request_arg(body, "scenario")
    n = body.get("count") or cfg["DEFAULT_SCENARIO_COUNT"]
    pick = _pick_scenarios(cfg, n, scenario_id_filter)
    if not pick["ok"]:
        return {"success": False, "error": pick["error"]}
    picked = []
    for archetype in pick["chosen"]:
        picked.append({
            "id": archetype.get("id"),
            "description": archetype.get("description"),
            "business_rationale": archetype.get("business_rationale"),
            "surfaces_covered": archetype.get("surfaces_covered", []),
            "synthesized": bool(archetype.get("synthesized")),
            "synthesis_rationale": archetype.get("synthesis_rationale"),
            "feedback_id": archetype.get("feedback_id"),
        })
    return {
        "success": True,
        "picked": picked,
        "synth_count": len(pick["synthesized"]),
        "static_count": len(pick["static_picks"]),
    }


# Stale threshold for the in-flight-run mutex check. A run that's
# been "running" longer than this is presumed dead (cloud function
# crash, OOM, etc.) and another run can proceed. Generous because
# a real run can take ~3-4 minutes end-to-end with cold starts.
_RUN_STALE_AFTER_MINUTES = 10


def _release_run_lock(run_id: str, started, trigger: str, actor: str,
                      *, error: str) -> None:
    """Mark an early-claimed lock doc as complete with a failure when
    the run never actually starts (pick_scenarios bailed, auth failed).
    Otherwise the stale "running" stub blocks all future runs until the
    10-minute staleness threshold elapses.

    Best-effort: any exception is logged but doesn't propagate, since
    the caller is already on an error path."""
    try:
        firestore_store.write_report(run_id, {
            "run_id": run_id,
            "status": "complete",
            "started_at": started.isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger,
            "actor": actor,
            "summary": {"total": 0, "pass": 0, "fail": 1},
            "scenarios": [],
            "error": error,
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent: failed to release run lock %s (%s)",
                       run_id, exc)


def _check_run_in_progress() -> "Optional[dict]":
    """Return info about an in-flight run if one is still active,
    else None. Used to prevent two /run requests from racing on the
    shared test user.

    Bug surfaced 2026-05-04 by run_20260504T210036Z_ee9985: a run
    started 19s after another run on the same test user (one was
    a manual trigger, one was scheduled), and the second run's
    setup_teardown wiped the first run's state mid-flight, then
    both runs' add-to-list calls interleaved. The result was a
    `verify_college_list_symmetry` failure with orphaned colleges
    from the other run.

    Returns dict with run_id + started_at when busy; None when free.
    A run is "busy" if status=='running' AND started_at is within
    _RUN_STALE_AFTER_MINUTES of now.
    """
    try:
        recent = firestore_store.list_recent_runs(limit=10)
    except Exception as exc:  # noqa: BLE001
        # If the lookup itself fails, prefer to allow the run rather
        # than block on a transient Firestore hiccup.
        logger.warning("qa_agent: in-flight check skipped (%s)", exc)
        return None

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=_RUN_STALE_AFTER_MINUTES)

    for run in recent:
        if run.get("status") != "running":
            continue
        started_str = run.get("started_at") or ""
        if not started_str:
            continue
        try:
            started_dt = datetime.fromisoformat(
                started_str.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            continue
        if started_dt > cutoff:
            return {
                "run_id": run.get("run_id"),
                "started_at": started_str,
            }
    return None


def _handle_run(body: dict, cfg: dict):
    """Execute a QA run. Returns either a dict (HTTP 200 implicit) or
    a (dict, status_code) tuple when an explicit status is needed
    (e.g. 429 when another run is in flight)."""
    trigger = body.get("trigger", "manual")
    scenario_id_filter = body.get("scenario") or request_arg(body, "scenario")
    n = body.get("count") or cfg["DEFAULT_SCENARIO_COUNT"]
    actor = body.get("actor", "anonymous")

    # The hourly Cloud Scheduler poll fires with trigger=schedule_check.
    # No-op unless the user-configured schedule says NOW is a run time.
    if trigger == "schedule_check":
        try:
            current_schedule = schedule.load_schedule()
            if not schedule.should_run_now(current_schedule, datetime.now(timezone.utc)):
                logger.info("qa_agent: schedule_check skipped — not in window")
                return {"success": True, "skipped": True}
        except Exception as exc:  # noqa: BLE001
            # If the schedule check itself errors, log + skip rather
            # than silently running. A missed run is recoverable; a
            # schedule-config error firing every hour is not.
            logger.exception("qa_agent: schedule_check failed; skipping")
            return {"success": False, "skipped": True, "error": str(exc)}

    # Mutex: refuse to start a run if another is already in flight on
    # the same test user. Two runs racing on the shared user produce
    # indeterminate state (verify_college_list_symmetry fails, etc.).
    busy = _check_run_in_progress()
    if busy:
        logger.info(
            "qa_agent: refusing concurrent run; %s is in flight (started %s)",
            busy.get("run_id"), busy.get("started_at"),
        )
        return ({
            "success": False,
            "skipped": True,
            "error": (
                f"another run is in flight: {busy.get('run_id')} "
                f"(started {busy.get('started_at')}); retry shortly"
            ),
            "in_flight_run_id": busy.get("run_id"),
        }, 429)

    # Claim the lock IMMEDIATELY by writing a status="running" stub.
    # Without this, two concurrent /run requests both pass the mutex
    # check (since neither has written its stub yet) and the race
    # repeats. Writing here narrows the window to a single Firestore
    # write (~tens of ms) instead of the ~5-10s of Gemini calls in
    # _pick_scenarios + narratives.build_plan that follow.
    #
    # The stub is minimal (no scenarios yet — those come from
    # _pick_scenarios). We update it later with the full scenario
    # list once we know what the run will actually execute.
    started = datetime.now(timezone.utc)
    run_id = f"run_{started.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:6]}"
    firestore_store.write_report(run_id, {
        "run_id": run_id,
        "status": "running",
        "started_at": started.isoformat(),
        "trigger": trigger,
        "actor": actor,
        "summary": {"total": 0, "pass": 0, "fail": 0},
        "scenarios": [],
        "test_plan": None,
    })

    pick = _pick_scenarios(cfg, n, scenario_id_filter)
    if not pick["ok"]:
        # Release the lock — flip the stub to "complete" so the next
        # /run isn't blocked by a stale running doc that never started.
        _release_run_lock(run_id, started, trigger, actor,
                          error=pick["error"])
        return {"success": False, "error": pick["error"]}
    archetypes = pick["archetypes"]
    history = pick["history"]
    chosen = pick["chosen"]
    active_feedback = pick["active_feedback"]

    # Authenticate as the test user before running scenarios. If the
    # token mint fails, every scenario will fail predictably; we surface
    # that as a top-level error rather than running the rest in a doomed
    # state.
    try:
        id_token = auth.get_id_token(cfg["TEST_USER_UID"], cfg["FIREBASE_API_KEY"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: failed to mint test-user ID token")
        err = f"auth: {type(exc).__name__}: {exc}"
        _release_run_lock(run_id, started, trigger, actor, error=err)
        return {"success": False, "error": err}

    run_cfg = runner.RunConfig(
        profile_manager_url=cfg["PROFILE_MANAGER_URL"],
        counselor_agent_url=cfg["COUNSELOR_AGENT_URL"],
        admin_token=cfg["ADMIN_TOKEN"],
        id_token=id_token,
        test_user_email=cfg["TEST_USER_EMAIL"],
        knowledge_base_url=cfg["KNOWLEDGE_BASE_URL"],
    )

    # Pre-run: ask the planner for a test_plan narrative + structured
    # rationale + coverage. Cheap (one Gemini Flash call), gives the
    # dashboard the "what is this run testing and why" context.
    test_plan = narratives.build_plan(chosen, history, gemini_key=cfg["GEMINI_API_KEY"])

    # Update the running stub now that we know what scenarios will
    # execute. The dashboard's "Running" placeholder gets the full
    # scenario list + test_plan; lock doc was written earlier (above)
    # so concurrent /run requests already see this run as in-flight.
    # See docs/prd/qa-run-preview-and-running-state.md.
    firestore_store.write_report(run_id, {
        "run_id": run_id,
        "status": "running",
        "started_at": started.isoformat(),
        "trigger": trigger,
        "actor": actor,
        "summary": {"total": len(chosen), "pass": 0, "fail": 0},
        "scenarios": [_pending_scenario_stub(a) for a in chosen],
        "test_plan": test_plan,
    })

    scenarios_results = []
    for archetype in chosen:
        variation = corpus.generate_variation(archetype, api_key=cfg["GEMINI_API_KEY"])
        materialized = corpus.apply_variation(archetype, variation)
        result = runner.run_scenario(materialized, run_cfg)
        _propagate_archetype_metadata(result, archetype)
        scenarios_results.append(result)
        firestore_store.update_history(
            archetype["id"],
            last_result="pass" if result["passed"] else "fail",
        )

    ended = datetime.now(timezone.utc)
    summary = {
        "total": len(scenarios_results),
        "pass": sum(1 for r in scenarios_results if r["passed"]),
        "fail": sum(1 for r in scenarios_results if not r["passed"]),
    }
    report = {
        "run_id": run_id,
        # status="complete" flips the dashboard from the "Running"
        # placeholder to the final pass/fail badge.
        "status": "complete",
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_ms": int((ended - started).total_seconds() * 1000),
        "trigger": trigger,
        "actor": actor,
        "summary": summary,
        "scenarios": scenarios_results,
        "test_plan": test_plan,
    }

    # Post-run: ask the planner for an outcome narrative + verdict +
    # first-look-at pointer. Verdict is computed deterministically from
    # the report (never LLM-derived).
    report["outcome"] = narratives.build_outcome(report, gemini_key=cfg["GEMINI_API_KEY"])

    firestore_store.write_report(run_id, report)
    logger.info("qa_agent: run %s complete — %d pass / %d fail",
                run_id, summary["pass"], summary["fail"])

    # Credit feedback items that drove a synthesized scenario, so the
    # dashboard's applied_count reflects which notes the agent has
    # addressed and the auto-dismiss threshold can fire.
    feedback_ids_used = _collect_feedback_ids(chosen)
    if feedback_ids_used:
        try:
            import feedback as feedback_mod  # noqa: WPS433
            feedback_mod.mark_applied(feedback_ids_used, run_id=run_id)
        except Exception as exc:  # noqa: BLE001 — non-critical
            logger.warning("qa_agent: mark_applied failed (%s)", exc)

    return {"success": True, "run_id": run_id, "summary": summary}


# ---- /schedule -------------------------------------------------------------


def _handle_get_schedule() -> dict:
    try:
        return {"success": True, "schedule": schedule.load_schedule()}
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: load_schedule failed")
        return {"success": False, "error": str(exc)}


def _handle_post_schedule(body: dict, actor: str) -> dict:
    err = schedule.validate_schedule(body)
    if err:
        return {"success": False, "error": err}
    try:
        schedule.save_schedule(body, actor=actor or "")
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: save_schedule failed")
        return {"success": False, "error": str(exc)}


# ---- /summary --------------------------------------------------------------


def _handle_summary(cfg: dict, request=None) -> dict:
    try:
        # Lazy imports keep unrelated requests from paying the import
        # cost, and avoid pulling firestore at module load time.
        import dashboard_prefs  # noqa: WPS433
        import coverage as coverage_mod  # noqa: WPS433
        import resolved_issues as resolved_issues_mod  # noqa: WPS433

        # Resolve recent_n: ?recent_n= query param wins, else stored prefs,
        # else default. The query param is admin-debug only — the saved
        # prefs is the source of truth that powers the dashboard pill.
        prefs = dashboard_prefs.load_prefs()
        recent_n = prefs.get("recent_n", 20)
        if request is not None:
            try:
                qp = request.args.get("recent_n")
                if qp:
                    recent_n = int(qp)
            except (TypeError, ValueError):
                pass

        runs = firestore_store.list_recent_runs(limit=60)
        # Pass the colleges allowlist into coverage so it can compute
        # universities_untested (allowlist - tested). Allowlist is
        # cheap to load (a small JSON), no need to cache.
        try:
            colleges_allowlist = _load_colleges_allowlist()
        except Exception:  # noqa: BLE001
            colleges_allowlist = []
        return {
            "success": True,
            "summary": narratives.build_summary(
                runs,
                recent_n=recent_n,
                gemini_key=cfg["GEMINI_API_KEY"],
            ),
            # End-to-end journeys the QA agent has VERIFIED across recent
            # runs. Ships in /summary so the dashboard fetches once.
            "coverage": coverage_mod.build_coverage(
                runs, colleges_allowlist=colleges_allowlist,
            ),
            # Recent FAIL → PASS transitions, evidence preserved.
            "resolved_issues": resolved_issues_mod.build_resolved_issues(runs),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: build_summary failed")
        return {"success": False, "error": str(exc)}


def _handle_get_dashboard_prefs() -> dict:
    """GET /dashboard-prefs — returns the current prefs (or defaults)."""
    try:
        import dashboard_prefs  # noqa: WPS433
        return {"success": True, "prefs": dashboard_prefs.load_prefs()}
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: load_prefs failed")
        return {"success": False, "error": str(exc)}


def _handle_post_dashboard_prefs(body: dict, actor: str) -> dict:
    """POST /dashboard-prefs — validate + save."""
    try:
        import dashboard_prefs  # noqa: WPS433
        err = dashboard_prefs.validate_prefs(body)
        if err:
            return {"success": False, "error": err}
        dashboard_prefs.save_prefs(body, actor=actor)
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: save_prefs failed")
        return {"success": False, "error": str(exc)}


# ---- /feedback -------------------------------------------------------------


def _handle_get_feedback() -> dict:
    """GET /feedback — list active items + the most recent retirements.

    `items` is the active list (unchanged shape; existing clients
    keep working). `recently_dismissed` is the new field the Steer
    panel uses to show "feedback that already drove runs and
    auto-retired" — fixes the dashboard loop where an operator's
    note hit max_applies and silently disappeared.
    """
    try:
        import feedback  # noqa: WPS433
        return {
            "success": True,
            "items": feedback.active_items(),
            "recently_dismissed": feedback.recently_dismissed_items(),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: load feedback failed")
        return {"success": False, "error": str(exc)}


def _handle_post_feedback(body: dict, actor: str) -> dict:
    """POST /feedback — add a new active item."""
    try:
        import feedback  # noqa: WPS433
        text = body.get("text") or ""
        max_applies = body.get("max_applies", feedback.DEFAULT_MAX_APPLIES)
        item = feedback.add_item(text, actor=actor, max_applies=max_applies)
        return {"success": True, "item": item}
    except ValueError as exc:
        # Validation error: 400-shaped response. Caller maps to 400 if
        # we ever refactor; for now we keep the {success: false} shape
        # consistent with the rest of qa-agent.
        return {"success": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: add feedback failed")
        return {"success": False, "error": str(exc)}


def _handle_delete_feedback(item_id: str) -> dict:
    """DELETE /feedback/<id> — dismiss the item."""
    try:
        import feedback  # noqa: WPS433
        ok = feedback.dismiss(item_id)
        if not ok:
            return {"success": False, "error": f"no feedback item with id {item_id!r}"}
        return {"success": True}
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: dismiss feedback failed")
        return {"success": False, "error": str(exc)}


# ---- /suggest-cause --------------------------------------------------------


# In-memory dedup so repeated clicks on "Suggest cause" for the same
# (run_id, scenario_id) reuse the cached answer rather than re-billing
# Gemini. Lifetime is the function instance — fine for the use case
# (admin clicks happen in bursts during a single debugging session).
_SUGGESTION_CACHE: dict = {}


def _handle_suggest_cause(body: dict, cfg: dict) -> dict:
    run_id = body.get("run_id")
    scenario_id = body.get("scenario_id")
    if not run_id or not scenario_id:
        return {"success": False, "error": "run_id and scenario_id required"}

    cache_key = f"{run_id}::{scenario_id}"
    if cache_key in _SUGGESTION_CACHE:
        return {
            "success": True,
            "suggestion": _SUGGESTION_CACHE[cache_key],
            "cached": True,
        }

    report = firestore_store.read_report(run_id)
    if not report:
        return {"success": False, "error": f"run {run_id} not found"}

    scenario = next(
        (s for s in report.get("scenarios", []) if s.get("scenario_id") == scenario_id),
        None,
    )
    if not scenario:
        return {
            "success": False,
            "error": f"scenario {scenario_id} not in run {run_id}",
        }

    api_key = cfg.get("GEMINI_API_KEY")
    suggestion = _gemini_suggest(scenario, api_key)
    _SUGGESTION_CACHE[cache_key] = suggestion
    return {"success": True, "suggestion": suggestion, "cached": False}


def _gemini_suggest(scenario: dict, api_key: str | None) -> str:
    """Call Gemini Flash for a 2-3 paragraph analysis of a failing
    scenario. On any failure (no key, malformed response, etc.) returns
    a fallback string so the dashboard always renders something."""
    failing_steps = [s for s in scenario.get("steps", []) if not s.get("passed")]
    if not failing_steps:
        return "Every step in this scenario passed; no analysis needed."

    if not api_key:
        return _heuristic_suggest(failing_steps)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = _build_suggest_prompt(scenario, failing_steps)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        return text or _heuristic_suggest(failing_steps)
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent: Gemini suggest failed (%s); using heuristic", exc)
        return _heuristic_suggest(failing_steps)


def _build_suggest_prompt(scenario: dict, failing_steps: list) -> str:
    excerpt_lines = []
    for step in failing_steps[:5]:
        failed_assertions = [
            a for a in step.get("assertions", [])
            if not a.get("passed")
        ]
        excerpt_lines.append(
            f"- step '{step.get('name')}' (status {step.get('status_code')}, "
            f"{step.get('elapsed_ms')}ms) at {step.get('endpoint')}\n"
            f"    failed assertions: "
            f"{[a.get('name') + ': ' + (a.get('message') or '') for a in failed_assertions]}\n"
            f"    response: {(step.get('response_excerpt') or '')[:500]}"
        )
    excerpt = "\n".join(excerpt_lines)

    return f"""You are analyzing a failed test run from a synthetic-monitoring agent that hits production endpoints. Distinguish between an "agent bug" (the test's expectations are wrong) and an "app regression" (production behavior changed). Be concrete and cite specific request/response fields.

Scenario: {scenario.get("description")}
Variation: {scenario.get("variation")}

Failing steps:
{excerpt}

In 2-3 short paragraphs:
1. State whether this is most likely an agent bug or an app regression, with reasoning.
2. Name the specific change in the response shape, status code, or behavior that's the proximate cause.
3. Suggest the smallest fix or next investigation step.

Be direct. No preamble. No disclaimers about being an AI."""


def _heuristic_suggest(failing_steps: list) -> str:
    """Fallback when the LLM call fails — string together the failing
    assertions so the operator at least sees the proximate symptoms."""
    lines = ["**Heuristic analysis (LLM unavailable)**", ""]
    for step in failing_steps[:5]:
        lines.append(
            f"- `{step.get('name')}` returned status {step.get('status_code')}"
        )
        for a in step.get("assertions", []):
            if not a.get("passed"):
                lines.append(f"    - failed: {a.get('name')} — {a.get('message')}")
    lines.append("")
    lines.append(
        "Next step: read the failing step's response excerpt to see whether "
        "the endpoint shape changed (likely an app regression) or the "
        "assertion is referencing a field that no longer exists (likely "
        "an agent bug)."
    )
    return "\n".join(lines)


# ---- /github-issue ---------------------------------------------------------


def _handle_github_issue(body: dict, cfg: dict) -> dict:
    """Build a pre-filled GitHub issue URL for a failing scenario. The
    browser opens this URL in a new tab and the user reviews + submits
    manually. We don't create the issue server-side — that would require
    a stored GH token, which is a heavier ops commitment than this PR
    needs."""
    run_id = body.get("run_id")
    scenario_id = body.get("scenario_id")
    if not run_id or not scenario_id:
        return {"success": False, "error": "run_id and scenario_id required"}

    report = firestore_store.read_report(run_id)
    if not report:
        return {"success": False, "error": f"run {run_id} not found"}

    scenario = next(
        (s for s in report.get("scenarios", []) if s.get("scenario_id") == scenario_id),
        None,
    )
    if not scenario:
        return {
            "success": False,
            "error": f"scenario {scenario_id} not in run {run_id}",
        }

    title = f"[QA] {scenario_id} failed in {run_id}"
    body_text = _build_issue_body(report, scenario)
    repo = cfg["GITHUB_REPO"]
    url = (
        f"https://github.com/{repo}/issues/new"
        f"?title={urllib.parse.quote(title)}"
        f"&body={urllib.parse.quote(body_text)}"
    )
    # GitHub's URL prefilling tops out around 8KB. If we're over, return
    # a title-only URL and signal to the caller; the body becomes
    # something the user pastes from clipboard.
    if len(url) > 7800:
        body_text_truncated = body_text[:5000] + "\n\n*(truncated — see admin dashboard for full detail)*"
        url = (
            f"https://github.com/{repo}/issues/new"
            f"?title={urllib.parse.quote(title)}"
            f"&body={urllib.parse.quote(body_text_truncated)}"
        )

    return {
        "success": True,
        "issue_url": url,
        "issue_title": title,
        "issue_body": body_text,
    }


def _build_issue_body(report: dict, scenario: dict) -> str:
    failing_steps = [s for s in scenario.get("steps", []) if not s.get("passed")]
    summary = report.get("summary", {})
    parts = [
        f"**QA agent run**: `{report.get('run_id')}`  ",
        f"**Scenario**: `{scenario.get('scenario_id')}`  ",
        f"**Status**: FAIL  ",
        f"**Run summary**: {summary.get('pass')}/{summary.get('total')} scenarios passed  ",
        f"**Trigger**: {report.get('trigger')} by {report.get('actor')}  ",
        f"**Started**: {report.get('started_at')}",
        "",
        f"### Description",
        f"{scenario.get('description')}",
        "",
        f"### Variation",
        "```json",
        json.dumps(scenario.get("variation") or {}, indent=2),
        "```",
        "",
        f"### Failing steps",
    ]
    for step in failing_steps[:5]:
        parts.append(f"#### `{step.get('name')}` — {step.get('status_code')} ({step.get('elapsed_ms')}ms)")
        parts.append(f"- Endpoint: `{step.get('endpoint')}`")
        parts.append("- Failed assertions:")
        for a in step.get("assertions", []):
            if not a.get("passed"):
                parts.append(f"  - `{a.get('name')}` — {a.get('message')}")
        parts.append("")
        parts.append("- Request:")
        parts.append("  ```json")
        parts.append("  " + json.dumps(step.get("request") or {}, indent=2).replace("\n", "\n  "))
        parts.append("  ```")
        parts.append("- Response (excerpt):")
        parts.append("  ```")
        parts.append("  " + (step.get("response_excerpt") or "").replace("\n", "\n  ")[:1500])
        parts.append("  ```")
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("*Generated by the QA agent dashboard. Please add reproduction context before submitting.*")
    return "\n".join(parts)


# ---- Helpers ---------------------------------------------------------------


def request_arg(body, key):
    """Helper for both body and query-string lookups (Cloud Scheduler
    sends a body; curl users sometimes pass ?scenario=)."""
    val = body.get(key)
    if val:
        return val
    return None


# ---- Synthesizer support files ---------------------------------------------


def _load_system_knowledge() -> str:
    """Read system_knowledge.md from disk. Returns empty string on error
    — synthesizer will then produce an empty list, caller uses static
    fallback."""
    try:
        path = os.path.join(os.path.dirname(__file__), "system_knowledge.md")
        with open(path) as f:
            return f.read()
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent: failed to read system_knowledge.md: %s", exc)
        return ""


def _load_colleges_allowlist() -> list:
    """Read scenarios/colleges_allowlist.json. Returns empty list on
    error — synthesizer rejects all candidates if the allowlist is
    empty, caller uses static fallback."""
    try:
        path = os.path.join(
            os.path.dirname(__file__), "scenarios", "colleges_allowlist.json",
        )
        with open(path) as f:
            data = json.load(f)
        return data.get("colleges", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent: failed to read colleges_allowlist.json: %s", exc)
        return []
