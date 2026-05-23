# Scenario: discover_filter_dropdowns_present

## Objective

Verify that all four filter controls are present on the Discover page with the
expected option labels. This is a structural rendering check — not a functional
filter test.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- `/universities` grid has loaded (pagination footer visible).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/universities`.
2. Wait for pagination footer (`/\d+ universities/i`) to confirm the grid loaded.
3. Assert the following controls or label texts are visible inside `<main>`:
   a. **Type dropdown** — options "All Types", "Public", "Private"
   b. **Location dropdown** — a combobox for state selection (50 states + DC)
   c. **Fit Category** — label text "Fit Category" (or similar); options include
      "All", "Safety", "Target", "Reach", "Super Reach"
   d. **Sort By** — label text "Sort By" (or similar); options include "US News Rank",
      "Acceptance Rate", "Tuition", "Name"
4. Assert each option label text is visible (whether the dropdown is open or the
   option text is accessible in-page).

## Expected outcomes

- All four filter controls present and visible.
- "All Types", "Public", "Private" visible.
- "Super Reach" visible as a fit category option (in dropdown or filter region).
- "US News Rank" visible as a sort option.

## Fixtures referenced

None. Static rendering check.

## Known edge cases

- Some dropdowns may show only the selected option label until opened. If "All Types"
  is the default label, it is visible without interaction. If not, the test opens the
  dropdown to assert options — the spec falls back to asserting visible text in the
  filter panel.
- Prior run confirmed: Type (All Types/Public/Private), Location (50 states + DC),
  Max Acceptance Rate slider (not a dropdown), Fit Category (All/Safety/Target/Reach/
  Super Reach), Sort By (US News Rank/Acceptance Rate/Tuition/Name) were all present.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §5.3
- Finding F-11 (prior run): Launchpad UI shows only 4 category buttons (not 5). Discover
  page DOES include "Super Reach" as a Fit Category filter option — this is consistent.
- Spec: `tests/playwright-prod/specs/discover.auth.spec.js` → `discover_filter_dropdowns_present`
- Iteration: 3
