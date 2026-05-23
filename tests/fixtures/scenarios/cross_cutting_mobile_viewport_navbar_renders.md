# Scenario: cross_cutting_mobile_viewport_navbar_renders

## Objective

Verify that on an iPhone 14 viewport (390×844 pixels), the navigation bar renders
in some accessible form (hamburger menu or horizontal nav links) and the Profile
route is reachable without horizontal overflow on the page body.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- Viewport is set to 390×844 before navigation.
- Non-blocking per §11.3 of the test plan. Failures here are filed as
  `enhancement,backlog` for PM/Designer — not treated as release blockers.

## Step-by-step actions

1. Set viewport to `{ width: 390, height: 844 }` (iPhone 14 dimensions).
2. Navigate to `https://stratiaadmissions.com/profile`.
3. Assert URL contains `/profile` (page did not redirect away).
4. Check for a hamburger/menu button OR a nav-role element with a Profile link.
5. If neither is immediately visible, look for a nav toggle button and open it.
6. Assert the page remains on `/profile` (not redirected away, no crash).
7. Assert no horizontal overflow: `body.scrollWidth <= body.clientWidth + 5px`.

## Expected outcomes

- Profile route accessible on mobile viewport.
- Navbar present in some form (hamburger or horizontal).
- No horizontal scroll on the `<body>` element.
- No crash or redirect to landing.

## Fixtures referenced

None.

## Known edge cases

- Both hamburger nav and horizontal scrollable nav are acceptable. The test
  does not mandate a specific mobile nav pattern.
- `+5px` tolerance on the overflow assertion accommodates sub-pixel rounding
  in browser layout engines.
- This is a smoke check, not a full mobile regression suite. File any specific
  mobile layout issues as `enhancement,backlog` for Designer.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §11.3
- Spec: `tests/playwright-prod/specs/cross-cutting.auth.spec.js` → `cross_cutting_mobile_viewport_navbar_renders`
- Iteration: 3

## TODO (not in scope for iteration 3)

- A11y deep-dive (axe DevTools on /universities and /profile): Designer Agent's lane (§11.4).
  File as `enhancement,backlog` when ready to schedule.
