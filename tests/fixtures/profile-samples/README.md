# QA Profile Fixtures

These fixtures are used by Section 6 of `docs/qa-browser-test-plan.md` to
validate the profile-upload and attribute-extraction flow against the live
`stratiaadmissions.com` product.

## Files

| File | Grade | Purpose |
|---|---|---|
| `sample-junior-comprehensive.pdf` | Grade 11 | Exercises every attribute the extraction code supports. Reference for the "all fields populated" assertion table in Section 6.3. |
| `sample-sophomore-partial.docx` | Grade 10 | Exercises ~50% of attribute types (no test scores, no AP exam scores, fewer activities, fewer awards). Confirms the extractor handles incomplete profiles gracefully. |

## Fixture content summary

### sample-junior-comprehensive.pdf

Fictional student: **Alex Rivera**, Grade 11, Riverside High School, Lakewood CA.

Covers:
- Basics: name, grade, school, location, graduation year, intended major
- Academics: weighted GPA, unweighted GPA, UC GPA, class rank
- Test scores: SAT total, SAT math, SAT reading/writing, ACT composite
- AP exams: 6 subjects with scores
- Courses: 13 courses across grades 9-11, typed as AP/Honors/Regular with semester grades
- Activities: 4 extracurriculars with role, grades, hours/week, description
- Awards: 5 awards at School/Regional/National level

### sample-sophomore-partial.docx

Fictional student: **Morgan Chen**, Grade 10, Mountain View Academy, Riverside CA.

Covers:
- Basics: name, grade, school, location, graduation year, intended major
- Academics: weighted GPA, unweighted GPA only (no UC GPA, no class rank)
- Test scores: none (not yet taken)
- AP exams: none explicitly scored
- Courses: 8 courses across grades 9-10 with semester grades
- Activities: 2 extracurriculars
- Awards: 1 award

## Data integrity

- All names, schools, and locations are fully fictional.
- No real email addresses (uses `alex.rivera@example.com`, IETF-reserved domain).
- No real phone numbers, SSNs, or credentials.
- School names ("Riverside High School", "Mountain View Academy") are generic
  placeholders — not real schools.
