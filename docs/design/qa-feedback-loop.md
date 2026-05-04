# Design — QA Agent Feedback Loop

Companion to [docs/prd/qa-feedback-loop.md](../prd/qa-feedback-loop.md).

## Architecture

```
┌──────────────────────────────────────────────┐
│  Dashboard (frontend)                        │
│                                              │
│  FeedbackPanel                               │
│   ├── Active items (with applied/total)      │
│   ├── Input box                              │
│   └── Submit / Dismiss buttons               │
└──────────────────┬───────────────────────────┘
                   │ GET/POST/DELETE /feedback
                   ▼
┌──────────────────────────────────────────────┐
│  qa-agent                                    │
│                                              │
│  /feedback (admin auth)                      │
│   ├── GET → list active items                │
│   ├── POST → add new item                    │
│   └── DELETE /<id> → dismiss                 │
│                                              │
│  /run (scheduler-triggered)                  │
│   ├── synthesizer.synthesize_scenarios(...)  │
│   │     ↑ now reads `feedback.active_items()`│
│   └── on completion: feedback.mark_applied(  │
│         items_used, run_id)                  │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
        Firestore qa_config/feedback
```

## Data shape

`qa_config/feedback` (single doc, array of items):

```python
{
  "items": [
    {
      "id": "fb_abc123",                # short uuid
      "text": "Focus on essay tracker — we shipped changes today",
      "status": "active",               # active | dismissed
      "created_at": "2026-05-04T06:30:00Z",
      "created_by": "cvsubs@gmail.com",
      "applied_count": 0,               # incremented per scheduler-fire that uses it
      "max_applies": 5,                 # auto-dismiss when reached
      "last_applied_run_id": null,
      "last_applied_at": null
    },
    ...
  ],
  "updated_at": "...",
  "updated_by": "..."
}
```

Bounds:
- ≤ 10 active items at once (prevent prompt bloat)
- text 5..500 chars (validate on save)
- max_applies in [1, 20], default 5

## API contract

### `GET /feedback` (admin auth)

```json
{
  "success": true,
  "items": [
    {
      "id": "fb_abc123",
      "text": "...",
      "status": "active",
      "created_at": "...",
      "created_by": "...",
      "applied_count": 2,
      "max_applies": 5,
      "last_applied_run_id": "run_..."
    }
  ]
}
```

Returns active + recently-dismissed items (last 24h of dismissed) so the admin can see what was just expired.

### `POST /feedback` (admin auth)

Request:
```json
{ "text": "Focus on essay tracker harder" }
```

Response:
```json
{ "success": true, "item": { "id": "fb_xyz789", "text": "...", "status": "active", ... } }
```

Validation errors → 400 with `{success: false, error: "..."}`.

### `DELETE /feedback/<id>` (admin auth)

Marks the item dismissed. Returns `{success: true}`.

## Server-side: `feedback.py`

New module `cloud_functions/qa_agent/feedback.py`:

```python
def load(db=None) -> dict
def save(payload: dict, db=None) -> None  # internal, callers use add/dismiss/mark_applied
def add_item(text: str, *, actor: str, max_applies: int = 5, db=None) -> dict
def dismiss(item_id: str, db=None) -> bool   # returns True if dismissed, False if not found
def active_items(db=None) -> list[dict]      # filter status=active, max 10
def mark_applied(item_ids: list[str], *, run_id: str, db=None) -> None
def validate_text(text: str) -> Optional[str]  # error message or None
```

`mark_applied` increments `applied_count` for each id, sets `last_applied_run_id` + `last_applied_at`, and auto-dismisses any item that reaches `max_applies`.

## Synthesizer integration

`synthesizer.synthesize_scenarios` already takes `system_knowledge` and history. Add a `feedback_items` parameter:

```python
def synthesize_scenarios(
    *,
    n: int,
    history: list[dict],
    system_knowledge: str,
    colleges_allowlist: list[str],
    feedback_items: list[dict] = None,   # NEW
    ...
) -> list[dict]:
```

`_build_prompt` formats feedback as a dedicated section near the top:

```
ADMIN FEEDBACK (steers scenario design — prioritize addressing these):
1. Focus on essay tracker — we shipped changes today (left 5 days ago, applied 2/5 runs)
2. Verify UC group fix landed (left 2 days ago, applied 0/5 runs)

When generating scenarios, prefer ones that exercise the feedback above.
Include the relevant feedback id in your synthesis_rationale (e.g.,
"Targets feedback fb_abc123: tests the essay tracker after the recent change").
```

The validator accepts a new optional `feedback_id` field on synthesized scenarios for traceability.

## main.py wiring

`/feedback` route handlers:
- `_handle_get_feedback()` — calls `feedback.load()` → returns active + recently-dismissed
- `_handle_post_feedback(body, actor)` — validates, calls `feedback.add_item`
- `_handle_delete_feedback(path)` — extracts id from `/feedback/<id>`, calls `feedback.dismiss`

`_handle_run` (after scenarios are generated):
- Collect any synthesized scenarios that reference `feedback_id`
- Call `feedback.mark_applied(item_ids, run_id=run_id)` so applied_count goes up

## Frontend: FeedbackPanel.jsx

New component, lives between ChatPanel and CoverageCard on `QaRunsListPage`:

```
┌────────────────────────────────────────────────────────┐
│  📝 Feedback to the QA agent          0 of 10 active   │
│  Anything you type here gets included in the next      │
│  scheduled run's scenario design.                      │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Focus on essay tracker after the recent ship...  │ │
│  └──────────────────────────────────────────────────┘ │
│                                          [ Submit ]    │
│                                                        │
│  Active items:                                         │
│   • Focus on UC schools more  applied 2/5  [dismiss]  │
│   • Test 0.0 GPA edge case   applied 0/5  [dismiss]  │
└────────────────────────────────────────────────────────┘
```

Service: `getFeedback`, `addFeedback`, `dismissFeedback` in `services/qaAgent.js`.

## Files

**New (server):**
- `cloud_functions/qa_agent/feedback.py`
- `tests/cloud_functions/qa_agent/test_feedback.py`

**Modified (server):**
- `cloud_functions/qa_agent/synthesizer.py` — accepts `feedback_items`, includes in prompt
- `cloud_functions/qa_agent/main.py` — `/feedback` routes, `_handle_run` calls `mark_applied`
- `tests/cloud_functions/qa_agent/test_synthesizer.py` — feedback in prompt + rationale

**New (frontend):**
- `frontend/src/components/qa/FeedbackPanel.jsx`
- `frontend/src/__tests__/FeedbackPanel.test.jsx`

**Modified (frontend):**
- `frontend/src/services/qaAgent.js` — feedback CRUD
- `frontend/src/pages/QaRunsListPage.jsx` — render `<FeedbackPanel />`

## Trade-offs

**Why a single doc instead of a collection?**
≤10 active items at a time; collection per-item is overkill, single doc with merged writes is simpler and avoids a fan-out query.

**Why auto-expire after N applies instead of by time?**
"Applied N times" is the actionable concept (the agent has had a chance to address it). A time-based expire ("dismiss after 7 days") would expire un-applied feedback if the scheduler is paused.

**Why not let the LLM decide whether to drop feedback?**
We want predictable application — if the admin says "test X harder", they expect at least one run to address X soon. Letting the LLM filter the input could cause ghost feedback that's silently ignored.

**Why include feedback id in the prompt?**
So the LLM can stamp scenarios with the specific feedback they target, giving us a clean signal in `mark_applied`. Without it we'd need fuzzy matching to credit feedback as "applied".

## Rollout

1. **PR-M (this docs PR)** — PRD + design only.
2. **PR-N** — Backend: `feedback.py`, synthesizer integration, `/feedback` endpoints + tests.
3. **PR-O** — Frontend: `FeedbackPanel` + service methods + page wiring.

After PR-O ships:
- Add a feedback item via dashboard
- Wait for next scheduler fire (≤30 min)
- Confirm the synthesized scenario in the resulting run carries `feedback_id` in `synthesis_rationale`
- Dismiss the item via dashboard, confirm next run no longer references it
