# Autonomous QA Loop — Operating Spec

> Spec for the autonomous test → find issues → fix → deploy → verify loop against the live Stratia Admissions product. Reference this doc from `/goal` commands instead of pasting the spec inline.

## Objective

Operate in an autonomous test → find issues → fix → deploy → verify loop against `stratiaadmissions.com` until all defined scenarios achieve a 100% pass rate. Continuously refine the test script as you learn, and systematically document scenarios as you go.

## Scope & Environment

- **Target environment:** `https://stratiaadmissions.com`
- **Test plan:** `docs/qa-browser-test-plan.md`
- **Test fixtures:** `tests/fixtures/`
- **Scenario documentation destination:** `tests/fixtures/scenarios/` (create if it doesn't exist)
- **Test user account:** `stratiaadmissions@gmail.com`
- **Test user password:** retrieve from Google Cloud Secret Manager, secret name `STRATIA_TEST_PASSWORD`. Fetch at runtime; never hardcode, log, print, echo, or commit the value. Do not include it in test output, error messages, GitHub issue bodies, or screenshots.

If the test plan is ambiguous or incomplete, surface this before inventing new scenarios.

## Data ownership model — read this first

Two categories of data exist in the system, and the agent treats them very differently:

- **Test-user-owned data (fully deletable, no approval needed):** Profiles, college fit data, essays, uploads, applications, saved lists, sessions, notifications, and any other records created by or scoped to `stratiaadmissions@gmail.com`. The agent has standing authorization to delete, reset, or otherwise destructively modify any of this data as needed for cleanup or scenario reset. No pause-and-ask required.
- **Shared/system data (strictly off-limits):** The university knowledgebase and any associated resources (university records, program catalogs, reference content, shared rubrics, etc.). The agent must never delete, modify, or otherwise alter this data, even if a scenario appears to call for it. If a scenario seems to require changing knowledgebase content, stop and surface it.

## Workflow

1. **Test** — Execute the test script against `stratiaadmissions.com` using Playwright or any other tooling you judge appropriate.
2. **Triage failures** — For each failure, determine whether it is (a) a test script bug, or (b) a real application defect.
3. **Refine the script** — Fix test script bugs, improve selectors, stabilize flaky tests, expand coverage where gaps are found, and re-run.
4. **Document the scenario** — As each scenario is exercised, add or update its documentation under `tests/fixtures/scenarios/` (see "Scenario documentation" below).
5. **Log real defects** — File application defects as GitHub issues in `cvsubs74/college-expert` with: reproduction steps, expected vs. actual behavior, environment details, screenshots/traces, severity, and a link to the corresponding scenario file.
6. **Hand off for fix & deploy** — The team lead owns merging the fix and deploying it. Tag or assign appropriately.
7. **Verify** — Once a fix is deployed, re-run the affected scenarios plus a regression pass on adjacent scenarios.
8. **Clean up test user data** — After every full pass of the suite, delete all test-user-owned data for `stratiaadmissions@gmail.com`. See "Test data cleanup" below.
9. **Loop** — Repeat until every scenario passes.

## Credential handling

- Retrieve the password from Google Cloud Secret Manager (`STRATIA_TEST_PASSWORD`) at runtime, using application default credentials or a service account with `roles/secretmanager.secretAccessor` on that secret.
- Fetch only when needed; do not cache the value to disk.
- Treat the value as sensitive throughout: redact from logs, never include in screenshots, never write to fixture files, never include in commits or issue descriptions.
- If retrieval fails (auth error, missing secret, permission denied), stop and surface the problem — do not fall back to prompting, hardcoding, or skipping authentication.

## Scenario documentation

- **Location:** `tests/fixtures/scenarios/`
- Each scenario gets its own file with a meaningful, descriptive label — not generic names like `scenario1` or `test_a`. Use names that describe the user journey or behavior under test. Examples: `applicant_creates_profile_and_submits_essay.md`, `counselor_reviews_pending_applications.md`, `student_uploads_transcript_pdf.md`.
- Use a consistent naming convention: lowercase, snake_case, descriptive verb-noun phrasing.
- Each scenario file should include: scenario name, objective, preconditions, step-by-step actions, expected outcomes, fixtures referenced, and any known edge cases.
- Profile samples must be labeled with the matching scenario name so they're trivially correlatable. If a scenario is `applicant_creates_profile_and_submits_essay`, the profile sample should be named `applicant_creates_profile_and_submits_essay.profile.json` (or equivalent extension) — same root name, just a different suffix.
- When a scenario evolves (new steps, new assertions, refined fixtures), update its documentation in the same commit as the test script change.

## Test data cleanup (mandatory after every pass)

- After every full pass of the suite — whether it ended in success, failure, or partial completion — delete all test-user-owned data for `stratiaadmissions@gmail.com`.
- Cleanup must include: profiles, college fit data, essays, applications, uploaded files, saved lists, transactions, sessions, cached state, notifications, audit-log artifacts the app exposes to the user, and any other user-scoped data the scenarios touched.
- Use whatever mechanism is most reliable — app delete endpoints, admin tooling, or direct DB/API calls — as long as the operation is scoped to `stratiaadmissions@gmail.com` only.
- **Never touch the university knowledgebase or its associated resources.** If a cleanup action would affect shared/system data, stop and surface it instead.
- Verify cleanup succeeded (re-query to confirm test-user data is gone; spot-check that the knowledgebase is intact) before starting the next pass. A pass does not count as complete until cleanup is verified.
- If cleanup fails or is partial, stop the loop and surface it — do not start the next pass against a dirty account.

## Authority & Autonomy

- Full authorization to choose and use tooling (Playwright, Cypress, custom scripts, etc.) — do not ask permission for tool choice or routine iteration decisions.
- Full authorization for destructive actions against test-user-owned data (profiles, college fit, essays, applications, etc.) — proceed without asking.
- Proceed autonomously on: test script edits, retries, selector changes, scenario refinement, scenario documentation, opening GitHub issues, re-running suites after deploys, and executing the cleanup step.

## Guardrails — Pause and surface before proceeding if you would

- Touch, modify, or delete any part of the university knowledgebase or its associated resources.
- Perform destructive actions outside the scope of `stratiaadmissions@gmail.com` (e.g., affecting other users' data or shared system data).
- Create production-visible side effects at scale (mass emails, payments, third-party API calls with cost or rate-limit risk).
- Modify application source code directly (that's the team lead's lane — you file issues, they fix).
- Disable, skip, or weaken a scenario to make it pass. If a scenario seems wrong, raise it; don't quietly remove it.
- Spend on paid services, sign up for new accounts, or change CI/CD configuration.
- Hardcode, log, print, or commit the test user password anywhere in the repo, test output, GitHub issues, or screenshots.

## Production-testing hygiene

- Use only the designated test account: `stratiaadmissions@gmail.com`.
- Avoid polluting analytics, transactional email, or payment systems — use sandbox modes where available.
- Cleanup (above) is the primary mechanism for keeping the test account clean; this hygiene section covers everything outside the test account's scope.

## Definition of Done

- 100% pass rate across all scenarios in the test plan.
- Every scenario is documented under `tests/fixtures/scenarios/` with a meaningful name, and its profile sample shares the same scenario name.
- All issues discovered during the loop are logged in GitHub (`cvsubs74/college-expert`), fixed, deployed, and verified.
- `stratiaadmissions@gmail.com` is in a clean, empty state at the end of the final pass — with the university knowledgebase and resources intact and unmodified.
- Final test script is committed and documented (how to run it, environment requirements including GCP Secret Manager setup for `STRATIA_TEST_PASSWORD`, known limitations, cleanup procedure including the knowledgebase exclusion).
- Summary report of: scenarios covered (with links to their docs), issues found and resolved, cleanup verifications, knowledgebase integrity confirmation, and any scenarios that required clarification.

## Reporting cadence

After each full pass of the suite, post a brief status update: pass/fail counts, new scenarios documented, new issues filed, issues verified fixed, cleanup status (including knowledgebase integrity check), and what you're doing next.
