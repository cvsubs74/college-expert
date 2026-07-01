# Runbook — yearly university KB refresh

How to update the university knowledge base for a new admission cycle
without destroying prior years' data. Design: ADR
`harness/decisions/0002-university-kb-year-versioning.md`.

## TL;DR

```bash
# 1. Re-collect data with the ADK agent (per university, or batch)
cd agents/university_profile_collector
python run_single_university.py "Stanford University"     # → research/stanford_university.json
# (run_top100_universities.py / run_all_250_universities.py for batches)

# 2. Validate without writing
cd ../..
python scripts/ingest_universities.py \
    --dir agents/university_profile_collector/research --dry-run

# 3. Ingest for the cycle (year defaults to the current cycle; pass it explicitly for clarity)
python scripts/ingest_universities.py \
    --dir agents/university_profile_collector/research --year 2026 --merge-with-current
```

**Use `--merge-with-current` for yearly refreshes.** A single fresh research
pass is usually much thinner than the original multi-agent collection
(observed: Princeton fresh pass had 272 leaf fields vs 741 in the KB).
Merge mode overlays only the cycle-sensitive sections — current admissions
status, application deadlines, US News rank/rankings, cost of attendance —
onto the KB's current rich profile, and unions `longitudinal_trends` by
year. Durable sections (majors, strategy advice, student insights,
scholarships) are kept from the richer base. Omit the flag only when the
fresh collection is a full-depth profile you want verbatim.

That's it. Each university gets a `versions/{2026}` snapshot in Firestore and
becomes the serving "current" doc. Last cycle's data stays readable at
`GET /?id=<uid>&year=2025`.

## Cycle-year convention

`year = N` is the cycle whose deadlines fall in **fall N / winter N+1**
(students enrolling fall N+1). Data collected June 2026 with ED Nov 2026 /
RD Jan 2027 deadlines → `--year 2026`. When `--year` is omitted the CLI
derives it from today's date (April–December → this year, January–March →
last year).

> ⚠️ **Collector year is OFF BY ONE from the KB cycle year — this is load-bearing.**
> `kb_collect_workflow.js` takes `year` = the **entering-cohort Fall year**
> (`CYCLE = "Fall ${year}"`), which is **KB cycle year + 1**. To refresh KB
> cycle year **Y**, run the collector with **`year = Y+1`**, then ingest
> **`--year Y`**. Example (done 2026-07): to fix the current cycle (KB
> `data_year=2026`, deadlines Nov 2026 / Jan 2027) we ran the workflow with
> `year=2027` and ingested `--year 2026`. Following the workflow's own
> "ingest with the *same* year" note instead files **last cycle's** deadlines
> under the current year — that off-by-one is exactly what made the whole KB
> one cycle stale (161 schools, fixed via `scripts/fix_stale_kb_deadline_years.py`).

## What the ingest enforces

- **Rejected (per-file FAIL, nothing written):** missing `_id`, missing
  `metadata.official_name`, acceptance rate outside (0, 100].
- **Warned (written, but check the output):** missing acceptance rate, no
  application deadlines, unparseable deadline dates, deadlines outside the
  cycle window (year-1 .. year+2 — usually means you're ingesting last
  year's JSON under the new year).

The CLI exits non-zero if any file failed, so it's safe in scripts.

## Useful operations

```bash
# One university only
python scripts/ingest_universities.py --file research/mit.json --year 2026

# A subset by id
python scripts/ingest_universities.py --dir research/ --only mit,stanford_university --year 2026

# What years does the KB hold for a university?
curl "$KB_URL/?id=mit&action=versions"

# Read last cycle's data
curl "$KB_URL/?id=mit&year=2025"

# Remove one bad snapshot (promotes the latest remaining year if it was current)
curl -X DELETE "$KB_URL" -H 'Content-Type: application/json' \
     -d '{"university_id": "mit", "year": 2026}'
```

`KB_URL=https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app`

## Gotchas

- **Deploy before ingesting with `--year`.** The CLI aborts if the deployed
  function predates versioning (it detects the missing `year` field in the
  response) — otherwise the old code would overwrite main docs with no
  snapshot.

- **Don't re-ingest stale collector JSONs under a new year.** The cycle
  window warning catches it, but the right fix is re-running the collector
  so deadlines/rates are actually current.
- Re-running ingest for the same year is safe — it refreshes that year's
  snapshot in place (idempotent).
- `ingest_specific.py` (repo root) predates versioning and points at the
  retired v1 (Elasticsearch) function — use `scripts/ingest_universities.py`.
- Consumers (counselor_agent, hybrid agent, frontend) always read the
  current doc; nothing downstream needs a change when you refresh.
