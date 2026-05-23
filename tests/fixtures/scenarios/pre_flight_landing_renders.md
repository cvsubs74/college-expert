# Scenario: pre_flight_landing_renders

## Objective

Verify that the production landing page at `https://stratiaadmissions.com/` is reachable, returns HTTP 200, and renders the hero section without errors. This is the cheapest pre-flight signal that the deploy is healthy.

## Preconditions

- Public internet access from the runner
- `https://stratiaadmissions.com` is the canonical production URL
- No authentication required

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/`
2. Assert response status is `200`
3. Assert page title matches `/Stratia Admissions/`
4. Assert an H1 with text matching `/One platform/i` is visible
5. Assert the hero CTA button labeled "Get Stratia free" is visible
6. Assert a footer line matching `/© 20\d{2} Stratia Admissions/` is visible (sanity check that the full document rendered, not just a shell)

## Expected outcomes

- All assertions pass
- No browser console errors emitted during page load
- No network 4xx/5xx responses for any subresource

## Fixtures referenced

- None (this scenario does not consume any profile or document fixture)

## Known edge cases

- Marketing copy changes — the H1 wording or the CTA label may evolve. When that happens, update both this scenario doc AND the assertion in `tests/playwright-prod/specs/no-auth.spec.js` in the same commit.
- Footer year — uses a regex with `20\d{2}` to be year-agnostic.
- "Open App" CTA — appears in the navbar only when authenticated; logged-out callers see "Get Stratia free" / "Get started free" instead. The test plan's §4.1 originally claimed "Open App" was the logged-out CTA — this scenario reflects the actual logged-out reality (Finding F-1 from the 2026-05-23 browser run).

## Related

- Test plan reference: `docs/qa-browser-test-plan.md` §3 (Pre-flight) + §4.1 (Landing CTA)
- Spec implementation: `tests/playwright-prod/specs/no-auth.spec.js` (describe block `pre_flight_landing_renders`)
- Prior run finding: F-1 in `docs/qa-runs/2026-05-23-stratia-browser-run.md`
