# PRD — QA Agent Chat

## Problem

The internal QA dashboard at `stratiaadmissions.com/qa-runs` shows what's been tested but doesn't help the operator make sense of it. To answer questions like "is the system getting healthier?", "which scenarios fail most often?", "what's the most common failure mode this week?", the operator currently has to click through individual run reports and reason from raw data.

The dashboard already has an executive summary card (a single LLM-generated paragraph), but it's static — written once per run, no follow-up. The operator can't ask clarifying questions, can't pivot to a different angle, can't drill in.

## Goal

Add a chat panel where the admin can ask freeform questions about QA runs, results, and system health. The agent answers using recent run reports as context. This makes the dashboard a real conversation partner instead of a static report.

## Non-goals

- Customer-facing chat (this is admin-only, gated by the same allowlist as the rest of the dashboard)
- Mutating actions from chat (no "rerun this scenario" or "delete this run" via chat for v1 — read-only Q&A)
- Persistent multi-session memory (each browser tab is its own conversation; refresh resets)
- Voice / multimodal — text only

## Users & jobs-to-be-done

Single user: the admin (cvsubs@gmail.com today, future allowlisted teammates).

Jobs:
1. **Diagnose**: "Why did `synth_high_achiever_junior_all_ucs` fail in the last run?"
2. **Trend-spot**: "Has the `roadmap_deep_link_integrity` assertion ever failed in the past 7 days?"
3. **Synthesize**: "Summarize the last 30 days of QA runs in 3 bullets."
4. **Plan**: "Which surface should I focus on improving next based on what's failing?"

## Success criteria

- Admin can ask a question, get a contextually grounded answer in <10s for typical queries
- Answer cites specific run IDs / scenario IDs / assertion names so the admin can drill in
- Doesn't hallucinate runs that don't exist (the LLM must ground in the supplied context, not its training data)
- Conversation context within a session: follow-ups like "and the one before that?" work

## Constraints

- Reuses existing Gemini 2.5 Flash setup (same API key, same allowlist for auth)
- Server-side: 1 new endpoint on `qa-agent` (`POST /chat`)
- Client-side: 1 new component on the dashboard
- No new infra — no vector DB, no separate chat-history collection (in-memory per session is fine for v1)
- Dashboard stays internal-only; same Firebase ID-token + email allowlist auth as the rest of qa-agent

## Open questions (resolved here)

- **Q: Persist chat history?** No, v1 is session-only. If needed later, add a Firestore collection.
- **Q: Streaming responses?** No, simple request-response for v1. Streaming adds complexity without much UX win at chat-message length.
- **Q: How much context to send?** Last 30 runs' summary (pass/fail counts + failing assertions, not full assertion bodies). Gemini can pull more per-question if needed via tool calls (out of scope for v1; v1 is a single-shot prompt).
- **Q: What if the model hallucinates a run ID?** Include only real run IDs in the context; instruct the model in the system prompt to never invent IDs. If it does, that's a model bug we'd catch in QA — not a structural one.

## Test plan

- Unit: `_handle_chat` (qa-agent) handles missing question, missing context, LLM error fallback
- Unit: `ChatPanel.jsx` renders messages, sends on Enter, shows loading state, handles errors
- Manual: ask the four jobs-to-be-done questions above against real prod run data, verify answers cite real run IDs and don't hallucinate
