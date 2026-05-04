# Design — University Friendly Labels

Spec: docs/prd/qa-university-friendly-labels.md.

## Approach: hybrid lookup + auto-prettify

A small client-side utility:

```js
const LABELS = {
  massachusetts_institute_of_technology: 'MIT',
  university_of_california_berkeley: 'UC Berkeley',
  university_of_california_los_angeles: 'UCLA',
  university_of_california_san_diego: 'UC San Diego',
  university_of_california_davis: 'UC Davis',
  university_of_california_santa_barbara: 'UC Santa Barbara',
  university_of_california_irvine: 'UC Irvine',
  university_of_minnesota_twin_cities: 'University of Minnesota',
  university_of_texas_at_austin: 'UT Austin',
  georgia_institute_of_technology: 'Georgia Tech',
  carnegie_mellon_university: 'Carnegie Mellon',
  // … plus a handful of standard short forms
};

export function formatUniversityName(id) {
  if (!id) return '';
  if (LABELS[id]) return LABELS[id];
  // Default: replace underscores with spaces, titlecase each word.
  return id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
```

The override map covers the ~32 schools in the allowlist plus the two
canonical aliases (`mit`, `ucla`) for graceful display of any legacy
records that slip through.

## Where it's applied

`frontend/src/components/qa/UniversitiesCard.jsx`:

- Tested rows: `<span className="font-mono ...">{formatUniversityName(u.id)}</span>`
  with `title={u.id}` for hover tooltip and `aria-label` on the row
  for screen readers.
- Untested chips: same prettifier; the comma-separated string becomes
  `"Princeton, Yale, Brown, Columbia"` instead of
  `"princeton, yale_university, brown_university, columbia_university"`.

The font-mono styling is dropped since these are now display strings,
not IDs.

## Tests

`frontend/src/__tests__/UniversitiesCard.test.jsx` adds:

- "renders MIT (not the snake_case id)" for the override path.
- "renders Tufts University for an id without an override" for the
  auto-prettify fallback.
- "tooltip on tested row preserves the canonical id" for the
  click-to-copy / debug story.

A separate `frontend/src/utils/__tests__/formatUniversityName.test.js`
unit-tests the helper in isolation (overrides, titlecase, empty input,
unknown id).

## Risk

Negligible:
- Pure presentation layer. No backend changes.
- The map is small and explicit — no fuzzy matching to cause surprises.
- Unknown ids degrade gracefully.
