# PRD: /update-notes endpoint

Status: Approved (shipped in PR #4, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

Every Firestore subcollection a student writes to (`roadmap_tasks`, `essay_tracker`, `scholarship_tracker`, `college_list`, `aid_packages`) already has a `notes` field on its documents — but no UI ever wrote to it. The Roadmap consolidation introduces an inline `NotesAffordance` component that wants to save a single text field per item, regardless of which collection that item belongs to.

There are five existing per-collection update endpoints (`update-essay-progress`, `update-scholarship-status`, etc.). Each accepts a different request shape. Wiring the notes UI into all five would scatter the same notes-saving logic across five call sites and three different request schemas.

## Goals

- One write endpoint that updates the `notes` field on any of the five whitelisted collections.
- A single client-side `saveNotes(collection, itemId, notes)` function that's the only thing the `NotesAffordance` component needs to know.
- Server-side enforcement that the `notes` field is the only thing that gets touched — no accidental cross-field writes.

## Non-goals

- A general-purpose "patch any field on any collection" endpoint. The whitelist is intentional.
- Notes-history versioning. The current value overwrites; if a student wants version control they have it already through their own external tool.
- Rich-text notes. Plain text only.
- Notes on collections that don't already have the field.

## Users

- The `NotesAffordance` component (used on every row of every Roadmap tab).
- The `ThisWeekFocusCard` component (when a student edits notes from the focus card).

## User stories

1. *As a student writing a note on an essay row*, the save fires once on blur and persists immediately. If I refresh, my note is still there.
2. *As a student writing a note on a roadmap task*, same UX, same network call shape.
3. *As an attacker who knows our endpoints*, I cannot use this endpoint to mutate any field other than `notes` — even by sending extra keys in the JSON body.

## Success metrics

- One endpoint, five collections covered.
- Zero cross-field corruption (enforced by code that only writes `notes` and `updated_at`).
- p50 write latency under 250ms.

## Open questions

- None at backfill time.
