# Scenario: roadmap_sub_tabs_render

## Objective

Verify that the Roadmap page renders all 4 sub-tab buttons (Plan, Essays,
Scholarships, Colleges) and that clicking each non-Plan tab transitions the URL
to `?tab=<id>` as expected.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- The Plan tab button is expected to be present even though its content is broken
  (issue #123 affects content, not the tab button itself).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/roadmap`.
2. Assert URL contains `/roadmap`.
3. Wait up to 10 seconds for the "Plan" tab button to appear.
4. Assert all 4 tab buttons are visible: Plan, Essays, Scholarships, Colleges.
5. For each non-Plan tab (Essays, Scholarships, Colleges):
   a. Click the tab button.
   b. Assert the URL transitions to `?tab=<id>` (essays, scholarships, colleges).

## Expected outcomes

- All 4 tab buttons visible.
- URL updates to `?tab=essays`, `?tab=scholarships`, `?tab=colleges` on click.
- No crash or error boundary during tab transitions.

## Fixtures referenced

None.

## Known edge cases

- Plan tab content is broken (issue #123). The button renders correctly; only
  content is affected. The test asserts button presence but does NOT click Plan
  or assert Plan content (covered in `roadmap_plan_tab_renders` which is skipped).
- Tab labels from RoadmapPage.jsx lines 44-47: `plan`, `essays`, `scholarships`,
  `colleges`.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.1–§8.5 (tab navigation sub-step)
- Issue #123: Roadmap Plan tab JS error (blocks Plan content but not tab button)
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_sub_tabs_render`
- Iteration: 3
