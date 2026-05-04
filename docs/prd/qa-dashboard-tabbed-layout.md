# PRD — QA Dashboard Tabbed Layout

## Problem

The dashboard has grown into a long single-scroll page. Top to bottom:

1. SYSTEM HEALTH (sparkline + summary card)
2. ASK THE QA AGENT (chat)
3. FEEDBACK TO THE QA AGENT (input + active items)
4. RUN NOW (button)
5. RUN SCHEDULE (frequency + interval)
6. WHAT'S VALIDATED (coverage)
7. ISSUES CAUGHT & FIXED (resolved fixes)
8. RECENT RUNS (table)

Eight cards. Anyone landing on the page has to scroll past six of them to reach the runs table. Each card is useful but they're all competing for primary real estate. The right answer for "what's the system status?" is one tab away from "trigger a manual run", which is one tab away from "ask a question". They don't all need to share the same fold.

## Goal

Reorganize into a tabbed layout where each tab has a clear job-to-be-done, and the most-used view (Overview) lands first.

## Tabs

```
┌─────────────────────────────────────────────────────────────┐
│  QA Agent                              [recent-N pass pill] │
│  Internal — synthetic monitoring runs                       │
│                                                             │
│  [ Overview ]  [ Runs ]  [ Ask ]  [ Steer ]                │
├─────────────────────────────────────────────────────────────┤
│  (active tab content)                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1. Overview (default)
The "is the system working?" view. Lands here on first visit.
- System Health card (existing — narrative + recent-N + 7d/30d + surfaces)
- 30-day sparkline (kept here — visual context for the headline)
- Coverage card (what's validated)
- Resolved-issues card (what's been fixed)
- A prominent **Run now** button up top (most common action, shouldn't require switching tabs)

### 2. Runs
The "what's been tested?" view. Single-purpose.
- Recent Runs table (existing component, full width)
- Filter chips: All / Running / Failures (small UX add — surface failures fast)

### 3. Ask
The "I want to ask a question" view.
- Chat panel (full-width, taller — gets room to breathe instead of being squeezed)

### 4. Steer
The "I want to influence the agent" view.
- Feedback panel (top — the active items + input box)
- Run Schedule editor (bottom — operational, less frequent)

## Non-goals

- Customer-facing redesign (still internal admin only).
- Data-shape changes — every component already exists; this is layout-only.
- Tab persistence across sessions — URL-based tab state is enough; no localStorage.

## Success criteria

- First view of the page is a single screen of useful info (no scroll required for Overview on a typical 1080p screen).
- Tab choice persists in the URL (`?tab=runs`) so refreshing or sharing a link keeps the user on the right tab.
- Recent-N pill stays visible across all tabs (in the header) so health context never disappears.
- Run now button is reachable without changing tabs (header on Overview).
- No regression on existing components — they render the same just inside tab containers.

## Constraints

- Reuses every existing component as-is. No prop changes.
- URL state via React Router query param (`?tab=`).
- Mobile: stacks tabs into a select dropdown if width is constrained.
- Lazy mount: each tab only mounts its content when active (saves initial-render Gemini calls — ChatPanel, ExecutiveSummary etc. each fetch on mount).

## Test plan

- Component test: `<QaRunsListPage />` renders Overview content by default; clicking each tab swaps the content; URL updates with `?tab=`.
- Visual: each tab fits in a typical viewport without scroll for the empty/normal cases.
- Manual: refresh on `?tab=runs` lands on Runs tab.
