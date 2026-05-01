# Design: Roadmap Consolidation

Status: Draft
Owner: Engineering
Last updated: 2026-04-30
Related PRD: [docs/prd/roadmap-consolidation.md](../prd/roadmap-consolidation.md)

## Design principles

- **No data migration.** Existing Firestore subcollections under `/users/{uid}/` (`roadmap_tasks`, `essay_tracker`, `scholarship_tracker`, `college_list`, `aid_packages`) are already in production and authoritative. The consolidation is a view-layer change plus one read-aggregation endpoint.
- **Surface, don't rebuild.** The `notes` field exists today on every relevant collection; we expose it. The semester templates exist today in [planner.py](../../cloud_functions/counselor_agent/planner.py); we keep them.
- **Reversible decisions.** The new route is additive (`/roadmap`); old routes are aliased via redirects. Rolling back means re-routing the nav and removing one new endpoint.
- **Each tab owns its data fetch.** The four tabs each call the existing per-collection endpoints they already use. The new `/work-feed` endpoint exists only to power the "This Week" focus card on the Plan tab.

## Information architecture

```
/roadmap                            (new top-level route)
  Header: "Roadmap" + grade/semester chip
  Tab strip: [ Plan | Essays | Scholarships | Colleges ]

  Plan tab (default)
    └── ThisWeekFocusCard           (new component, calls /work-feed)
    └── RoadmapView                 (lifted from CounselorPage, unchanged)
            grade/semester now computed, not hardcoded

  Essays tab
    └── EssayDashboard              (lifted from /essays, /progress)
            with new inline NotesAffordance on every row

  Scholarships tab
    └── ScholarshipTracker          (lifted from /progress)
            with new inline NotesAffordance on every row

  Colleges tab
    └── ApplicationsPage            (lifted from /applications)
            with new inline NotesAffordance on every college card
```

Tab state lives in the URL: `/roadmap?tab=plan|essays|scholarships|colleges`. Default is `plan`.

## Frontend

### New / lifted components

- `frontend/src/pages/RoadmapPage.jsx` — new top-level page. Owns the tab strip, reads `?tab=` from URL, renders the active tab.
- `frontend/src/components/roadmap/ThisWeekFocusCard.jsx` — new. Calls `/work-feed`, renders top items with notes affordance and source-collection icons.
- `frontend/src/components/roadmap/NotesAffordance.jsx` — new. Reusable inline notes editor (icon → expands → textarea → saves on blur). Takes `{ collection, itemId, value, onSave }`.
- Existing components reused as-is or with minimal changes:
  - `frontend/src/components/counselor/RoadmapView.jsx` — keep, drop the parent `<CounselorPage>` chrome (chat sidebar moves out in M2; in M1 the sidebar simply isn't rendered inside the new page).
  - `frontend/src/pages/EssayDashboard.jsx` — keep. Render with `embedded={true}` prop so it omits its standalone-page chrome (it already has this prop based on the existing dual-route pattern).
  - `frontend/src/pages/ScholarshipTracker.jsx` — keep. Same embedded-mode pattern.
  - `frontend/src/pages/ApplicationsPage.jsx` — keep. Add embedded-mode if missing.

### Route changes

In [frontend/src/App.jsx](../../frontend/src/App.jsx):

- Add `<Route path="/roadmap" element={<ProtectedRoute><RoadmapPage /></ProtectedRoute>} />`.
- Replace `<Route path="/counselor">` with `<Navigate to="/roadmap?tab=plan" replace />`.
- Replace `<Route path="/progress">` with `<Navigate to="/roadmap?tab=essays" replace />`.
- Replace `<Route path="/essays">` with `<Navigate to="/roadmap?tab=essays" replace />`.
- Replace `<Route path="/applications">` with `<Navigate to="/roadmap?tab=colleges" replace />`.
- Update `navLinks` to a single "Roadmap" entry pointing at `/roadmap`.

### Grade & semester resolution

`RoadmapView` currently receives a hardcoded `'11th Grade'`. Replace with:

1. `RoadmapPage` reads `profile.grade_level` from the existing profile fetch.
2. `RoadmapPage` computes current semester client-side from `Date.now()`:
   - Aug-Dec → `fall`
   - Jan-May → `spring`
   - Jun-Jul → `summer`
3. Passes `{ gradeLevel, semester }` down to `RoadmapView`.
4. `RoadmapView` calls `fetchStudentRoadmap(userEmail, gradeLevel, semester)` — `semester` is a new optional argument. The backend uses it to pick `<grade>_<semester>` template.

If `profile.grade_level` is missing, default to `'11th Grade'` and surface a warning toast prompting the student to complete their profile.

### Notes affordance behavior

```
[icon]          ← collapsed, shows count if notes exist
[icon] click → expands inline:
  ┌──────────────────────────┐
  │ <textarea>               │  ← autofocus
  └──────────────────────────┘
  saves on blur (or Cmd/Ctrl+Enter)
```

Persistence: a single `POST /update-notes` call (see backend section). Optimistic UI update; revert + toast on failure. Debounce blur events at 500ms to absorb rapid focus changes.

## Backend

The split follows the role pattern already established in the codebase: `counselor_agent` is the read-side aggregator (its env.yaml already lists `PROFILE_MANAGER_URL` and `KNOWLEDGE_BASE_UNIVERSITIES_URL` as data sources). `profile_manager_v2` and `knowledge_base_manager_universities` are simple data managers. Aggregated read endpoints belong in `counselor_agent`; writes to user documents stay in `profile_manager_v2`.

### `/work-feed` endpoint (new) — on `counselor_agent`

Lives in [cloud_functions/counselor_agent/main.py](../../cloud_functions/counselor_agent/main.py). It composes the unified focus list from multiple sources without owning any of their data.

**Request**
```
GET /work-feed?user_email=...&limit=8
```

**Response**
```json
{
  "items": [
    {
      "id": "<stable id>",
      "source": "roadmap_task" | "essay" | "scholarship" | "college_deadline",
      "title": "Draft personal statement",
      "subtitle": "Personal Statement · Common App",     // optional
      "due_date": "2026-07-15",                          // ISO date
      "days_until": 3,
      "urgency": "overdue" | "urgent" | "soon" | "later",
      "university_id": "stanford",                        // optional
      "university_name": "Stanford University",           // optional
      "status": "pending|draft|...",                      // source-specific
      "notes": "...",                                     // current notes value
      "deep_link": "/roadmap?tab=essays&essay_id=..."     // where clicking lands
    }
  ]
}
```

**Implementation (where each piece of data comes from)**
- **Roadmap tasks, essays, scholarships, college list**: HTTP-call `profile_manager_v2`'s existing endpoints (`/get-tasks` or its equivalent on profile_manager_v2, `/get-essay-tracker`, `/get-scholarship-tracker`, `/get-college-list`). Fetch in parallel — these are independent reads. If a bundling endpoint is added later in profile_manager_v2 to return all four in one round trip, swap to it; for M1 the parallel calls are fine.
- **College deadlines**: use `counselor_agent`'s existing `fetch_aggregated_deadlines()` ([counselor_agent/counselor_tools.py](../../cloud_functions/counselor_agent/counselor_tools.py)) directly — no HTTP call needed since the function lives in this same Cloud Function. Internally that helper already calls `profile_manager_v2` for the college list and `knowledge_base_manager_universities` for per-university deadlines.
- Filter each source to active items (status != completed/final/received).
- Normalize all sources into the response shape above.
- Sort by `due_date` ascending; items without `due_date` go to the bottom.
- Truncate to `limit`.
- Compute `days_until` and `urgency` server-side so all clients agree on what "urgent" means. Suggested thresholds: `overdue` (< 0), `urgent` (≤ 7), `soon` (≤ 30), `later` (> 30).

**Why this lives in `counselor_agent`, not `profile_manager_v2`**
- The pattern is already established: `counselor_agent` is the BFF for the Roadmap surface and is the only function with simultaneous read access to user data (via profile_manager_v2) and university data (via the knowledge base). Putting the aggregation here keeps `profile_manager_v2` focused on user-document CRUD and avoids it sprouting cross-domain logic.
- The deadline-aggregation logic is already here. `/work-feed` reuses it directly, no cross-function call for deadlines.

**Latency mitigations**
- Deploy `counselor_agent` with `--min-instances=1` (matching the [deploy.sh:305-309](../../deploy.sh) pattern used for the hybrid ADK agent) so the focus card never lands on a cold start.
- Add a small per-instance in-memory cache inside `counselor_agent` for the per-user work-feed payload, with a short TTL (suggested: 60-120 seconds). Work-feed reads happen often (every Roadmap-page load, tab switches); the underlying data changes only when the user mutates state. Cache misses on stale data are tolerable.
- The cache is best-effort, in-memory, and intentionally simple — not a correctness boundary. We do not need a distributed cache for M1.

### `/update-notes` endpoint (new) — on `profile_manager_v2`

Lives in [cloud_functions/profile_manager_v2/main.py](../../cloud_functions/profile_manager_v2/main.py). Notes are direct writes to user-owned Firestore documents, so the data manager owns this endpoint.

```
POST /update-notes
Body: {
  user_email: string,
  collection: "roadmap_tasks" | "essay_tracker" | "scholarship_tracker"
              | "college_list" | "aid_packages",
  item_id: string,
  notes: string
}
```

Writes only the `notes` field on the targeted document. Returns 200 with `{ ok: true, updated_at: <ts> }`.

Alternative considered: extend each existing per-collection update endpoint (`update-essay-progress`, `update-scholarship-status`, etc.) with a `notes` field. Slightly less new code, but spreads notes-writing logic across endpoints — easier to introduce inconsistency. The unified endpoint is the cleaner choice.

### `counselor_agent` other changes

- `POST /roadmap` accepts an optional `semester` field. When omitted, server computes it from `datetime.now()` using the same fall/spring/summer rule as the client. (Client and server both compute it so both can render consistent labels independently.)
- When `grade_level` is not provided, fetch it from the user's profile via the existing `profile_manager_v2` call (already in place via `counselor_tools.get_student_profile`).
- No changes to the templates themselves.

## Routing & redirects

All redirects use `<Navigate replace>` so the browser's back button skips the legacy URL. Query params from the legacy URL pass through unchanged where they make sense (e.g., `?school=stanford` survives the redirect from `/applications`).

## Phasing

### M1 (target: one PR per area)

| PR | Scope |
|---|---|
| 1 | Backend: `GET /work-feed` on `counselor_agent`. Composes parallel calls to `profile_manager_v2` (tasks/essays/scholarships/college list) + reuses local `fetch_aggregated_deadlines`. Adds 60-120s per-user in-memory cache. Bump `counselor_agent` deploy to `--min-instances=1` to match the hybrid-agent pattern. |
| 2 | Backend: `POST /update-notes` on `profile_manager_v2`. Single write endpoint covering all five collections that already have a `notes` field. Tests against Firestore emulator. |
| 3 | Backend: `counselor_agent` semester computation + profile-based grade lookup on `/roadmap`. |
| 4 | Frontend: `RoadmapPage` skeleton with tab strip. Lift in `EssayDashboard`, `ScholarshipTracker`, `ApplicationsPage` in embedded mode. Add nav entry. |
| 5 | Frontend: `ThisWeekFocusCard` component on Plan tab. Wire to `counselor_agent` `/work-feed`. |
| 6 | Frontend: `NotesAffordance` component. Wire into all four tabs against `/update-notes`. |
| 7 | Frontend: redirects from `/counselor`, `/progress`, `/essays`, `/applications`. Remove old nav entries. |

PRs 1 and 2 can land independently of frontend. PRs 3-6 sequence on top of each other.

### M2 (separate effort)

- `artifact_ref` resolution from generic template tasks → essay/scholarship rows.
- Counselor chat as a floating launcher.
- Manual task creation UI on the Plan tab.
- Per-college expandable mini-dashboard within the Colleges tab.

## Testing

### Backend
- Unit tests for `/work-feed` aggregation logic — at minimum: empty user, single-source user, all-sources user, urgency thresholds at boundaries.
- Unit tests for `/update-notes` — happy path per collection, unknown collection (400), nonexistent item (404).
- Existing bash integration tests under `test_*.sh` get a new `test_roadmap_consolidation.sh` covering the two new endpoints end-to-end.

### Frontend
- The codebase has no automated frontend test suite today. Manual verification per the dev-server-and-browser convention:
  - Open `/roadmap`, see Plan tab with focus card and timeline.
  - Switch tabs; URL `?tab=` updates.
  - Old routes redirect correctly (test each).
  - Notes affordance: write notes on each tab, refresh, notes persist.
  - Profile with `grade_level` missing → default + warning toast.

### Smoke tests on staging
- Verify `/work-feed` against a real user with mixed-status items in each collection.
- Verify redirects don't loop or strip query params unexpectedly.

## Risks

- **Cold-start latency on the focus card**. `/work-feed` lands on `counselor_agent` and fans out to `profile_manager_v2`. If either is at zero instances, the focus card waits on a cold start (~5–15s for Python Cloud Functions with Gemini deps in `counselor_agent`). Mitigation: deploy `counselor_agent` with `--min-instances=1` (matching the hybrid agent), and add a 60–120s per-instance work-feed cache inside `counselor_agent`. `profile_manager_v2` cold starts are shorter and amortized across many call sites; not a focus-card concern in practice.
- **Fan-out call count**. `/work-feed` makes 4+ parallel HTTP calls into `profile_manager_v2`. That's fine at expected user volumes but worth profiling once live; if it turns into hot traffic on `profile_manager_v2`, add a single `/get-trackers` bundling endpoint there and switch to one call.
- **Embedded-mode pages**. `EssayDashboard`, `ScholarshipTracker`, `ApplicationsPage` may have layout assumptions that break inside a tab container (e.g., they each expect to control page-level scroll). M1 PR #4 needs to verify each renders cleanly inside a tab; if not, light refactoring is in scope for that PR.
- **Bookmarks and external links**. Old routes that other systems link to (emails from earlier Stripe webhooks, support docs) will redirect — but only as long as we keep the redirect rules. The PRD success metric tracks legacy traffic decay.
- **Tab-state vs. browser back**. Switching tabs pushes URL query updates. We use `replace` for tab clicks (not pushState) so back doesn't have to traverse every tab visit.

## Open questions for engineering

- `/work-feed` endpoint name: does the existing convention prefer kebab-case (`work-feed`) or snake-case (`work_feed`) in URLs? Inspect existing routes in `counselor_agent/main.py` and match.
- Cache TTL on the work-feed payload: 60-120s is a starting point. Tune based on observed staleness complaints once the feature is live.
- "This Week" notes affordance: do we save notes to the source-collection's document, or to a new "focus-card" overlay? Decision: source-collection. The focus card is a view; the source is canonical. Already reflected in the `/update-notes` design above.
- `/get-trackers` bundling endpoint on `profile_manager_v2` — do we add it preemptively in M1, or wait until profiling shows fan-out is hot? Default: wait.
