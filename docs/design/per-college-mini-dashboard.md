# Design: Per-college mini-dashboard

Status: Approved (shipped in PR #14, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/per-college-mini-dashboard.md](../prd/per-college-mini-dashboard.md)

## Component

`frontend/src/components/colleges/CollegeMiniDashboard.jsx` — the expanded body. Lives inside the existing college card on `ApplicationsPage.jsx` (the Colleges tab content).

## Card layout

```
┌─────────────────────────────────────────────────────────┐
│  MIT                                              [▼]   │  ← collapsed (existing card)
└─────────────────────────────────────────────────────────┘

clicked ↓

┌─────────────────────────────────────────────────────────┐
│  MIT                                              [▲]   │
│  ───────────────────────────────────────────────────────│
│  Deadline      Jan 5, 2027 · Regular Decision           │
│  Essays        2 supplements                            │
│                  • "Why MIT?" — drafted                 │
│                  • "Maker's portfolio" — not started    │
│  Scholarships  1 match                                  │
│                  • Presidential Scholarship — eligible  │
│  Progress      ████████░░░░░░  40%                      │
│  Notes         [📝]                                      │
└─────────────────────────────────────────────────────────┘
```

## Data sources

Everything the mini-dashboard renders is already fetched by the parent `ApplicationsPage`:

- **Deadline + type** — from `/get-college-list` (each college row has `deadline` and `deadline_type`).
- **Essays** — from `/get-essay-tracker`. Filtered to `essays.where(university_id == card.university_id)`. Each essay has `status` (`not_started | drafted | reviewing | final`).
- **Scholarships** — from `/get-scholarship-tracker`. Filtered to scholarships where `university_id == card.university_id`.
- **Notes** — the `notes` field on the `college_list` row itself, edited via `<NotesAffordance collection="college_list" itemId={card.id} value={card.notes} />`.

No new endpoints. All filtering is client-side over already-fetched data.

## Progress bar calculation

```
total       = essays.length + scholarships.length + 1   // +1 for the application itself
done        = essays.filter(e => e.status === 'final').length
            + scholarships.filter(s => s.status === 'submitted').length
            + (card.application_status === 'submitted' ? 1 : 0)
percent     = Math.round(100 * done / total)
```

Simple ratio. Doesn't need to be a perfect predictor — it's a directional cue.

## Expand state

Per-card boolean. Stored in a `Set<universityId>` in the parent component's state. Persisted to localStorage under `colleges_expanded_<user_email>` so refreshes preserve which cards are open.

## Deep-link auto-expand

`ApplicationsPage` reads `?school=<id>` from URL params on mount. If present:
1. Add the school to the expanded set.
2. Scroll the school's card into view.
3. Briefly highlight (1.5s outline ring).

## Multi-expand

Multiple cards can be expanded simultaneously. No accordion behavior — the student can compare schools.

## Animation

CSS `max-height` + `opacity` transition for expand/collapse, 200ms. Caret icon rotates.

## Testing strategy

- **Vitest** in `frontend/src/__tests__/MiniDashboard.test.jsx`:
  - Renders the right essay/scholarship counts given a filtered dataset.
  - Progress bar calculates correctly across edge cases (zero essays, all done, none done).
  - Expand state persists to localStorage.
  - Deep-link `?school=mit` auto-expands MIT.
- **Playwright**: smoke check the Colleges tab renders without error.

## Risks

- **Card height stability** — expanding/collapsing changes layout. Mitigation: smooth transition + no `key` change so the DOM nodes don't unmount.
- **Filter performance with many essays** — if a student has 30+ essays, filtering on each render isn't cheap but is still trivial in practice (<1ms). If it ever matters, memo the filter by university_id.
- **localStorage quota** — the persisted Set is at most a few hundred bytes per user. Not a concern.

## Alternatives considered

- **Open the full Colleges tab in a per-school view via routing.** Rejected: too heavyweight for "give me a glance at this school." Inline expand is the right grain.
- **A side panel that slides in showing the selected school.** Rejected: clashes with the floating chat panel; competes for the right side of the screen.
- **Always-expanded cards.** Rejected: long list visual noise. Default-collapsed with cheap expand is the better tradeoff.
