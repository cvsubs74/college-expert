# QA Dashboard — Visibility Gaps

## Problem

Two operator-facing visibility bugs reported on 2026-05-04 looking at
the live dashboard:

### 1. Feedback silently disappears

The Steer panel filters by `status: "active"`. When a feedback item's
`applied_count` reaches `max_applies` (default 5), `mark_applied`
flips status to `"dismissed"` and the item is removed from view —
permanently. The operator's note `fb_fa136214` ("Make sure to cover
every single university in the subsequent…") was on its 5th apply and
is now invisible, even though it drove 5 real runs.

The auto-dismiss is correct (we don't want a single note steering
the synthesizer forever). The invisibility is wrong: an operator
who comes back to the Steer panel a day later sees an empty list and
has no idea their note worked.

### 2. Sparkline shows "81% green" but no green bars

`SparklineByDay` renders 30 daily buckets, each colored by the worst
run that day (any fail → red, all pass → green, no runs → gray
`#E5E7EB`). With 21 runs spread across 30 days (the agent has only
been running consistently for the last week), 27 of the 30 buckets
are empty (gray) and the visible bars look mostly blank with one
red. The headline "81% green" is per-RUN (PR #61 fix), so the math
disagrees with the visual.

## Goals

- An operator can tell their feedback drove runs even after it
  auto-retires.
- The sparkline bars match the headline they sit next to.

## Non-goals

- Not changing the auto-dismiss threshold or behaviour.
- Not introducing real charting libraries (the inline SVG sparkline
  is fine — just re-bucket the data).

## Success criteria

- The Steer panel renders a "Retired" section listing the most recent
  N (5? 10?) dismissed items with their final `applied_count` and
  `last_applied_run_id`.
- The sparkline shows one bar per run (not per day), colored by that
  run's pass/fail. The bar count matches the headline run count.
