#!/usr/bin/env bash
# Session-start banner: orient any new Claude session against GitHub state.
# Output goes to additionalContext for the model.

set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "=== engineering-workflow harness ==="
echo "cwd: $(pwd)"
echo

# --- git context ---
if [ -d .git ]; then
  echo "--- last 5 commits ---"
  git log --oneline -5 2>/dev/null || echo "(no commits yet)"
  echo
  BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "(detached)")
  echo "--- branch ---"
  echo "$BRANCH"
  echo
fi

# --- GitHub context (fail open if gh missing or not authenticated) ---
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1 && git remote get-url origin >/dev/null 2>&1; then
  # If on an issue-<n>-* branch, surface the linked issue.
  case "${BRANCH:-}" in
    issue-*)
      N=$(printf '%s' "$BRANCH" | sed -E 's/^issue-([0-9]+).*/\1/')
      if [ -n "$N" ] && [ "$N" != "$BRANCH" ]; then
        echo "--- linked issue ---"
        gh issue view "$N" --json number,title,state,labels,assignees \
          --jq '"#\(.number) [\(.state)] \(.title)\n  labels: \(.labels | map(.name) | join(", "))\n  assignees: \(.assignees | map(.login) | join(", "))"' 2>/dev/null \
          || echo "(could not fetch issue #$N)"
        echo
      fi
      ;;
  esac

  echo "--- open issues assigned to you ---"
  gh issue list --assignee @me --state open --limit 10 \
    --json number,title,labels \
    --jq '.[] | "  #\(.number) \(.title)  [\(.labels | map(.name) | join(","))]"' 2>/dev/null \
    || echo "  (gh issue list failed)"
  echo

  echo "--- open PRs ---"
  gh pr list --state open --limit 10 \
    --json number,title,headRefName,isDraft,statusCheckRollup,reviewDecision \
    --jq '.[] | "  #\(.number) \(.title)  (\(.headRefName)) \(.reviewDecision // "no-review") \(.isDraft|if . then "DRAFT" else "" end)"' 2>/dev/null \
    || echo "  (gh pr list failed)"
  echo

  # Next pick — what /next would choose
  echo "--- next pick (/next) ---"
  if NEXT_N=$(bash scripts/gh-next-issue.sh 2>/dev/null); then
    gh issue view "$NEXT_N" --json number,title,labels \
      --jq '"  #\(.number) \(.title)  [\(.labels | map(.name) | join(","))]"' 2>/dev/null \
      || echo "  #$NEXT_N"
  else
    echo "  (no open unassigned stories)"
  fi
  echo
else
  echo "--- GitHub state ---"
  echo "  (gh not installed, not authenticated, or no remote — run /start to set up)"
  echo
fi

# --- progress log ---
if [ -f harness/progress.md ]; then
  echo "--- last progress entry ---"
  tail -n 20 harness/progress.md
  echo
fi

echo "Next: read CLAUDE.md and run /next (or /start if this is a fresh boilerplate, or /kickoff after /start)."
