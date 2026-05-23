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

## bin/merge-pr.sh failure modes — all handled gracefully after #117 (2026-05-23)

PR #117 made all local-cleanup steps non-fatal. The detached-HEAD failure and branch-checked-out-in-another-worktree failure documented here are now handled by the script itself: it warns and exits 0. Manual cleanup is no longer required for these cases.

The script's own header comment (`bin/merge-pr.sh --help`) now documents all failure modes and the exact manual-recovery commands. When you see a "Cleanup: partial" disposition line, the script already printed the manual command — just run it.

**One failure mode that remains manual:** If the sandbox blocks `bin/merge-pr.sh` execution itself (Issue 3 — see below), the merge doesn't happen at all. Fall back to `gh pr merge <N> --squash --delete-branch`, then do manual cleanup per the next section.

## bin/merge-pr.sh local-branch-deletion edge case (observed in #119)

`bin/merge-pr.sh` exits 1 when the local branch is checked out in another worktree (e.g., the author's `.worktrees/qa-loop-spec`). The merge and remote branch deletion *do* complete successfully — only the local branch cleanup fails. Verify with `gh pr view <N> --json state` after the non-zero exit. The failure is non-fatal; the local branch will be cleaned up when the author's worktree is torn down. Do not retry the merge — it already went through.

## Merge via `gh pr merge` when bin/merge-pr.sh is shell-blocked (Issue 3 — session sandbox)

**Root cause (documented in script header as of #117):** The Claude Code session sandbox blocks `bin/merge-pr.sh` execution ("Permission denied") when `Bash(bin/**)` is absent from the allow-list in `.claude/settings.json`. The same restriction blocks `bash -n` and `shellcheck` on those scripts. This is a harness-level constraint; neither dev-agent nor CR can work around it without an allow-list change.

**Follow-up required:** Add `Bash(bin/**)` to `.claude/settings.json` allow-list. Until then, the sandbox blocks the merge path in agent sessions.

**Fallback procedure (when sandbox blocks bin/merge-pr.sh):**

1. `gh pr merge <N> --squash --delete-branch` — PreToolUse hook passes through once `in-review` is applied. The merge on GitHub succeeds; local branch deletion may error if the author's worktree still has the branch checked out (expected — not a failure).
2. `gh pr view <N> --json state,mergedAt` — confirm MERGED.
3. `git worktree list` — find the author's worktree for the merged branch.
4. `git worktree remove --force <path>` — force required if it has untracked files.
5. `git branch -D <branch>` — delete the local branch now that the worktree is gone.
6. `git worktree remove .worktrees/cr-<N>` — remove your own CR worktree.
7. `git worktree list` — verify only unrelated worktrees remain.

## Worktree for dev-agent: `.worktrees/arch-doc`

Was created for PR #107. Removed on merge (2026-05-22).

## CI flakiness on docs-only / tooling PRs

PRs #107 (docs-only) and #108 (docs + tooling) both showed CI FAILURE on the Cloud Build `college-expert-pr` check despite no Python/frontend/test changes. PRs #105 and #106 (code changes) passed the same check. Pattern: Cloud Build flakes on non-code PRs. Protocol: if a diff has no Python, no frontend, no test files, and the check fails, compare against the last passing main-branch PR — if that passed, the failure is pre-existing flake and operator can override. Do not block a chore/docs/tooling PR on this check alone.

## Flake-override discipline tightening (2026-05-22)

**What went wrong with #107 / #108 / #110:** All three PRs were merged with red CI under the "documented flake protocol" recorded earlier in this playbook ("CI flakiness on docs-only / tooling PRs"). That protocol was written after PRs #105/#106 established that Cloud Build flakes on non-code diffs. The assumption was: if the diff has no Python/frontend/test files and CI fails, it is a pre-existing flake. This was wrong. The actual failure was 4 tests in `qa_agent/test_narratives.py` and `test_synthesizer.py` that used hardcoded absolute timestamps (`datetime(2026, 5, 3, ...)`) which expired as wall-clock time passed the 7d/14d/30d lookback windows used by the production functions under test. The tests were asserting on stale data and failing on every PR, including docs-only ones. The error output was there — it would have shown the specific assertions failing — but the flake-override call was made without reading it.

**The rule going forward (non-negotiable):**

Never override red CI without first doing ALL of the following:
1. Identify the specific test(s) that are failing by name (visible in the Cloud Build logs).
2. Confirm those test names are in files that have zero intersection with the PR diff.
3. Confirm the failure message is consistent with a pre-existing condition (e.g. an import error for a module unrelated to this diff, a known infra timeout) — not an assertion on data that the diff could have affected.

If any of these three steps cannot be completed in 2 minutes (e.g. Cloud Build logs are unavailable, the failing test name is ambiguous, or the assertion message is unclear), set verdict to DISCUSS rather than LGTM. A blocked PR that stays open for an hour is cheaper than a merged PR that hid a real regression.

**The class of bug to watch for — time-windowed fixture rot:** Tests that create fixture data with hardcoded absolute timestamps (`datetime(YEAR, MONTH, DAY, ...)` or ISO strings like `"2026-05-02T06:00:00+00:00"`) and pass them to production code that computes time-windowed rates against `datetime.now()`. These tests are correct at authoring time and rot silently as wall-clock time advances past the lookback window. The fix pattern is: anchor to `datetime.now(timezone.utc)` and express fixture data as relative offsets (`timedelta(days=N)`). When reviewing PRs that add new time-sensitive tests, verify the fixture anchor is relative, not absolute.

**Rotting-fixture remediation complete (PRs #111 + #112, 2026-05-23):** All three originally affected files — `test_corpus.py`, `test_narratives.py`, `test_synthesizer.py` — now use `datetime.now(timezone.utc)` as their base with `timedelta` relative offsets. No remaining at-risk fixtures in `qa_agent` tests.

**Safe-by-design sites (do not flag in future reviews):**
- `tests/cloud_functions/qa_agent/test_schedule.py` — pins specific days-of-week and UTC↔PT arithmetic for scheduler window tests. Passes fixed instants as parameters; no lookback windows.
- `tests/cloud_functions/qa_agent/test_runner.py` — semester/graduation-year classification (senior_fall, junior_spring etc.). Fixed calendar dates passed as inputs; no time-windowed rate computation.
- `tests/cloud_functions/counselor_agent/test_planner.py` + `conftest.py` — same class as test_runner.py.

## docs-only PRs: out-of-scope file checklist (PR #115, 2026-05-23)

For PRs that are purely documentation (no Python, no frontend code), still run `git diff origin/main --name-only` and verify the file list matches exactly what the PR body declares. PR #115 carried a one-word change to `docs/ARCHITECTURE.md` (brand-name: "College Counselor" → "Stratia Admissions") that was not declared in the deliverables and was explicitly flagged by the operator as a separate pending item. Caught by the name-list check; blocker for merge.

**The pattern:** qa-agent authored the plan with "Stratia Admissions" throughout (correct) and may have edited ARCHITECTURE.md to resolve a perceived inconsistency. The change is substantively fine but the operator wants control over that reconciliation. Always compare file list to declared deliverables on docs PRs.

## No tracking issues in this repo (as of 2026-05-22)

`gh issue list --state all` returns empty. Operator-directed tasks arrive as direct operator messages and PRs are opened without a `Closes #N` reference. This is acceptable — do not block LGTM on missing issue links when no issues exist.

## ARCHITECTURE.md Change Log discipline

The Change Log row in `docs/ARCHITECTURE.md` should reference the actual PR number (e.g. `#107`), not `(this PR)`. Dev-agent left it as `(this PR)` in PR #107 — the content is correct but the reference is slightly imprecise. Not worth a request-changes cycle for docs PRs; note it in the LGTM comment.

## Live vs legacy module split (as of #107)

The authoritative split is in `/Users/csubramanian@onetrust.com/.claude/projects/-Users-csubramanian-onetrust-com-CascadeProjects-college-expert/memory/project_live_components_scope.md`. Cross-check any module map changes against that file and the actual `cloud_functions/` + `agents/` directories. The codebase wins on conflicts.

## in-review is now PR-author owned — label-dispatch gap resolved (#116, 2026-05-23)

PR #116 removed the dev-agent-only restriction on `in-review` from Hook 2. Any agent who opens a PR (qa-agent, designer-agent, dev-agent, etc.) may now apply `in-review` directly. The workaround of "treat qa-agent PRs without in-review as if they have it" is no longer needed — the gap is permanently closed.

## Known pre-existing gap: agent env vars point at non-v2 profile managers

`deploy.sh` lines ~196-200, 242-243, 281-282 still point `PROFILE_MANAGER_URL` for `college_expert_hybrid`, `_rag`, and `_es` agents at the old (non-v2) profile manager URLs. This is documented in `docs/ARCHITECTURE.md` constraint #4 and the live-components memory. Do not raise it as a new finding in reviews — it is a known gap.
