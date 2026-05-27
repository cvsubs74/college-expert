---
description: Merge a PR back into main and clean up — runs from the issue branch or its worktree
allowed-tools: Bash, Read, Edit
---

# /ship

Squash-merge the PR for the current issue into `main`, confirm the issue auto-closes, move the project card to Done, and remove the worktree if applicable.

## Preconditions

You are on a branch named `issue-<n>-*` (either in the main repo or in its worktree).

The PR for this branch is OPEN, CI is GREEN, and the reviewer has APPROVED (or the harness is solo and you're self-approving — branch protection still requires CI).

## Steps

### 1. Extract issue number from branch

```bash
BRANCH=$(git symbolic-ref --short HEAD)
case "$BRANCH" in
  issue-*) ;;
  *) echo "error: not on an issue-* branch ($BRANCH)" >&2; exit 1 ;;
esac
N=$(echo "$BRANCH" | sed -E 's/^issue-([0-9]+).*/\1/')
```

### 2. Verify locally

```bash
git status                  # clean
bash harness/verify.sh      # exit 0
```

### 3. Push any final commits and confirm PR state

```bash
git push
PR=$(gh pr list --head "$BRANCH" --json number,state,mergeable --jq '.[0]')
[ -n "$PR" ] || { echo "error: no PR for $BRANCH — run scripts/merge-worktree.sh first or open one manually" >&2; exit 1; }
echo "$PR" | jq -e '.state == "OPEN" and .mergeable == "MERGEABLE"' >/dev/null \
  || { echo "error: PR not mergeable. State: $PR"; exit 1; }
```

### 4. Confirm CI is green and review is approved

```bash
PR_NUM=$(echo "$PR" | jq -r .number)
gh pr checks "$PR_NUM" --required   # exits non-zero if any required check is failing/pending
gh pr view "$PR_NUM" --json reviewDecision --jq '.reviewDecision' \
  | grep -qE '^(APPROVED|null)$'    # APPROVED, or null if no protection enforced reviews
```

If checks aren't green, stop. Branch protection will block the merge anyway — surface the failing check to the user.

### 5. Merge

```bash
gh pr merge "$PR_NUM" --squash --delete-branch
```

This:
- Squash-merges into `main`.
- Closes issue `#$N` via the `Closes #$N` in the PR body.
- Deletes the remote branch.

### 6. Update the project board

```bash
bash scripts/gh-project.sh set-status "$N" "Done"
```

### 7. Clean up the local branch and worktree

If we're in a worktree:

```bash
WT_ROOT=$(git rev-parse --show-toplevel)
MAIN_ROOT=$(git worktree list --porcelain | awk '$1=="worktree"{p=$2} $1=="branch" && $2 ~ /^refs\/heads\/main$/ {print p; exit}')
cd "$MAIN_ROOT"
git fetch --prune
git worktree remove "$WT_ROOT"
git branch -D "$BRANCH" 2>/dev/null || true
```

If we're in the main repo:

```bash
git checkout main
git pull --ff-only
git branch -D "$BRANCH" 2>/dev/null || true
```

### 8. Append progress.md entry

On `main`:

```
## <YYYY-MM-DD HH:MM> — shipped #<N>
- PR #<pr-num>, squash-merged, branch deleted
- Issue closed, project card → Done
```

Commit + push:

```bash
git add harness/progress.md
git commit -m "log(ship): #$N shipped"
git push
```

### 9. Report

Print:

```
✓ Shipped #<N>.
  PR:     <url>
  Issue:  closed
  Board:  Done
Recent log:
  <git log --oneline -5>
```

## Failure handling

- **Required check failing:** surface which check, link to its run, stop. Don't override.
- **Merge conflict:** `gh pr merge` will report it. Tell the user to rebase locally on `main`, push, and re-run `/ship`. Don't auto-resolve.
- **Worktree remove fails:** typically means uncommitted state. Surface, ask the user.
