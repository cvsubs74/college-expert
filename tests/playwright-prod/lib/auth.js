// auth.js — storageState guard for auth-gated Playwright specs.
//
// Called from playwright.config.js globalSetup to fail-fast if the
// storageState is missing or older than the expiry threshold.
//
// Firebase Auth sessions last ~30 days. We rotate at 25 days to leave
// headroom before expiry (which would cause silent auth failures rather
// than a clear test error).

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const AUTH_STATE_PATH = path.resolve(
  __dirname,
  '../auth-state/storageState.json',
);

// Rotation threshold: 25 days expressed as milliseconds.
const EXPIRY_DAYS = 25;
const EXPIRY_MS = EXPIRY_DAYS * 24 * 60 * 60 * 1000;

/**
 * Verify that auth-state/storageState.json exists and is not older than
 * EXPIRY_DAYS days.
 *
 * Throws with a clear, actionable error message on any failure.
 * Called from the `auth` Playwright project's globalSetup (if configured)
 * or from each auth-gated spec via beforeAll.
 */
export function assertAuthStateValid() {
  if (!fs.existsSync(AUTH_STATE_PATH)) {
    throw new Error(
      'auth-state expired or missing — re-run capture-auth.spec.js with --project=capture\n' +
        `  Expected path: ${AUTH_STATE_PATH}\n` +
        '  Run: HEADED=1 npx playwright test --project=capture --headed',
    );
  }

  const stat = fs.statSync(AUTH_STATE_PATH);
  const ageMs = Date.now() - stat.mtimeMs;
  if (ageMs > EXPIRY_MS) {
    const ageDays = Math.floor(ageMs / (24 * 60 * 60 * 1000));
    throw new Error(
      `auth-state expired or missing — re-run capture-auth.spec.js with --project=capture\n` +
        `  storageState.json is ${ageDays} days old (threshold: ${EXPIRY_DAYS} days).\n` +
        '  Run: HEADED=1 npx playwright test --project=capture --headed',
    );
  }
}
