# Design — Automated, versioned university KB capture

- Issue: #193 (epic)
- Date: 2026-06-03
- Status: proposed (for review)
- Author: architecture analysis

## 1. Purpose

Re-architect how the university knowledge base is **captured, validated,
versioned, and refreshed year over year**. Today the data is collected by a
fragile ADK multi-agent collector that emits freeform LLM JSON, has no curated
source-of-truth, and is ingested with **no versioning** (overwrite-on-ingest).
This doc proposes a source-registry-driven, schema-constrained, **yearly
versioned** pipeline and recommends Claude workflows (hybrid with deterministic
API pulls) for orchestration.

## 2. Current state (analysis)

### 2.1 Schema (`agents/university_profile_collector/model.py`)
- `UniversityProfile`: **40 Pydantic models, ~220 fields**, 12 top-level
  sections (metadata, strategic_profile, admissions_data, academic_structure,
  application_process, application_strategy, financials, credit_policies,
  student_insights, outcomes, student_retention).
- Temporal fields: only `metadata.last_updated` (ingest date) + inline
  `admissions_data.longitudinal_trends[]` (a few years of trend rows). There is
  **no root data-cycle/year**.
- **Most of the value is cycle-specific:** acceptance rates (overall/in-state/
  OOS/intl/transfer + per early-plan), admitted GPA/test middle-50%,
  demographics, cost-of-attendance, deadlines, scholarship amounts/deadlines,
  outcomes, retention. All of this changes annually.

### 2.2 Capture (ADK collector)
- Topology: `LlmAgent` root → `SequentialAgent` → `ParallelAgent` (13
  sub-agents) → `ProfileBuilder` → `FileSaver`. Model: `gemini-2.5-flash` +
  `google_search`; a few `api_*` agents touch College Scorecard / IPEDS.
- **Pain points (evidenced):**
  - **~2,000 lines of `fix_*.py` repair scripts** + a `json_corrector_agent` —
    freeform LLM JSON is malformed often (escape chars, trailing commas, type
    mismatches: `"7.47%"` vs `7.47`, dict-vs-list, etc.).
  - **Non-idempotent**: same university → different output each run.
  - **Shared-state fragility**: 13 agents write one session dict; a silent
    sub-agent failure → null section, no isolation.
  - **Cost/latency**: 5–10 min/university; ~$3k+ for a full 250 run.
  - **No structured-output enforcement, no per-section validation, no
    cross-source verification, no provenance/confidence.**

### 2.3 Source registry (`agents/source_curator/`)
- Already prototypes the right idea: a **per-university YAML** of tiered
  sources — Tier-1 deterministic APIs (College Scorecard, Urban Institute
  IPEDS), Tier-2 curated web (Common Data Set PDFs by section, catalogs,
  admissions/financial-aid pages), each with `url`, `extraction_method`,
  `is_active`, `last_validated`. A `yaml_generator_agent` + API can produce them.
- **But:** only **USC** is curated, and **nothing in the capture/ingest path
  consumes these YAMLs**. It is unused scaffolding today.

### 2.4 Ingestion + versioning (`knowledge_base_manager_universities_v2`)
- `ingest_university()` → extracts a few top-level fields + stores the full
  `profile` → `db.save_university(slug, doc)` → Firestore `universities/{slug}`
  via `.set()` (**overwrite**). No deep schema validation at ingest.
- **No versioning of any kind.** One doc per university; each ingest destroys
  the prior cycle. `last_updated` = ingest time, not the data's cycle. ES is
  offline (Firestore-only).

## 3. Goals & non-goals

**Goals**
1. **Source-of-truth registry** that maps every schema section/field to
   authoritative, validated sources (tiered), maintained year over year.
2. **Yearly versioned storage**: immutable per-cycle snapshots + a "current"
   pointer + a change log. Never destroy a prior cycle.
3. **Deterministic, high-quality capture**: schema-constrained structured
   output, per-section validation, cross-source verification, provenance +
   confidence — eliminate the repair-script burden.
4. **Automation**: an annual refresh cadence + year-over-year change detection +
   a human review gate for low-confidence/high-variance fields.
5. A clear **orchestration recommendation** (Claude workflows vs ADK).

**Non-goals**
- Changing the consumer-facing read schema/UI (the `profile` shape stays;
  we add fields, not break them).
- Real-time/continuous scraping. Cadence is annual (plus targeted patches, e.g.
  the #191 deadline pilot).

## 4. Proposed architecture

Four decoupled layers, each independently testable:

```
┌─ (A) SOURCE REGISTRY ─────────────────────────────────────────────┐
│  sources/universities/{slug}.yaml  (tiered, validated, versioned)  │
│  field/section → {source, tier, url, extraction_method, freshness} │
└───────────────┬───────────────────────────────────────────────────┘
                │ drives
┌─ (B) CAPTURE PIPELINE (per university × per section) ──────────────┐
│  Tier-1: deterministic API pulls (no LLM)                          │
│  Tier-2/3: fetch source → schema-constrained LLM extraction        │
│  → cross-source verify (API ⇄ web) → per-field provenance+conf     │
│  → assemble section → validate section against Pydantic            │
└───────────────┬───────────────────────────────────────────────────┘
                │ produces a candidate snapshot
┌─ (C) VERSIONED STORE + DIFF ──────────────────────────────────────┐
│  validate full profile → diff vs prior cycle → change log          │
│  write universities/{slug}/versions/{cycle} (immutable)            │
│  promote → update universities/{slug} (current pointer)            │
└───────────────┬───────────────────────────────────────────────────┘
                │ gated by
┌─ (D) AUTOMATION + REVIEW ─────────────────────────────────────────┐
│  annual schedule (CDS/IPEDS publication window) · review queue for │
│  low-confidence / large-delta fields · source-freshness sweep      │
└───────────────────────────────────────────────────────────────────┘
```

### (A) Source registry — the missing config

Generalize `source_curator` into the system's backbone. Per university, a YAML
binds **each schema section** to its authoritative sources, tiered by trust:

- **Tier 1 — deterministic APIs** (no LLM, ground truth):
  College Scorecard + Urban Institute IPEDS → acceptance rate, enrollment,
  cost of attendance, retention/graduation, median earnings, demographics.
  Keyed by `ipeds_id`. These cover a large fraction of the cycle-specific
  numeric fields *deterministically*.
- **Tier 2 — structured official web**: the school's **Common Data Set** (the
  gold standard — Section C admissions, H financial aid, B/F demographics/test),
  official admissions/financial-aid/catalog pages → deadlines, test policy,
  middle-50% ranges, scholarships, majors/impaction.
- **Tier 3 — qualitative/crowd**: Niche, Reddit, College Confidential →
  `student_insights`, `application_strategy`, college archetypes (inherently
  soft; lower trust, never overrides Tier-1/2 numbers).

A **global field-map** (`sources/schema_field_map.yaml`) declares, once, which
schema field each tier/source is authoritative for, and the reconciliation rule
when sources disagree (Tier-1 API wins for numerics; CDS wins for
admissions-profile; flag conflicts > threshold). The per-university YAML only
needs URLs/ids + validation state. This is the regulatory-intelligence pattern:
**a versioned, validated source registry drives the ingestor.**

### (B) Capture pipeline — kill the determinism problem

Per (university, section) unit:
1. **Tier-1 pull** (plain Python, no LLM): hit the APIs from the registry, map
   fields deterministically. ~Half the numeric fields land here with zero LLM
   risk.
2. **Tier-2/3 extraction**: fetch the registry's source (CDS PDF section / web
   page), run a **schema-constrained** extraction (structured output bound to
   that section's Pydantic model) with the source text in-context and a
   **cite-or-null** rule (return a value only if grounded in the fetched
   source; else null + reason).
3. **Cross-source verification**: reconcile Tier-2 extractions against Tier-1
   ground truth (e.g., acceptance rate from CDS vs Scorecard). Disagreement
   beyond tolerance → flag for review, prefer the higher tier.
4. **Provenance + confidence**: every captured field records `{source_id,
   fetched_at, tier, confidence}` in a parallel `_provenance` map.
5. **Per-section validate** against Pydantic immediately — failures are isolated
   to one section, retried, never corrupt the whole profile.

Because output is schema-bound and validated per section, the **~2,000 lines of
`fix_*.py` disappear** — malformed-JSON repair is replaced by
generate-validated-or-retry.

### (C) Versioned store

Firestore layout (additive, backward-compatible):
- `universities/{slug}` — **current pointer**: the latest promoted snapshot
  (same shape consumers read today) + `data_cycle`, `captured_at`.
- `universities/{slug}/versions/{cycle}` — **immutable yearly snapshots**
  (e.g. `2026-2027`), each a full `UniversityProfile` + `_provenance`.
- `universities/{slug}/change_log/{cycle}` — structured diff vs the prior cycle
  (field, old, new, %Δ, source) for "what changed this year" + auditing.

Ingest becomes: validate → write `versions/{cycle}` (never overwrite) →
diff vs prior → if it passes gates, update the current pointer. A bad/partial
new cycle never destroys a good prior cycle.

**Schema additions** (small, non-breaking): root `data_cycle: str`
("2026-2027"), `captured_at: str`, and an optional parallel `_provenance` map.
Existing consumers ignore unknown fields.

### (D) Automation + review

- **Annual schedule**: a cron-triggered full refresh in the
  CDS/IPEDS publication window (mid-year), producing the next `{cycle}` for all
  universities. Plus on-demand targeted patches (e.g. the #191 deadline fix).
- **Change detection**: the diff feeds a review queue; large deltas (acceptance
  rate swing, test-policy flip, tuition jump, new/removed majors) and
  low-confidence fields are surfaced before the snapshot is promoted to current.
- **Source-freshness sweep**: validate registry URLs/`last_validated`; broken or
  stale Tier-2 sources flagged for re-curation.

## 5. Orchestration: Claude workflows vs ADK (recommendation)

**Recommendation: hybrid — deterministic Python for Tier-1, a Claude workflow
for Tier-2/3 extraction + verification + assembly + diff.**

Why Claude workflows over the current ADK collector:

| Need | ADK collector today | Claude workflow |
|---|---|---|
| Valid structured output | Freeform JSON → ~2k lines of repair | Schema-constrained `agent({schema})`, validated at the tool layer |
| Determinism / idempotence | Non-idempotent, shared-state | Deterministic control flow; resumable journal |
| Isolation of failures | One shared session dict | Per-(uni×section) agents; one fails → one retries |
| Fan-out at scale | ThreadPool batch scripts | `pipeline()`/`parallel()` fan-out, capped concurrency, budget-aware |
| Verification | None | Adversarial/cross-source verify stage built into the pipeline |
| Provenance/confidence | None | Captured per agent result |

Shape of the workflow (per refresh run):
```
phase Capture:  pipeline(universities,
  uni => parallel(sections.map(s =>
           agent(extract(uni, s, registry), {schema: SECTION_SCHEMA[s]}))),
  // each section: tier-1 pull (tool) + tier-2/3 extract + cite-or-null
  sectionsToProfile)
phase Verify:   per profile → cross-source reconcile + confidence gate
phase Diff:     diff vs prior cycle → change_log
phase Ingest:   validate → write versions/{cycle} → promote if gates pass
```
Keep ADK only if its Google-grounded search is needed for Tier-3 qualitative
capture; even there, a Claude workflow with web search + structured output is
simpler and more controllable. The **source registry, schema, and versioned
store are orchestrator-agnostic** — they are the durable assets; the
orchestrator is replaceable.

## 6. Phased rollout

1. **Versioned store + schema** (foundation): add `data_cycle`/`captured_at`,
   `versions/{cycle}` subcollection + change_log; make ingest write a version +
   promote a pointer. Backfill the current docs as cycle `2025-2026`. *No
   capture change yet — pure storage upgrade, immediately useful.*
2. **Source registry**: finalize the YAML schema + the global field-map; curate
   the pilot set (Duke, Ohio State, UCSD, USC — aligns with #191). Build the
   registry loader.
3. **Capture workflow (pilot)**: Claude workflow capturing the pilot schools
   from the registry with structured output + verification; diff + version +
   ingest; verify in-app. Compare quality/cost vs the ADK output.
4. **Scale + automate**: expand registry to all ~191; schedule the annual
   refresh; wire the review queue.
5. **Decommission** the `fix_*.py` repair layer as the ADK path is retired.

## 7. Risks & open questions

- **CDS/Tier-2 extraction reliability**: CDS PDFs vary in layout. Mitigation:
  per-section structured output + cite-or-null + Tier-1 cross-check; review gate.
- **Source coverage for smaller schools**: some lack a public CDS. Mitigation:
  tier fallbacks + confidence-gated null rather than guessing.
- **Cost of full annual run**: bounded by Tier-1-first (no LLM for ~half the
  numerics) + workflow budget controls.
- **Schema evolution across years**: store a `schema_version` per snapshot so
  old cycles remain interpretable.
- **Open**: exact `cycle` key convention (`2026-2027` vs IPEDS year); retention
  policy (keep N years vs all); whether to also version the registry YAMLs in
  git per year (recommended).

## 8. What this unlocks

- Trustworthy, dated data (no more "Passed"/stale-cycle bugs by construction).
- "What changed this year" insights for students and content.
- Auditability (provenance per field) and reproducibility (immutable snapshots).
- A maintainable capture system an order of magnitude less brittle than the
  current repair-script-laden ADK collector.
