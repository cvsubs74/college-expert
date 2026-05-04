"""
QA Agent Chat — admin Q&A grounded in recent run reports.

Specs: docs/prd/qa-agent-chat.md, docs/design/qa-agent-chat.md.

Single endpoint, admin-only, gated by the same allowlist as the rest of
qa-agent. Stateless per session (no Firestore persistence for chat
history). Uses Gemini 2.5 Flash with last-30-run summaries as context.

Public surface:
  handle_chat(body: dict, cfg: dict) -> (response_dict, status_code)

Helpers (also tested directly):
  _system_prompt() -> str
  _format_run_context(runs: List[dict]) -> str
  _format_history(history: List[dict]) -> str
  _load_recent_run_summaries(limit: int = 30) -> List[dict]
  _call_gemini(system: str, prompt: str, api_key: str) -> str
"""

from __future__ import annotations

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


# ---- Public handler --------------------------------------------------------


def handle_chat(body: dict, cfg: dict) -> Tuple[dict, int]:
    """Validate input, load context, call Gemini, return answer.

    Returns (response_dict, status_code). The qa-agent dispatcher in
    main.py wraps this with CORS and returns the response.
    """
    question = (body.get("question") or "").strip()
    if not question:
        return {"success": False, "error": "question is required"}, 400

    history = body.get("history", [])
    if not isinstance(history, list):
        return {"success": False, "error": "history must be a list"}, 400

    runs = _load_recent_run_summaries(limit=30)
    if not runs:
        return {
            "success": False,
            "error": "no QA runs found yet — trigger a run before chatting",
        }, 400

    feedback_ctx = _load_feedback_context()

    system = _system_prompt()
    context_text = _format_run_context(runs)
    feedback_text = _format_feedback_context(
        feedback_ctx["active"], feedback_ctx["dismissed"],
    )
    history_text = _format_history(history)
    prompt = (
        f"{context_text}\n\n"
        f"{feedback_text}\n\n"
        f"{history_text}\n\n"
        f"User: {question}"
    )

    try:
        answer = _call_gemini(system, prompt, cfg.get("GEMINI_API_KEY"))
    except Exception as exc:  # noqa: BLE001 — model call can fail many ways
        logger.warning("qa_agent: chat Gemini call failed: %s", exc)
        return {
            "success": False,
            "error": f"chat backend temporarily unavailable: {exc}",
        }, 503

    return {
        "success": True,
        "answer": answer,
        "model": "gemini-2.5-flash",
        "context_run_count": len(runs),
    }, 200


# ---- System prompt ---------------------------------------------------------


_SYSTEM_PROMPT = """You are a QA analyst answering questions about scheduled
monitoring runs of the Stratia Admissions college-admissions system. You have
access to summaries of the most recent QA runs (run ID, pass/fail counts,
trigger, and for failing scenarios the failing step name + a short assertion
message), plus a list of admin-authored feedback notes that steer scenario
synthesis (active and recently retired).

Rules:
- Ground every answer in the supplied context. If the user asks about
  something not in the context, say so plainly — never invent run IDs,
  scenario IDs, assertions, or feedback notes.
- Cite specific run IDs and scenario IDs when possible so the operator can
  drill in.
- When a question touches operator feedback, join `feedback_id` stamps on
  scenarios with the corresponding feedback `text` from the feedback
  section. Quote the operator's actual note text rather than just the id.
- Keep answers concise (1-3 paragraphs unless the user asks for more detail
  or for a list).
- If the context shows a clear pattern (the same scenario failing repeatedly,
  a specific step regressing across runs, etc.), surface it.
- If recent runs are all passing, say so confidently — don't manufacture
  concerns.
- The QA agent runs every 30 minutes by default. "Recent" means the last
  hour or two unless the user specifies otherwise.
"""


def _system_prompt() -> str:
    return _SYSTEM_PROMPT


# ---- Run-context formatting ------------------------------------------------
#
# Budget: aim for <30k chars (~7k tokens) so a 60-run history fits with
# room for system prompt + history + answer. Each run gets a one-line
# header and (for failing scenarios) one indented line per failing step.
# Pass-only scenarios are summarized in the header — no per-step detail.
#
# Format (plain text, easy for the LLM to scan):
#   run_20260504T010246Z_bdba3a · 5/8 pass · 2026-05-04T01:02 · agent_loop
#       FAIL synth_high_achiever_junior_all_ucs / roadmap_generate
#         metadata.template_used=='junior_fall': got 'sophomore_spring'
#       FAIL freshman_fall_starter / roadmap_generate
#         metadata.template_used=='freshman_fall': got 'freshman_spring'


_MAX_CONTEXT_CHARS = 28000  # safe under the 30k soft cap from tests
_MAX_FAILING_PER_RUN = 5     # avoid one spectacular bad run dominating context
_ASSERTION_MSG_TRUNCATE = 160


def _format_run_context(runs: List[dict]) -> str:
    if not runs:
        return "There are no QA runs to summarize yet (0 runs)."

    lines: List[str] = []
    total_size = 0
    for run in runs:
        run_lines = _format_one_run(run)
        block = "\n".join(run_lines) + "\n"
        if total_size + len(block) > _MAX_CONTEXT_CHARS:
            lines.append(
                f"\n[truncated — {len(runs) - len([l for l in lines if l.startswith('run_')])} "
                f"older runs omitted to stay within prompt budget]"
            )
            break
        lines.extend(run_lines)
        total_size += len(block)
    return "Recent QA runs (most recent first):\n" + "\n".join(lines)


def _format_one_run(run: dict) -> List[str]:
    summary = run.get("summary") or {}
    pass_n = summary.get("pass", 0)
    total = summary.get("total", 0)
    started = run.get("started_at", "")
    trigger = run.get("trigger", "")
    run_id = run.get("run_id", "<unknown>")

    header = f"run {run_id} · {pass_n}/{total} pass · {started} · {trigger}"
    out = [header]

    # Distinct colleges exercised in this run — answers "what schools
    # has the QA agent covered?". Skip the line entirely when no
    # scenarios carry colleges_template (legacy runs) so we don't
    # render an empty "colleges:" line.
    colleges_seen: List[str] = []
    seen: set = set()
    for scen in run.get("scenarios") or []:
        for uni in scen.get("colleges_template") or []:
            if not isinstance(uni, str) or not uni or uni in seen:
                continue
            seen.add(uni)
            colleges_seen.append(uni)
    if colleges_seen:
        out.append(f"    colleges: {', '.join(colleges_seen)}")

    # Per-failing-scenario detail (capped).
    failing = [s for s in (run.get("scenarios") or []) if not _is_passed(s)]
    for scen in failing[:_MAX_FAILING_PER_RUN]:
        scen_id = scen.get("scenario_id", "<unknown>")
        for step in scen.get("steps") or []:
            if _is_passed(step):
                continue
            step_name = step.get("name", "<step>")
            # First failing assertion message — truncated.
            msg = ""
            for a in step.get("assertions") or []:
                if not _is_passed(a):
                    msg = (a.get("message") or "")[:_ASSERTION_MSG_TRUNCATE]
                    break
            out.append(f"    FAIL {scen_id} / {step_name}: {msg}")
    if len(failing) > _MAX_FAILING_PER_RUN:
        out.append(f"    ... ({len(failing) - _MAX_FAILING_PER_RUN} more failing scenarios omitted)")
    return out


def _is_passed(d: dict) -> bool:
    """Firestore sometimes returns booleans as strings ('True'/'False')
    when round-tripping; tolerate both."""
    v = d.get("passed")
    if v is True:
        return True
    if isinstance(v, str) and v.lower() == "true":
        return True
    return False


# ---- History formatting ----------------------------------------------------


def _format_history(history: List[dict]) -> str:
    if not history:
        return "(no prior conversation in this session)"
    parts = []
    for msg in history:
        role = (msg.get("role") or "user").lower()
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        prefix = "User" if role == "user" else "Assistant"
        parts.append(f"{prefix}: {content}")
    return "Conversation so far:\n" + "\n".join(parts) if parts else (
        "(no prior conversation in this session)"
    )


# ---- Feedback context ------------------------------------------------------
#
# So an operator can ask "did my note about UC group treatment drive
# any runs?" and the LLM can join the feedback_id stamped on scenarios
# back to the original note text. Without this section, the chat sees
# `feedback_id: fb_xyz` and has no idea what fb_xyz said.

# Caps so a long-running setup with lots of retired notes doesn't blow
# the prompt budget. Active items already cap at MAX_ACTIVE_ITEMS=10
# in feedback.py; we mirror that for symmetry.
_MAX_FEEDBACK_ITEMS_PER_GROUP = 10
_FEEDBACK_TEXT_TRUNCATE = 200


def _load_feedback_context() -> dict:
    """Fetch active + recently-dismissed feedback items.

    Returns {"active": [...], "dismissed": [...]} on success and on any
    failure (a feedback-store outage must NOT take down the chat
    endpoint — the chat is more useful answering "what's broken" than
    refusing to answer because feedback storage is down).
    """
    try:
        import feedback  # noqa: WPS433 — lazy import for test stubs
        return {
            "active": feedback.active_items() or [],
            "dismissed": feedback.recently_dismissed_items() or [],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("qa_agent: chat could not load feedback (%s)", exc)
        return {"active": [], "dismissed": []}


def _format_feedback_context(active: List[dict], dismissed: List[dict]) -> str:
    """Render active + retired feedback as a compact prompt section so
    the LLM can answer 'did my note X drive any runs?' by joining the
    feedback_id stamps in run records back to the operator's note text.
    """
    if not active and not dismissed:
        return ("Admin feedback (operator notes that steer the synthesizer):\n"
                "(no operator feedback in scope)")

    lines = ["Admin feedback (operator notes that steer the synthesizer):"]
    for it in (active or [])[:_MAX_FEEDBACK_ITEMS_PER_GROUP]:
        lines.append(_format_feedback_item(it, status_label="ACTIVE"))
    for it in (dismissed or [])[:_MAX_FEEDBACK_ITEMS_PER_GROUP]:
        lines.append(_format_feedback_item(it, status_label="RETIRED"))
    return "\n".join(lines)


def _format_feedback_item(it: dict, *, status_label: str) -> str:
    fid = it.get("id", "<unknown>")
    text = (it.get("text") or "")[:_FEEDBACK_TEXT_TRUNCATE]
    applied = it.get("applied_count", 0)
    cap = it.get("max_applies", 5)
    last_run = it.get("last_applied_run_id")
    bits = [f"  - {status_label}: {fid} · applied {applied}/{cap}"]
    if last_run:
        bits.append(f"last_run={last_run}")
    bits.append(f'"{text}"')
    return " · ".join(bits)


# ---- Firestore loader ------------------------------------------------------


def _load_recent_run_summaries(limit: int = 30) -> List[dict]:
    """Pull the most recent N qa_runs docs. Already-existing helper in
    firestore_store; this thin wrapper just keeps chat.py self-contained
    for tests that monkeypatch it."""
    import firestore_store  # noqa: WPS433 — lazy import for test stubs
    return firestore_store.list_recent_runs(limit=limit)


# ---- Gemini call -----------------------------------------------------------


def _call_gemini(system: str, prompt: str, api_key: str) -> str:
    """Single-shot Gemini Flash call. Matches the pattern used by
    narratives.py + synthesizer.py so we share auth + library setup."""
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    import google.generativeai as genai  # noqa: WPS433
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system,
    )
    resp = model.generate_content(prompt)
    text = (getattr(resp, "text", None) or "").strip()
    if not text:
        raise RuntimeError("model returned empty response")
    return text
