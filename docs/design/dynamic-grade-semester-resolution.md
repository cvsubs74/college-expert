# Design: Dynamic grade & semester resolution on /roadmap

Status: Approved (shipped in PR #5, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/dynamic-grade-semester-resolution.md](../prd/dynamic-grade-semester-resolution.md)

## Resolver

In [cloud_functions/counselor_agent/planner.py](../../cloud_functions/counselor_agent/planner.py), `resolve_template_key(caller_grade, caller_semester, profile, today)` returns `(template_key, grade, semester, source)` using the priority order below.

### Priority order

1. **`source = "caller"`** — both `caller_grade` and `caller_semester` are present. Use both verbatim. The frontend has explicitly told us what to render; honor it.
2. **`source = "profile"`** — `profile.graduation_year` is present. Compute grade from `(graduation_year - today.year)` then clamp to `[freshman, senior]`. Use `caller_semester` if provided, else compute it from `today` (Aug-Dec→fall, Jan-May→spring, Jun-Jul→summer).
3. **`source = "caller-grade-only"`** — no profile, but `caller_grade` is present. Use it with computed semester.
4. **`source = "default"`** — nothing else worked. Return `senior_fall`. This is the conservative fallback (a senior at the start of application season has the broadest, most-content-rich template; everything else degrades gracefully if the template isn't perfect for them).

Note the asymmetry: `caller_semester` alone (without `caller_grade`) IS used to override the computed semester. This protects against the legacy frontend's hardcoded `'11th Grade'` (which is why `caller_grade` alone is ignored) while still allowing semester previews.

### Grade clamping

```python
years_until_grad = profile["graduation_year"] - today.year
if years_until_grad >= 4:        grade = "freshman"
elif years_until_grad == 3:      grade = "sophomore"
elif years_until_grad == 2:      grade = "junior"
else:                            grade = "senior"   # 1, 0, or negative
```

This clamps middle-schoolers (≥4 years out) to freshman and post-grads to senior. Both edges are real — the app gets used by students who signed up early and by students who are between admit decisions.

### Semester computation

```python
month = today.month
if month in (8, 9, 10, 11, 12):  semester = "fall"
elif month in (1, 2, 3, 4, 5):   semester = "spring"
else:                             semester = "summer"   # 6, 7
```

### Template fallback

Not every (grade, semester) has a template. The fallback table:

| Computed | Falls back to |
|---|---|
| `freshman_summer` | `freshman_spring` |
| `sophomore_summer` | `sophomore_spring` |
| `senior_summer` | `senior_spring` |
| `junior_summer` | `junior_summer` (HAS its own; no fallback needed) |

`metadata.semester_used` reflects what was computed (so the UI can label the chip correctly), but `metadata.template_used` reflects what actually got rendered.

## Endpoint changes

`POST /roadmap` now accepts:

```json
{
  "user_email": "...",
  "grade_level": "11th Grade" (optional),
  "semester": "spring" (optional)
}
```

`grade_level` is parsed leniently — accepts "11th Grade", "11", "junior", "Junior", etc. Lookup table.

Response gains a `metadata` object:

```json
{
  "metadata": {
    "template_used": "junior_spring",
    "grade_used": "junior",
    "semester_used": "spring",
    "resolution_source": "profile" | "caller" | "caller-grade-only" | "default",
    "colleges_count": 3,
    "personalized": true,
    "last_updated": "2026-04-15T12:00:00"
  }
}
```

## Profile fetch

`generate_roadmap()` calls `get_student_profile(user_email)` (existing helper, hits `profile_manager_v2`) and pulls `graduation_year` off the result. If the call fails or the field is absent, the resolver falls through to `caller-grade-only` or `default`.

## Testing strategy

- Unit tests in `tests/cloud_functions/counselor_agent/test_planner.py` cover the resolver in isolation: every priority branch, the clamping edges, the fallback table.
- Integration tests in `tests/cloud_functions/counselor_agent/test_generate_roadmap_scenarios.py` (added later, PR #18) drive the full endpoint with stubbed profile/college-context fetches and assert on the returned `metadata.template_used` for all 12 grade × semester combinations plus the major edges (already-graduated, far-future, summer fallbacks, missing graduation_year, etc.). 34 scenario tests.

## Risks

- **Profile fetch latency added to every /roadmap call.** `get_student_profile` adds one HTTP hop to `profile_manager_v2`. Acceptable: it's already done by other parts of the same flow (the deadline aggregation), so the cost is amortized.
- **A profile with `graduation_year=null`** — handled: falls through to default and the test suite pins this down.
- **Grade-text parsing leniency.** "Junior" vs. "junior" vs. "11th Grade" all map to `junior`. The lookup is conservative (case-insensitive, trims). An unrecognized string falls through to source=default.
- **Date-of-truth.** `today` is `datetime.now()` server-side. The client may be in a different timezone, so a student in Hawaii at 11pm on Aug 31 sees Aug 31 (fall) while the server sees Sept 1 (still fall). Acceptable — the boundary cases (last day of a month) are hours wide and the templates are weeks wide.

## Alternatives considered

- **Compute (grade, semester) on the client only.** Rejected: forces every client (current and future, including notification emails) to re-implement the resolver. Server-owned policy is the cleaner choice.
- **Hardcode the priority differently — e.g., profile always wins, even over caller.** Rejected: kills the explicit-override use case (frontend previews of a different semester, manual support overrides). Caller-wins-when-both-present preserves debugging power.
- **Refuse to render a roadmap when `graduation_year` is missing.** Rejected: degrades the experience for students who skipped that onboarding step. Defaulting to senior_fall is a better failure mode than blank screen.
