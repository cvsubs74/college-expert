# PRD: /work-feed endpoint

Status: Approved (shipped in PR #3, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

The Plan tab on `/roadmap` needs a "This Week" focus card that shows the 5–8 most urgent items across every kind of work the student tracks: roadmap tasks, essays, scholarships, and college deadlines. The data already exists, but it's spread across four different collections owned by `profile_manager_v2` plus a deadline-aggregation helper inside `counselor_agent`.

A naïve frontend implementation would issue four parallel HTTP calls, then run urgency-bucketing and sort logic in JavaScript. That spreads policy ("what counts as urgent?") across every client and forces every client to re-implement the same sort. We want one canonical answer the server computes.

## Goals

- Single endpoint a frontend can call to populate the focus card.
- Urgency thresholds defined once, server-side.
- Server-side sort and limit so the client renders what it gets.
- Stable item shape across all four sources so the UI renders one component, not four.

## Non-goals

- A general-purpose "search across all collections" endpoint. This is shaped specifically for the focus card.
- Mutation. The endpoint is read-only; checking off a task or marking an essay done goes to the source-collection endpoint that already owns it.
- Per-user personalization beyond "what's urgent for them right now". No ranking by ML signals, etc.

## Users

- The Plan tab's `ThisWeekFocusCard` component (the only caller in M1).
- Future: any other surface that wants a unified urgency feed (e.g., a notification widget, a daily-digest email).

## User stories

1. *As the focus card*, I get back a sorted list of items with `urgency` already computed, so I can render bucket-colored badges without owning the threshold logic.
2. *As the focus card*, every item carries a `deep_link` so a click takes the student to the right tab + item with no client-side routing logic.
3. *As an item with notes*, my current notes value comes back inline so the focus card can show a notes affordance without an extra round trip.

## Success metrics

- p50 response time under 500ms when warm; under 2s on cold start.
- One round-trip from the client to populate the focus card (vs. four if we'd done it client-side).
- Zero divergence between client urgency labels and server urgency labels (because the server is the only computer of them).

## Open questions

- None at backfill time. The 60–120s per-instance cache TTL has held up under early use; we revisit if staleness complaints come in.
