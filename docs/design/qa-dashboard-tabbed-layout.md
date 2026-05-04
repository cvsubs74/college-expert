# Design — QA Dashboard Tabbed Layout

Companion to [docs/prd/qa-dashboard-tabbed-layout.md](../prd/qa-dashboard-tabbed-layout.md).

## Component graph

```
QaRunsListPage  (state: activeTab from URL ?tab=)
├── DashboardHeader (always visible)
│   ├── Title + subtitle
│   ├── recent-N pass-rate pill (shared component)
│   └── Sparkline (compact — moved into header)
│
├── TabBar
│   └── [Overview] [Runs] [Ask] [Steer]
│
└── tab content (lazy)
    ├── Overview tab
    │   ├── ExecutiveSummary
    │   ├── CoverageCard
    │   ├── ResolvedIssuesCard
    │   └── (CTA: Run now button at top)
    ├── Runs tab
    │   └── RunsTable + filter chips
    ├── Ask tab
    │   └── ChatPanel (full-width)
    └── Steer tab
        ├── FeedbackPanel
        ├── ScheduleEditor
        └── RunNowPanel (also lives here for completeness)
```

## URL state

`/qa-runs?tab=overview` (default) | `?tab=runs` | `?tab=ask` | `?tab=steer`

Implemented with `useSearchParams` from `react-router-dom`. Default to `overview` when missing or invalid.

## Tab switching behavior

- Clicking a tab updates the URL via `setSearchParams({ tab })` so refresh/share preserves state.
- Each tab's content is rendered with `{activeTab === 'overview' && <Overview />}` so unmounted tabs don't fetch on a refresh — saves on Gemini-billable summary calls.
- Sticky tab bar so it stays visible while scrolling within a tab.

## Run-now placement

- **Overview tab**: a compact "Run now" call-to-action at the very top. This is the most-clicked button by the admin; it should not require switching to a different tab to reach.
- **Steer tab**: full RunNowPanel with description text (same as today). Useful as the deliberate-action surface.

Both buttons feed into the same flow (preview → confirm → run); they're just different entry points.

## Compact sparkline in header

The sparkline currently uses ~240×40 px and sits to the right of the title. It works well as a header element. Move it into the persistent header so the visual stays available across tabs.

The recent-N pill (the "100% green" number) lives in the same header next to the sparkline.

## Files

**New (frontend):**
- `frontend/src/components/qa/DashboardHeader.jsx` — title + subtitle + sparkline + pill.
- `frontend/src/components/qa/TabBar.jsx` — tab buttons; reads/writes `?tab=`.
- `frontend/src/__tests__/TabBar.test.jsx`

**Modified (frontend):**
- `frontend/src/pages/QaRunsListPage.jsx` — Lift `activeTab` from URL; route content through `<TabBar>` switch.
- (No changes to ExecutiveSummary, CoverageCard, ResolvedIssuesCard, ChatPanel, FeedbackPanel, ScheduleEditor, RunNowPanel, RunsTable — they render unchanged inside tab containers.)

## Trade-offs

**Why not a side-nav (left rail)?** Side-nav scales better past 5 tabs but consumes horizontal real estate; the dashboard's content is wide. Top tabs match the existing visual language.

**Why URL state instead of just useState?** Refreshing should keep you on the same tab; sharing a link to a specific tab works.

**Why lazy-mount instead of always-mount?** ExecutiveSummary, ChatPanel each call `/summary` and friends on mount. Every tab having mount-time fetches multiplies Gemini cost without value when those tabs aren't visible.

**Why no animation between tabs?** Browser-native tab UX is instant. Adding a slide transition costs perceived performance for no functional gain.

**Why keep the sparkline always-visible?** It's the at-a-glance signal even when the user is on the Runs or Steer tab — they shouldn't need to navigate back to Overview to know if the system is healthy.

## Mobile (out of scope but planned)

If width < 640px, render the tabs as a `<select>` element instead of a tab strip. Doesn't ship in v1 (admin dashboard is desktop-first) but the TabBar component should be structured so this swap is a small follow-up.
