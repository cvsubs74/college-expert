// Playwright config for production-mode browser tests against stratiaadmissions.com.
// See README.md for setup. Auth-state for OAuth-gated specs lands in iteration 2.

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
      name: 'no-auth',
      testMatch: /no-auth\.spec\.js$/,
      use: { ...devices['Desktop Chrome'] },
    },
    // Iteration 2 will add an 'auth' project that loads auth-state/storageState.json.
  ],
});
