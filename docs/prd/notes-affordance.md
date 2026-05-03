# PRD: Inline notes affordance

Status: Approved (shipped in PR #9, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

Every Firestore document a student writes to (roadmap tasks, essays, scholarships, colleges, aid packages) already has a `notes` field. None of it is visible in the UI today. Students keep their context-rich reminders ("Mom said to ask about merit aid before Nov 1", "Email Dr. Smith for rec letter by Friday") in external apps — meaning the moments they need that note most (when looking at the related work item) are exactly the moments the note isn't there.

## Goals

- A reusable `NotesAffordance` component that drops onto any row across the four Roadmap tabs.
- Click a small icon → expands into an inline textarea → save on blur → done.
- The UI hints whether a note exists (icon shows a count or filled-state) without forcing the student to expand it to find out.
- Optimistic update: the textarea acts saved immediately; if the API call fails, revert and toast.

## Non-goals

- Rich text formatting. Plain text only.
- Notes history / version control. Last-write-wins.
- Notes shared between users (e.g., between student and counselor). Single-author per item.
- Notes on cards that don't already have a `notes` field in Firestore.

## Users

- Students on every Roadmap tab.

## User stories

1. *As a student looking at an essay row*, I see a small notes icon that tells me at a glance whether a note exists.
2. *As a student clicking the icon*, the textarea opens inline (no modal, no navigation) and is autofocused so I can start typing.
3. *As a student typing a note*, my work persists when I tab away — no explicit "save" button to remember.
4. *As a student offline or with a flaky network*, the UI doesn't lie about success — if the save fails, I see a toast and the icon reverts to its old state.
5. *As a student on a touch device*, tapping the icon opens the same affordance the same way.

## Success metrics

- The same component used in 4+ places (focus card, essay rows, scholarship rows, college cards) without per-call-site customization.
- Notes-save success rate ≥ 99% under normal conditions.
- p50 perceived save latency under 100ms (because optimistic).

## Open questions

- None at backfill time.
