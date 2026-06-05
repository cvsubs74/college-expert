---
name: kb-snapshot
description: Capture a versioned yearly snapshot of a university knowledge-base profile via the source registry + schema-constrained capture workflow from docs/design/university-kb-capture-automation.md (epic #193). Use for KB ingest/refresh — not for ad-hoc fix_*.py edits.
disable-model-invocation: true
---

# Versioned university KB snapshot

Replaces the scattered, non-idempotent one-off scripts (`update_*.py`,
`fix_*.py`, `update_essay_prompts_batch*.py`, `update_*deadlines.py`) with one
repeatable, versioned procedure.

**Authoritative design:** `docs/design/university-kb-capture-automation.md`
(epic [#193]). Read it before running — this skill is the operational summary,
the design doc is the contract.

## Workflow

1. **Resolve sources.** Pull the university's entries from the source registry
   (authoritative URLs per field/section). Do not scrape arbitrary pages.
2. **Schema-constrained capture.** Extract into the constrained KB schema
   (~40 models / ~220 fields). Reject/flag fields with no registry-backed
   source rather than hallucinating.
3. **Write a versioned snapshot.** Store under the yearly versioned store —
   **never overwrite the previous cycle in place**. The prior cycle stays
   readable for diffing and rollback.
4. **Diff & report.** Surface what changed vs. the previous cycle (especially
   `deadline_date` and other structured fields) so a human can sanity-check
   before it goes live.

## ⚠ Open decisions (pending #193 — confirm with the user before relying on these)

- **Cycle key convention** — e.g. `2026-27` admissions cycle vs. calendar year.
  Not yet finalized.
- **Retention policy** — how many past cycles to keep before pruning.
- **Orchestration** — hybrid Claude-workflow + ADK collector; phased rollout
  starts with the versioned store. Confirm the current phase before running.

## Hard rules

- **Non-idempotent collector caveat.** The legacy ADK
  `university_profile_collector` overwrites on ingest with no versioning — do
  **not** route through it for snapshots until the versioned store is in place.
- **Source-backed only.** Every captured field traces to a registry source.
- **No in-place overwrite of a prior cycle.** Versioned snapshots are
  append/new-cycle, never destructive.
- **Account pin.** Any `gcloud`/`firebase`/Firestore access uses
  `--account cvsubs@gmail.com --project college-counselling-478115`.
