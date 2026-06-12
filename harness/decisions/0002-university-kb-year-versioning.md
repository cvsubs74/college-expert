# ADR 0002 — Year-versioned university knowledge base

- Status: accepted
- Date: 2026-06-12
- Area: knowledge_base_manager_universities_v2

## Context

University data changes every admissions cycle: acceptance rates, deadlines,
new programs, costs, test policies. The KB pipeline is:

```
university_profile_collector (ADK agent) → research/<id>.json
    → POST {profile} to knowledge_base_manager_universities_v2
    → Firestore universities/{id}   (unconditional .set() — full overwrite)
```

Re-ingesting a university **destroys the previous cycle's data**. There is no
way to refresh the KB for the current year while keeping prior years, no way
to read what the KB said last cycle, and no validation gate at the ingest
boundary — a malformed collector JSON overwrites a good document.

## Decision

### 1. Version unit: admission **cycle year** (integer)

`cycle_year = N` means the application cycle whose deadlines fall in
fall N / winter N+1 (i.e. the "N – N+1 cycle", enrolling fall N+1).
Example: data with ED Nov 2026 / RD Jan 2027 deadlines is cycle **2026**.

Default when the caller doesn't pass a year: derived from today's date —
months **April–December → current calendar year**, January–March → previous
year (in Jan–Mar the live application season is still the one that opened the
prior fall; by April schools publish the next cycle's information).
Callers can always pass `year` explicitly; the derivation is only a fallback.

### 2. Firestore layout: current doc + versions subcollection

```
universities/{id}                      ← the CURRENT serving doc (unchanged shape)
    + data_year: int                   ← cycle year of the data in this doc
    + available_years: [int]           ← denormalized list of stored versions
universities/{id}/versions/{year}      ← full snapshot per cycle year
                                         (same shape as the main doc, incl. profile)
```

The main doc keeps its exact existing shape (plus the two new fields), so
**every existing consumer — counselor_agent, hybrid agent, frontend, search,
list, batch — keeps working unchanged** and always sees the latest year.
Search/list operate on main docs only; versions are point-read by id+year.

### 3. Write rules (ingest)

- `POST {profile, year?}` — snapshot is always written to `versions/{year}`.
- The main doc is **promoted** (overwritten) only when `year >= data_year`
  of the existing main doc. Ingesting a historical year never clobbers the
  current serving data.
- A legacy main doc with no `data_year` (pre-versioning) is treated as older
  than any explicit year — the first versioned ingest takes over the main doc.
- Re-ingesting the same year overwrites only that year's snapshot
  (idempotent refresh within a cycle).

### 4. Read rules

- `GET /?id=X` — unchanged: main doc (current year).
- `GET /?id=X&year=2025` — that year's snapshot; 404-style error if absent.
- `GET /?id=X&action=versions` — list stored years with per-year metadata.

### 5. Delete rules

- `DELETE {university_id}` — main doc **and all version snapshots**.
- `DELETE {university_id, year}` — that snapshot only; if it was the year
  serving the main doc, the latest remaining version is promoted; if none
  remain, the main doc is deleted too.

### 6. Accuracy gate at the ingest boundary

`versioning.validate_profile()` runs on every ingest:

- **Errors (reject, HTTP 400):** missing `_id`, missing
  `metadata.official_name`, `acceptance_rate` outside (0, 100], `profile`
  not an object.
- **Warnings (accept, reported in the response and logged):** missing
  acceptance rate, no application deadlines, unparseable deadline dates,
  deadline dates far outside the declared cycle window (year-1 .. year+2).

This is deliberately a *boundary* check; deep accuracy work (source
cross-checking, gap-filling) stays in the collector + uniminer pipeline.

### 7. Canonical ingestion CLI

`scripts/ingest_universities.py` replaces ad-hoc `ingest_specific.py` usage:
per-file or per-directory ingest of collector JSONs with `--year`,
`--dry-run`, `--only`, local pre-validation, and a per-file result summary.

## Alternatives considered

- **Separate flat collection `universities_versions/{id}_{year}`** — avoids
  subcollections but pollutes collection-level scans and makes per-university
  version listing a filtered query instead of a subcollection read.
- **Versioned fields inside the main doc** (`profile_2025`, `profile_2026`) —
  doc size grows unboundedly toward Firestore's 1 MiB limit (full profiles
  are 50–150 KB each).
- **Version everything, no "current" doc** — breaks every existing consumer
  and makes search/list O(versions).

## Consequences

- Yearly refresh = run the collector, then `scripts/ingest_universities.py
  --dir ... --year N`. Prior years remain readable forever.
- Storage grows by one full snapshot per university per year (~150 KB × 250
  universities ≈ 37 MB/year — negligible).
- `delete_university` now does N+1 deletes (versions + main).
- Consumers that later want historical views (trend charts, "what changed
  since last year") have a stable read API to build on.
