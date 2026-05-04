# PRD — Insightful QA Dashboard

## Problem

The QA dashboard shows raw activity but doesn't tell a story. After three consecutive all-pass runs the System Health card still shows "69% pass rate over the last 30 days" — the 30-day window is sticky enough that recent improvements get drowned out by old failures. Test descriptions read like persona blurbs ("first-generation 10th-grade student with below-average GPA") rather than business-purpose statements ("validates that students starting late with weaker grades still get a viable college list"). And there's no surface that says "what has been validated end-to-end" or "what bugs the agent caught and we fixed".

The result: a non-engineer skimming the page can't tell whether the system is healthy, what's actually being tested, or what value the QA agent is producing over time.

## Goal

Make the dashboard answer four questions at a glance:

1. **Is the system healthy *right now*?** — Health based on the most recent N runs (not a static 30-day window), with N user-configurable.
2. **What is each test actually testing?** — Each scenario has a business-context rationale a non-engineer can read.
3. **What end-to-end use cases are validated?** — A "Coverage" card that lists user journeys the agent confirms work today, drawn from passing scenarios.
4. **What did we catch and fix?** — A "Resolved issues" card that surfaces scenarios that recently transitioned FAIL → PASS, with the failing assertion message preserved as evidence.

## Non-goals

- Customer-visible analytics (stays internal-only behind the existing allowlist)
- Replacing the run-detail page (this is dashboard-summary work)
- Real-time push (next-poll latency is fine)
- Tracking fixes back to specific commits/PRs in v1 (the run state transition is enough signal)

## Users & jobs

Single user: the admin (cvsubs@gmail.com today).

Jobs:
1. **Health check at a glance** — "looking now, is it green or red?" Should reflect the last N runs, not a stale 30-day average.
2. **Justify a scenario** — "what does `synth_first_gen_low_gpa_sophomore_spring` actually validate?" Should read as one or two sentences a PM or designer could understand.
3. **Confidence story** — "what major journeys is this agent verifying for me?" Should list end-to-end paths (profile → college list → roadmap → essays etc.).
4. **Value story** — "what bugs did the QA agent catch?" Should show the most recent FAIL → PASS transitions with what was failing.

## Success criteria

- After 3 all-pass runs, the System Health pill says "100% — last 20 runs" (or whatever N is set), not "69% — last 30 days".
- Each scenario card has a 1-2 sentence business rationale (not just a persona description).
- Coverage card lists at least 5 distinct end-to-end journeys verified across recent runs.
- Resolved Issues card lists the most recent N scenario fixes with their failing-assertion message + the run ID where they passed again.

## Design constraints

- Reuses existing data — qa_runs collection has full run history, no new persistence.
- Stays under the same auth + Firestore security rules.
- Health window N stored in qa_config alongside the schedule (single source of truth for dashboard prefs).
- Business rationale lives on the scenario document (LLM-generated for synthesized scenarios; manually authored for static ones); falls back to existing `description` if missing.

## Test plan

- Unit: `build_summary(runs, recent_n=20)` returns pass-rate based on the last N runs in addition to the existing time-window rates.
- Unit: A new `build_coverage(runs)` extracts distinct journey-tuples from passing scenarios and returns a deduplicated list.
- Unit: A new `build_resolved_issues(runs)` walks runs in chronological order and emits one entry per scenario that flipped FAIL → PASS, retaining the last-known failing assertion message.
- Frontend: ExecutiveSummary renders the recent-N pill prominently; CoverageCard + ResolvedIssuesCard render with seed data; collapse/empty states.
- Manual: open the dashboard after the next scheduler-triggered run and verify the four cards tell a coherent story.
