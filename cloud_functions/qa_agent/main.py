"""
QA Agent — Cloud Function entry point.

POST /run                   → run a fresh batch (4-5 scenarios)
POST /run?scenario=<id>     → run one specific archetype
GET  /                      → liveness ping

Trigger sources:
  - Cloud Scheduler (daily) — request body {"trigger":"schedule"}
  - Admin UI "Run now" button — request body {"trigger":"manual"}
  - curl from a developer's laptop for ad-hoc runs

Auth: every request must carry the QA agent's admin token in the
X-Admin-Token header (rotated via Secret Manager). The token is the
single line of defense against accidental triggers from outside; it is
NOT a substitute for the test user email allowlist enforced inside
profile_manager_v2's clear-test-data endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

import functions_framework
from flask import jsonify

import auth
import corpus
import firestore_store
import runner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---- Configuration ---------------------------------------------------------


def _config():
    """Pulled fresh per request so unit tests can override env."""
    return {
        "PROFILE_MANAGER_URL": os.getenv("PROFILE_MANAGER_URL"),
        "COUNSELOR_AGENT_URL": os.getenv("COUNSELOR_AGENT_URL"),
        "ADMIN_TOKEN": os.getenv("QA_ADMIN_TOKEN"),
        "TEST_USER_EMAIL": os.getenv("QA_TEST_USER_EMAIL", "duser8531@gmail.com"),
        "TEST_USER_UID": os.getenv("QA_TEST_USER_UID", ""),
        "FIREBASE_API_KEY": os.getenv("FIREBASE_WEB_API_KEY"),
        "DEFAULT_SCENARIO_COUNT": int(os.getenv("QA_SCENARIO_COUNT", "4")),
    }


# ---- CORS helper -----------------------------------------------------------


def _cors(payload, status=200):
    resp = jsonify(payload) if isinstance(payload, dict) else payload
    resp.status_code = status
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Token"
    return resp


def _check_admin_token(request, expected_token: str) -> bool:
    """Constant-time check on X-Admin-Token. Empty expected token rejects
    everything (prevents misconfigured deploys from being open)."""
    if not expected_token:
        return False
    provided = request.headers.get("X-Admin-Token", "")
    return secrets.compare_digest(provided, expected_token)


# ---- Entry point -----------------------------------------------------------


@functions_framework.http
def qa_agent(request):
    if request.method == "OPTIONS":
        return _cors({"status": "ok"})

    cfg = _config()
    path = request.path.strip("/")

    if path in ("", "health"):
        return _cors({"status": "ok", "test_user": cfg["TEST_USER_EMAIL"]})

    if path != "run":
        return _cors({"success": False, "error": f"unknown path: {path}"}, 404)

    if not _check_admin_token(request, cfg["ADMIN_TOKEN"]):
        return _cors({"success": False, "error": "unauthorized"}, 401)

    body = request.get_json(silent=True) or {}
    return _cors(_handle_run(body, cfg))


# ---- Run handler -----------------------------------------------------------


def _handle_run(body: dict, cfg: dict) -> dict:
    trigger = body.get("trigger", "manual")
    scenario_id_filter = body.get("scenario") or request_arg(body, "scenario")
    n = body.get("count") or cfg["DEFAULT_SCENARIO_COUNT"]
    actor = body.get("actor", "anonymous")

    archetypes = corpus.load_archetypes()
    if not archetypes:
        return {"success": False, "error": "no archetypes loaded"}

    if scenario_id_filter:
        archetypes = [a for a in archetypes if a["id"] == scenario_id_filter]
        if not archetypes:
            return {
                "success": False,
                "error": f"scenario not found: {scenario_id_filter}",
            }

    history = firestore_store.load_history([a["id"] for a in archetypes])
    chosen = corpus.select_scenarios(archetypes, history, n=n)

    # Authenticate as the test user before running scenarios. If the
    # token mint fails, every scenario will fail predictably; we surface
    # that as a top-level error rather than running the rest in a doomed
    # state.
    try:
        id_token = auth.get_id_token(cfg["TEST_USER_UID"], cfg["FIREBASE_API_KEY"])
    except Exception as exc:  # noqa: BLE001
        logger.exception("qa_agent: failed to mint test-user ID token")
        return {"success": False, "error": f"auth: {type(exc).__name__}: {exc}"}

    run_cfg = runner.RunConfig(
        profile_manager_url=cfg["PROFILE_MANAGER_URL"],
        counselor_agent_url=cfg["COUNSELOR_AGENT_URL"],
        admin_token=cfg["ADMIN_TOKEN"],
        id_token=id_token,
        test_user_email=cfg["TEST_USER_EMAIL"],
    )

    started = datetime.now(timezone.utc)
    run_id = f"run_{started.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:6]}"

    scenarios_results = []
    for archetype in chosen:
        variation = corpus.generate_variation(archetype, api_key=os.getenv("GEMINI_API_KEY"))
        materialized = corpus.apply_variation(archetype, variation)
        result = runner.run_scenario(materialized, run_cfg)
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
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_ms": int((ended - started).total_seconds() * 1000),
        "trigger": trigger,
        "actor": actor,
        "summary": summary,
        "scenarios": scenarios_results,
    }
    firestore_store.write_report(run_id, report)
    logger.info("qa_agent: run %s complete — %d pass / %d fail",
                run_id, summary["pass"], summary["fail"])
    return {"success": True, "run_id": run_id, "summary": summary}


def request_arg(body, key):
    """Helper for both body and query-string lookups (Cloud Scheduler
    sends a body; curl users sometimes pass ?scenario=)."""
    val = body.get(key)
    if val:
        return val
    return None
