# tests/playwright-prod — Production-mode browser tests

Browser tests that exercise the **live production** app at `https://stratiaadmissions.com`
as part of the autonomous QA loop (`docs/qa-autonomous-loop-spec.md`).

Not the same suite as `frontend/tests-e2e/` — that runs locally against `localhost:4173`
with mocked HTTP and a faked auth bypass. This suite runs against production with real
network calls and (for auth-gated specs) a captured Google OAuth session.

## Setup (one-time)

```bash
cd tests/playwright-prod
npm install
npx playwright install chromium
```

## Environment

- **gcloud ADC** active with `cvsubs@gmail.com` (or a service account holding
  `roles/secretmanager.secretAccessor` on the `STRATIA_TEST_PASSWORD` secret in
  project `college-counselling-478115`).
- Pre-flight: `gcloud secrets versions access latest --secret=STRATIA_TEST_PASSWORD --project=college-counselling-478115 --account=cvsubs@gmail.com >/dev/null` should exit 0. Specs that need the password call `lib/secret-manager.js#getTestPassword()`, which fetches it at runtime and never writes the value to disk or logs.
- **Never** log, print, commit, or screenshot the password value.

## Running

```bash
# No-auth specs only (pre-flight, public pages, unauthenticated redirects)
npx playwright test --project=no-auth

# Capture OAuth session (interactive — headed, operator must approve 2FA push)
HEADED=1 npx playwright test --project=capture --headed

# Auth-gated specs (requires auth-state/storageState.json — run capture first)
npx playwright test --project=auth

# All specs (no-auth + auth; excludes capture which is always manual)
npx playwright test --project=no-auth --project=auth
```

## Auth: capturing storageState

The primary test account `stratiaadmissions@gmail.com` has Google 2-Step Verification
enabled, so OAuth completion requires a human-in-the-loop phone tap. To make subsequent
runs unattended, we capture the post-auth session as `auth-state/storageState.json`
(gitignored) and reuse it across runs.

### Capture flow

1. Run: `HEADED=1 npx playwright test --project=capture --headed`
2. A headed Chromium window opens and navigates to `stratiaadmissions.com`.
3. The spec clicks "Get Stratia free", which opens the Firebase Auth popup.
4. **If `STRATIA_AUTOFILL_PASSWORD=1`** (recommended): the spec fetches the password
   from GCP Secret Manager and fills it automatically. You only need to approve the
   2FA push notification on your phone.
5. **Default (manual)**: bring the Chromium window to the foreground, type the password,
   and approve the 2FA push.
6. Once the main tab redirects to `/universities`, the spec saves
   `auth-state/storageState.json` and exits.

```bash
# Autofill mode (password from Secret Manager; operator handles 2FA only):
STRATIA_AUTOFILL_PASSWORD=1 HEADED=1 npx playwright test --project=capture --headed

# Manual mode (operator types both password and approves 2FA):
HEADED=1 npx playwright test --project=capture --headed
```

### Expiry policy

Firebase Auth sessions last approximately **30 days**. The `auth` project guard
(`lib/auth.js`) enforces a **25-day rotation threshold** — any `auth.spec.js` run
will fail immediately with:

```
auth-state expired or missing — re-run capture-auth.spec.js with --project=capture
  Expected path: .../auth-state/storageState.json
  Run: HEADED=1 npx playwright test --project=capture --headed
```

Re-run the capture spec at least every 25 days to maintain unattended auth runs.
`storageState.json` is gitignored and must be re-captured after each machine reset.

## Directory layout

```
tests/playwright-prod/
├── README.md                      # this file
├── package.json                   # Playwright + GCP Secret Manager deps
├── playwright.config.js           # three projects: no-auth, capture, auth
├── auth-state/                    # storageState.json — gitignored
├── lib/
│   ├── secret-manager.js          # fetches STRATIA_TEST_PASSWORD from GCP at runtime
│   ├── auth.js                    # storageState presence + expiry guard (25-day threshold)
│   └── cleanup.js                 # UI-driven cleanup helpers (resetProfile, clearCollegeList)
└── specs/
    ├── no-auth.spec.js            # public pages + unauthenticated redirects
    ├── capture-auth.spec.js       # interactive OAuth capture (run with --project=capture)
    └── profile.auth.spec.js       # auth-gated profile scenarios (§6.1, §6.2, §6.9)
```

## Cleanup discipline

Per `docs/qa-autonomous-loop-spec.md`, every full pass must end with deletion of all
test-user-owned data for `stratiaadmissions@gmail.com`. The university knowledgebase
is strictly off-limits.

`lib/cleanup.js` provides three idempotent helpers:

- `resetProfile(page)` — navigates to /profile and clicks the Reset Profile button.
  Safe to call on an empty account.
- `clearCollegeList(page)` — navigates to /launchpad and removes all saved schools.
  Safe to call on an empty list.
- `assertCleanState(page)` — verifies no profile data and no saved schools remain.
  Throws with a descriptive error if cleanup was incomplete.

### Why UI-driven cleanup (not the backend endpoint)

The `clear-test-data` endpoint in `profile_manager_v2` (`main.py` line 1744) only
accepts `duser8531@gmail.com` and will 403 for `stratiaadmissions@gmail.com`. A
follow-up issue has been filed requesting the endpoint's allow-list be extended to
accept the primary browser test account. Until that ships, the UI-driven helpers in
`lib/cleanup.js` are the primary cleanup mechanism.

## Scenarios catalog

Each scenario this suite exercises has a matching markdown doc under
`tests/fixtures/scenarios/`. See that directory for the index.

### Iteration 1 scenarios (no-auth)

- `pre_flight_landing_renders` (plan §3 + §4.1)
- `unauthenticated_profile_redirect` (plan §4.6)
- `public_resources_page_renders` (plan §10)

### Iteration 2 scenarios (auth-gated + capture)

- `capture_oauth_storage_state` — interactive OAuth session capture
- `profile_tab_renders_five_tabs` (plan §6.1)
- `profile_upload_pdf_processes_to_completion` (plan §6.2)
- `profile_upload_unsupported_format_rejects` (plan §6.9)
