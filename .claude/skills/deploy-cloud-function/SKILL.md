---
name: deploy-cloud-function
description: Deploy a single College Counselor cloud function (or the frontend) safely — uses deploy.sh's built-in cvsubs@gmail.com / college-counselling-478115 pin and a live-components guard so legacy *_es / *_rag / *_vertexai functions are never deployed by accident.
disable-model-invocation: true
---

# Deploying a cloud function

This is a **user-invoked, side-effecting** skill. It deploys real
infrastructure to GCP project `college-counselling-478115`. Never run it
speculatively.

## Before you deploy

1. Confirm you are on a merged/intended commit, not mid-edit work.
2. `harness/verify.sh` is green.
3. The target is a **live** component (see below). Legacy variants are offline —
   deploying them is always a mistake.

## Live components only

Deploy *only* these (from auto-memory `project_live_components_scope`):

- `counselor_agent`
- `profile_manager_v2`
- `payment_manager_v2`
- `contact_form`
- `qa_agent`
- `knowledge_base_manager_universities_v2`
- the React frontend (Firebase Hosting)

If asked to deploy `*_es`, `*_rag`, `*_vertexai`, `profile_manager` (v1),
`payment_manager` (v1), or `knowledge_base_manager_universities` (v1) — **stop**
and confirm with the user; these are legacy/offline.

## How to deploy

`deploy.sh` already pins the account and project internally
(`GCP_ACCOUNT=cvsubs@gmail.com`, `PROJECT_ID=college-counselling-478115`) — do
not re-pin or override unless the user asks.

```bash
./deploy.sh agent        # counselor_agent
./deploy.sh profile      # profile_manager (maps to the live v2 target)
./deploy.sh knowledge    # knowledge_base_manager_universities_v2
./deploy.sh functions    # all live cloud functions
./deploy.sh backend      # agent + all functions
./deploy.sh frontend     # Firebase Hosting (or ./deploy_frontend.sh)
```

Run `./deploy.sh` with no args only when the user explicitly wants a full
deploy.

## After you deploy

- Confirm the deploy reported success for the named target.
- Note that `main`-merged changes also auto-deploy via path-based
  `cloudbuild-main.yaml` — a manual deploy is usually only for hotfixes or
  pre-merge validation. Mention if a manual deploy may race the pipeline.

## Hard rules

- **Never deploy legacy/offline functions.** See the live list above.
- **Never strip the account pin.** The machine default account is OneTrust;
  without the pin you deploy to the wrong account.
- **Don't deploy on a dirty tree** without telling the user what's uncommitted.
