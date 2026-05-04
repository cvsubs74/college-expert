# PRD — QA Agent Feedback Loop

## Problem

The QA agent designs each run autonomously: the synthesizer reads recent run history + system context, picks 2 LLM-generated scenarios, and the corpus picks the rest. This works well for steady-state monitoring but doesn't let the admin steer.

When the admin notices something — "we just shipped essay-tracker changes, exercise that surface harder", "the UC group treatment regressed last week, retest after the fix", "we should validate freshmen with 0.0 GPAs more aggressively" — there's no way to communicate that intent to the next scheduled run. The admin can pick a single static scenario via "Run now", but that doesn't influence the synthesizer's choices and doesn't carry forward to the next scheduled fire.

## Goal

Give the admin a feedback input on the dashboard. Whatever they type gets attached to the next scheduled run's synthesizer prompt, steering scenario design without bypassing the agent's autonomy. The feedback persists across multiple runs (with an auto-expire so stale notes don't keep biasing forever), and the admin can dismiss any item early.

## Non-goals

- Replacing the synthesizer entirely (admin specifies test cases by hand) — the agent should still drive scenario selection
- Customer-visible feedback — internal admin only
- Per-scenario feedback ("rerun this exact scenario differently") — that's what "Run now" + scenario selection covers
- Real-time push — feedback applies on the next scheduled fire

## Users & jobs

Single user: the admin (cvsubs@gmail.com today).

Jobs:
1. **Steer focus**: "Focus next runs on essay tracker — we just shipped changes there."
2. **Targeted retest**: "Verify the UC group fix landed. Cover at least one all-UC scenario per run."
3. **Edge case**: "Try freshmen with 0.0 GPA — I want to make sure that doesn't crash."
4. **Dismiss when satisfied**: After a few runs of green, mark the feedback as resolved.

## Success criteria

- Admin can type freeform feedback and submit it from the dashboard.
- The next scheduler-triggered run's synthesizer prompt includes the active feedback verbatim.
- The synthesizer references the feedback in its `synthesis_rationale` when relevant ("Targeting feedback X by ...").
- Feedback auto-applies for up to N runs (default 5), then expires; the admin sees a "applied to 3 of 5 runs" badge.
- Admin can dismiss any feedback item early.

## Constraints

- Reuses existing auth + Firestore security rules.
- Feedback stored at `qa_config/feedback` (single doc with an array of items, capped at ~10 active).
- Synthesizer prompt size stays under existing budget.
- No regression on existing synthesizer behavior when feedback is empty.

## Open questions (resolved here)

- **Persistence model?** List of items, each with status (`active` / `applied` / `dismissed`) and a `applied_count`. Items auto-promote to `dismissed` after `applied_count >= max_applies` (default 5). Caller can manually dismiss any time.
- **Multi-item ordering?** Newest first in the prompt; older items take a back seat without being dropped (until they expire).
- **Conflicting feedback?** Don't try to mediate — pass all active items to the LLM and let it decide. If two items contradict, the prompt makes that obvious.
- **Audit trail?** Each item carries `created_at`, `created_by`, `applied_count`, `last_applied_run_id`. The admin can see when feedback was last used.

## Test plan

- Unit: `feedback.py` load/save/list/dismiss/mark_applied behave atomically; expire-after-N is enforced.
- Unit: synthesizer's `_build_prompt` includes the active feedback section when items exist; omits it cleanly when empty; references it in the LLM ask.
- Frontend: FeedbackPanel renders, submits, shows applied counts, supports dismiss.
- Integration manual: leave feedback "test essay tracker harder", wait for next scheduler fire, confirm a synthesized scenario references it in `synthesis_rationale`.
