# PRD: Per-college mini-dashboard

Status: Approved (shipped in PR #14, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

The Colleges tab lists every college a student is applying to as a card. Each card shows the school name and overall deadline today. To see what they actually need to do for that school — which essays are required, what's the application deadline by type (RD/EA/ED), what scholarships apply — the student has to navigate to other tabs and mentally piece it together.

A student picking which school to work on next wants a per-school view: "for MIT, what's open, what's due, what essays do I owe." All the data exists; it's just not joined and rendered together anywhere.

## Goals

- Each college card on the Colleges tab is expandable.
- Expanded view shows: deadline + type, essay count + their statuses, scholarship count + their statuses, overall progress bar, and the school's notes affordance.
- Expand state is per-card, multiple cards can be expanded simultaneously.
- Expand state survives tab switches (so a student who expanded MIT, switched to Plan, switched back, sees MIT still expanded).

## Non-goals

- A separate per-school full-screen view. Inline expansion only.
- Editing essays or scholarships from the mini-dashboard. The expanded view links out to the relevant tabs (via artifact_ref pills).
- Per-school chat with the counselor agent. Single chat surface (the floating launcher).
- Sortable/filterable colleges list. Existing list ordering is preserved.

## Users

- Students with at least one college on their list, picking what to work on next.

## User stories

1. *As a senior with five schools on my list*, I expand the MIT card and see "RD due Jan 5, 2 supplemental essays (1 drafted, 1 not started), 1 scholarship matching." Now I know what to do for MIT in 5 seconds.
2. *As a student with two cards expanded simultaneously*, I can compare the workload between two schools side by side.
3. *As a student deep-linking from the Plan tab via an artifact-ref pill (`?school=mit`)*, I land on the Colleges tab with MIT auto-expanded.
4. *As a student wanting to leave a note about a specific school* ("Email admissions about scholarship deadline"), the expanded card has a notes affordance for the college's `college_list` row.

## Success metrics

- p50 expand-to-content-rendered latency under 50ms (data already on the page).
- Students who expand at least one college: meaningful share of Colleges-tab sessions.
- Zero regressions in existing collapsed-card list rendering.

## Open questions

- Should the expanded view show a small "next action" recommendation? Defer; the focus card already serves that purpose globally.
