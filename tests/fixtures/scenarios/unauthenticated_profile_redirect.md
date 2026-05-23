# Scenario: unauthenticated_profile_redirect

## Objective

Verify that navigating to a protected route (`/profile`) without an authenticated session redirects the user cleanly to the landing page — never a 5xx, never a white screen, never an unhandled JavaScript error.

This is a negative-path scenario: it confirms the auth-gate works as a defense in depth, and protects the user experience from a poorly-handled 401.

## Preconditions

- Public internet access from the runner
- No authentication cookie / no captured `storageState.json`
- `https://stratiaadmissions.com` is the canonical production URL

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/profile`
2. Wait for the SPA's client-side router to make its auth decision
3. Assert the final URL is the landing page (`https://stratiaadmissions.com/`)
4. Assert the hero CTA "Get Stratia free" is visible (confirms landing rendered, not a partial state)

## Expected outcomes

- URL ends up at `/` (or any path that matches `/^https?:\/\/[^/]+\/$/`)
- Landing page chrome and hero render correctly
- No browser console errors during the redirect
- No network 4xx/5xx (other than possibly a 401 on a backend probe, which is acceptable — the SPA handles it gracefully)

## Fixtures referenced

- None

## Known edge cases

- If the SPA caches a stale auth token in `localStorage`, the redirect may not fire on first nav. The test runs in a fresh browser context per test, so cookies/localStorage are empty.
- The plan also called out an alternative route (login prompt instead of redirect). Either behavior is acceptable per the test plan; this scenario asserts the redirect-to-landing variant, which is the observed production behavior as of 2026-05-23.

## Related

- Test plan reference: `docs/qa-browser-test-plan.md` §4.6
- Spec implementation: `tests/playwright-prod/specs/no-auth.spec.js` (describe block `unauthenticated_profile_redirect`)
- Prior run: PASS (one of the 6 sub-sections that ran cleanly without auth in 2026-05-23 run)
