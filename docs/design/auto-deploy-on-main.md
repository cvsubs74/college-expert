# Design: Auto-deploy on main

Status: Proposed
Last updated: 2026-05-05
Related PRD: [docs/prd/auto-deploy-on-main.md](../prd/auto-deploy-on-main.md)

## Architecture

Two Cloud Build configurations, both at the repo root:

| File | Trigger | Stages |
|---|---|---|
| `cloudbuild.yaml` | `college-expert-pr` (every PR) | tests only — unchanged |
| `cloudbuild-main.yaml` | `college-expert-main` (push to main) | tests + path detection + deploy |

The PR config stays as-is — we are not adding a deploy step to PR builds. The main config reuses the exact test stages from `cloudbuild.yaml` and appends a path-detection stage and a deploy stage.

The `college-expert-main` trigger is reconfigured (one-time, console UI per `docs/cicd-setup.md`) to point at `cloudbuild-main.yaml` instead of `cloudbuild.yaml`.

```
push → main
  ↓
  ├─ backend-tests        ← same as PR config (pytest)
  ├─ bash-syntax          ← same as PR config (bash -n on deploy*.sh)
  ├─ frontend             ← same as PR config (vitest + vite build + playwright)
  ↓ (waits for above)
  ├─ detect-targets       ← runs scripts/cicd/detect_changed_targets.py
  ↓
  └─ deploy               ← reads /workspace/targets.txt and runs ./deploy.sh / ./deploy_frontend.sh
```

A red test stage skips both `detect-targets` and `deploy` because Cloud Build aborts on first step failure by default.

## Path detection

`scripts/cicd/detect_changed_targets.py` is a small, dependency-free Python script (uses only stdlib + a `subprocess` call to `git`). It owns the **single** source of truth for `path-prefix → deploy.sh target` mapping.

### Inputs

```
$ python3 scripts/cicd/detect_changed_targets.py [--rev-range REV1..REV2]
```

Default rev range is `HEAD^..HEAD` — appropriate for the squash-merge style this repo uses, where every PR becomes one commit on main. CI passes `${COMMIT_SHA}^..${COMMIT_SHA}` explicitly to be deterministic.

### Output

Newline-separated deploy targets, deduplicated, sorted, written to stdout. Empty output (zero bytes) means "no live component changed; skip deploy."

### Mapping table

```python
PATH_TARGET_MAP = [
    # cloud_functions — only the live ones from project_live_components_scope.md
    ("cloud_functions/profile_manager_v2/",                "profile-v2"),
    ("cloud_functions/payment_manager_v2/",                "payment-v2"),
    ("cloud_functions/counselor_agent/",                   "counselor-agent"),
    ("cloud_functions/contact_form/",                      "contact"),
    ("cloud_functions/knowledge_base_manager_universities_v2/", "knowledge-universities-v2"),
    ("cloud_functions/knowledge_base_manager/",            "knowledge-rag"),
    ("cloud_functions/knowledge_base_manager_ES/",         "knowledge-es"),
    ("cloud_functions/qa_agent/",                          "qa-agent"),
    # agents — live Cloud Run services
    ("agents/college_expert_hybrid/",                      "agent-hybrid"),
    ("agents/college_expert_rag/",                         "agent-rag"),
    ("agents/college_expert_es/",                          "agent-es"),
    # frontend
    ("frontend/",                                          "frontend"),
]
```

The script iterates the changed files and adds a target whenever a file path starts with the prefix. Order matters only for prefix overlap, which the table avoids — every prefix is non-overlapping.

### Deliberately excluded

- `cloud_functions/profile_manager`, `_es`, `_vertexai` — replaced by `_v2`, dead code.
- `cloud_functions/payment_manager` — replaced by `_v2`.
- `cloud_functions/knowledge_base_manager_universities` (no `_v2`) — Elasticsearch-backed, ES cluster offline.
- `cloud_functions/knowledge_base_manager_vertexai` — UI selector removed.
- `cloud_functions/scheduled_notifications` — cron-only, no `deploy.sh` target. (If we wire one later, add the row.)
- `agents/college_expert_adk` — vertexai removed.
- `agents/source_curator`, `agents/sourcery`, `agents/uniminer`, `agents/university_profile_collector` — standalone tools, not part of the main app.
- `docs/`, `tests/`, `scripts/`, `cloudbuild*.yaml`, `deploy*.sh`, top-level `*.md`, `requirements-test.txt` — infrastructure changes. A change here does not by itself ship to a runtime; the next runtime-touching PR will redeploy with the latest infra.

A change that only touches excluded paths produces empty output → no deploy.

### Frontend env-var changes

A change to `frontend/.env.example` is not a frontend deploy trigger by path — `.env.example` lives in the frontend dir and matches the `frontend/` prefix, but it doesn't affect the built bundle. We accept the false-positive (a no-op redeploy is harmless) rather than complicating the matcher with file-level exclusions.

## Cloud Build stages (`cloudbuild-main.yaml`)

Stages 1–3 are byte-identical to the PR config. Stages 4–5 are new.

```yaml
substitutions:
  _DEPLOY_ACCOUNT: 'cvsubs@gmail.com'
  _DEPLOY_PROJECT: 'college-counselling-478115'

steps:
  # 1–3: backend-tests, bash-syntax, frontend — verbatim from cloudbuild.yaml
  ...

  # 4. Compute deploy targets from the diff between the merged commit and its parent.
  - name: 'gcr.io/cloud-builders/git'
    id: 'detect-targets'
    waitFor: ['backend-tests', 'bash-syntax', 'frontend']
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        set -euo pipefail
        # Cloud Build clones the repo with full history when the trigger is
        # configured with "Include logs from CI hooks" + the default. The
        # sha-range form below works for squash-merge commits on main.
        python3 scripts/cicd/detect_changed_targets.py \
            --rev-range "${COMMIT_SHA}^..${COMMIT_SHA}" \
          > /workspace/targets.txt
        echo "::: deploy targets :::"
        cat /workspace/targets.txt || echo "(none)"

  # 5. Run ./deploy.sh for each backend target, then ./deploy_frontend.sh if
  #    frontend changed. Sequential — keeps blast radius readable in the log.
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'deploy'
    waitFor: ['detect-targets']
    entrypoint: 'bash'
    env:
      - 'CLOUDSDK_CORE_ACCOUNT=${_DEPLOY_ACCOUNT}'
      - 'CLOUDSDK_CORE_PROJECT=${_DEPLOY_PROJECT}'
      - 'GCP_ACCOUNT=${_DEPLOY_ACCOUNT}'
      - 'GCP_PROJECT_ID=${_DEPLOY_PROJECT}'
    args:
      - '-c'
      - |
        set -euo pipefail
        if [ ! -s /workspace/targets.txt ]; then
          echo "No deploy targets — skipping."
          exit 0
        fi

        # Run frontend last so it picks up any newly-deployed backend URLs.
        backend_targets=$(grep -v '^frontend$' /workspace/targets.txt || true)
        frontend_target=$(grep '^frontend$' /workspace/targets.txt || true)

        for t in $backend_targets; do
          echo "::: deploy.sh $t :::"
          ./deploy.sh "$t"
        done

        if [ -n "$frontend_target" ]; then
          echo "::: deploy_frontend.sh :::"
          # Pull the rendered .env from Secret Manager rather than the laptop file.
          gcloud secrets versions access latest \
              --secret=frontend-env-prod > frontend/.env
          # Use ADC for firebase deploy. The CI deploy SA already has roles/editor
          # which covers firebasehosting.sites.update.
          export FIREBASE_TOKEN=""  # force ADC path in firebase-tools
          ./deploy_frontend.sh
        fi
```

## Frontend deploy in CI

The current `deploy_frontend.sh` has two laptop-only assumptions that would block CI:

1. `firebase login:list 2>/dev/null | grep -q "$FIREBASE_ACCOUNT"` — fails because the build container has no logged-in Firebase user.
2. `frontend/.env` must exist on disk — fails because the repo doesn't (and shouldn't) ship that file.

**Fix 1** — replace the login check with a CI-aware branch:

```bash
if [ -n "${CI:-}" ] || [ -n "${BUILD_ID:-}" ]; then
    echo "CI run — using application default credentials for Firebase."
    # firebase-tools picks up GOOGLE_APPLICATION_CREDENTIALS from the
    # Cloud Build environment automatically (mounted at
    # /workspace/serviceaccount.json by gcr.io/cloud-builders/gcloud).
elif ! firebase login:list 2>/dev/null | grep -q "$FIREBASE_ACCOUNT"; then
    # ... existing error message
fi
```

`BUILD_ID` is set in every Cloud Build environment, so the gate is reliable.

**Fix 2** — the deploy step writes `frontend/.env` from Secret Manager before invoking `deploy_frontend.sh` (see Cloud Build stage 5 above). The script's existing `if [ ! -f .env ]; then exit 1` continues to work as a defence in depth.

A new Secret Manager entry `frontend-env-prod` is created once, holding the full rendered `.env` content (the same content a deploying engineer would have on their laptop today). The PRD's "single secret holding the .env" choice keeps the surface small — adding individual `VITE_*` secrets would mean ~20 round-trips on every deploy.

## IAM

The `college-expert-main` trigger's Cloud Build service account is `college-counselling-478115@appspot.gserviceaccount.com` — the App Engine default SA — which already has `roles/editor`. That covers:

- `cloudfunctions.functions.create/update/get` (cloud-function deploys)
- `run.services.update/get` (Cloud Run / agent deploys)
- `firebasehosting.sites.update` (frontend deploy)
- `secretmanager.versions.access` (reading `frontend-env-prod`)
- `iam.serviceAccounts.actAs` against `qa-agent@…iam.gserviceaccount.com` (the qa-agent function's runtime SA — required because `gcloud functions deploy --service-account=...` checks actAs)

A future hardening PR can swap to a dedicated `cicd-deployer@…iam.gserviceaccount.com` with the minimum role set above. For v1 we ride the existing grant.

## Test plan

### Unit tests (`tests/cicd/test_detect_changed_targets.py`)

The path-detector script is the only piece of new code that has logic worth covering. Tests parametrise `_targets_for_files()` (the pure function the CLI wraps) so they don't shell out to `git`.

| Test | Input files | Expected targets |
|---|---|---|
| qa-agent backend change | `cloud_functions/qa_agent/main.py` | `['qa-agent']` |
| qa-agent scenario JSON | `cloud_functions/qa_agent/scenarios/all_uc_only.json` | `['qa-agent']` |
| profile-v2 + frontend | `cloud_functions/profile_manager_v2/main.py`, `frontend/src/App.tsx` | `['frontend', 'profile-v2']` |
| docs only | `docs/prd/foo.md`, `README.md` | `[]` |
| tests only | `tests/cloud_functions/qa_agent/test_runner.py` | `[]` |
| cloudbuild config | `cloudbuild.yaml` | `[]` |
| deploy script edit | `deploy.sh` | `[]` |
| dead code (legacy) | `cloud_functions/profile_manager/main.py` | `[]` |
| sorted output | `frontend/x.ts`, `cloud_functions/qa_agent/main.py` | `['frontend', 'qa-agent']` (alphabetical) |
| dedup | `cloud_functions/qa_agent/main.py`, `cloud_functions/qa_agent/runner.py` | `['qa-agent']` |
| live agent | `agents/college_expert_hybrid/main.py` | `['agent-hybrid']` |
| dead agent | `agents/college_expert_adk/main.py` | `[]` |

Plus a CLI integration test that shells out to a temp git repo, makes a known commit, and asserts stdout matches the expected target list.

### Bash syntax

The existing `bash-syntax` step runs `bash -n deploy.sh deploy_frontend.sh`. We extend it to cover `cloudbuild-main.yaml` indirectly: a separate `python3 -c "import yaml; yaml.safe_load(open('cloudbuild-main.yaml'))"` step verifies the new YAML parses. (Cloud Build itself does not validate config server-side until trigger save time, so a parse check at build time is the earliest safe gate.)

### Smoke verification on first run

After the trigger is reconfigured to use `cloudbuild-main.yaml`:

1. Open a docs-only PR, merge it. Build should run all test stages, then `detect-targets` produces empty output, `deploy` step exits 0 without deploying anything. **Expected: zero new revisions on any cloud function.**

2. Open a `cloud_functions/qa_agent/` PR (e.g. comment-only edit), merge it. **Expected: `qa-agent-NNNNN` revision created within 5 minutes of merge; `gcloud run revisions list` confirms the revision's creation timestamp matches the build time.**

3. Open a multi-component PR (e.g. `cloud_functions/qa_agent/` + `frontend/`), merge it. **Expected: backend deploys first, then frontend; final hosting release timestamp matches the build.**

If step 2 or 3 fails, revert via `gcloud builds triggers describe` to point the trigger back at `cloudbuild.yaml` (the previous config) and triage from the failed build's logs.

## Phasing

We can ship this in one PR — the path detector is small, the cloudbuild change is additive (new file alongside the existing one), and the trigger reconfiguration is a one-line console change. No phased rollout needed.

## Risks

- **A deploy stage failure leaves CI red while production is fine.** Mitigation: each `./deploy.sh <target>` is idempotent (re-running a deploy uploads the same source again). A red deploy step blocks no merge — it's on the main branch — but it does emit a CI failure email. Operators can re-run the build from the Cloud Build console.
- **Path detector misses a new live component.** Mitigation: PRs introducing a new live component must update both `project_live_components_scope.md` and `scripts/cicd/detect_changed_targets.py`. The latter has unit tests, so a missing entry is caught when the contributor adds the corresponding test row.
- **Secret leak via build logs.** `frontend-env-prod` is fetched and written to a file; the file is not echoed. `deploy_frontend.sh` already echoes individual URL values but never the Firebase API key. No new logging is introduced.
- **Concurrent runs / state contamination.** Out of scope here — the QA agent's mutex (PRs #89/#91) handles that for QA-agent runs. Cloud Function deploys are inherently sequential per-function on the GCP side.
