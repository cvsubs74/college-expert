# Scenario: public_resources_page_renders

## Objective

Verify that the public Resources page at `/resources` renders without authentication, lists the published whitepapers, and shows the public-only navigation (Resources / Pricing / Get Started — without the authenticated app tabs). Also verify a whitepaper deep-link loads with a route-specific title.

## Preconditions

- Public internet access from the runner
- No authentication required
- The published whitepaper "The Hidden Cost of College Research" is live at `/resources/hidden-cost-of-research` (true as of 2026-05-23 — if rotated, update both this scenario and the spec)

## Step-by-step actions

### Part A — Resources index page

1. Navigate to `https://stratiaadmissions.com/resources`
2. Assert page title matches `/Resources/`
3. Assert H1 contains `/Why and how Stratia works/i`
4. Assert public nav links/buttons are visible: `Resources`, `Pricing`, `Get Started`
5. Assert authenticated-app nav links are NOT present: `Profile`, `Discover`, `Launchpad`, `Roadmap` (each should resolve to 0 matches)
6. Assert at least one whitepaper card is visible (`/Hidden Cost of College Research/i`)

### Part B — Whitepaper deep-link

7. Navigate to `https://stratiaadmissions.com/resources/hidden-cost-of-research`
8. Assert page title matches `/The Hidden Cost of College Research/`

## Expected outcomes

- All assertions pass
- No browser console errors
- No network 4xx/5xx

## Fixtures referenced

- None

## Known edge cases

- Whitepaper rotation — if a whitepaper is renamed or unpublished, the deep-link assertion will fail. When that happens, surface as a test-script update (not a bug) and pick a stable replacement.
- The `Get Started` button currently leads to the OAuth flow. The button label may evolve ("Get Stratia free" vs "Get Started" — same target, different copy in different contexts). This scenario uses the exact `Get Started` label observed in the navbar of `/resources`.

## Related

- Test plan reference: `docs/qa-browser-test-plan.md` §10
- Spec implementation: `tests/playwright-prod/specs/no-auth.spec.js` (describe block `public_resources_page_renders`)
- Prior run: PASS (the Resources page rendered correctly with 2 whitepapers and the deep-link worked)
