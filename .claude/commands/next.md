---
description: Build the next highest-priority open GitHub Issue, end to end
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent
---

# /next

Build **one** issue, sequentially, on a new branch off `main`. Use `/parallel <issue-#>` instead if you want to work in a worktree.

## Steps

### 1. Verify baseline

```bash
pwd
git status                  # working tree must be clean
git log --oneline -5
bash harness/init.sh
bash harness/verify.sh      # must exit 0
```

If `verify.sh` fails, **stop**. Fix the baseline as its own commit on `main` before picking an issue.

### 2. Pick the issue

```bash
N=$(bash scripts/gh-next-issue.sh)
```

`N` is the issue number. If the script exits non-zero, the backlog is empty or every story/bug is assigned — tell the user, stop.

Fetch the title for branch naming and announce:

```bash
TITLE=$(gh issue view "$N" --json title --jq .title)
echo "Building issue #$N — $TITLE"
```

### 3. Claim the issue

```bash
gh issue edit "$N" --add-assignee @me
bash scripts/gh-project.sh set-status "$N" "In progress"
```

### 4. Create the branch

Derive a slug from the title (lowercase, alnum + hyphens, max 40 chars) — see `scripts/new-worktree.sh` for the canonical recipe. Branch name: `issue-<n>-<slug>`.

```bash
git checkout main
git pull --ff-only
git checkout -b "issue-${N}-<slug>"
```

### 5. Run the agent pipeline

Dispatch in order, passing each agent the issue number `N`:

1. **product-manager** — re-read `gh issue view $N` body. Canonicalize the schema if needed. Flag ambiguous acceptance.
2. **architect** — only if the issue is `type:epic`-spanning or labeled `area:*` for a new domain.
3. **implementer** — write code. Commit messages format: `<type>(<area>): <subject> (#$N)`.
4. **tester** — runs `verify.sh`, posts evidence comment, ticks `### Acceptance criteria` checkboxes (only the tester touches those).
5. **reviewer** — runs after the PR is open (step 7); blocks via `gh pr review --request-changes`.

### 6. Push the branch

```bash
git push -u origin "issue-${N}-<slug>"
```

### 7. Open the PR

```bash
gh pr create --base main --head "issue-${N}-<slug>" \
  --title "$TITLE (#$N)" \
  --body "Closes #$N"
bash scripts/gh-project.sh set-status "$N" "In review"
```

Now invoke the **reviewer** agent on the open PR.

### 8. Append progress.md entry

```
## <YYYY-MM-DD HH:MM> — #<N> <title>
- Implementer: <one-line approach>
- Tester evidence: posted on issue
- PR: #<pr-number>
- Reviewer: approved | changes requested
```

Commit and push:

```bash
git add harness/progress.md
git commit -m "log(#$N): session note"
git push
```

### 9. Hand off

Tell the user: PR URL, current state ("In review" until reviewer approves and CI is green), next command (`/ship`).

## Hard rules

- **Do not edit `### Acceptance criteria`** to make a check pass. Push back to product-manager if it's wrong.
- **Do not touch other issues** in the same session. If you find a blocker, file a new issue via `gh issue create` and stop.
- **Do not skip `verify.sh`.** It must be green before *and* after.
- **Do not merge the PR yourself.** `/ship` does that, after reviewer approves and CI is green.
- **One issue per session.** When the PR is open and reviewer-approved, stop. `/ship` is a separate step.
