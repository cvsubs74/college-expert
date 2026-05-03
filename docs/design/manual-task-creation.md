# Design: Manual task creation

Status: Approved (shipped in PR #13, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/manual-task-creation.md](../prd/manual-task-creation.md)

## Frontend

### Components

- `frontend/src/components/roadmap/AddTaskPill.jsx` — the entry point button. Sits near the top of the Plan tab, sticky-ish below the focus card.
- `frontend/src/components/roadmap/AddTaskModal.jsx` — modal dialog with the form.

### AddTaskPill

```
┌─────────────────────┐
│  +  Add task        │
└─────────────────────┘
```

Renders as a small filled pill button. Click opens `AddTaskModal`.

### AddTaskModal

```
Add a task
─────────────────────────────────────────────
Title           [_________________________]
Due date        [____________]  (optional)
Notes           [____________]  (optional)

                        [Cancel]   [Add task]
```

- `<form>` element submits via Enter.
- Title is required (cannot be empty/whitespace).
- Due date uses a native `<input type="date">` — accepts ISO date strings.
- Notes is a textarea, capped at 1000 chars.
- "Add task" button is disabled while a save is in flight.
- Modal closes on successful save, stays open with an error message on failure.

The dialog uses `role="dialog"` and `aria-label="Add a task"` for accessibility (and so the Playwright test can locate it).

## Backend

### Endpoint

`POST /save-roadmap-task` on `profile_manager_v2` — the data manager that owns user-document writes.

Request body:
```json
{
  "user_email": "...",
  "title": "Email coach about recruiting",
  "due_date": "2026-11-15",     // ISO date, optional
  "notes": "..."                  // optional
}
```

Response:
```json
{ "success": true, "task_id": "user_task_<uuid>" }
```

### Storage

Writes to `users/{uid}/roadmap_tasks/{task_id}` with the shape:

```json
{
  "id": "user_task_<uuid>",
  "title": "...",
  "type": "user",                 // distinguishes from template tasks
  "due_date": "...",
  "notes": "...",
  "status": "pending",
  "created_at": "...",
  "updated_at": "..."
}
```

`type: "user"` keeps these tasks identifiable for any future code that wants to treat them differently — not used for visual differentiation in M1.

### Validation

- `title` required, trimmed, max 200 chars.
- `due_date` if present must parse as ISO date; rejected otherwise.
- `notes` capped at 1000 chars.
- Failures return `400` with `{ success: false, error: "<reason>" }`.

### Auth

Same Firebase auth gate as the rest of `profile_manager_v2`. `user_email → uid` lookup uses the existing helper.

## Refetch flow

After a successful save, the Plan tab refetches:
- `/roadmap` — so the timeline includes the new task.
- `/work-feed` — so the focus card picks up the new task if it qualifies.

The fetches happen in parallel; both use existing endpoints.

## Testing strategy

- **Vitest** in `frontend/src/__tests__/AddTaskModal.test.jsx`:
  - Renders the form when opened.
  - Submit with empty title → blocked, shows validation message.
  - Submit valid task → POSTs to `/save-roadmap-task` with the right body, modal closes.
  - Network error → modal stays open, error toast appears.
- **Playwright**: open the modal, fill title, submit; modal closes (count = 0).
- **Backend pytest** — `tests/cloud_functions/profile_manager_v2/` covers the endpoint: happy path, missing title (400), invalid date format (400).

## Risks

- **Click intercepted by other fixed-position elements** (chat panel, sticky nav). Mitigation in tests: `force: true` on the click. Production: the layout positions the chat panel below the pill so they don't overlap unless the chat is open and the user has scrolled past the pill.
- **A user creating dozens of tasks** — no soft limit on task count. Acceptable for now; if it ever causes a perf problem, paginate the timeline.
- **Date timezone confusion** — `<input type="date">` returns a date string like "2026-11-15" with no timezone. We store it as-is. Rendering elsewhere assumes the user's local TZ for "days_until" calculation. Edge cases (a task due "tomorrow" displaying differently in two TZs) are weeks-wide concerns over a date-wide field; acceptable.

## Alternatives considered

- **Inline new-task row at the bottom of the timeline.** Rejected: too easy to miss, conflicts with existing timeline rendering. A clear "Add task" pill is more discoverable.
- **Free-form natural-language ("Add task: email coach Friday")** sent to the counselor agent for parsing. Rejected for M1: more delightful but more complex than the form. Could ship as an addition later.
- **Persist drafts of unsaved tasks in localStorage.** Rejected: minor convenience, adds state and revival logic. Submit-or-cancel is fine for a small form.
