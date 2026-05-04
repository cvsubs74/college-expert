# Design — Configurable Feedback Auto-Retire Threshold

Spec: docs/prd/qa-feedback-configurable-max-applies.md.

## Backend

`cloud_functions/qa_agent/feedback.py`:

- `MAX_APPLIES_BOUND` 20 → 99 so a "Never" option in the UI can map
  to a finite value that round-trips through the existing
  `max(1, min(MAX_APPLIES_BOUND, …))` clamp without code changes.
- `DEFAULT_MAX_APPLIES = 5` unchanged so anyone hitting the API
  without specifying gets the same behaviour.

`_handle_post_feedback` already accepts and forwards `max_applies`
from the request body; no handler change needed.

## Frontend

`frontend/src/components/qa/FeedbackPanel.jsx`:

- Add a controlled `maxApplies` state, initial value `5`.
- Render a `<select>` between the character counter and the Submit
  button:

  ```
  ┌──────────────────────────────────────────────────┐
  │ [textarea: "Anything you type here ..."]         │
  │                                                  │
  │ 0/500           Expires after: [5 ▼] runs  [Submit] │
  └──────────────────────────────────────────────────┘
  ```

  Options: `1`, `3`, `5` (default selected), `10`, `20`, `Never`.
  "Never" maps to `99` when sent to the backend.

- `submitFeedback()` passes `{ text, max_applies: maxApplies }` to
  `addFeedback()`.

- `addFeedback()` in `services/qaAgent.js` accepts the new field and
  forwards it as `max_applies` in the POST body.

- Update the panel description copy:
  > Anything you type here gets included in the next scheduled run's
  > scenario design. Each item carries its own auto-retire limit
  > (default 5 runs). Pick "Never" for persistent steers — you can
  > always retire manually via the X button.

- Reset the selector to its default after a successful submit.

## Tests

Backend:
- `test_feedback.py::TestAddItem` — new case asserting
  `max_applies=99` is preserved (proves bound bump took effect).
- Existing `test_caps_active_items_at_10` etc. unchanged.

Frontend (vitest):
- `FeedbackPanel.test.jsx` — new cases:
  - Default selector value is "5".
  - Selecting "1" and submitting calls `addFeedback({ text, max_applies: 1 })`.
  - Selecting "Never" submits `max_applies: 99`.
  - Selector resets to default after a successful submit.

## Risk

Low:
- Backend change is a single constant + an existing clamp. The new
  upper bound only affects items the operator explicitly opts into.
- No data migration: existing items keep their stored `max_applies`.
- Frontend opt-in: the selector defaults to 5 so an operator who
  ignores it gets today's behaviour.
