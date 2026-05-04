# PRD: The smartest QA engineer agent

Status: Draft (awaiting approval)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/qa-agent.md](./qa-agent.md), [docs/prd/qa-agent-dashboard.md](./qa-agent-dashboard.md)

## Problem

The QA agent shipped in PR #27 + the dashboard in PR #30 give us a working synthetic-monitoring system: it picks scenarios, runs them, writes reports, and lets a human drill into failures. But it stops short of being *smart*.

Specifically:

- **Reports are flat.** A reviewer sees pass/fail badges and a step trace. They don't see *what was actually being tested* in plain English, what *strategy* the agent followed, or what the result *means* for system health.
- **No executive view.** The dashboard's run list answers "what happened today?" but not "how is the system trending?" or "where are the recurring weak spots?".
- **Hardcoded schedule.** Cloud Scheduler is wired manually via gcloud. Changing when daily runs fire requires a developer to re-run a gcloud command. There's no UI, no per-scenario schedule, no way to schedule a one-off run for a specific time tomorrow morning.
- **Mechanical scenario selection.** The selection policy is "untried first, recently-failed next, random rotation." The variation step is "tweak the student name and intended major." Neither of these *thinks*. They never invent a new edge case based on what's been tested or what's known to be fragile.

The vision: a QA agent that reads as if a thoughtful senior engineer ran the tests, summarized the work, and left structured notes for the team. Same system data, dramatically more useful.

## Goals

### Run-level intelligence

- **Test plan** at the top of every run: a 2-3 sentence narrative explaining *what this run tests, why these scenarios were chosen, and which surfaces are exercised*. LLM-generated from the chosen scenarios + historical context.
- **Outcome narrative** at the bottom of every run: a 2-3 sentence narrative explaining *what was verified, what failed, what it likely means, and what an engineer should look at first*. LLM-generated from the run results.
- **Per-scenario "what this tests"** structured field on every archetype + rendered prominently in the dashboard. Plain-English bullet list, e.g., "Resolver picks `junior_spring`", "5 colleges add via `/add-to-list`", "Roadmap returns `metadata.template_used == junior_spring`".

### Executive summary

A dedicated card at the top of `/qa-runs` showing:
- **Pass rate** (last 7d, last 30d, with trend arrow)
- **Mean time to recovery** for failed scenarios (how long does a regression typically last?)
- **Surface health** — small per-surface badges for `profile`, `college_list`, `roadmap`, `fit`, etc., colored by recent failure rate.
- **System health narrative** — 2-3 sentences synthesized by the LLM from the last 30 days of data. e.g., "The system has been stable for 18 of the last 21 days. The roadmap surface has flaked 3 times this week, all on UC-list scenarios — worth a closer look at translation. Fit analysis has been green throughout."

### User-configurable schedule

An admin UI on the dashboard for editing when scheduled runs fire:
- Pick **time of day**.
- Pick **frequency**: daily, twice daily, weekly, off.
- Pick **days of week** (for weekly).
- Pick **timezone**.
- Schedule changes take effect within ~1 hour.

A "Run at..." panel for one-off scheduled runs (e.g., "run all scenarios at 6:30am tomorrow before the team standup").

### Smart, adaptive testing

The agent acts like a senior engineer planning a test pass:
- **Reads its own history.** Looks at the last 30 days of runs and identifies *which surfaces have been under-tested, which scenarios have flaked, and which assertions have caught nothing*.
- **Coverage-aware.** Tracks which surfaces / endpoints / response shapes have been exercised; biases selection toward gaps.
- **Failure-focused.** When a scenario fails, the next several runs prioritize variations on that scenario to confirm whether the failure is a flake or a real regression.
- **Out-of-the-box thinker (v2).** An LLM-driven scenario *synthesis* step that proposes new archetypes by combining existing ones in unusual ways, or by inventing edge cases the corpus doesn't cover. (Behind a feature flag in v1; promoted to default once we trust the output.)

## Non-goals

- Replacing CI's PR gate.
- Mutation testing or fuzzing at the byte level.
- Self-healing (the agent reports, humans fix).
- Multi-environment testing (one prod project today).
- Multi-account testing (one designated test account today).
- Scenario synthesis that produces archetypes a human reviewer doesn't see — every novel archetype goes through a human approval step before joining the corpus.

## Users

- **Engineering** — wants 30-second answers ("is the system green?") and 5-minute drill-downs ("what broke and why?").
- **Manual QA reviewer** — wants the agent's narrative summary so they can sanity-check without reproducing the run themselves.
- **Leadership** — wants the executive summary card and trend numbers.

## User stories

1. *As an engineer opening the dashboard for the first time today*, the executive summary tells me in one sentence whether the system is healthy. If something's red, the same paragraph tells me which surface and where to look first.
2. *As a manual QA reviewer skimming yesterday's run*, the test plan tells me in plain English what was tested. The outcome narrative tells me what passed, what didn't, and what an engineer should investigate. I trust the agent's read enough to ship/hold the build without redoing the work.
3. *As an engineer who only has standups in the morning*, I open the schedule UI, set runs to fire at 06:00 and 13:00 PT every weekday, and never think about it again.
4. *As an engineer who just merged a risky PR*, I schedule a one-off run for 10 minutes from now to verify the deploy didn't break anything.
5. *As an engineer reading a failing run report*, I see "this is most likely an app regression in the roadmap surface — the response shape changed" because the agent's outcome narrative did the analysis a smart human would have done.
6. *As an engineer reviewing the corpus over time*, I see that the agent has been proposing new archetypes (some good, some not), I approve the good ones to join the corpus, and the test surface keeps growing without my having to author scenarios manually.

## Success metrics

- **Reading time-to-decision**: a manual QA reviewer can decide ship/hold from a single run report in **under 60 seconds** (today: requires drilling through every scenario).
- **Coverage growth**: the corpus grows by **≥1 new approved archetype per week** through the synthesis flow (v2).
- **False-positive rate**: **<5%** of "Suggest cause" outputs and outcome narratives are misleading. Tracked via a thumbs-up/down per narrative.
- **Schedule self-service**: zero developer interventions to change run cadence after this ships (today: every change is a gcloud command).
- **Health-narrative accuracy**: spot-check of executive summary narratives against ground truth shows ≥90% directionally correct phrasing in the first month.

## Phased scope

### v1 (this work)

- Run-level test plan + outcome narratives (LLM-generated, with deterministic fallback)
- Per-archetype `tests` field (structured bullets) + dashboard rendering
- Executive summary card at top of `/qa-runs`
- User-configurable schedule UI + Firestore-backed schedule + hourly Cloud Scheduler poll
- Coverage-aware selection policy (bias toward under-exercised surfaces)
- Failure-focused selection policy (bias toward recently-failed archetypes for confirmation)

### v2 (follow-up)

- Scenario synthesis: LLM proposes new archetypes from gap analysis. Human reviews + approves before they join the corpus.
- "Run at <future time>" one-shot scheduling (today: only periodic).
- Trend graphs (per-surface pass rate over time, MTTR, etc.).
- Slack notifications.
- Per-archetype history panel ("show me every junior_spring run from the last 90 days").

## Open questions

1. **LLM provider**: continuing with Gemini Flash for narratives + planning. Cap costs at ~$1/day (5 narratives × $0.001 + executive summary × $0.005). Confirm.
2. **Schedule storage**: Firestore at `qa_config/schedule` (single doc). Hourly Cloud Scheduler poll. Acceptable lag of ≤1h for schedule changes? Confirm — alternative is calling Cloud Scheduler Admin API to update the job directly, which needs more IAM but offers minute-precision.
3. **Archetype `tests` field**: hand-authored per archetype (minor schema change) vs. LLM-derived from `description` (free, but variable quality). Recommend hand-authored for the existing 8 archetypes; LLM-derived for synthesized archetypes in v2.
4. **Executive summary refresh**: computed live on each dashboard load (cheap if we cache the last 30 days of runs in memory) vs. precomputed nightly into a `qa_summary/today` doc. Recommend live for v1 (simpler); switch to precomputed if dashboard load times degrade past 1s.
5. **Health-narrative tone**: confident with disclaimers, or hedged throughout? Recommend confident with one closing disclaimer ("AI-generated; verify before acting").
