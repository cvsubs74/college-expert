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

export const FIREBASE_INDEXEDDB_PATH = path.resolve(
  __dirname,
  '../auth-state/firebase-indexeddb.json',
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
/**
 * Dump Firebase Auth's IndexedDB (`firebaseLocalStorageDb`) entries from the
 * authenticated page context. Called from capture-auth.spec.js after the
 * /universities redirect, before saving auth state.
 *
 * Returns an array of {fbase_key, value} objects. Empty array if the DB
 * doesn't exist yet (auth not completed).
 */
export async function dumpFirebaseIndexedDB(page) {
  return await page.evaluate(async () => {
    return new Promise((resolve) => {
      const dbReq = indexedDB.open('firebaseLocalStorageDb');
      dbReq.onerror = () => resolve([]);
      dbReq.onsuccess = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('firebaseLocalStorage')) {
          db.close();
          resolve([]);
          return;
        }
        const tx = db.transaction(['firebaseLocalStorage'], 'readonly');
        const store = tx.objectStore('firebaseLocalStorage');
        const getAll = store.getAll();
        getAll.onsuccess = () => {
          db.close();
          resolve(getAll.result);
        };
        getAll.onerror = () => {
          db.close();
          resolve([]);
        };
      };
    });
  });
}

/**
 * Restore Firebase Auth IndexedDB entries into a fresh page context.
 *
 * Must be called AFTER the page has navigated to a stratiaadmissions.com
 * origin (IndexedDB is origin-scoped). The caller's pattern is:
 *   1. await page.goto('/')
 *   2. await restoreFirebaseIndexedDB(page, entries)
 *   3. await page.reload()   // Firebase SDK now reads the restored tokens
 *   4. Continue with auth-gated assertions
 */
export async function restoreFirebaseIndexedDB(page, entries) {
  if (!entries || entries.length === 0) return;
  await page.evaluate(async (records) => {
    return new Promise((resolve, reject) => {
      const openReq = indexedDB.open('firebaseLocalStorageDb', 1);
      openReq.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('firebaseLocalStorage')) {
          db.createObjectStore('firebaseLocalStorage', { keyPath: 'fbase_key' });
        }
      };
      openReq.onerror = () => reject(openReq.error);
      openReq.onsuccess = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('firebaseLocalStorage')) {
          db.close();
          reject(new Error('firebaseLocalStorage object store missing'));
          return;
        }
        const tx = db.transaction(['firebaseLocalStorage'], 'readwrite');
        const store = tx.objectStore('firebaseLocalStorage');
        for (const r of records) store.put(r);
        tx.oncomplete = () => {
          db.close();
          resolve();
        };
        tx.onerror = () => {
          db.close();
          reject(tx.error);
        };
      };
    });
  }, entries);
}

/**
 * Load the saved Firebase IndexedDB entries from disk, returning an array.
 * Returns [] if the file doesn't exist.
 */
export function loadFirebaseIndexedDB() {
  if (!fs.existsSync(FIREBASE_INDEXEDDB_PATH)) return [];
  return JSON.parse(fs.readFileSync(FIREBASE_INDEXEDDB_PATH, 'utf8'));
}

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
