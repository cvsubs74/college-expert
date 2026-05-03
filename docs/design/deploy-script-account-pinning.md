# Design: Deploy script account & project pinning

Status: Approved (shipped in PR #1, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/deploy-script-account-pinning.md](../prd/deploy-script-account-pinning.md)

## Context

`gcloud` reads its account and project from a global config file (`~/.config/gcloud/`). Any script that calls `gcloud …` without specifying `--account` and `--project` inherits whatever the active values happen to be. On a multi-account workstation that means the deploy target is determined by the last `gcloud config set …` the operator ran — which may have been hours ago in an unrelated session.

The two scripts that matter:
- `deploy.sh` — deploys all backend cloud functions and the hybrid ADK agent
- `deploy_frontend.sh` — deploys the Vite build to Firebase Hosting

Both run dozens of `gcloud` and `firebase` invocations. We need the pinning to apply uniformly across all of them.

## Approach

Use the `CLOUDSDK_CORE_ACCOUNT` and `CLOUDSDK_CORE_PROJECT` environment variables, set at the top of each deploy script. These are the documented gcloud override mechanism — every gcloud invocation in the script's process tree picks them up automatically, with no `--account=…` flag plumbing required at each call site.

```bash
# deploy.sh (top of file)
export CLOUDSDK_CORE_ACCOUNT="cvsubs@gmail.com"
export CLOUDSDK_CORE_PROJECT="college-counselling-478115"
```

For Firebase tooling (which has its own auth model independent of gcloud), use `firebase use --add` pinning at the top of `deploy_frontend.sh` and verify the alias before deploy.

## Pre-flight check

Before any deploy work runs, the script verifies:

1. The pinned account has a valid auth token: `gcloud auth list --filter=account:$CLOUDSDK_CORE_ACCOUNT --format='value(account)'`. Empty output → die with the `gcloud auth login --account=cvsubs@gmail.com` hint.
2. The pinned project is reachable: `gcloud projects describe "$CLOUDSDK_CORE_PROJECT" >/dev/null`. Failure → die with the same auth hint (most likely cause is not being logged in to the right account).
3. Echo the pinned values to stdout so the operator sees them in the deploy log:
   ```
   Deploying with:
     account: cvsubs@gmail.com
     project: college-counselling-478115
   ```

The pre-flight runs before any `gcloud functions deploy` — failures cost nothing, successes give the operator visible confirmation.

## What we deliberately did NOT do

- **`gcloud config set account …` at the top of the script.** This mutates user-global state. After a `deploy.sh` run, the operator's other shells silently switch to the personal account too, which is the inverse of the bug we're fixing.
- **Service-account key files committed to the repo.** Adds key-rotation operational burden for a problem that env vars solve cleanly.
- **Wrapper scripts that re-exec gcloud with explicit flags.** Brittle; misses any new gcloud command added later.

## Frontend deploy

`deploy_frontend.sh` similarly pins:
- `CLOUDSDK_CORE_ACCOUNT` / `CLOUDSDK_CORE_PROJECT` for any gcloud calls (e.g., reading deploy outputs).
- `firebase use college-counselling-478115` at the top, with a pre-flight check that the alias resolves to the right project.

## Testing strategy

- Manual: run `gcloud config set account someone-else@…` then `./deploy.sh --dry-run` (an existing flag). Verify the script proceeds against the pinned account, not the active one.
- Manual: revoke the personal account's auth (`gcloud auth revoke cvsubs@gmail.com`) and run `./deploy.sh`. Verify the pre-flight check fails with the right hint.
- No automated tests — the surface is shell scripting against real gcloud, which doesn't lend itself to unit testing. The pre-flight checks ARE the tests.

## Migration / rollout

Drop-in change. The first time an operator runs the modified script, they may discover their `cvsubs@gmail.com` token has expired (it had been silently fine before because it hadn't been used). The pre-flight prints the right hint and they fix it once.

## Risks

- **CI runs.** Cloud Build uses its own service-account identity, not user gcloud config. The env vars set by the script don't break CI but they're also redundant there. No-op risk: low.
- **Operator surprise.** An operator who's used to "the script just runs against whatever's active" sees a new pre-flight step. Mitigation: clear log output naming the account/project being used.
- **Hardcoded values drift.** If we ever need a second project (staging), the hardcoded `college-counselling-478115` becomes a bottleneck. Mitigation: read from a `.deploy-config` file that's gitignored, with a tracked `.deploy-config.example`. Out of scope for this round; a one-line change later.

## Alternatives considered

- **Service-account JSON key + activate-service-account** at script start. Solves the pinning correctness, but introduces a key file to manage, rotate, and keep out of git. Env-var pinning is simpler and equally correct for human-driven deploys.
- **Refactor every `gcloud` call site to pass `--account` / `--project` flags explicitly.** Equivalent correctness, much more code churn, and easy to forget on future additions. Env vars cover all current and future call sites for free.
