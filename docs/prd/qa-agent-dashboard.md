# PRD: QA Agent admin dashboard (`/qa-runs`)

Status: Approved
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/qa-agent.md](./qa-agent.md)

## Problem

The QA agent ships reports to Firestore at `qa_runs/<run_id>`, but the only ways to read them today are the Firebase Console and a curl + a JSON unwrapper. That works for an engineer debugging the agent itself; it fails the user the agent is built for — a manual QA reviewer who wants a 30-second answer to "is the app working today?" and a 2-minute drill-down when something is red.

We need an admin-only browser surface that turns the raw Firestore data into something readable, actionable, and *trustworthy enough to alert on*.

## Goals

- A new admin-only route, `/qa-runs`, gated to the existing email allowlist (`cvsubs@gmail.com` for now; small list later).
- **Run list** — most recent runs first, with timestamp, trigger (manual / scheduled), actor, summary (pass/fail counts), duration, and a coloured pass/fail status badge.
- **Run detail** — drill into one run, see scenarios with expand-to-step-detail, every step's endpoint + status + assertions + redacted request + truncated response.
- **30-day pass-rate sparkline** — at-a-glance health indicator above the list.
- **"Run now" button** — kick off a fresh run directly from the page, choose between full batch and single scenario.
- **LLM-powered improvement suggestions** — for failing runs, a Gemini call analyzes the failure, distinguishes "agent bug" vs "app regression", and proposes a likely root cause.
- **One-click bug reporting** — for any failing scenario, a button generates a pre-filled GitHub issue (title, body with the run id, scenario, failing step, request, response, assertion that fired).
- Read path uses Firebase ID token + email allowlist (browser-friendly), not the curl-shaped admin token.

## Non-goals

- Public access. The dashboard is internal — students never see it.
- A general-purpose Firestore browser. The shape is specific to qa_runs.
- An issue tracker. We integrate with GitHub Issues; we don't build one.
- Realtime streaming during a run. The run is bounded (~15-30s); the page refreshes when the run finishes.
- Editing scenario archetypes from the UI. Archetypes are code-owned; new ones merge as PRs.
- Cross-environment views. One project, one set of runs.

## Users

- **Primary**: engineering reviewing health post-deploy or post-deploy-skip (e.g., "I haven't pushed in a week — is anything broken?").
- **Secondary**: manual QA reviewer who runs a sweep before a release.
- **Tertiary**: leadership wanting a "system green / yellow / red" answer.

## User stories

1. *As an engineer right after a deploy*, I open `/qa-runs`, click "Run now", wait ~15s, and see a green badge — I'm done.
2. *As a QA reviewer skimming yesterday's overnight run*, I see 4/5 passed, click into the failure, see exactly which step (endpoint, status, assertion text) broke, and know whether to file a bug or rerun.
3. *As an engineer staring at a confusing failure*, I click "Suggest cause" and read a 2-3 paragraph LLM analysis pointing at probable root cause (e.g., "the response shape changed — `metadata.template_used` is now nested under `metadata.template`"), saving me 15 minutes of digging.
4. *As an engineer who just confirmed a real prod regression*, I click "Report bug" — a GitHub issue opens in a new tab pre-filled with run id, scenario, failing step's request/response, and a default title. I add one sentence and submit.
5. *As anyone glancing at the page*, I see a 30-day pass-rate sparkline so I know whether the failing run today is unusual or part of a pattern.
6. *As an engineer running an ad-hoc smoke test*, I select a single archetype from a dropdown ("just exercise junior_spring_5school"), click Run, and skip the full batch.

## Success metrics

- An engineer can answer "is the app green today?" in **under 10 seconds** of opening the page.
- An engineer can drill from "failing run" to "specific assertion that broke + request/response" in **under 3 clicks**.
- "Run now" → result visible **under 30 seconds** for a single scenario, **under 2 minutes** for a full batch.
- "Suggest cause" → useful response **80%+ of the time** (qualitative — track via thumbs).
- Reports persist for 90 days; older runs auto-deleted by a separate retention job (out of scope for this PR).

## Open questions

1. **Auth path on qa-agent**: agent currently requires `X-Admin-Token`. For browser triggers, switch the agent to *also* accept a Firebase ID token + email-allowlist check (in addition to the token). The browser uses the ID token; curl users keep using the admin token. Confirm.
2. **Read path for the dashboard**: read directly from Firestore via Firebase SDK (with security rules gating to admin emails) vs. add `GET /runs` and `GET /runs/<id>` endpoints to qa-agent. Recommend **direct Firestore reads** — fewer moving parts, instantly reactive, no extra deploys when shape changes.
3. **GitHub repo for bug reports**: hardcoded `cvsubs74/college-expert`. OK?
4. **LLM suggestions cost**: ~2-3 paragraphs of Gemini Flash output per click. Cheap; cap at 1 call per run-id per session via in-memory dedup.
5. **30-day retention cleanup**: ship as a separate small Cloud Function with a daily Scheduler job. Out of scope for this PR; flagged here as a follow-up.
