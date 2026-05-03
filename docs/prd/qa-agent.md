# PRD: QA Agent — synthetic monitoring + adaptive scenarios

Status: Approved
Owner: Engineering
Last updated: 2026-05-03

## Problem

The app shipped 25+ features in two days across three Cloud Functions, a knowledge-base swap-out, a frontend consolidation, and a public marketing surface. CI catches code-level regressions on every PR; deploy-time integration tests (`test_*.sh`) catch endpoint-level issues at deploy time. Neither catches the *next* class of failure: things that work the day they ship and break a week later — a quota change, an upstream API edit, a Firestore index drift, a third-party model regression, a credentials rotation that didn't propagate everywhere.

We need a system that *continuously* exercises the app the way a real student would, against the real production endpoints, and tells us when something stops working — even if we haven't pushed any code in a week.

## Goals

- A **QA agent** that runs **on-demand** (manual trigger) and **once daily** (scheduled), with no human in the loop.
- Tests are **API-driven, end-to-end**: against the deployed cloud functions, using a designated test account (`duser8531@gmail.com`), exercising real flows — profile build, university addition, roadmap generation, fit analysis.
- The agent is **adaptive**: scenarios vary across runs. Different student profiles (grade, GPA, interests, target schools) get tested different days; the same exact path doesn't run every time.
- Each scenario **creates and tears down** its own data — the test account never accumulates stale state.
- Each run produces a **detailed report** a manual QA can review: which scenarios were chosen, what each step did, the inputs and outputs, pass/fail, error details, durations. Reports are persistable and browsable through an admin UI.
- The agent **learns** in a small but real way: it tracks which scenarios have been tried, which failed recently, and biases its next run toward gaps and known-flaky areas.

## Non-goals

- Replacing CI's PR gate. The QA agent is post-deploy synthetic monitoring; PR-time tests still run on every change.
- Load testing. The agent runs a handful of scenarios per day, not thousands per minute.
- UI testing. Playwright-style browser automation stays in CI for the happy-path check; the QA agent is API-only because that's faster, more reliable, and easier to attribute failures.
- Self-healing. The agent reports failures; humans investigate. No auto-rollback, no auto-retry-with-mutation beyond what we explicitly script.
- Multi-account testing. One designated test account at launch.
- Production data leakage prevention beyond cleanup. The test account is dedicated and isolated by `user_email`; we'll teardown reliably and accept that a midrun crash might leave residue until the next run cleans it up.

## Users

- **Primary**: engineering, getting an alert when something is broken in prod.
- **Secondary**: a manual QA reviewer who wants to spot-check the daily run, see what was tested, and dig into failure detail without instrumenting their own session.
- **Tertiary**: future product / leadership reviewers who want a "is the system working today?" dashboard.

## User stories

1. *As an engineer who hasn't pushed in a week*, the daily QA run alerts me when an upstream model returns a different shape and breaks fit analysis — before any real user reports it.
2. *As an engineer who just shipped a deploy*, I trigger the QA agent manually post-release and see all green within five minutes — confirming the deploy didn't silently break a flow that wasn't covered by CI.
3. *As a manual QA reviewer*, I open the admin `/qa-runs` page and see today's run summary: 5 scenarios, 4 pass, 1 fail. I click the failing scenario and see the exact request, the response, the assertion that broke, and a diff against yesterday's successful run.
4. *As an engineer debugging a flaky issue*, I see in the report that a specific scenario has failed three times this week with the same error, while other scenarios are stable — narrowing the search.
5. *As a product reviewer*, I check a "system health" indicator on the admin page and see a 30-day rolling pass-rate by surface (profile, college list, roadmap, fit).

## Test surface (MVP)

The agent exercises four flows:

1. **Profile build** — onboard a synthetic student profile (variations: grade level, graduation year, GPA, intended major, region, interests).
2. **College list management** — add and remove universities (variations: 1-school list, 5-school list, all-UC list, mixed-T20-and-state list, with-and-without-merit-aid focus).
3. **Roadmap generation** — request `/roadmap`, validate response shape and template selection (variations: every grade × semester resolution path).
4. **Fit analysis** — run AI fit analysis on a school in the test list (variations: dream school, safety, mismatch by GPA, mismatch by major).

A scenario combines one variation from each of those axes. The agent picks 3-5 scenarios per run.

## Adaptive behavior

- A persistent **scenario corpus** lives in Firestore with all known scenario archetypes (10-20 at launch).
- Each archetype has metadata: last run timestamp, last result, failure history (last 30 days), surfaces covered.
- The selection policy biases toward (a) untried recent scenarios, (b) recently-failed scenarios for re-test, and (c) random rotation across the remainder.
- A small LLM step (Gemini) generates *variations* on a chosen archetype — different student names, slightly different specific facts, different target schools — so the same archetype doesn't produce identical traffic each run. This is the "learning" layer; the agent doesn't blindly replay yesterday's exact requests.
- Over time, archetypes that consistently fail get flagged for human attention; archetypes that consistently pass slot into a regression-only rotation.

## Reporting

Each run writes a **report** with:

- Run ID, start/end timestamps, total duration
- Scenario list with archetype name, generated variation, surfaces touched
- Per-step record: endpoint called, request body (PII-redacted where applicable), response status, response body excerpt, assertion outcome, duration
- Pass/fail summary
- Error details with stack trace (if any)
- Comparison link to the previous run

Reports are persisted in Firestore (`qa_runs` collection) and browsable through a new admin-only `/qa-runs` page in the frontend.

A failing run additionally fires a notification (email or Slack — TBD; see open questions).

## Success metrics

- **Coverage**: agent exercises every endpoint a real user would hit in a typical session. Target: 90%+ of the production flows mapped to at least one scenario.
- **Lead time**: time from a new prod failure to the agent flagging it < 24 hours (the run cadence).
- **Signal quality**: < 5% false-positive rate (reported failures that turn out to be agent bugs, not app bugs).
- **Reviewability**: manual QA can read a daily report and decide "ship / hold" in under 5 minutes.
- **Adaptive**: at least 2/3 of scenarios in any 7-day window are not bitwise identical to a scenario from the previous 7 days.

## Open questions

1. **Notification channel for failures**: email to a fixed address, Slack webhook, or just the admin UI? I'd start with **admin UI + email** (cheapest); add Slack if email gets noisy. Confirm.
2. **Schedule cadence**: daily at a fixed time vs. every-N-hours? I'd recommend **once daily at 06:00 PT** — runs are non-trivial in cost (LLM calls + multiple HTTP fans-out), and 24h is fine for synthetic monitoring. Confirm.
3. **Scope of MVP test surface**: 4 flows above (profile / colleges / roadmap / fit). Drop or add? Notes / scholarships / essays could come in a v2.
4. **LLM variation step**: include in MVP, or ship a static-variation table first and add LLM variation in v2? I'd ship LLM variation in MVP — it's a one-shot Gemini call per scenario and gives the "learning" property the user explicitly asked for.
5. **Auth model**: agent uses Firebase Admin SDK to mint custom tokens for the test user, exchanges them for ID tokens, and calls production endpoints with the same auth path a real user would. Confirm this is acceptable rather than going through a separate "test mode" backdoor.
6. **Retention**: how long do we keep run reports? **90 days** in Firestore; cold-storage older runs to GCS if anyone asks.
7. **Cost cap**: Gemini calls + Cloud Function invocations + Firestore writes. At 5 scenarios/day × ~20 endpoint calls + 1 LLM call each, daily cost is well under $1. No budget concern; flag if scope grows.
