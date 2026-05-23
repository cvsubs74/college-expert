// capture-auth.spec.js — One-shot OAuth session capture for the autonomous QA loop.
//
// INTERACTIVE SPEC — must be run headed. The operator's role is to complete the
// 2-Factor Authentication (IPP push on their phone). If STRATIA_AUTOFILL_PASSWORD=1
// the spec fills the password field automatically from GCP Secret Manager; otherwise
// the operator must type both password AND approve 2FA.
//
// Run:
//   HEADED=1 npx playwright test --project=capture --headed
//
// Output:
//   tests/playwright-prod/auth-state/storageState.json (gitignored)
//
// After capture, run the auth-gated specs:
//   npx playwright test --project=auth
//
// Expiry: Firebase Auth sessions last ~30 days. Re-run this spec if the auth
// project fails with an "auth-state expired" error (guard in playwright.config.js).
//
// Scenario doc: tests/fixtures/scenarios/capture_oauth_storage_state.md

import { test, expect } from '@playwright/test';
import { getTestPassword } from '../lib/secret-manager.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_STATE_PATH = path.resolve(__dirname, '../auth-state/storageState.json');

// How long to wait for the operator to complete 2FA (in ms). Generous because
// the IPP push round-trip can take 1–3 minutes on a slow connection.
const TWO_FA_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

test.describe('capture_oauth_storage_state', () => {
  // tests/fixtures/scenarios/capture_oauth_storage_state.md
  test('capture authenticated session to auth-state/storageState.json', async ({
    page,
    context,
    browser,
  }) => {
    const autofill = process.env.STRATIA_AUTOFILL_PASSWORD === '1';

    // Navigate to the app landing page.
    await page.goto('/');
    await expect(page.getByRole('button', { name: 'Get Stratia free' })).toBeVisible();

    // Click the CTA to start the OAuth flow.
    await page.getByRole('button', { name: 'Get Stratia free' }).click();

    // Firebase Auth opens a popup. Wait for it.
    const [popup] = await Promise.all([
      page.waitForEvent('popup', { timeout: 15_000 }),
    ]);

    // Wait for the Google account chooser / sign-in page to load.
    await popup.waitForLoadState('domcontentloaded');

    // If not already on the account chooser, wait until we are.
    await popup.waitForURL(/accounts\.google\.com/, { timeout: 15_000 });

    // Pre-fill the email field (the account chooser may skip this if already signed in).
    const emailInput = popup.getByRole('textbox', { name: /email/i });
    const emailInputVisible = await emailInput.isVisible().catch(() => false);
    if (emailInputVisible) {
      await emailInput.fill('stratiaadmissions@gmail.com');
      await popup.getByRole('button', { name: /next/i }).click();
    }

    if (autofill) {
      // Autofill mode: fetch password from Secret Manager and fill it in.
      // NEVER log, print, or persist the password value.
      const password = await getTestPassword();
      const passwordInput = popup.getByRole('textbox', { name: /password/i });
      await passwordInput.waitFor({ state: 'visible', timeout: 15_000 });
      await passwordInput.fill(password);
      await popup.getByRole('button', { name: /next/i }).click();
      // Fall through — operator still handles 2FA push below.
      console.log(
        '\n[capture-auth] Password filled. Waiting for operator to approve 2FA push...',
      );
    } else {
      // Manual mode: pause for operator to type both password AND approve 2FA.
      console.log(
        '\n[capture-auth] Pausing for operator to complete password entry and 2FA push.',
        '\n  - Type the account password in the Chromium window.',
        '\n  - Approve the 2FA push on your phone.',
        '\n  - The spec will auto-continue once the app redirects to /universities.',
      );
    }

    // Wait for the main page tab to redirect to /universities — that is the
    // signal that OAuth completed and Firebase ID tokens are in localStorage.
    console.log('[capture-auth] Waiting for redirect to /universities ...');
    await page.waitForURL(/\/universities/, { timeout: TWO_FA_TIMEOUT_MS });

    // Assert: authenticated state reached.
    await expect(page).toHaveURL(/\/universities/);
    console.log('[capture-auth] OAuth succeeded. Saving storage state...');

    // Save the storage state (Firebase ID tokens, cookies) to the gitignored path.
    await context.storageState({ path: AUTH_STATE_PATH });
    console.log(`[capture-auth] Storage state saved to:\n  ${AUTH_STATE_PATH}`);
    console.log(
      '[capture-auth] IMPORTANT: this file expires in ~25 days. Re-run this spec before it expires.',
    );
  });
});
