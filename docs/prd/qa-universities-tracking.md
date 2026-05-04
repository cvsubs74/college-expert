# QA Universities Tracking, Feature Coverage Visibility, and Feedback Visibility

## Problem

Three connected gaps surfaced from operator usage of the QA dashboard:

1. **Universities are invisible.** Asked "what universities have been
   covered?", chat answered vaguely. Run records do not propagate the
   archetype's `colleges_template`, so neither the LLM nor the
   dashboard can name the schools the QA agent has actually exercised.
2. **Validated features feel stale.** The Coverage card lists journey
   surfaces (profile, college list, roadmap, …) and validated test
   bullets, but does not surface the *university* dimension at all —
   no list of schools tested, no list of schools still untested.
3. **Feedback feels invisible.** The Steer panel writes feedback into
   `qa_config/feedback`, the synthesizer reads it, the run record
   stamps `feedback_id` on synthesised scenarios — but operators have
   no signal that "their feedback got applied". Every feedback entry
   looks identical regardless of whether it has driven a single
   scenario yet.

## Goals

- Chat can answer "which universities has the QA agent tested today?"
  by name, citing recent runs.
- The Overview tab shows a "Universities tested" card with per-school
  count + last-tested timestamp, plus a list of allowlisted schools
  still untested.
- The Steer panel shows, per feedback entry, whether it has been
  applied to a scenario — and lets the operator click through to a
  recent run that picked it up.

## Non-goals

- Not redesigning the archetype/synthesizer pipeline. We extend the
  existing `_PROPAGATED_FIELDS` propagation, not the schema.
- Not building per-university drill-downs. The card is a summary; the
  Runs tab remains the place to drill in.
- Not changing how feedback is captured (still `POST /feedback`).

## Success criteria

- Asking chat "what universities have been covered?" returns a
  concrete list of school IDs grounded in the recent-runs context.
- Overview tab renders a Universities card listing the tested schools
  with counts and the untested allowlist (capped to 25 in the UI).
- A feedback entry that produced a scenario shows an "✓ applied"
  pill and a link to the run that consumed it.
