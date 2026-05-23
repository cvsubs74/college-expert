# Code Reviewer Playbook — college-expert

Per-agent scratchpad. Append when you learn something worth keeping; delete when stale.

---

## bin/merge-pr.sh (merged in #108, 2026-05-23)

`bin/merge-pr.sh` is now on main and is the REQUIRED merge path per SDLC.md Step 6. Call it as:

```bash
bin/merge-pr.sh <N> --squash
```

It resolves headRefName before the merge, calls `gh pr merge <N> --squash --delete-branch`, removes the matching `.worktrees/<id>` worktree (clean first, --force fallback), then deletes the local branch. If no worktree exists it logs "nothing to clean" and exits 0.

**Bootstrap exception (one-time only):** PR #108 itself was merged via direct `gh pr merge 108 --squash --delete-branch` because the script did not yet exist on main. That exception is now closed. Never use direct `gh pr merge` again — always call `bin/merge-pr.sh`.

**One known behavior:** `gh pr merge --delete-branch` only removes the remote ref; local branch deletion is a separate step that `bin/merge-pr.sh` handles. If the branch is checked out in a worktree, the worktree must be removed first (which the script does in the correct order).

## Worktree for dev-agent: `.worktrees/arch-doc`

Was created for PR #107. Removed on merge (2026-05-22).

## CI flakiness on docs-only / tooling PRs

PRs #107 (docs-only) and #108 (docs + tooling) both showed CI FAILURE on the Cloud Build `college-expert-pr` check despite no Python/frontend/test changes. PRs #105 and #106 (code changes) passed the same check. Pattern: Cloud Build flakes on non-code PRs. Protocol: if a diff has no Python, no frontend, no test files, and the check fails, compare against the last passing main-branch PR — if that passed, the failure is pre-existing flake and operator can override. Do not block a chore/docs/tooling PR on this check alone.

## No tracking issues in this repo (as of 2026-05-22)

`gh issue list --state all` returns empty. Operator-directed tasks arrive as direct operator messages and PRs are opened without a `Closes #N` reference. This is acceptable — do not block LGTM on missing issue links when no issues exist.

## ARCHITECTURE.md Change Log discipline

The Change Log row in `docs/ARCHITECTURE.md` should reference the actual PR number (e.g. `#107`), not `(this PR)`. Dev-agent left it as `(this PR)` in PR #107 — the content is correct but the reference is slightly imprecise. Not worth a request-changes cycle for docs PRs; note it in the LGTM comment.

## Live vs legacy module split (as of #107)

The authoritative split is in `/Users/csubramanian@onetrust.com/.claude/projects/-Users-csubramanian-onetrust-com-CascadeProjects-college-expert/memory/project_live_components_scope.md`. Cross-check any module map changes against that file and the actual `cloud_functions/` + `agents/` directories. The codebase wins on conflicts.

## Known pre-existing gap: agent env vars point at non-v2 profile managers

`deploy.sh` lines ~196-200, 242-243, 281-282 still point `PROFILE_MANAGER_URL` for `college_expert_hybrid`, `_rag`, and `_es` agents at the old (non-v2) profile manager URLs. This is documented in `docs/ARCHITECTURE.md` constraint #4 and the live-components memory. Do not raise it as a new finding in reviews — it is a known gap.
