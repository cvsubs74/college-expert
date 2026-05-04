# Design — QA College ID Canonicalization

Spec: docs/prd/qa-college-id-canonicalization.md.

## Three-layer fix

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

## Tests

`tests/cloud_functions/qa_agent/test_coverage.py::TestUniversityCanonicalization`
adds five cases:

- `test_alias_mit_folds_to_canonical`
- `test_alias_ucla_folds_to_canonical`
- `test_alias_and_canonical_collapse_to_single_row`
- `test_canonical_id_omitted_from_untested_when_alias_was_tested`
- `test_unknown_id_passes_through_unchanged`

Existing `TestUniversitiesTested` tests changed `"mit"` → `"harvard"`
to keep their semantics independent of the alias map.

## Risk

Negligible:
- Pure refactor for any new run after the allowlist change.
- `_canonicalize` is opt-in by entry — unknown ids pass through, so
  the dashboard never silently swallows valid data.
- The alias map is small (2 entries today) and additions are explicit.
