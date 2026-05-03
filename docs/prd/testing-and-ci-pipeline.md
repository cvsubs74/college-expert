# PRD: Automated testing & CI pipeline

Status: Approved (shipped in PRs #16, #17, #18; doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03

## Problem

The codebase shipped its first dozen features without an automated test suite. Verification was "deploy and click around" — fast for one engineer working on one feature, but it doesn't scale to the kind of cross-cutting work the Roadmap consolidation kicked off (resolver + 12 grade × semester combos × per-college translations). A bug in `planner.py` that mutated a shared template across users would have shipped silently. A regression in a Vitest-coverable React component would have surfaced as a user complaint two days later.

We need a CI gate on every PR and every push to main that runs:

1. Backend unit tests.
2. Frontend unit tests.
3. A frontend production build (catches type/import errors that don't show up in dev).
4. At least one frontend E2E test that drives the real bundle.

And it has to be fast enough that nobody disables it — well under 5 minutes.

## Goals

- **PR gate**: every PR is blocked from merging until CI passes.
- **Backend coverage**: pytest suite that exercises every cloud function's public surface; unit-style (no real GCP, no network), runs in seconds.
- **Frontend coverage**: Vitest unit tests + at least one Playwright happy-path E2E.
- **Build sanity**: `vite build` runs in CI to catch type errors and missing imports before they hit a user.
- **Multi-environment safety**: tests run cleanly without GCP credentials (so contributors can run them locally without auth setup).
- **Scenario coverage**: critical multi-input flows (the roadmap resolver across 12 grade × semester combos, college translations, etc.) are tested at the integration level so refactors don't silently break them.

## Non-goals

- End-to-end tests against deployed cloud functions. Those exist as `test_*.sh` files for manual post-deploy verification. CI runs unit + browser-only.
- Performance / load testing in CI. Out of scope.
- Coverage thresholds with a hard fail-below percentage. We track coverage but don't gate on a number.
- Mutation testing.

## Users

- Every engineer working on this codebase. CI is for them.
- Future contributors who want confidence that their change doesn't break anything else.

## User stories

1. *As an engineer opening a PR*, CI starts within seconds and reports pass/fail in under 5 minutes.
2. *As an engineer running tests locally*, `pytest` and `npm test` both succeed without any GCP setup or env vars.
3. *As an engineer reading a CI failure*, the output points at the failing test by name and shows the assertion that broke — no hunting through logs.
4. *As a refactor-anxious engineer*, I can run the suite, see green, and know nothing in the affected surface area regressed.
5. *As a future engineer adding a feature*, the existing tests are my best documentation of the contracts I shouldn't break.

## Success metrics

- CI cold-cache run time: under 5 minutes (Phase 1: ~30s for 168 backend tests; Phase 2: +90s for Vitest + build + Playwright).
- Test count grows with every feature PR (loose target — observed 168 → 196 → 202 over three CI PRs).
- PR turnaround time doesn't measurably regress (CI parallelizes with review).
- Zero CI-blocked merges that turned out to be flaky.

## Open questions

- Coverage tooling (`pytest-cov` + `c8` for Vitest) — added if/when we want a metric. Not blocking.
- Visual regression testing (Playwright snapshots) — defer until UI churn slows.
