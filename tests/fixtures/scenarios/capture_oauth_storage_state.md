# Scenario: capture_oauth_storage_state

**Test plan section:** §13.2 (Automation handoff — real-OAuth pattern)  
**Auth required:** Interactive (operator must complete Google 2FA push)  
**Spec file:** `tests/playwright-prod/specs/capture-auth.spec.js`  
**Project:** `capture`  
**Iteration:** 2

## Objective

Capture an authenticated browser session for `stratiaadmissions@gmail.com` and save it to `auth-state/storageState.json` so subsequent auth-gated specs can run unattended without repeating the interactive OAuth flow.

This is a **one-shot maintenance spec**, not a regression test. Run it whenever `storageState.json` expires or is missing.

## Preconditions

- GCP ADC configured as `cvsubs@gmail.com` (for Secret Manager access if `STRATIA_AUTOFILL_PASSWORD=1`).
- Chromium window must be visible (operator's physical screen or a headed display).
- Operator has access to the Google account's 2FA device (phone with IPP push enabled).
- `auth-state/` directory exists under `tests/playwright-prod/` (gitignored).

## Step-by-step actions

1. Run: `HEADED=1 npx playwright test --project=capture --headed`
2. Playwright opens a headed Chromium window.
3. Spec navigates to `https://stratiaadmissions.com/` and clicks "Get Stratia free".
4. Firebase Auth popup opens; spec waits for Google account chooser.
5. If the email field is visible, the spec pre-fills `stratiaadmissions@gmail.com` and clicks Next.
6. **Autofill mode** (`STRATIA_AUTOFILL_PASSWORD=1`): spec fills the password field from GCP Secret Manager. Operator only needs to approve the 2FA push.
7. **Manual mode** (default, `STRATIA_AUTOFILL_PASSWORD=0` or unset): operator types both the password AND approves the 2FA push.
8. Main app tab redirects to `/universities` — signal that OAuth is complete.
9. Spec saves `context.storageState()` to `tests/playwright-prod/auth-state/storageState.json`.

## Expected outcomes

- `auth-state/storageState.json` is created (or updated) with valid Firebase ID tokens and cookies.
- The file is NOT committed to git (it is in `.gitignore`).
- The spec reports success and prints the file path and expiry reminder.

## Session expiry policy

Firebase Auth sessions last approximately **30 days**. The `auth` project guard (`lib/auth.js`) rotates at **25 days** — it fails any `auth.spec.js` run if the file is older than 25 days, with error:

```
auth-state expired or missing — re-run capture-auth.spec.js with --project=capture
```

Re-run this spec at least every 25 days to maintain unattended auth-gated test runs.

## Fixtures referenced

None — this scenario uses live Google OAuth, not fixture data.

## Known edge cases

- The IPP push can take 1–3 minutes on a slow mobile connection. The spec waits up to 5 minutes for the `/universities` redirect.
- If the account chooser shows multiple accounts, select `stratiaadmissions@gmail.com` explicitly.
- The spec does not persist the password value to disk, logs, or screenshots at any point (`getTestPassword()` is called in-process only if autofill mode is enabled).
- If the popup is blocked by the browser, dismiss the block notification and retry.
