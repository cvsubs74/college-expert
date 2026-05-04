# Design — Insightful QA Dashboard

Companion to [docs/prd/qa-dashboard-insights.md](../prd/qa-dashboard-insights.md).

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Dashboard (frontend)                            │
│  ┌──────────────────────────────────────────┐   │
│  │ ExecutiveSummary                          │   │
│  │   • Recent-N pass rate (PRIMARY)          │   │
│  │   • 7d / 30d (secondary)                  │   │
│  │   • Surface health (existing)             │   │
│  │   • [N=20 ▾] selector → saves to qa_config│   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ ChatPanel (existing)                       │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ CoverageCard (NEW)                         │   │
│  │   • Validated end-to-end journeys          │   │
│  │   • One row per distinct journey           │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │ ResolvedIssuesCard (NEW)                   │   │
│  │   • Recent FAIL → PASS transitions         │   │
│  │   • Shows the failing-assertion message    │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
                    │
                    ▼ GET /summary?recent_n=20
┌──────────────────────────────────────────────────┐
│  qa-agent /summary                                │
│  • build_summary(runs, recent_n=N)                │
│  • build_coverage(runs)                           │
│  • build_resolved_issues(runs)                    │
└──────────────────────────────────────────────────┘
                    │
                    ▼
            qa_runs (Firestore)
```

## Data shapes

### `build_summary` (extended)

```python
{
    "narrative": "Last 20 runs are 100% pass; surfaces all green.",
    "pass_rate_recent": 100,
    "recent_n": 20,
    "pass_rate_7d": 100,           # existing, kept as secondary
    "pass_rate_30d": 84,           # existing, kept as secondary
    "trend": "improving",
    "surfaces": { "profile": ..., "college_list": ..., "roadmap": ... },
}
```

### `build_coverage(runs)` — NEW

Walks the most recent ~30 runs, collects passing scenarios, and groups by their `surfaces_covered` tuple to produce distinct end-to-end journeys.

```python
{
    "journeys": [
        {
            "id": "profile_buildout_with_college_list",  # stable hash of surfaces tuple
            "surfaces": ["profile", "college_list", "roadmap"],
            "summary": "Profile build → add 3 colleges → roadmap generation",
            "scenarios": [
                {"id": "junior_spring_5school", "verified_at": "2026-05-04T04:30Z"},
                ...
            ],
            "verified_count": 12,  # how many recent runs touched this journey successfully
        },
        ...
    ],
    "total_journeys": 7,
}
```

### `build_resolved_issues(runs)` — NEW

Walks runs in chronological order; for each (scenario_id, step_name) pair, tracks the most recent failure → success transition. Emits one entry per recent fix.

```python
{
    "fixes": [
        {
            "scenario_id": "synth_high_achiever_junior_all_ucs",
            "step_name": "roadmap_generate",
            "failing_message": "metadata.template_used=='junior_fall': got 'sophomore_spring'",
            "failed_at_run": "run_20260504T010246Z_bdba3a",
            "fixed_at_run": "run_20260504T011634Z_46140b",
            "fixed_at_time": "2026-05-04T01:16:34Z",
        },
        ...
    ],
    "total_fixes": 4,
    "lookback_runs": 30,
}
```

The state-transition logic:
- Walk runs newest-to-oldest
- For each scenario_id: if it's currently passing AND the most recent prior run had it failing on the same step, that's a "fix" (record both run IDs + the failure message)
- Cap at 10 most recent fixes for the dashboard

### Recent-N persistence

Add a new doc `qa_config/dashboard_prefs`:

```python
{
    "recent_n": 20,           # default
    "updated_at": "...",
    "updated_by": "admin@..."
}
```

Bounds: 5 ≤ N ≤ 100. Default 20.

## API contract

**Existing `GET /summary`** gains an optional `?recent_n=N` query param. Without it, falls back to the saved prefs (or 20 default).

Response now includes `coverage` + `resolved_issues` blocks alongside the existing fields:

```json
{
  "success": true,
  "summary": {
    "narrative": "...",
    "pass_rate_recent": 100,
    "recent_n": 20,
    "pass_rate_7d": 100,
    "pass_rate_30d": 84,
    "trend": "improving",
    "surfaces": {...}
  },
  "coverage": { "journeys": [...], "total_journeys": 7 },
  "resolved_issues": { "fixes": [...], "total_fixes": 4, "lookback_runs": 30 }
}
```

## Business-context scenario rationale (Feature B)

Each scenario doc currently has `description` ("Junior in spring with a 5-school...") and `tests` (a checklist of what to verify). Add a new field `business_rationale` — 1-2 sentences in plain language.

For the 8 static scenarios (`scenarios/*.json`), I'll author the rationale by hand. For LLM-synthesized scenarios, the synthesizer prompt is updated to require this field in its output, with examples showing the desired tone.

The `ScenarioCard` component renders `business_rationale` if present, falling back to `description`.

Example:
- `description`: "Junior in spring with a 5-school reach-and-target list mixing T20s and UCs."
- `business_rationale`: "Validates that junior-year students still mid-college-search get a fully personalized roadmap that recognizes both reach schools and UC group dynamics — the most common journey for our highest-engagement users."

## Files

**New (server):**
- `cloud_functions/qa_agent/coverage.py` — `build_coverage(runs)`, `_journey_id`, `_summarize_journey`
- `cloud_functions/qa_agent/resolved_issues.py` — `build_resolved_issues(runs)`, `_state_transitions`
- `cloud_functions/qa_agent/dashboard_prefs.py` — `load_prefs(db=None)`, `save_prefs(prefs, actor, db=None)`, `validate_prefs(prefs)`
- `tests/cloud_functions/qa_agent/test_coverage.py`
- `tests/cloud_functions/qa_agent/test_resolved_issues.py`
- `tests/cloud_functions/qa_agent/test_dashboard_prefs.py`

**Modified (server):**
- `cloud_functions/qa_agent/narratives.py` — `build_summary` gains `recent_n` param + `pass_rate_recent` field
- `cloud_functions/qa_agent/main.py` — `_handle_summary` includes coverage + resolved_issues + honors `?recent_n`
- `cloud_functions/qa_agent/scenarios/*.json` — add `business_rationale` to each
- `cloud_functions/qa_agent/synthesizer.py` — prompt asks for `business_rationale`; validator accepts it

**New (frontend):**
- `frontend/src/components/qa/CoverageCard.jsx`
- `frontend/src/components/qa/ResolvedIssuesCard.jsx`
- `frontend/src/__tests__/CoverageCard.test.jsx`
- `frontend/src/__tests__/ResolvedIssuesCard.test.jsx`

**Modified (frontend):**
- `frontend/src/components/qa/ExecutiveSummary.jsx` — show `pass_rate_recent` as primary; add N selector
- `frontend/src/components/qa/ScenarioCard.jsx` — render `business_rationale` when present
- `frontend/src/pages/QaRunsListPage.jsx` — render `<CoverageCard />` + `<ResolvedIssuesCard />`
- `frontend/src/services/qaAgent.js` — pass through coverage + resolved_issues

## Rollout (PR sequence)

1. **PR-F**: Backend — `build_summary(recent_n)` + dashboard_prefs storage + ExecutiveSummary frontend update
2. **PR-G**: Backend — coverage.py + CoverageCard frontend
3. **PR-H**: Backend — resolved_issues.py + ResolvedIssuesCard frontend
4. **PR-I**: Scenarios — add `business_rationale` to the 8 static scenarios + update synthesizer prompt + ScenarioCard frontend

Each PR ships independently behind feature presence checks (frontend tolerates missing fields). Tests-first per the workflow rule.

## Trade-offs

**Why a single executive summary endpoint instead of three?**
Coverage and resolved-issues are derived from the same recent-runs scan. Doing all three on the server keeps the frontend simple (one fetch) and the LLM narrative grounded in the same data. The cost is one larger response payload, well under any practical limit.

**Why not learn the journey list?**
Each scenario already declares `surfaces_covered` — that's authoritative metadata. The "journey" is just the unique combination of those surfaces. No clustering or LLM needed.

**Why FAIL → PASS as the resolved-issues signal?**
It's the cheapest source of truth — derivable from existing run data. Tracking commits/PRs would require either explicit linking from PR descriptions to scenario IDs (brittle) or a webhook from GitHub (overkill for v1). State transitions answer "did the QA agent verify a fix landed?" which is the question that matters.

**Why qa_config/dashboard_prefs as a separate doc?**
Keeps the schedule doc focused on its purpose and avoids merge conflicts when one prefs is updated more often than the other. Same auth + Firestore rules apply.
