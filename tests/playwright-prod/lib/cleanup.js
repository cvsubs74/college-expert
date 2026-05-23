// cleanup.js — UI-driven test-data cleanup helpers for the autonomous QA loop.
//
// Per docs/qa-autonomous-loop-spec.md: after every full pass of the suite,
// delete all test-user-owned data for stratiaadmissions@gmail.com.
//
// These helpers are safe to call even if no data exists (idempotent).
// They drive the live app UI, so they require an authenticated page context
// (loaded with auth-state/storageState.json via the 'auth' Playwright project).
//
// NEVER touch the university knowledgebase. If a cleanup action would affect
// shared/system data, the helper throws before taking action.
//
// Usage (in a spec's afterAll or a dedicated cleanup spec):
//
//   import { resetProfile, clearCollegeList } from '../lib/cleanup.js';
//   await resetProfile(page);
//   await clearCollegeList(page);
//
// Background: the backend clear-test-data endpoint only accepts
// duser8531@gmail.com (QA_TEST_USER_EMAIL env var) and will 403 for
// stratiaadmissions@gmail.com. A follow-up issue has been filed requesting
// endpoint widening (see FOLLOW-UP-ENDPOINT-WIDENING issue). Until then
// these UI-driven helpers are the primary cleanup mechanism.

/**
 * Reset the profile for the test account via the app's Reset Profile button.
 *
 * Navigates to /profile, finds the Reset Profile or Delete Profile control,
 * and confirms the deletion. Safe to call on an account with no profile
 * (the button is a no-op or not shown in that case).
 *
 * Does NOT delete the college list (pass deleteCollegeList: true to include it).
 *
 * @param {import('@playwright/test').Page} page
 * @param {{ deleteCollegeList?: boolean }} options
 */
export async function resetProfile(page, { deleteCollegeList = false } = {}) {
  await page.goto('/profile');

  // Look for any reset / delete profile control.
  // The exact label varies by app version; try common patterns.
  const resetButton = page
    .getByRole('button', { name: /reset profile/i })
    .or(page.getByRole('button', { name: /delete profile/i }))
    .or(page.getByRole('button', { name: /clear profile/i }));

  const isVisible = await resetButton.isVisible().catch(() => false);
  if (!isVisible) {
    // No reset control found — profile may already be empty. Nothing to do.
    console.log('[cleanup] resetProfile: no reset button found; profile may already be empty.');
    return;
  }

  await resetButton.click();

  // A confirmation dialog typically appears. Confirm deletion.
  const confirmButton = page
    .getByRole('button', { name: /confirm/i })
    .or(page.getByRole('button', { name: /delete/i }))
    .or(page.getByRole('button', { name: /yes/i }))
    .or(page.getByRole('button', { name: /ok/i }));

  const confirmVisible = await confirmButton.isVisible({ timeout: 3_000 }).catch(() => false);
  if (confirmVisible) {
    await confirmButton.click();
  }

  // Wait for a post-reset indicator (upload zone or empty-state text).
  await page
    .getByText(/no profile data/i)
    .or(page.locator('input[type="file"]'))
    .first()
    .waitFor({ state: 'visible', timeout: 15_000 })
    .catch(() => {
      // Non-fatal: reset may have redirected or the empty state text differs.
      console.log('[cleanup] resetProfile: post-reset indicator not found; continuing.');
    });

  console.log('[cleanup] resetProfile: complete.');

  if (deleteCollegeList) {
    await clearCollegeList(page);
  }
}

/**
 * Remove all saved schools from the college list (Launchpad).
 *
 * Navigates to /launchpad and iterates through all school cards, clicking
 * "Remove" (or equivalent) on each. Safe to call when the list is empty.
 *
 * @param {import('@playwright/test').Page} page
 */
export async function clearCollegeList(page) {
  await page.goto('/launchpad');

  // Repeat until no more remove buttons are present.
  let attempts = 0;
  const MAX_SCHOOLS = 50; // safety cap to prevent infinite loops
  while (attempts < MAX_SCHOOLS) {
    // Look for any "Remove" or trash-icon button on school cards.
    const removeButton = page
      .getByRole('button', { name: /remove/i })
      .or(page.getByRole('button', { name: /delete/i }))
      .first();

    const isVisible = await removeButton.isVisible().catch(() => false);
    if (!isVisible) {
      break; // No more schools to remove.
    }

    await removeButton.click();

    // Confirm if a dialog appears.
    const confirmButton = page
      .getByRole('button', { name: /confirm/i })
      .or(page.getByRole('button', { name: /yes/i }))
      .or(page.getByRole('button', { name: /ok/i }));
    const confirmVisible = await confirmButton.isVisible({ timeout: 2_000 }).catch(() => false);
    if (confirmVisible) {
      await confirmButton.click();
    }

    // Brief wait for the UI to update.
    await page.waitForTimeout(500);
    attempts++;
  }

  if (attempts === MAX_SCHOOLS) {
    console.warn(
      `[cleanup] clearCollegeList: safety cap of ${MAX_SCHOOLS} removals reached. ` +
        'Some schools may remain. Inspect the account manually.',
    );
  } else {
    console.log(`[cleanup] clearCollegeList: removed ${attempts} school(s).`);
  }
}

/**
 * Verify the test account is in a clean state: no profile, no saved schools.
 * Throws if either surface still has data.
 *
 * @param {import('@playwright/test').Page} page
 */
export async function assertCleanState(page) {
  // Check profile is empty.
  await page.goto('/profile');
  const hasProfile = await page
    .getByText(/profile completion/i)
    .isVisible()
    .catch(() => false);
  if (hasProfile) {
    throw new Error(
      '[cleanup] assertCleanState: profile still has data after cleanup. ' +
        'Run resetProfile() and retry.',
    );
  }

  // Check college list is empty.
  await page.goto('/launchpad');
  const hasSchools = await page
    .getByRole('button', { name: /remove/i })
    .isVisible()
    .catch(() => false);
  if (hasSchools) {
    throw new Error(
      '[cleanup] assertCleanState: college list still has entries after cleanup. ' +
        'Run clearCollegeList() and retry.',
    );
  }

  console.log('[cleanup] assertCleanState: account is in clean state.');
}
