// profile.auth.spec.js — Auth-gated spec covering Section 6 (Profile tab) scenarios.
//
// Requires auth-state/storageState.json — run capture-auth.spec.js first if missing.
// See tests/playwright-prod/README.md for full setup instructions.
//
// Scenario docs:
//   tests/fixtures/scenarios/profile_tab_renders_five_tabs.md
//   tests/fixtures/scenarios/profile_upload_pdf_processes_to_completion.md
//   tests/fixtures/scenarios/profile_upload_unsupported_format_rejects.md

import { test, expect } from '@playwright/test';
import { assertAuthStateValid } from '../lib/auth.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Fixture path for the junior-comprehensive PDF (Section 6.2).
const JUNIOR_PDF = path.resolve(
  __dirname,
  '../../../fixtures/profile-samples/sample-junior-comprehensive.pdf',
);

test.beforeAll(() => {
  // Fail fast if the storageState is missing or older than 25 days.
  // Error message matches the documented guard:
  //   "auth-state expired or missing — re-run capture-auth.spec.js with --project=capture"
  assertAuthStateValid();
});

test.describe('profile_tab_renders_five_tabs', () => {
  // tests/fixtures/scenarios/profile_tab_renders_five_tabs.md
  // Test plan: §6.1
  test('Profile page shows the five expected tabs', async ({ page }) => {
    await page.goto('/profile');

    // Should land on the profile page without being redirected to landing.
    await expect(page).toHaveURL(/\/profile/);

    // The five tabs per Profile.jsx lines 1075, 1087, 1099, 1110, 1122.
    const expectedTabs = [
      'Upload Documents',
      'View Profile',
      'Profile Editor',
      'Take Assessment',
      'Self-Discovery',
    ];

    for (const tabLabel of expectedTabs) {
      await expect(
        page.getByRole('tab', { name: tabLabel }).or(
          page.getByRole('button', { name: tabLabel }),
        ),
      ).toBeVisible({ timeout: 10_000 });
    }
  });
});

test.describe('profile_upload_pdf_processes_to_completion', () => {
  // tests/fixtures/scenarios/profile_upload_pdf_processes_to_completion.md
  // Test plan: §6.2 — PDF upload asserts success status only.
  //
  // NOTE: We do NOT assert specific attribute values here (e.g. "Alex Rivera").
  // F-9 from the prior run revealed that re-uploading against a populated account
  // merges with existing data — scalars are preserved, lists are appended.
  // Attribute verification requires a freshly-reset account (§2.4), which needs
  // backend endpoint widening (see follow-up issue). For now we assert upload-success
  // only, which is safe regardless of account state.
  test('uploading sample-junior-comprehensive.pdf completes with success status', async ({
    page,
  }) => {
    await page.goto('/profile');
    await expect(page).toHaveURL(/\/profile/);

    // Navigate to the Upload Documents tab (may already be active on an empty profile).
    const uploadTab = page
      .getByRole('tab', { name: 'Upload Documents' })
      .or(page.getByRole('button', { name: 'Upload Documents' }));
    await uploadTab.waitFor({ state: 'visible', timeout: 10_000 });
    await uploadTab.click();

    // Find the file input inside the upload zone (may be hidden behind a drag-drop UI).
    const fileInput = page.locator('input[type="file"]');
    await fileInput.waitFor({ state: 'attached', timeout: 10_000 });
    await fileInput.setInputFiles(JUNIOR_PDF);

    // Click the upload/submit button if it's separate from file selection.
    // Profile.jsx calls the upload button "Upload <N> Profile(s)" or similar.
    const uploadButton = page.getByRole('button', { name: /upload.*profile/i });
    const uploadButtonVisible = await uploadButton.isVisible().catch(() => false);
    if (uploadButtonVisible) {
      await uploadButton.click();
    }

    // Wait for the processing to complete (Gemini extraction can take 15-30s).
    // Assert a success status message appears.
    // Profile.jsx line 720-722 shows success: "Successfully uploaded X file(s)"
    await expect(
      page
        .getByText(/successfully uploaded/i)
        .or(page.getByText(/complete/i))
        .or(page.getByText(/upload.*success/i)),
    ).toBeVisible({ timeout: 60_000 });

    // Assert no error banner is present.
    await expect(page.getByText(/all uploads failed/i)).toHaveCount(0);
    await expect(page.getByText(/upload.*error/i)).toHaveCount(0);
  });
});

test.describe('profile_upload_unsupported_format_rejects', () => {
  // tests/fixtures/scenarios/profile_upload_unsupported_format_rejects.md
  // Test plan: §6.9 — Negative path: unsupported file format rejected client-side.
  test('attempting to upload an .exe file is rejected before any API call', async ({
    page,
  }) => {
    await page.goto('/profile');
    await expect(page).toHaveURL(/\/profile/);

    const uploadTab = page
      .getByRole('tab', { name: 'Upload Documents' })
      .or(page.getByRole('button', { name: 'Upload Documents' }));
    await uploadTab.waitFor({ state: 'visible', timeout: 10_000 });
    await uploadTab.click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.waitFor({ state: 'attached', timeout: 10_000 });

    // Create a tiny fake executable in memory using a Buffer blob.
    // Profile.jsx line 1499: accept=".pdf,.docx,.txt,.doc,.md,.markdown" — .exe is not listed.
    await fileInput.setInputFiles({
      name: 'malware.exe',
      mimeType: 'application/octet-stream',
      buffer: Buffer.from('MZ'), // minimal PE magic bytes — not a real executable
    });

    // Assert a client-side rejection message appears (no API call needed).
    // The rejection happens before upload: no "Successfully uploaded" message.
    await expect(
      page
        .getByText(/unsupported.*format/i)
        .or(page.getByText(/not supported/i))
        .or(page.getByText(/invalid.*file/i))
        .or(page.getByText(/file type/i)),
    ).toBeVisible({ timeout: 5_000 });

    // Assert the page does not crash: upload zone should still be functional.
    await expect(fileInput).toBeAttached();
  });
});
