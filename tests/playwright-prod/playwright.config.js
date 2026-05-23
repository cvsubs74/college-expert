// Playwright config for production-mode browser tests against stratiaadmissions.com.
// See README.md for setup, credential handling, and auth-state capture instructions.
//
// Three projects:
//   no-auth  — specs/no-auth.spec.js         Public pages; runs unattended. No OAuth required.
//   capture  — specs/capture-auth.spec.js    One-shot interactive OAuth capture. Run HEADED.
//   auth     — specs/*.auth.spec.js          Auth-gated scenarios. Requires auth-state/storageState.json.

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  fullyParallel: false,
  // Production tests run sequentially against a single test account; no parallelism
  // across specs to avoid cross-contamination and rate-limit risk.
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    baseURL: 'https://stratiaadmissions.com',
    headless: process.env.HEADED ? false : true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      // no-auth: public pages + unauthenticated redirects. Runs unattended.
      name: 'no-auth',
      testMatch: /no-auth\.spec\.js$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      // capture: interactive one-shot spec that walks through Google OAuth and
      // saves the browser context's storageState to auth-state/storageState.json.
      // Must be run HEADED so the operator can approve the 2FA push on their phone.
      // Run: HEADED=1 npx playwright test --project=capture --headed
      name: 'capture',
      testMatch: /capture-auth\.spec\.js$/,
      use: {
        ...devices['Desktop Chrome'],
        headless: false, // Always headed — operator must interact for 2FA.
      },
    },
    {
      // auth: auth-gated scenarios. Loads the saved OAuth storageState so tests
      // run unattended (no interactive sign-in needed on each run).
      // Fails fast with a clear error if storageState is missing or older than
      // 25 days (Firebase Auth sessions last ~30 days; 25-day threshold leaves
      // headroom to rotate before silent auth failures occur).
      // Error message: "auth-state expired or missing — re-run capture-auth.spec.js
      // with --project=capture"
      name: 'auth',
      testMatch: /\.auth\.spec\.js$/,
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'auth-state/storageState.json',
      },
    },
  ],
});
