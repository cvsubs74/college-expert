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

## Mobile viewport (§11.3 — non-blocking)

- iPhone 14 viewport (390x844): body.scrollWidth=440 vs clientWidth=390 on `/profile`.
- 50px horizontal overflow observed 2026-05-23 (issue #133).
- §11.3 is non-blocking. The cross-cutting spec documents but does NOT fail on overflow.

## Cleanup after a QA pass

1. Reset profile: `POST https://profile-manager-v2-<hash>-ue.a.run.app/reset-all-profile`
   with `Authorization: Bearer <Firebase ID token>` and `Content-Type: application/json`.
   Body: `{"confirmation": "DELETE_ALL_PROFILE_DATA"}`.
   Returns: `{"success": true, "deleted": {college_list, files, fits, profile}}`.
2. College list: if schools remain after reset, use `clearCollegeList(page)` from
   `tests/playwright-prod/lib/cleanup.js`, or call
   `DELETE /remove-from-college-list` API per school.
3. Issue #128 — the `/clear-test-data` endpoint only allows `duser8531@gmail.com`,
   not `stratiaadmissions@gmail.com`. PR #131 widens the allow-list; verify the
   endpoint works for `stratiaadmissions@gmail.com` before relying on it.

## Known bugs (tracked in GitHub)

- **#123** (Plan tab Connection Error): fixed in PR #132 (deployed 2026-05-23). Pass 1
  of §TWO-PASS complete. Pass 2 needed before `resolved` label.
- **#133** (Mobile 50px overflow on /profile): `enhancement,backlog`.
- **#134** (Test plan §5.5 accuracy — full-page route not dialog): `enhancement,backlog`.
- **#136** (Welcome email 500 when no profile): `bug` — backend fails on accounts with
  no profile doc. Fires as console error on every authenticated page for reset accounts.

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

## Scenario count (iteration 4)

- Total executable: 22 scenarios
- Passing: 21
- Intentionally skipped: 1 (`launchpad_fit_modal_opens_with_bounds` — no saved schools)
- EXIT: 0 (full suite passes)

Last real-run: 2026-05-23 by QA Agent (iteration 4 session).
