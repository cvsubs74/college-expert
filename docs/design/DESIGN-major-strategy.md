# DESIGN — Major Strategy: discovery + per-school application-major strategy

- Status: bundle + agent-write trust route shipped (#310 — 1-credit add-college bundle: fit + chances; free trust-enforced agent saves); per-college major chances (#302/#306); phase 2 (#284 — major map + per-school synthesis, server-side credits, kb_gaps telemetry); phase 1 (#281/#282/#283)
- Date: 2026-07-01
- Epic: #280 · Related: #193 (collector asks → #287), #203/#252 (drift), #223 (auth), #285 (credit regression), #289 (normalizer bug)
- Provenance: synthesized from a 3-design judge panel (student-journey / data-trust / agent-native lenses, scored by an engineer judge and an admissions-domain judge; data-trust won on both cards) plus the panel's shared blind spots.

## Problem

Students (a) only consider the one major name they know, missing adjacent and
strategic alternatives, and (b) apply to overcompetitive majors (UIUC CS ≈ 7%
admit) and get rejected where a different entry point would have worked.
Nothing in the product addresses major selection: the profile holds a single
`intended_major` string, onboarding's 3-major picker posted to a route that
didn't exist (silent data loss), the Launchpad `selected_major` dropdown never
persisted (local React state; the list-enrichment whitelist stripped it), and
`compute-single-fit` ignored everything but `profile.intended_major`.

## Data reality (measured, not assumed)

Audit of all 179 legacy profiles (4,857 majors) + 3 verified samples:
- Structural fields are the trustworthy spine: `admissions_pathway` 98%,
  `direct_admit_only` 98%, `internal_transfer_allowed` 97% — and these are
  the fields the verified collector keeps.
- Per-major `acceptance_rate` is 7% present and 100% unverified; the verified
  collector drops it entirely. **Never a factor input, always hedged.**
- The `is_impacted` trap: verified UIUC CS is `is_impacted:false` (no official
  designation) at a ~7% admit. Rendering that as "not competitive" is the
  exact harm this feature exists to prevent.

## Core primitives

**Trust taxonomy** — every claim carries a `basis`:
`kb_verified` (quote-backed official) · `kb_reported` (legacy, unprovenanced —
hedge) · `opinion` (counselor take: strategic_fit_advice, tactics) · held-null
(rendered as "the school doesn't publish this", never blank, never estimated).
Legacy-only numeric fields are ALWAYS `kb_reported` (presence proves origin).

**`entry_path`** — deterministic keyword classifier over `admissions_pathway`
free text → `direct_admit | pre_major | secondary_application |
open_declaration | unclear`. The `unclear` bucket carries the school's
verbatim wording; a guessed door-policy badge is the worst trust failure.
Composite "pre-major then competitive application" resolves to the gate the
applicant faces first (`pre_major`). Corpus feasibility: ~81% classified
naively, 17% unclear; the collector-side enum (#287 ask 1) retires the
classifier from the trust path over time.

**`entry_risk`** — the crown jewel: honest competitiveness without fabricated
numbers. "Does the door lock behind you?"
- `capped_door`: `direct_admit_only` OR internal transfer not allowed —
  if you're not admitted directly you cannot switch in later.
- `elevated`: officially impacted / capped college / transfer GPA ≥3.5 /
  secondary-application gate.
- `standard`: known path, no risk flags. `unknown`: not enough structure.

**Hard guardrails** (from the domain judge's blind-spot review):
- Anti-backdoor rule: when `entry_risk=capped_door`, advice must WARN against
  the apply-easier-then-transfer play, never recommend it; the application
  and essays must cohere with the listed major (interest-fit is read).
- School-type stratification: where colleges admit by university rather than
  by major, say "the listed major barely affects admission here" instead of
  generating tactics with false gravity.
- Never charge credits for "we don't know" (phase 2).

## Architecture: where things live

The extractor lives **in the KB service** (`major_facts.py`, exposed as
`GET ?id=X&action=majors[&college=][&q=][&year=]`) — a single implementation
of the trust rules; the connector, the app, and any counselor surface consume
the same labeled facts. (All three panel designs put extraction in
profile_manager_v2 or the connector; both judges flagged the resulting
triple-implementation drift — this is the fix.) `year=` composes with ADR
0002 snapshots for per-year major comparison.

**Three-layer artifact model** (agent-native graft): the candidate set
(`profile.intended_majors[]`, ≤5 ranked, `intended_major` mirrored from the
primary — load-bearing in fit computation), the per-school decision
(`college_list/{id}.major_choice {primary, backup, rationale, source,
matched, match_confidence, kb_year, updated_at}` + legacy `selected_major`
mirror), and the narrative (research notebook, kind `strategy` + tag
`majors` — no new kind; avoids the 3-place VALID_KINDS touch).

**Match-binding ladder** (`major_match.py`): normalize + abbreviation table +
overlap ladder → exact/strong auto-canonicalize to the KB spelling; fuzzy is
stored as-given with `matched:false` and `near_misses` surfaced — never
block, never silently rewrite student intent. Durable fix is CIP codes
(#287 ask 8).

**Fit major resolution** (`resolve_intended_major`): explicit request param →
`major_choice.primary` → legacy `selected_major` → `profile.intended_major`;
the fit doc stamps `intended_major_used` + `intended_major_source` so
KB-drift and major-change causes are distinguishable later (#252).

## Phase 1 (this work) — "the major you pick actually flows, and the facts are honest"

- **KB**: `action=majors` trust-labeled extract (deterministic, free).
- **profile_manager_v2**: `save-onboarding-profile` (validated against the
  REAL OnboardingModal payload — nested under `profile_data`),
  `set-intended-majors`, `set-major-choice` (KB-validated; requires the
  school on the list; no stray items, no `added_at` re-stamp),
  `compute-single-fit` resolution order + stamps, `get_college_list`
  enrichment now returns `selected_major`/`major_choice` (the round-trip bug).
- **Connector**: `get_university_majors` (labeled facts + a `guidance` string
  carrying the trust discipline and both guardrails), `set_intended_majors`,
  `set_major_choice` (client-attributed source), `recompute_fit(major=...)`;
  server instructions gain the major-session recipe (explore interests FIRST,
  then facts, then persist, then recompute, then save narrative).
- **Frontend (#283)**: onboarding persists + "Undecided — exploring" chip;
  Launchpad picker persists via set-major-choice with an EXPLICIT recompute
  chip ("Fit was computed for {old} — Recompute with {new}? (1 credit)") —
  no silent recompute; FitAnalysisPage `?tab=majors` facts-only panel
  (entry-path badges with basis labels, amber door-policy callouts with
  verbatim quotes, hedged "Reported ~X% (unverified)" styling, explicit
  not-published sentences, data-notes footer).

## Phase 2 (#284) — synthesis + discovery

`generate-major-map` (profile → career-theme clusters citing the student's
own record as first-party evidence; grade-aware; maps pre-professional
intents like "pre-med" to real majors) and `generate-major-strategy`
(labeled-extract-grounded synthesis incl. `essay_implication` and
`what_to_verify_yourself`; post-hoc numeric-claim validator strips any %/GPA
token not present in the extract). Both 1 credit, server-side
check→402→deduct-on-success; pure miss = 200, no charge, `kb_gaps` demand
telemetry (collection priority queue for #193). Persisted at
`users/{email}/major_map/current` and `major_strategies/{university_id}`
with history archives (never destroyed). KbRefreshReviewModal-style change
card when re-collection removes previously shown reported stats. MCP
get/generate tools + Profile Major Map card + Launchpad door-policy callout.
Depends on: #285 (credit enforcement pattern), #223 caveat (server gating is
spoofable until auth lands — and deduction on caller-supplied email lets an
attacker drain a victim's credits, so sequence deliberately).

## Bundle + agent-write trust model (#310)

Owner decision (2026-07-02): **adding a college always costs 1 credit and
generates BOTH the fit analysis AND the per-college major-chances ranking** —
one credit for the bundle, not two. **Regeneration has a FREE agent path**: the
in-app Generate is 1 credit, but ChatGPT/Claude can compute the analyses
themselves (their subscription bears the LLM cost) and save them into the SAME
Firestore structure via MCP — 0 Stratia credits.

**Bundle** (`POST /add-college-analysis`, `add_college_analysis.py`): one credit
gate — reusing `fit_billing`'s exact sequencing (check → 402 insufficient /
503 on the #298 `credits_read_failed` marker → generate → deduct once AFTER
success, never on failure, never on a fallback fit) — around a single billed
unit. Inside it: (a) compute the fit (`calculate_fit_for_college`,
resolution-order major) + save-with-archive; (b) fetch the KB majors and, if
present, generate the ranking via `major_llm.run_ranking_generation` (the
extracted UNBILLED core of `run_rank_college_majors`) + save-with-archive. The
fit is the primary artifact: its failure/save-failure fails the whole add
(500, unbilled); a KB-majors miss → `major_chances:null` + note + `kb_gap`
(no second charge, fit still saved); a ranking hiccup degrades chances to null
too. `force` regenerates both (the card's "Update Fit"). The granular
`compute-single-fit` / `rank-college-majors` endpoints stay for single-artifact
in-app regen.

**Agent-write trust re-application** — THE critical correctness surface. An agent
can save for free, but it must NOT be able to write fabricated or malformed
data, so every agent write is re-validated + trust-enforced by reusing the EXACT
in-app normalizers/post-processors (agent-saved and Stratia-generated artifacts
are indistinguishable in trust):

- Shared schema (`analysis_schema.py`): FIT_SCHEMA + MAJOR_CHANCES_SCHEMA
  (fields, types, enums, required, per-kind human-readable `trust_rules`) +
  `validate_against(kind, payload)`. The SINGLE source for both the agent-facing
  describe surface (`GET /get-analysis-schema` → MCP `get_analysis_schema`,
  never wired into the app UI) and agent-write shape validation.
- `POST /save-external-fit` (`agent_writes.py`): validate shape → RE-APPLY
  `fit_computation.post_process_fit` (extracted so the in-app LLM path and the
  agent path enforce IDENTICAL rules: selectivity floor/ceiling, match% band
  clamp, factor bounds, don't-submit-when-no-scores). `acceptance_rate` + KB
  provenance are sourced from the KB, **never** the agent — so an inflated
  category for a hyper-selective school is floored regardless of what the agent
  sends. Stamp `source`(claude/chatgpt)/`basis:inference`, archive prior, save,
  0 credits.
- `POST /save-external-major-chances`: validate shape → run the agent's
  `{majors:[{name,tier,rationale}]}` through `major_llm.assemble_and_save_ranking`
  → `normalize_college_major_ranking` (entry_path/entry_risk re-derived from the
  KB, per-major numeric-claim validator strips fabricated %/GPA, capped_door
  door-lock, catalog name-match drops off-catalog majors, tiers coerced). A
  school with no KB majors → 400 (chances can't be validated). Stamp
  source/basis, archive prior, save, 0 credits.

Connector: `get_analysis_schema` (readOnly, free) + `save_fit_analysis` /
`save_major_chances` (write rate-guard, `_client_attribution` source, honest
field-error relay so the agent can fix + retry). Server instructions carry the
credit-saving recipe. Frontend surfaces a free "Update via ChatGPT/Claude"
`AgentChatHandoff` on the card; the schema is never rendered in the UI.

## Phase 3 — data depth

#287 collector asks land (entry_path enum, second-choice policy,
internal-transfer policy, undeclared option, officially published per-major
rates only, major-level provenance rows, `metadata.verification_status`
stamping — the badge switch, CIP codes); badges flip to Verified
school-by-school; major-aware drift detection in `/check-fit-recomputation`.

## Risks

- Classifier misclassification (silent wrong badge) — mitigated by the
  unclear bucket + conservative conflict handling; gate: hand-audit precision
  on `capped_door` calls before phase-2 badges headline recommendations
  (<98% → ship quotes-only).
- Matcher false binds — mitigated by exact/strong-only auto-bind.
- "Reported/unverified" is the default experience for ~176/179 schools —
  the bet is that honest-and-thin beats confident-and-fabricated; phase 1's
  facts panel is the cheapest test of that before phase-2 LLM spend.
