---
description: Summarize backlog and recent progress from GitHub
allowed-tools: Bash, Read
---

# /status

Print a concise snapshot of the project state. GitHub is the source of truth — read from `gh`, not from local files.

## Steps

### 1. Backlog by priority

```bash
for p in P0 P1 P2; do
  open=$(gh issue list --state open  --label "priority:$p" -L 500 --json number --jq 'length')
  closed=$(gh issue list --state closed --label "priority:$p" -L 500 --json number --jq 'length')
  total=$((open + closed))
  echo "[$p] $closed/$total  (open: $open)"
done
```

### 2. In flight

Issues assigned to me, open:

```bash
gh issue list --state open --assignee @me \
  --json number,title,labels \
  --jq '.[] | "  #\(.number) \(.title)  [\(.labels | map(.name) | join(","))]"'
```

### 3. Open PRs

```bash
gh pr list --state open --json number,title,headRefName,isDraft,statusCheckRollup \
  --jq '.[] | "  #\(.number) \(.title)  (\(.headRefName))  \(.isDraft|if . then "DRAFT" else "" end)"'
```

### 4. Worktrees

```bash
git worktree list
```

### 5. Recent commits on main

```bash
git log --oneline -10 main
```

### 6. Last progress entry

```bash
tail -n 30 harness/progress.md
```

### 7. Next pick — what `/next` would choose

```bash
N=$(bash scripts/gh-next-issue.sh 2>/dev/null) || N=""
if [ -n "$N" ]; then
  gh issue view "$N" --json number,title,labels \
    --jq '"  #\(.number) \(.title)  [\(.labels | map(.name) | join(","))]"'
else
  echo "  (no open unassigned stories)"
fi
```

### 8. Project board URL

```bash
OWNER=$(jq -r .owner .github/project-config.json 2>/dev/null)
PROJ=$(jq -r .project_number .github/project-config.json 2>/dev/null)
if [ -n "$OWNER" ] && [ -n "$PROJ" ] && [ "$PROJ" != "null" ]; then
  echo "Project: https://github.com/users/$OWNER/projects/$PROJ"
fi
```

Format as a short report with these section headers. No prose narration.
