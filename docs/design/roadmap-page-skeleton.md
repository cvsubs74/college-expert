# Design: /roadmap page skeleton

Status: Approved (shipped in PR #6, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/roadmap-page-skeleton.md](../prd/roadmap-page-skeleton.md)

## Component layout

```
RoadmapPage (frontend/src/pages/RoadmapPage.jsx)
├── PageHeader  (title "Roadmap" + grade/semester chip)
├── TabStrip    ([Plan] [Essays] [Scholarships] [Colleges])
└── <active tab content>
        Plan         → RoadmapView (lifted from CounselorPage)
        Essays       → EssayDashboard      (embedded={true})
        Scholarships → ScholarshipTracker  (embedded={true})
        Colleges     → ApplicationsPage    (embedded={true})
```

## URL state

```
/roadmap?tab=plan        ← default if no ?tab present
/roadmap?tab=essays
/roadmap?tab=scholarships
/roadmap?tab=colleges
```

`tab` is read with `useSearchParams()` from `react-router-dom`. Tab clicks call `setSearchParams({ tab: nextTab }, { replace: true })`. Using `replace` (not `push`) for tab clicks means the back button doesn't have to traverse every tab visit — it returns to wherever the user came from before they landed on `/roadmap`.

A deep link with an unknown `tab` value falls back to `plan`.

## Route registration

In `frontend/src/App.jsx`:

```jsx
<Route
  path="/roadmap"
  element={<ProtectedRoute><RoadmapPage /></ProtectedRoute>}
/>
```

`ProtectedRoute` is the existing wrapper that redirects unauthenticated users to `/`.

## Header chip

```
┌──────────────────────────────────────────┐
│  Roadmap                                 │
│  ┌────────────────┐                      │
│  │ Junior · Spring│                      │
│  └────────────────┘                      │
└──────────────────────────────────────────┘
```

The chip text reads `<grade> · <semester>` from the profile + the same client-side semester computation the resolver uses (kept in sync deliberately so the label matches what the backend chose).

If the profile lacks `graduation_year`, the chip shows "Set your graduation year" with a link to the profile editor instead of guessing.

## Embedded mode

`EssayDashboard`, `ScholarshipTracker`, and `ApplicationsPage` already accepted an `embedded` prop from a prior dual-route pattern. Passing `embedded={true}` strips their standalone-page chrome (page title, breadcrumb, full-bleed background) so they nest cleanly inside the tab.

## Auth bypass for E2E

The `AuthContext` reads `localStorage.__E2E_TEST_USER__` when `import.meta.env.MODE !== 'production'` and uses it as the signed-in user. This is the hook Playwright tests use (PR #17). The bypass is statically eliminated from production builds by Vite's tree-shaking on `MODE === 'production'`.

## Testing strategy

- **Unit (Vitest)** in `frontend/src/__tests__/RoadmapPage.test.jsx`:
  - Renders Plan tab by default.
  - Tab click updates `?tab=` and renders the right component.
  - Header chip reads from profile.
- **E2E (Playwright)** in `frontend/tests-e2e/roadmap.spec.js`:
  - Lands on /roadmap, sees the Roadmap header.
  - Clicks each tab; URL updates.
  - Refresh on a non-default tab keeps the user on that tab.

## Risks

- **Embedded-mode layout drift**: each lifted page may have edge-case layout assumptions (full-bleed scroll, etc.) that misbehave inside a tab container. Mitigation: this PR's manual verification covered each tab; subsequent PRs are small enough that any regression would be obvious.
- **Tab strip vs. nav focus**: keyboard tab order should reach the tab strip after the page header; verified manually.
- **Active tab visual on long names**: not a problem yet because all four labels are one short word each.

## Alternatives considered

- **Stack the four pages vertically with anchor links instead of tabs.** Rejected per the user's stated preference (`feedback_ui_tabs_preference.md`): consolidations get inner tabs, not single scrolling pages.
- **Use a routing library's nested-route mechanism for tab content.** Rejected: react-router v7 nested routes with `<Outlet />` would work but add no value over `?tab=` for our four flat tabs. Search-param approach is simpler.
- **Persist last-active-tab in localStorage.** Rejected: URL state is enough; a saved tab can fight the user's deep links.
