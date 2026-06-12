# Consolidated system scenarios

The verification suite for the year-versioned university knowledge base and
the fit-staleness UX (ADR 0002, `docs/design/DESIGN-kb-refresh-fit-staleness.md`),
plus the system-wide health gates. Every scenario here is **executable**:

```bash
.venv/bin/python scripts/run_scenarios.py            # runs everything
.venv/bin/python scripts/run_scenarios.py --skip-live # unit/build gates only
```

The runner writes a dated report to `docs/scenarios/SCENARIO-RUN-<date>.md`.
Live scenarios hit production (GCP project `college-counselling-478115`) using
clearly-named sentinel documents (`_harness_scenario_*`) and clean up after
themselves. Nothing touches real user data; no scenario spends LLM credits.

**When to run:** after every yearly KB refresh (see
`docs/university-kb-yearly-refresh.md`), and before shipping changes to
`knowledge_base_manager_universities_v2`, `profile_manager_v2` fit paths, or
`counselor_agent` planner.

---

## S1 — Backend unit suite

**Given** the repo at HEAD. **When** `pytest tests/` runs. **Then** every test
passes (the suite covers KB versioning storage rules, ingest validation,
percent normalization, cycle-refresh merge, fit provenance/staleness severity,
history archival, nudge suppression, and roadmap deadline annotation).

## S2 — Frontend unit suite + production build

**Given** `frontend/` with dependencies installed. **When** `vitest run` and
`vite build` run. **Then** all tests pass (vintage chip tones, banner gating
incl. per-cycle dismissal memory, review-modal facts/retry/suppression) and
the build succeeds.

## S3 — KB versioning lifecycle (live Firestore)

**Given** a sentinel university id. **When** snapshots are ingested across
years through the real `FirestoreDB` layer. **Then**, in order:
1. First ingest (2025) creates `versions/2025` and promotes the main doc.
2. Newer ingest (2026) promotes; 2025 snapshot intact; `available_years` grows.
3. Older ingest (2024) archives **without** touching the serving doc.
4. Same-year re-ingest refreshes that snapshot only (idempotent).
5. A **legacy** main doc (no `data_year`) is auto-archived under `year-1`
   before the first versioned ingest takes it over (#199).
6. Deleting the serving year promotes the latest remaining snapshot.
7. Full delete removes the main doc and every version. Cleanup verified.

## S4 — Versioned read APIs (deployed function)

**Given** `princeton_university` refreshed for 2026 with a 2025 archive.
**When** the deployed KB function is called. **Then**:
- `GET /?id=princeton_university` serves current data with the legacy response
  shape intact (consumer back-compat) plus `data_year`/`available_years`.
- `GET ...&year=2025` serves the archived cycle (older acceptance rate).
- `GET ...&action=versions` lists both years, newest first.

## S5 — Ingest validation gate (deployed function)

**When** a profile missing `_id`/`official_name` is POSTed → **Then** HTTP 400
with `validation_errors`, nothing written. **When** `year=1990` is sent →
**Then** HTTP 400 (out of range 2000–2100).

## S6 — KB 2026 data integrity (live Firestore)

**Given** the full `universities` collection after the 2026 refresh. **Then**
every doc serves `data_year == 2026`; every `acceptance_rate` is in (0, 100]
with **no fraction-style values** (the 98-university regression of 2026-06-12);
≥185 universities retain a 2025 archive (3 known exceptions: arizona_state,
colorado_state, duquesne — no pre-refresh source existed).

## S7 — Collector output validation (research_2026 corpus)

**Given** the 191 collector JSONs in
`agents/university_profile_collector/research_2026/`. **When** each is run
through `versioning.validate_profile` for cycle 2026. **Then** zero files
fail (warnings allowed — they're data-quality signals, e.g. rolling
admissions with no fixed deadline).

## S8 — Fit staleness detection + application-clock suppression (deployed)

**Given** a sentinel user with two saved fits stamped `kb_data_year: 2025`
against universities now serving 2026 data — one college `planning`, one
`applied`. **When** the deployed `/check-fit-recomputation` runs. **Then**:
- Both fits appear in `kb_updates` with `fit_kb_year: 2025`,
  `current_kb_year: 2026`.
- A tier-crossing acceptance-rate change is flagged **material**, and the
  projected category shift derives from the selectivity floor (e.g.
  `REACH → SUPER_REACH` when the new rate is < 8%).
- The `applied` college is `nudge_suppressed: true` (no banner nudge), the
  `planning` one is not — but **both** keep their staleness data (the
  passive vintage chip needs it).
- A user with no fits returns `success: true, kb_updates: []`.
Sentinel docs deleted afterwards; deletion verified.

## S9 — Fit history archival (deployed)

**Given** the sentinel user's saved 2025-stamped fit. **When** a new fit is
saved over it via `/save-fit-analysis` (no LLM involved). **Then**
`/get-fit-history` returns the replaced fit archived under history key
`2025` with its original category — nothing the student saw was destroyed.

## S10 — Roadmap deadline-change annotation

**Given** saved roadmap tasks and regenerated tasks where a KB refresh moved
a deadline. **Then** the regenerated task carries `previous_due_date` and
`deadline_change_note` ("Deadline updated: old → new") — never a silent date
swap; unmoved/new tasks are not annotated. (Executed via the dedicated unit
tests; the deterministic generator has no LLM dependency.)

## S11 — Live synthetic monitoring (QA agent)

**Given** the QA agent's scheduled runs against production (every 20 min:
profile build, college list, roadmap, fit chat, work feed, deadlines).
**Then** the most recent completed run has zero failed scenarios.

## S12 — Deployed function health

**Then** the KB function's `/health` reports Firestore connectivity, and
`/check-fit-recomputation` + `/get-fit-history` respond with their new
contracts on the deployed `profile-manager-v2`.

---

## Known exceptions / accepted findings

| Scenario | Exception | Why accepted |
|---|---|---|
| S6 | 3 universities lack a 2025 archive | Refreshed in wave 1 before the auto-archive fix (#199); no pre-refresh source file existed. History survives via `longitudinal_trends`. |
| S6 | 1 university has no application deadlines | Wichita State is rolling-admissions; flagged as a warning at ingest by design. |
| S7 | Warnings on some files | Data-quality signals (unparseable "Rolling" dates, out-of-window scholarship deadlines) — surfaced, not blocking. |
| S7 | `georgia_institute_of_technology` and `michigan_state_university` absent from research_2026 | Deep-research JSON output truncates on their large program catalogs (3 attempts each, 2026-06-12). Their KB docs are uncorrupted (merged rich data, serving 2026); re-collect manually next cycle. The fragment-detection added to `extract_json_from_response` + the pre-merge validation in the ingest CLI prevent fragments from ever masquerading as refreshes again — the original run shipped 19/191 fragment files that the merge silently masked. |
