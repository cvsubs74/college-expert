# University Profile Collector — Claude Workflow (`kb_collect_workflow.js`)

The self-verifying replacement for the ADK/Gemini collector. Takes a **university + year**, gathers the profile from **official sources**, **verifies itself** (blind verifier + arithmetic gate), and emits a **year-versioned `UniversityProfile`** with provenance — designed for **no human review** (see `REDESIGN.md` for the why).

## Input / Output

```
Input:  args = { university: "<name>", year: <Fall entering-cohort year, e.g. 2024> }
Output: { profile, _provenance, _trust_report, _source_ledger }
        profile       → UniversityProfile JSON (model.py schema), ingest-ready
        _provenance   → per-field { status, confidence, source, url, quote, as_of_cycle }
        _trust_report → counts of corroborated / canonical-single / nulled fields + source totals
        _source_ledger→ EVERY URL consulted across all stages (used or rejected), deduped,
                        annotated with which stage/field used it and whether it backed a published value
```

`year` pins everything: which Common Data Set edition (`<year>-<year+1>`), which Scorecard cycle, the `as_of_cycle` tags, and `metadata.cycle_year`. Re-running a later year produces a new snapshot (ADR 0002 year-versioning), it does not overwrite prior years.

## How to run

It's a Claude Workflow, so it runs via the Workflow tool (ask Claude, or invoke from a harness):

```
Workflow({ scriptPath: "agents/university_profile_collector/kb_collect_workflow.js",
           args: { university: "Purdue University", year: 2024 } })
```

Then persist + validate + ingest:

```bash
# save the workflow's returned JSON to result.json, then:
python agents/university_profile_collector/save_profile.py result.json --year 2024
#   → validates against model.py AND the server ingest gate, writes research/<id>.json
#     + research/_provenance/<id>.json, prints the trust report
python scripts/ingest_universities.py --file agents/university_profile_collector/research/<id>.json --year 2024
```

## The pipeline (code = pure-JS gate, LLM = agent)

| # | Stage | Kind | What it does |
|---|-------|------|--------------|
| 1 | **Resolve** | LLM | Official name, **IPEDS UnitID** (confirmed on name+city+state — works for *any* school, not a 40-entry dict), location, and the authoritative source URLs for the cycle (CDS edition, Scorecard, admissions, aid, catalog). |
| 2 | **Anchor** | LLM | Pulls **48 deterministic-official fields** from the CDS + College Scorecard, each with a verbatim quote, source URL, CDS cell/section, and cycle. The LLM *locates and quotes*; it does not author numbers freehand. |
| 3 | **Verify** | LLM | A **blind verifier** independently re-derives the 6 highest-stakes fields (acceptance, SAT, ACT, retention, 6-yr grad, tuition) from scratch; its prior is **REJECT**. |
| 3′ | **Gate** | **code** | Corroborate anchor vs verifier; run **arithmetic invariants** (admits/apps==rate, SAT==section-sum, 4yr≤6yr grad, race≈100%, never publish a 0 acceptance rate). Each field → `CORROBORATED` / `CANONICAL_SINGLE` / `CONFLICT`→null / `INVARIANT_FAIL`→null / `UNVERIFIED`→null. |
| 4 | **Sections** | LLM | Eight parallel collectors for the non-deterministic sections (strategy, colleges/majors, deadlines, aid/scholarships, credit policies, student insights, strategy tactics, employer outcomes) — official sources where the field is official, multi-source community where it's opinion. |
| 5 | **Assemble** | **code** | Builds the `UniversityProfile` from sections + the *verified* deterministic values; **null-over-guess** is enforced in code (no LLM aggregator elects a value); attaches provenance + a trust report. |

## What "verified" means here

- **Deterministic-official fields** (rates, scores, counts, retention, grad, tuition, earnings, race, waitlist): anchored to the CDS/Scorecard, blind-verified for the high-stakes ones, arithmetic-gated. Published only when corroborated or canonical-single; otherwise **null with a reason** — never guessed, never coerced to `0`.
- **Official-unstructured** (deadlines, test policy, credit rules, scholarships, majors): extracted from official `.edu` pages with quotes.
- **Subjective** (vibe, tactics, tips): synthesized from multiple community sources, labeled opinion, never presented as fact.

Every published field carries `{source, url, verbatim_quote, as_of_cycle, status, confidence}` in `_provenance`.

## Full transparency: the source ledger

Beyond per-field provenance, **every URL any agent searched or fetched is logged** — used *or* rejected — so the assembly of the data is completely auditable with no human in the loop. Each agent (resolve, anchor, blind-verifiers, all 8 sections) returns a `sources_consulted` list; the assembly stage dedupes them into `_source_ledger`:

```jsonc
{ "url": "https://www.dmi.illinois.edu/.../cds_2024_2025.xlsx",
  "roles": ["resolve:common_data_set", "anchor:overall_acceptance_rate", "verify:overall_acceptance_rate", ...],
  "used": true,
  "backed_published_fields": ["overall_acceptance_rate", "sat_composite_middle_50", ...],
  "notes": ["C117 applied=73742; C118 admitted=31247 ..."] }
```

`save_profile.py` writes a human-readable **`<id>.sources.md`** report (every URL grouped into "backed a published value" vs "other consulted", with the verbatim quote) alongside the profile, plus the full ledger in `_provenance/<id>.json`. `_trust_report` carries `total_sources_consulted` and `sources_backing_published_values`. So for any number in the profile you can trace: which field → which source URL → which verbatim quote → which cycle — and also see every other source that was looked at and *not* used.

## Proven result (UIUC, year 2024 — a school *not* in the legacy IPEDS dict)

`_trust_report`: **21/48 deterministic fields published, 27 honestly null, 0 fabricated.** acceptance **42.37% (CORROBORATED** — CDS cells C117/C118), SAT 1390-1520 (CORROBORATED), ACT 30-34 (CORROBORATED), retention 94.8% (CORROBORATED), 6-yr grad 85.1%, earnings $81,054, in-state tuition $12,992, waitlist 2,794→1, IPEDS 145637 — all quote-backed to the 2024-25 CDS. Out-of-state tuition was **CONFLICT → nulled** (UIUC's OOS tuition genuinely varies by program — nulling is correct); the race breakdown came back as raw *counts* and the **race-sum arithmetic gate caught it** and nulled it rather than publish "White: 3112%"; ED/EA correctly empty (UIUC has neither). Both `model.py` Pydantic **and** the server ingest gate: **PASS**. (Output: `verified_samples/university_of_illinois_urbana_champaign.json` + `.provenance.json`.)

## Known limits & next enhancements

- **Conflict referee.** Today a `CONFLICT` field is nulled. The sibling demo (`.kb_verify_demo.js`) shows a **referee** that re-derives from the canonical authority and distinguishes a *cycle mismatch* from a real disagreement (it recovered UIUC's 42.4% vs 36.6% split correctly). Folding that in would recover safely-resolvable conflicts (e.g. ACT) instead of nulling them. *(Avoided here to keep resume cheap; it's the next iteration.)*
- **Batch scale.** For 200+ schools, drive the collect/verify agents through the Anthropic **Message Batches API** (≈50% cost) or a standalone runner; the workflow shape is unchanged.
- **Per-major admit rates.** Many schools (incl. UIUC) don't publish these in the CDS; they live on live admissions pages and are inherently single-cycle — collected in the `academic_structure` section with explicit `as_of_cycle`, not forced into the CDS-anchored core.
- **Transient infra.** Section agents can hit transient socket errors; they degrade to empty (never fabricate) and are recovered by re-running with `resumeFromRunId` (cached agents return instantly).

## Files

- `kb_collect_workflow.js` — the production collector workflow (this doc).
- `save_profile.py` — persist + dual-validate (model.py + server ingest gate) + write provenance sidecar.
- `.kb_verify_demo.js` — minimal reference collector showing the blind-verify + referee loop on 6 fields.
- `audit_consistency.py` — LLM-free internal-consistency auditor (use as a publish-blocking gate).
- `REDESIGN.md` — the full review, doctrine, architecture, and empirical validation.
