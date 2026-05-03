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

```bash
# PR trigger: every PR touching the default branch.
gcloud builds triggers create github \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115 \
    --region=global \
    --name=college-expert-pr \
    --repo-name=college-expert \
    --repo-owner=cvsubs74 \
    --pull-request-pattern='^main$' \
    --build-config=cloudbuild.yaml \
    --comment-control=COMMENTS_ENABLED \
    --description='Run unit tests + frontend build on every PR'

# Main-push trigger: every commit landing on main.
gcloud builds triggers create github \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115 \
    --region=global \
    --name=college-expert-main \
    --repo-name=college-expert \
    --repo-owner=cvsubs74 \
    --branch-pattern='^main$' \
    --build-config=cloudbuild.yaml \
    --description='Run unit tests + frontend build on every push to main'
```

After creating the triggers, optionally make them required status checks on
the default branch in GitHub: **Settings → Branches → Branch protection rules →
main → Require status checks**, and tick the `college-expert-pr` check.

## Verify the trigger fires

Push any branch to GitHub, open a PR. You should see a "Cloud Build / college-expert-pr"
status appear under the PR Checks tab within a minute. Click "Details" to
follow the build live.

If the trigger doesn't fire:

- `gcloud builds triggers list --account=cvsubs@gmail.com --project=college-counselling-478115`
  to confirm both triggers exist.
- Check the GitHub side: **Settings → Integrations → Google Cloud Build** —
  the app must be installed for the repo.
- Inspect a manual run: `gcloud builds submit --config=cloudbuild.yaml . --account=cvsubs@gmail.com --project=college-counselling-478115`. This bypasses the trigger entirely and runs the pipeline locally on Cloud Build, useful for diagnosing pipeline issues vs. trigger config issues.

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
