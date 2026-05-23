// pricing.no-auth.spec.js — No-auth spec covering Section 9.1 (Pricing page).
//
// The pricing page is publicly accessible without authentication.
// No auth storageState required.
//
// This spec is added to the 'no-auth' project in playwright.config.js.
//
// Scenario docs:
//   tests/fixtures/scenarios/pricing_page_renders_four_tiers.md

import { test, expect } from '@playwright/test';

test.describe('pricing_page_renders_four_tiers', () => {
  // tests/fixtures/scenarios/pricing_page_renders_four_tiers.md
  // Test plan: §9.1
  //
  // Prior run (2026-05-23) observed 4 tier cards:
  //   1. Free (disabled "Active Plan" button)
  //   2. Monthly ("Start Monthly")
  //   3. Season Pass ("BEST VALUE" badge, "Get Season Pass")
  //   4. Top tier ("Requires Subscription", disabled)
  //
  // Finding F-5: The Free tier card shows "Active Plan" (disabled) even to
  // unauthenticated visitors, implying enrollment without sign-up. This is a
  // UX finding; the test ASSERTS the behavior (documents production state),
  // not fixes it.
  test('pricing page renders 4 tier cards, Free shows Active Plan, explainer sections visible', async ({
    page,
  }) => {
    await page.goto('/pricing');

    // Assert the pricing page renders.
    await expect(page).toHaveURL(/\/pricing/);

    // Wait for the pricing content to render.
    // Look for the "How Credits Work" section which is below the fold.
    await page.waitForLoadState('domcontentloaded');

    // Assert 4 tier cards are visible.
    // Tier cards are likely rendered as article or section elements, or elements
    // with data-testid / class containing "tier" or "plan".
    // Fallback: count distinct CTA buttons (one per card) and assert >= 4.
    //
    // Strategy: collect elements containing tier names from prior run.
    // "Free" tier — the disabled "Active Plan" button uniquely identifies this card.
    await expect(
      page.getByRole('button', { name: /active plan/i })
        .or(page.getByText(/active plan/i)),
    ).toBeVisible({ timeout: 10_000 });

    // "Monthly" tier card.
    await expect(
      page.getByRole('button', { name: /start monthly/i })
        .or(page.getByText(/start monthly/i)),
    ).toBeVisible({ timeout: 5_000 });

    // "Season Pass" card (BEST VALUE badge).
    // Use .first() to avoid strict-mode violation — the page contains multiple
    // nodes matching /season pass/i or /best value/i (heading, badge, button).
    await expect(
      page.getByText(/season pass/i).or(page.getByText(/best value/i)).first(),
    ).toBeVisible({ timeout: 5_000 });

    // Fourth tier card (varies — "Requires Subscription" or a higher tier).
    // Assert at least 4 tier cards exist by counting CTA buttons or tier containers.
    // Conservative approach: assert the total number of non-text interactive elements
    // is >= 4 (one per tier).
    const tierCtaButtons = page.getByRole('button').filter({
      hasText: /active plan|start monthly|season pass|subscribe|upgrade|get started|requires subscription/i,
    });
    const ctaCount = await tierCtaButtons.count();
    expect(
      ctaCount,
      `Expected at least 4 tier CTA buttons, found ${ctaCount}`,
    ).toBeGreaterThanOrEqual(4);

    // Finding F-5: "Active Plan" button on Free tier is visible to logged-out users.
    // This is the documented production behavior; asserting it makes regressions detectable.
    // If the button is removed or changed to "Sign Up Free", this assertion will catch it.
    await expect(
      page.getByRole('button', { name: /active plan/i }).first(),
    ).toBeVisible({ timeout: 5_000 });

    // "How Credits Work" section.
    await expect(page.getByText(/how credits work/i)).toBeVisible({ timeout: 5_000 });

    // "Common Questions" FAQ section (prior run: 4 FAQ entries present).
    await expect(page.getByText(/common questions/i)).toBeVisible({ timeout: 5_000 });
  });
});
