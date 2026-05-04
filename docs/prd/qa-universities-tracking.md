# PRD — Universities Tracking + Chat Grounding

## Problem

Three related gaps observed in prod after the dashboard tabbed-layout shipped:

### 1. Chat can't answer university questions
Asked "What universities have been covered by these tests?" the chat replied:
> "the only explicit reference to universities is found in the scenario `synth_high_achiever_junior_all_ucs`... This scenario name implies coverage of the University of California (UC) system. No other specific university names are mentioned in the test run summaries."

Reality: every scenario carries a `colleges_template` like `["mit", "stanford_university", "university_of_california_berkeley", ...]`. That data exists on the archetype but **is not propagated onto run records**, so the chat's run-context formatter never sees it. The agent ends up guessing from scenario IDs.

### 2. No "Universities tested" view in the dashboard
The Coverage card aggregates surfaces and test bullets, but doesn't tell the operator which schools have actually been exercised. The admin even left feedback "Every test should try out a new university... goal is to test every university in the knowledgebase" — and there's no surface to show whether that's working.

### 3. Feedback-drove-scenario loop is invisible
Feedback items show `applied 2/5` and `last: run_…` — that's correct, but the user has to click through to verify the synthesized scenario actually addressed the feedback. The Steer tab should make the linkage more obvious.

## Goal

1. **Propagate `colleges_template`** from archetype → run-time scenario record so the chat backend, coverage aggregator, and any future tooling can see what was actually tested.
2. **New "Universities tested" card** on the Overview tab listing each university with run-count + last-tested timestamp + a "next to test" callout for any allowlisted university with zero recent runs.
3. **Tighten the feedback loop in the panel**: when an item has applied N≥1 times, link to the run(s) that addressed it so the admin can confirm.
4. **Update chat's run-context** to include per-run university coverage so questions like "what unis have we hit" answer correctly.

## Non-goals

- Per-university fail rate dashboards (interesting but a separate feature).
- Recommending which university to test next via LLM (the deterministic "untested in last N runs" list is sufficient).
- Tracking universities the user manually adds outside the allowlist.

## Success criteria

- Chat answers "what universities have been covered?" with a real list (e.g., "Across the last 30 runs the agent has tested 18 of the 34 universities in the allowlist: MIT (8 times), Stanford (7), UC Berkeley (5)..., not yet tested: Princeton, Yale, ...") — not a hand-wave from the scenario IDs.
- Overview tab has a Universities Tested card showing top-N tested + count of untested.
- Feedback Panel shows "addressed in run_xxx, run_yyy" inline next to each item with `applied_count > 0`.
- After leaving feedback "test more new universities" and waiting for the next scheduler run, the synthesizer's picks include scenarios with universities not yet covered (existing behavior — but now visibly traceable).

## Constraints

- Allowlist already lives at `cloud_functions/qa_agent/scenarios/colleges_allowlist.json` (34 ids); reuse.
- Chat token budget: each university entry adds ~25 tokens; 34 IDs × N runs is fine, but format compactly (don't emit JSON arrays per scenario).
- No new endpoints; piggyback on `/summary` response and `/feedback` GET response.

## Test plan

- **Unit (backend)**: `_propagate_archetype_metadata` carries `colleges_template`. `coverage.build_coverage` returns a `universities_tested: [{id, count, last_tested_at}]` block + `universities_untested` list. `chat._format_run_context` includes a "colleges:" line per run.
- **Unit (frontend)**: `UniversitiesCard` renders tested + untested counts; `FeedbackPanel` shows linked run IDs when applied_count > 0.
- **Integration manual**: ask the chat the failing question above, get a real list. Refresh the dashboard, see Universities Tested. Leave feedback, wait for next scheduler fire, verify the run referenced the feedback id.
