---
description: Write a retrospective for a shipped issue — appends to progress.md and posts a comment on the closed issue
allowed-tools: Bash, Read, Edit, Write
argument-hint: <issue-number>
---

# /retro $ARGUMENTS

Write a retrospective for issue `#$ARGUMENTS` (or the most recently shipped issue if no argument is given). Append it to `harness/progress.md` AND post it as a final comment on the closed issue, so the audit trail lives on GitHub.

## Steps

### 1. Identify the issue

If `$ARGUMENTS` is provided, use it. Otherwise, find the most recent shipped issue:

```bash
N=$(git log --oneline -20 main | grep -oE '\(#[0-9]+\)' | head -1 | tr -d '()#')
```

If `N` is empty, stop and ask the user to pass an issue number.

### 2. Verify issue is closed

```bash
STATE=$(gh issue view "$N" --json state --jq .state)
[ "$STATE" = "CLOSED" ] || { echo "error: issue #$N is $STATE; only retro closed issues" >&2; exit 1; }
```

### 3. Gather context

```bash
gh issue view "$N" --json title,body,labels
gh pr list --search "#$N" --state closed --json number,title,mergedAt --jq '.[0]'
git log --oneline --grep "#$N" -20
```

### 4. Append to progress.md

```
## <YYYY-MM-DD HH:MM> — retro #<N>
- **What worked**: <1-3 bullets>
- **What didn't**: <1-3 bullets, or "nothing notable">
- **Surprises**: <anything learned mid-build>
- **Follow-ups**: <new issue numbers filed, or "none">
- **Memory candidates**: <facts worth saving to user/project memory, or "none">
```

### 5. Post the same retro as a comment on the closed issue

```bash
gh issue comment "$N" --body-file - <<'EOF'
### Retro

- **What worked**: ...
- **What didn't**: ...
- **Surprises**: ...
- **Follow-ups**: ...
EOF
```

### 6. File follow-up issues (if any)

For each follow-up surfaced during retro, create a new GitHub Issue:

```bash
gh issue create \
  --title "<title>" \
  --label "type:story,priority:P2,area:<name>" \
  --body "Follow-up from retro of #$N: <one-line context>"
```

Update the progress.md "Follow-ups" line with the new issue numbers.

### 7. Commit

```bash
git add harness/progress.md
git commit -m "log(retro): #$N"
git push
```

## Notes

- Retros are short. Three bullets per section is the cap.
- If the retro surfaces blocking work, file it as `priority:P1`, not `P2`.
- Memory candidates: facts that are non-obvious and useful for *future* sessions. Skip if nothing genuinely surprising came up — saving routine entries dilutes memory.
