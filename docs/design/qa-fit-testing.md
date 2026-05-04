# Design — QA College Fit Testing (Phase 1)

Spec: docs/prd/qa-fit-testing.md.

## What I learned about the current algorithm

Source: `cloud_functions/profile_manager_v2/fit_computation.py`.

**Inputs**:
- Student profile (Firestore `profiles/{email}` doc): GPA, SAT/ACT,
  AP count, ECs, awards, intended major, test_optional flag, etc.
- University profile (KB `kb_universities/{id}`): acceptance rate,
  admitted_student_profile, scholarships, essay prompts, programs.

**Endpoint**: `POST {profile_manager_v2_url}/compute-single-fit`
with `{user_email, university_id}` → `{success, fit_analysis}`.

**Algorithm shape**:
1. Load profile + university.
2. Bucket the school into one of 5 selectivity tiers based on
   `acceptance_rate`:
   - `<8%`   → ULTRA_SELECTIVE, floor SUPER_REACH
   - `8-15%` → HIGHLY_SELECTIVE, floor REACH
   - `15-25%`→ VERY_SELECTIVE, no floor
   - `25-40%`→ SELECTIVE, no floor
   - `>=40%` → ACCESSIBLE, no floor (ceiling SAFETY at >=50%)
3. Single Gemini Flash-Lite LLM call with a 200-line prompt that
   asks for `match_percentage`, `fit_category`, `factors[4]`,
   `gap_analysis`, `essay_angles[]`, `application_timeline`,
   `scholarship_matches[]`, `test_strategy`, `major_strategy`,
   `demonstrated_interest_tips[]`, `red_flags_to_avoid[]`,
   `recommendations[]`.
4. **Deterministic post-processing** (cannot be overridden by LLM):
   - **Selectivity floor**: clamp category to floor when `acc < 15%`.
   - **Selectivity ceiling**: clamp category to SAFETY when `acc>=50`,
     to TARGET when `acc>=25`.
   - **Match-% range alignment** per category: SAFETY 75-100,
     TARGET 55-74, REACH 35-54, SUPER_REACH 0-34.
   - **Category whitelist**: must be in {SAFETY, TARGET, REACH,
     SUPER_REACH}.
5. **Fallback**: on LLM failure, derive category from acceptance rate
   alone; return `match_percentage=50`.

The post-processing rules are **strict invariants**. They are the
right place for our first round of testing — high signal, no
subjective judgement required.

## Phase 1 scope (this PR)

### Backend — runner step

`cloud_functions/qa_agent/runner.py` gains a `compute_fit` step
inserted between `roadmap_generate` and `work_feed`. It only fires
when the scenario carries a new `fit_target_college` field.

```python
# Optional fit-analysis step. Skipped unless the archetype declares
# a fit_target_college (default: scenarios stay roadmap-focused).
fit_target = scenario.get("fit_target_college")
if fit_target:
    fit_ctx = poster(
        f"{pm}/compute-single-fit",
        {"user_email": cfg.test_user_email, "university_id": fit_target},
        admin_token=cfg.admin_token,
    )
    expected_floor = scenario.get("fit_expected_floor")  # optional
    expected_category = scenario.get("fit_expected_category")
    fit_asserts = [
        assertions.status_is_2xx(),
        assertions.key_equals("success", True),
        # ... see fit_assertions below
    ]
    if expected_category:
        fit_asserts.append(
            assertions.key_equals("fit_analysis.fit_category", expected_category)
        )
    steps.append(_step(f"compute_fit:{fit_target}", fit_ctx, fit_asserts))
```

### Backend — assertion library

`cloud_functions/qa_agent/fit_assertions.py` (new module):

```python
def category_in_valid_set(path="fit_analysis.fit_category") -> AssertionFn:
    """Category must be one of {SAFETY, TARGET, REACH, SUPER_REACH}."""

def match_percentage_in_range(path="fit_analysis.match_percentage") -> AssertionFn:
    """match_percentage ∈ [0, 100]."""

def match_percentage_aligns_with_category(
    pct_path="fit_analysis.match_percentage",
    cat_path="fit_analysis.fit_category",
) -> AssertionFn:
    """Match-% must be in the band declared for its category:
    SAFETY 75-100, TARGET 55-74, REACH 35-54, SUPER_REACH 0-34.
    Catches LLM/post-processor drift."""

def selectivity_floor_respected(
    cat_path="fit_analysis.fit_category",
    rate_path="fit_analysis.acceptance_rate",
) -> AssertionFn:
    """If acceptance_rate < 8, category MUST be SUPER_REACH.
    If 8 <= acceptance_rate < 15, category MUST be SUPER_REACH or REACH.
    Catches selectivity-floor regression — the production override the
    LLM cannot beat."""

def selectivity_ceiling_respected(...) -> AssertionFn:
    """If acceptance_rate >= 50, category MUST be SAFETY.
    If acceptance_rate >= 25, category MUST be SAFETY or TARGET."""

def factor_bounds_respected(path="fit_analysis.factors") -> AssertionFn:
    """factors[*].score ∈ [0, factors[*].max] for each entry, and
    the four factor names match {Academic, Holistic, Major Fit,
    Selectivity}."""

def required_advisory_blocks_present() -> AssertionFn:
    """Phase 1 doesn't judge content quality; just asserts the 8 blocks
    exist and are non-empty arrays/objects."""
```

### Backend — first archetype

`cloud_functions/qa_agent/scenarios/fit_ultra_selective_reach.json`:

```json
{
  "id": "fit_ultra_selective_reach",
  "description": "Strong junior evaluated against an <8% school. Expect SUPER_REACH regardless of profile strength (selectivity floor).",
  "business_rationale": "Catches regressions in the selectivity-floor rule — the strict guarantee that no student profile can elevate an ultra-selective school out of SUPER_REACH. A real-world misadvisement here would tell a strong-but-realistic family that an Ivy is a TARGET. Worth detecting in monitoring.",
  "default_student_name": "Sam Chen",
  "profile_template": {
    "grade_level": "11th Grade",
    "graduation_year": 2027,
    "gpa": 3.95,
    "intended_major": "Computer Science",
    "interests": ["robotics", "research"]
  },
  "colleges_template": ["massachusetts_institute_of_technology"],
  "fit_target_college": "massachusetts_institute_of_technology",
  "fit_expected_category": "SUPER_REACH",
  "expected_template_used": "junior_spring",
  "surfaces_covered": ["profile", "college_list", "roadmap", "fit"],
  "tests": [
    "Selectivity floor: ultra-selective school stays SUPER_REACH for any profile",
    "match_percentage in [0, 34] when fit_category is SUPER_REACH",
    "All four factors present with correct max values",
    "8 advisory blocks present"
  ]
}
```

### Coverage card surface

The Coverage card already groups scenarios by `surfaces_covered`. By
adding `"fit"` to the new archetype, the dashboard shows a new journey
"Profile build → college list → roadmap → fit analysis", giving
operators a visible signal that the fit dimension is being tested.

## Tests (Phase 1)

`tests/cloud_functions/qa_agent/test_fit_assertions.py` — pure unit
tests of each assertion against synthetic fit responses:

- `category_in_valid_set` passes on all 4 categories, fails on
  `"INVALID"`, `null`, missing key.
- `match_percentage_in_range` passes on 50, fails on -1, 101,
  non-numeric, missing.
- `match_percentage_aligns_with_category` — happy path for each of
  the 4 categories, regression cases for each (e.g. SUPER_REACH at
  match=50 fails with a clear message).
- `selectivity_floor_respected` — `<8%` + non-SUPER_REACH fails;
  `<8%` + SUPER_REACH passes; `15%` + REACH passes; etc.
- `selectivity_ceiling_respected` — `>=50%` + non-SAFETY fails;
  `>=50%` + SAFETY passes.
- `factor_bounds_respected` — each factor at its max passes; 41 on
  Academic fails; missing factor fails.
- `required_advisory_blocks_present` — all 8 blocks present passes;
  empty essay_angles fails.

`tests/cloud_functions/qa_agent/test_runner.py` — extend existing
runner tests with a fixture archetype that sets `fit_target_college`
and a stubbed poster that returns a synthetic fit response. Verify
the `compute_fit` step is added when the field is present and
omitted otherwise.

## Phase 2b — Cross-school relative ordering

Built on Phase 1's foundation; no breaking changes to existing
archetypes.

**Runner extension:** the `compute_fit` block now reads
`fit_target_colleges` (list) in addition to `fit_target_college`
(string). When the list has 2+ entries, the runner:
1. Runs a `compute_fit:<uni>` step per school with all 7 Phase 1
   invariants.
2. Skips the single-value `fit_expected_category` pin (it can't
   apply across multiple schools at different tiers).
3. Appends a synthetic `fit_relative_ordering` step whose assertions
   come from `fit_assertions.check_category_rank_monotonic_with_selectivity`.

**The cross-school assertion:**
- Reads `acceptance_rate` and `fit_category` from each collected
  response.
- Sorts by `acceptance_rate` ascending (most-selective first).
- For each consecutive pair, asserts `cur.rank >= prev.rank` where
  rank is `{SUPER_REACH:0, REACH:1, TARGET:2, SAFETY:3}`.
- Returns one `AssertionResult` per pair so failures are pinpointable
  ("ohio_state vs mit: ohio_state at 60% is TARGET but mit at 4% is
  SAFETY — student should never get a worse fit at a less-selective
  school").

**The new archetype `fit_relative_ordering`** exercises three schools
in a single run: MIT (4%) + UC Berkeley (11%) + Ohio State (60%).
Production data from Phases 1+2a shows the algorithm naturally
produces the right ordering for these three; this PR makes that an
explicit, programmatic test so any future drift fails CI rather than
silently degrading operator experience.

## Risk

Low for Phase 1:
- The runner step is gated behind a per-archetype field; existing
  scenarios are unchanged.
- Assertions are pure functions over known response shapes; no
  network in tests.
- The new archetype runs against a real production endpoint, but
  `compute-single-fit` is read-only (it doesn't mutate user data
  beyond saving the fit analysis).
- Cost: one extra Gemini Flash-Lite call per scheduled run (the fit
  archetype runs once per run when picked). Pennies.
