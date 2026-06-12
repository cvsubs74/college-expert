# DESIGN — Fit analyses across yearly KB refreshes

- Status: proposed
- Date: 2026-06-12
- Related: ADR `harness/decisions/0002-university-kb-year-versioning.md` (KB is now year-versioned), `docs/design/qa-fit-testing.md` (fit algorithm)

## Problem

The Discover page and all university surfaces always render the KB's **current**
(most recent cycle) data. Fit analyses, however, are computed once and cached in
`users/{uid}/college_fits/{university_id}` with a `computed_at` timestamp but
**no reference to the KB vintage that produced them**. Recomputation triggers
only on *student profile* changes (`needs_fit_recomputation` flag) — never on
KB changes.

So when the KB refreshes for a new admission cycle:

- A student's saved fit badge (e.g. SAFETY, 82%) sits next to a Discover card
  showing *this* year's acceptance rate — computed from *last* year's. The two
  can silently disagree, including category-level errors (a school that
  tightened 46% → 35% keeps its SAFETY badge).
- Scholarship matches, deadlines in the fit's application timeline, test
  strategy, and cost commentary all describe a cycle that no longer exists.
- Nothing in the UI tells the student any of this happened.

Two failure modes to avoid, in tension with each other:

1. **Silent staleness** — the student plans against dead data.
2. **Silent churn** — fits/categories shift under the student's feet overnight,
   which is worse for trust than staleness (User Sovereignty, `ETHOS.md`).
   A TARGET→REACH flip mid-senior-fall is an emotional event, not a cache
   refresh.

## Design principles

1. **Stamp everything with its vintage.** Data without provenance can't be
   reasoned about — by us or the student.
2. **Detect, don't assume.** Most universities change little year-over-year;
   only recompute (and only notify) where inputs *materially* changed.
3. **The student applies the update; we never swap their plan silently.**
   Refresh is a guided, reviewable moment — with the old analysis retained.
4. **Respect the application clock.** A senior who has submitted applications
   should not be nudged to re-litigate their list.

## Mechanism

### 1. Provenance stamping (foundation)

At fit-compute time, copy onto the fit document the KB doc's vintage:

```
college_fits/{university_id}:
  ...existing fields...
  kb_data_year: 2025          ← university doc's data_year used as input
  kb_last_updated: <iso>      ← university doc's last_updated at compute time
  input_snapshot:             ← the handful of load-bearing inputs
    acceptance_rate: 44.0
    test_policy: "..."
    deadlines_hash: <sha1 of application_deadlines>
    total_coa: ...
```

`input_snapshot` makes staleness *diffable* without fetching version history.

### 2. Staleness detection (server, cheap, deterministic)

Extend the existing `checkFitRecomputationNeeded` response (already polled by
the frontend on load) with a KB dimension:

```
GET /check-fit-recomputation
→ {
    needs_recomputation: bool,            # existing: profile-driven
    kb_updates: [                          # new: KB-driven, per saved fit
      {
        university_id, university_name,
        fit_kb_year: 2025, current_kb_year: 2026,
        changes: [
          {field: "acceptance_rate", old: 44.0, new: 35.2, severity: "material"},
          {field: "application_deadlines", severity: "material", detail: "ED moved Nov 1 → Oct 15"},
          {field: "total_coa", old: 82000, new: 86000, severity: "minor"},
        ],
        projected_category_shift: "SAFETY → TARGET" | null,
      }, ...
    ]
  }
```

Severity rules are deterministic (no LLM cost):
- **material** — acceptance rate crosses a selectivity-tier boundary or moves
  >5 points; any deadline date change; test-policy change; intended-major
  program removed/added.
- **minor** — rate moves within tier; COA drift <10%; rank moves.
- `projected_category_shift` comes from the existing selectivity floor/ceiling
  rules applied to the new rate — a guaranteed-correct lower bound on impact,
  shown *before* spending an LLM call.

### 3. UX flow

**a. The moment** — first session after a KB cycle change touching the
student's list: one non-blocking banner on Launchpad/Discover:

> 🗓️ **2026–27 admissions data is in.** 3 of your 8 colleges changed in ways
> that may affect your fit. **[Review what changed]** · [Later]

No banner if nothing material changed for *their* list (minor-only changes get
a passive vintage chip update, nothing more).

**b. Review screen** — one card per affected college, concrete old→new facts,
not vibes:

> **Northeastern University**   `fit computed on 2025–26 data`
> - Acceptance rate **44% → 35%** — selectivity tier changed
> - ED deadline **Nov 1 → Oct 15**
> - Projected fit: **SAFETY → TARGET**
> [Update fit analysis]   [Keep last year's]

Plus one **[Update all]**. Updating recomputes with current KB data; the old
fit is retained (see d).

**c. The reveal** — recomputed fit shows the delta, explained in the data's
terms: "Acceptance rate tightened 44% → 35%, so this moved from Safety to
Target. Your essays plan doesn't change; your timeline does — ED is now
Oct 15." Side-by-side old/new on first view.

**d. History, mirrored from the KB** — prior fit docs move to
`college_fits/{id}/history/{kb_year}` on recompute (same pattern as
`universities/{id}/versions/{year}`). The fit modal gets "View 2025–26
analysis". Nothing the student saw is ever destroyed.

**e. Vintage chips everywhere a fit surfaces** (FavoriteCard, FitAnalysisModal,
Launchpad): neutral `Based on 2026–27 data` when current; amber
`2025–26 data — update available` when stale. The chip *is* the passive
fallback for students who dismiss the banner.

**f. Application-clock guardrails:**
- College-list entries with application status submitted/accepted/committed:
  excluded from nudges entirely; their fit keeps a quiet "as of 2025–26" chip.
- Seniors after Oct 1: deadline changes still propagate to the roadmap (those
  are facts), but fit-category nudges are suppressed unless the change is
  material *and* the app is unsubmitted.
- Roadmap tasks built on a moved deadline get a visible "deadline updated
  Nov 1 → Oct 15" diff on the task rather than a silent date swap (planner
  already regenerates on "Refresh Tasks"; this adds the annotation).

### 4. What we deliberately don't do

- **No automatic mass recompute on ingest.** 191 universities × N students ×
  LLM cost, most of it churn the student never asked for — and it swaps plans
  silently. Detection is free; computation is user-triggered (or triggered by
  their existing profile-change path).
- **No blocking modals.** The banner is dismissible; the chips carry the state
  thereafter.
- **No auto-deleting old fits.** History is part of the product story
  ("colleges got harder this year" is itself counseling-relevant).

## Implementation phases

1. **Stamp + detect** (backend): provenance fields on fit save;
   `kb_updates` in check-fit-recomputation; unit tests on severity rules.
2. **Chips + banner + review screen** (frontend): vintage chip component;
   banner driven by `kb_updates`; review cards with per-college update CTA.
3. **History + reveal** (full): fit history subcollection; side-by-side delta
   view; roadmap deadline-diff annotations; application-clock suppression.

Phase 1 is pure backend and unblocks everything; chips alone (phase 2 partial)
already kill the silent-staleness failure mode.
