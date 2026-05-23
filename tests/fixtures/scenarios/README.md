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
| [`discover_page_loads_with_university_grid`](./discover_page_loads_with_university_grid.md) | §5.1 | Yes (storageState) | `tests/playwright-prod/specs/discover.auth.spec.js` | 3 |
| [`discover_search_filters_by_name`](./discover_search_filters_by_name.md) | §5.2 | Yes (storageState) | `tests/playwright-prod/specs/discover.auth.spec.js` | 3 |
| [`discover_filter_dropdowns_present`](./discover_filter_dropdowns_present.md) | §5.3 | Yes (storageState) | `tests/playwright-prod/specs/discover.auth.spec.js` | 3 |
| [`discover_university_detail_six_tabs`](./discover_university_detail_six_tabs.md) | §5.5 | Yes (storageState) | `tests/playwright-prod/specs/discover.auth.spec.js` | 3 |
| [`launchpad_renders_categorized_list`](./launchpad_renders_categorized_list.md) | §7.1 + §7.2 | Yes (storageState) | `tests/playwright-prod/specs/launchpad.auth.spec.js` | 3 |
| [`launchpad_fit_modal_opens_with_bounds`](./launchpad_fit_modal_opens_with_bounds.md) | §7.3 | Yes (storageState) | `tests/playwright-prod/specs/launchpad.auth.spec.js` | 3 |
| [`roadmap_sub_tabs_render`](./roadmap_sub_tabs_render.md) | §8 (tab buttons) | Yes (storageState) | `tests/playwright-prod/specs/roadmap.auth.spec.js` | 3 |
| [`roadmap_essays_tab_lists_essays`](./roadmap_essays_tab_lists_essays.md) | §8.2 | Yes (storageState) | `tests/playwright-prod/specs/roadmap.auth.spec.js` | 3 |
| [`roadmap_scholarships_tab_renders`](./roadmap_scholarships_tab_renders.md) | §8.4 | Yes (storageState) | `tests/playwright-prod/specs/roadmap.auth.spec.js` | 3 |
| [`roadmap_colleges_tab_renders`](./roadmap_colleges_tab_renders.md) | §8.5 | Yes (storageState) | `tests/playwright-prod/specs/roadmap.auth.spec.js` | 3 |
| [`roadmap_counselor_chat_widget_present`](./roadmap_counselor_chat_widget_present.md) | §8.6 | Yes (storageState) | `tests/playwright-prod/specs/roadmap.auth.spec.js` | 3 |
| [`roadmap_plan_tab_renders`](./roadmap_plan_tab_renders.md) | §8.1 | Yes (storageState) | `tests/playwright-prod/specs/roadmap.auth.spec.js` | 3 (SKIPPED — #123) |
| [`cross_cutting_no_console_errors_authenticated_pass`](./cross_cutting_no_console_errors_authenticated_pass.md) | §11.1 | Yes (storageState) | `tests/playwright-prod/specs/cross-cutting.auth.spec.js` | 3 |
| [`cross_cutting_mobile_viewport_navbar_renders`](./cross_cutting_mobile_viewport_navbar_renders.md) | §11.3 | Yes (storageState) | `tests/playwright-prod/specs/cross-cutting.auth.spec.js` | 3 |
| [`pricing_page_renders_four_tiers`](./pricing_page_renders_four_tiers.md) | §9.1 | No | `tests/playwright-prod/specs/pricing.no-auth.spec.js` | 3 |

## When updating a scenario

- Update its `.md` file in the SAME commit as the matching spec change.
- If a scenario evolves (new step, new assertion, new edge case), reflect it here first — the doc is the spec.
- If you can't write a concrete observable assertion for a step, the step isn't well-defined yet.
