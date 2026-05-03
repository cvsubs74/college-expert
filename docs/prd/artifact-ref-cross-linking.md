# PRD: Artifact-ref cross-linking

Status: Approved (shipped in PR #12, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

The Plan tab's timeline shows generic semester tasks like "Submit RD Applications" and "Research universities — programs, admissions, fit." These tasks are real work, but they're abstract — students see "Submit RD Applications" and have to mentally translate that into "I need to finish the MIT app, Stanford app, and Berkeley app." Then they have to navigate from the Plan tab to the Colleges tab to find the per-school details.

Every translated task should connect back to the concrete artifact it's about: the MIT college card on the Colleges tab, the personal statement row on the Essays tab, etc. The translation already happens in `planner.translate_task` (in M1 it produced per-school task titles like "Submit MIT app"); the missing piece is a deep link from the task to its target.

## Goals

- Every translated task carries an `artifact_ref` describing exactly where the student should go to do that task.
- The frontend renders an `artifact_ref` as a small green pill ("Open MIT ›") next to the task title.
- Clicking the pill navigates to the target tab + scrolls to the target item, with no per-task bespoke logic on the client.
- The pill labels itself contextually — for a UC group task covering 3 schools, it shows "Open UC Berkeley, UCLA, UCSD" — so the student knows which school(s) the task touches before clicking.

## Non-goals

- Editing the artifact from the pill. Pill is read-only navigation.
- Inverse links (artifact → task). Students can find their tasks from the Plan tab; the missing direction was Plan → artifact.
- Multi-target pills. Each pill goes to one place. UC group tasks resolve to a single anchor school; the label conveys that the task covers all UCs.

## Users

- Students looking at the Plan tab, especially during application crunch in senior fall.

## User stories

1. *As a senior looking at "Submit MIT app — Jan 5"*, I see an "Open MIT ›" pill, click it, and land on the Colleges tab with the MIT card expanded.
2. *As a junior looking at "Research MIT — programs, admissions, fit"*, the same pill takes me to MIT's college card on the Colleges tab so I can read about the programs.
3. *As a senior with three UCs on my list looking at the UC group task*, the pill says "Open UC Berkeley, UCLA, UCSD" so I know all three are covered before clicking.
4. *As a student looking at "Draft Common App essay"*, the pill takes me to the Essays tab with the Common App row in view.
5. *As a student looking at "Verify materials received"*, the pill takes me to the Colleges tab as a whole (it's a per-tab task, not per-school).

## Success metrics

- Every translated task in `senior_fall` (the densest template) has an `artifact_ref`. Spot-checked across the other templates.
- Click-through rate from the Plan tab to a deep-linked artifact > 20% (loose target — observe).
- Zero broken pills (each pill resolves to a real, scrollable target item).

## Open questions

- Should the pill also show a status-progress indicator (e.g., "Open MIT — 2 of 5 things done")? Defer until we have a clear signal of whether the simple version is enough.
