# University Profile Collector — Review & Redesign for Self-Verifying, Zero-Wrong-Value Capture

> Status: design proposal · Author: automated review (2026-06-15) · Relates to Epic #193, PR #194
>
> Question driving this doc: *"Humans can't review the data. The agent workflow itself has to verify it. Can a Claude workflow do this, and what's the strategy to keep it ~100% accurate?"*

---

## 0. TL;DR

- The current collector has **no factual verification layer at all**. Its "validation" is JSON-shape repair + Pydantic schema-checking, plus type-coercion that *fabricates plausible-but-wrong values* (missing acceptance rate → `0.0`, missing counts → `0`).
- The one reliable data path it built — the College Scorecard + IPEDS API tools — is **dead code**: imported by three `api_*` agents and never wired into any `tools=[]`. **100% of every number is authored by Gemini-2.5-Flash reading Google-search snippets, single-pass, single-model.**
- A deterministic, LLM-free audit of the **179 already-collected profiles** found: **92% carry zero provenance**, and **17% self-contradict on arithmetic** even on the few fields where two values exist to cross-check (a floor, not the true error rate). Two stored copies of UC San Diego disagree with each other (26.8% vs 28.41% acceptance; 87% vs 88% grad rate).
- A **live verification of stored numbers against schools' own Common Data Sets** found the deeper root cause: the stored values are **systematically sourced from third-party aggregators (Niche/PrepScholar) rather than primary sources**, so they're subtly and consistently off — Michigan's stored 15.6% acceptance vs the CDS's **17.9%**; Purdue's stored ACT **26-33** vs the CDS's **28-34**; Michigan's "93.7% grad rate" is actually the *Pell-subgroup of an older cohort*, not the 93.2% overall. These are exactly the errors a student would act on and a human reviewer would never catch.
- **Yes — a Claude Workflow can do this**, and it is the right tool: the orchestration primitive maps 1:1 onto an anchor → collect → adversarially-verify → consistency-gate → publish-or-null pipeline, with the deterministic gates as real code and structured-output schemas forcing provenance on every field. Demonstrated live (§7).
- The achievable bar isn't "every field filled" — true 100% on web facts is unprovable. It's **"zero wrong values ever surfaced,"** achieved by making *wrong* structurally impossible and trading coverage for correctness: **an honest `null` beats a confident hallucination.**

---

## 1. What exists today

**Stack.** Google ADK, `gemini-2.5-flash` for all 21 agents. `agent.py` wires a root `LlmAgent` → `ResearchAndSave` (`SequentialAgent`) → a `ParallelAgent` fan-out of ~13 research sub-agents → `ProfileBuilder` (LLM aggregator) → `file_saver`. A `gap_filler_agent` does targeted re-fetches of named missing fields. A separate `deep_research_cli.py` + `deep_research_prompt.md` is a one-shot Gemini deep-research path.

**Schema (`model.py`, 1081 lines, Pydantic).** A genuinely good, rich target: 12 top-level sections, ~200 fields, with per-field `[REQUIRED]/[OPTIONAL]` tags and source hints. The schema is not the problem — the *acquisition and verification* of values for it is.

**The sub-agent pattern.** Each section agent is a `Sequential( Parallel(micro-agents) → aggregator )`. Each micro-agent is a focused `LlmAgent` with `tools=[google_search]` and an `output_key`. The `ProfileBuilder` then reads all `output_key`s from session state and emits one JSON blob.

### 1.1 Confirmed defects (grounded in the code + an audit of outputs)

| # | Defect | Evidence | Impact |
|---|--------|----------|--------|
| D1 | **The deterministic API anchor is dead code.** `api_admissions_agent`, `api_financials_agent`, `api_outcomes_agent` import `get_college_scorecard_data` / `get_ipeds_*` then build micro-agents with `tools=[google_search]`. | `grep` of `tools=[` across `sub_agents/`: **45× `[google_search]`, 1× `[write_file]`, 0× any api_tool**. | Every number — even acceptance rates and earnings that exist verbatim in federal data — is hallucination-prone LLM output. |
| D2 | **Coercion fabricates values.** `validation_logic.apply_all_fixes` sets missing `overall_acceptance_rate`→`0.0`, missing `applications_total/admits_total`→`0`, etc. | `validation_logic.py:246–281, 126–145`. Audit found **20 profiles with fabricated zero app/admit counts**. | A `0.0%` acceptance rate reads as "impossible to get in," not "unknown." Worse than missing. |
| D3 | **"Validation" is shape-only.** `validate_research.py` and `run_single_university.validate_profile` run `UniversityProfile.model_validate` (structure), and on failure call `json_corrector_agent` — *another Gemini* — to fix **JSON syntax**, not facts. | `run_single_university.py:58–75, 186–208`. | A profile can be 100% schema-valid and 100% wrong. Nothing checks truth. |
| D4 | **No provenance.** `report_source_files` exists but is unenforced. | Audit: **164/179 (92%) profiles have an empty source list.** | The system cannot verify itself or be audited later — there's no link from value → source. |
| D5 | **No corroboration, single model, single pass.** Every field is one Flash call over search snippets; no second source, no second model, no re-derivation. | 21× `gemini-2.5-flash`. | Whatever the first pass says is final. |
| D6 | **No internal-consistency checks.** Nothing verifies admits/apps==rate, SAT sections==composite, race sums≈100, 4yr≤6yr grad. | Audit: **17% violate arithmetic** where checkable (13 SAT composite≠section-sum; yield≠enrolled/admits; etc.). | Mutually-contradictory numbers ship. |
| D7 | **Identity resolution covers ~40 schools.** `IPEDS_LOOKUP` is a hardcoded 40-entry dict; everything else falls back to fuzzy name search ("may be inaccurate"). | `api_tools.py:23–61`. | Even if D1 were fixed, the anchor would only reach ~40 of ~250 schools, and name-search can match the wrong school entirely. |
| D8 | **No reconciliation across re-runs / cycles.** Re-collecting a school overwrites with no diff or version check. | Two UCSD files: `26.8%` vs `28.41%`, grad `87` vs `88`, different `test_policy` text. | Silent drift; no "which is right." |

> **Net:** the pipeline is a high-quality *collector* with essentially no *verifier*. For a use case where the output drives a student's college decisions and **no human reviews it**, the missing half is the important half.

---

## 2. The accuracy doctrine (non-negotiables)

These six principles are what make "wrong" structurally hard. Everything in §3 implements them.

1. **Null-over-guess is the loss function.** False-acceptance destroys the trust contract; false-rejection only costs coverage. Every gate resolves ambiguity to `null`/`UNVERIFIED`, never to a value. The system never emits a value it cannot tie to a source — missing → `null` + a reason code, *never* a coerced `0.0`. → **Delete all value-fabricating coercion** in `validation_logic.py`; there must be no code path from "absent" to a number.
2. **The claim is the unit of work, not the profile.** Nothing is written to a profile; only `Claim` records are — `{field_path, value, field_class, source_url, source_quote, source_tier, as_of_cycle, status}`. A claim is born `UNVERIFIED` and is **structurally invalid without a `source_quote` that literally contains the value** (or its operands). No quote, no value. A partially-failed profile ships its verified fields and nulls the rest — exactly right when humans can't review.
3. **Field-class routing is static.** `DETERMINISTIC_OFFICIAL` / `OFFICIAL_UNSTRUCTURED` / `SUBJECTIVE_CROWDSOURCED` is a declared schema property (a registry), never an LLM decision. It selects the source policy, the verifier, the tolerance, and whether a field is even *eligible* to be published as fact. The LLM is *forbidden* from authoring deterministic numbers.
4. **Deterministic code is the writer-of-record where ground truth exists, and the verifier is blind.** For deterministic fields a typed API client — not an LLM — emits the value; **LLMs propose and locate, code disposes.** The independent verifier never sees the collector's value or source and **defaults to REJECT** — the only defense against two models laundering the same hallucination into a false "confirmation."
5. **Arithmetic invariants are hard gates.** Internal consistency is checked in code; any record that violates an invariant is rejected and re-collected — **never coerced** (§3.4).
6. **Confidence, staleness & per-cycle versioning are first-class.** Each field has a confidence and an `as_of_cycle`; the app can refuse low-confidence/stale fields. Versioned per admission cycle (ties into KB year-versioning, ADR 0002).

---

## 3. The recommended architecture: anchor → collect → verify → gate → publish/null

### 3.1 Pipeline (which stage is deterministic **code** vs **LLM**)

| Stage | Code / LLM | What it does |
|---|---|---|
| **0. Identity resolution** | **Code** | Resolve the school to its **IPEDS UnitID** for *any* of ~6,000 institutions via the IPEDS/Scorecard name-search API — not a 40-entry dict. Pin the UnitID as the universal join key. *(Fixes D7.)* |
| **1. Anchor** | **Code/API** | Pull every `DETERMINISTIC_OFFICIAL` field from College Scorecard + Urban-Institute IPEDS *by UnitID*. Ground truth, no LLM. Stamp `source` + `as_of_cycle`. *(Fixes D1.)* |
| **2. CDS reconciliation** | **LLM-extract + Code-check** | Fetch the school's current **Common Data Set**; extract the same fields (CDS is fresher/more granular than Scorecard's ~2-yr lag); require match-within-tolerance vs the anchor. This is the *independent corroboration* for deterministic fields. Disagreement → §3.5 adjudication. |
| **3. Unstructured collection** | **LLM (per-section fan-out)** | Official-page extraction for deadlines, test policy, AP/IB credit, supplements, scholarships, impacted majors, internal-transfer GPAs — each with a **verbatim quote + source URL**. |
| **4. Subjective synthesis** | **LLM** | Crowdsourced vibe/archetype/tips, drawn from *multiple* community sources, **labeled opinion**, attributed — never presented as fact. |
| **5. Adversarial verify** | **LLM (per-field, parallel)** | An *independent* verifier re-derives/refutes each non-anchored field from a *second* source; **defaults to reject if not independently confirmed**. |
| **6. Consistency gate** | **Code** | Run all arithmetic invariants + range checks + schema shape. **Reject-and-recollect** on violation (bounded retries). *(Fixes D2, D6.)* |
| **7. Assemble + grade** | **Code** | Build the provenance+confidence record; publish CORROBORATED/canonical, `null` everything else with a reason. Emit a per-profile **trust report** (% verified, conflicts, nulls). |
| **8. Drift monitor** | **Code (ongoing)** | Periodically re-run the anchor; if a published value drifts from the authority, alert + re-verify. **This is the standing "no-human" safety net.** |

### 3.2 Field-class routing

- **`DETERMINISTIC_OFFICIAL`** (acceptance rates, app/admit/enroll counts, SAT/ACT mid-50, GPA, race/ethnicity, retention, 4/6-yr grad, COA/tuition, yield, waitlist counts): **fetched & parsed from authorities, never authored by an LLM.** Corroborated anchor↔CDS.
- **`OFFICIAL_UNSTRUCTURED`** (deadlines, test policy, AP/IB rules, supplements, scholarships, impacted majors, internal-transfer GPA, curriculum): **LLM-extracted from official `.edu` pages, must quote**, ≥1 official source + a format/recency check, then adversarially verified.
- **`SUBJECTIVE_CROWDSOURCED`** (campus vibe, archetype, weeder courses, essay tips, red flags, analyst takeaways, gaming tactics): **LLM-synthesized from multiple community sources, labeled opinion, attributed.** Held to a "multiple independent mentions" bar, never to "fact" status.

### 3.3 The provenance + confidence record (every field)

```jsonc
"overall_acceptance_rate": {
  "value": 43.4,
  "unit": "percent",
  "source_name": "University of Illinois Common Data Set 2023-24",
  "source_url": "https://.../cds_2023_2024.pdf",
  "verbatim_quote": "Overall admit rate: 43.4% (admitted 38,650 of 89,113)",
  "source_tier": "canonical",          // canonical | official | aggregator | community
  "as_of_cycle": "Fall 2023",
  "verification_method": "anchor+cds_corroborated",
  "confidence": "high",                 // high | medium | low | none
  "status": "CORROBORATED"              // CORROBORATED | CANONICAL_SINGLE | ADJUDICATED | CONFLICT | UNVERIFIED
}
```

A consumer (the app, `counselor_agent`) can then **refuse to surface** anything below a confidence threshold or past a staleness horizon — turning "humans can't review" into "the machine won't show unverified data."

### 3.4 Arithmetic invariants (hard gates, run in code)

- `admits_total / applications_total * 100 ≈ acceptance_rate_overall` (±2pp)
- `enrolled_total / admits_total * 100 ≈ yield_rate` (±3pp)
- `sat_reading_mid50 + sat_math_mid50 ≈ sat_composite_mid50` (±40)
- `Σ racial_breakdown ≈ 100%` (85–115)
- `graduation_rate_4_year ≤ graduation_rate_6_year`
- `admitted_from_waitlist / accepted_spots * 100 ≈ waitlist_admit_rate`
- ranges ordered & in domain (SAT 400–1600, ACT 1–36, GPA 1.0–5.5, rates 0–100, rank 1–450)
- early + regular admit counts reconcile with the cycle total
- **cycle coherence**: all "current" figures share one admission cycle (no Frankenstein profiles mixing 2021 and 2024).

Any violation → the offending field(s) are dropped to `null` and re-collection is attempted; the record never ships in a self-contradictory state.

### 3.5 Conflict adjudication

When anchor↔CDS↔official disagree beyond tolerance, a **referee** (a stronger model — Claude for judgment) fetches the *single most canonical authority for that specific field and cycle* and either resolves to one quote-backed value or returns `LEAVE_NULL`. Cycle-mismatch is reported explicitly (the two sources are often just different years).

---

## 4. Is a Claude Workflow possible? Yes — and it's the right tool.

The Claude Workflow primitive maps **1:1** onto this design:

- `pipeline(schools, anchor, cdsReconcile, collect, verify, gate, assemble)` — fan a batch of schools through all stages with no barrier (school A can be in *verify* while B is still in *anchor*).
- `parallel(fields.map(verifyOne))` — per-field adversarial verification concurrently.
- `agent(prompt, { schema })` — **forces** the structured provenance record at every collection step (the model *must* return `{value, source_url, verbatim_quote, …}` or retry).
- **Plain JS** for the deterministic gates — identity resolution, the arithmetic invariants, corroboration logic, publish/null — so they are *real code*, not an LLM "please check." This is exactly what's missing today.
- `model` per agent — Claude for adjudication/judgment, a cheap model for bulk extraction. Model diversity is itself a verification signal.
- **loop-until-corroborated** — keep collecting a conflicted field from new sources until two independent ones agree or a budget is hit.

Two ways to adopt it:

- **Option A (recommended) — port orchestration to a Claude Workflow.** Replaces the ADK graph. Gains: structured-output guarantees, deterministic gates as code, model diversity, native adversarial verification, the provenance ledger.
- **Option B (incremental) — keep ADK collection, add a Claude verification *gate*.** A Claude Workflow ingests the ADK JSON and runs anchor-reconcile + invariants + provenance-grading + publish/null *before* Firestore. Lower migration cost, captures most of the accuracy benefit, and can run as the CI gate for Epic #193's yearly snapshots.

---

## 5. The "100% accuracy" strategy (honest version)

True 100% on web-sourced facts is **unprovable** — so don't chase it. Chase the bar that actually protects the student: **zero wrong values ever surfaced.** You get there by making *wrong* structurally impossible and trading coverage for correctness:

1. **Authoritative-source anchoring** — deterministic fields are *fetched*, never *authored* (kills the largest hallucination surface).
2. **Independent corroboration before publish** — anchor↔CDS / two-source agreement.
3. **Arithmetic invariants as hard gates** — internal contradiction is caught in code.
4. **Null-over-guess** — delete fabricating coercion; an honest gap beats a confident lie.
5. **Mandatory provenance + verbatim quotes** — every field is machine-auditable.
6. **Confidence + staleness + per-cycle versioning** — the app refuses low-confidence/stale data.
7. **Standing drift monitor** — re-anchors over time; the no-human safety net.

The result is not "every field filled." It's **"every filled field is right, and the rest are honestly empty,"** with a per-profile trust report quantifying coverage. For an app where a wrong acceptance rate misdirects a teenager's future, that is the only defensible definition of done.

### 5.1 Honest residual risk (what survives even this)

No design reaches *literal* 100%. After all the gates, these failure modes remain — each gets a monitor, not a silent pass:

- **Correlated-source error.** IPEDS, Scorecard, and the CDS can all derive from one mis-reported institutional submission; "independent" corroboration is then secretly single-source. *Monitor:* track source-family per field; flag any published field whose corroboration collapses to one upstream submitter.
- **Single-source coherent fabrication.** A plausible value on a sparse field with no sibling to cross-check passes the consistency engine. Correct behavior is `FLAGGED`, not `PUBLISHED` — so coverage on thin-data fields is *deliberately* low. *Monitor:* a rising publish-rate on single-source fields is a regression, not progress.
- **Staleness / cycle drift.** "Correct for Fall 2023" is wrong for the asked-about cycle — the Purdue/Wisconsin pattern, where the right number depends entirely on which cycle the store tracks (and the live demo's UIUC 42.4% vs 36.6% split was *exactly* this). The `as_of_cycle` tag mitigates; nightly re-pull when a new CDS/IPEDS release lands closes most of it.
- **Quote-faithful-but-wrong source.** The verifier confirms the value appears in the quote; a mangled page can carry a wrong number verbatim. *Monitor:* periodic deterministic re-audit (the LLM-free auditor already written) over the *published* store, with a floor target of **0 fabricated zeros and 0 invariant violations**.

**Net:** fabrication → ~0 (no code path invents a value); most silent errors convert to explicit `null`/`FLAGGED`. The irreducible residual is correlated upstream error and single-source coherent error — and for both, the honest, contract-preserving output is a flag, never a confident number.

---

## 6. Concrete next steps

1. **Stop the bleeding (today):** delete value-fabricating coercion (D2); make missing → `null`. Add the §3.4 invariants as a blocking check in `validate_research.py`; quarantine the 31 self-contradicting profiles.
2. **Wire the anchor (small):** put `get_college_scorecard_data`/`get_ipeds_*` into the `api_*` agents' `tools=[]`, and replace the 40-entry dict with live UnitID resolution (D1, D7).
3. **Add provenance (schema change):** wrap every field in the §3.3 record; enforce non-empty source on publish (D4).
4. **Stand up the Claude verification gate (Option B):** the §7 workflow, generalized to all 12 sections, run as the Epic #193 snapshot gate.
5. **Backfill:** re-verify the existing 179 profiles through the gate; publish only what passes; null the rest with reasons.

---

## 7. Empirical validation

Three runs back this design: a deterministic audit of the existing store, a live external audit against primary sources, and a **working reference collector** that proves the Claude-Workflow approach end-to-end with no human.

### 7.1 Deterministic internal audit (LLM-free, `audit_consistency.py`)

Over the 179 stored profiles, using pure arithmetic (no external data):

| Signal | Count |
|---|---|
| Profiles with **zero recorded provenance** | **164 / 179 (92%)** |
| Profiles with ≥1 **internal arithmetic contradiction** (floor) | **31 / 179 (17%)** |
| Fabricated **zero** application/admit counts | 20 profiles |
| **SAT composite ≠ section-sum** (hallucination signature) | 13 profiles |
| yield ≠ enrolled/admits · acceptance ≠ admits/apps · race-sum off | 11 profiles |

17% is a floor: most fields can't be checked because their sibling fields are null.

### 7.2 Live external audit vs schools' own Common Data Sets (5 schools × 5 fields)

The stored numbers were checked against primary sources. **3/25 fields were outright MISMATCHES and ~9 more were "CLOSE" (subtly wrong / stale)** — the *root cause* being reliance on aggregators instead of the CDS:

| School | Field | Stored | Authoritative (CDS) | Verdict |
|---|---|---|---|---|
| Michigan | acceptance rate | 15.6% | **17.9%** (15,722/87,632) | MISMATCH (aggregator value) |
| Michigan | 6-yr grad | 93.7% | **93.2%** | CLOSE — 93.7% is the *Pell-subgroup of an older cohort* (mis-attribution) |
| Purdue | ACT mid-50 | 26-33 | **28-34** | MISMATCH (low both ends, matches no cycle) |
| Purdue | SAT 25th | 1210 | **1220** | CLOSE — 1210 is a stale prior-cycle value |
| UC San Diego | acceptance (copy 2) | 28.41% | **26.8%** (Fall 2024) | MISMATCH — matches no official rate; the other stored copy is right |
| Boston U | acceptance rate | 11.1% | 10.85% (Fall 2023 CDS) | CLOSE — stale by a cycle |

Takeaway: the errors are **not random noise** — they're a *systematic sourcing defect* (aggregator-over-primary, cycle-blind) that the anchor→CDS-reconcile pipeline (§3) eliminates by construction.

### 7.3 Live reference collector — a working Claude Workflow, no human (`.kb_verify_demo.js`)

Target: **University of Illinois Urbana-Champaign** — deliberately a school **not** in the legacy 40-entry IPEDS dict (i.e., the general case the current system fails). Two independent collection paths → deterministic cross-verify + arithmetic gate → referee for conflicts → provenance ledger. Result: **6/6 high-stakes fields published with full provenance, 0 guessed.**

| Field | Published | Status | Provenance (every field) |
|---|---|---|---|
| acceptance rate | **42.4%** | ADJUDICATED | UIUC CDS 2024-25 §C1, cells C117/C118 (73,742 applied → 31,247 admitted), Fall 2024 |
| SAT mid-50 | **1390-1520** | CORROBORATED | UIUC CDS 2024-25 §C9 (C905/C907) |
| ACT mid-50 | **30-34** | CORROBORATED | UIUC CDS 2024-25 §C9 (C914/C916) |
| freshman retention | **94.8%** | CORROBORATED | UIUC CDS 2024-25 §B22 (=0.948) |
| 6-yr grad | **84.9%** | CORROBORATED | UIUC CDS 2023-24 §B (6,365/7,498); 2024-25 rows were N/A |
| test policy | **Optional** | CORROBORATED | UIUC CDS 2024-25 §C8/C8F |

The decisive moment was the **conflict adjudication**: Path A (CDS) gave 42.4%, Path B (admissions page) gave 36.6%. Instead of averaging or coin-flipping, the referee fetched the canonical CDS, recognized the split as a **cycle mismatch** (Fall 2024 CDS vs the later 2025 cycle), published the CDS-anchored 42.4% with its exact cells and a verbatim quote, and recorded that 36.6% is a *legitimate later-year figure, not an error*. That is the cycle-coherence judgment §3.4 demands — executed autonomously.

### 7.4 What this proves

- The current store is **provably unreliable** (92% unprovenanced; systematic aggregator errors a human can't catch) → the verification half is the important half.
- A **Claude Workflow can self-verify with no human** — collect from independent paths, gate on arithmetic in code, adjudicate conflicts by re-deriving from the canonical authority, and **publish-or-null with machine-checkable provenance** — and it works on the *general* school case (no hardcoded ID), at ~130k tokens for 6 fields on one school. Scaling the same pattern across all 12 sections and batching schools (Message Batches API) is the production path.
- The honest bar — **"zero wrong values surfaced; null-over-guess"** — is not only achievable, it was *demonstrated*: 6/6 right with provenance, and the one ambiguous case resolved to the correct cycle rather than a guess.

---

*Artifacts produced by this review (under `agents/university_profile_collector/`): `audit_consistency.py` (the deterministic auditor), `.kb_design_workflow.js` (audit + design panel), `.kb_verify_demo.js` (the working reference collector). The two `.js` files are runnable Claude Workflows and are the starting templates for Option A / Option B in §4.*
