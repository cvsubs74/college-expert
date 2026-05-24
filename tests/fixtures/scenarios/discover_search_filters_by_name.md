# Scenario: discover_search_filters_by_name

## Objective

Verify that typing "Stanford" into the Discover search box (after a debounce period)
narrows the university grid to exactly the Stanford result, and that the displayed
card title contains "Stanford".

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- The university knowledgebase contains "Leland Stanford Junior University" (confirmed
  in prior run 2026-05-23; classified as Super Reach for this account).
- `/universities` grid is visible before typing begins.

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/universities`.
2. Dismiss any onboarding overlay (modal with "Let's get started") if present — press
   Escape, then click "Skip for now" if visible. Required for fresh/reset accounts where
   the overlay appears on first authenticated visit and intercepts pointer events.
3. Wait for the **pagination footer** (`/Page 1 of \d+/i`) to confirm the grid is fully
   loaded. Do NOT rely on "Explore 150+ universities" in the hero paragraph — that text
   renders immediately before the grid and causes a false-ready condition.
4. Locate the search input inside `<main>` (placeholder `/university name/i`).
5. Fill the search input with the string `"Stanford"`.
6. Wait up to 8 s for at least one `h3` heading within `<main>` containing "Stanford"
   to become visible (handles debounce + re-render without a fixed sleep).
7. Assert the first matching heading's text content matches `/Stanford/i`.

## Expected outcomes

- After the search filter fires, the grid narrows to 1 or more results matching "Stanford".
- The first result heading contains "Stanford" (confirmed: "Leland Stanford Junior University").
- No error banner appears.

## Fixtures referenced

None. Live production data.

## Known edge cases

- If Stanford is removed from the knowledgebase, this test would fail. The knowledgebase
  is off-limits to QA modifications; a knowledgebase regression would be a separate bug.
- The onboarding overlay (step 2) appears on accounts with no profile document. The
  dismissal block handles both: Escape + "Skip for now" click.
- **Root cause of iteration-5 failure** (2026-05-24): the old spec used `getByText(/\d+
  universities/i)` as the grid-ready signal, which matched the "150+ universities" hero
  paragraph immediately — causing the search to run before the grid loaded. Fixed by
  waiting for the pagination footer instead.
- Prior confirmed result: "Leland Stanford Junior University (Stanford, CA, Private,
  3.6% accept, #4 US News, Super Reach)".

## Related

- Test plan: `docs/qa-browser-test-plan.md` §5.2
- Spec: `tests/playwright-prod/specs/discover.auth.spec.js` → `discover_search_filters_by_name`
- Iteration: 5 (spec fix: overlay dismissal + correct grid-ready signal)
