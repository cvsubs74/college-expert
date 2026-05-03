# Design: QA Agent

Status: Approved
Last updated: 2026-05-03
Related PRD: [docs/prd/qa-agent.md](../prd/qa-agent.md)

## Architecture

```
┌──────────────────┐     daily HTTP         ┌────────────────────────┐
│ Cloud Scheduler  │ ─────────────────────▶ │  qa_agent (Cloud Fn)   │
└──────────────────┘                        │                        │
                                            │  selects scenarios     │
┌──────────────────┐     manual trigger     │  generates variation   │
│  Admin /qa-runs  │ ─────────────────────▶ │  runs steps            │
│  in frontend     │                        │  writes report         │
└──────────────────┘                        └─────────┬──────────────┘
                                                      │
            ┌─────────────────────────────────────────┴──────────────┐
            │                                                        │
            ▼                                                        ▼
   ┌──────────────────┐                              ┌──────────────────────┐
   │ profile_manager  │                              │ counselor_agent      │
   │ knowledge_base   │  ←  exercised as test user   │ /roadmap, /work-feed │
   │ /chat, etc.      │                              │ /deadlines           │
   └──────────────────┘                              └──────────────────────┘

                               ┌──────────────────────┐
                               │ Firestore            │
                               │  qa_scenarios/       │  (corpus + history)
                               │  qa_runs/            │  (reports)
                               └──────────────────────┘
```

## A new Cloud Function: `qa_agent`

Lives at `cloud_functions/qa_agent/`. Same deploy plumbing as the existing functions (`deploy.sh`, env.yaml, `--min-instances=0`). Endpoint: `POST /run` (with optional `scenario_id` for manual targeting).

Responsibilities:

1. **Select scenarios.** Read `qa_scenarios` collection. Apply the selection policy (untried first, recently-failed next, random rotation otherwise). Pick 3–5 archetypes for this run.
2. **Generate variations.** For each chosen archetype, call Gemini to produce a small variation — e.g., a different student name, slightly different intended major, different target schools — keeping the archetype's intent intact. Falls back to the static defaults if the LLM call fails.
3. **Authenticate as the test user.** Mint a custom token for the test UID via Firebase Admin, exchange for an ID token via Firebase Auth REST.
4. **Run scenario steps.** Call the production endpoints in sequence (profile build → college list → roadmap → fit). Capture every request, response, duration, and assertion outcome.
5. **Tear down.** Reach into Firestore via Admin SDK and clear the test user's roadmap_tasks, college_list, essay_tracker, scholarship_tracker entries. Reset profile to a baseline.
6. **Persist the report.** Write to `qa_runs/<run_id>` in Firestore.
7. **Notify on failure.** Send a single email summarizing failures (one email per run, even if multiple scenarios fail).

## Test user

- Account: `duser8531@gmail.com`. Real Firebase user, real UID, dedicated to QA traffic.
- The agent uses the Firebase Admin SDK service account to mint custom tokens for this UID — no password, no OAuth dance.
- Custom token → ID token via `https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=<api_key>`.
- ID token is included as `Authorization: Bearer <token>` on every request to the production endpoints.

This means the QA agent exercises the exact same auth path real users do. If Firebase auth breaks, the agent's tests fail — which is the right behavior for synthetic monitoring.

## Scenario corpus

Firestore collection `qa_scenarios`. One document per archetype:

```json
{
  "id": "junior_5school_mixed",
  "description": "Junior with a 3.7 GPA, 5-school list mixing 2 reach + 2 target + 1 safety",
  "profile_template": {
    "grade_level": "11th Grade",
    "graduation_year": 2027,
    "gpa": 3.7,
    "intended_major": "Computer Science",
    "interests": ["coding", "robotics"]
  },
  "colleges_template": ["mit", "stanford", "berkeley", "ucla", "uc_davis"],
  "fit_targets": ["mit", "uc_davis"],
  "surfaces_covered": ["profile", "college_list", "roadmap", "fit"],
  "history": {
    "last_run_at": "2026-05-02T14:00:00Z",
    "last_result": "pass",
    "runs_last_30d": 8,
    "failures_last_30d": 0
  }
}
```

10–15 archetypes at launch, hand-curated to cover:
- Every grade (freshman/sophomore/junior/senior) at least once
- Both fall and spring semesters
- 1-school, 3-school, 5-school, and all-UC college list shapes
- High-GPA reach lists, low-GPA-realistic lists
- One "edge" archetype: just-graduated student, profile with missing fields, etc.

Adding an archetype = drop a JSON in `cloud_functions/qa_agent/scenarios/` and run a one-shot upload script. Iteration is fast.

## Scenario selection policy

```python
def select_scenarios(corpus, n=4):
    untried_recently  = [s for s in corpus if days_since(s.last_run_at) > 7]
    recent_failures   = [s for s in corpus if s.failures_last_30d > 0
                                          and days_since(s.last_run_at) <= 7]
    rotation          = corpus

    chosen = []
    chosen.extend(sample(untried_recently, min(2, len(untried_recently))))
    chosen.extend(sample(recent_failures, min(1, len(recent_failures))))
    while len(chosen) < n:
        c = random.choice(rotation)
        if c not in chosen:
            chosen.append(c)
    return chosen
```

This biases toward freshness while always running known-flaky scenarios for confirmation.

## LLM variation step

Given an archetype, ask Gemini to produce a concrete variation:

```
Prompt:
You are generating a synthetic student profile to test a college admissions app.
The archetype is: <archetype.description>
Base values: <archetype.profile_template>
Generate a single variation: a JSON object with the same shape but with these
fields varied within reasonable bounds:
  - student name (random first + last)
  - GPA (within ±0.2 of base)
  - intended major (a related major from the same broad field)
  - one extra interest

Respond with the JSON only, no commentary.
```

Validates the response against the schema; falls back to the archetype's exact `profile_template` if the LLM returns malformed JSON. Costs ~$0.001 per scenario (Gemini Flash); ~$0.005 per run.

## Step execution

Each scenario runs as a sequence:

```
1. setup:    POST /clear-test-data  (custom admin endpoint, see below)
2. profile:  POST /update-onboarding-profile (profile_manager_v2)
3. colleges: POST /add-to-college-list  ×N  (profile_manager_v2)
4. roadmap:  POST /roadmap (counselor_agent) — assert metadata.template_used etc.
5. fit:      POST /fit-analysis (counselor_agent or fit endpoint)
6. teardown: POST /clear-test-data (and verify empty)
```

Each step:
- Times out at 30 seconds individually, 5 minutes for the whole scenario.
- Captures: URL, method, request body (with PII redaction — no real names), response status, response body (truncated to first 8KB), duration in ms.
- Runs assertions specific to the step (e.g., "roadmap response carries metadata.template_used", "fit response has a percent score").
- Records pass/fail with assertion details.

Failures don't abort the scenario — subsequent steps still run so we capture the whole picture. The scenario's overall status is "pass" iff every step passed.

## Teardown / `clear-test-data` endpoint

A new admin endpoint on `profile_manager_v2`:

```
POST /clear-test-data
Body: { "user_email": "duser8531@gmail.com", "admin_token": "..." }
```

Wipes every document under `users/{uid}/{collection}/` for the test UID, where collection is in the existing whitelist (`roadmap_tasks`, `essay_tracker`, `scholarship_tracker`, `college_list`, `aid_packages`). Plus a single `delete()` on the profile doc to reset to nothing.

Gated by:
1. Email must be exactly `duser8531@gmail.com` (allowlist).
2. Admin token must match a Secret Manager secret only the QA agent's service account can read.

Both gates required. The endpoint cannot be used to wipe a real user's data even if the admin token leaks.

## Reports

`qa_runs/<run_id>` document shape:

```json
{
  "run_id": "run_2026-05-04T06:00:00Z_abc123",
  "started_at": "2026-05-04T06:00:00Z",
  "ended_at":   "2026-05-04T06:03:14Z",
  "duration_ms": 194021,
  "trigger": "schedule" | "manual",
  "actor":   "scheduler" | "<admin email>",
  "summary": { "total": 4, "pass": 3, "fail": 1 },
  "scenarios": [
    {
      "scenario_id": "junior_5school_mixed",
      "variation": { ...the LLM-generated variation... },
      "result": "pass" | "fail",
      "started_at": "...",
      "duration_ms": 32104,
      "steps": [
        {
          "name": "profile",
          "endpoint": "POST .../update-onboarding-profile",
          "request":  { ... redacted ... },
          "response_status": 200,
          "response_excerpt": "...",
          "duration_ms": 1043,
          "assertions": [
            { "name": "status=200", "pass": true },
            { "name": "response.success=true", "pass": true }
          ],
          "pass": true
        },
        ...
      ]
    },
    ...
  ]
}
```

Retention: 90 days, cleaned by a separate Cloud Scheduler job that deletes older `qa_runs` docs.

## Admin UI: `/qa-runs`

A new admin-only page in the frontend. Gated by the existing email allowlist (currently `cvsubs@gmail.com`).

- Top: 30-day pass-rate sparkline + today's status badge.
- Middle: list of recent runs, click into one to expand.
- Per-run drill-down: scenarios with pass/fail badges, click into a scenario for the full step-by-step request/response trace.
- Filters: pass-only, fail-only, surface, archetype.

Routes:
- `/qa-runs` — list
- `/qa-runs/<run_id>` — single run

Read directly from Firestore (the admin user has read access). No new endpoint needed for the read path.

## Manual trigger

Two options, both exposed:

1. **HTTP**: `POST https://qa-agent-...cloudfunctions.net/run` with admin token. Curl-friendly.
2. **Admin UI button**: a "Run now" button on `/qa-runs` that POSTs to the HTTP endpoint and refreshes the list when done.

Manual triggers can specify `?scenario=<id>` to run a single scenario, useful for "I think I just broke X, let me verify."

## Failure notifications

Initial: a single email to `cvsubs@gmail.com` per failing run, sent via the existing `contact-form` cloud function's email helper (or a new tiny one-shot helper in `qa_agent`). Subject: `[QA] N/M scenarios failing — <date>`. Body: brief summary + link to the admin UI.

Slack webhook can be added later if the email volume gets noisy.

## Cloud Scheduler

```
gcloud scheduler jobs create http qa-agent-daily \
  --schedule="0 6 * * *" \
  --time-zone="America/Los_Angeles" \
  --uri="https://qa-agent-...cloudfunctions.net/run" \
  --http-method=POST \
  --headers="Authorization=Bearer $(...)" \
  --message-body='{"trigger":"schedule"}'
```

The scheduler's identity has invoker permission on the qa_agent function. Runs daily at 06:00 PT.

## Deploy plumbing

`deploy.sh` gets a new block for `qa_agent`:

```bash
gcloud functions deploy qa_agent \
  --gen2 \
  --runtime=python312 \
  --region=us-east1 \
  --trigger-http \
  --entry-point=qa_agent \
  --service-account=qa-agent-sa@... \
  --set-env-vars=FIREBASE_API_KEY=...,...
```

The service account needs:
- Firebase Admin SDK access (Auth + Firestore)
- Read access to relevant Secret Manager secrets

## Testing the QA agent itself

- Unit tests in `tests/cloud_functions/qa_agent/` cover:
  - Scenario selection policy (untried-first, fail-first behaviors)
  - LLM variation parsing + fallback on bad JSON
  - Step assertion logic
  - Report shape
- Integration tests stub the production endpoints with `responses` (requests-mock), so the agent's logic is exercised end-to-end without hitting real cloud functions.
- A staging-mode flag lets the agent dry-run: it picks scenarios, prints what it would do, but doesn't make HTTP calls or write reports. Useful for local dev.

## Risks

- **Test data leakage to real users.** Mitigated by the email allowlist on `clear-test-data` and dedicated test account. If the agent ever runs against a non-test account, the endpoint refuses.
- **Flaky tests becoming background noise.** Mitigated by the failure-history tracking — repeatedly-failing scenarios become visible in the admin UI; humans can decide to fix the test or fix the bug.
- **LLM variation generating invalid data.** Mitigated by schema validation + fallback to static archetype values.
- **Cost runaway.** Bounded by 5 scenarios/day cap and Gemini Flash pricing. Worst case ~$30/year. We'd notice in billing alerts long before this matters.
- **Cloud Scheduler dependency.** If the scheduler trigger fails to fire, the daily run is missed silently. Mitigation: a simple "last-run-was-yesterday" check on every admin UI load — if last run is > 36h ago, banner the page.

## Alternatives considered

- **Run the QA agent in CI** (GitHub Actions / Cloud Build cron triggers). Rejected: CI runners are intended for build verification, not 24/7 monitoring; they expire, they have rate limits, they're not the right home for production monitoring traffic.
- **Use a third-party synthetic monitoring service** (Checkly, Datadog Synthetics, etc.). Rejected for MVP: they don't speak our domain (template resolution, college list shapes), and the "adaptive learning" angle the user wants is bespoke. Could complement the QA agent later for raw uptime alerts.
- **Test against a staging environment instead of prod.** Rejected: there is no staging environment for this project. Adding one is a significant undertaking, and the test account isolation gives us 80% of the safety with 5% of the cost.
- **Run the agent without the LLM variation step.** Considered. Static archetypes alone would catch most regressions but miss the user's "adaptive" requirement. LLM variation is cheap; keep it.
- **Test through the frontend (Playwright) instead of API direct.** Rejected: slower, flakier, and conflates UI bugs with backend bugs. The CI Playwright happy-path covers the integration concern; the QA agent owns the API surface.

## Phasing

| PR | Scope |
|---|---|
| 1 | New `qa_agent` Cloud Function with scenario corpus, selection policy, step runner, report writer. Hardcoded test user. No LLM variation yet — uses archetype templates verbatim. New `clear-test-data` endpoint on `profile_manager_v2`. |
| 2 | LLM variation step (Gemini Flash). Schema validation + fallback. |
| 3 | Admin UI `/qa-runs` in frontend. Cloud Scheduler job. Failure email. |
| 4 | Retention cleanup job + 30-day pass-rate metric. |

PR 1 is the core; everything after is iterative. After PR 1, the agent is invokable manually and produces reports — that's already useful even before scheduling.

## Open implementation questions

- Whether to put the admin token in Secret Manager or a Cloud Function env var — Secret Manager is cleaner; env vars are simpler. Recommend Secret Manager (existing pattern).
- The existing `deploy.sh` doesn't have `--min-instances` for non-hot Cloud Functions. The QA agent doesn't need warm starts. Default to 0.
- What service account does the QA agent run under? New `qa-agent-sa@...` with the minimum permissions, separate from the user-facing functions.
