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

| Scenario | Test plan section | Auth required? | Spec file |
|---|---|---|---|
| [`pre_flight_landing_renders`](./pre_flight_landing_renders.md) | §3 + §4.1 | No | `tests/playwright-prod/specs/no-auth.spec.js` |
| [`unauthenticated_profile_redirect`](./unauthenticated_profile_redirect.md) | §4.6 | No | `tests/playwright-prod/specs/no-auth.spec.js` |
| [`public_resources_page_renders`](./public_resources_page_renders.md) | §10 | No | `tests/playwright-prod/specs/no-auth.spec.js` |

Iteration 2+ scenarios (authenticated paths — Profile upload, Discover, Launchpad, Roadmap, Payment) will be added once the OAuth `storageState` capture infrastructure lands.

## When updating a scenario

- Update its `.md` file in the SAME commit as the matching spec change.
- If a scenario evolves (new step, new assertion, new edge case), reflect it here first — the doc is the spec.
- If you can't write a concrete observable assertion for a step, the step isn't well-defined yet.
