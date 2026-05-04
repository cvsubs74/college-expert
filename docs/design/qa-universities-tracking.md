# Design — Universities Tracking + Chat Grounding

Companion to [docs/prd/qa-universities-tracking.md](../prd/qa-universities-tracking.md).

## Architecture

```
┌─ archetype JSON (e.g. junior_spring_5school.json) ─────────┐
│   colleges_template: ["mit", "stanford_university", ...]   │
└────────────────┬───────────────────────────────────────────┘
                 │ /run picks scenario, materializes
                 ▼
┌─ runner.run_scenario ──────────────────────────────────────┐
│   returns scenario record { scenario_id, passed, steps,...}│
│   (does NOT include colleges_template today)               │
└────────────────┬───────────────────────────────────────────┘
                 │ _propagate_archetype_metadata
                 ▼
┌─ NEW: scenario record now carries colleges_template ───────┐
│   so coverage.py + chat.py can see it                      │
└────────────────┬───────────────────────────────────────────┘
                 │
       ┌─────────┴────────────────────────────────┐
       ▼                                          ▼
┌─ coverage.build_coverage ──────┐  ┌─ chat._format_run_context ──┐
│  ALSO emits:                   │  │  ALSO emits per-run line:    │
│   universities_tested: [...]   │  │    "colleges: mit, stanford,│
│   universities_untested: [...] │  │     uc_berkeley"            │
│   total_universities_tested: N │  │  so the LLM can answer       │
│   allowlist_size: 34           │  │  "what unis tested?"         │
└────────────────┬───────────────┘  └─────────────────────────────┘
                 │
                 ▼
       /summary response gains a `universities` block
                 │
                 ▼
       Frontend UniversitiesCard on Overview tab
```

## Data shape changes

### `_propagate_archetype_metadata`
Add `colleges_template` to `_PROPAGATED_FIELDS`:
```python
_PROPAGATED_FIELDS = (
    "tests", "surfaces_covered",
    "business_rationale",
    "synthesized", "synthesis_rationale",
    "feedback_id",
    "colleges_template",  # NEW
)
```

Same change to `_pending_scenario_stub` so running docs also carry it.

### `coverage.build_coverage` — new fields

In addition to the existing `journeys` + `validated_features`:
```python
{
    "universities_tested": [
        {"id": "mit", "count": 8, "last_tested_at": "2026-05-04T..."},
        {"id": "stanford_university", "count": 7, "last_tested_at": "..."},
        ...
    ],
    "universities_untested": ["princeton_university", "yale_university", ...],
    "total_universities_tested": 18,
    "allowlist_size": 34,
}
```

`universities_untested` is the set difference between the allowlist (loaded from `scenarios/colleges_allowlist.json`) and the set of `id`s in `universities_tested`. Capped at 20 to keep the response compact.

`universities_tested` is sorted by `count` desc.

### `chat._format_run_context` — augment per-run line

Today each run gets a one-line summary. Add a compact "colleges:" sub-line:
```
run_20260504T... · 4/4 pass · 2026-05-04T01:00 · agent_loop
  colleges: mit, stanford_university, university_of_california_berkeley
  FAIL ... (only when failures present)
```

## Frontend — UniversitiesCard

New component on Overview tab between CoverageCard and ResolvedIssuesCard:

```
┌─ UNIVERSITIES TESTED ─── 18 of 34 covered ────────┐
│ Schools the QA agent has exercised in recent runs.│
│                                                   │
│ Most-tested:                                      │
│  • MIT                                  8x  6m ago│
│  • Stanford                             7x  6m ago│
│  • UC Berkeley                          5x 12m ago│
│  ... +15 more                                     │
│                                                   │
│ Not yet tested (16):                              │
│   princeton, yale, brown, columbia, ...           │
│   → leave feedback to ask for these               │
└───────────────────────────────────────────────────┘
```

Data from `summaryResp.coverage.universities_tested` + `universities_untested`.

## Frontend — Feedback panel tighter signal

Each feedback item in the panel currently shows:
```
fb_xxx · applied 2/5 · last: run_xxx
```

Augment the `last:` to a clickable `<Link to="/qa-runs/run_xxx">` so the admin can jump straight to the run where the feedback was applied.

Also: when `applied_count > 0`, render a small green "✓ applied" pill so the admin sees at a glance which items the agent has acted on.

## Files

**New (server):**
- (none — augmenting existing modules)

**Modified (server):**
- `cloud_functions/qa_agent/main.py` — add `colleges_template` to `_PROPAGATED_FIELDS` + `_pending_scenario_stub`
- `cloud_functions/qa_agent/coverage.py` — emit `universities_tested` + `universities_untested` + `total_universities_tested` + `allowlist_size`
- `cloud_functions/qa_agent/chat.py` — `_format_run_context` includes per-run colleges line
- `tests/cloud_functions/qa_agent/test_main_endpoints.py` — propagation test for colleges_template
- `tests/cloud_functions/qa_agent/test_coverage.py` — universities_tested aggregation tests
- `tests/cloud_functions/qa_agent/test_chat.py` — context includes colleges

**New (frontend):**
- `frontend/src/components/qa/UniversitiesCard.jsx`
- `frontend/src/__tests__/UniversitiesCard.test.jsx`

**Modified (frontend):**
- `frontend/src/pages/QaRunsListPage.jsx` — render `<UniversitiesCard />` on Overview
- `frontend/src/components/qa/FeedbackPanel.jsx` — clickable run id + "✓ applied" pill

## Trade-offs

**Why piggyback on /summary instead of a new endpoint?** Allows a single fetch to populate the Overview tab's three cards (Coverage, Universities, Resolved Issues). Adding a separate /universities endpoint would multiply round trips with no functional benefit.

**Why emit the untested list in the response?** So the dashboard can render "next to test" without a second roundtrip + so the chat can mention "still untested: X, Y, Z" if the operator asks.

**Why cap untested at 20?** Allowlist is 34 today; if 34 are all untested we still show 20 + "+14 more". Keeps the JSON compact and the UI readable.

**Why not have the agent automatically rotate to untested universities?** That's a synthesizer behavior change — could be a follow-up. For now, leaving feedback "test more new universities" already does the right thing (verified in prod earlier).

## Rollout

1. **PR-T (this docs PR)**.
2. **PR-U** — backend changes + tests, frontend `UniversitiesCard` + `FeedbackPanel` link, page wiring. Single PR (frontend can't ship without the backend response, and the changes are tightly coupled).

This skips the usual "backend PR + frontend PR" split because the backend additions are small (3 modules, additive only) and the frontend is one card.
