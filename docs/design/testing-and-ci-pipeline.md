# Design: Automated testing & CI pipeline

Status: Approved (shipped in PRs #16, #17, #18; doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/testing-and-ci-pipeline.md](../prd/testing-and-ci-pipeline.md)

## Phasing

The work shipped in three PRs, each adding one tier:

| PR | Phase | Adds |
|---|---|---|
| #16 | Phase 1 | Backend pytest + Cloud Build CI trigger |
| #17 | Phase 2 | Frontend Vitest + Playwright E2E |
| #18 | Phase 3 | Student-scenario integration tests + the template-mutation bugfix they caught |

After Phase 3 the suite is at **202 backend pytest tests, 41 Vitest tests, 2 Playwright happy-path tests** — all running in under 5 minutes from cold cache.

## Cloud Build

`cloudbuild.yaml` at the repo root defines the pipeline. Cloud Build triggers (managed via the Console UI per `docs/cicd-setup.md` — gcloud trigger creation kept failing) fire the build on:

- Pull request opened / updated → "PR" trigger.
- Push to main → "main-push" trigger.

Both triggers run the same `cloudbuild.yaml`. The PR trigger is the gate — its status check appears on the PR and blocks merge until green.

### Pipeline steps

```yaml
steps:
  1. backend-tests       # python:3.12-slim → pytest
  2. bash-syntax         # bash -n on deploy.sh / deploy_frontend.sh
  3. frontend            # mcr.microsoft.com/playwright:v1.59.1-jammy
                         #   npm ci + vitest + vite build + playwright test
```

`E2_HIGHCPU_8` machine, `600s` timeout, `CLOUD_LOGGING_ONLY` (avoids the dual-logging permission issue for legacy projects).

## Backend tests (Phase 1)

### Layout

```
tests/
  cloud_functions/
    counselor_agent/
      conftest.py                    ← stubs google.cloud.firestore + google.adk
      test_planner.py
      test_work_feed.py
      test_counselor_tools.py
      test_generate_roadmap_scenarios.py   ← Phase 3
    profile_manager_v2/
      conftest.py
      test_firestore_db.py
```

### Stubbing strategy

`conftest.py` in each function's test dir does the heavy lifting: stubs out `google.cloud.firestore`, `google.adk`, `vertexai`, etc. so the real cloud-function code can be imported without GCP auth. Stubs are in-memory (a dict masquerading as a Firestore collection) and keyed to the test's expectations.

The function code itself is not modified for testability — it imports its production deps; the tests inject stubs at import time via `sys.modules` manipulation in conftest.

### Test runner

`requirements-test.txt`:
```
pytest
requests
```

That's it. No GCP libs needed because the conftest stubs them.

`pytest.ini` configures the `rootdir` and collects from `tests/`.

### What's covered

- `counselor_agent`: planner resolver (every priority branch + clamping edges), translate_task and family, generate_roadmap end-to-end across all 12 grade × semester combos plus edges (Phase 3), work-feed aggregation (empty/single-source/all-sources/threshold boundaries).
- `profile_manager_v2`: firestore_db happy paths and edge cases for every endpoint (`update-notes` covers all 5 collections via parametrize; `save-roadmap-task` happy + missing-title + invalid-date).

## Frontend tests (Phase 2)

### Vitest

Configured via `vite.config.js`'s `test` block. `jsdom` for the DOM. `@testing-library/react` for component rendering.

Tests live in `frontend/src/__tests__/`:
- `setup.js` — global mocks (axios, Firebase Auth) + jsdom polyfills.
- `RoadmapPage.test.jsx`, `AddTaskModal.test.jsx`, `ThisWeekFocusCard.test.jsx`, `MiniDashboard.test.jsx`, `NotesAffordance.test.jsx`.

Mocking: every test mocks `axios` so no real network. Firebase auth is mocked at module level so no real auth either.

`npm run test` runs once and exits (Vitest's `--run` mode under `vitest run`).

### Playwright E2E

Configured via `playwright.config.js`. Single project (chromium only — we trust cross-browser parity for our happy paths and a Chrome-only E2E catches the integration bugs we care about).

```
frontend/
  playwright.config.js
  tests-e2e/
    roadmap.spec.js
```

#### Auth bypass

`AuthContext.jsx` reads `localStorage.__E2E_TEST_USER__` when `import.meta.env.MODE !== 'production'` and uses it as the signed-in user. The test's `beforeEach` injects this via `page.addInitScript`. The bypass is statically eliminated from production builds via Vite's tree-shaking on `MODE === 'production'`.

#### Build mode

Playwright's `webServer` config builds with `vite build --mode test` (NOT production), so the auth bypass survives, and serves with `vite preview`. CI sets `CI=true` so Playwright's config switches to single-worker + retries=1 + no `reuseExistingServer`.

#### HTTP mocking

The two scenario tests intercept every backend URL via `page.route` — fulfilled with the smallest payload that keeps the rendered surface alive. CORS headers (`Access-Control-Allow-Origin: *` etc.) are required or axios silently rejects responses.

Route handlers are registered in reverse-priority order (Playwright runs handlers in reverse of registration), so the catch-all goes FIRST and specific handlers (registered after) take precedence.

#### Playwright + Docker version pinning

The Playwright Docker image `mcr.microsoft.com/playwright:v1.59.1-jammy` ships browsers preinstalled. The `@playwright/test` npm package version MUST match the image tag exactly — they're versioned in lockstep because the image bundles the binaries the package looks for. Both pinned to `1.59.1`; bumping requires updating both.

## Scenario tests (Phase 3)

`test_generate_roadmap_scenarios.py` drives `generate_roadmap()` end-to-end with frozen `datetime.now()` and stubbed profile / college-context fetches. 34 tests covering:

- Every grade × semester combo (9 templates × profile-driven path).
- Grade clamping edges (already-graduated, far-future, summer fallbacks).
- Resolver source matrix (caller / caller-grade-only / profile / default).
- College-context translation (per-school RD, UC group, essays, verify-materials, overdue marker, single UC, missing deadline).
- Template-isolation regression test (catches the `.copy()` shallow-copy mutation bug).
- Response-shape contract (parametrized).

Fixtures:
- `fixed_today(year, month, day)` — context manager that patches `planner.datetime.now()`.
- `make_request(**body)` — Mock-based stand-in for Flask's `request.get_json()`.
- `stub_student(profile=…, context=…)` — patches `get_student_profile` and `get_college_context` for one test.
- `college_context(*colleges, …)` — builder for college-context dicts.

## Caught bugs

Phase 3 caught a real bug while it was being written: `generate_roadmap` did `template = TEMPLATES[key].copy()` (shallow copy). The translator then mutated `template['phases'][i]['tasks']`, which still pointed at the global `TEMPLATES` dict. Subsequent users on the same instance saw the previous user's translated tasks. Fix: `import copy; template = copy.deepcopy(TEMPLATES[key])`. Test pinning this down: `test_template_isolation_across_calls`.

## Risks

- **Stubbing drift**. Stubbed Firestore could diverge from real Firestore behavior. Mitigation: the stubs are intentionally minimal (return shapes, not behavior); tests assert on what we control. The shell-level integration tests (`test_*.sh`) hit live URLs and catch contract drift on the real backend.
- **Flaky Playwright**. Playwright tests can flake on race conditions (element appears before content loads). Mitigation: every assertion uses `expect(locator).toBeVisible()` which retries; explicit `force: true` on clicks fighting fixed-position overlays; `CI=true` enables retries=1.
- **CI cost**. Cloud Build minutes are billable. Mitigation: 5-minute budget kept the cost trivial. Caches help: `npm ci --prefer-offline` reuses `~/.npm` between runs; pip's wheel cache is small enough to redownload each time.
- **CI vs. local divergence**. The CI placeholder URLs don't match local dev URLs. Mitigation: Playwright route handlers match by path suffix (`/work-feed(\?|$)`) not full URL — works regardless of host.

## Alternatives considered

- **GitHub Actions instead of Cloud Build.** Rejected: Cloud Build keeps GCP-native auth and integrates with the existing project's IAM. GH Actions would have meant managing a separate set of credentials.
- **Single mega-test for the resolver.** Rejected: a parametrized matrix that fails at one cell tells you exactly which scenario is broken; a single failing assertion that "everything broke somewhere" is useless.
- **Skip the production build step in CI.** Rejected: type/import errors that don't show up in `vite dev` (because of HMR / lazy resolution) DO show up in `vite build`. Cheap insurance.
- **Mock the entire frontend in Vitest using shallow rendering.** Rejected: shallow rendering misses the integration bugs Vitest with full render catches. Full render is fast enough.
