# QA — University Friendly Labels

## Problem

The new `UniversitiesCard` (PR #65) renders raw snake_case IDs:

```
• university_of_california_berkeley           2x  6m ago
• massachusetts_institute_of_technology       3x  6m ago
• boston_college, brown_university, ...
```

These are correct but visually noisy and hard to skim. Operators see
"Stanford University" everywhere else in the app — the QA dashboard
shouldn't be the one place with engineering-only IDs.

## Goal

Render friendly display names in the UniversitiesCard's tested + untested
sections while keeping the underlying canonical ID in the data model
(routes, hover, screen reader fallback).

## Non-goals

- Not changing the run record schema. The `id` remains the canonical
  snake_case form.
- Not introducing a knowledge-base lookup. Friendly names are a small
  client-side concern, not worth a network round-trip per school.
- Not localizing the names. English-only for now.

## Success criteria

- "Massachusetts Institute of Technology" (or "MIT") renders instead of
  `massachusetts_institute_of_technology`.
- "UC Berkeley" renders instead of `university_of_california_berkeley`.
- Unknown ids gracefully degrade to titlecased-with-spaces (e.g.
  `tufts_university` → "Tufts University") without code changes.
- Hover tooltip on each row reveals the canonical ID for operators
  building tickets / queries.
