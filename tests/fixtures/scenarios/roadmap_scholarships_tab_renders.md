# Scenario: roadmap_scholarships_tab_renders

## Objective

Verify that the Roadmap Scholarships tab becomes active and renders content
(the ScholarshipTracker component embedded) without a JS error or Connection Error card.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- The Scholarships tab is accessible from `/roadmap?tab=scholarships`.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/roadmap?tab=scholarships`.
2. Assert URL contains `/roadmap`.
3. Wait up to 10 seconds for the Scholarships tab button to appear.
4. Assert the Scholarships tab button is visible.
5. Assert the main content area renders.
6. Assert no "Connection Error" text is visible.
7. Assert URL contains `tab=scholarships`.

## Expected outcomes

- Scholarships tab button visible and active.
- Main content renders without error.
- URL: `?tab=scholarships`.

## Fixtures referenced

None. Live production data.

## Known edge cases

- If the account has no scholarship tracker entries, an empty state renders —
  acceptable as long as there is no error boundary.
- Per RoadmapPage.jsx line 112: ScholarshipTracker is rendered in embedded mode.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.4
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_scholarships_tab_renders`
- Iteration: 3
