# 0001 — Stack

**Status:** accepted (locked in by existing production deployment)
**Date:** 2026-05-26

## Context

This product (College Counselor) is already live in production. The `/kickoff` ADR captures the stack as it stands the moment the engineering-workflow harness is adopted, not a fresh greenfield choice. New work must respect this stack unless a follow-up ADR supersedes it.

## Decision

| Layer | Choice |
|---|---|
| Backend runtime | **Python 3.11 on Cloud Functions Gen2**, region `us-east1`, GCP project `college-counselling-478115` |
| Backend code home | `cloud_functions/<service>/` for HTTP-triggered functions; `agents/<name>/` for Google ADK agents deployed to Cloud Run |
| Primary data store | **Firestore** (native mode); `universities` collection populated by offline ingestion scripts |
| Read-side aggregator | **`counselor_agent`** — BFF that aggregates `profile_manager_v2` + `knowledge_base_manager_universities_v2` for chat, roadmap, college fit, work feed |
| Writes | Frontend → `profile_manager_v2` directly (no aggregation needed on writes) |
| LLM | **Gemini Flash** via the `google-genai` SDK (single LLM provider; no fallbacks) |
| Payments | **Stripe** + **`payment_manager_v2`** for subscriptions, credits, webhook reconciliation |
| Frontend | **React 19 + Vite SPA** on **Firebase Hosting** (`frontend/`) |
| Auth | Firebase Auth |
| CI | **Google Cloud Build** — `cloudbuild.yaml` for PR checks (`college-expert-pr (college-counselling-478115)`), `cloudbuild-main.yaml` for path-based auto-deploy on merge to `main`; plus **GitHub Actions** `verify` job introduced by the engineering-workflow harness |
| Account discipline | All `gcloud` / `firebase` invocations must pass `--account cvsubs@gmail.com --project college-counselling-478115` — default machine account is OneTrust |

The detailed module map, change log, and live-vs-legacy variant lists live in `docs/ARCHITECTURE.md` (= `docs/architecture.md` on macOS APFS; case-insensitive). That document is the canonical architecture reference; this ADR captures only the *decision-level* shape.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Move backend to Cloud Run services (away from Cloud Functions) | The Cloud Functions Gen2 deploys are working; the cost of migration outweighs the marginal latency / cold-start benefit at current scale. Revisit if cold starts become a felt issue or a service grows past Cloud Functions' resource ceiling. |
| Switch LLM to a multi-provider abstraction (Gemini + OpenAI + Anthropic) | Multi-provider adds operational complexity (auth, retry surfaces, model-version drift) without a current product justification. Single-provider keeps prompts tunable and costs predictable. Revisit if Gemini outage tolerance becomes a stated requirement. |
| Migrate from Firestore to Postgres | Firestore's schemaless writes + Firebase Auth integration + serverless billing fit the current product shape. The cost of migration is unjustifiable. Revisit if relational queries (cross-user aggregates, complex joins) become a constant pain. |
| Re-activate Elasticsearch path (`*_es`, `*_rag`) | The ES cluster is offline; the hybrid Firestore-backed KB (`knowledge_base_manager_universities_v2`) is the live path. Re-activation would require resurrecting cluster infra and re-indexing — explicit follow-up ADR required. |
| Replace React with Next.js / a meta-framework | The SPA on Firebase Hosting is shipping. SSR / RSC benefits don't outweigh the rewrite cost at current scale. |

## Consequences

- New backend services should be added under `cloud_functions/<service>/` following the existing v2 structure (entry point in `main.py`, requirements in `requirements.txt`, deploy via `./deploy.sh <name>`).
- New ADK agents go under `agents/<name>/` with their own deploy target.
- New frontend code goes under `frontend/src/`; the existing Vite + React 19 conventions stand.
- Any introduction of a second LLM provider, a non-Firestore data store, a non-`us-east1` region, or a non-GCP runtime requires a new ADR superseding the relevant row above.
- The **live-components allow-list** (auto-memory `project_live_components_scope`) names every cloud function that's actually wired to the frontend; legacy variants (`profile_manager`, `profile_manager_es`, `profile_manager_vertexai`, `knowledge_base_manager_vertexai`, etc.) are NOT reachable and should not be wired up. Frontend → `counselor_agent` for reads, frontend → `profile_manager_v2` for writes, `payment_manager_v2` for Stripe events.
- `harness/init.sh` and `harness/verify.sh` must bring up and smoke-test against this exact stack — devops fills them in alongside this ADR (see issue filed during kickoff for the audit trail).
