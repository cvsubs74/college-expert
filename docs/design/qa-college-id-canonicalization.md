# Design — QA College ID Canonicalization

Spec: docs/prd/qa-college-id-canonicalization.md.

## Four-layer fix

### 1. Allowlist cleanup (source of truth)

`cloud_functions/qa_agent/scenarios/colleges_allowlist.json`:

- Drop `"mit"` and `"ucla"`.
- Keep `"massachusetts_institute_of_technology"` and
  `"university_of_california_los_angeles"` as the canonical forms.
- The `_comment` field documents the rule: "Use full canonical names;
  short aliases are folded by `coverage._CANONICAL_ALIASES` at
  dashboard-build time and must not be added here."

The synthesizer's `validate_archetype` already rejects scenarios with
ids not in the allowlist, so once an alias is removed the LLM cannot
emit it.

### 2. Static scenario cleanup

Two existing static archetypes referenced the alias forms:

- `scenarios/junior_spring_5school.json`: `"mit"` →
  `"massachusetts_institute_of_technology"`.
- `scenarios/sophomore_spring_explorer.json`: `"ucla"` →
  `"university_of_california_los_angeles"`.

`scenarios/README.md` example also updated for consistency.

### 3. Coverage canonicalization (legacy data)

Even after the allowlist is cleaned, Firestore still holds run records
from before today that reference `"mit"` and `"ucla"`. We don't want
the dashboard to keep showing duplicates for ~24h until those age out
of the recent-30-runs window.

`cloud_functions/qa_agent/coverage.py` adds:

```python
_CANONICAL_ALIASES = {
    "mit": "massachusetts_institute_of_technology",
    "ucla": "university_of_california_los_angeles",
}

def _canonicalize(uni: str) -> str:
    return _CANONICAL_ALIASES.get(uni, uni)
```

Applied inside the per-scenario aggregation loop in `build_coverage`,
right after the basic type check:

```python
for uni in scen.get("colleges_template") or []:
    if not isinstance(uni, str) or not uni:
        continue
    uni = _canonicalize(uni)
    slot = universities.setdefault(uni, {...})
    ...
```

`universities_untested` correctness follows for free: the tested set
is keyed by canonical id, so the allowlist-difference computation
already excludes the canonical form when an alias was tested.

### 4. Archetype-write-time normalization (synthesizer)

The first three layers leave one corner case: a static archetype JSON
file silently reintroducing `"mit"`, or a future code path that bypasses
the synthesizer's allowlist validation. In those cases the *run record
itself* would carry an alias even though the dashboard view stays clean.

`cloud_functions/qa_agent/synthesizer.py` adds:

```python
_CANONICAL_ALIASES = {
    "mit": "massachusetts_institute_of_technology",
    "ucla": "university_of_california_los_angeles",
}

def canonicalize_college_id(uni):
    if isinstance(uni, str):
        return _CANONICAL_ALIASES.get(uni, uni)
    return uni

def canonicalize_archetype(archetype) -> None:
    """Mutate archetype['colleges_template'] in place: canonicalize each
    id and dedupe. No-op when the field is missing or wrong shape."""
    ...
```

`main.py::_pick_scenarios` calls `canonicalize_archetype(a)` for every
archetype in `chosen` (synthesized + static) right before the run begins.
Both copies of the alias map are intentionally kept independent so the
two layers (write-time + read-time) don't collapse into a single point
of failure.

## Tests

`tests/cloud_functions/qa_agent/test_coverage.py::TestUniversityCanonicalization`
covers the read-time layer (5 cases):

- `test_alias_mit_folds_to_canonical`
- `test_alias_ucla_folds_to_canonical`
- `test_alias_and_canonical_collapse_to_single_row`
- `test_canonical_id_omitted_from_untested_when_alias_was_tested`
- `test_unknown_id_passes_through_unchanged`

`tests/cloud_functions/qa_agent/test_synthesizer.py::TestCanonicalizeCollegeId`
+ `TestCanonicalizeArchetype` cover the write-time layer (13 cases):

- both known aliases (`mit`, `ucla`) fold to canonical
- already-canonical input passes through
- unknown ids pass through unchanged
- non-string input doesn't crash
- archetype mutation handles dedup, order preservation, idempotency,
  missing-field, non-string entries inside the list, and non-dict input

Existing `TestUniversitiesTested` tests changed `"mit"` → `"harvard"`
to keep their semantics independent of the alias map.

## Risk

Negligible:
- Pure refactor for any new run after the allowlist change.
- Both `canonicalize_*` helpers are opt-in by entry — unknown ids
  pass through, so the dashboard never silently swallows valid data.
- The alias map is small (2 entries today) and additions are explicit.
- Both layers are independent: a regression in one is caught by the
  other.
