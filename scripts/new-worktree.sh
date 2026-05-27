#!/usr/bin/env bash
# new-worktree.sh <issue-number>
#
# Creates ../<repo>-wt-issue-<n> as a git worktree on a new branch
# issue-<n>-<slug> off main. Resolves the issue title via gh and posts a
# comment on the issue announcing the worktree path.
#
# Does NOT touch features.json (that file no longer exists). All state
# lives on GitHub.

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $0 <issue-number>" >&2
  exit 2
fi

N="${1#\#}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

command -v gh >/dev/null || { echo "error: gh CLI required" >&2; exit 1; }

# Fetch issue title + state
ISSUE_JSON=$(gh issue view "$N" --json title,state,number 2>/dev/null || true)
if [ -z "$ISSUE_JSON" ]; then
  echo "error: issue #$N not found in this repo" >&2
  exit 1
fi
STATE=$(echo "$ISSUE_JSON" | jq -r .state)
if [ "$STATE" != "OPEN" ]; then
  echo "error: issue #$N is $STATE; refusing to start a worktree on a closed issue" >&2
  exit 1
fi

TITLE=$(echo "$ISSUE_JSON" | jq -r .title)
# Slug: strip "[Type] " prefix, lowercase, non-alnum→hyphen, trim, max 40 chars
SLUG=$(printf '%s' "$TITLE" \
  | sed -E 's/^\[[^]]+\] *//' \
  | tr 'A-Z' 'a-z' \
  | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' \
  | cut -c1-40 \
  | sed -E 's/-+$//')

if [ -z "$SLUG" ]; then
  SLUG="work"
fi

BRANCH="issue-${N}-${SLUG}"
REPO_NAME="$(basename "$ROOT")"
WT_PATH="$(cd .. && pwd)/${REPO_NAME}-wt-issue-${N}"

if [ -e "$WT_PATH" ]; then
  echo "error: $WT_PATH already exists" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "error: branch $BRANCH already exists" >&2
  exit 1
fi

BASE_BRANCH="$(git symbolic-ref --short HEAD)"
git worktree add -b "$BRANCH" "$WT_PATH" "$BASE_BRANCH"

# Announce on the issue
gh issue comment "$N" --body "Worktree opened: \`$WT_PATH\` on branch \`$BRANCH\`."

echo
echo "Worktree ready: $WT_PATH"
echo "Branch:         $BRANCH"
echo "Issue:          #$N — $TITLE"
echo
echo "Open a new terminal:"
echo "  cd \"$WT_PATH\""
echo "  claude"
echo "  > /next"
