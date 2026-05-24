# QA Agent Playbook

Running notebook for project-specific QA knowledge — gotchas, env quirks, repro tips.
Append when you learn something; delete when it goes stale.

---

## Auth state (Firebase OAuth)

- `storageState.json` captures cookies + localStorage but **NOT** IndexedDB.
- Firebase Auth tokens live in IndexedDB (`firebaseLocalStorageDb`). Use
  `dumpFirebaseIndexedDB()` / `restoreFirebaseIndexedDB()` from `lib/auth.js`.
- Both files live in `tests/playwright-prod/auth-state/` (gitignored).
- Expiry threshold: 25 days. If `assertAuthStateValid()` throws, re-run
  `capture-auth.spec.js` headed with `HEADED=1 STRATIA_AUTOFILL_PASSWORD=1`.
- Session file is for `stratiaadmissions@gmail.com` only. Never commit it.
- **Auth-state is ephemeral and machine-local.** It is NOT preserved between
  Claude Code agent sessions. Every new QA agent session that needs auth-gated
  specs must either (a) find valid `auth-state/storageState.json` on disk from
  a previous capture, or (b) re-run `capture-auth.spec.js` interactively.
- **2FA is not skippable in unattended mode.** The `STRATIA_AUTOFILL_PASSWORD=1`
  autofill confirms: password fill works automatically. But Google sends a
  2FA push to the operator's phone regardless. The capture spec has a 10-minute
  window (`TWO_FA_TIMEOUT_MS`). The operator must approve the push on their
  phone during that window or the capture times out.
- **Pass 2 §TWO-PASS sessions require pre-captured auth state.** If the operator
  wants a QA agent to run Pass 2 verification unattended, they must ensure
  `auth-state/storageState.json` and `auth-state/firebase-indexeddb.json`
  are present on disk before spawning the agent (i.e., they ran capture
  interactively in a prior session on the same machine).

## Secret Manager / ADC mismatch on this machine

- The machine's `application_default_credentials.json` points to the OneTrust
  account, not `cvsubs@gmail.com`.
- `lib/secret-manager.js` handles this: it first tries the Node.js SDK (ADC);
  on PERMISSION_DENIED (error code 7) it falls back to:
  ```
  gcloud secrets versions access latest --secret=STRATIA_TEST_PASSWORD \
    --account cvsubs@gmail.com --project college-counselling-478115
  ```
- This fallback works because the gcloud CLI credential store has the correct
  cvsubs@gmail.com credentials.

## Account-state sensitivity

The `stratiaadmissions@gmail.com` test account behaves differently depending on
whether it has a profile:

- **With profile**: normal app flow, profile page shows data, no 404 from get-profile.
- **Without profile (after reset)**: onboarding overlay may appear on first authenticated
  visit; console fires 404 from `get-profile` and 500 from `welcome-email` — both are
  filtered in `cross-cutting.auth.spec.js` as known/expected.

After `POST /reset-all-profile`, the console error filters in
`cross-cutting.auth.spec.js` are sufficient to prevent false failures.

## Onboarding overlay

After a profile reset, the app may show a z-50 fixed overlay (onboarding/welcome modal)
that intercepts pointer events. `discover.auth.spec.js` §5.5 handles this by pressing
Escape and then clicking Skip/Close before the Explore button interaction.

If other specs fail due to pointer-intercepted clicks, add the same dismissal block.

## Playwright strict mode

`toBeVisible()` fails if the locator resolves to multiple elements. Always use
`.first()` when a locator can match more than one element. Common traps:
- `getByText(/foo/i)` often matches hidden elements (e.g., `<option>` inside `<select>`).
- Use `:not(option)` or `:not(select)` CSS selectors when targeting visible badge text.
- `page.getByText(/total essays/i)` resolved to 3 elements on the Essays tab.

## University detail page

`/universities` grid "Explore" button navigates to a **full-page route**
(`/universities/<id>`), NOT a dialog/modal. The page is scroll-based with section
headings (About, Campus Life, Academics, etc.). Test plan §5.5 was written incorrectly;
enhancement #134 tracks the correction.

## Mobile viewport (§11.3 — resolved)

- iPhone 14 viewport (390x844): horizontal overflow (50px) was issue #133, fixed in PR #146 (merged 2026-05-23).
- Post-deploy verification 2026-05-23: scrollWidth=388 on `/` and scrollWidth=390 on `/discover` at 390px — no overflow.
- §11.3 spec assertion can be tightened to assert no overflow (was non-blocking; blocker no longer needed).

## Cleanup after a QA pass

1. Reset profile: `POST https://profile-manager-v2-pfnwjfp26a-ue.a.run.app/reset-all-profile`
   with `Authorization: Bearer <Firebase ID token>` and `Content-Type: application/json`.
   Body: `{"user_email": "stratiaadmissions@gmail.com", "confirmation": "DELETE_ALL_PROFILE_DATA"}`.
   Do NOT pass `"delete_college_list": true` — this triggers bug #148 (500 error).
   Returns: `{"success": true, "deleted": {...}}`.
2. Verify profile gone: `GET /get-profile?user_email=stratiaadmissions@gmail.com` → expect 404.
3. Verify college list empty: `GET /get-college-list?user_email=stratiaadmissions@gmail.com`
   → expect `{"college_list": [], "success": true}`.
4. Get Firebase ID token: use stored refreshToken from `auth-state/firebase-indexeddb.json`
   with `https://securetoken.googleapis.com/v1/token?key=<FIREBASE_API_KEY>` (grant_type=refresh_token).
   Never use email/password — the test account uses Google OAuth only (PASSWORD_LOGIN_DISABLED).
5. Profile manager URL: `https://profile-manager-v2-pfnwjfp26a-ue.a.run.app` (confirmed 2026-05-24).
   The `64jnwiqg7a` hash seen in playbook history is wrong — use `pfnwjfp26a`.

## Known bugs (tracked in GitHub)

- **#123** (Plan tab Connection Error): `resolved` — fixed PR #132, §TWO-PASS complete 2026-05-23/24.
- **#133** (Mobile 50px overflow on /profile): `resolved` — fixed in PR #146; verified 2026-05-23.
- **#134** (Test plan §5.5 accuracy — full-page route not dialog): `enhancement,backlog`.
- **#136** (Welcome email 500 when no profile): `resolved` — fixed PR #139 (500→200), filter removed PR #143.
  §TWO-PASS complete 2026-05-24 (Pass 1+2 of autonomous loop iteration 5).
- **#148** (reset-all-profile 500 with delete_college_list=true): `bug` — `'list' object has no
  attribute 'get'` in college-list deletion code path. Profile IS deleted; error is in cleanup
  path. Filed 2026-05-24. Workaround: omit delete_college_list=true and use separate
  college-list cleanup.

## Roadmap Plan tab (§6.1 — after PR #132)

- Before PR #132: tab showed "Connection Error" card due to `grade.trim()` crash.
- After PR #132: tab shows "THIS WEEK" heading in the loading skeleton.
- The skeleton renders before semester boards populate. "THIS WEEK" heading is the
  correct post-fix assertion; do NOT assert semester board text (it may not be present
  for accounts with no profile data).

## launchpad_fit_modal_opens_with_bounds (§7.3)

- This scenario auto-skips when the account has no saved schools.
- After a profile reset, the account has 0 saved schools — the skip is expected.
- To run this scenario, save a school from Discover first, wait for fit analysis
  to compute, then run the spec.

## Scenario count (iteration 5)

- Total executable: 22 scenarios
- Passing: 21
- Intentionally skipped: 1 (`launchpad_fit_modal_opens_with_bounds` — no saved schools)
- EXIT: 0 (full suite passes)

Last real-run: 2026-05-24 by QA Agent (iteration 5 / autonomous loop pass 1+2).

### Discover search test fix (iteration 5)
`discover_search_filters_by_name` was failing due to two compounding issues:
1. Onboarding overlay intercepting pointer events (same fix as §5.5 already had).
2. Wrong grid-ready signal: `getByText(/\d+ universities/i)` matched "Explore 150+
   universities" hero text immediately on page load (before grid renders), causing
   search to fire too early. Fixed by waiting for pagination footer `/Page 1 of \d+/i`.
Both fixes applied in spec + scenario doc. Test now stable (verified passing in Pass 1+2).
