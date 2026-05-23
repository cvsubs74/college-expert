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
- Pre-flight: `gcloud secrets versions access latest --secret=STRATIA_TEST_PASSWORD --project=college-counselling-478115 >/dev/null` should exit 0. Specs that need the password call `lib/secret-manager.js#getTestPassword()`, which fetches it at runtime and never writes the value to disk or logs.
- **Never** log, print, commit, or screenshot the password value.

## Running

```bash
# No-auth specs only (pre-flight, public pages, unauthenticated redirects)
npx playwright test specs/no-auth.spec.js

# All specs (requires storageState — see below)
npx playwright test
```

## Auth: capturing storageState (iteration 2)

The primary test account `stratiaadmissions@gmail.com` has Google 2-Step Verification
enabled, so OAuth completion requires a human-in-the-loop phone tap. To make subsequent
runs unattended, we capture the post-auth session as `auth-state/storageState.json`
(gitignored) and reuse it across runs.

The capture spec lands in iteration 2. Until then, only the no-auth specs in this
suite run unattended.

When storageState expires (Firebase Auth sessions typically last ~30 days), specs
will fail with a clear "auth-state expired" error and the operator re-runs the
capture spec interactively.

## Directory layout

```
tests/playwright-prod/
├── README.md                # this file
├── package.json             # Playwright + GCP Secret Manager deps
├── playwright.config.js     # config for production-mode tests
├── auth-state/              # storageState.json — gitignored (iteration 2)
├── lib/
│   ├── secret-manager.js    # fetches STRATIA_TEST_PASSWORD from GCP at runtime
│   └── auth.js              # storageState loader (iteration 2)
└── specs/
    ├── no-auth.spec.js      # specs that don't require auth
    └── capture-auth.spec.js # one-shot OAuth capture (iteration 2)
```

## Cleanup discipline

Per `docs/qa-autonomous-loop-spec.md`, every full pass must end with deletion of all
test-user-owned data for `stratiaadmissions@gmail.com`. The university knowledgebase
is strictly off-limits. Cleanup helpers land in iteration 2 (`lib/cleanup.js`).

## Scenarios catalog

Each scenario this suite exercises has a matching markdown doc under
`tests/fixtures/scenarios/`. See that directory for the index.

This iteration ships 3 scenario docs + 1 spec covering them:

- `pre_flight_landing_renders` (plan §3)
- `unauthenticated_profile_redirect` (plan §4.6)
- `public_resources_page_renders` (plan §10)

All three are no-auth and should pass green against production today.
