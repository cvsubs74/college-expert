#!/usr/bin/env bash
# merge-worktree.sh
#
# Run from inside a worktree on a branch named issue-<n>-<slug>. Verifies
# locally, pushes the branch, opens a PR via gh (with "Closes #<n>" in the
# body) if one isn't already open. Does NOT merge locally — branch protection
# on main and `/ship` finish the job.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

command -v gh >/dev/null || { echo "error: gh CLI required" >&2; exit 1; }

BRANCH="$(git symbolic-ref --short HEAD)"
case "$BRANCH" in
  issue-*) ;;
  *) echo "error: not on an issue-* branch (currently on $BRANCH)" >&2; exit 1 ;;
esac

N=$(printf '%s' "$BRANCH" | sed -E 's/^issue-([0-9]+).*/\1/')
if [ -z "$N" ] || [ "$N" = "$BRANCH" ]; then
  echo "error: could not extract issue number from branch '$BRANCH'" >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree not clean — commit or stash before /ship" >&2
  exit 1
fi

echo "Running verify.sh in worktree..."
bash harness/verify.sh

echo "Pushing $BRANCH to origin..."
git push -u origin "$BRANCH"

# Open PR if missing
EXISTING_PR=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number' 2>/dev/null || true)
if [ -z "$EXISTING_PR" ] || [ "$EXISTING_PR" = "null" ]; then
  TITLE=$(gh issue view "$N" --json title --jq .title 2>/dev/null || echo "$BRANCH")
  gh pr create --base main --head "$BRANCH" \
    --title "$TITLE (#$N)" \
    --body "Closes #${N}"
  EXISTING_PR=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number')
fi

echo
echo "PR #$EXISTING_PR open against main. Awaiting CI + review."
echo "Run /ship to merge once CI is green and the reviewer has approved."
