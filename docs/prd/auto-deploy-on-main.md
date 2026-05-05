# PRD: Auto-deploy on main

Status: Proposed
Owner: Engineering
Last updated: 2026-05-05

## Problem

When a PR merges to main, the test gate (`college-expert-pr` Cloud Build trigger) goes green and the merge button activates — but the change does not reach production until someone manually runs `./deploy.sh <target>` from a laptop. In practice this happens hours after the merge. Cron-driven workloads (notably the QA agent's 30-minute synthetic run) keep firing on the pre-merge code in the meantime, surfacing user-visible bugs that the merged fix already addresses.

Concrete impact observed 2026-05-05:

- **PR #88** (KB orphan removal from the QA allowlist) merged at **2026-05-04 21:18 UTC**. The first qa-agent revision built from that merge (`qa-agent-00035`) only landed at **2026-05-05 04:18 UTC** — a 7-hour gap.
- During the gap, scheduled run `run_20260505T033041Z` hit a 404 on `compute_fit:university_of_chicago` because the running function instance still had the pre-PR allowlist. The fix was already merged but not yet live.
- PRs #91 (mutex tightening) and #92 (assertion two-tier split) followed the same pattern: green merge, then hours of latency before the fix touched production.

The CI doc `docs/cicd-setup.md` flags this as a deliberate Phase-1 omission ("Auto-deploy on merge to main — intentional. Deploy stays manual via `./deploy.sh` until we trust the test coverage enough to gate auto-deploys on it"). Test coverage has since grown to 691 backend tests + 41 Vitest + 2 Playwright covering every live cloud function, the qa-agent's full assertion library, the synthesizer, and the runner. The original "we don't trust the gate yet" rationale no longer applies.

## Goals

- **Auto-deploy on green main**: when a push to `main` passes the test gate, deploy the changed components to production. No manual `./deploy.sh` step required.
- **Path-based scoping**: only deploy what changed. A doc-only PR doesn't restart any cloud function. A `cloud_functions/qa_agent/` change deploys only `qa-agent`.
- **Safety on top of the existing test gate**: the deploy stage runs *after* `backend-tests`, `bash-syntax`, and `frontend` succeed. A red gate skips deploy.
- **Account/project pinning**: deploy must use `cvsubs@gmail.com` + `college-counselling-478115` per the project's GCP-account memory rule. Cloud Build's runner SA must inherit those defaults via env vars.
- **No new flake surface**: the path detector and the deploy stages must be unit-tested. Bash-syntax CI must catch shell errors before they hit a production push.
- **Backout via revert**: if a deploy lands a regression, the response is "open a revert PR; that PR's merge auto-deploys the rollback." No bespoke rollback automation.

## Non-goals

- **Blue/green or canary deploys.** Cloud Functions and Cloud Run already keep prior revisions; "rollback" is `gcloud functions deploy` from the previous commit, which a revert PR delivers.
- **Auto-deploy on PR builds.** Only `main` deploys. PR builds stay test-only.
- **Integration tests post-deploy in CI.** The existing `test_*.sh` scripts hit live URLs and stay manual; that's tracked separately.
- **Migrating off the App Engine default service account.** A future hardening PR can swap to a least-privilege SA; this work uses the existing build SA and its `roles/editor` grant.
- **Deploying out-of-scope variants** (the legacy `profile_manager`, `profile_manager_es`, `knowledge_base_manager_vertexai`, etc. listed in `project_live_components_scope.md`). Path detection deliberately does not map them to deploy targets.

## Users

- **Engineers shipping fixes.** A PR merge becomes a real production rollout in minutes, not when someone remembers to deploy.
- **Operators watching the QA dashboard.** No more "the fix is in main but the latest scheduled run was on stale code."
- **The QA agent's monitoring.** Cron-driven runs see the merged code as soon as the next deploy completes (typically 2–3 minutes after merge).

## User stories

1. *As an engineer merging a backend bugfix*, the green merge triggers an auto-deploy and the fix is live before I start the next task.
2. *As an engineer landing a docs-only PR*, no deploy fires — Cloud Build returns green in under 2 minutes.
3. *As an engineer touching multiple components in one PR* (e.g. `cloud_functions/qa_agent/` + `frontend/`), every changed component deploys; nothing is silently skipped.
4. *As an operator on call*, when something breaks I can read the build log to see exactly which deploy targets ran for which commit, and I can revert the offending PR to roll back.
5. *As a future engineer adding a new live cloud function*, I update one mapping (path prefix → deploy target) in `scripts/cicd/detect_changed_targets.py` and the auto-deploy picks it up.

## Success metrics

- **Deploy lag**: median time from "main merge SHA" to "first qa-agent revision built from that SHA" drops from hours (current) to under 5 minutes.
- **Test gate to deploy**: 100% of green main pushes that touch a live component result in a deploy of that component. Zero green merges that silently leave the prior revision running.
- **Doc-only PRs**: zero deploys triggered by changes that touch only `docs/` or `tests/`. Verified by inspection of the path detector's output.
- **Build duration**: total `cloudbuild-main.yaml` time stays under 10 minutes on cold cache (test gate ~5 min + sequential cloud-function deploys ~3–5 min).
- **No CI-driven outages**: in the first month, zero production incidents whose root cause is "auto-deploy ran something it shouldn't have."

## Open questions

- **Frontend env in CI**: the prod frontend build needs real values for `VITE_API_URL`, `VITE_FIREBASE_*`, and the various `_URL` vars. Design doc resolves this via a single `frontend-env-prod` Secret Manager entry whose body is a fully-rendered `.env`. No new secret structure is invented; the secret holds exactly what `frontend/.env` already contains on a deploy laptop.
- **Firebase auth in CI**: `firebase deploy` against the `college-counselling-478115` project. Design doc resolves this via `GOOGLE_APPLICATION_CREDENTIALS` pointing at the build SA — `firebase-tools` accepts ADC since v11.
- **Concurrent deploys vs. sequential**: cloud functions deploy independently; Cloud Build steps could run them in parallel via `waitFor`. Design doc opts for sequential as a v1 simplicity bias; we can parallelise later if cold-cache builds creep above 10 minutes.
