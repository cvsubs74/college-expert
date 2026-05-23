# Scenario: discover_page_loads_with_university_grid

## Objective

Verify that the Discover (`/universities`) page loads for an authenticated user,
renders a grid containing at least one Super Reach university card, and displays
a pagination footer indicating the total university count as a positive integer.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com` (auth storageState loaded).
- Account has a profile that produces at least one Super Reach classification (the
  prior-run account — Aditi Subramanian, SAT 1420 — meets this condition with the
  existing saved schools).
- Production database contains > 0 universities (currently 191 as of the 2026-05-23 run).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/universities`.
2. Assert the URL contains `/universities`.
3. Wait up to 10 seconds for the grid to render.
4. Assert that the text "Super Reach" is visible somewhere in the main content area
   (at least one card classified as Super Reach).
5. Assert that the pagination footer matches the pattern `/\d+\s+universities/i`
   (e.g., "191 universities").
6. Parse the integer from that text; assert it is > 0.

## Expected outcomes

- URL: `https://stratiaadmissions.com/universities`
- At least one "Super Reach" label visible in the grid.
- Pagination footer visible with a positive university count.
- The count is not hardcoded in the assertion — the regex captures whatever the
  production database currently reports.

## Fixtures referenced

None. Live production data.

## Known edge cases

- If the account profile is empty, fit-category labels may not appear — the
  assertion covers "Super Reach" text anywhere in the grid, which is also present
  in filter dropdown options (fallback safety net).
- The count may change if universities are added/removed from the knowledgebase.
  The assertion only requires a positive integer, not a specific value.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §5.1
- Finding F-10 (prior run): plan claimed "1,600+ schools"; actual count is 191.
  This spec does NOT hardcode 191; it captures the live count dynamically.
- Spec: `tests/playwright-prod/specs/discover.auth.spec.js` → `discover_page_loads_with_university_grid`
- Iteration: 3
