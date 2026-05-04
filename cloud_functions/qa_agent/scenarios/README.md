# Scenario archetypes

One JSON file per archetype. The QA agent loads every file in this
directory at run time, picks a few according to the selection policy in
`corpus.py`, and applies an LLM-generated variation before executing.

## Schema

```json
{
  "id": "unique_archetype_id",
  "description": "one-sentence summary used in reports + LLM prompt",
  "default_student_name": "Test Student",
  "profile_template": {
    "grade_level": "11th Grade",
    "graduation_year": 2027,
    "gpa": 3.7,
    "intended_major": "Computer Science",
    "interests": ["coding", "robotics"]
  },
  "colleges_template": ["massachusetts_institute_of_technology", "stanford_university", "..."],
  "expected_template_used": "junior_spring",
  "surfaces_covered": ["profile", "college_list", "roadmap"]
}
```

- `id` is stable across runs and is used as the document key in
  `qa_scenarios/`.
- `expected_template_used` is asserted on the `/roadmap` response. Omit
  if the archetype's profile alone shouldn't determine a specific
  template (e.g., a new-user scenario that hasn't completed onboarding).
- Adding an archetype is just dropping a new file here; redeploy the
  function. No corpus migration step.

## Coverage so far

| File | Grade | Schools | Notes |
|---|---|---|---|
| `freshman_fall_starter.json` | 9 | 1 (state univ) | Fresh user, just starting |
| `sophomore_spring_explorer.json` | 10 | 3 (mixed) | Exploring options |
| `junior_spring_5school.json` | 11 | 5 (T20 + UCs) | Mid-tier reach list |
| `junior_summer_rising_senior.json` | 11 | 4 | The only `_summer` template |
| `senior_fall_application_crunch.json` | 12 | 6 (T20 + safeties) | Application season |
| `senior_spring_decisions.json` | 12 | 5 | Decision time |
| `all_uc_only.json` | 11 | 4 (UCs) | UC group treatment |
| `single_school_test.json` | 11 | 1 | Edge: one-school list |
