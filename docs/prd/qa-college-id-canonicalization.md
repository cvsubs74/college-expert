# QA College ID Canonicalization

## Problem

Production `/summary` on 2026-05-04 surfaced both `"mit"` AND
`"massachusetts_institute_of_technology"` as separate entries in the
new universities-tested list (PR #65), and the same for
`"ucla"` vs `"university_of_california_los_angeles"`. The dashboard
was double-counting the same school.

Root cause: the synthesizer's allowlist (`scenarios/colleges_allowlist.json`)
historically contained both forms, so the LLM could pick either at
random. Two static scenarios also referenced the short aliases. With
no normalization step, mixed-form data flowed straight into the
universities aggregation in `coverage.build_coverage`.

## Goals

- One row per school in `coverage.universities_tested`, regardless of
  which form (alias or canonical) the run record stored.
- Old runs already in Firestore that used `"mit"` or `"ucla"` still
  render correctly under the canonical id — no backfill needed.
- The allowlist drives the synthesizer toward canonical ids only, so
  new runs never produce aliases.

## Non-goals

- Not touching the knowledge base or any other downstream system that
  may consume scenario records — those keep their existing IDs.
- Not introducing a fuzzy/matchall normalizer. The alias map is
  explicit and small; new aliases are added by hand.

## Success criteria

- New `TestUniversityCanonicalization` cases (5) cover folding,
  collapse-into-single-row, untested set difference, and unknown-id
  pass-through.
- Production `/summary` shows neither `"mit"` nor `"ucla"` after
  redeploy.
