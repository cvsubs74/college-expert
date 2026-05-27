---
description: Spawn a git worktree for parallel work on a GitHub Issue
allowed-tools: Bash, Read, Edit
argument-hint: <issue-number>
---

# /parallel $ARGUMENTS

Create an isolated git worktree so another Claude session can build issue `#$ARGUMENTS` in parallel without conflicting with the current session.

## Steps

1. Confirm `$ARGUMENTS` is a number. Strip leading `#` if present.
2. Confirm the issue is OPEN, has no assignee, and is not labeled `type:epic`:

   ```bash
   gh issue view $ARGUMENTS --json state,assignees,labels --jq \
     'if .state != "OPEN" then "error:not-open"
      elif (.assignees | length) > 0 then "error:assigned"
      elif (.labels | map(.name) | index("type:epic")) then "error:epic"
      else "ok" end'
   ```

   Stop with the matching error if not `ok`.

3. Run:

   ```bash
   bash scripts/new-worktree.sh $ARGUMENTS
   ```

   This creates `../<repo>-wt-issue-$ARGUMENTS` on branch `issue-$ARGUMENTS-<slug>` and posts a comment on the issue announcing the worktree path.

4. Print:

   ```
   Worktree ready at <path>. Open a new terminal:

     cd <path>
     claude
     > /next

   That session will pick up issue #$ARGUMENTS automatically (it's the issue on this branch).
   When done, run /ship from inside the worktree to push, open a PR, and merge.
   ```

## Notes

- Don't enter the worktree from this session. The point is a fresh Claude session per worktree.
- If `scripts/new-worktree.sh` fails, surface the error verbatim — it already prints clear messages.
- The worktree path is recorded only as a comment on the issue. There is no local state file.
