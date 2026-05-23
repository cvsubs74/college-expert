# tests/fixtures/scenarios — Autonomous QA loop scenario catalog

Per `docs/qa-autonomous-loop-spec.md`, each scenario the QA loop executes has a
markdown file here documenting: objective, preconditions, steps, expected
outcomes, fixtures referenced, and known edge cases.

## Naming convention

- **lowercase, snake_case, descriptive verb-noun phrasing**
- No generic names (`scenario1`, `test_a`) — names describe the user journey or behavior under test
- Profile-sample fixtures share the same root name as the scenario (e.g.
  `applicant_creates_profile_and_submits_essay.md` ↔
  `tests/fixtures/profile-samples/applicant_creates_profile_and_submits_essay.profile.json`)

## Catalog

| Scenario | Test plan section | Auth required? | Spec file | Iteration |
|---|---|---|---|---|
| [`pre_flight_landing_renders`](./pre_flight_landing_renders.md) | §3 + §4.1 | No | `tests/playwright-prod/specs/no-auth.spec.js` | 1 |
| [`unauthenticated_profile_redirect`](./unauthenticated_profile_redirect.md) | §4.6 | No | `tests/playwright-prod/specs/no-auth.spec.js` | 1 |
| [`public_resources_page_renders`](./public_resources_page_renders.md) | §10 | No | `tests/playwright-prod/specs/no-auth.spec.js` | 1 |
| [`capture_oauth_storage_state`](./capture_oauth_storage_state.md) | §13.2 | Interactive | `tests/playwright-prod/specs/capture-auth.spec.js` | 2 |
| [`profile_tab_renders_five_tabs`](./profile_tab_renders_five_tabs.md) | §6.1 | Yes (storageState) | `tests/playwright-prod/specs/profile.auth.spec.js` | 2 |
| [`profile_upload_pdf_processes_to_completion`](./profile_upload_pdf_processes_to_completion.md) | §6.2 | Yes (storageState) | `tests/playwright-prod/specs/profile.auth.spec.js` | 2 |
| [`profile_upload_unsupported_format_rejects`](./profile_upload_unsupported_format_rejects.md) | §6.9 | Yes (storageState) | `tests/playwright-prod/specs/profile.auth.spec.js` | 2 |

Iteration 3+ scenarios (Discover, Launchpad, Roadmap, Payment) will be added in subsequent iterations.

## When updating a scenario

- Update its `.md` file in the SAME commit as the matching spec change.
- If a scenario evolves (new step, new assertion, new edge case), reflect it here first — the doc is the spec.
- If you can't write a concrete observable assertion for a step, the step isn't well-defined yet.
