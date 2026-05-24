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

## Best-effort handler pattern: 200-always with success:false body (#139, 2026-05-23)

When a Cloud Function handler wraps a best-effort side-effect (welcome email, analytics ping, notification), the correct HTTP contract is 200-always with a `{success: bool, error?: str}` payload — not 500 on failure. A 500 propagates through axios as a thrown error, causing browser console noise and breaking fire-and-forget callers.

Checklist when reviewing a new best-effort endpoint or a change to an existing one:

1. **Confirm all failure branches return 2xx.** Both the False-return branch and the except branch must return 200 (or 202 for async).
2. **Confirm the response body still carries `success: false`.** The 200 status is for the transport layer; the boolean tells the caller what actually happened. Removing it entirely would make silent failures undetectable.
3. **Trace every caller.** For each caller, verify: (a) no retry logic keyed on HTTP status, (b) no error toast keyed on HTTP status, (c) the `.catch` firing on 500 is the ONLY failure signal (if so, 200 correctly silences it).
4. **Check for scheduler/webhook callers.** A cloud scheduler that fires a best-effort endpoint and expects 500 on failure for alerting would have its alert silenced by a 200. Grep `cloudbuild*.yaml`, `deploy.sh`, and `scripts/` for references before approving the change.

**Simulation-only tests vs. real handler tests:** When a handler test file uses `_simulate_fixed_handler()`-style inline functions rather than calling the real handler, it cannot catch a regression where someone re-introduces the bug in `main.py` without touching the test. This is acceptable when the Flask/functions-framework runtime is not available in the unit test harness, but call it out as a gap in the LGTM comment and suggest a follow-up integration test if the harness is ever extended.

## Known pre-existing gap: agent env vars point at non-v2 profile managers

`deploy.sh` lines ~196-200, 242-243, 281-282 still point `PROFILE_MANAGER_URL` for `college_expert_hybrid`, `_rag`, and `_es` agents at the old (non-v2) profile manager URLs. This is documented in `docs/ARCHITECTURE.md` constraint #4 and the live-components memory. Do not raise it as a new finding in reviews — it is a known gap.

## QA_TEST_USER_EMAIL: two-tier env-var contract (#128, 2026-05-23)

`QA_TEST_USER_EMAIL` means different things to two different consumers — this is a cross-flow contract trap to watch for in future deploy.sh PRs.

- **`profile_manager_v2`** (`cloud_functions/profile_manager_v2/main.py`): parses the env var as a comma-separated **allow-list** (`.split(',')` + strip + filter). Accepts multiple emails. Widened in #128.
- **`qa_agent`** (`cloud_functions/qa_agent/main.py` line 84): reads the env var as a **raw single string** — no split — and uses it verbatim as the Firebase login account email for the entire runner session. Passing a comma-separated value here breaks Firebase auth, every profile-manager API call, and the `/health` response.

**Invariant:** the `qa-agent` block in `deploy.sh` must always carry a single email for `QA_TEST_USER_EMAIL`. A 4-line comment immediately after that heredoc (added in #131 commit `07ab1085`) documents this. If a future PR widens the qa-agent block, flag it immediately as a cross-flow contract violation — the fix is to revert that hunk only; the profile-manager-v2 block correctly holds the two-value list.

## Firestore profile schema: grade field type ambiguity (2026-05-23)

`profile_extraction.py` LLM schema emits `grade` as `integer 9-12`. `GuidedInterview` writes it as a string. Any frontend code that reads `profile.grade` and calls string methods on it must coerce via `String(profile.grade ?? '').trim()`, not `(profile.grade || '').trim()`. The `|| ''` guard only catches falsy values; truthy integers (12) bypass it. Follow-up #130 tracks producer-side normalization + Firestore data fix. Until #130 merges, treat `profile.grade` as `string | number | null | undefined` on the consumer side.

Also: the Designer gate (SDLC.md §5) applies to UI/UX visual changes, not to every `.jsx` file. A pure data-coercion bug fix in a `load()` function body with no JSX markup change does not require Designer approval.

## Playwright console-error filters: scope 500 filters narrowly, always add issue link (#138, 2026-05-23)

When `cross-cutting.auth.spec.js` filters console errors, patterns like `text.includes('failed to load resource') && text.includes('500')` suppress ALL 500s, not just the specific endpoint under investigation. A future 500 from a different backend endpoint would be silently swallowed.

**Rule:** Every broad status-code filter (`'500'`, `'404'`) must be paired with a URL substring check specific to the known offender, plus an inline `// TODO: remove once #NNN is fixed` comment. Example:

```js
// Welcome-email 500 — backend fails when no profile doc exists. Filed as bug #136.
// TODO: remove once #136 is fixed.
if (text.includes('welcome-email') && text.includes('500')) return false;
```

When reviewing future console-filter additions, reject any pattern that is broader than a single URL path unless the author has explicitly argued the broadness is intentional.

## Playwright scenario-doc "update in same commit" rule — roadmap_plan_tab_renders missed (#138)

When a test is unskipped, the corresponding `tests/fixtures/scenarios/<name>.md` must be updated in the same commit to remove any `## Status: BLOCKED` / `SKIPPED` heading and bump the iteration number. PR #138 correctly updated `discover_university_detail_six_tabs.md` but missed `roadmap_plan_tab_renders.md` which still carries `## Status: BLOCKED — pending issue #123` and `Iteration: 3`.

**Checklist for unskip PRs:**
1. `test.skip(...)` line fully removed (not commented) — YES.
2. Corresponding scenario doc status updated — check explicitly. QA must fix `roadmap_plan_tab_renders.md` in next iteration.

## cloudbuild-main.yaml is the auto-deploy source of truth (#135, 2026-05-23)

`cloudbuild.yaml` is the PR-only test pipeline — no deploy steps. `cloudbuild-main.yaml` is the push-to-main pipeline that runs the same test gate then adds path-based auto-deploy via `scripts/cicd/detect_changed_targets.py`. Both backend Cloud Functions and frontend (Firebase Hosting) are auto-deployed when their path prefixes change. Docs/tests/config-only merges emit an empty target list — no deploy fires. When reviewing PRs that amend CI/CD docs, always verify against both files, not just the one `cloudbuild.yaml` that appears first in the root listing.
