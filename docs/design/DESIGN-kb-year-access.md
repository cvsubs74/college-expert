# DESIGN — Year-by-year university profile access for agents

- Status: implemented (issue #279)
- Date: 2026-07-01
- Related: ADR `harness/decisions/0002-university-kb-year-versioning.md` (storage + write rules),
  `docs/design/DESIGN-kb-refresh-fit-staleness.md` (fit-side consumer), issues #193 / #203 / #252,
  follow-up #286 (university-chat + AdmissionsTab consumers)

## Problem

ADR 0002 gave the KB per-cycle snapshots (`universities/{id}/versions/{year}`)
and a year read API — but **no consumer used it**. The MCP `get_university`
tool took only `university_id`; there was no history/versions tool and no way
to fetch less than a full 50–150 KB profile. So agents answering "what changed
at X the past couple of years" leaned on the profile-baked
`admissions_data.longitudinal_trends` section, which is:

- capped at 8 rows by the connector and **dropped first** when a profile
  exceeds the 120k tool-result cap;
- ~92% unprovenanced legacy data (REDESIGN.md);
- written as a **single row** by the new verified collector — so it thins out
  as re-collection proceeds, exactly when snapshots become the real history.

## The year-axis trap (core design decision)

There are **two different year conventions** in the data and they must never
be merged into one timeline:

- **Cycle year** (ADR 0002): snapshot `versions/{N}` = applications due fall
  N / winter N+1, enrolling fall N+1. A cycle-N snapshot is the KB's
  *state of knowledge during cycle N* — its deadlines are for cycle-N
  applicants; its admitted-class stats are whatever the school had most
  recently published at collection time.
- **Trend year** (collector `LongitudinalTrend.year`): the entering-class /
  decision year — a different axis, and inconsistently applied across the
  three data generations.

A merged, deduped timeline would double-count the same admitted class under
adjacent year keys or falsely suppress distinct rows (adversarial review
finding, verified against `versioning.py:14-23` vs `model.py:235-238`).
**Resolution: return both structures separately, honestly labeled, and let
the reasoning agent handle the semantics** — consistent with the product's
agent-native doctrine (labeled facts > fabricated synthesis).

## API (knowledge_base_manager_universities_v2) — all additive

1. **Section projection** — `GET ?id=X[&year=N]&sections=a,b`
   - Projects `university.profile` to the requested top-level sections.
   - Response gains `sections_returned`, `sections_available`, and
     `unknown_sections` (typos). All-typo request → HTTP 400 listing valid
     names. Valid-but-absent sections are omitted silently (absence is data).
   - Without the param the response shape is unchanged (guarded by the
     backward-compat regression test). The envelope additionally gains
     `us_news_rank` + `soft_fit_category` (previously only on search/list —
     the connector read a field this endpoint never sent).

2. **Self-describing year reads**
   - `GET ?id=X&year=N` responses now include `available_years`, backfilled
     from the main doc via a **field-mask read** (`get_available_years`) —
     snapshots don't carry the field (it's main-doc-only per ADR 0002).
   - A year miss lists the available years in the error message and payload.

3. **`GET ?id=X&action=history`** — the two-axis view:
   - Default (compact): `snapshots` = one row per stored version
     (`extract_year_summary`, a pure function): year, `cycle_label`
     ("2026–27"), `source` (`kb_snapshot` / `kb_current`),
     `vintage_estimated`, `as_of`, acceptance rates (overall/in/OOS),
     class size, test policy + `is_test_optional`, early-plan stats, SAT/ACT
     middle-50, in/out-of-state tuition + COA, rank, deadlines. Plus
     `reported_trends` = the current profile's trend rows passed through
     with `source: profile_trend`, `verified: false`. Plus `notes[]` with
     honest caveats (zero-snapshot schools, estimated vintages).
   - `&sections=a,b` → `{years: {N: {section: data}}}` raw per-year sections
     (kb snapshots only). `&years=2024,2025` filters; a lone `year=` is
     accepted as an alias rather than silently ignored.
   - `action=history` without an id → 400.
   - The main doc **never contributes its own snapshot row when versions
     exist** (post-versioning it always duplicates one); a zero-version
     legacy school gets a single `kb_current` row whose year may be null —
     never guessed.

4. **Provenance for guessed vintages** — the auto-archive path
   (`save_university`) now stamps `vintage_estimated: true` on legacy docs it
   snapshots under a guessed `year-1`; history rows surface the flag.
   Pre-existing guessed archives can't be distinguished retroactively — the
   tool docstring carries the caveat.

5. **Defensive read-time normalization** — `extract_year_summary` applies the
   fraction→percent heuristic (`0 < v < 1` → `×100`, same rule as
   `versioning.normalize_percentages`) because snapshots written before the
   ingest-time fix (and verbatim legacy archives) carry fraction-style rates;
   it also handles both deadline key spellings (`plan_type|type`,
   `date|deadline`).

## MCP connector (stratia_connector)

- `get_university(university_id, year=None, sections=None)` — forwards both;
  `sections` is **enum-typed** (`Literal` of the 11 section names) so agents
  discover valid names from the tool schema with zero calls; the backend
  stays permissive. Backend errors are surfaced verbatim (they name the
  missing year and list available ones) instead of collapsing to "not found".
- **New tool `get_university_history(university_id, sections=None, years=None)`**
  — the one-call answer to "what changed at X". Docstring defines both year
  axes and the trust semantics (snapshots vs `verified:false` trends,
  `vintage_estimated`), warns against inferring a trend from one row, and
  instructs "don't derive the current cycle from the calendar date" (the
  repo has both April- and August-rollover conventions).
- **Deploy-skew guard**: an older KB ignores unknown actions and returns a
  full profile with `success:true`; the wrapper requires the history envelope
  (`snapshots`/`years`) and raises a clear error otherwise.
- **Size discipline**: sections-mode responses evict **oldest years first**
  (never the newest) until under the 120k cap, recording `truncated_years`
  so the agent re-calls with `years=[...]`. Compact mode drops
  `reported_trends` under extreme pressure (droppable section).

## Non-goals / follow-ups

- University-chat trend context + frontend AdmissionsTab switch to
  `action=history` → **#286** (split out: live user surface, zero existing
  chat test coverage, N+1 reads per turn need caching design).
- Batch+year reads, server-side diffing, KB auth (#223), unifying the
  April/August cycle-rollover constants.
- Read amplification note: `action=history` streams all version snapshots on
  a no-auth endpoint — negligible at 1–2 versions/school, linear growth per
  cycle; future optimization is persisting the compact summary onto the main
  doc at ingest (single point read).

## Testing

- `tests/.../test_year_history.py`: projection (valid/absent/typo), envelope
  additions, self-describing year reads, extractor (full row, fraction rates,
  dual deadline keys, empty doc, vintage flag), history (multi-version,
  years filter, zero-version legacy school, auto-archived estimated vintage,
  sections mode, all-typo error, unknown school).
- Connector: param forwarding, error enrichment, compact mode, sections+years
  forwarding, deploy-skew rejection, oldest-first eviction; smoke test
  asserts the new tool + enum-typed schema (verified against real `mcp`).
- The KB conftest now aliases `gemini_fallback`, so the KB suite passes in
  isolation (previously it depended on counselor_agent's conftest side
  effects — and silently bound the *wrong* module's copy).
