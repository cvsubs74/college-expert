# DevOps Playbook — college-expert

Running notebook for project-specific deploy knowledge. Append when you learn something; delete when it goes stale.

---

## Frontend deploy (Firebase Hosting)

**Command:** `./deploy_frontend.sh` from the worktree root.

**Account/project pinning:** The script auto-pins `cvsubs@gmail.com` + `college-counselling-478115`. No manual `--account`/`--project` flags needed when running the script (it handles them internally).

**Firebase site:** `college-strategy` (NOT `college-counsellor.web.app` — that hosts UniMiner, a different app).

**Custom domain:** `https://stratiaadmissions.com` maps to the `college-strategy` live channel.

**Verify release timestamp after deploy:**
```bash
firebase hosting:channel:list --account cvsubs@gmail.com --project college-counselling-478115 --site college-strategy
```

### Gotcha: `.env` not in worktrees

`frontend/.env` is gitignored. When deploying from a fresh worktree it won't be present. Copy it from the primary repo:
```bash
cp /path/to/college-expert/frontend/.env .worktrees/<worktree>/frontend/.env
```
The primary repo at `/Users/csubramanian@onetrust.com/CascadeProjects/college-expert/frontend/.env` is the authoritative source. Never commit `.env`.

### Smoke checks
After deploy, curl both:
- `https://stratiaadmissions.com/` — expect HTTP 200, ~6KB HTML
- `https://stratiaadmissions.com/roadmap` — expect HTTP 200, SPA shell (same ~6KB HTML, React router handles the route client-side)

---

## Cloud Functions deploy

**Command:** `./deploy.sh <target>` — use `./deploy.sh --help` for valid target names. Target names do NOT match function names 1:1; e.g. `profile-manager-v2` the function deploys via `./deploy.sh profile-v2`.

Pass `--account cvsubs@gmail.com --project college-counselling-478115` to any raw `gcloud` invocations outside the script.

### Gotcha: clean-main guard — deploy from primary repo `main`, not from worktrees

`deploy.sh` has a branch-name guard: it refuses to deploy unless `git branch --show-current` returns `main`. Worktrees are on named branches (e.g. `devops/deploy-131`), so they always trip this guard. `deploy_frontend.sh` has no such guard.

**Correct pattern for Cloud Functions deploys:**
1. `git fetch origin && git pull --ff-only origin main` in the PRIMARY repo (not a worktree).
2. If tracked files are modified locally, `git stash push -m "..." <file>` before pulling.
3. Run `./deploy.sh <target>` from the primary repo root.
4. `git stash pop` to restore after deploy.

`DEPLOY_ALLOW_DIRTY=1` bypasses both branch AND cleanliness checks — only for genuine emergencies where waiting is not an option.

### Gotcha: CI/CD pipeline may already be deploying

Merging a PR to `main` triggers a Cloud Build pipeline that auto-deploys affected functions. If you attempt a manual deploy within ~5 minutes of a merge, you may get `409: unable to queue the operation`. Check first:
```bash
gcloud functions describe <function> --gen2 --region=us-east1 \
  --account cvsubs@gmail.com --project college-counselling-478115 \
  --format="table(state,updateTime)"
gcloud builds list --account cvsubs@gmail.com --project college-counselling-478115 --limit 3 \
  --format="table(id,status,createTime)"
```
If `state=DEPLOYING` and there's a `WORKING` build, wait for CI to finish — it's deploying the same code. No manual intervention needed.

### Verify deployed env vars (critical for config changes)
```bash
gcloud functions describe <function> --gen2 --region=us-east1 \
  --account cvsubs@gmail.com --project college-counselling-478115 \
  --format="value(serviceConfig.environmentVariables)"
```

### Get current Cloud Run revision
```bash
gcloud run services describe <function> --region=us-east1 \
  --account cvsubs@gmail.com --project college-counselling-478115 \
  --format="table(status.latestReadyRevisionName,status.traffic[0].percent)"
```

### Security note: env.deploy.yaml

`deploy.sh` writes `cloud_functions/<name>/env.deploy.yaml` during deploy. This file contains plaintext secret values (GEMINI_API_KEY etc.). It is now gitignored (`env.deploy.yaml`, `**/env.deploy.yaml` added 2026-05-23). Never commit it; safe to delete locally after confirming deploy succeeded.

---

## Deploy history (abbreviated)

| Date | PR | What | Release / Notes |
|---|---|---|---|
| 2026-05-23 | #132 | `fix(roadmap): coerce profile.grade to string before .trim()` | `college-strategy` live, 16:11:24Z; smoke PASS |
| 2026-05-23 | #131 | `feat(profile_manager_v2): widen clear-test-data allow-list` | CI deployed `profile-manager-v2-00089-zuh`, 23:16:39Z; env var confirmed; destructive smoke deferred pending QA loop completion |
