# QA — College Fit Testing

## Problem

The QA agent today exclusively exercises the **roadmap** flow:
profile-build → add-colleges → /roadmap → /work-feed. The **college
fit** algorithm — student profile × university profile → fit category,
match %, factor breakdown, essay angles, scholarship matches, etc. —
runs in production every time an operator views a college, but is
**not exercised by any synthetic monitoring**.

The fit algorithm is a single Gemini Flash-Lite LLM call (200-line
prompt) wrapped by deterministic post-processing rules. The output is
high-stakes and operator-visible:

- **`fit_category`** ∈ {SAFETY, TARGET, REACH, SUPER_REACH}
- **`match_percentage`** ∈ [0, 100]
- **4 factor scores**: Academic (40), Holistic (30), Major Fit (15),
  Selectivity adjustment (-15..+5)
- **8 advisory blocks**: essay_angles, application_timeline,
  scholarship_matches, test_strategy, major_strategy,
  demonstrated_interest_tips, red_flags_to_avoid, recommendations

Operators rely on these outputs to advise students. An incorrect
category — calling a 4% acceptance-rate school a TARGET — is a
real-world misadvisement. Today we have no automated detection.

## Goals

1. **Deterministic invariant coverage.** The post-processing rules in
   `fit_computation.py` make many invariants strict, not subjective.
   Synthetic monitoring should catch every regression of those rules:
   - Selectivity floor (`<8%` cannot be SAFETY/TARGET/REACH)
   - Selectivity ceiling (`>=50%` cannot be REACH/SUPER_REACH)
   - Match-% range alignment per category
   - Factor-max bounds (Academic 40, Holistic 30, Major Fit 15,
     Selectivity 5)
   - Required-field presence + types
2. **Selectivity-tier behavioural coverage.** Run a known-good profile
   against schools across all 5 selectivity tiers and assert the
   *relative* category ranking matches expectations.
3. **Synthesizer-driven exploratory scenarios.** Let the LLM-driven
   synthesizer generate fit-targeted scenarios that probe edge cases
   (test-optional, first-gen, intended-major mismatch, low-GPA
   reach, etc.).
4. **Operator-controlled focus.** Wire the Steer panel's existing
   feedback loop so an operator can say *"focus next runs on fit
   accuracy at UCs"* and the synthesizer responds.
5. **Algorithm improvement, when warranted.** Once tests start
   surfacing concrete flaws, propose targeted fixes — but only when
   the data backs them. Not before.

## Non-goals (for Phase 1)

- Not building a "ground-truth fit oracle" (no reference dataset of
  *"actually MIT is REACH for this profile"*). The first cut is
  invariant + relative-ordering testing only.
- Not testing the LLM advisory blocks (essay angles, scholarship
  matches, etc.) for content correctness. Phase 2 introduces an
  LLM-as-judge for those; Phase 1 is structural.
- Not changing the production fit algorithm. We test what's there
  first; algorithm changes follow from evidence.

## Phased plan

### Phase 1 — Foundation (this PR)

- New runner step `compute_fit` calls
  `POST {pm}/compute-single-fit` with `{user_email, university_id}`.
- A library of deterministic fit assertions covering all the
  invariants in §Goals 1.
- One static archetype `fit_ultra_selective_reach` (a strong student
  evaluated against an `<8%`-acceptance school; expect SUPER_REACH).
- New surface name `fit` so the Coverage card on the dashboard shows
  whether this dimension has been tested today.

### Phase 2 — Behavioural coverage

- 4-5 more static archetypes spanning all selectivity tiers + a
  `fit_test_optional` archetype + a `fit_intended_major_mismatch`
  archetype.
- A *cross-college* scenario (`fit_relative_ordering`) that picks 3
  colleges at different selectivity tiers, runs the fit on each, and
  asserts the *match-% ordering* matches selectivity-tier ordering
  (a perfect student should not fit a 4% school better than a 50%
  school).

### Phase 3 — Synthesizer integration

- Extend the synthesizer prompt with a "fit-focused scenario"
  archetype it can produce (alongside today's roadmap-focused ones).
- Surface the fit dimension in the Coverage card + chat grounding so
  operators can ask *"how often did the fit category match the
  selectivity floor?"*.

### Phase 4 — LLM-as-judge for advisory blocks

- For each scenario, after computing fit, run a second LLM call that
  evaluates `essay_angles` + `scholarship_matches` against the
  student profile + university data and asserts grounding (not just
  presence).

### Phase 5 — Algorithm improvement (only if needed)

- Once Phases 1-4 surface a clear flaw — e.g. *"the model produces
  match-% inside the right range but the actual ranking across the 5
  tiers is non-monotonic"* — propose targeted prompt or post-
  processing fixes. Each improvement is its own PR with tests
  proving the regression is fixed.

## Success criteria — Phase 1

- New `compute_fit` step runs successfully against the production
  `profile-manager-v2`.
- Every invariant in §Goals 1 has a unit test in
  `tests/cloud_functions/qa_agent/` and is asserted in the runner.
- `fit_ultra_selective_reach` archetype runs to completion in
  scheduled runs and surfaces in the Coverage card.
- Future regression of any invariant flips the run from PASS to FAIL
  with a clear assertion message.
