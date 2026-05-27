# Product spec — College Counselor

This product is live. This spec captures **what exists today** and the near-term direction so the harness's product-manager agent can file forward-looking work as GitHub Issues against a real, running system.

For the system shape, module map, and change log see `docs/ARCHITECTURE.md`. For workflow see `CLAUDE.md`. For principles see `ETHOS.md`.

## What we're building

A college counseling web app that gives high-school students (and their parents) a personalized application strategy: ranked college fit, an actionable roadmap of deadlines and milestones, a chat counselor powered by Gemini, and AI-assisted essay feedback. The product is paid (Stripe subscriptions + credits).

## Why

Independent college counselors are scarce and expensive; school counselors are over-allocated; generic web search produces noisy lists and zero accountability for outcome. Families want a single trusted surface that knows their student's profile, knows the universities, and continuously turns "where could I go" into "what should I do this week."

## Primary users

- **High-school student (grades 9–12)** — main user; owns the profile, reads roadmap, chats, drafts essays.
- **Parent / family member** — co-viewer of the same account; sometimes drives subscription decisions.
- **Operator (us)** — internal usage of `qa_agent`'s admin dashboard, KB ingestion scripts, and Stripe back-office tools.

## Core user flows

1. **Onboard + build profile.** Student signs up via Firebase Auth, completes the multi-step strategic profile (grades, scores, activities, preferences). Profile is written directly to `profile_manager_v2`.
2. **Get college fit.** Frontend calls `counselor_agent`, which aggregates profile + `knowledge_base_manager_universities_v2` and returns a ranked, explained college list with reach/target/safety bands. Results are cached on the profile.
3. **Manage college list.** Student adds/removes colleges, sees per-college fit reasoning, deadlines, and required materials.
4. **Generate / refine the roadmap.** Student sees a personalized timeline of application milestones (essays, recs, tests, deadlines) tailored to their list.
5. **Chat with counselor.** Free-form chat with Gemini-backed counselor that has profile + college list + KB context.
6. **Essay help.** Student selects an application essay prompt, drafts, receives AI feedback / suggested rewrites.
7. **Pay.** Stripe Checkout for subscription or credit pack; `payment_manager_v2` webhook reconciles to Firestore.
8. **Internal QA.** `qa_agent` runs scheduled synthetic scenarios end-to-end and surfaces failures in an admin dashboard.

## Must-have features (already shipped — maintenance + iteration)

- Auth + profile CRUD (`profile_manager_v2`).
- College fit ranking served by `counselor_agent`, cached on profile.
- College list management with per-college reasoning.
- Roadmap generation.
- Chat counselor (Gemini Flash).
- Essay prompt selection + AI feedback.
- Stripe subscriptions and credit purchases (`payment_manager_v2`).
- Internal `qa_agent` synthetic monitoring + admin dashboard.
- Universities KB pipeline (Firestore-backed `knowledge_base_manager_universities_v2`, offline ingestion under `agents/university_profile_collector/` + `scripts/`).

## Should-have / in-flight directions

(Source of truth: GitHub Issues with `priority:P1` / `P2`. This list is a hint, not the queue.)

- Tighter onboarding-to-fit funnel: fewer profile steps → faster first college list.
- Roadmap UX consolidation (history shows several iterations under the previous workflow).
- Essay feedback quality + prompt coverage.
- Mobile polish (390px breakpoint).
- Pricing & paywall iteration.

## Out of scope (for now)

- Multi-counselor / institutional mode (B2B).
- Direct application submission (Common App integration, etc.).
- Re-activating the legacy Elasticsearch path (`*_es`, `*_rag` cloud functions). They remain deployed but offline; do not re-target them without an explicit ADR.
- New LLM providers. Gemini Flash via `google-genai` is the only LLM surface.

## Constraints

- **Stack lock-in.** Python 3.11 Cloud Functions Gen2 in `us-east1`, GCP project `college-counselling-478115`. Frontend is React 19 + Vite on Firebase Hosting. Firestore is the primary store. Don't introduce a new runtime, region, or provider without an ADR.
- **Two GCP accounts on this machine.** Default account is OneTrust; project work uses `cvsubs@gmail.com`. Always pass `--account cvsubs@gmail.com --project college-counselling-478115` to raw `gcloud` / `firebase`.
- **Live-component allow-list.** Only the cloud functions enumerated in auto-memory `project_live_components_scope` are reachable from the frontend; the rest are legacy. Don't wire the frontend to legacy variants.
- **Read-side aggregation only via `counselor_agent`.** Frontend never reaches into `knowledge_base_manager_*` directly. Writes go directly to `profile_manager_v2`.
- **Auto-deploy on merge.** `cloudbuild-main.yaml` path-deploys backend + frontend on merge to `main`. Treat `main` as production; no direct commits.

## Success criteria

The MVP is shipped. Forward success criteria for the next iteration phase live on GitHub Issues / milestones. As a project-level health bar:

- `harness/verify.sh` green on `main` continuously.
- All `priority:P0` issues closed within their iteration.
- No regression of the live cloud functions in `project_live_components_scope` (`qa_agent` archetype scenarios stay green).
- Stripe webhook reconciliation drift = 0 (subscriptions in Firestore match Stripe).

## Migration note

The previous workflow (8-agent team from `cvsubs74/claude-workflow`, with PRD / Design Doc gating in `docs/prd/` + `docs/design/`) is superseded by the engineering-workflow harness defined in `CLAUDE.md`. Existing PRD / Design Doc files remain valid as historical product context; new work uses GitHub Issues + ADRs under `harness/decisions/` instead.
