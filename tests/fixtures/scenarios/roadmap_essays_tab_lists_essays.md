# Scenario: roadmap_essays_tab_lists_essays

## Objective

Verify that the Roadmap Essays tab renders the EssayDashboard component with essay
stats visible (Total Essays, Not Started, Drafts, In Review, Finalized counts)
and that at least one school's essay collection is listed when the account has
saved schools with essay prompts.

## Preconditions

- User is authenticated as `stratiaadmissions@gmail.com`.
- Account may have saved schools with essay tracker entries. Prior run (2026-05-23)
  showed 10 essays across 2 schools: UC Application UCSB (8 prompts) + Emory (2).

## Step-by-step actions

1. Navigate to `https://stratiaadmissions.com/roadmap?tab=essays`.
2. Assert URL contains `/roadmap`.
3. Wait up to 15 seconds for the EssayDashboard to render (embedded mode).
4. Assert at least one of these stat labels is visible: "Total Essays", "Not Started",
   "In Review", "Finalized".
5. If the account has essays: assert at least one school heading or essay entry
   is visible in the main content area.
6. If the account has no essays: assert an empty-state UI renders (no crash, no
   Connection Error card).
7. Assert no "Connection Error" card is visible.

## Expected outcomes

- EssayDashboard renders without error boundary.
- Essay stats labels visible.
- School essay collections listed (if account has essay data) OR empty state renders.
- No "Connection Error" text visible.

## Fixtures referenced

None. Live production data.

## Known edge cases

- If the account was reset before this run, essays may be absent. The test handles
  the empty state gracefully (no crash assertion).
- Prior run confirmed: Essays tab rendered correctly while Plan tab failed. The tab
  click from Roadmap home transitions the URL correctly.
- The EssayDashboard is rendered in embedded mode per RoadmapPage.jsx line 111.

## Related

- Test plan: `docs/qa-browser-test-plan.md` §8.2
- Spec: `tests/playwright-prod/specs/roadmap.auth.spec.js` → `roadmap_essays_tab_lists_essays`
- Iteration: 3
