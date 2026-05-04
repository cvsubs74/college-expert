// Map canonical (snake_case) college IDs to human-friendly display
// names. Used by the QA dashboard's UniversitiesCard so operators see
// "MIT" instead of "massachusetts_institute_of_technology".
//
// Spec: docs/prd/qa-university-friendly-labels.md +
//       docs/design/qa-university-friendly-labels.md.
//
// Hybrid strategy:
//   1. Look up an explicit override (covers the ~32 schools currently
//      in the allowlist + the two legacy aliases).
//   2. Fall back to underscore→space + titlecase so a brand-new school
//      id renders reasonably without a code change.

const LABELS = {
    // Schools where the friendly name differs meaningfully from a
    // mechanical titlecase of the ID.
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
    new_york_university: 'NYU',
    ohio_state_university: 'Ohio State',
    penn_state_university: 'Penn State',

    // Legacy short aliases — backend canonicalizes them, but render
    // gracefully if any sneak through (e.g. very old run records).
    mit: 'MIT',
    ucla: 'UCLA',
};

export function formatUniversityName(id) {
    if (!id) return '';
    if (LABELS[id]) return LABELS[id];
    return id.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
