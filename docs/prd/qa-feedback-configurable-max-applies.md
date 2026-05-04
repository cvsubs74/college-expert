# QA Feedback — Configurable Auto-Retire Threshold

## Problem

Every feedback item the operator leaves in the Steer panel auto-retires
after exactly **5** applied runs. The number is hardcoded as
`DEFAULT_MAX_APPLIES = 5` and the dashboard offers no way to override
it. Two real failure modes:

1. The operator wants a one-shot tweak: "do this in the very next run,
   then drop it" (`max_applies=1`). Today they have to dismiss it
   manually after the next run.
2. The operator wants a persistent steer: "always test new universities
   in every run". Today the note auto-expires after 5 runs and they
   have to keep retyping it.

Operator feedback on 2026-05-04: *"We should not automatically retire
after 5 runs. The user should be allowed to configure that."*

## Goals

- Operator chooses the auto-retire threshold per feedback item at
  creation time.
- A "Never" affordance exists for persistent steers (operator dismisses
  manually via the X button when done).
- Existing behaviour preserved as the default (5 runs).

## Non-goals

- Not adding a per-item *update* endpoint. Threshold is fixed at
  creation; the operator can dismiss + recreate to change it.
- Not making the threshold a global default across all items — each
  item carries its own.

## Success criteria

- The Steer-panel form has a small selector "Expires after: [5 ▼]
  runs" with options `1`, `3`, `5`, `10`, `20`, `Never`.
- Submitting passes the chosen value through to `POST /feedback`.
- "Never" maps to `max_applies = 99` (above any realistic operator
  cycle); the existing 1-N clamp is widened to 1-99 so this round-trips.
- Existing feedback items keep their per-item `max_applies` from
  creation time.
