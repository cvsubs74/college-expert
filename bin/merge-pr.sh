#!/usr/bin/env bash
# merge-pr.sh — canonical squash-merge path for Code Reviewer agents.
#
# Usage:
#   bin/merge-pr.sh <PR-NUMBER> [--squash|--merge|--rebase]
#
# Defaults to --squash if merge flag is omitted.
#
# Why this script exists:
#   PostToolUse hooks from settings.json do NOT fire in agent sub-sessions
#   (anthropics/claude-code #34692). Hook 7 (cleanup-on-merge) is silent for
#   agent-driven merges. This script runs worktree cleanup explicitly, making
#   it work in all contexts — from interactive operators to CR agent sessions.
#
# What it does:
#   1. Resolves the PR's head branch name (before the merge removes it).
#   2. Prints what it is about to do.
#   3. Calls `gh pr merge <N> <flag> --delete-branch` (Hook 6 enforces
#      --delete-branch; this script always passes it).
#   4. Removes the matching worktree under .worktrees/<task-id> if one exists.
#   5. Deletes the local branch if it still exists (--delete-branch only
#      removes the remote ref).
#
# Recovery:
#   If a worktree is already gone (Dev cleaned up, or CR worked from the
#   primary repo), the script logs "no worktree to clean" and exits 0.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

log()  { echo "==> $*"; }
info() { echo "    $*"; }
err()  { echo "ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

PR_NUMBER="${1:-}"
MERGE_FLAG="${2:---squash}"

if [[ -z "$PR_NUMBER" ]]; then
  echo "Error: PR number is required." >&2
  usage
fi

if [[ ! "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
  err "PR number must be a positive integer, got: $PR_NUMBER"
fi

case "$MERGE_FLAG" in
  --squash|--merge|--rebase) ;;
  *) err "Unknown merge flag '$MERGE_FLAG'. Use --squash, --merge, or --rebase." ;;
esac

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

if ! command -v gh >/dev/null 2>&1; then
  err "gh CLI not found. Install from https://cli.github.com/"
fi
if ! command -v git >/dev/null 2>&1; then
  err "git not found."
fi

# Resolve repo root — needed for worktree parsing regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Step 1 — Resolve head branch BEFORE the merge removes the remote ref
# ---------------------------------------------------------------------------

log "Resolving PR #${PR_NUMBER} head branch..."
HEAD_BRANCH="$(gh pr view "$PR_NUMBER" --json headRefName -q .headRefName 2>/dev/null)" \
  || err "Could not retrieve PR #${PR_NUMBER}. Is the PR number correct and do you have gh auth?"

if [[ -z "$HEAD_BRANCH" ]]; then
  err "gh returned an empty headRefName for PR #${PR_NUMBER}."
fi

info "PR #${PR_NUMBER}  head branch : $HEAD_BRANCH"
info "Merge flag                    : $MERGE_FLAG"
info "Will delete remote branch     : yes (--delete-branch)"

# ---------------------------------------------------------------------------
# Step 2 — Merge
# ---------------------------------------------------------------------------

log "Merging PR #${PR_NUMBER} ($MERGE_FLAG --delete-branch)..."
gh pr merge "$PR_NUMBER" "$MERGE_FLAG" --delete-branch
log "Merge complete."

# ---------------------------------------------------------------------------
# Step 3 — Worktree cleanup
#
# Parse `git worktree list --porcelain` to find a worktree whose branch
# matches HEAD_BRANCH. Worktrees live under .worktrees/<task-id>/ per SDLC.
# ---------------------------------------------------------------------------

log "Scanning worktrees for branch '$HEAD_BRANCH'..."

WORKTREE_PATH=""
# Parse porcelain output: blocks separated by blank lines; each block has
#   worktree <path>
#   HEAD <sha>
#   branch refs/heads/<name>   (or "detached" for detached HEAD)
current_path=""
while IFS= read -r line; do
  if [[ "$line" == worktree\ * ]]; then
    current_path="${line#worktree }"
  elif [[ "$line" == "branch refs/heads/${HEAD_BRANCH}" ]]; then
    WORKTREE_PATH="$current_path"
    break
  fi
done < <(git -C "$REPO_ROOT" worktree list --porcelain)

if [[ -z "$WORKTREE_PATH" ]]; then
  log "No worktree found for branch '$HEAD_BRANCH' — nothing to clean up."
else
  info "Found worktree: $WORKTREE_PATH"
  log "Removing worktree..."
  # Prefer clean removal; use --force only if the working tree has untracked
  # files or locked state (common for agent sessions that were interrupted).
  if git -C "$REPO_ROOT" worktree remove "$WORKTREE_PATH" 2>/dev/null; then
    info "Worktree removed cleanly."
  else
    log "Clean removal failed — retrying with --force..."
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_PATH"
    info "Worktree removed (forced)."
  fi
fi

# ---------------------------------------------------------------------------
# Step 4 — Delete local branch if it still exists
# (--delete-branch removes the remote ref; local is separate)
# ---------------------------------------------------------------------------

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$HEAD_BRANCH" 2>/dev/null; then
  log "Deleting local branch '$HEAD_BRANCH'..."
  git -C "$REPO_ROOT" branch -D "$HEAD_BRANCH"
  info "Local branch deleted."
else
  info "Local branch '$HEAD_BRANCH' does not exist — skipping."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

log "Done. PR #${PR_NUMBER} merged and workspace cleaned up."
