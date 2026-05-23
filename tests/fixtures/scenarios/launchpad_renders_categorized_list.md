# Scenario: launchpad_renders_categorized_list

## Objective

Verify that the Launchpad (`/launchpad`) page loads for an authenticated user,
displays a greeting, and renders exactly 4 category filter buttons: "All Schools",
"Reach", "Target", and "Safety". No "Super Reach" category button is present.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- The Launchpad route is accessible (`/launchpad`).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/launchpad`.
2. Assert the URL contains `/launchpad`.
3. Wait up to 10 seconds for the greeting to appear ("Good morning/afternoon/evening").
4. Assert each of the 4 expected category button labels is visible:
   - "All Schools"
   - "Reach"
   - "Target"
   - "Safety"
5. Assert that NO button or tab with the label "Super Reach" is present.

## Expected outcomes

- Greeting visible (format: "Good [morning|afternoon|evening], [display name]").
- All 4 category buttons visible.
- Count of category buttons: 4 (not 5).
- "Super Reach" not present as a UI category button (it exists as an internal
  fit bucket but is not exposed in the Launchpad filter bar).

## Fixtures referenced

None. Live production data.

## Known edge cases

- Finding F-11 from the 2026-05-23 run confirmed only 4 categories in the UI.
  The test plan originally claimed 5 (including "Super Reach") — this scenario
  deliberately documents the correct observed behavior.
- If the account has no saved schools, the category buttons may still render
  (with zero counts) or may be hidden. The assertion is on button presence, not
  count badges.
- StratiaLaunchpad.jsx lines 488-492 define the 4 filter labels authoritatively.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §7.1 + §7.2
- Finding F-11 (prior run): 4 UI categories, not 5
- Spec: `tests/playwright-prod/specs/launchpad.auth.spec.js` → `launchpad_renders_categorized_list`
- Iteration: 3
