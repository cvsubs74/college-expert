# Design — QA Dashboard Visibility Gaps

Spec: docs/prd/qa-dashboard-visibility-gaps.md.

## 1. Feedback retirement visibility

### Backend

`feedback.py` adds:

```python
def recently_dismissed_items(limit=10, db=None) -> List[dict]:
    """Return up to `limit` most-recently-dismissed items, sorted by
    last_applied_at desc (falls back to created_at). Used by the Steer
    panel to show 'feedback that already steered runs and retired'."""
```

`main.py::_handle_get_feedback` returns both fields:

```json
{ "success": true,
  "items": [...],                    // active (unchanged shape)
  "recently_dismissed": [...] }      // newest 10, dismissed
```

The existing `items` field stays exactly as-is, so the frontend
upgrade is purely additive.

### Frontend

`FeedbackPanel` gains a "Retired" subsection rendered when
`recently_dismissed.length > 0`. Each retired row shows:
- the original text (muted)
- a "✓ retired after N runs" pill
- last applied run id as a clickable router `<Link>` (same pattern
  as the active rows)
- created/dismissed timestamps

This makes the "the feedback worked" loop visible end-to-end.

## 2. Per-run sparkline

### Frontend

Rename `SparklineByDay.jsx` → `Sparkline.jsx` (legacy import path
preserved via a one-line re-export so the rename is reversible).
Inside:

- Drop the day-bucketing loop entirely.
- One bar per run, ordered oldest→newest left→right (latest = right
  edge, matching today's read direction).
- Width: target ~6-8 px per bar with a small gap; cap the total at
  the existing `W=240`. If we have more runs than fit, take the most
  recent that fit and show "showing latest N of M" caption.
- Color rule unchanged at the bar level: any fail in that run's
  `summary.fail` → red; otherwise green.
- Headline "X% green" stays per-run (already correct).

### Tests

`SparklineByDay.test.jsx` (or new `Sparkline.test.jsx`):

- 5 passing runs + 1 failing run → 5 green bars + 1 red bar in
  chronological order.
- 0 runs → empty viewbox + "—" headline (existing behaviour).
- 30+ runs → only the most recent N bars render, plus a
  "showing latest N of M" caption.

## Risk

Low:
- The feedback change is purely additive at the API level
  (`recently_dismissed` is a new field; `items` stays as-is).
- The sparkline rename keeps a re-export for backward import paths.
- Both fixes ship behind the same release; no schema changes.
