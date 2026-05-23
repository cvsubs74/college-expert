#!/usr/bin/env bash
# merge-pr.sh — canonical squash-merge path for Code Reviewer agents.
#
# Usage:
#   bin/merge-pr.sh <PR-NUMBER> [--squash|--merge|--rebase] [--no-cleanup] [--force-cleanup]
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
#   4. Removes the matching worktree under .worktrees/<task-id> if one exists
#      (best-effort: logs a warning and exits 0 if removal fails).
#   5. Deletes the local branch if it still exists — best-effort (--delete-branch
#      only removes the remote ref; local is separate). Failures here are
#      NON-FATAL: they are logged as warnings and the script exits 0.
#
# Recovery:
#   If a worktree is already gone (Dev cleaned up, or CR worked from the
#   primary repo), the script logs "no worktree to clean" and exits 0.
#
# Known failure modes (all handled gracefully — merge still succeeds):
#   Detached-HEAD context:
#     Running from `gh pr checkout --detach <N>` or any detached worktree is
#     safe. The merge succeeds on GitHub; local-branch deletion is skipped with
#     a warning. Manual cleanup: git branch -D <branch>
#
#   Branch checked out in another worktree:
#     If the merged branch is still checked out in the PR author's worktree
#     (e.g. .worktrees/qa-browser-test-plan), git refuses branch deletion.
#     The script warns and exits 0. Manual cleanup:
#       git worktree remove .worktrees/<task-id>
#       git branch -D <branch>
#
#   Worktree has untracked/modified files:
#     Clean removal fails; --force is tried. If force also fails (e.g. sandbox
#     restrictions block destructive git ops — see §Sandbox note below), the
#     script warns and exits 0.
#
#   Session-sandbox restriction (Claude Code):
#     The Claude Code session sandbox may block execution of bin/merge-pr.sh
#     itself ("Permission denied") when the Bash allow-list in
#     .claude/settings.json does not include Bash(bin/merge-pr.sh) or
#     Bash(bin/**). If the script cannot be executed:
#       1. Fall back to: gh pr merge <N> --squash --delete-branch
#       2. Then run manual local cleanup (git worktree remove / git branch -D).
#       3. File an issue to widen the allow-list or add Bash(bin/**) to
#          .claude/settings.json permissions.
#
# Options:
#   --no-cleanup       Skip all local cleanup steps (worktree + branch deletion).
#                      Useful in CI or when the caller knows they'll clean up.
#   --force-cleanup    Escalate to --force on worktree removal if clean removal
#                      fails. Default: warn-and-continue rather than force-remove.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
  sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

log()  { echo "==> $*"; }
info() { echo "    $*"; }
warn() { echo "WARN: $*" >&2; }
err()  { echo "ERROR: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

PR_NUMBER=""
MERGE_FLAG="--squash"
NO_CLEANUP=0
FORCE_CLEANUP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --squash|--merge|--rebase)
      MERGE_FLAG="$1"
      shift
      ;;
    --no-cleanup)
      NO_CLEANUP=1
      shift
      ;;
    --force-cleanup)
      FORCE_CLEANUP=1
      shift
      ;;
    -h|--help)
      usage
      ;;
    -*)
      err "Unknown flag '$1'. Use --squash, --merge, --rebase, --no-cleanup, or --force-cleanup."
      ;;
    *)
      if [[ -z "$PR_NUMBER" ]]; then
        PR_NUMBER="$1"
      else
        err "Unexpected argument '$1'."
      fi
      shift
      ;;
  esac
done

if [[ -z "$PR_NUMBER" ]]; then
  echo "Error: PR number is required." >&2
  usage
fi

if [[ ! "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
  err "PR number must be a positive integer, got: $PR_NUMBER"
fi

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
# Step 2 — Merge (LOAD-BEARING: only non-zero exit that counts)
# ---------------------------------------------------------------------------

log "Merging PR #${PR_NUMBER} ($MERGE_FLAG --delete-branch)..."
gh pr merge "$PR_NUMBER" "$MERGE_FLAG" --delete-branch
log "Merge complete."

# Everything below is best-effort cleanup. No step below should exit non-zero.

if [[ "$NO_CLEANUP" -eq 1 ]]; then
  log "Cleanup skipped (--no-cleanup). PR #${PR_NUMBER} merged."
  exit 0
fi

# ---------------------------------------------------------------------------
# Step 3 — Worktree cleanup (best-effort)
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

CLEANUP_STATUS="OK"

if [[ -z "$WORKTREE_PATH" ]]; then
  log "No worktree found for branch '$HEAD_BRANCH' — nothing to clean up."
else
  info "Found worktree: $WORKTREE_PATH"
  log "Removing worktree (best-effort)..."
  # Try clean removal first. Escalate to --force only if the caller passed
  # --force-cleanup (opt-in). Default is warn-and-continue so we never
  # silently nuke a worktree with uncommitted work.
  if git -C "$REPO_ROOT" worktree remove "$WORKTREE_PATH" 2>/dev/null; then
    info "Worktree removed cleanly."
  elif [[ "$FORCE_CLEANUP" -eq 1 ]]; then
    log "Clean removal failed — retrying with --force (--force-cleanup is set)..."
    if git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_PATH" 2>/dev/null; then
      info "Worktree removed (forced)."
    else
      warn "Could not remove worktree at $WORKTREE_PATH even with --force."
      warn "Manual cleanup: git worktree remove --force $WORKTREE_PATH"
      CLEANUP_STATUS="partial"
    fi
  else
    warn "Could not remove worktree at $WORKTREE_PATH (clean removal failed)."
    warn "Tip: re-run with --force-cleanup to force-remove, or manually:"
    warn "     git worktree remove --force $WORKTREE_PATH"
    CLEANUP_STATUS="partial"
  fi
fi

# ---------------------------------------------------------------------------
# Step 4 — Delete local branch if it still exists (best-effort)
# (--delete-branch removes the remote ref; local is separate)
#
# Non-fatal: failures here indicate the branch is checked out in another
# worktree (e.g. the PR author's dev worktree) or we are in a detached-HEAD
# context. The merge on GitHub already succeeded — this is bookkeeping only.
# ---------------------------------------------------------------------------

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$HEAD_BRANCH" 2>/dev/null; then
  log "Deleting local branch '$HEAD_BRANCH' (best-effort)..."
  if git -C "$REPO_ROOT" branch -D "$HEAD_BRANCH" 2>/dev/null; then
    info "Local branch deleted."
  else
    warn "Could not delete local branch '$HEAD_BRANCH'."
    warn "Likely cause: branch is checked out in another worktree, or detached-HEAD context."
    warn "Manual cleanup: git branch -D $HEAD_BRANCH  (after freeing any worktree that has it checked out)"
    CLEANUP_STATUS="partial"
  fi
else
  info "Local branch '$HEAD_BRANCH' does not exist locally — skipping."
fi

# ---------------------------------------------------------------------------
# Done — report disposition
# ---------------------------------------------------------------------------

if [[ "$CLEANUP_STATUS" == "OK" ]]; then
  log "Done. PR #${PR_NUMBER} merged and workspace cleaned up."
else
  log "Done. PR #${PR_NUMBER} merged. Cleanup: partial — see warnings above."
fi
