# CI/CD — Architecture Reference

A reusable blueprint for the Cloud-Build-driven CI/CD pattern used in
this project. Built around a small, opinionated set of choices:

- **No GitHub Actions.** Cloud Build runs the pipeline. One config
  file (`cloudbuild.yaml`), two triggers, no per-job YAML sprawl.
- **No auto-deploy.** Merge to `main` runs CI but does **not** push
  to production. Deploy is a deliberate human action via `deploy.sh`.
- **Clean-main guard in the deploy script.** The script refuses to
  deploy unless the working tree is on `main`, clean, and up to date.
- **Same pipeline for PR and main.** PR runs are gated for merge;
  main runs catch regressions if a PR was merged with stale CI.

This is a generalised restatement of the system in
[`cloudbuild.yaml`](../cloudbuild.yaml) +
[`docs/cicd-setup.md`](cicd-setup.md) +
[`deploy.sh`](../deploy.sh) +
[`deploy_frontend.sh`](../deploy_frontend.sh).

---

## 1. What & Why

**What it is.** Every PR and every push to `main` runs a single
~5-minute pipeline that gates merges and catches regressions. Deploys
are manual via `deploy.sh`, which itself enforces "deploy only from
clean main, after CI passed."

**Why this shape:**

1. **CI gates merges; deploys gate themselves.** Auto-deploy is
   tempting but couples two unrelated decisions (does the code build?
   should we ship right now?). Keeping them separate makes it safe to
   merge speculative work and lets the operator pick the deploy
   moment.
2. **One config file = one mental model.** Multi-job GitHub Actions
   workflows fragment fast (one for tests, one for build, one for
   security, one for…). A single `cloudbuild.yaml` is easier to keep
   honest.
3. **Cloud Build co-locates with the rest of the GCP stack.** No
   separate billing, no separate secret management, no third-party
   runner trust boundary.
4. **The clean-main guard makes "what's deployed?" answerable from
   git history alone.** Anyone can `git log origin/main` and read the
   deployed state. No "wait, was this branch deployed?" surprises.

---

## 2. High-Level Architecture

```
                     PR opened or pushed
                              │
                              ▼
                 ┌────────────────────────┐
                 │   Cloud Build trigger   │
                 │ college-expert-pr      │  ← reports status to GitHub
                 │   (event: pull_request)│
                 └───────────┬────────────┘
                             │ same cloudbuild.yaml
                             ▼
        ┌──────────────────────────────────────────┐
        │      pipeline (≤5 min, parallel-ish)      │
        │   1. backend pytest                       │
        │   2. bash -n on deploy scripts            │
        │   3. frontend npm ci + vitest + build +   │
        │      playwright (one shared step)         │
        └────────────────────┬─────────────────────┘
                             │ green
                             ▼
                  GitHub status check passes
                             │
                             ▼
                       PR mergeable
                             │
                             ▼
              ╔══════════════════════════╗
              ║  push to main            ║
              ╚══════════════════════════╝
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
   ┌──────────────────────┐   ┌──────────────────────┐
   │  college-expert-main │   │  human runs           │
   │  (event: push to     │   │  ./deploy.sh <target> │
   │   main)              │   │  from local main      │
   │  same pipeline       │   │  ↓                    │
   │  (regression check)  │   │  clean-main guard     │
   └──────────────────────┘   │  ↓                    │
                              │  gcloud functions     │
                              │  deploy / firebase    │
                              │  hosting deploy / etc │
                              └──────────────────────┘
```

The two triggers run the **same** `cloudbuild.yaml`. The only
difference is the trigger event — PR or push. This avoids "drift
between PR and main pipelines" entirely.

---

## 3. The Pipeline (cloudbuild.yaml)

Five steps, all in one file, designed to fit comfortably under
**5 minutes from cold cache**.

| # | Step | Image | Purpose |
|---|------|-------|---------|
| 1 | Backend pytest | `python:3.12-slim` | Unit tests against `tests/cloud_functions/` (~600 tests, sub-second). Heavy GCP libs are stubbed in `conftest.py` so install is just `pytest + requests`. |
| 2 | Bash syntax check | `gcr.io/cloud-builders/gcloud` | `bash -n deploy.sh deploy_frontend.sh` — catches typos that would break a real deploy. |
| 3-5 | Frontend pipeline | `mcr.microsoft.com/playwright:vX.Y.Z-jammy` | One step that runs `npm ci`, `vitest run`, `vite build`, then `playwright test` against `vite preview`. The Playwright image bundles the browsers, so the cold-start cost is bounded. |

**Why one step for frontend, not three?** `npm ci` is the dominant
cost (~30s with cache, ~2 min cold). Splitting vitest, build, and
Playwright into three Cloud Build steps would re-run `npm ci` per
step. One step shares it.

**Why Playwright runs against `vite preview`, not against deployed
URLs?** Determinism. The E2E config (`frontend/playwright.config.js`)
intercepts every backend HTTP call via `page.route`. The test never
hits a real Cloud Function, so it can't false-fail on production
flakiness.

**Critical detail — the Playwright image version must match the
`@playwright/test` version in `package.json`** because the image
bundles the browser binaries the package expects. Bump both together
when upgrading.

---

## 4. The Two Triggers

Both created via the **Cloud Build console UI** (not `gcloud builds
triggers create github` — that CLI flow is unreliable for 1st-gen
GitHub-App-connected repos).

### `<project>-pr` — PR-time check

| Field | Value |
|-------|-------|
| Event | **Pull request** |
| Source | 1st gen, `<owner>/<repo>` |
| Base branch | `^main$` |
| Comment control | **Required except for owners and collaborators** |
| Configuration | `cloudbuild.yaml` |

The comment-control setting is important: anyone can open a PR, but
external contributors need an owner/collaborator to comment "/gcbrun"
before CI fires. Keeps drive-by attackers from burning your CI quota.

### `<project>-main` — push-to-main regression check

Same form, but **Push to a branch** with `^main$`. Catches the case
where main moves (e.g. a force-push, a multi-PR merge race) without a
fresh PR run.

### Branch protection (GitHub side)

After both triggers exist, in the GitHub repo's **Settings → Branches
→ Branch protection rules → `main`**:

- ✅ Require status checks to pass before merging
- ✅ Tick `<project>-pr (<gcp-project-id>)` as required

Now no PR can be merged until CI is green. Combined with the deploy
script's clean-main guard, this means **every deployed commit was
tested**.

---

## 5. The Deploy Script (`deploy.sh`)

The deploy script is the second half of the system. It enforces:

1. **Branch must be `main`** — refuses to deploy from feature
   branches. The "deploy whatever I have locally" anti-pattern is
   blocked at the source.
2. **Working tree must be clean** (no modifications to tracked
   files). Untracked files like `.claude/` session dirs are
   tolerated.
3. **Local main vs `origin/main`**: a soft warning if they differ —
   not a hard refusal, because the operator can choose to deploy a
   committed-but-not-pulled state if they need to.

Sketch of the guard (it's ~40 lines including the help text):

```bash
if [ "${DEPLOY_ALLOW_DIRTY:-0}" != "1" ]; then
    [ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "not on main"; exit 1; }
    [ -z "$(git status --porcelain -uno)" ]           || { echo "dirty"; exit 1; }
    git fetch origin main --quiet
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || \
        echo "warning: local differs from origin/main"
fi
```

**`DEPLOY_ALLOW_DIRTY=1`** is the documented escape hatch for
emergency hotfixes that genuinely cannot wait for CI. Loud red
warning when used.

### Targets

`./deploy.sh` accepts a single argument naming what to deploy:

```
./deploy.sh                    # deploy everything
./deploy.sh frontend           # frontend only
./deploy.sh qa-agent           # one cloud function
./deploy.sh profile-v2         # another cloud function
./deploy.sh agents             # all the agents (a group)
```

The `case` statement at the bottom dispatches to per-component
functions (`deploy_frontend`, `deploy_qa_agent`, etc.). Each function
is responsible for the `gcloud functions deploy …` (or `firebase
deploy --only hosting`) call for its component.

### Account + project pinning

The script sets `CLOUDSDK_CORE_ACCOUNT` and `CLOUDSDK_CORE_PROJECT`
env vars at the top so every child `gcloud` invocation targets the
right account + project — **without** mutating global gcloud config
(which would leak into other shells / projects).

```bash
GCP_ACCOUNT=${GCP_ACCOUNT:-"<owner>@example.com"}
PROJECT_ID=${GCP_PROJECT_ID:-"<project-id>"}
export CLOUDSDK_CORE_ACCOUNT="$GCP_ACCOUNT"
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"
```

If you have multiple GCP accounts (e.g. personal + work), this
pattern is essential. The script also checks the expected account is
authenticated and refuses to run otherwise.

---

## 6. Test Layout

The repo has one `tests/` tree mirroring `cloud_functions/`:

```
tests/
└── cloud_functions/
    ├── qa_agent/
    │   ├── conftest.py     ← stubs google.cloud.firestore + sets sys.path
    │   ├── test_main_endpoints.py
    │   ├── test_runner.py
    │   ├── test_synthesizer.py
    │   └── …
    └── profile_manager_v2/
        ├── conftest.py
        ├── test_fit_computation_fallback.py
        └── …
```

The crucial pattern: **each cloud function's `conftest.py` stubs the
heavy Google libraries (firestore, firebase-admin, generativeai) at
import time** so tests run fast and CI doesn't need to install
`google-cloud-firestore` (which is large). Tests still exercise real
business logic; only the SDK boundaries are stubbed.

`pytest.ini` at repo root pins discovery + warning filters:

```ini
[pytest]
testpaths = tests
addopts = -ra --strict-markers --strict-config --tb=short
filterwarnings = ignore::DeprecationWarning:google
```

`requirements-test.txt` is **separate** from each cloud function's
runtime `requirements.txt`. CI installs only `pytest + requests`,
keeping the cold-cache install under 30 seconds.

---

## 7. Why No Auto-Deploy?

This is the most opinionated choice. Here's the reasoning:

1. **CI green ≠ ready to ship.** A PR can be technically green but
   semantically wrong — incompatible with current production data,
   missing a config secret, depending on an unmerged frontend
   change. The human deploy step is the natural pause to think
   about that.
2. **Atomic deploys across services need orchestration.** This repo
   has a frontend, multiple cloud functions, and an admin tool that
   touch the same Firestore. Auto-deploy each on merge would race;
   `./deploy.sh all` lets the operator coordinate.
3. **Cost control.** A redeploy of every cloud function on every PR
   merge runs up Cloud Build minutes. Manual gating keeps the
   cadence to "after a meaningful batch lands."
4. **Rollback story.** `git revert` + `./deploy.sh <target>` is the
   rollback. With auto-deploy, you have to chase whatever the most
   recent commit was at deploy time.

The escape hatch: when you DO want auto-deploy for a service that's
stable enough, add a third Cloud Build trigger on push-to-main with a
`steps:` block that runs `./deploy.sh <service>`. Per-service
opt-in. Don't blanket-enable.

---

## 8. Lessons Learned

Real bugs that informed permanent choices:

1. **Branch + cleanliness guard caught real damage.** Before the
   guard, a developer once deployed a feature-branch's WIP code
   directly to production by running `./deploy.sh` in their
   worktree. The guard makes that impossible without an explicit
   `DEPLOY_ALLOW_DIRTY=1`.
2. **`gcloud config set` leaks across shells.** Initial versions of
   the script did `gcloud config set account …`. That mutated the
   user's global gcloud state and broke their other projects.
   Switching to `CLOUDSDK_CORE_*` env vars is fully scoped to the
   process.
3. **Playwright image / package.json drift.** A Playwright minor
   version bump in `package.json` without a matching image bump
   broke CI silently — the package looked for browser binaries the
   image didn't ship. Now the cloudbuild.yaml comment explicitly
   notes the lockstep.
4. **CI status check name has the GCP project ID in it.** GitHub
   shows `<trigger-name> (<gcp-project-id>)`. When tightening branch
   protection, you have to copy that exact string. Easy to miss
   first time.
5. **PR triggers can't be invoked via `gcloud builds triggers run`**
   — the API rejects with "RunTrigger is not supported for GitHub
   PullRequest Triggers." Push an empty commit (`git commit
   --allow-empty -m "ci: re-run"`) instead. Document this so the
   next person doesn't burn an hour on it.

---

## 9. Cost

For a project with ~50 PRs/week:

- **PR builds**: ~50/week × ~5 min = 250 min/week of Cloud Build
- **Main builds**: ~50/week (same trigger count)
- **E2_HIGHCPU_8 machine**: $0.016/min
- **Total**: ~$8/week ≈ $35/month

Plus Firebase Hosting (free tier covers most projects) and Cloud
Functions deploys (zero standing cost; you pay only when functions
run).

---

## 10. Replication Checklist

To stand up this exact pattern in a new project:

### Prerequisites (~30 min)

- [ ] GCP project provisioned with billing enabled.
- [ ] Cloud Build API enabled.
- [ ] Cloud Build's GitHub App installed on the org/user, granted
      access to the target repo.
- [ ] You have repo admin (to set branch protection later).

### Step 1 — `cloudbuild.yaml` at repo root (~15 min)

Use the file in this repo as a starting point. Replace:
- The Python version (`python:3.12-slim`) if needed.
- The Playwright image version to match `@playwright/test` in your
  `package.json`.
- The frontend `dir:` if your frontend isn't at `frontend/`.
- The placeholder `.env` block for your build's required env vars.

Verify locally:
```bash
gcloud builds submit --config=cloudbuild.yaml . \
    --account=<your-account> --project=<your-project>
```

### Step 2 — Triggers (~5 min, console only)

Open `https://console.cloud.google.com/cloud-build/triggers/add`,
create the **PR trigger** and the **main-push trigger** per §4.

Verify both exist:
```bash
gcloud builds triggers list \
    --account=<your-account> --project=<your-project> \
    --format='table(name,github.pullRequest.branch:label=PR,github.push.branch:label=PUSH)'
```

### Step 3 — Branch protection (~2 min, GitHub UI)

Repo → Settings → Branches → add rule for `main`:
- Require status checks
- Tick `<your-pr-trigger-name> (<gcp-project-id>)`

### Step 4 — `deploy.sh` (~30 min — copy + adapt)

Copy `deploy.sh` from this repo. Adapt:
- The `GCP_ACCOUNT`, `PROJECT_ID`, `REGION` constants at the top.
- The list of `deploy_<component>()` functions for your services.
- The `case` dispatcher at the bottom.

Keep the clean-main guard verbatim.

### Step 5 — Test layout (~30 min — start small)

- `tests/<service>/conftest.py` per service, stubbing the heavy
  Google libs.
- `pytest.ini` at root with the same options.
- `requirements-test.txt` with just the stuff CI's pytest step needs.

### Step 6 — Frontend pipeline (~15 min if frontend exists)

- `frontend/playwright.config.js` with `webServer:` pointing at
  `vite preview`, all backend HTTP intercepted via `page.route`.
- `frontend/tests-e2e/` with one happy-path E2E.
- `frontend/package.json` `scripts.test` running `vitest run`.

### Step 7 — Documentation (~10 min)

Drop a `docs/cicd-setup.md` (analogous to ours) describing how to
re-create the triggers if needed. Future operators will thank you.

---

## 11. Where to Read Next

- [`cloudbuild.yaml`](../cloudbuild.yaml) — the actual pipeline
  config, ~100 lines.
- [`docs/cicd-setup.md`](cicd-setup.md) — one-shot setup guide for
  triggers + branch protection.
- [`deploy.sh`](../deploy.sh) — the deploy script + clean-main guard
  + per-component dispatcher.
- [`deploy_frontend.sh`](../deploy_frontend.sh) — the
  `firebase deploy --only hosting` wrapper.
- [`pytest.ini`](../pytest.ini) — backend test discovery + warning
  filters.
- [`frontend/playwright.config.js`](../frontend/playwright.config.js)
  — Playwright setup with intercepted backend HTTP.
- [`docs/qa-agent-architecture.md`](qa-agent-architecture.md) — the
  same blueprint shape applied to a different subsystem (QA agent
  monitoring).
