# Scenario: roadmap_plan_tab_renders

## Objective

Verify that the Roadmap Plan tab renders the PlanTab component with semester boards
(or a "Generate Plan" CTA if no plan exists) and a "This Week" focus card, with no
"Connection Error" card visible and no JavaScript errors in the browser console.

## Status: PASSING

Scenario is live and asserting. The `test.skip()` guard was removed in PR #138
(iteration 4, 2026-05-23) after PR #132 (`grade.trim` fix) deployed to production
at commit `bba3c5b3` (2026-05-23T16:11:24Z).

**Fix deployed:** PR #132 resolved the `trim is not a function` JS crash by ensuring
`grade` is coerced to a string before `.trim()` is called. Issue #123 closed.

**Pass 1 verification (2026-05-23, iteration 4):**
- "THIS WEEK" heading visible; no "Connection Error" card; no error boundary.
- Pass 2 (§TWO-PASS) pending in a separate QA session before `resolved` is applied
  to issue #123.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- Account may or may not have a generated roadmap plan.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/roadmap` (defaults to `?tab=plan`).
2. Assert URL contains `/roadmap`.
3. Assert the Plan tab button is selected/active.
4. Assert NO "Connection Error" card is visible.
5. Assert the "THIS WEEK" heading is visible (rendered in loading skeleton even
   when no plan data has been generated yet).
6. Assert no React error boundary text ("Something went wrong") is visible.

## Expected outcomes

- Plan tab renders without a "Connection Error" card.
- "THIS WEEK" heading visible in the plan skeleton.
- No React error boundary text visible.

Note: Semester boards or a "Generate Plan" CTA may not be visible on accounts with
no profile/plan data — the skeleton shows "THIS WEEK" but no populated tasks. Do
NOT assert semester board content unconditionally.

## Fixtures referenced

None.

## Known edge cases

- Accounts with no profile data show the Plan skeleton with "THIS WEEK" but no
  semester boards or task rows. This is correct post-fix behavior.
- If account has an existing roadmap plan, semester boards may be visible. The
  assertion is intentionally loose to handle both states.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.1
- Issue #123: [BUG] Roadmap Plan tab JS error — "trim is not a function" (closed, fix verified)
- PR #132: grade.trim fix (deployed 2026-05-23 at bba3c5b3)
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_plan_tab_renders`
- Iteration: 4 (skip guard removed; test live)
