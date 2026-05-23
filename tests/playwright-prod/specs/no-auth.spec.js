// No-auth specs for the autonomous QA loop.
//
// These scenarios don't require an authenticated session and can run unattended
// against production. They cover the public surface (landing, resources) and
// the unauthenticated-redirect path for protected routes.
//
// Scenario docs: tests/fixtures/scenarios/*.md (same root name as the test name).

import { test, expect } from '@playwright/test';

test.describe('pre_flight_landing_renders', () => {
  // tests/fixtures/scenarios/pre_flight_landing_renders.md
  test('landing page returns 200 and renders hero', async ({ page }) => {
    const response = await page.goto('/');
    expect(response).not.toBeNull();
    expect(response.status()).toBe(200);

    await expect(page).toHaveTitle(/Stratia Admissions/);
    await expect(page.getByRole('heading', { level: 1, name: /One platform/i })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Get Stratia free' })).toBeVisible();

    // Footer present (sanity: full document rendered, not white screen)
    await expect(page.getByText(/© 20\d{2} Stratia Admissions/)).toBeVisible();
  });
});

test.describe('unauthenticated_profile_redirect', () => {
  // tests/fixtures/scenarios/unauthenticated_profile_redirect.md
  test('navigating to /profile without auth redirects to landing', async ({ page }) => {
    await page.goto('/profile');

    // Expect the SPA to bounce us back to landing (not a 5xx, not a blank screen).
    await expect(page).toHaveURL(/^https?:\/\/[^/]+\/$/);
    await expect(page.getByRole('button', { name: 'Get Stratia free' })).toBeVisible();
  });
});

test.describe('public_resources_page_renders', () => {
  // tests/fixtures/scenarios/public_resources_page_renders.md
  test('/resources renders with whitepapers + public-only nav', async ({ page }) => {
    await page.goto('/resources');

    await expect(page).toHaveTitle(/Resources/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/Why and how Stratia works/i);

    // Public-only nav: Resources + Pricing + Get Started. NO Profile/Discover/Launchpad/Roadmap.
    await expect(page.getByRole('link', { name: 'Resources' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Pricing' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Get Started' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Profile' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Discover' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Launchpad' })).toHaveCount(0);
    await expect(page.getByRole('link', { name: 'Roadmap' })).toHaveCount(0);

    // At least one whitepaper card present
    await expect(page.getByText(/Hidden Cost of College Research/i)).toBeVisible();
  });

  test('whitepaper deep-link loads with route-specific title', async ({ page }) => {
    await page.goto('/resources/hidden-cost-of-research');
    await expect(page).toHaveTitle(/The Hidden Cost of College Research/);
  });
});
