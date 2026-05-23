# Scenario: roadmap_colleges_tab_renders

## Objective

Verify that the Roadmap Colleges tab becomes active and renders content
(the ApplicationsPage component embedded) without a JS error or Connection Error card.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- The Colleges tab is accessible from `/roadmap?tab=colleges`.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/roadmap?tab=colleges`.
2. Assert URL contains `/roadmap`.
3. Wait up to 10 seconds for the Colleges tab button to appear.
4. Assert the Colleges tab button is visible.
5. Assert the main content area renders.
6. Assert no "Connection Error" text is visible.
7. Assert URL contains `tab=colleges`.

## Expected outcomes

- Colleges tab button visible and active.
- Main content renders without error.
- URL: `?tab=colleges`.

## Fixtures referenced

None. Live production data.

## Known edge cases

- If the account has no saved schools, the ApplicationsPage may render an empty state
  — acceptable as long as no error boundary appears.
- ApplicationsPage is rendered in embedded mode per RoadmapPage.jsx.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.5
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_colleges_tab_renders`
- Iteration: 3
