# Design: LLM scenario synthesis

Status: Draft (awaiting approval)
Last updated: 2026-05-03
Related PRD: [docs/prd/llm-scenario-synthesis.md](../prd/llm-scenario-synthesis.md)

## Architecture sketch

```
        ┌─────────────────────┐    ┌──────────────────────┐
        │ system_knowledge.md │    │  Last 20 run reports │
        │ (curated, in-repo)  │    │  (Firestore qa_runs) │
        └──────────┬──────────┘    └──────────┬───────────┘
                   │                          │
                   └─────────┬────────────────┘
                             ▼
                ┌─────────────────────────┐
                │  synthesizer.py         │
                │  build_synthesis_prompt │
                │  call_gemini            │
                │  validate_archetype     │
                │  fallback_if_invalid    │
                └────────────┬────────────┘
                             ▼
                ┌─────────────────────────┐
                │  N synthesized          │
                │  archetypes (validated) │
                │  + M static fallback    │
                └────────────┬────────────┘
                             ▼
                ┌─────────────────────────┐
                │  Existing runner        │
                │  (no changes here)      │
                └─────────────────────────┘
```

The synthesizer slots in BEFORE the existing selector. The runner doesn't know whether a scenario was synthesized or static — both look like the same archetype dict shape.

## Data shape: synthesized archetype

Same shape as a static archetype, with two extra fields:

```jsonc
{
  "id": "synth_2026-05-03_a3f9",
  "synthesized": true,                     // marker — surfaces in dashboard
  "synthesis_rationale": "This scenario tests a low-GPA student (3.1) with two reach schools. Last 14 days had zero runs with GPA<3.4 against Tier-1 colleges; recent UC-list flake suggests stress on the per-college path. Targets profile + roadmap.",
  "description": "Junior with 3.1 GPA targeting Stanford and MIT — a stretch profile.",
  "tests": [
    "Resolver picks junior_spring",
    "Profile build accepts GPA below the median of past runs",
    "/roadmap returns a coherent plan even with reach-only college list"
  ],
  "default_student_name": "Sam Chen",
  "profile_template": {
    "grade_level": "11th Grade",
    "graduation_year": 2027,
    "gpa": 3.1,
    "intended_major": "Computer Science",
    "interests": ["robotics", "music"]
  },
  "colleges_template": ["stanford_university", "massachusetts_institute_of_technology"],
  "expected_template_used": "junior_spring",
  "surfaces_covered": ["profile", "college_list", "roadmap"]
}
```

`synthesized: true` is the dashboard's signal to render the "🤖 LLM-generated" badge + the rationale paragraph. `synthesis_rationale` is what the reviewer reads to trust (or distrust) the agent's intuition.

## New module: `cloud_functions/qa_agent/synthesizer.py`

```python
def synthesize_scenarios(
    *,
    n: int,
    history: list[dict],
    system_knowledge: str,
    static_archetype_summaries: list[dict],
    gemini_key: str | None = None,
) -> list[dict]:
    """
    Returns up to n validated synthesized archetypes.
    Falls back to static archetypes when LLM fails or output is invalid.
    """
```

Pipeline:

1. **Build context** — concatenate system_knowledge.md + summarized run history + summary of static archetypes (so the LLM knows what's already covered).
2. **Build prompt** — see "Prompt" section below.
3. **Call Gemini Flash** — with structured JSON output mode if available; plain JSON parsing with fallback otherwise.
4. **Validate each scenario** — schema check (required fields), value bounds (grade in [9, 12], gpa in [0, 4], college IDs against allowlist), test contract (`expected_template_used` matches what the resolver would actually pick for the synthesized profile).
5. **Reject invalid** — drop bad scenarios; log + count toward a per-day "bad LLM output" counter.
6. **Top up with static** — if we end up with fewer than `n` valid synthesized scenarios, pull from the static corpus.

## System knowledge document

A new file: `cloud_functions/qa_agent/system_knowledge.md`

Hand-authored, ~200 lines. Sections:

```markdown
# QA agent — system knowledge

## App overview
The college admissions app helps students build a profile, choose colleges,
and follow a personalized application roadmap. Four key surfaces:
- profile: structured fields (grade, graduation year, GPA, intended major, interests)
- college_list: list of universities the student is targeting
- roadmap: AI-generated semester-by-semester plan
- fit: per-college fit analysis (LLM-driven)

## Endpoints
### POST profile-manager-v2/update-structured-field
- Body: { user_email, field_path, value, operation }
- Sets one profile field at a time. The full profile is built up by N
  sequential calls.
...

## Valid input ranges
- grade_level: "9th Grade" | "10th Grade" | "11th Grade" | "12th Grade"
- graduation_year: integer in [today.year, today.year + 6]
- gpa: float in [0.0, 4.0]
- intended_major: free text
- interests: list of strings (1-5 items)

## Valid college IDs
A small allowlist (the agent must NOT invent IDs; only use these):
- mit, stanford_university, university_of_california_berkeley, ...
- (full list maintained in scenarios/colleges_allowlist.json)

## Known fragile areas (high-priority test targets)
- UC group treatment when a list contains 1 UC vs 4 UCs vs only UCs
- Summer template fallbacks (sophomore_summer → sophomore_spring, etc.)
- Edge GPA values (0.0, 4.0, 4.5 if accepted)
- Missing optional profile fields (intended_major absent, interests empty)

## Persona examples (for variety)
- High-achieving STEM: 3.95 GPA, robotics + competitive programming
- Recruited athlete: 3.5 GPA, varsity sport, narrower school list
- First-gen: middle GPA, regional college mix
- Late starter (12th grade fall, no roadmap yet)
- Specialist: 3.7 GPA, niche major (musicology, classics)

## Anti-patterns (do NOT generate)
- Made-up college IDs (must come from the allowlist)
- GPAs > 4.5 or < 0.0
- Profiles missing required fields (grade_level, graduation_year)
- Scenarios with > 8 colleges (rate-limit hostile)
```

The LLM reads this as plain context. Curated by the human reviewer; updated as the app grows.

## The prompt

```
You are a senior QA engineer planning the next test pass for a college
admissions app. Your job is to produce {n} synthesized test scenarios
that target gaps and risks in the recent test history.

# System you're testing
{system_knowledge}

# Recent run history (last 20 runs)
For each run:
- Scenarios that ran (id + which surfaces touched)
- Pass/fail per scenario
- Notable failed assertions

{history_summary}

# Coverage gaps in the last 14 days
- Surfaces with the fewest runs: {under_tested_surfaces}
- Persona shapes that haven't been tested: {persona_gaps}
- GPA buckets under-represented: {gpa_gaps}

# What the static corpus already covers (don't re-create these)
{static_summary}

# Your task
Generate exactly {n} test scenarios in JSON. Each scenario must:
1. Target a gap or risk you observe — not a routine case the corpus
   already handles.
2. Stay within valid input ranges (see above).
3. Include a `synthesis_rationale` field of 2-3 sentences explaining
   what gap/risk the scenario targets and why.
4. Include 3-6 `tests` bullets — what the scenario verifies in plain
   English.
5. Use only college IDs from the allowlist.

Return JSON only:
{
  "scenarios": [ {schema} ]
}
```

Output validation:
- JSON parse OK
- Each scenario has all required fields
- `colleges_template` entries are in the allowlist
- `gpa` is in [0, 4]
- `grade_level` is one of the valid strings
- `expected_template_used` matches `compute_template_key(grade, semester)` deterministically (i.e., the agent isn't making up template names)

Anything that fails validation → discard, log, fall back to static.

## Wiring into `main.py` (the existing `_handle_run`)

Replace the existing static-only selection with a hybrid pick:

```python
# Existing
chosen = corpus.select_scenarios(archetypes, history, n=n)

# After
synth_n = int(os.getenv("QA_SYNTHESIS_COUNT", "2"))
static_n = max(1, n - synth_n)

synthesized = synthesizer.synthesize_scenarios(
    n=synth_n,
    history=load_recent_runs(20),
    system_knowledge=load_system_knowledge(),
    static_archetype_summaries=summarize(archetypes),
    gemini_key=cfg["GEMINI_API_KEY"],
)
static_picks = corpus.select_scenarios(archetypes, history, n=static_n)
chosen = synthesized + static_picks
```

If `synthesize_scenarios()` returns fewer than `synth_n` (validation failures), the static count automatically takes up the slack via top-up logic inside the synthesizer.

## Dashboard surfacing

`ScenarioCard` (existing component) gets two additions:

1. **Synthesized badge** — small "🤖 LLM-generated" pill next to the scenario id when `scenario.synthesized === true`.
2. **Synthesis rationale block** — between the description and the `tests` bullets, render a callout: "Why this was generated: {synthesis_rationale}".

In `ExecutiveSummary`, add a new metric:
- "X% of scenarios synthesized this week" — rolling count.

## Validation: the resolver-aware sanity check

Before a synthesized scenario hits the runner, we do one extra check beyond schema:

> Compute `expected_template = resolver.pick(grade, today.semester, graduation_year)`. If the LLM's `expected_template_used` doesn't match, reject the scenario.

This catches scenarios where the LLM hallucinated a template name (e.g., claimed `senior_winter` exists when it doesn't). The runner has the resolver in code; we use it pre-run as a contract check on synthesized scenarios.

This is a harder gate than the JSON schema check and is the load-bearing safety mechanism.

## Adaptive feedback loop — concrete signals

The history summary the LLM sees includes:

```
- Surface coverage (last 14d):
    profile:      18 runs, 1 failure
    college_list: 17 runs, 0 failures
    roadmap:      18 runs, 1 failure (UC group, run abc)
    fit:           3 runs, 0 failures   ← under-tested
- Recent failures (last 7d):
    run xyz: senior_fall_application_crunch failed at roadmap step
        — metadata.template_used was 'senior_spring' (expected senior_fall)
        — variation: low GPA (3.2), 6 colleges including 3 UCs
- Persona shapes covered (last 30d):
    high-achieving stem: 12 runs
    humanities: 4 runs
    recruited athlete: 0 runs   ← gap
    first-gen: 1 run            ← gap
    late starter: 2 runs
- GPA distribution (last 30d):
    [0-2.5]:   0 runs
    [2.5-3.0]: 1 run            ← under-represented
    [3.0-3.5]: 2 runs
    [3.5-4.0]: 14 runs
```

The LLM reads these and proposes scenarios that target the gaps. Concrete behavior:
- "Recruited athlete: 0 runs" → propose a recruited-athlete scenario.
- "GPA [2.5-3.0]: 1 run" → propose a low-GPA scenario.
- "Recent UC-group failure" → propose another UC-group scenario with a slightly different shape.

This is the agent "thinking out of the box" — it's not random; it's targeting evidence.

## New backend tests (TDD: written first, fail, then implement)

`tests/cloud_functions/qa_agent/test_synthesizer.py`:

- `test_validate_rejects_invalid_college_id` — synthesizer rejects scenarios with college IDs not in the allowlist.
- `test_validate_rejects_out_of_range_gpa` — gpa=5.0 rejected.
- `test_validate_rejects_template_hallucination` — `expected_template_used` that doesn't match resolver output → rejected.
- `test_synthesizer_falls_back_to_static_when_llm_unavailable` — no GEMINI_API_KEY → returns 0 synthesized + N static.
- `test_synthesizer_falls_back_when_llm_returns_malformed_json` — LLM returns garbage → 0 synthesized; full fallback.
- `test_synthesizer_returns_partial_when_some_scenarios_invalid` — LLM returns 3 scenarios, 1 invalid → returns 2 valid + 1 static fallback.
- `test_history_summary_includes_coverage_gaps` — given a history, the summary names the under-tested surfaces.
- `test_resolver_validation_independent_of_llm` — runs synchronously, no LLM call.

## New frontend tests

`frontend/src/__tests__/SynthesizedBadge.test.jsx`:
- Badge renders only when `scenario.synthesized === true`.
- Rationale text rendered.
- ScenarioCard distinguishes synthesized from static visually.

## Phasing — implementation PRs

| PR | Scope |
|---|---|
| 1 | `synthesizer.py` + `system_knowledge.md` + colleges allowlist + validation + tests. Synthesizer is invokable but not yet wired into the run loop (so we can iterate the prompt safely). |
| 2 | Wire synthesizer into `_handle_run` behind `QA_SYNTHESIS_COUNT` env var (default 0; flip to 2 once prompt is stable). |
| 3 | Frontend: synthesized badge + rationale rendering on ScenarioCard + "% synthesized" metric in ExecutiveSummary. |
| 4 | Adaptive loop tightening — history summary improvements + per-persona / per-GPA bucket tracking. |

PRs 1+2+3 are bundle-able if we trust the prompt out of the gate; safer to ship 1 alone, observe a few days of synthesizer-only output, then flip the count up.

## Risks

- **LLM hallucinations.** Synthesized scenarios with made-up template names, made-up college IDs, or out-of-range values. Mitigation: hard validation gate (resolver pre-check + value-range check + allowlist). Bad output is dropped + counted, never run.
- **Drift in system knowledge.** The static markdown can lag behind reality. Mitigation: when the runner discovers a real endpoint shape mismatch (the agent hits a 404 because the system_knowledge claims an endpoint exists that doesn't), surface that in the dashboard so the human knows to update the doc.
- **LLM cost runaway.** Capped by `QA_SYNTHESIS_DAILY_CAP` (default 50 calls/day). Above that, fall back to static for the rest of the day.
- **Same scenario repeated across runs.** The LLM doesn't see its own output as "done" — could propose the same shape twice. Mitigation: per-run-id seeding + a cheap dedup against the last 5 synthesized runs (by hash of the rationale + profile shape).
- **Reviewer trust.** If the rationale isn't well-written, reviewers will lose trust quickly. Mitigation: prompt explicitly demands "concrete reasoning, no fluff" + we audit the first 50 synthesized scenarios manually before flipping the synth-count up.

## Alternatives considered

- **Multi-step planning (planner → critic → executor)**. More principled but 3x the cost and 2x the latency. Single-step synthesis is enough for v1; can layer a critic on top later if quality plateaus.
- **Persistent corpus growth (synthesized → static)**. The "promote a synthesized scenario to a permanent archetype" workflow needs human review UX which is its own PR. Out of scope for v1.
- **LLM owns the assertions too**. Rejected — assertions are the part we trust most; we don't want them moving with the prompt. Static assertion library + LLM-generated input is the right split.
- **Use a cheaper LLM** (e.g., Haiku-class). Considered. Gemini Flash is already cheap enough; no need to optimize further.
- **Drop static archetypes entirely**. Too risky for v1. Static is the safety net when synthesis is broken; we revisit once the synthesizer has months of clean output.
