# CI/CD Setup — Cloud Build for college-expert

This is a one-time setup guide for wiring [cloudbuild.yaml](../cloudbuild.yaml)
to the `cvsubs74/college-expert` GitHub repo. After this, every PR and every
push to `main` runs the pipeline automatically.

The pipeline runs three checks (under 2 minutes total):

1. **Backend unit tests** — `pytest` against `tests/cloud_functions/`. ~170 tests, sub-second.
2. **Shell-script syntax** — `bash -n` on `deploy.sh` and `deploy_frontend.sh`.
3. **Frontend production build** — `vite build`, catches type/import errors.

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
| Description | `Run unit tests + frontend build on every push to main` |
| Event | **Push to a branch** |
| Branch | `^main$` |
| (Comment control field doesn't apply to push triggers) | — |

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

- **Frontend tests** — Vitest + Playwright are Phase 2 of the CI plan.
- **Integration tests against deployed endpoints** — the `test_*.sh` files
  are still manual after deploy. A future trigger could run them automatically
  after a successful deploy job.
- **LLM evals against `counselor_chat`** — Phase 3, scheduled (nightly), not
  per-PR (Gemini calls cost money).
- **Auto-deploy on merge to main** — intentional. Deploy stays manual via
  `./deploy.sh` until we trust the test coverage enough to gate auto-deploys
  on it. See the readiness assessment in the project history for details.
