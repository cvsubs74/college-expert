# Design — Structured `deadline_date` in the university knowledge base

- Issue: #191
- PRD: docs/prd/kb-deadline-date.md
- Date: 2026-05-29
- Status: approved

## Overview

Add a machine-readable `deadline_date` to KB scholarship records (and refresh
stale application-deadline dates), populate accurate 2026–27 values for a pilot
set from trusted sources, and make the roadmap/work-feed consume the structured
date. Free-text `deadline` is preserved for display.

## 1. Schema changes

### Scholarship (source of truth: Pydantic model)

`agents/university_profile_collector/model.py` — `Scholarship`:

```python
deadline: str       = ""    # unchanged — human display text
deadline_date: Optional[str] = None   # NEW: ISO 'YYYY-MM-DD' for the upcoming
                                       # cycle, or None when there is no fixed
                                       # date ("Automatic"/"Varies"/etc.)
```

Collector prompt (`sub_agents/scholarships_agent.py`): add `deadline_date` to
the output JSON example + an instruction:
> `deadline_date`: the scholarship's application deadline as ISO `YYYY-MM-DD`
> for the upcoming cycle, or null if there is no separate fixed date. Keep the
> human description in `deadline`.

### Application deadlines

`ApplicationDeadline.date` already exists (ISO). No schema change; the pilot
**refreshes** stale `date` values to the 2026–27 cycle.

### KB document shape (unchanged location)

`profile.financials.scholarships[]` gains `deadline_date`;
`profile.application_process.application_deadlines[].date` is refreshed.

## 2. Population (pilot)

A single idempotent utility — `scripts/populate_deadline_dates.py`:

- Input: a small hand-authored mapping (authored from official-source lookups)
  of `{university_id: {scholarships: {name → deadline_date|null}, application_deadlines: {plan_type → date}}}`
  for the 4 pilot schools.
- For each university: `db.get_university(id)` → set `deadline_date` on matching
  scholarships (match by `name`) and refresh `application_deadlines[].date`
  (match by `plan_type`) → `db.save_university(id, doc)`.
- **Read-modify-write only the deadline fields.** Never replaces other data.
  Idempotent (re-running yields the same result). `--dry-run` prints a diff.

The deadline values themselves are looked up by the author (me) from official
pages (school financial-aid/admissions sites; College Scorecard / Common Data
Set per `agents/source_curator/sources/universities/*.yaml`). Set `null` when
not confidently found.

> Rationale for a hand-authored mapping over live fetch in the script: keeps the
> migration deterministic, reviewable, and free of LLM/network nondeterminism —
> matching the "be careful, don't mass-guess" requirement.

## 3. Consumers

### planner.py — scholarship branch (`generate_personalized_tasks`)

Replace the free-text parse (`_normalize_scholarship_deadline`, added in #187)
with: prefer `scholarship.get('deadline_date')`; if present, roll forward to the
next on/after-today occurrence (reuse the existing roll-forward helper); if
absent/null, **drop** the task (no date to schedule). Keep dropping
"Automatic"/"Varies" implicitly (they have null `deadline_date`).

`_normalize_scholarship_deadline` is retained only as a fallback for records
that still lack `deadline_date` (Phase-2 schools), so behavior never regresses.

### work_feed.py — `_normalize_scholarships`

Prefer `deadline_date`; fall back to parsing `deadline` text.

### Application-deadline consumers

`counselor_tools.fetch_aggregated_deadlines` and the planner deadline branch
already read ISO `date`; refreshed dates flow through unchanged.

### Frontend

No change. UI keeps rendering the `deadline` text; the roadmap's
"Upcoming Deadlines" now receives correct dates from the backend.

## 4. Data flow

```
official sources ──(author)──► pilot mapping ──► populate_deadline_dates.py
   └─ read-modify-write ─► KB (universities/{id}) : scholarships[].deadline_date,
                                                    application_deadlines[].date
KB ──► counselor_agent (planner / work_feed) ──► roadmap "Upcoming Deadlines"
                                                  (rolls past→next, drops null)
```

## 5. Error handling

- Migration: skip a scholarship if no name match (log it); never delete fields;
  abort the doc write if the doc is missing required structure.
- planner: null/absent `deadline_date` → task dropped (not shown), no exception.
- Roll-forward helper already handles leap-day + termination (#187).

## 6. Testing

- `model.py`: `deadline_date` defaults to None; round-trips.
- `populate_deadline_dates.py`: unit test on a synthetic doc — sets dates by
  name/plan_type, preserves other fields, idempotent, `--dry-run` makes no write.
- `planner.py`: scholarship with future `deadline_date` used as-is; past rolls
  forward; null dropped; record lacking `deadline_date` still falls back to text
  parse.
- Live (browser): pilot schools' roadmap shows real upcoming scholarship
  deadlines; applications tab no longer all "Passed".

## 7. Rollout

1. Schema + consumers + migration utility + tests (branch `issue-191-...`).
2. Author pilot mapping from official sources; run migration (prod KB,
   `cvsubs@gmail.com`/`college-counselling-478115`).
3. Deploy `counselor_agent`; verify live for the 4 pilot schools.
4. Phase 2 (separate issue): scale to all 191 in reviewed batches.
