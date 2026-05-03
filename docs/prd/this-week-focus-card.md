# PRD: ThisWeekFocusCard

Status: Approved (shipped in PR #8, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

A student opening `/roadmap` shouldn't have to scan a full semester timeline to figure out what to work on right now. They open the app for ~5–15 minutes at a time, often between classes or before practice — they want a clear "the 5–8 things you should look at this session" answer, not a project plan.

## Goals

- Top of the Plan tab: a card titled "This Week" listing 5–8 items.
- Each item shows what it is, when it's due, how urgent it is, and where it lives.
- Click an item → land on the right tab + scroll to the right row.
- Inline notes affordance on each item so a student can leave themselves a note without navigating away.

## Non-goals

- A user-tunable "show me the next N items" control. The server picks the limit.
- Drag-and-drop reordering. The order is the urgency-sorted order from `/work-feed`.
- A dismissed-items list. If a student doesn't want to see something, they finish it (or change its status), and the next page-load drops it.
- Personalization beyond "what's urgent for them right now."

## Users

- Every student landing on the Plan tab.

## User stories

1. *As a student opening the app on Tuesday afternoon*, the focus card is the first thing I see and tells me my five most urgent things in 5 seconds.
2. *As a student looking at "Submit MIT app — 5 days"*, I click it and land on the Plan tab's task list, scrolled to that task.
3. *As a student looking at "Common App essay"*, I click it and land on the Essays tab with that essay row highlighted.
4. *As a student wanting to remember "Mom said to ask about merit aid before Nov 1"*, I click the notes icon on the relevant item and type the note inline.
5. *As a student with no urgent items this week*, the card shows an encouraging empty state instead of disappearing.

## Success metrics

- p50 time-to-first-action on the Plan tab drops measurably (no quantified target — observe and tune).
- Click-through rate on focus-card items > 30% (we'd love to see this; not a hard gate).
- Zero students reporting "I missed a deadline I would have caught."

## Open questions

- None at backfill time.
