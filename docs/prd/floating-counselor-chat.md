# PRD: Floating counselor chat launcher

Status: Approved (shipped in PR #11, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

Pre-consolidation, the counselor chat lived as a left sidebar inside `/counselor`. After consolidation, the chat needs a home that:
- Doesn't permanently consume horizontal space on every Roadmap tab.
- Is reachable from every tab without a navigation step.
- Doesn't break the four-tab visual hierarchy of the Plan / Essays / Scholarships / Colleges layout.

## Goals

- A floating launcher button (bottom-right corner, always visible on `/roadmap`) that opens the chat panel.
- The chat panel is a fixed-position overlay (380×600) — visible alongside the page content, not modal.
- Open/closed state persists across page reloads via localStorage.
- Smooth open/close animation (no layout shift on the underlying page).
- Chat content is unchanged from the prior `/counselor` sidebar — same agent, same conversation API.

## Non-goals

- Multiple simultaneous chats. One panel.
- Mobile-specific full-screen mode. Same fixed overlay on every breakpoint for now (the panel is small enough to fit even on narrow viewports).
- Chat history search, export, or other power-user features. Strictly the launcher + the existing chat content.
- Notifications / unread count badges on the launcher. The chat is reactive — students open it when they want it.

## Users

- Students on every Roadmap tab.

## User stories

1. *As a student on the Plan tab*, I see a chat-bubble button in the bottom-right corner that I can click to talk to my counselor agent.
2. *As a student on the Colleges tab with the chat open*, switching tabs keeps the chat visible — it's not bound to one tab.
3. *As a student who opens the chat, refreshes the page, and reopens the app*, the chat is still open. (Or, if I closed it, it's still closed.)
4. *As a student wanting to focus on a task*, closing the chat hides it cleanly with no leftover residue.

## Success metrics

- Chat-launcher click-to-open latency < 100ms (no API call required to open).
- Open-rate (% of `/roadmap` sessions that open the chat at least once) — track and observe; no hard target yet.
- Zero regressions in chat-message round-trip latency vs. the pre-consolidation sidebar.

## Open questions

- None at backfill time.
