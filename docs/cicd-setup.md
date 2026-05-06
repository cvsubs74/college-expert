# CI/CD Setup — Cloud Build for college-expert

This is a one-time setup guide for wiring [cloudbuild.yaml](../cloudbuild.yaml)
(PR-only) and [cloudbuild-main.yaml](../cloudbuild-main.yaml) (main-push,
test + auto-deploy) to the `cvsubs74/college-expert` GitHub repo. After this,
every PR runs the test gate automatically and every merge to main runs the
gate plus path-based deploys to production.

Two configs because PR builds must never touch production:

- **`cloudbuild.yaml`** — `college-expert-pr` trigger (every PR). Tests only.
- **`cloudbuild-main.yaml`** — `college-expert-main` trigger (push to main).
  Same tests, then `scripts/cicd/detect_changed_targets.py` + `./deploy.sh`
  for whatever components the merged commit touched.

The PR pipeline runs three checks (under 2 minutes total):

1. **Backend unit tests** — `pytest` against `tests/cloud_functions/`. ~170 tests, sub-second.
2. **Shell-script syntax** — `bash -n` on `deploy.sh` and `deploy_frontend.sh`.
3. **Frontend production build** — `vite build`, catches type/import errors.

The main pipeline runs the same checks, then two more stages:

4. **detect-targets** — `scripts/cicd/detect_changed_targets.py` reads
   `git diff --name-only $COMMIT_SHA^..$COMMIT_SHA` and emits the deploy.sh
   targets to deploy. Doc/test-only diffs produce empty output and the
   deploy step exits 0.
5. **deploy** — runs `./deploy.sh <target>` for each backend target, then
   `./deploy_frontend.sh` if `frontend/` changed. Frontend env is fetched
   from the `frontend-env-prod` Secret Manager entry.

See [docs/prd/auto-deploy-on-main.md](prd/auto-deploy-on-main.md) and
[docs/design/auto-deploy-on-main.md](design/auto-deploy-on-main.md) for the
end-to-end rationale.

## Prerequisites

- Cloud Build API enabled in `college-counselling-478115`.
- Connected repo: GitHub → Cloud Build via the [Cloud Build GitHub App](https://github.com/marketplace/google-cloud-build).
- The Cloud Build service account (`<project-number>@cloudbuild.gserviceaccount.com`) needs the default `roles/cloudbuild.builds.builder` role, which is attached automatically when you enable the API.

If the repo isn't connected yet, run:

```bash
# In the GCP console, navigate to:
#   Cloud Build → Triggers → Manage repositories → CONNECT REPOSITORY
# Pick GitHub (Cloud Build GitHub App), authorize for cvsubs74/college-expert.
# Or via gcloud (1st-gen connection):
gcloud builds connections create github college-expert-github \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115 \
    --region=us-east1
```

## Create the triggers

Two triggers — one for PRs, one for main pushes. Both run the same pipeline,
but the pull-request trigger reports status checks back to GitHub so PRs can
be gated on green.

**Use the Cloud Build console UI for both triggers, not gcloud.** The
`gcloud builds triggers create github` CLI returns `INVALID_ARGUMENT` for
1st-gen GitHub-App-connected repos until at least one trigger has been
created via the console, and even then is unreliable for additional
trigger creation. The console form is straightforward and only takes a
minute.

Open: <https://console.cloud.google.com/cloud-build/triggers/add?project=college-counselling-478115>

### PR trigger — `college-expert-pr`

| Field | Value |
|---|---|
| Name | `college-expert-pr` |
| Description | `Run unit tests + frontend build on every PR` |
| Region | `global` |
| Event | **Pull request** |
| Source — Repository generation | **1st gen** |
| Source — Repository | `cvsubs74/college-expert` |
| Base branch | `^main$` |
| Comment control | **Required except for owners and collaborators** |
| Configuration — Type | **Cloud Build configuration file (yaml or json)** |
| Configuration — Location | **Repository** → `cloudbuild.yaml` |

### Main-push trigger — `college-expert-main`

Same form, with these differences:

| Field | Value |
|---|---|
| Name | `college-expert-main` |
| Description | `Run tests + auto-deploy changed components on push to main` |
| Event | **Push to a branch** |
| Branch | `^main$` |
| Configuration — Location | **Repository** → `cloudbuild-main.yaml` |
| (Comment control field doesn't apply to push triggers) | — |

Important: the **Configuration → Location** field for this trigger must be
`cloudbuild-main.yaml`, not the default `cloudbuild.yaml`. The PR config
must NOT deploy; only the main config has the deploy stages.

### Frontend env in Secret Manager

The deploy stage in `cloudbuild-main.yaml` reads `frontend/.env` from the
`frontend-env-prod` Secret Manager entry. This is a one-time provisioning
step. On a deploy laptop, you already have a working `frontend/.env`;
upload it as the secret:

```bash
gcloud secrets create frontend-env-prod \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115 \
    --replication-policy=automatic \
    --data-file=frontend/.env

# Subsequent updates use add-version:
gcloud secrets versions add frontend-env-prod \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115 \
    --data-file=frontend/.env
```

The build SA (`college-counselling-478115@appspot.gserviceaccount.com`)
already has `roles/editor`, which includes `secretmanager.versions.access`.
No additional IAM needed.

### After both triggers exist

Optionally make the PR check required for merge:
**GitHub repo → Settings → Branches → Branch protection rules → `main` →
Require status checks → tick `college-expert-pr (college-counselling-478115)`**.
After that, no PR can be merged without a green build.

You can verify both triggers exist via gcloud:

```bash
gcloud builds triggers list \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115 \
    --format='table(name,github.pullRequest.branch:label=PR_BRANCH,github.push.branch:label=PUSH_BRANCH)'
```

Should show both `college-expert-pr` and `college-expert-main`.

## Verify the trigger fires

Push any branch to GitHub, open a PR. You should see a "college-expert-pr
(college-counselling-478115)" status appear under the PR Checks tab within
a minute. Click "Details" to follow the build live.

If the PR trigger was created AFTER the PR was opened, the trigger won't
have seen the original event — push an empty commit to fire a "synchronize"
event:

```bash
git commit --allow-empty -m "ci: trigger Cloud Build pipeline"
git push origin <branch>
```

If the trigger still doesn't fire:

- `gcloud builds triggers list --account=cvsubs@gmail.com --project=college-counselling-478115`
  to confirm both triggers exist and aren't `disabled`.
- Check the GitHub side: <https://github.com/settings/installations> — the
  Google Cloud Build app must be installed and have access to
  `cvsubs74/college-expert` (it should appear under "Repository access").
- Inspect a manual run: `gcloud builds submit --config=cloudbuild.yaml .
  --account=cvsubs@gmail.com --project=college-counselling-478115`. This
  bypasses the trigger entirely and runs the pipeline locally on Cloud
  Build, useful for diagnosing pipeline issues vs. trigger config issues.
- Note: PR triggers can't be invoked via `gcloud builds triggers run` —
  the API returns "RunTrigger is not supported for GitHub PullRequest
  Triggers". Push an empty commit instead.

## Running the suite locally

Anyone can reproduce the CI checks before pushing:

```bash
# 1. Backend unit tests — same as the `backend-tests` step.
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-test.txt
pytest -q

# 2. Shell syntax — same as the `bash-syntax` step.
bash -n deploy.sh && bash -n deploy_frontend.sh

# 3. Frontend build — same as the `frontend-build` step.
(cd frontend && npm ci && npm run build)
```

## What this does NOT do (yet)

- **Integration tests against deployed endpoints** — the `test_*.sh` files
  are still manual after deploy. A future trigger could run them automatically
  after a successful deploy job.
- **LLM evals against `counselor_chat`** — scheduled (nightly), not per-PR
  (Gemini calls cost money).
- **Blue/green or canary rollouts.** Cloud Functions/Cloud Run keep prior
  revisions; rollback is "open a revert PR; auto-deploy ships the rollback."

## Auto-deploy semantics

The `college-expert-main` trigger uses `cloudbuild-main.yaml`, which adds
`detect-targets` + `deploy` after the test gate. Path → target mapping is
owned by `scripts/cicd/detect_changed_targets.py` and unit-tested in
`tests/cicd/test_detect_changed_targets.py`. To add a new live cloud function:

1. Add a row to `PATH_TARGET_MAP` in `scripts/cicd/detect_changed_targets.py`.
2. Add a test row to `test_each_live_function_maps`.
3. Add the deploy.sh target if it doesn't already exist.
4. Update `project_live_components_scope.md`.

Doc-only and test-only PRs produce empty `targets.txt` and trigger no deploys.
The build is still green — the deploy stage is a no-op.

## Auto-deploy retro (2026-05-05)

PR #93 shipped the auto-deploy pipeline; the first end-to-end success
required **six follow-up fixes plus one IAM grant**, all caught by the
smoke-test PRs themselves. Future CI/CD changes should review this list
before they land:

| # | Bug | Fix |
|---|---|---|
| 1 | Cloud Build's source clone is shallow; `git diff $SHA^..$SHA` failed in `detect-targets` | `git fetch --depth=2 origin "$COMMIT_SHA"` before the diff (PR #96) |
| 2 | A `$SHA` token inside a bash comment was treated as a substitution by Cloud Build's pre-flight check | Avoid `$UPPERCASE_NAME` in YAML even inside comments (PR #97) |
| 3 | `deploy.sh`'s CI bypass required both `CI=true` AND `BUILD_ID`, but Cloud Build doesn't auto-inject `BUILD_ID` into step containers | Bypass on `CI=true` alone (PR #98) |
| 4 | `deploy.sh` refused to proceed without `gcloud auth list` showing the user account, but the build SA isn't a user account | Skip the auth-list assertion in CI; rely on ADC (PR #99) |
| 5 | `cloudbuild-main.yaml` set `CLOUDSDK_CORE_ACCOUNT=cvsubs@gmail.com`, which forces gcloud away from ADC; every secret/deploy call then failed with "could not fetch" | Drop the env var; defensively `unset` in `deploy.sh`'s CI branch too (PR #101) |
| 6 | The build SA had `roles/editor` but **not** `roles/secretmanager.secretAccessor` — Editor doesn't include Secret Manager | One-time grant: `gcloud projects add-iam-policy-binding ... --role=roles/secretmanager.secretAccessor` |
| 7 | `deploy.sh`'s tool-availability check hard-failed on missing `adk`/`npm`/`firebase` even when only deploying `qa-agent` (which uses just `gcloud`) | Hard-fail only on `gcloud`; warn on the rest (PR #102) |
| 8 | `gcloud functions deploy` succeeds at deploying the code but then calls `run.services.setIamPolicy` (to make the function public-invokable) and fails with 403 unless the build SA has Cloud Run admin permission. Build status goes red even though the new revision is live | One-time grant: `gcloud projects add-iam-policy-binding ... --role=roles/run.admin` (caught on PR #103's profile-manager-v2 deploy) |

Common themes worth pinning:

- **Cloud Build's substitution engine runs on the entire YAML, not just shell-quoted regions.** Comments are not safe from it. Use `$$` or avoid `$UPPERCASE` entirely.
- **`roles/editor` does NOT include Secret Manager, Cloud Scheduler, or the IAM-policy-set permissions on Cloud Run services.** When wiring a build SA, audit the actual permission list against what `deploy.sh` calls. Current minimum grants on the build SA: `roles/editor` + `roles/secretmanager.secretAccessor` + `roles/run.admin`. (Cloud Functions Gen2 deploys go through Cloud Run under the hood, so `roles/run.admin` covers the post-deploy `setIamPolicy` call that makes the function public-invokable.)
- **CI containers don't inherit user gcloud auth.** Anything that pins `CLOUDSDK_CORE_ACCOUNT` to a user email will block ADC fallback. Pin the project, not the account.
- **Test-mode bypasses must be defensive.** A hostile env var elsewhere in the chain (or in a future cloudbuild edit) shouldn't be able to re-introduce a "use the user account" path. `unset` is cheaper than untangling who set what.
