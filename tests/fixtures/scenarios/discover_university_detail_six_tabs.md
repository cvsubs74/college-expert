# Scenario: discover_university_detail_six_tabs

## Objective

Verify that clicking the "Explore" button on any university card successfully
navigates to the university detail page and renders content without a crash or
error boundary.

## CORRECTION — iteration 4 finding (2026-05-23)

The test plan §5.5 originally described a 6-tab dialog/modal. **Production does NOT
use a dialog/modal.** Clicking "Explore" navigates to a full-page detail route
(e.g., `/universities/<university-id>`). The page uses a scroll-based layout with
section headings (About, Campus Life, Academics, Admissions, Financials, Outcomes)
— NOT tab navigation inside a modal. The dialog/tab assertions have been removed;
this scenario now verifies the detail page loads correctly.

Enhancement issue #134 tracks updating the test plan §5.5 to document the
scroll-based layout.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- At least one university card is visible in the Discover grid.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/universities`.
2. Wait for the grid to load (pagination footer visible).
3. Dismiss any onboarding/welcome overlay that may block pointer events
   (press Escape, then click Skip/Close if visible).
4. Click the first "Explore" button visible in the grid.
5. Wait for "Back to Universities" navigation link to be visible.
6. Assert the page has an `<h1>` university name heading.
7. Assert at least one content section heading is visible (About, Campus,
   Academics, Admissions, Financials, or Outcomes).
8. Assert "Something went wrong" is NOT visible (no React error boundary).

## Expected outcomes

- Browser navigates to `/universities/<id>` (full-page route, not a dialog).
- "Back to Universities" link visible.
- `<h1>` university name heading present.
- At least one section heading (About, Campus Life, Academics, Admissions,
  Financials, Outcomes) visible in the scroll layout.
- No React error boundary text ("Something went wrong") visible.

## Fixtures referenced

None. Any university card in the live grid will do.

## Known edge cases

- Profile-reset accounts may show an onboarding overlay on first visit. The spec
  dismisses this via Escape + Skip button before clicking Explore.
- The "Explore" button label was confirmed in the 2026-05-23 run. If renamed,
  update the spec locator.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §5.5
- Enhancement #134: update test plan §5.5 to reflect scroll-based detail layout
- Spec: `tests/playwright-prod/specs/discover.auth.spec.js` → `discover_university_detail_six_tabs`
- Iteration: 4
