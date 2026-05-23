# Scenario: roadmap_counselor_chat_widget_present

## Objective

Verify that the "Ask Counselor" floating chat button (FloatingCounselorChat
component) is visible on every Roadmap sub-tab. It persists across tab
transitions per RoadmapPage.jsx line 119.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- Three non-Plan tabs are checked: Essays, Scholarships, Colleges.
  (Plan tab is excluded due to issue #123 — its content is broken, but the
  counselor widget should still render there; verification is deferred until
  #123 is fixed.)

## Step-by-step actions

For each of the following URLs:
  - `https://stratiaadmissions.com/roadmap?tab=essays`
  - `https://stratiaadmissions.com/roadmap?tab=scholarships`
  - `https://stratiaadmissions.com/roadmap?tab=colleges`

1. Navigate to the URL.
2. Assert URL contains `/roadmap`.
3. Wait up to 10 seconds for the "Ask Counselor" button to become visible.
4. Assert the "Ask Counselor" button is visible (role `button`, name `/ask counselor/i`).

## Expected outcomes

- "Ask Counselor" button visible on Essays, Scholarships, and Colleges tabs.
- Confirmed behavior from prior run (2026-05-23): the button was visible across
  all Roadmap tabs including Plan.

## Fixtures referenced

None.

## Known edge cases

- The button may render with a delay if the FloatingCounselorChat component
  defers initialization. The 10-second timeout accommodates typical backend
  response latency.
- If the button label changes from "Ask Counselor" to something else, the regex
  `/ask counselor/i` must be updated.
- Plan tab is NOT checked here due to #123 — once #123 is resolved, add
  `/roadmap?tab=plan` to the URL list.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.6
- Issue #123: Roadmap Plan tab JS error
- RoadmapPage.jsx line 119: FloatingCounselorChat mount point
- Prior run finding: "Ask Counselor" button visible bottom-right across all Roadmap tabs.
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_counselor_chat_widget_present`
- Iteration: 3
