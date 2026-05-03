# PRD: LLM scenario synthesis + deep data validation — the QA agent that thinks

Status: Approved
Owner: Engineering
Last updated: 2026-05-04
Parent: [docs/prd/qa-agent.md](./qa-agent.md), [docs/prd/smart-qa-engineer.md](./smart-qa-engineer.md)

## Two threads, one feature

This PRD covers two related upgrades that ship together because they make the agent *smart*:

1. **Scenario synthesis** — the LLM generates fresh scenarios per run from system knowledge + recent run history. (Original proposal in this doc.)
2. **Deep data validation** — assertions don't just check `status_is_2xx`; they cross-reference data flow. When the agent adds MIT to the test user's college list, the runner first fetches MIT's data from the knowledge base (essays required, deadlines, deadline type, mascot, financial aid stats), and every downstream endpoint's response is verified against that ground truth. The essay tracker should surface essays that match MIT's required-essay count. The fit response should reference MIT's actual mascot. Every fetched piece of information gets validated for accuracy — not just shape.

Today's tests catch broken endpoints. The upgraded tests catch *broken data flow*: when the API returns 200 but the data doesn't match what the source-of-truth said it should be.

## Problem

The QA agent today picks from a fixed list of 8 hand-authored archetypes — junior_spring_5school, all_uc_only, single_school_test, etc. — and lightly varies them (different student name, slightly different major, gpa Δ). That covers the basics but it isn't *thinking*. The agent never invents a scenario that targets a gap it noticed in past runs. It never tries an unusual combination of inputs because it noticed the system has been stable in the routine ones. It never says "I haven't tested the fit surface in two weeks — let me build a scenario that exercises it."

A senior QA engineer doing this work would do all of the above. They'd read the recent runs, notice patterns, and design new tests targeting the weakest seams. They'd document why each test was chosen. The agent should behave the same way.

## Goals

The QA agent should generate **most of its scenarios on the fly** from:
1. **Domain knowledge** of the app (surfaces, endpoints, known fragile areas, valid input ranges).
2. **Recent run history** (what's been tested, what's failed, what hasn't been touched lately).

Each synthesized scenario carries a clear, LLM-authored explanation of *what it's testing and why* — so a human reviewer reading the dashboard understands the agent's intent without having to read code.

The agent gets *adaptively smarter* over time. Every run feeds back into the next:
- A scenario that finds a bug gets variations spun up in the next run.
- A scenario that always passes becomes lower-priority.
- Surfaces that haven't seen failures recently get coverage-biased visits.
- Fragile combinations (e.g., "low-GPA + reach school") that have flaked before get re-tested with similar shapes.

Static archetypes stay around as a safety net but are no longer the primary source of test scenarios.

## Deep data validation goals

For every scenario (synthesized or static), the runner gathers **ground truth** before executing the test, then validates every response against it:

- **Pre-run ground truth fetch.** Before adding any college, the runner pulls each university's record from `knowledge_base_manager_universities_v2`. Stashes: id, canonical name, application deadline + type, supplemental essay count + prompts, financial aid signals, mascot, location. This is the agent's "what should the system return?" snapshot.
- **Post-add cross-reference.** After `POST /add-to-list`, fetch the test user's college list back. Validate each entry's `name`, `university_id`, `deadline`, `deadline_type` against the snapshot. The university_id we wrote should be the same one we read; the deadline returned should match the KB's deadline.
- **Essay tracker alignment.** When the test pulls `/get-essay-tracker`, count essays per university. The count must match what the KB said that university requires (or be a known supplemental-essay subset). University IDs on essay records must match the colleges we added.
- **Fit analysis cross-reference.** When the test triggers fit analysis on a school, the response must reference that school's actual `university_id`, `name`, and contain at least one fact (mascot, location, programs) that matches the KB record. Hallucinated university references are an automatic fail.
- **Roadmap deep-link integrity.** Every `artifact_ref.deep_link` in the roadmap response must point at a `university_id` that's actually on the user's college list — no stale or orphaned references.
- **Symmetry checks.** The set of universities added (write-side) must equal the set returned by `/get-college-list` (read-side). One-off discrepancies between writes and reads count as a failure even if status codes are clean.

The principle: the agent verifies that the *data the user sees* matches the *data the system was told to remember*.

## Non-goals

- **Self-modifying assertions.** The agent generates scenarios; it doesn't invent its own assertion functions. Assertions stay code-owned.
- **Auto-promotion to permanent corpus.** Synthesized scenarios live for one run by default. A v3 follow-up could add a "promote this synthesized scenario to a permanent archetype" workflow with human review; not in this scope.
- **Exploring the app like a real user.** The agent uses the API; no headless browser. The product surface is the API surface.
- **Adversarial fuzzing at the byte level.** Generated inputs stay within reasonable human-shaped bounds (a real student profile, a real college list).
- **Multi-agent / multi-step planning** (planning + critic + executor). Single LLM call for synthesis; deterministic execution; deterministic verdict. Keeps the cost + latency tolerable.

## Users

- **Engineering.** Wants the agent to find edge cases it wouldn't have thought to write down.
- **Manual QA reviewer.** Wants to read each scenario's rationale in plain English and decide whether the agent's intuition was good.
- **Leadership.** Wants the trend metric ("synthesized scenarios catch ~N% more bugs than static ones over 30 days").

## User stories

1. *As an engineer reading today's run report*, I see 4 scenarios — 2 of which were synthesized this morning. Each synthesized scenario has a "🤖 LLM-generated" badge and a one-paragraph rationale explaining what gap or risk it targets.
2. *As a manual QA reviewer*, I open a synthesized scenario and read: "This scenario tests a low-GPA student (3.1) targeting a reach school (Stanford). The agent picked this combination because three runs in the last week tested high-GPA reach lists and zero tested below-average GPAs against Tier 1 schools." That tells me what to look for + whether the rationale is sound.
3. *As an engineer noticing a regression yesterday on UC group treatment*, today's run prioritizes synthesized scenarios that exercise UC group paths in different shapes (4 UCs, 1 UC + 5 non-UCs, all-UC list with mixed campuses, etc.).
4. *As an engineer worried about LLM cost*, the synthesizer caps at 3 scenarios per run, uses Gemini Flash, and produces a deterministic-fallback set when it's offline.
5. *As an engineer reviewing the corpus over time*, I track in the executive summary how often synthesized scenarios catch real failures vs static ones — the agent's "thinking" is itself measurable.

## What the agent should know

The synthesizer reads two contexts to plan a run:

**System knowledge** (a static markdown doc the agent ships with):
- The app's domain: high-school students, college applications, four key surfaces (profile, college_list, roadmap, fit).
- The endpoints exercised + their request/response shapes.
- The valid input ranges (grade levels 9-12, graduation years 2026-2030, GPA 0.0-4.0, valid college IDs).
- Known fragile areas: UC group translation, summer template fallbacks, multi-school RD ordering, edge GPA values, missing optional fields.
- Persona examples: high-achieving STEM, humanities-leaning, recruited athlete, first-gen, late starter.

**Recent run history** (live, last ~20 runs):
- Which scenarios ran, which surfaces they touched.
- Which assertions fired green vs red.
- Which surfaces haven't been tested in N days.
- Which kinds of inputs have been over-represented (e.g., 5 of last 6 runs used GPAs >= 3.5).

## Adaptive learning loop

```
        ┌────────────────────────┐
        │  Past run history      │
        │  + System knowledge    │
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │  LLM synthesizer       │
        │  Plans 2-3 scenarios   │
        │  + 1-2 static fallback │
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │  Validation + run      │
        │  (same runner as today)│
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │  Run report            │
        │  + scenario rationale  │
        │  + assertion results   │
        └────────────┬───────────┘
                     ▼
        ┌────────────────────────┐
        │  History feeds back    │
        │  into NEXT run's plan  │
        └────────────────────────┘
```

Every cycle the agent:
1. Looks at what happened in the past 30 days.
2. Identifies gaps (under-tested surfaces) and risks (recently-failed scenarios).
3. Synthesizes scenarios that target both.
4. Mixes in 1-2 static archetypes as a safety net.
5. Runs everything, captures results.
6. Updates history (so next run's planner sees this run too).

## Success metrics

- **Synthesized share**: target 60-80% of scenarios per run are LLM-synthesized within 2 weeks of launch (rest are static safety net).
- **Bug-find rate**: synthesized scenarios catch real regressions at ≥ the rate of static ones (early target: parity; stretch: 1.5x).
- **Reviewer trust**: 80%+ of synthesized scenarios pass the "is the rationale sound?" eye test in spot-checks.
- **Cost**: < $5/month in LLM calls for synthesis (Gemini Flash, ~3 calls per run × 4 runs/day × 30 days × $0.005/call ≈ $1.80).
- **Latency**: synthesis adds < 5 seconds to a run's wall-clock time.
- **No flakes from synthesis itself**: if a synthesized scenario produces a malformed output that the runner can't execute, the agent catches it pre-run and substitutes a static archetype. Zero crashes from bad LLM output.

## Open questions

1. **Per-run mix**: 1 static + 3 synthesized? 2/2? Tunable via `QA_SYNTHESIS_RATIO` env var. Recommend default 2 synthesized + 2 static for first 2 weeks, then 3+1 once we trust the output.
2. **System knowledge format**: a single hand-authored markdown is the simplest start. Could grow to per-surface specs later. Confirm.
3. **History window for the planner**: 20 runs / 14 days? Tunable. The LLM doesn't need 60 days of context — recent + diverse is enough.
4. **Schema validation severity**: if the LLM produces a partially-valid scenario (e.g., one field malformed), do we (a) reject it and fall back, or (b) repair it and run? Recommend (a) for v1 — keep the agent honest about its synthesis quality.
5. **"Promote to permanent" workflow**: out of scope for this PR (deferred to v3). Synthesized scenarios are ephemeral by default.
6. **LLM cost caps**: `QA_SYNTHESIS_DAILY_CAP = 50` calls would cap ~$0.25/day. Hard guard.
