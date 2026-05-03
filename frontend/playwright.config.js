// Playwright config for the frontend E2E suite.
//
// Strategy: build the app with `npm run build`, serve it with `vite preview`,
// run Playwright against the previewed URL with all backend HTTP intercepted
// via `page.route` so the test is fully deterministic and doesn't need any
// real Cloud Function deployment.
import { defineConfig, devices } from '@playwright/test';

const port = 4173;                                    // vite preview default

export default defineConfig({
    testDir: './tests-e2e',
    timeout: 30_000,
    expect: { timeout: 5_000 },
    fullyParallel: true,
    // CI hates flaky retries; one retry covers transient infra hiccups
    // without masking real bugs.
    retries: process.env.CI ? 1 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? [['list'], ['github']] : 'list',
    use: {
        baseURL: `http://localhost:${port}`,
        trace: 'on-first-retry',
        // headless on CI; configurable locally for debugging.
        headless: true,
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],
    // Boots `vite preview` automatically before the suite runs, tears it
    // down after. Skipped if a server is already listening on the port.
    //
    // `--mode test` is critical: it sets import.meta.env.MODE='test', which
    // unlocks the AuthContext E2E bypass. A production-mode build would
    // statically eliminate the bypass branch, leaving Firebase auth as the
    // only sign-in path — and Firebase doesn't run in Playwright without a
    // live identity, so the test would hang on a redirect to the landing.
    webServer: {
        command: `npx vite build --mode test && npx vite preview --port ${port} --strictPort`,
        url: `http://localhost:${port}`,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
    },
});
