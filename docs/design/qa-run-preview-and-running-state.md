# Design — Run Preview + Running State

Companion to [docs/prd/qa-run-preview-and-running-state.md](../prd/qa-run-preview-and-running-state.md).

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Dashboard (frontend)                                      │
│                                                            │
│  RunNowPanel                                               │
│   ├─ click "Run now"                                       │
│   │     POST /run/preview ─┐                              │
│   │                         ▼                              │
│   ├─ render PreviewModal — list of scenarios picked        │
│   │     [Run] [Cancel]                                     │
│   │     on Run: fire POST /run, close modal                │
│   ▼                                                        │
│  RunsTable                                                 │
│   ├─ Firestore real-time listener on qa_runs               │
│   ├─ Row with status="running" → Running badge + spinner   │
│   ▼                                                        │
│  QaRunDetailPage                                           │
│   ├─ status="running" → render picked scenarios as         │
│   │     pending; show "X of Y done" progress               │
│   └─ status="complete" → existing rendering                │
└────────────────────────────────────────────────────────────┘
                       │
                       ▼ POST /run/preview
                       │ POST /run (modified)
                       ▼
┌────────────────────────────────────────────────────────────┐
│  qa-agent                                                  │
│                                                            │
│  POST /run/preview (admin auth)                            │
│   1. corpus.load_archetypes()                              │
│   2. Synthesizer (if enabled) + corpus.select_scenarios   │
│   3. Returns: { picked: [{id, description, rationale,     │
│      surfaces}], synth_count, static_count }               │
│   No Firestore writes, no scenario execution.              │
│                                                            │
│  POST /run (modified)                                      │
│   1. Pick scenarios (same as today)                        │
│   2. Generate run_id + write Firestore qa_runs/{run_id}    │
│      with status="running", scenarios=[stubs], started_at  │
│   3. (existing) Run each scenario, build report            │
│   4. Update qa_runs/{run_id} with full report,             │
│      status="complete"                                     │
└────────────────────────────────────────────────────────────┘
```

## Data shape changes

`qa_runs/{run_id}` gets a new `status` field:
- `"running"` — written at start, scenarios are stubs without results yet
- `"complete"` — written at end with the full report

A "running" doc looks like:
```python
{
  "run_id": "run_...",
  "status": "running",
  "started_at": "...",
  "trigger": "manual" | "schedule_check",
  "actor": "...",
  "summary": {"total": N, "pass": 0, "fail": 0},  # placeholder
  "scenarios": [
    {"scenario_id": "junior_spring_5school", "status": "pending",
     "description": "...", "surfaces_covered": [...]},
    ...
  ],
}
```

A "complete" doc has all the existing fields PLUS `status: "complete"`. Legacy docs without `status` are treated as complete (`status === "running"` is the only special case).

## API: `POST /run/preview`

Request:
```json
{}        // optional: {count: 4} to override default scenario count
```

Response:
```json
{
  "success": true,
  "picked": [
    {
      "id": "junior_spring_5school",
      "description": "Junior in spring with a 5-school list...",
      "business_rationale": "Validates the most common journey...",
      "surfaces_covered": ["profile", "college_list", "roadmap"],
      "synthesized": false
    },
    {
      "id": "synth_essay_tracker_focus",
      "description": "...",
      "synthesis_rationale": "Targets fb_abc123 admin feedback...",
      "synthesized": true,
      "feedback_id": "fb_abc123"
    }
  ],
  "synth_count": 1,
  "static_count": 1
}
```

The preview makes the same picks `/run` would. It uses the same selectors so the user sees what they'll get. Cost: one Gemini-Flash call (synthesizer) + one Firestore read (history). No scenario execution, no test-user state changes.

## `_handle_run` modifications

Two new write calls:
1. Right after picking scenarios + before the per-scenario loop:
   ```python
   firestore_store.write_report(run_id, {
       "run_id": run_id,
       "status": "running",
       "trigger": trigger, "actor": actor,
       "started_at": started.isoformat(),
       "summary": {"total": len(chosen), "pass": 0, "fail": 0},
       "scenarios": [_stub_scenario(a) for a in chosen],
   })
   ```
2. At the end, the existing `firestore_store.write_report(run_id, report)` overwrites the doc with the full report; we add `report["status"] = "complete"`.

The stub format mirrors the final scenario record shape so the frontend's existing rendering code mostly Just Works:
```python
def _stub_scenario(archetype):
    return {
        "scenario_id": archetype.get("id"),
        "status": "pending",       # NEW field
        "description": archetype.get("description"),
        "business_rationale": archetype.get("business_rationale"),
        "surfaces_covered": archetype.get("surfaces_covered", []),
        "synthesized": archetype.get("synthesized", False),
        "synthesis_rationale": archetype.get("synthesis_rationale"),
        "passed": None,             # not yet known
        "steps": [],
    }
```

## Frontend changes

### `RunNowPanel.jsx`
- Click handler calls `getRunPreview()` → opens `PreviewModal`
- `PreviewModal` shows the picked scenarios with their description + rationale
- Confirm → calls `triggerRun()` (existing) → closes modal → calls `onComplete` to refresh the run list

### `PreviewModal.jsx` (new)
- Modal overlay with the scenario list
- Each row: scenario id (mono), description, surfaces (badges), business_rationale (italic), synthesized badge if applicable, feedback_id pill if applicable
- Footer: [Cancel] [Run]

### `RunsTable.jsx`
- For each row, check `run.status`
- If `"running"`: render a `Running` badge (spinner + label) instead of the pass/fail count

### `QaRunDetailPage.jsx`
- Header pill: `Running` if `status === "running"`, else existing pass/fail
- Scenario cards: when scenario.status === "pending", render a "Pending" placeholder with the description + rationale; when scenario has results, render normally
- Live update: if the page is viewing a `running` run, re-fetch every 5 seconds (or use Firestore real-time listener) to pick up state changes

### `services/qaAgent.js`
- New `getRunPreview({count})` function — `POST /run/preview`

## Files

**New (server):**
- (modifications only — new endpoint reuses existing imports)

**Modified (server):**
- `cloud_functions/qa_agent/main.py`:
  - New `/run/preview` route + `_handle_run_preview()`
  - `_handle_run` writes the running doc + sets `status` field
- `cloud_functions/qa_agent/firestore_store.py`:
  - Maybe a small helper `write_running(run_id, partial)` if it makes the call site cleaner; else inline the call
- `tests/cloud_functions/qa_agent/test_main_endpoints.py`:
  - Tests for `/run/preview` + the running-doc write in `/run`

**New (frontend):**
- `frontend/src/components/qa/PreviewModal.jsx`
- `frontend/src/__tests__/PreviewModal.test.jsx`

**Modified (frontend):**
- `frontend/src/components/qa/RunNowPanel.jsx` — preview-then-run
- `frontend/src/components/qa/RunsTable.jsx` — running badge
- `frontend/src/pages/QaRunDetailPage.jsx` — running pill + pending scenarios + auto-refresh
- `frontend/src/services/qaAgent.js` — `getRunPreview`

## Trade-offs

**Why write the running doc from inside `/run` rather than from the frontend?** Two reasons: (a) one source of truth for run picks (the synthesizer + corpus selectors live server-side), (b) scheduler-triggered runs need the same behavior — they don't have a frontend.

**Why not Firestore real-time listeners on the detail page?** We could (and should add it later), but a 5-sec poll is enough for a 2-3 min run and keeps the change small.

**Why not pre-compute the run_id on the preview call?** That would let the user open the detail page before clicking Run. Not worth the complexity — preview is information, "Run" is the commitment.

**Why a confirm step instead of just running?** The user explicitly asked for the preview ("before running it should detail the scenario"). Without confirmation, the modal is just a flashbang.

## Rollout

1. **PR-P** — this PRD + design.
2. **PR-Q** — backend: `/run/preview` + `_handle_run` writes running doc.
3. **PR-R** — frontend: PreviewModal + Running badge + detail-page state.

Each PR ships independently. The backend changes are forward-compatible: legacy frontend that doesn't know about `status` will still work (status="complete" docs have the full report shape they already expect; status="running" docs would render as "0/N pass" until they complete, which is acceptable as an interim).
