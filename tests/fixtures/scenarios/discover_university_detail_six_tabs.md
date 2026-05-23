# Scenario: discover_university_detail_six_tabs

## Objective

Verify that clicking the "Explore" button on any university card opens the
university detail modal and renders exactly 6 tabs in the documented order:
Overview, Academics, Admissions, Financials, Outcomes, Campus.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- At least one university card is visible in the Discover grid.
- The corrected tab order is: Overview | Academics | Admissions | Financials |
  Outcomes | Campus (NOT the earlier incorrect order that had Campus before Outcomes).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/universities`.
2. Wait for the grid to load (pagination footer visible).
3. Click the first "Explore" button visible in the grid.
4. Wait for the detail modal/dialog to appear (up to 10 seconds).
5. Assert the modal is visible (role `dialog`, or identifiable by class name containing
   "detail-modal" or "DetailModal").
6. Locate all tab elements inside the modal (role `tab`).
7. Assert exactly 6 tabs are present.
8. For each tab at index 0–5, assert the text content contains the expected label
   in order: Overview, Academics, Admissions, Financials, Outcomes, Campus.

## Expected outcomes

- Detail modal opens without a page crash or error boundary.
- Exactly 6 tabs present in the modal.
- Tab order: Overview (0), Academics (1), Admissions (2), Financials (3),
  Outcomes (4), Campus (5).
- No "Connection Error" card visible in the modal (that symptom belongs to the
  Roadmap Plan tab — issue #123).

## Fixtures referenced

None. Any university card in the live grid will do.

## Known edge cases

- If the Explore button is not labeled "Explore" (e.g., renamed to "View" or
  "Details"), the locator may need updating. Prior run (2026-05-23) confirmed
  the label is "Explore".
- The corrected tab order was documented in the 2026-05-23 run and in the test
  plan update for issue #115. The old incorrect order (Campus before Outcomes)
  must NOT be used.
- If the modal has additional tabs injected by a feature flag (e.g., a "Chat" tab
  or an "Apply" tab), the exact-count assertion will fail — investigate before
  adjusting the count.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §5.5
- Issue #115: corrected tab order (Outcomes before Campus)
- Spec: `tests/playwright-prod/specs/discover.auth.spec.js` → `discover_university_detail_six_tabs`
- Iteration: 3
