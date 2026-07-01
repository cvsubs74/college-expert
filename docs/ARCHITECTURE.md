# Architecture

> Update + append a Change Log row whenever a change touches module shape, data flow, schema, or constraints.

## System overview

College Counselor is a Python 3.11 / Cloud Functions Gen2 backend (us-east1) fronted by a React 19 + Vite SPA on Firebase Hosting. The primary data store is Firestore; `knowledge_base_manager_universities_v2` also reads from a dedicated `universities` Firestore collection populated by offline ingestion scripts. A legacy Elasticsearch cluster (used by the `_rag` and `_es` approaches) is offline — its two cloud functions remain deployed but are seldom exercised. Gemini Flash (via the `google-genai` SDK) is the LLM for all AI-driven features. `counselor_agent` is the read-side BFF: the frontend sends chat, roadmap, and college-fit requests to it, and it aggregates from `profile_manager_v2` and `knowledge_base_manager_universities_v2` before responding. Writes go directly from the frontend to `profile_manager_v2`. Stripe handles subscription billing via `payment_manager_v2`, which receives lifecycle events over webhooks. Cloud Build runs CI on every PR; on merge to `main` it also runs a path-based auto-deploy (`cloudbuild-main.yaml`) — backend Cloud Functions and the frontend (Firebase Hosting) are both auto-deployed when their paths change; a docs/tests/config-only merge deploys nothing. GCP project: `college-counselling-478115`.

---

## Module map

```
college-expert/
│
├── cloud_functions/               # Backend — Python 3.11 Cloud Functions Gen2
│   │
│   │── [LIVE — always on]
│   ├── counselor_agent/           # Read-side BFF: chat, roadmap, college fit, work feed
│   ├── profile_manager_v2/        # User profile CRUD, college list, essays, fit cache, credits
│   ├── payment_manager_v2/        # Stripe subscriptions, credit grants, webhook handler
│   ├── contact_form/              # Contact page email relay
│   ├── qa_agent/                  # Synthetic monitoring: scheduled runs + admin dashboard
│   │
│   │── [LIVE — approach-specific, selectable from UI]
│   ├── knowledge_base_manager_universities_v2/  # Default (hybrid) — Firestore-backed university KB
│   ├── knowledge_base_manager/                  # rag approach — GCS+RAG (ES cluster is offline)
│   ├── knowledge_base_manager_ES/               # elasticsearch approach — Elasticsearch (offline)
│   │
│   │── [LEGACY — do not touch]
│   ├── profile_manager/            # Replaced by v2
│   ├── profile_manager_es/         # Replaced by v2
│   ├── profile_manager_vertexai/   # Replaced by v2
│   ├── payment_manager/            # Replaced by v2
│   ├── knowledge_base_manager_universities/  # ES-backed v1 — ES cluster offline
│   ├── knowledge_base_manager_vertexai/      # vertexai approach removed from UI
│   └── scheduled_notifications/   # Cron-only; not part of main app
│
├── agents/                        # Google ADK agents — Python, deployed to Cloud Run
│   │
│   │── [LIVE — approach-specific]
│   ├── college_expert_hybrid/     # Default approach — hybrid KB + Gemini reasoning
│   ├── college_expert_rag/        # rag approach — retrieval-augmented generation
│   ├── college_expert_es/         # elasticsearch approach — ES-backed retrieval
│   │
│   │── [DEAD — not reachable from UI]
│   ├── college_expert_adk/        # vertexai approach removed from UI selector
│   │
│   │── [Background / standalone — not part of main app]
│   ├── university_profile_collector/  # Offline data ingestion agent
│   ├── sourcery/                      # Content sourcing tool
│   ├── source_curator/                # Source curation tool
│   └── uniminer/                      # University data mining tool
│
├── frontend/                      # React 19 + Vite SPA — Firebase Hosting
│   └── src/                       # Components, pages, services, context, utils
│
├── tests/                         # pytest suites — cloud_functions/<service>/
├── scripts/                       # Operational scripts: data fixes, KB ingestion, migrations
├── knowledgebase/                 # Source markdown files for university profiles (offline)
├── prompts/                       # LLM prompt templates used by agents/functions
├── bin/                           # Developer tooling: bootstrap-labels.sh, init-project.sh
├── docs/                          # Architecture refs, design docs, PRDs, playbooks
│   ├── ARCHITECTURE.md            # This file
│   ├── cicd-architecture.md       # CI/CD pipeline reference
│   ├── qa-agent-architecture.md   # QA agent architecture reference
│   ├── STRIPE_WEBHOOKS.md         # Stripe webhook event reference
│   ├── design/                    # DESIGN-<topic>.md per feature (~30 docs)
│   ├── prd/                       # PRD-<topic>.md per feature
│   └── playbooks/                 # Per-agent operational scratchpads
├── deploy.sh                      # Canonical deploy script (account-pinned, clean-main guard)
├── deploy_frontend.sh             # firebase deploy --only hosting wrapper
└── cloudbuild.yaml                # CI pipeline — same file for PR and main triggers
```

---

## Data flow

### User request (read path)

```
Browser (Firebase Hosting)
  │
  │  Firebase Auth (Google Sign-In)
  │
  ▼
frontend/src/services/api.js
  │
  ├──[profile reads]──────────────────────────────────────────────▶ profile_manager_v2
  │                                                                        │
  │                                                                        ▼
  │                                                                   Firestore
  │                                                              users/{uid}/profile/data
  │                                                              users/{uid}/college_list/
  │                                                              users/{uid}/essays/
  │                                                              users/{uid}/college_fits/
  │                                                              users/{uid}/credits/data
  │
  ├──[chat / roadmap / fit]──────────────────────────────────────▶ counselor_agent (BFF)
  │                                                                        │
  │                                           ┌───────────────────────────┤
  │                                           │                           │
  │                                           ▼                           ▼
  │                                  profile_manager_v2       knowledge_base (approach-specific)
  │                                     (read profile)          ├─ hybrid → knowledge_base_manager_universities_v2
  │                                                             ├─ rag    → knowledge_base_manager (GCS+RAG)
  │                                           │                 └─ es     → knowledge_base_manager_ES
  │                                           └──────────────────────────────────┐
  │                                                                               ▼
  │                                                                  Agent (approach-specific)
  │                                                                  ├─ hybrid → college_expert_hybrid (Cloud Run)
  │                                                                  ├─ rag    → college_expert_rag   (Cloud Run)
  │                                                                  └─ es     → college_expert_es    (Cloud Run)
  │                                                                               │
  │                                                                               ▼
  │                                                                          Gemini Flash
  │
  ├──[billing / credits]─────────────────────────────────────────▶ payment_manager_v2
  │                                                                        │
  │                                                                        ▼
  │                                                              Firestore + Stripe API
  │
  └──[contact]────────────────────────────────────────────────────▶ contact_form
```

### User write path

```
Frontend ──[profile / college list / essay saves]──▶ profile_manager_v2 ──▶ Firestore
Frontend ──[subscription / payment]─────────────────▶ payment_manager_v2 ──▶ Stripe
Stripe  ──[lifecycle webhooks]──────────────────────▶ payment_manager_v2 ──▶ Firestore
                                                    (checkout.session.completed,
                                                     invoice.payment_succeeded,
                                                     customer.subscription.deleted, …)
```

### Synthetic monitoring (QA)

```
Cloud Scheduler (every 30 min)
  │  POST /run  (X-Admin-Token)
  ▼
qa_agent (Cloud Function)
  │  acts as synthetic test user
  ├──▶ profile_manager_v2   (seed / teardown profile)
  ├──▶ counselor_agent       (exercise chat, roadmap, fit)
  └──▶ Firestore qa_runs/   (write structured report)
         │
         ▼
Admin Dashboard (React SPA, /qa-runs route)
```

### CI/CD

```
PR open / push
  │
  ▼
Cloud Build trigger (college-expert-pr)
  │  cloudbuild.yaml — test gate only, never deploys
  ├── pytest tests/
  ├── bash -n deploy.sh deploy_frontend.sh
  └── npm ci + vitest + vite build + playwright (against vite preview)
  │
  │  [green → PR mergeable]
  ▼
merge to main
  │
  ▼
Cloud Build trigger (college-expert-main)
  │  cloudbuild-main.yaml — same test gate, then path-based auto-deploy
  ├── [test gate — identical to PR pipeline]
  ├── detect-targets: scripts/cicd/detect_changed_targets.py
  │     maps changed path prefixes → deploy.sh targets
  │     cloud_functions/<svc>/  →  ./deploy.sh <svc-target>
  │     frontend/               →  ./deploy_frontend.sh
  │     docs/ tests/ config     →  (no target; step exits 0)
  └── deploy: runs each target in sequence; frontend last
  │
  ▼
DevOps verifies deploy + runs smoke tests
```

> **Both backend Cloud Functions and frontend (Firebase Hosting) are path-based auto-deployed** by the `college-expert-main` Cloud Build trigger on every merge to `main`. The deploy only fires for the surfaces whose files changed — a docs/tests/config-only merge emits an empty targets list and is a no-op. First observed in production: build `7a3fe287` (PR #131, 2026-05-23).
>
> `./deploy.sh <target>` and `./deploy_frontend.sh` remain available for manual re-deploys (e.g. after a config secret change). `deploy.sh` requires running from the primary repo on `main` (clean-main guard); `deploy_frontend.sh` has no such guard.

> ⚠ `docs/cicd-architecture.md` predates the auto-deploy feature and is out of date — §1, §2, and §7 still describe the old "no auto-deploy" model. Cleanup tracked in issue #137. For current behavior, see the diagram above and `cloudbuild-main.yaml` + `scripts/cicd/detect_changed_targets.py`.

---

## Schemas

### Firestore — `users` root collection

All user data lives under `users/{user_email}/` subcollections. Owned by `profile_manager_v2`.

| Subcollection | Owner | Schema location |
|---|---|---|
| `profile/data` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `files/{file_id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `credits/data` | `profile_manager_v2` + `payment_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py`, `cloud_functions/payment_manager_v2/firestore_db.py` |
| `college_list/{university_id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `essays/{essay_id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `college_fits/{university_id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `chat_conversations/{id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `fit_chat_conversations/{id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |
| `purchases/data` | `payment_manager_v2` | `cloud_functions/payment_manager_v2/firestore_db.py` |
| `purchase_history/{id}` | `payment_manager_v2` | `cloud_functions/payment_manager_v2/firestore_db.py` |
| `aid_packages/{university_id}` | `profile_manager_v2` | `cloud_functions/profile_manager_v2/firestore_db.py` |

### Firestore — `universities` collection

University profiles, **versioned by admission cycle year** (ADR `harness/decisions/0002-university-kb-year-versioning.md`). Owned by `knowledge_base_manager_universities_v2`. Populated by offline ingestion: `agents/university_profile_collector` (ADK agent) produces `research/<id>.json`, then `scripts/ingest_universities.py --year N` POSTs each profile to the function.

```
universities/{id}                    ← CURRENT serving doc (latest cycle year)
    data_year: int                   ← cycle year of this doc's data
    available_years: [int]           ← which version snapshots exist
universities/{id}/versions/{year}    ← full per-year snapshot, same shape
```

Cycle year N = applications due fall N / winter N+1. Ingest always writes the `versions/{year}` snapshot; the main doc is overwritten only when the year is ≥ the current `data_year`, so historical re-ingest never clobbers current data and yearly refreshes never destroy prior years. Reads: `GET /?id=X` (current, unchanged contract), `GET /?id=X&year=2025` (snapshot), `GET /?id=X&action=versions` (list). Search/list/batch operate on current docs only. Ingest is validated at the boundary (`versioning.validate_profile`): structural errors reject with 400; data-quality issues (unparseable or out-of-cycle deadlines, missing acceptance rate) are returned as warnings. Schema in `cloud_functions/knowledge_base_manager_universities_v2/firestore_db.py` + `versioning.py`.

### Firestore — QA collections

Owned by `qa_agent`. See [`docs/qa-agent-architecture.md`](qa-agent-architecture.md) §4 for the full schema.

| Collection | Purpose |
|---|---|
| `qa_runs/{run_id}` | Per-run structured report |
| `qa_scenarios/{archetype_id}` | Synthesized scenario docs |
| `qa_config/dashboard` | Operator knobs |
| `qa_config/schedule` | Cron configuration |
| `qa_config/feedback` | Operator steering notes |

### Stripe

Payment objects (subscription IDs, customer IDs) are stored on Firestore under `users/{uid}/purchases/data`. Stripe is the system of record for billing state; Firestore mirrors the state needed for access control and credit management. See [`docs/STRIPE_WEBHOOKS.md`](STRIPE_WEBHOOKS.md) for the webhook event reference.

### Elasticsearch (legacy — ES cluster offline)

Index `university_documents` was used by `knowledge_base_manager_ES`. Schema in `cloud_functions/knowledge_base_manager_ES/main.py` lines 61–89. Do not deploy or ingest to this index; use the Firestore `universities` collection instead.

---

## Constraints / invariants

1. **GCP account and project are pinned.** All `gcloud` and `firebase` invocations must target `cvsubs@gmail.com` + `college-counselling-478115`. The machine's active default account is an OneTrust account — forgetting `--account` or `--project` (or the `CLOUDSDK_CORE_*` env vars in `deploy.sh`) silently hits the wrong project. `deploy.sh` sets `CLOUDSDK_CORE_ACCOUNT` and `CLOUDSDK_CORE_PROJECT` at startup; never call raw `gcloud` without passing these.

2. **Only `_v2` variants of profile and payment managers are live.** `profile_manager`, `profile_manager_es`, `profile_manager_vertexai`, and `payment_manager` are replaced by their v2 counterparts and must not be deployed or routed to. The frontend hardcodes `VITE_PROFILE_MANAGER_V2_URL` for all approaches.

3. **`counselor_agent` is read-only.** It is the BFF/aggregator for reads — chat, roadmap, fit analysis. It must not write user-facing data. All writes go directly from the frontend to `profile_manager_v2` (or `payment_manager_v2` for billing). This separation makes `counselor_agent` cacheable and keeps the write path auditable.

4. **No code duplication across cloud functions.** Functions call each other over HTTP for shared data rather than copy-pasting logic. Latency is mitigated via `min-instances` (hybrid agent and key functions run with `min-instances=1`) and caching within request scope. See the live-components memory for the known inconsistency: agents' `deploy.sh` env vars still point at old profile manager URLs (not v2) — a known gap to fix before building features that depend on agents reading profile data.

5. **No direct commits to `main`.** Every change ships through a PR + squash-merge. CI (Cloud Build) must be green before the PR is mergeable. `deploy.sh` enforces a clean-main guard; see [`docs/cicd-architecture.md`](cicd-architecture.md) §5.

6. **Frontend default approach is `hybrid`.** The `ApproachContext` default (set in `frontend/src/context/ApproachContext.jsx`) is `hybrid`. The selectable approaches are `hybrid`, `rag`, and `elasticsearch`. `vertexai` was removed from the UI enum — `college_expert_adk` is dead from the UI's perspective.

7. **Update this doc + append a Change Log row** whenever a change touches module shape, data flow, schema, or major constraints. Code Reviewer enforces this as part of PR review.

---

## External dependencies

| Service | Purpose | Failure mode if down |
|---|---|---|
| **Firestore** | Primary data store for user profiles, college lists, university KB, QA runs, credits | All reads and writes fail; app is non-functional |
| **Firebase Auth** | Google Sign-In authentication | Users cannot log in; all authenticated endpoints return 401 |
| **Firebase Hosting** | Serves the React SPA | Frontend unavailable; backend functions still reachable directly |
| **Cloud Functions Gen2** | Hosts all backend services (`counselor_agent`, `profile_manager_v2`, etc.) | API calls from frontend fail; degraded by function |
| **Cloud Run** | Hosts ADK agents (`college_expert_hybrid`, `_rag`, `_es`) | Agent-powered chat / fit analysis fails; profile reads and other non-agent features continue |
| **Vertex AI / Gemini Flash** | LLM for counselor chat, roadmap generation, fit analysis, QA synthesis, narratives | AI-generated features fail; static profile reads continue |
| **Stripe** | Subscription billing, credit packs | Users cannot purchase or renew; existing credits continue to work until exhausted |
| **Cloud Build** | CI pipeline (PR gates + regression checks) | PRs cannot be merged; manual `DEPLOY_ALLOW_DIRTY=1` override exists for emergencies |
| **Cloud Scheduler** | Triggers QA agent every 30 minutes | Synthetic monitoring stops; no user impact; operator must trigger manually |
| **Elasticsearch** (legacy) | `_rag` / `_es` approach KB search | `rag` and `elasticsearch` approach selectors degrade; `hybrid` (default) is unaffected |
| **GCS (Cloud Storage)** | Stores user-uploaded documents (profile files) | File upload / download fails; profile text data already extracted to Firestore is unaffected |
| **Secret Manager** | Stores API keys (`GEMINI_API_KEY`, `STRIPE_WEBHOOK_SECRET`, etc.) | `deploy.sh` fails to fetch secrets at deploy time; running functions use cached env vars until cold start |

---

## Cross-flow contracts

These are the points where a schema or API change must update **both sides simultaneously**. Code Reviewer checks for both-sides-updated discipline on PRs that touch these boundaries.

### 1. Frontend ↔ `counselor_agent` API shape

The frontend calls `counselor_agent` at `/chat`, `/roadmap`, `/fit`, `/work-feed`. Request and response shapes are defined implicitly in `cloud_functions/counselor_agent/main.py` (server side) and `frontend/src/services/api.js` (client side). A breaking change to either side without updating the other silently breaks those features.

### 2. `counselor_agent` ↔ `profile_manager_v2` profile schema

`counselor_agent` fetches the user profile by calling `profile_manager_v2`. The profile schema is owned by `cloud_functions/profile_manager_v2/firestore_db.py`. If fields are renamed or restructured in `profile_manager_v2`, `counselor_agent`'s downstream usage in `counselor_tools.py` must be updated in the same PR.

### 3. `counselor_agent` ↔ `knowledge_base_manager_universities_v2` university schema

`counselor_agent` fetches university data from the KB. The university schema is owned by `cloud_functions/knowledge_base_manager_universities_v2/firestore_db.py`. Field renames in the university profile must be reflected in `counselor_agent`'s consumption of that data.

### 4. Frontend ↔ `profile_manager_v2` profile schema

The frontend reads and writes profile fields directly. Schema changes in `profile_manager_v2` that add required fields or rename existing ones must be mirrored in `frontend/src/` form components and services.

### 5. Stripe webhook contract (`payment_manager_v2`)

`payment_manager_v2` handles the Stripe webhook events listed in [`docs/STRIPE_WEBHOOKS.md`](STRIPE_WEBHOOKS.md). Adding, removing, or renaming handled events requires updating both the Stripe Dashboard webhook configuration and `cloud_functions/payment_manager_v2/main.py`. The webhook endpoint URL (`payment-manager-v2-pfnwjfp26a-ue.a.run.app/webhook`) is registered in Stripe and must not change without updating the dashboard config.

### 6. QA agent ↔ live product API surface

`qa_agent` exercises the live app as a synthetic user. Any change to `profile_manager_v2` or `counselor_agent` endpoints that the QA runner calls (in `cloud_functions/qa_agent/runner.py`) must be reflected in the runner's expectations. A silent API break will appear as QA scenario failures, not as a deploy-time error.

---

## Change Log

> Most recent at the top.

| Date | PR | What changed | Why |
|---|---|---|---|
| 2026-07-01 | #279 | Year-versioned KB is now agent-readable: KB GET gains `sections=` projection (+`sections_returned`/`unknown_sections`; envelope adds `us_news_rank`/`soft_fit_category`), year reads self-describe with `available_years` (field-mask read), and `?action=history` returns a two-axis view — compact per-cycle `snapshots` (new pure module `year_history.py`; fraction-rate + dual-deadline-key defensive normalization; `vintage_estimated` stamped on auto-archived legacy snapshots) plus school-reported `reported_trends` (`verified:false`), never merged (cycle year ≠ trend/entering-class year). MCP connector: `get_university(year, sections)` (enum-typed sections) + new `get_university_history(sections, years)` tool with deploy-skew guard and oldest-year-first eviction | Agents couldn't read the ADR-0002 versioned KB at all — multi-year questions fell back to the profile-baked `longitudinal_trends`, which is capped at 8 rows, dropped first under the 120k tool cap, ~92% unprovenanced, and now written as a single row by the verified collector (design: `docs/design/DESIGN-kb-year-access.md`) |
| 2026-06-12 | (this PR) | `universities` KB is year-versioned: per-cycle snapshots under `universities/{id}/versions/{year}`, main doc serves the latest year (`data_year`, `available_years` added); ingest takes optional `year` + validation gate; `GET ?year=` / `?action=versions` read APIs; `DELETE` accepts `year`; new canonical CLI `scripts/ingest_universities.py` | Yearly KB refresh used to `.set()`-overwrite each university, destroying prior cycle's data; no validation at the ingest boundary (ADR 0002) |
| 2026-05-25 | #154 | `profile_manager_v2` — `add_university_to_list` and `remove_university_from_list` in `college_list.py` now return `college_list` (the updated list after the operation) in the success response; failure path returns `college_list: []`. Response contract: `{success, message, college_list}` | Fixes #153 — frontend `handleToggleCollegeList` was calling `setMyCollegeList(result.college_list \|\| [])` but the old response had no `college_list` field, resetting state to empty after every save. The `college_list_agent` in the hybrid agents already expected this field (defaulting to `[]`). |
| 2026-05-23 | #143 | `profile_extraction.py` LLM schema prompt changed: `grade` now described as string `'9'-'12'` (not `integer 9-12`); post-extraction coercion added; `scripts/fix_grade_field_type.py` one-shot migration backfills existing integer grades in Firestore | Closes the schema inconsistency (#130) that survived the #123 hotfix — any new consumer that assumed `grade` is a string would re-introduce a crash without this change |
| 2026-05-23 | #135 | Document CI/CD path-based auto-deploy behavior (both backend + frontend); correct "deploys are manual" prose | Behavior was already live but doc still described it as manual; DevOps observed the auto-deploy during PR #131 deploy (build ID 7a3fe287) |
| 2026-05-22 | (this PR) | Initial architecture doc | `CLAUDE.md` required it as cold-start reading but only the template existed |
