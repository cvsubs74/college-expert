// launchpad.auth.spec.js — Auth-gated spec covering Section 7 (Launchpad) scenarios.
//
// Requires auth-state/storageState.json — run capture-auth.spec.js first if missing.
// See tests/playwright-prod/README.md for full setup instructions.
//
// Scenario docs:
//   tests/fixtures/scenarios/launchpad_renders_categorized_list.md
//   tests/fixtures/scenarios/launchpad_fit_modal_opens_with_bounds.md

import { test, expect } from '@playwright/test';
import {
  assertAuthStateValid,
  loadFirebaseIndexedDB,
  restoreFirebaseIndexedDB,
} from '../lib/auth.js';

// Fit factor bounds from cloud_functions/qa_agent/fit_assertions.py lines 43-49.
// These are the ground truth — do not change without also updating fit_assertions.py.
const FIT_BOUNDS = {
  academic: { min: 0, max: 40 },
  holistic: { min: 0, max: 30 },
  majorFit: { min: 0, max: 15 },
  selectivity: { min: -15, max: 5 },
};

// Match % ranges by category. From fit_assertions.py lines 35-40 (_CATEGORY_MATCH_RANGES).
const MATCH_PCT_RANGES = {
  SAFETY: { min: 75, max: 100 },
  TARGET: { min: 55, max: 74 },
  REACH: { min: 35, max: 54 },
  SUPER_REACH: { min: 0, max: 34 },
};

let firebaseEntries = [];

test.beforeAll(() => {
  assertAuthStateValid();
  firebaseEntries = loadFirebaseIndexedDB();
});

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await restoreFirebaseIndexedDB(page, firebaseEntries);
});

// ---------------------------------------------------------------------------
// §7.1 + §7.2 — Launchpad renders categorized list
// ---------------------------------------------------------------------------

test.describe('launchpad_renders_categorized_list', () => {
  // tests/fixtures/scenarios/launchpad_renders_categorized_list.md
  // Test plan: §7.1 + §7.2
  //
  // NOTE (Finding F-11): The UI shows only 4 category buttons (All Schools / Reach /
  // Target / Safety), NOT 5. Despite "Super Reach" existing as an internal fit bucket,
  // the Launchpad category bar does not expose it as a separate UI button. This is
  // per StratiaLaunchpad.jsx lines 488-492 which define exactly 4 filter labels.
  test('navigates to /launchpad, shows greeting, shows exactly 4 category buttons', async ({
    page,
  }) => {
    await page.goto('/launchpad');
    await expect(page).toHaveURL(/\/launchpad/);

    // Wait for the page to render (greeting visible).
    // Prior run: "Good afternoon, Stratia." — uses account display name.
    await expect(
      page.getByText(/good (morning|afternoon|evening)/i),
    ).toBeVisible({ timeout: 10_000 });

    // The 4 expected category button labels (from StratiaLaunchpad.jsx lines 488-492).
    const expectedCategories = ['All Schools', 'Reach', 'Target', 'Safety'];

    for (const label of expectedCategories) {
      await expect(
        page.getByRole('button', { name: label }).or(
          page.getByRole('tab', { name: label }),
        ),
      ).toBeVisible({ timeout: 5_000 });
    }

    // Assert there is NO 5th "Super Reach" category button.
    // This documents the confirmed production state per finding F-11.
    const superReachBtn = page
      .getByRole('button', { name: /super reach/i })
      .or(page.getByRole('tab', { name: /super reach/i }));
    await expect(superReachBtn).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// §7.3 — Fit Analysis Modal with factor bounds verification
// ---------------------------------------------------------------------------

test.describe('launchpad_fit_modal_opens_with_bounds', () => {
  // tests/fixtures/scenarios/launchpad_fit_modal_opens_with_bounds.md
  // Test plan: §7.3
  //
  // The FitAnalysisModal is opened from a saved school card via the "Fit" or
  // "Explore" CTA. Factor scores are verified against documented bounds from
  // fit_assertions.py lines 43-49. Match % is verified against the category
  // band from fit_assertions.py lines 35-40.
  test('fit modal opens with factor scores and match% within documented bounds', async ({
    page,
  }) => {
    await page.goto('/launchpad');
    await expect(page).toHaveURL(/\/launchpad/);

    // Wait for the page to render.
    await expect(
      page.getByText(/good (morning|afternoon|evening)/i),
    ).toBeVisible({ timeout: 10_000 });

    // Skip gracefully if the account has no saved schools.
    // A missing school list means FitAnalysisModal cannot be opened.
    const schoolCards = page.locator(
      '[data-testid*="school-card"], [class*="school-card"], [class*="SchoolCard"], [class*="college-card"]',
    );
    const cardCount = await schoolCards.count();
    if (cardCount === 0) {
      // Also check for the SmartDiscoveryAlert which renders when list is empty.
      const alert = page.getByText(/add schools/i).or(page.getByText(/discover schools/i));
      const alertVisible = await alert.isVisible().catch(() => false);
      if (alertVisible || cardCount === 0) {
        test.skip(
          true,
          'Account has no saved schools — cannot open FitAnalysisModal. ' +
            'Add schools via Discover first, then re-run.',
        );
        return;
      }
    }

    // Trigger the Fit modal: click the fit/explore button on the first school card.
    // The CTA may be labeled "Analyze Fit", "Fit", "Explore", or show the fit score.
    const fitCta = page
      .getByRole('button', { name: /analyze fit/i })
      .or(page.getByRole('button', { name: /fit/i }))
      .or(page.getByRole('button', { name: /explore/i }))
      .first();

    await fitCta.waitFor({ state: 'visible', timeout: 10_000 });
    await fitCta.click();

    // Wait for the FitAnalysisModal to open.
    const modal = page
      .getByRole('dialog')
      .or(page.locator('[class*="FitAnalysis"], [class*="fit-analysis"], [data-testid="fit-modal"]'));
    await modal.waitFor({ state: 'visible', timeout: 15_000 });

    // --- Academic factor (0–40) ---
    await assertFactorInBounds(modal, /academic/i, FIT_BOUNDS.academic.min, FIT_BOUNDS.academic.max, 'Academic');

    // --- Holistic factor (0–30) ---
    await assertFactorInBounds(modal, /holistic/i, FIT_BOUNDS.holistic.min, FIT_BOUNDS.holistic.max, 'Holistic');

    // --- Major Fit factor (0–15) ---
    await assertFactorInBounds(modal, /major fit/i, FIT_BOUNDS.majorFit.min, FIT_BOUNDS.majorFit.max, 'Major Fit');

    // --- Selectivity factor (-15 to +5) ---
    await assertFactorInBounds(modal, /selectivity/i, FIT_BOUNDS.selectivity.min, FIT_BOUNDS.selectivity.max, 'Selectivity');

    // --- Match % within category band ---
    // Find the match percentage value in the modal.
    const matchPctLocator = modal.getByText(/\d+%/).first();
    await expect(matchPctLocator).toBeVisible({ timeout: 5_000 });
    const matchRaw = await matchPctLocator.textContent();
    const matchPct = parseFloat(matchRaw?.replace('%', '') ?? 'NaN');
    expect(isNaN(matchPct), `Could not parse match% from: "${matchRaw}"`).toBe(false);
    expect(matchPct).toBeGreaterThanOrEqual(0);
    expect(matchPct).toBeLessThanOrEqual(100);

    // Determine category label from the modal and verify match% falls in its range.
    // The category is displayed as SAFETY / TARGET / REACH / SUPER_REACH or a
    // lower-case variant (Safety / Target / Reach / Super Reach).
    const possibleCategories = Object.keys(MATCH_PCT_RANGES);
    let foundCategory = null;
    for (const cat of possibleCategories) {
      // Match case-insensitively against both UPPER_CASE and Title Case variants.
      const normalized = cat.replace('_', ' ');
      const catText = modal.getByText(new RegExp(normalized, 'i'));
      if (await catText.count() > 0) {
        foundCategory = cat;
        break;
      }
    }

    if (foundCategory !== null) {
      const range = MATCH_PCT_RANGES[foundCategory];
      expect(
        matchPct,
        `Match% ${matchPct} out of bounds for category ${foundCategory} (expected ${range.min}–${range.max})`,
      ).toBeGreaterThanOrEqual(range.min);
      expect(matchPct).toBeLessThanOrEqual(range.max);
    }
    // If category label not found, we still validated match% is in [0, 100] above.
  });
});

// ---------------------------------------------------------------------------
// Helper: parse a numeric factor score from the modal and assert bounds.
// ---------------------------------------------------------------------------

/**
 * Locate the score associated with a factor label within `parent`, parse it
 * as a float, and assert it falls in [min, max].
 *
 * @param {import('@playwright/test').Locator} parent - The modal locator.
 * @param {RegExp} labelPattern - Regex matching the factor label (e.g., /academic/i).
 * @param {number} min - Minimum expected value (inclusive).
 * @param {number} max - Maximum expected value (inclusive).
 * @param {string} factorName - Human-readable factor name for assertion messages.
 */
async function assertFactorInBounds(parent, labelPattern, min, max, factorName) {
  // Locate the label element, then find a nearby number.
  // The score may be rendered as text adjacent to or inside the label's parent.
  const labelEl = parent.getByText(labelPattern).first();
  await expect(labelEl).toBeVisible({ timeout: 5_000 });

  // Walk up to the containing row/block, then grab the numeric text within it.
  // Strategy: textContent of the label's parent, then regex-extract the number.
  const row = labelEl.locator('..');
  const rowText = await row.textContent();

  // Extract the first number (including negative numbers) from the row text.
  const numMatch = rowText?.match(/-?\d+(\.\d+)?/);
  if (!numMatch) {
    // Fallback: look for a sibling element with numeric text.
    const siblingText = await parent
      .getByText(labelPattern)
      .locator('..')
      .locator('..')
      .textContent();
    const fallbackMatch = siblingText?.match(/-?\d+(\.\d+)?/);
    if (!fallbackMatch) {
      throw new Error(
        `Could not extract ${factorName} score from modal. Row text: "${rowText}"`,
      );
    }
    const value = parseFloat(fallbackMatch[0]);
    expect(
      value,
      `${factorName} score ${value} out of bounds (expected ${min}..${max})`,
    ).toBeGreaterThanOrEqual(min);
    expect(value).toBeLessThanOrEqual(max);
    return;
  }

  const value = parseFloat(numMatch[0]);
  expect(
    value,
    `${factorName} score ${value} out of bounds (expected ${min}..${max})`,
  ).toBeGreaterThanOrEqual(min);
  expect(value).toBeLessThanOrEqual(max);
}
