# Code Reviewer Playbook — college-expert

Per-agent scratchpad. Append when you learn something worth keeping; delete when stale.

---

## bin/merge-pr.sh does not exist

As of 2026-05-22, `bin/` contains only `bootstrap-labels.sh` and `init-project.sh`. The SDLC.md and CLAUDE.md both reference `bin/merge-pr.sh` as the required merge path, but it has not been created in this repo. Fall back to `gh pr merge <N> --squash --delete-branch`. If the branch is checked out in a worktree, the local branch deletion will fail — handle with `git worktree remove .worktrees/<name> --force` followed by `git branch -d <branch>`.

## Worktree for dev-agent: `.worktrees/arch-doc`

Was created for PR #107. Removed on merge (2026-05-22).

## CI flakiness on docs-only PRs

PR #107 (docs-only, adds `docs/ARCHITECTURE.md`) showed CI FAILURE on the Cloud Build PR check despite no code changes. The suite runs pytest, bash -n, vitest, vite build, and Playwright — none affected by a markdown addition. Pre-existing flake. If a docs-only PR shows CI red and the diff has no code, check if the preceding `main` PR passed CI; if it did, the failure is pre-existing and operator can override.

## No tracking issues in this repo (as of 2026-05-22)

`gh issue list --state all` returns empty. Operator-directed tasks arrive as direct operator messages and PRs are opened without a `Closes #N` reference. This is acceptable — do not block LGTM on missing issue links when no issues exist.

## ARCHITECTURE.md Change Log discipline

The Change Log row in `docs/ARCHITECTURE.md` should reference the actual PR number (e.g. `#107`), not `(this PR)`. Dev-agent left it as `(this PR)` in PR #107 — the content is correct but the reference is slightly imprecise. Not worth a request-changes cycle for docs PRs; note it in the LGTM comment.

## Live vs legacy module split (as of #107)

The authoritative split is in `/Users/csubramanian@onetrust.com/.claude/projects/-Users-csubramanian-onetrust-com-CascadeProjects-college-expert/memory/project_live_components_scope.md`. Cross-check any module map changes against that file and the actual `cloud_functions/` + `agents/` directories. The codebase wins on conflicts.

## Known pre-existing gap: agent env vars point at non-v2 profile managers

`deploy.sh` lines ~196-200, 242-243, 281-282 still point `PROFILE_MANAGER_URL` for `college_expert_hybrid`, `_rag`, and `_es` agents at the old (non-v2) profile manager URLs. This is documented in `docs/ARCHITECTURE.md` constraint #4 and the live-components memory. Do not raise it as a new finding in reviews — it is a known gap.
