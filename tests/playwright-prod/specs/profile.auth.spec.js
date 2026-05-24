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
import {
  assertAuthStateValid,
  loadFirebaseIndexedDB,
  restoreFirebaseIndexedDB,
} from '../lib/auth.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Fixture path for the junior-comprehensive PDF (Section 6.2).
// From specs/: up 2 dirs is tests/, then fixtures/profile-samples/.
const JUNIOR_PDF = path.resolve(
  __dirname,
  '../../fixtures/profile-samples/sample-junior-comprehensive.pdf',
);

let firebaseEntries = [];

test.beforeAll(() => {
  // Fail fast if the storageState is missing or older than 25 days.
  // Error message matches the documented guard:
  //   "auth-state expired or missing — re-run capture-auth.spec.js with --project=capture"
  assertAuthStateValid();
  // Load Firebase IndexedDB entries (auth tokens) saved during capture-auth.
  // Required because storageState alone doesn't capture IndexedDB.
  firebaseEntries = loadFirebaseIndexedDB();
});

test.beforeEach(async ({ page }) => {
  // Land on the stratiaadmissions.com origin first — IndexedDB is origin-scoped,
  // so the write below needs an active context for the right origin.
  await page.goto('/');
  await restoreFirebaseIndexedDB(page, firebaseEntries);
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

    // The onboarding overlay ("Let's get started") appears on fresh/reset accounts
    // after an async profile-check completes. It intercepts all pointer events.
    // Wait for the Upload Documents tab first (confirms page settled), then suppress
    // the overlay via CSS injection — this survives React re-renders (unlike DOM removal).
    const uploadTab = page
      .getByRole('tab', { name: 'Upload Documents' })
      .or(page.getByRole('button', { name: 'Upload Documents' }));
    await uploadTab.waitFor({ state: 'visible', timeout: 10_000 });

    // Inject CSS to suppress any z-50 fixed overlay. This is equivalent to clicking
    // Skip in terms of test validity (we're testing upload behavior, not the overlay).
    // CSS injection survives React virtual DOM re-renders; DOM removal does not.
    await page.addStyleTag({
      content: 'div[class*="fixed"][class*="inset-0"][class*="z-50"] { display: none !important; pointer-events: none !important; }',
    });
    await page.waitForTimeout(200); // brief settle

    await uploadTab.click();

    // Set the file directly on the hidden input. Profile.jsx wires the onChange
    // handler to the underlying <input type="file">, so setInputFiles + a manual
    // change-event dispatch is sufficient to update React state — no filechooser
    // click required.
    const fileInput = page.locator('input[type="file"]');
    await fileInput.waitFor({ state: 'attached', timeout: 10_000 });
    await fileInput.setInputFiles(JUNIOR_PDF);

    // Wait for the UI to reflect the selection. Profile.jsx renders
    // "1 file(s) selected" + the filename + an enabled "Upload N Profile(s)" button.
    await expect(page.getByText(/file\(s\) selected/i)).toBeVisible({ timeout: 10_000 });

    const uploadButton = page.getByRole('button', { name: /upload.*profile/i });
    await uploadButton.waitFor({ state: 'visible', timeout: 10_000 });
    await uploadButton.click();

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
  // Test plan: §6.9 — Negative path: unsupported file format rejected by accept attribute.
  //
  // NOTE: The original behavioral test (set .exe via setInputFiles, expect a rejection
  // banner) is unreliable because browsers don't enforce `accept` on programmatic
  // setInputFiles, and Profile.jsx has no JS-side format validation — it relies
  // solely on the file input's `accept` attribute to restrict the OS picker dialog.
  // We test the attribute statically instead — that's the actual user-protection mechanism.
  test('file input accept attribute restricts to supported formats only', async ({
    page,
  }) => {
    await page.goto('/profile');
    await expect(page).toHaveURL(/\/profile/);

    // Wait for page to settle, then suppress overlay via CSS injection.
    const uploadTab2 = page
      .getByRole('tab', { name: 'Upload Documents' })
      .or(page.getByRole('button', { name: 'Upload Documents' }));
    await uploadTab2.waitFor({ state: 'visible', timeout: 10_000 });
    await page.addStyleTag({
      content: 'div[class*="fixed"][class*="inset-0"][class*="z-50"] { display: none !important; pointer-events: none !important; }',
    });
    await page.waitForTimeout(200);

    await uploadTab2.click();

    const fileInput = page.locator('input[type="file"]');
    await fileInput.waitFor({ state: 'attached', timeout: 10_000 });

    // Per Profile.jsx line ~1499 the accept attribute should be:
    //   .pdf,.docx,.txt,.doc,.md,.markdown
    const accept = await fileInput.getAttribute('accept');
    expect(accept, 'file input must have an accept attribute').not.toBeNull();
    expect(accept.toLowerCase()).toContain('.pdf');
    expect(accept.toLowerCase()).toContain('.docx');
    expect(accept.toLowerCase()).toContain('.txt');
    // .exe must NOT be in the list — that's the user-facing safety guarantee.
    expect(accept.toLowerCase()).not.toContain('.exe');
  });
});
