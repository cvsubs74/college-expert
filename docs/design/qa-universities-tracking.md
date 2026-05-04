# Design — QA Universities Tracking, Coverage, and Feedback Visibility

Spec: docs/prd/qa-universities-tracking.md.

## Backend

### Propagation

- Add `"colleges_template"` to `_PROPAGATED_FIELDS` in
  `cloud_functions/qa_agent/main.py`.
- Add `"colleges_template": archetype.get("colleges_template", [])`
  to `_pending_scenario_stub` so even pending/running scenario
  records carry the schools they will exercise.
- `_propagate_archetype_metadata` already iterates the propagated
  fields list — including `colleges_template` makes it flow to the
  run record automatically.

### Coverage

`cloud_functions/qa_agent/coverage.py::build_coverage` gains an
optional `colleges_allowlist` keyword arg.

For each *passing* scenario in each run:
- For each `uni` in `scen.colleges_template`, accumulate
  `{ id, count, last_tested_at }`. Use the run's `started_at` (fall
  back to the scenario's) as the tested timestamp; keep the latest.

Return shape extends with:

```
universities_tested: [
  { id, count, last_tested_at }, ...   # sorted by count desc, then id
],
total_universities_tested: int,
universities_untested: [id, id, ...],  # allowlist - tested, capped at 25
allowlist_size: int,
```

Cap untested rendering at `MAX_UNTESTED_UNIVERSITIES = 25` to keep
the response compact; `allowlist_size` still reflects the real total.

### Allowlist load

`_handle_summary` in `main.py` loads the colleges allowlist (best-
effort — empty list on any error so coverage still works) and passes
it into `coverage_mod.build_coverage(runs, colleges_allowlist=...)`.

### Chat grounding

`chat.py::_format_one_run` adds a per-run `colleges:` line:

```
run run_xyz · 5/5 pass · 2026-05-04T... · agent_loop
    colleges: mit, stanford, uc_berkeley
    FAIL ...
```

Rules:
- Distinct school IDs only (dedupe within the run).
- Skip the line entirely when no scenarios in the run carry
  `colleges_template` (legacy runs).

This unblocks chat from grounding "what schools have been tested?"
answers in actual data.

## Frontend

### `<UniversitiesCard />`

```
┌─ UNIVERSITIES TESTED ─── 18 of 34 covered ────────┐
│ Schools the QA agent has exercised in recent runs.│
│  • MIT                                  8x  6m ago│
│  • Stanford University                  3x  18m  │
│  ...                                              │
│ Not yet tested (16):                              │
│   princeton, yale, brown, columbia, ...           │
└───────────────────────────────────────────────────┘
```

- Reads `summary.coverage.universities_tested` and
  `universities_untested`.
- Shows top 15 tested in the visible list; `... +N more` if
  truncated.
- Shows up to 25 untested (already capped server-side).
- Empty state: "No university coverage yet — schedule a run."

Wired into `QaRunsListPage.jsx` Overview tab between `CoverageCard`
and `ResolvedIssuesCard`.

### `<FeedbackPanel />` upgrades

Each feedback row gains:

- An "✓ applied" pill when `applied_count > 0`.
- A clickable "applied to run_xyz" link (most recent run that
  consumed it) when present.

The feedback record already gets `applied_count` and
`last_applied_run_id` stamped server-side on each run.

## Tests

Backend (pytest):
- `test_coverage.py::TestUniversitiesTested` — 8 tests covering
  aggregation, sort order, last_tested_at tracking, untested
  difference, cap, and legacy scenarios.
- `test_main_endpoints.py::TestPropagateArchetypeMetadata` — 2 new
  tests for propagation of `colleges_template`.
- `test_chat.py::TestChatContextIncludesColleges` — 3 tests covering
  per-run colleges line, dedupe, and skip-when-empty.

Frontend (vitest):
- `UniversitiesCard.test.jsx` — renders tested with counts, untested
  list, "+N more" truncation, empty state.
