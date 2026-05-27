---
description: First-session bootstrap — seed GitHub Issues, draft architecture, fill init/verify, enable branch protection
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# /kickoff

You are running the **first session** of a new product built on the engineering-workflow harness. Your job is to bootstrap the project from `docs/spec.md` so every future session has the state it needs — and to make GitHub the visible center of gravity for the work.

## Preconditions

1. `docs/spec.md` exists and is non-empty. If empty, stop and ask the user to fill it in.
2. `gh auth status` shows a logged-in user with scopes including `project` and `read:org`. If `project` is missing, run `gh auth refresh -s project,read:org` and re-check.
3. A GitHub remote exists (`git remote get-url origin`). If not, stop and tell the user to run `/start` first.
4. `gh issue list --label meta:bootstrap --state closed --limit 1 --json number --jq '.[0].number'` returns nothing — i.e. no prior kickoff. If it has output, stop: project is already kicked off; ask the user whether to abort or treat this as an additive update.

## Steps

### 1. Bootstrap repo state (idempotent)

Run `bash scripts/gh-bootstrap.sh`. This syncs labels, ensures `v0.1` milestone, creates the Projects v2 board with custom fields (Status, Estimate, Iteration, Worktree), and writes `.github/project-config.json`. Safe to re-run.

### 2. product-manager — seed the backlog

Dispatch the `product-manager` agent with this brief:

> Read `docs/spec.md`. File the backlog as GitHub Issues following the agent spec (see `.claude/agents/product-manager.md`):
> - 3-6 `type:epic` issues, one per major capability cluster, labeled `area:<name>` and `meta:bootstrap`, added to milestone `v0.1`.
> - 15-30 `type:story` issues, one per atomic feature, labeled `type:story`, `priority:P0|P1|P2`, `area:<name>`, added to milestone `v0.1`. Each story body follows the canonical schema with `### Acceptance criteria` as a `- [ ]` checkbox list.
> - For each story, run `scripts/gh-sub-issue.sh <epic#> <story#>` to link it as a sub-issue of its parent epic.
> - For each story, run `scripts/gh-project.sh add-item <story#>` to put it on the board.
> - If the product uses areas not already in `.github/labels.json`, add them and re-run `scripts/gh-bootstrap.sh` to sync.

### 3. architect — draft architecture

Dispatch the `architect` agent:

> Read `docs/spec.md` and `gh issue list --label type:epic --json number,title,body`. Draft `docs/architecture.md` covering stack, modules, data model, dependencies, cross-cutting concerns. Record the stack choice as `harness/decisions/0001-stack.md` AND file a closed `type:spike` + `meta:bootstrap` issue linking to it.

### 4. devops — fill init.sh / verify.sh / CI

Dispatch the `devops` agent:

> Read `docs/architecture.md` for the stack choice. Fill `harness/init.sh` (idempotent, brings the dev env up), `harness/verify.sh` (real end-to-end smoke test, exits 0/non-zero). Write `.github/workflows/ci.yml` — **the job must be named `verify`**; branch protection at the end of this command requires a check by that exact name. Extend `.github/labels.json` with any `area:*` entries the product needs.

### 5. Verify the baseline

```bash
bash harness/init.sh
bash harness/verify.sh
```

Must exit 0. If not, the devops agent's work failed — return to it.

### 6. Append kickoff entry to progress.md

```
## <YYYY-MM-DD HH:MM> — kickoff
- Spec: docs/spec.md
- Epics filed: <N> (issues #...)
- Stories filed: <N> (P0: <a>, P1: <b>, P2: <c>)
- Architecture: <one-line stack summary>
- ADR 0001: <stack rationale>
- Bootstrap issues closed: <N> (audit trail)
```

### 7. Commit and push

```bash
git add -A
git commit -m "Kickoff: seed backlog, architecture, harness scripts"
git push -u origin main
```

### 8. Watch the first CI run

The push triggers `.github/workflows/ci.yml`. Watch the first run:

```bash
sleep 5   # give Actions a moment to register the run
RUN_ID=$(gh run list --branch main --workflow ci.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch "$RUN_ID" --exit-status
```

If CI fails, stop here. Fix the baseline (devops issue), commit, push again, re-watch. Do not enable branch protection until CI is green at least once.

### 9. Configure merge style and enable branch protection

```bash
REPO_NWO="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

# Squash merge with branch delete (default merge style)
gh api --method PATCH "repos/$REPO_NWO" \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F allow_squash_merge=true \
  -F delete_branch_on_merge=true >/dev/null

# Branch protection: require the `verify` check, allow self-merge
gh api --method PUT "repos/$REPO_NWO/branches/main/protection" \
  --input - <<'EOF'
{
  "required_status_checks": { "strict": true, "contexts": ["verify"] },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

### 10. Report

Print:

```
✓ Kickoff complete.
  Repo:          <gh repo url>
  Project:       <project url>
  Milestone:     v0.1
  Epics filed:   <N>
  Stories filed: <N> (P0: <a>, P1: <b>, P2: <c>)
  CI:            green on main
  Protection:    enabled (requires `verify` check)
  Merge style:   squash, delete branch on merge

Next:
  /status                 see the backlog
  /next                   pick the top P0 and start building
  /parallel <issue-#>     work on an issue in an isolated worktree
```

## Failure handling

- If any subagent fails, do **not** push partially. Leave commits local, surface the error, ask the user.
- If CI fails on first run, fix the cause (typically a devops issue) and re-push. Don't disable the workflow.
- If branch protection fails to apply (auth scope, permissions), surface the error with `gh auth refresh -s admin:org` (or similar) as a hint. The harness still works without protection; it's a defense-in-depth layer.
