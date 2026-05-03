# PRD: /roadmap page skeleton

Status: Approved (shipped in PR #6, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

The Roadmap consolidation needs a single landing page with four inner tabs (Plan, Essays, Scholarships, Colleges) that subsume the four legacy routes. Before any tab content can be wired up, the container itself needs to exist: a route, a tab strip, URL-driven tab state, and the protected-route gating.

## Goals

- One new route `/roadmap` that renders a tab strip + the active tab's content.
- Tab state lives in the URL (`?tab=plan|essays|scholarships|colleges`) so deep links work and the browser back button navigates between tabs.
- Each tab embeds the existing page component for that surface (in "embedded" mode — no double headers).
- Default landing tab is Plan.
- Header shows the student's grade + semester chip (data flows in from the resolver shipped in PR #5).

## Non-goals

- The actual content of each tab beyond rendering the existing component. Per-tab features (focus card, notes affordance, mini-dashboard, manual-task-creation) ship as their own PRs.
- Mobile-specific tab UI. Same horizontal tab strip on every breakpoint for now.
- Persisting last-active-tab across sessions. URL is the source of truth.

## Users

- Every student loading `/roadmap` from the redirected nav links or a direct deep link.

## User stories

1. *As a student*, I see a header that names my grade and semester so I know the roadmap is talking to me, not to a generic 11th grader.
2. *As a student*, the tab strip is always visible and tells me what tab I'm on with a clear active-state visual.
3. *As a student clicking a tab*, the URL updates so I can copy a link straight to "my Essays tab" and have it land back there next time.
4. *As a student using browser back*, going back from Essays returns me to the previously viewed tab, not to the home page.

## Success metrics

- All four tabs render without errors against a real user profile.
- URL `?tab=` survives page refresh and is the source of truth.
- The legacy embed-mode props on EssayDashboard / ScholarshipTracker / ApplicationsPage carry through unchanged.

## Open questions

- None at backfill time.
