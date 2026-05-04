# QA agent — system knowledge

Read by `synthesizer.py` as context for the LLM. Update this file when
the app's surfaces change. Hand-curated.

## App overview

The college admissions app helps high-school students build a profile,
choose colleges, and follow a personalized application roadmap.

Four key surfaces:

- **profile** — structured fields (grade level, graduation year, GPA,
  intended major, interests)
- **college_list** — list of universities the student is targeting
- **roadmap** — semester-by-semester plan generated from the profile +
  college list. Picks one of nine hand-curated templates based on the
  student's grade and the current semester.
- **fit** — per-college fit analysis (LLM-driven; not exercised by
  every scenario).

## Endpoints exercised by the QA agent

| Endpoint | Method | Purpose |
|---|---|---|
| `profile-manager-v2/clear-test-data` | POST | Reset test user's data |
| `profile-manager-v2/update-structured-field` | POST | Set ONE profile field |
| `profile-manager-v2/add-to-list` | POST | Add a college to the list |
| `profile-manager-v2/get-college-list` | GET | Read the list back |
| `profile-manager-v2/get-essay-tracker` | GET | Read tracker entries |
| `counselor-agent/roadmap` | POST | Generate a roadmap |
| `counselor-agent/work-feed` | GET | Get the focus feed |
| `counselor-agent/deadlines` | GET/POST | Aggregated deadlines |

## Valid input ranges

- `grade_level`: `"9th Grade"` | `"10th Grade"` | `"11th Grade"` | `"12th Grade"`
- `graduation_year`: integer in `[2026, 2030]`
- `gpa`: float in `[0.0, 4.0]`
- `intended_major`: free text
- `interests`: list of 1-5 strings

## Known fragile areas (high-priority test targets)

- **UC group treatment** when the list contains 1, 4, or all UCs vs a
  mix of UCs and non-UCs.
- **Summer template fallbacks**: freshman_summer → freshman_spring,
  sophomore_summer → sophomore_spring, senior_summer → senior_spring.
  Only `junior_summer` is a real summer template.
- **Edge GPA values** at 0.0, 4.0.
- **Late starter** — 12th grade, fall semester, no roadmap history yet.
- **Persona under-coverage**: recruited athletes, first-gen,
  specialists (musicology, classics) have been historically
  under-represented.
- **Single-school list** — exercises per-school code paths in isolation.

## Persona examples for variety

- **High-achieving STEM**: GPA 3.85+, robotics + competitive programming,
  4-6 reach + target list (MIT, Stanford, CMU, GT, UCs).
- **Recruited athlete**: GPA 3.4-3.7, varsity sport, narrower
  3-school list focused on athletic conferences.
- **First-gen**: GPA 3.3-3.7, regional college mix, specific aid focus.
- **Specialist**: GPA 3.6-3.9, niche major (musicology, classics,
  marine biology, anthropology).
- **Late starter**: 12th grade fall, no profile yet, last-minute
  application crunch.
- **Below-median GPA explorer**: GPA 2.8-3.2, mixed reach + safety list.

## Anti-patterns — DO NOT generate

- Made-up college IDs (must come from the allowlist).
- GPAs > 4.5 or < 0.0.
- Profiles missing required fields (`grade_level`, `graduation_year`).
- Scenarios with > 8 colleges (rate-limit hostile).
- Made-up template names (must be one of the 9 real templates).

## Templates

The roadmap resolver picks from these:

| Grade | Fall | Spring | Summer |
|---|---|---|---|
| Freshman (9th) | freshman_fall | freshman_spring | freshman_spring (fallback) |
| Sophomore (10th) | sophomore_fall | sophomore_spring | sophomore_spring (fallback) |
| Junior (11th) | junior_fall | junior_spring | junior_summer ← only real summer |
| Senior (12th) | senior_fall | senior_spring | senior_spring (fallback) |

## What "good coverage" looks like

A solid 30-day window covers:
- All 4 grade levels at least twice.
- All 3 semesters (fall, spring, summer).
- At least one all-UC scenario, one no-UC scenario, one mixed scenario.
- At least one persona from each of the 6 examples above.
- GPA distribution that touches all four buckets [0-2.5, 2.5-3, 3-3.5, 3.5-4].
