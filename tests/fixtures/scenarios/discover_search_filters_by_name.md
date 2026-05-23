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
2. Wait for pagination footer (`/\d+ universities/i`) to confirm grid has loaded.
3. Locate the search input inside `<main>` (role `searchbox` or placeholder matching
   `/search/i`).
4. Fill the search input with the string `"Stanford"`.
5. Wait 1,200 ms for the debounce to fire (debounce is ~300 ms; 1,200 ms provides
   comfortable headroom).
6. Assert at least one heading within `<main>` contains the text "Stanford".
7. Assert the first matching heading's text content matches `/Stanford/i`.

## Expected outcomes

- After debounce, the grid narrows to 1 or more results matching "Stanford".
- The first result heading contains "Stanford".
- No error banner appears.

## Fixtures referenced

None. Live production data.

## Known edge cases

- If Stanford is removed from the knowledgebase, this test would fail. The knowledgebase
  is off-limits to QA modifications; a knowledgebase regression would be a separate bug.
- Debounce timing may vary; 1,200 ms is conservative. If the app changes debounce to
  > 1,200 ms, the wait must be updated.
- Prior run (2026-05-23) confirmed single result: "Leland Stanford Junior University
  (Stanford, CA, Private, 3.6% accept, #4 US News, Super Reach)".

## Related

- Test plan: `docs/qa-browser-test-plan.md` §5.2
- Spec: `tests/playwright-prod/specs/discover.auth.spec.js` → `discover_search_filters_by_name`
- Iteration: 3
