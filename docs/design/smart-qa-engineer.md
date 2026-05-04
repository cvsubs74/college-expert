# Design: The smartest QA engineer agent

Status: Draft (awaiting approval)
Last updated: 2026-05-03
Related PRD: [docs/prd/smart-qa-engineer.md](../prd/smart-qa-engineer.md)

## What changes, at a glance

```
                      v1 (this work)
                      ──────────────
         ┌─────────────────────────────────────────────────────┐
         │  qa-agent (existing) gets four new responsibilities │
         │                                                     │
         │  1. plan a run        → test_plan narrative         │
         │  2. select smarter    → coverage + failure aware    │
         │  3. summarize outcome → outcome narrative           │
         │  4. honor schedule    → reads qa_config/schedule    │
         └─────────────────────────────────────────────────────┘

                        Frontend (existing dashboard)
                        ─────────────────────────────
         ┌─────────────────────────────────────────────────────┐
         │  /qa-runs                                           │
         │   ┌───────────────────────────────────────────────┐ │
         │   │  ExecutiveSummary (NEW, top of page)          │ │
         │   │   pass-rate × 7d/30d, surface badges, story   │ │
         │   └───────────────────────────────────────────────┘ │
         │   ┌───────────────────────────────────────────────┐ │
         │   │  ScheduleEditor (NEW)                         │ │
         │   │   pick time, freq, days, timezone             │ │
         │   └───────────────────────────────────────────────┘ │
         │   RunNowPanel + RunsTable (existing)                │
         │                                                     │
         │  /qa-runs/<id>                                      │
         │   ┌───────────────────────────────────────────────┐ │
         │   │  TestPlanCard (NEW, top)                      │ │
         │   │  ScenarioCard with `tests` bullets (enriched) │ │
         │   │  OutcomeNarrative (NEW, bottom)               │ │
         │   └───────────────────────────────────────────────┘ │
         └─────────────────────────────────────────────────────┘
```

## Run report shape (additions)

```jsonc
{
  "run_id": "run_...",
  "started_at": "...",
  "ended_at":   "...",
  "trigger": "schedule" | "manual",
  "actor":   "...",
  "summary": { "total": 4, "pass": 3, "fail": 1 },

  // NEW — written before any scenario runs
  "test_plan": {
    "narrative":  "...",          // 2-3 sentences
    "rationale":  "untried_recently | recently_failed | coverage_gap | rotation",
    "coverage":   { "profile": 1, "college_list": 1, "roadmap": 1, "fit": 0 }
  },

  // NEW — written after every scenario runs
  "outcome": {
    "narrative":  "...",          // 2-3 sentences
    "verdict":    "all_pass" | "minor_flake" | "regression_likely",
    "first_look_at": [             // pointer at where to investigate first
      { "scenario_id": "...", "step": "...", "reason": "..." }
    ]
  },

  "scenarios": [
    {
      "scenario_id": "...",
      "description": "...",
      // NEW — copied from archetype, rendered as bullets
      "tests": [
        "Resolver picks junior_spring",
        "5 colleges add via /add-to-list",
        "Roadmap returns metadata.template_used == junior_spring"
      ],
      "variation":  { ... },
      "steps":      [ ... ]
    }
  ]
}
```

## Backend changes

### New module: `cloud_functions/qa_agent/planner.py`

Generates the `test_plan` and `outcome` narratives. Two entry points:

```python
def build_plan(chosen_archetypes, history, *, gemini_key=None) -> dict:
    """Pre-run. Returns {narrative, rationale, coverage}.
    Falls back to a deterministic template when LLM unavailable."""

def build_outcome(report, *, gemini_key=None) -> dict:
    """Post-run. Returns {narrative, verdict, first_look_at}.
    Verdict is computed deterministically from pass/fail counts;
    narrative is LLM-authored (with fallback)."""
```

Prompts:

**Plan prompt:**
```
You are a senior QA engineer planning a synthetic-monitoring run. The
agent picked these N scenarios:

  <id>: <description>  (last run: <when>, last result: <pass/fail>)
  ...

Coverage of surfaces this run touches: <comma-separated>.

In 2-3 sentences:
1. State what this run is testing in plain English.
2. Note any deliberate emphasis (e.g., re-testing a recently-failed
   scenario, exploring an under-tested surface).
3. Be direct. No preamble. No disclaimers.
```

**Outcome prompt:**
```
You are a senior QA engineer reviewing the run you just oversaw. Here
is the run summary and the failing steps (truncated):

  <pass>/<total> scenarios passed.
  Failing scenarios:
    <id> — failed at step '<name>': <first failed assertion message>
    ...

In 2-3 sentences:
1. State what the run verified.
2. State what failed and what it most likely means (agent bug vs app
   regression — refer to the failing assertions for evidence).
3. Recommend the single smartest first place to investigate.

Be direct.
```

Both prompts get a deterministic fallback that lists what was run + what failed without LLM phrasing — keeps the report readable when Gemini is down.

### Selection policy upgrades (`corpus.py`)

Add two signals on top of the existing untried-first / recently-failed / random rotation:

1. **Coverage gap** — for each surface (`profile`, `college_list`, `roadmap`, `fit`), compute how many of the last 14 days of runs touched it. Surfaces under the median get a +1 weight on their archetypes.
2. **Variation budget** — when an archetype is chosen, the LLM variation step is biased toward harder cases (lower GPA delta range, less common majors, etc.) more often when the archetype has been run > 3 times in the last week.

The selection function signature stays the same; the policy is implemented as a small `score(archetype, history, coverage_window)` function.

### Schedule (`schedule.py`)

A new module with two operations:

```python
def load_schedule(db=None) -> dict:
    """Reads qa_config/schedule. Returns {time, days, frequency, timezone}.
    Defaults to {time: '06:00', days: ['mon'..'sun'], frequency: 'daily', timezone: 'America/Los_Angeles'}."""

def should_run_now(schedule: dict, now: datetime) -> bool:
    """Returns True iff `now` matches the schedule (within ±5min window)."""
```

Schedule doc shape (`qa_config/schedule`):

```json
{
  "frequency": "daily" | "twice_daily" | "weekly" | "off",
  "times":     ["06:00", "13:00"],
  "days":      ["mon", "tue", "wed", "thu", "fri"],
  "timezone":  "America/Los_Angeles",
  "updated_at": "...",
  "updated_by": "<email>"
}
```

A single Cloud Scheduler job fires `qa-agent /run` **every hour** with `{"trigger": "schedule_check"}`. The agent calls `should_run_now()` and either proceeds or no-ops with a `{ "skipped": true }` response. This keeps the schedule purely Firestore-driven; no IAM for Cloud Scheduler Admin needed.

The existing daily Cloud Scheduler job (if any) gets retired in favor of the hourly poller.

### Two new endpoints on qa-agent

```
GET  /schedule         → returns the current schedule doc (auth-gated)
POST /schedule         → updates the schedule (auth-gated)
```

Auth: same dual-auth as the rest of the agent (`X-Admin-Token` or Firebase ID token + email allowlist).

### Archetype `tests` field

Schema additions to each `cloud_functions/qa_agent/scenarios/*.json`:

```jsonc
{
  "id": "junior_spring_5school",
  "description": "Junior in spring with a 5-school reach-and-target list mixing T20s and UCs.",
  "tests": [                                       // NEW
    "Resolver picks junior_spring template based on graduation_year=2027 + spring",
    "5 colleges added via /add-to-list (no UC group)",
    "Roadmap response carries metadata.template_used == junior_spring",
    "All 5 colleges show up in /work-feed deadlines"
  ],
  "profile_template": { ... },
  ...
}
```

Hand-authored per archetype. The runner copies the field into each scenario's record at run time.

## Frontend changes

### `/qa-runs` — Executive summary card

`frontend/src/components/qa/ExecutiveSummary.jsx`

Reads the last 30 days of `qa_runs/` directly from Firestore (the dashboard already does this). Computes:

- **Pass rate** for last 7d and last 30d (% of runs with `summary.fail == 0`)
- **Trend arrow** (compare 7d to 30d; up if 7d > 30d, down if 7d < 30d - 5%)
- **Surface badges** — for each surface, count runs that touched it in last 14d, count failures, render small green/yellow/red chip
- **Health narrative** — fetched on demand from a new `GET /summary` endpoint on qa-agent that runs the LLM. Cached client-side for 5 minutes.

### `/qa-runs` — Schedule editor

`frontend/src/components/qa/ScheduleEditor.jsx`

A small inline form:
- Frequency dropdown
- Times (one or two depending on frequency)
- Days-of-week checkboxes (greyed for "daily")
- Timezone dropdown
- Save button → `POST /schedule`
- Last-changed line ("Updated by cvsubs@gmail.com 2 hrs ago")

### `/qa-runs/:runId` — Test plan + outcome

Two new components rendered on the detail page:

- **`TestPlanCard`** at the top (above scenario list): shows `test_plan.narrative` + the rationale chip + a small coverage row (e.g., "Surfaces: profile, college_list, roadmap").
- **`OutcomeCard`** at the bottom (below scenario list): shows `outcome.narrative`, the verdict badge, and a "First look at →" pointer that scrolls to the named scenario/step.

### `ScenarioCard` enrichment

Render the `tests` array as a bullet list in each scenario's expanded body, above the steps:

```
What this scenario tests:
  • Resolver picks junior_spring template
  • 5 colleges added via /add-to-list
  • Roadmap returns metadata.template_used == junior_spring
  • All 5 colleges show up in /work-feed deadlines
```

## qa-agent flow with the new pieces

```
hourly Cloud Scheduler tick
  ↓
qa-agent /run with {"trigger": "schedule_check"}
  ↓
load_schedule()
  ├─ should_run_now(now)? false → respond {skipped: true}, exit
  └─ true → continue ↓
load_archetypes() + load_history(30d) + load_coverage(14d)
  ↓
select_scenarios(...) using new score()
  ↓
build_plan(chosen, history) → test_plan dict
  ↓ (parallel for each scenario)
generate_variation(archetype) → variation
apply_variation(archetype, variation) → scenario
run_scenario(scenario, run_cfg) → result with steps
  ↓
build_outcome(report) → outcome dict
  ↓
write_report({test_plan, outcome, scenarios, ...})
  ↓
update_history per scenario (existing)
```

## Testing strategy

- **planner.py** — unit tests cover prompt building, fallback path, output validation.
- **schedule.py** — unit tests cover `should_run_now()` across timezone, frequency, day-of-week, and edge cases (5-min window).
- **selection score** — unit tests cover coverage-bias and failure-bias behaviors with a deterministic random seed.
- **/schedule endpoint** — unit tests cover read + write + auth gates.
- **Frontend** — Vitest for ExecutiveSummary (mocked Firestore docs), ScheduleEditor (form submit posts to mocked endpoint), TestPlanCard / OutcomeCard render the right bits.
- **End-to-end smoke** — manual test post-deploy: change schedule to "in 1 minute", confirm hourly poll fires (within 1 hour), confirm test_plan + outcome show up on the detail page.

## Risks

- **LLM narrative drift.** Bad prompts can produce confident-but-wrong analysis. Mitigation: deterministic fallback always available; verdict field is computed deterministically from pass/fail counts (never LLM-derived); we explicitly flag narratives as "AI-generated, verify before acting."
- **Hourly poll overhead.** 24 invocations per day at minimal cost (function only does a Firestore read + comparison and exits). ~$0.01/month. Negligible.
- **Schedule miss window.** Schedule changes take up to 1 hour to take effect (next hourly poll). Acceptable for synthetic monitoring; we surface the next-fire time in the schedule editor so the user knows when to expect their change.
- **Coverage tracking accuracy.** A surface counts as "covered" if any scenario in a run touched it. If a scenario claims to test a surface but its assertions are weak, we'd over-count. Mitigation: `surfaces_covered` is hand-authored on each archetype and reviewed as part of archetype changes.
- **Token cost runaway.** Capped: 1 plan call + 1 outcome call + 1 summary call per run, ≤ 4 runs per day, ≤ ~$0.02/day for narratives at Gemini Flash pricing. Will alert if monthly LLM spend > $5.

## Phasing — implementation PRs

| PR | Scope |
|---|---|
| 1 | `planner.py` (test_plan + outcome) + run-report shape additions + frontend TestPlanCard + OutcomeCard + per-archetype `tests` field rendering |
| 2 | `schedule.py` + `GET/POST /schedule` endpoints + ScheduleEditor UI + hourly Cloud Scheduler poll + retire old daily job |
| 3 | ExecutiveSummary card + `GET /summary` endpoint + surface health badges + 7d/30d pass-rate metric |
| 4 | Coverage-aware + failure-focused selection upgrades + new tests on `corpus.score()` |

Each PR independently shippable; PR 1 is the highest user-visible value (richer reports). PR 2 unblocks the user's "I want to choose when tests run" ask. PR 3 lands the executive summary.

## Alternatives considered

- **Use Cloud Scheduler Admin API to update the job directly when the schedule changes.** Rejected for v1: needs broader IAM and the schedule-change UX is not so latency-sensitive that an hourly poll is bad. Revisit if users want minute-precision schedules.
- **Bake the test plan + outcome generation into the runner itself instead of a separate planner module.** Rejected: keeps prompt logic + runner logic interleaved, harder to test in isolation. Separate module is cleaner.
- **Generate the executive summary on every run write (server-side) and store at `qa_summary/today`.** Considered. Cheaper if dashboard traffic is heavy; more moving parts if not. Stick with live computation for v1; switch if the page slows past 1s.
- **Synthesize new archetypes immediately in v1.** Rejected: premature. The synthesis output needs human review before it joins the corpus, and we don't have that workflow yet. Defer to v2.
