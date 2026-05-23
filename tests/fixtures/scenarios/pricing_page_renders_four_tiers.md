# Scenario: pricing_page_renders_four_tiers

## Objective

Verify that the Pricing page (`/pricing`) renders correctly for an unauthenticated
visitor: 4 tier cards visible, the Free tier shows an "Active Plan" button (a known
UX finding F-5 that persists in production), and both the "How Credits Work" and
"Common Questions" sections are present.

## Preconditions

- No authentication required (`/pricing` is a public route per App.jsx).
- The test runs with a fresh browser context (no OAuth session).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/pricing`.
2. Assert URL contains `/pricing`.
3. Wait for `domcontentloaded`.
4. Assert the "Active Plan" disabled button is visible (Free tier — documented
   production behavior per finding F-5).
5. Assert "Start Monthly" text or button is visible (Monthly tier).
6. Assert "Season Pass" or "Best Value" text is visible (Season Pass tier).
7. Count all tier CTA buttons matching
   `/active plan|start monthly|season pass|subscribe|upgrade|get started|requires subscription/i`.
   Assert count >= 4.
8. Assert "How Credits Work" section is visible.
9. Assert "Common Questions" section (FAQ) is visible.

## Expected outcomes

- 4 tier cards visible with distinct CTAs.
- Free tier shows "Active Plan" button (disabled) — F-5 documented production behavior.
- "How Credits Work" and "Common Questions" sections present.
- No crash or error boundary.

## Fixtures referenced

None. Public production page.

## Known edge cases

- Finding F-5: "Active Plan" on the Free tier for logged-out users. This assertion
  DOCUMENTS the current production behavior, not the ideal UX. If the Free tier is
  changed to show "Sign Up Free" for logged-out visitors, update this assertion.
- If a fifth tier card is added in a future release, the `>= 4` count assertion
  remains valid (will not falsely fail).
- The exact CTA labels on paid tiers may change if pricing is restructured. Update
  the regex pattern and scenario doc together when that happens.
- Prior run (2026-05-23): 4 tiers confirmed — Free (Active Plan), Monthly (Start
  Monthly), Season Pass (BEST VALUE badge, Get Season Pass), Top tier (Requires
  Subscription).

## Related

- Test plan: `docs/qa-browser-test-plan.md` §9.1
- Finding F-5 (prior run): "Active Plan" shown to logged-out users on Free tier
- Spec: `tests/playwright-prod/specs/pricing.no-auth.spec.js` → `pricing_page_renders_four_tiers`
- Project: `no-auth` (no auth required)
- Iteration: 3
