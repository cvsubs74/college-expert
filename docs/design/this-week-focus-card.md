# Design: ThisWeekFocusCard

Status: Approved (shipped in PR #8, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/this-week-focus-card.md](../prd/this-week-focus-card.md)

## Component

`frontend/src/components/roadmap/ThisWeekFocusCard.jsx`

```
ThisWeekFocusCard
├── header: "This Week" + counter ("5 items")
├── list:
│     for each item from /work-feed:
│         ┌──────────────────────────────────────────────────────┐
│         │ [icon by source]  Title              ┌──────────┐    │
│         │                   Subtitle           │ urgent   │    │
│         │                   in 5 days          └──────────┘    │
│         │                                       [📝 notes]      │
│         └──────────────────────────────────────────────────────┘
│                                  ↑
│                              click area → router.push(item.deep_link)
└── empty state ("Nothing urgent — nice work")
```

## Data fetch

```js
useEffect(() => {
  axios.get(`${COUNSELOR_AGENT_URL}/work-feed`, {
    params: { user_email, limit: 8 }
  }).then(...)
}, [user_email])
```

Refetches on mount only. After a notes save (which flows through `NotesAffordance` → `/update-notes`), the component refetches so the cached/computed `urgency` and any side-effects propagate.

## Click → deep link

`item.deep_link` is a fully-formed URL the server builds. The card is a dumb consumer: `<button onClick={() => navigate(item.deep_link)}>`. No conditional logic on `source` — that's the entire point of the unified shape.

## Urgency rendering

`item.urgency` comes pre-computed from the server. The component maps it to badge color:

| urgency | badge |
|---|---|
| `overdue` | red |
| `urgent` | orange |
| `soon` | yellow |
| `later` | gray |

Threshold logic stays on the server (see `/work-feed` design). UI never decides "is 5 days urgent?".

## Notes affordance integration

Each item carries an `id`, a `source` (which maps to a `collection` for `/update-notes`), and a `notes` value. The card composes `<NotesAffordance collection={...} itemId={item.id} value={item.notes} onSave={...} />`. Map from `source` to collection:

| source | collection |
|---|---|
| `roadmap_task` | `roadmap_tasks` |
| `essay` | `essay_tracker` |
| `scholarship` | `scholarship_tracker` |
| `college_deadline` | `college_list` |

## Empty state

When `items.length === 0`, render a friendly empty card: title "Nothing urgent — nice work", subtitle linking to "View full plan ↓" which scrolls to the timeline below.

## Loading state

Skeleton rows (3 placeholder cards with shimmer) while `/work-feed` is in flight. On error (network/500), show "Couldn't load focus card — refresh to try again" with a retry button.

## Testing strategy

- **Vitest** in `frontend/src/__tests__/ThisWeekFocusCard.test.jsx`:
  - Renders skeleton during fetch.
  - Renders items with correct urgency badges given a mocked /work-feed response.
  - Click on an item navigates to its `deep_link`.
  - Empty state renders when items array is empty.
  - Error state renders on fetch failure.
- **Playwright E2E**: focus card item is visible after page load (smoke test in `roadmap.spec.js`).

## Risks

- **Stale data after a mutation elsewhere**. If the student finishes an essay on the Essays tab and then comes back to Plan, the focus card may still show that essay until the cache TTL expires. Acceptable: refetch happens on tab activation; tolerable lag.
- **A future source not yet mapped**. Adding a fifth `source` value to `/work-feed` and forgetting to add it to the source→collection map would silently break notes. Mitigation: the mapping table is small and tested; extending it is one well-known place.
- **Click target overlap with notes icon**. The whole row navigates; the notes icon is a nested button. Tested that nested-button clicks `event.stopPropagation()` so notes editing doesn't navigate.

## Alternatives considered

- **Server pushes via WebSocket/SSE.** Rejected for M1 — overkill for "refresh on page load" use case.
- **Fully-rendered HTML widget from the server.** Rejected — couples backend to UI markup; we like the unified-shape JSON contract.
- **Show all items, no limit.** Rejected — defeats the focus-card purpose. The full timeline is below.
