# Scenario: roadmap_plan_tab_renders

## Objective

Verify that the Roadmap Plan tab renders the PlanTab component with semester boards
(or a "Generate Plan" CTA if no plan exists) and a "This Week" focus card, with no
"Connection Error" card visible and no JavaScript errors in the browser console.

## Status: BLOCKED — pending issue #123

This scenario is skipped (`test.skip()`) in `roadmap.auth.spec.js` until issue #123
is fixed and deployed. The Roadmap Plan tab currently throws a reproducible JavaScript
error and renders a "Connection Error" card instead of the expected content.

**Error from prior run (2026-05-23):**
```
(((intermediate value)(intermediate value)(intermediate value) || {}).grade || "").trim is not a function
```

**Observed:** The "This Week" section shows "Nothing urgent right now." followed by
a Connection Error card exposing the JS error message to users.

## Preconditions (when unblocked)

- Issue #123 is fixed and deployed to production.
- User is authenticated as `stratiaadmissions@gmail.com`.
- Account may or may not have a generated roadmap plan.

## Step-by-step actions (when unblocked)

1. Navigate to `https://stratiaadmissions.com/roadmap` (defaults to `?tab=plan`).
2. Assert URL contains `/roadmap`.
3. Assert the Plan tab button is selected/active.
4. Assert NO "Connection Error" card is visible.
5. Assert the "This Week" focus card is visible.
6. Assert either:
   - Semester boards or task lists are visible (if a plan has been generated), OR
   - A "Generate Plan" CTA is visible (if no plan has been generated).
7. Assert no JavaScript error matching the pattern `trim is not a function` appears
   in the browser console.

## Expected outcomes

- Plan tab content renders without a Connection Error card.
- "This Week" heading or card visible.
- Semester boards OR "Generate Plan" CTA visible.
- No JS error in the browser console related to `.trim is not a function`.

## Fixtures referenced

None.

## Known edge cases

- The JS error (`trim is not a function`) is caused by a non-string `grade` field in
  the profile data. This may be account-specific. Verify on a freshly-reset account
  after the fix is deployed.
- If the account has no roadmap plan, the empty-state CTA is acceptable. Do not
  require semester boards unconditionally.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.1
- Issue #123: [BUG] Roadmap Plan tab JS error — "trim is not a function"
- Prior run finding: F-12 (BUG — Roadmap Plan tab JS error, high severity)
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_plan_tab_renders` (skipped)
- Iteration: 3 (scaffolded; unblock when #123 is fixed)
