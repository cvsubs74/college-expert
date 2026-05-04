# QA Agent — Architecture Reference

A reusable blueprint for building a synthetic-monitoring + admin-dashboard
service that exercises a live application end-to-end, surfaces real
regressions, and lets a human operator steer test design.

This is a generalized restatement of the system in
`cloud_functions/qa_agent/` + `frontend/src/components/qa/`. It's
intentionally implementation-agnostic where it can be (you can swap
Cloud Functions for any HTTP-callable backend, Firestore for any
schemaless store, Gemini for any text LLM), and concrete where the
detail matters.

Spec docs that go deeper on individual features live under
`docs/prd/qa-*.md` and `docs/design/qa-*.md`. This doc is the map.

---

## 1. What & Why

**What it is.** A long-running service that, on a fixed schedule plus
on demand, runs a curated + LLM-synthesized set of end-to-end scenarios
against the live production stack as a test user, records a structured
report per run, and exposes the results to a small admin dashboard.

**Why we built it instead of a standard E2E test suite.** Three reasons:

1. **It runs against production.** Pre-deploy CI tests pass, then
   prod regresses anyway because the test environment isn't the prod
   environment. We needed a tight feedback loop on the live stack.
2. **The system has too many surfaces to write static cases for them
   all.** An LLM-driven synthesizer can generate fresh personas
   targeting under-tested gaps without a human writing each one.
3. **A dashboard turns runs into operator signal.** Pass-rate trends,
   failing journeys, fixed-since-last-run, "which schools have we
   actually tested" — these are operator questions, not CI metrics.

The operator's mental model: this is a **synthetic user that lives
in production, never touches real customer data, and tells you when
the product breaks.**

---

## 2. High-Level Architecture

```
                ┌──────────────────────────────────────┐
                │          Admin Dashboard             │
                │   (React SPA, Firebase Hosting)      │
                │  Overview │ Runs │ Ask │ Steer       │
                └───────────────┬──────────────────────┘
                                │ X-Admin-Token  /  Firebase ID token
                                │ over HTTPS
                                ▼
        ┌───────────────────────────────────────────────┐
        │             qa-agent (Cloud Function)         │
        │   ┌──────────┬─────────┬─────────┬─────────┐  │
        │   │  HTTP    │ Synthe- │ Runner  │  Chat   │  │
        │   │ dispatch │  sizer  │ (E2E)   │ (LLM)   │  │
        │   └──────────┴─────────┴─────────┴─────────┘  │
        │   ┌──────────┬─────────┬─────────┬─────────┐  │
        │   │ Coverage │ Resolved│Narrative│Feedback │  │
        │   │  build   │ Issues  │ (LLM)   │  loop   │  │
        │   └──────────┴─────────┴─────────┴─────────┘  │
        └───────────────────┬───────────────────────────┘
              writes runs   │   reads recent runs       ▲
                            ▼                           │
                    ┌────────────────┐         ┌────────┴────────┐
                    │   Firestore    │◀────────│ Cloud Scheduler │
                    │   qa_runs/     │  cron   │  every 30 min   │
                    │   qa_config/   │         └─────────────────┘
                    └───────┬────────┘
                            │ run.scenarios[*]
                            │  → calls profile-manager,
                            │     counselor-agent, etc.
                            ▼
                    ┌────────────────┐
                    │  Live product  │
                    │   (the thing   │
                    │  being tested) │
                    └────────────────┘
```

**One sentence per arrow:**

- The dashboard talks to the qa-agent over HTTPS with a dual-auth gate.
- Cloud Scheduler hits the qa-agent's `/run` endpoint on a cron.
- The agent reads recent runs from Firestore for context, runs new
  scenarios against the live product (acting as a dedicated test user),
  and writes a structured report back.
- The dashboard re-reads runs + summary on demand; nothing is push-based.

---

## 3. Components

Files reference the reference implementation; the responsibilities
generalize.

### Backend (one Python cloud function)

| File | Responsibility |
|---|---|
| `main.py` | HTTP dispatcher, dual-auth gate, route handlers, helpers shared across handlers. The only entry point. |
| `corpus.py` | Loads static archetype JSON files from disk; selection policy (which archetypes to run today). |
| `synthesizer.py` | Builds an LLM prompt from recent run history + system knowledge + admin feedback, generates N fresh archetypes, validates each against schema + value bounds + allowlist. |
| `runner.py` | Executes one materialized scenario end-to-end: clear test data → seed profile → add colleges → trigger downstream features → assert outputs → teardown. Never raises; every failure becomes a structured assertion result. |
| `assertions.py`, `data_assertions.py`, `ground_truth.py` | Per-step assertion helpers. Compare actual response to either a derived expected (e.g. resolver template) or a manually maintained ground-truth bag. |
| `firestore_store.py` | Single point for `write_report`, `list_recent_runs`, `load_history`. Insulates the rest of the code from the storage layer. |
| `coverage.py` | Aggregates passing scenarios into "what did we validate?" — journeys, features, universities tested + not yet tested. Read-time alias canonicalization here. |
| `resolved_issues.py` | Walks recent runs to find FAIL→PASS transitions ("fixed since last run"). |
| `narratives.py` | LLM-generated executive summary that grounds itself in the coverage + recent-runs context. |
| `chat.py` | Admin Q&A over recent runs. Stateless per session, grounded in last-30-run summaries. |
| `schedule.py` | Reads/writes a single Firestore doc that the scheduled-run trigger consults. |
| `feedback.py` | Admin-authored notes that steer the next synthesizer call. Items auto-dismiss after N runs reference them. |
| `dashboard_prefs.py` | A few configurable knobs (e.g. recent-N window) the operator changes from the dashboard. |
| `auth.py` | Dual-auth: `X-Admin-Token` (server-to-server, scheduler) **or** Firebase ID token + email allowlist (browser). |

### Frontend (React SPA, dashboard only)

| Component | Role |
|---|---|
| `QaRunsListPage` | Tabbed shell. Tab state in `?tab=` URL param. |
| `RunsTable`, `ScenarioCard`, `OutcomeCard`, `StepRow` | Per-run drill-down. |
| `ExecutiveSummary` | LLM-generated narrative at the top of Overview. |
| `CoverageCard`, `UniversitiesCard`, `ResolvedIssuesCard` | Operator-facing aggregations on Overview. |
| `RunNowPanel`, `PreviewModal` | Manual trigger + "what will run" preview. |
| `ChatPanel` | Ask tab; admin Q&A over recent runs. |
| `FeedbackPanel`, `ScheduleEditor` | Steer tab; operator-authored notes + cron config. |
| `AdminGate` | Email allowlist check on the client (defense-in-depth — server still enforces). |

---

## 4. Data Shapes

These are the interfaces that matter most for replication.

### 4.1 Archetype (static OR synthesized)

```json
{
  "id": "junior_spring_5school",
  "description": "Junior in spring with a 5-school reach-and-target list...",
  "business_rationale": "Validates the most common journey for our highest-engagement users...",
  "default_student_name": "Sam Chen",
  "profile_template": {
    "grade_level": "11th Grade",
    "graduation_year": 2027,
    "gpa": 3.85,
    "intended_major": "Computer Science",
    "interests": ["robotics", "competitive programming", "music"]
  },
  "colleges_template": ["massachusetts_institute_of_technology", "..."],
  "expected_template_used": "junior_spring",
  "surfaces_covered": ["profile", "college_list", "roadmap"],
  "tests": [
    "Resolver picks junior_spring template from graduation_year=2027 + spring",
    "5 colleges added via /add-to-list",
    "..."
  ],
  "synthesized": false,
  "synthesis_rationale": null,
  "feedback_id": null
}
```

Synthesized archetypes are the same shape with `synthesized: true` and a
non-null `synthesis_rationale`. They may also carry `feedback_id` (string
or array of strings) crediting the admin notes that drove their design.

### 4.2 Run record (one Firestore doc per run)

```json
{
  "run_id": "run_20260504T141919Z_ba07d4",
  "started_at": "2026-05-04T14:19:19+00:00",
  "trigger": "manual" | "agent_loop" | "schedule_check",
  "status": "running" | "complete",
  "summary": { "pass": 4, "fail": 0, "total": 4 },
  "scenarios": [
    {
      "scenario_id": "junior_spring_5school",
      "passed": true,
      "duration_ms": 12340,
      "steps": [
        { "name": "profile_build", "passed": true, "assertions": [...] },
        { "name": "add_college:massachusetts_institute_of_technology", "passed": true, ... },
        { "name": "roadmap_generate", "passed": true, ... }
      ],
      "tests": ["..."],
      "surfaces_covered": ["profile", "college_list", "roadmap"],
      "business_rationale": "...",
      "synthesized": false,
      "colleges_template": ["massachusetts_institute_of_technology", "..."],
      "feedback_id": null
    }
  ]
}
```

**Two-phase write:** the agent writes a `status: "running"` stub *before*
running, so the dashboard can render the in-progress run. When the
scenarios finish, the same doc is replaced with `status: "complete"`
and the real results.

### 4.3 Coverage block (returned by `/summary`)

```json
{
  "summary": {
    "pass_rate_recent": 100, "pass_rate_7d": 89, "pass_rate_30d": 89,
    "recent_n": 5, "trend": "steady",
    "surfaces": { "profile": {"status":"green", ...}, ... },
    "narrative": "The synthetic monitoring system reports a 100% pass rate over its last 5 runs..."
  },
  "coverage": {
    "journeys": [{ "id, surfaces[], summary, scenarios[], verified_count" }],
    "validated_features": [{ "text, count" }],
    "universities_tested": [{ "id, count, last_tested_at" }],
    "universities_untested": ["..."],
    "allowlist_size": 32,
    "total_universities_tested": 24,
    "total_features": 302,
    "total_journeys": 8
  },
  "resolved_issues": {
    "fixes": [{ "scenario_id, step_name, failing_message, failed_at_run, fixed_at_run, fixed_at_time" }],
    "lookback_runs": 40, "total_fixes": 11
  }
}
```

### 4.4 Feedback item

```json
{
  "id": "fb_a1b2c3d4",
  "text": "Focus on essay tracker after the recent ship.",
  "status": "active" | "dismissed",
  "applied_count": 2,
  "max_applies": 5,
  "last_applied_run_id": "run_...",
  "last_applied_at": "2026-05-04T14:00:37+00:00",
  "created_at": "2026-05-03T18:00:00+00:00",
  "created_by": "admin@example.com"
}
```

Auto-dismisses when `applied_count >= max_applies`. Items appear in
the synthesizer prompt with their stable IDs so the LLM can stamp
generated scenarios with `feedback_id` for credit tracking.

---

## 5. HTTP API

All endpoints accept `X-Admin-Token` or `Authorization: Bearer <id_token>`.
The token is checked first; the bearer flow only fires when the token is
absent and the email decoded from the ID token is on the admin allowlist.

| Method | Path | Purpose |
|---|---|---|
| GET | `/scenarios` | List static + recently-synthesized archetypes (public, no auth — read-only metadata). |
| POST | `/run` | Kick off a fresh run. Body: `{ count?, trigger?, scenario_id? }`. Returns the final summary. Long: ~60s. |
| POST | `/run/preview` | Pick the same scenarios `/run` would, return them without executing. |
| POST | `/suggest-cause` | LLM analysis of a single failing scenario; deduplicated by (run_id, scenario_id). |
| POST | `/github-issue` | Build a pre-filled GitHub issue URL for a failing scenario. |
| GET, POST | `/schedule` | Read or write the cron schedule doc. |
| GET | `/summary` | Health + coverage + resolved-issues + narrative for the Overview tab. |
| GET, POST | `/dashboard-prefs` | Read or write operator-configurable knobs. |
| POST | `/chat` | Admin Q&A grounded in last-30-run summaries. Body: `{ question, history[] }`. |
| GET, POST, DELETE | `/feedback`, `/feedback/<id>` | List, append, dismiss steer-the-synthesizer notes. |

CORS: each handler routes through a single `_cors(payload, status)` helper
so allowed origins / preflight live in one place.

---

## 6. Frontend Dashboard

Single SPA route (`/qa-runs`) with four tabs persisted in `?tab=`:

1. **Overview** — `RunNowPanel` (manual trigger) → `ExecutiveSummary` (narrative + sparkline) → `CoverageCard` (journeys + features) → `UniversitiesCard` (per-school count + untested) → `ResolvedIssuesCard` (FAIL→PASS).
2. **Runs** — `RunsTable` with click-through to per-run drill-down.
3. **Ask** — `ChatPanel` (admin Q&A).
4. **Steer** — `FeedbackPanel` (operator notes) + `ScheduleEditor` (cron config) + `RunNowPanel` again.

All tabs lazy-mount their data fetches so non-visible tabs don't fire
network calls on every page load.

---

## 7. Operational Model

### Triggering

- **Cloud Scheduler** hits `POST /run` every 30 minutes (configurable
  via the schedule doc). The cron call passes `X-Admin-Token` from
  Secret Manager.
- **Manual** triggers from the dashboard hit the same endpoint with
  the operator's Firebase ID token.

### Concurrency / cold starts

- Cloud Functions Gen 2, `concurrency=1` per instance (each request
  loads an LLM client + does end-to-end fan-out, so memory is
  predictable per request).
- `max-instances=5` so a `/summary` from the dashboard doesn't get
  aborted while a `/run` holds an instance. Lower values caused
  ~13 "no available instance" aborts per week; 5 eliminates that
  while bounding cost.
- `min-instances=0`. Cold starts are acceptable for a 30-minute cadence
  monitor; we don't want to pay for idle warmth.
- Memory: `512 MB` (default 256 MB is too tight for the LLM client +
  JSON parsing of multi-scenario runs).
- Timeout: `540s` (a single end-to-end run of 4 scenarios takes ~60s
  but the scheduler retries on timeout, so we leave generous headroom).

### Storage

- Single Firestore collection `qa_runs/` keyed by `run_id`.
- Single config doc `qa_config/dashboard` for operator knobs.
- Single config doc `qa_config/schedule` for the cron config.
- Single config doc `qa_config/feedback` for steering notes.
- No indexes beyond what Firestore creates automatically.

### Costs

- Gemini Flash calls: ~3 per run (synthesizer, narrative, optional
  chat) at ~$0.001/call. ~$0.10/day at 30-min cadence.
- Cloud Functions runtime: ~60s per run, 48 runs/day = ~50 min of
  active instance time. Pennies.
- Firestore: 30-run rolling history + small config docs. Pennies.

---

## 8. Auth Model

```
                          incoming request
                                  │
                                  ▼
                       ┌────────────────────┐
                       │ X-Admin-Token      │
                       │ matches secret?    │
                       └─────┬────────┬─────┘
                             │YES     │NO
                             │        │
                             │        ▼
                             │  ┌──────────────────────┐
                             │  │ Authorization header │
                             │  │ has Firebase token?  │
                             │  └─────┬───────────┬────┘
                             │        │YES        │NO
                             │        │           │
                             │        ▼           │
                             │  ┌──────────────┐  │
                             │  │ verify_token │  │
                             │  │ + email ∈    │  │
                             │  │  allowlist?  │  │
                             │  └─────┬────┬───┘  │
                             │        │YES │NO    │
                             │        │    │      │
                             ▼        ▼    ▼      ▼
                          ALLOW    ALLOW  401    401
```

- The token is the scheduler-friendly path (server-to-server, no
  user identity).
- The bearer flow is the dashboard path (operator identity, admin
  allowlist gate).
- Public endpoints (`/scenarios`) bypass both — they expose no PII
  and are useful for the "what scenarios exist?" widget.

---

## 9. Lessons Learned (a.k.a. things to copy)

These are real bugs we hit. Each one informed a permanent design choice.

1. **The synthesizer occasionally emits structured fields in unexpected
   shapes** (e.g. `feedback_id` as `["fb_a","fb_b"]` instead of a
   string). The collection loop must normalize **at write time**, not
   crash. Helper: `_collect_feedback_ids(scenarios) -> list[str]`.

2. **Allowlists drift toward duplicates** — synonymous IDs creep in
   ("mit" + "massachusetts_institute_of_technology"). Defense in depth:
   - clean the allowlist (source-of-truth)
   - update static fixtures
   - **read-time canonicalization** in the coverage builder (so legacy
     data already in the store renders correctly)
   - **write-time canonicalization** in the synthesizer (so newly-
     written records use canonical forms regardless of source)
   - keep the two alias maps independent so the layers don't
     collapse into a single point of failure.

3. **Run records need a propagation step.** The runner produces results
   that don't carry archetype-level metadata (rationale, feature
   bullets, surfaces, the schools involved). A small
   `_propagate_archetype_metadata(result, archetype)` helper called
   right before write is the cleanest pattern.

4. **Two-phase writes for long-running operations.** Write a
   `status: "running"` stub first, replace with `status: "complete"`
   when done. The dashboard renders "running" rows naturally, and a
   crashed agent leaves visible breadcrumbs instead of a silent gap.

5. **LLM grounding > LLM creativity.** The chat endpoint is grounded
   in last-30-run summaries — it's instructed to refuse questions it
   can't ground in the supplied context. The narrative is grounded in
   coverage + sparkline + surface health. Without this rule, the LLM
   confabulates run IDs.

6. **Friendly labels at the leaf, canonical IDs in the data.** The
   dashboard renders "MIT" / "UC Berkeley", but every row carries
   `title=<canonical_id>` so an operator can hover/inspect to copy
   the engineering form for tickets.

7. **Cap everything that the LLM or accumulators produce.**
   `MAX_VALIDATED_FEATURES`, `MAX_UNTESTED_UNIVERSITIES`,
   `MAX_FAILING_PER_RUN`, `_MAX_CONTEXT_CHARS`. The full count is
   always exposed alongside (`total_features`, `allowlist_size`) so the
   UI can say "showing top 20 of 302".

8. **The synthesizer should NEVER block a run.** If the LLM is down
   or returns malformed JSON, log a warning and fall back to all-
   static. Synthesis is enrichment, not a critical path.

9. **Feedback loop visibility.** Operators stop trusting features they
   can't see working. The "✓ applied" pill + clickable run-id link on
   each feedback row was the difference between "is the steer panel
   actually doing anything?" and "yes — that note drove run X".

10. **Deploy from clean main, not from a worktree.** A `deploy.sh` guard
    that refuses to deploy unless `git status` is clean and the branch
    is `main` is worth the friction. Otherwise dirty work-in-progress
    code ships.

---

## 10. Replication Checklist

To stand up the same shape in a new project:

### Backend (1-2 days)

- [ ] One HTTP-callable function (Cloud Functions Gen 2, AWS Lambda
      behind API Gateway, or any persistent server). Single entry
      point dispatches by `(method, path)`.
- [ ] Schemaless store with a `qa_runs/` collection and a small
      `qa_config/` namespace.
- [ ] Cron trigger pinging `POST /run` on a fixed cadence (start at
      30 min; tune later).
- [ ] Dual-auth: a fixed token for server-to-server + the project's
      existing identity provider for operators, with an email
      allowlist gate.
- [ ] A handful of static scenario JSON files describing distinct
      personas + journeys. Aim for ~6-10. Each needs:
      `id, description, business_rationale, profile_template,
      colleges_template (or your-equivalent), expected_*, tests`.
- [ ] A runner that knows how to drive your product end-to-end as a
      dedicated test user (clear data → seed → exercise → assert →
      teardown). Never raise; convert every failure to a structured
      assertion.
- [ ] Write a `status: "running"` stub before executing, replace it
      with the final result on completion.

### Synthesis (½ day)

- [ ] A `synthesizer` module that prompts a text LLM with: system
      knowledge + recent run history + admin feedback + value
      bounds + the canonical entity allowlist.
- [ ] A strict `validate_archetype` step that rejects malformed output
      rather than crashing.
- [ ] An archetype-write-time canonicalizer applied to every chosen
      archetype before the run begins.

### Aggregation (½ day)

- [ ] A coverage builder that walks recent runs and produces:
      journeys, features verified, entities tested, entities not
      yet tested, with caps + totals.
- [ ] A resolved-issues walker that finds FAIL→PASS transitions per
      `(scenario_id, step_name)`.
- [ ] A narrative endpoint: LLM grounded in coverage + recent-runs
      sparkline + surface health.

### Dashboard (1 day)

- [ ] React SPA route gated by the same admin allowlist.
- [ ] Tabbed layout: Overview / Runs / Ask / Steer with state in
      `?tab=` so refresh works.
- [ ] Lazy-mount data fetches per tab.
- [ ] Cards: ExecutiveSummary, CoverageCard, EntitiesCard,
      ResolvedIssuesCard.
- [ ] RunsTable with drill-down to per-step assertions.
- [ ] ChatPanel grounded in last-N-run summaries.
- [ ] FeedbackPanel with "✓ applied" pill + clickable run link.

### Operations (½ day)

- [ ] `deploy.sh` guard: refuse if `git status` is dirty or branch
      isn't `main`.
- [ ] `max-instances >= concurrent-readers + 1` so dashboard
      requests don't get aborted while a run is in flight.
- [ ] A `docs/<service>-setup.md` documenting the one-shot secret +
      IAM provisioning so the next person doesn't have to reverse-
      engineer it.

### Cultural

- [ ] Plan → tests → implement, every change. Every PR has its
      `docs/prd/<name>.md` + `docs/design/<name>.md`.
- [ ] Deploy only from clean main, never from a feature worktree.
- [ ] When a bug is caught, fix it at the layer it leaked from AND
      add a defense-in-depth layer downstream (the canonicalization
      story is the canonical example: 4 layers, each independent).

---

## 11. Where to Read Next

- [`docs/qa-agent-setup.md`](qa-agent-setup.md) — one-shot secrets +
  IAM provisioning.
- [`docs/prd/qa-agent.md`](prd/qa-agent.md) — original product brief.
- [`docs/prd/qa-dashboard-insights.md`](prd/qa-dashboard-insights.md) +
  [`docs/design/qa-dashboard-insights.md`](design/qa-dashboard-insights.md)
  — the Overview-tab cards.
- [`docs/prd/qa-agent-chat.md`](prd/qa-agent-chat.md) — the chat panel.
- [`docs/prd/qa-feedback-loop.md`](prd/qa-feedback-loop.md) — operator
  steering.
- [`docs/prd/qa-universities-tracking.md`](prd/qa-universities-tracking.md)
  — per-entity coverage card (the worked example for adding a new
  dimension to the dashboard).
- [`docs/design/qa-college-id-canonicalization.md`](design/qa-college-id-canonicalization.md)
  — the four-layer defense-in-depth story.
- [`cloud_functions/qa_agent/scenarios/README.md`](../cloud_functions/qa_agent/scenarios/README.md)
  — how to add a new static archetype.
