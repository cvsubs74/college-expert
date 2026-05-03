# PRD: Legacy route redirects

Status: Approved (shipped in PR #10, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03
Parent: [docs/prd/roadmap-consolidation.md](./roadmap-consolidation.md)

## Problem

Before consolidation, students navigated through four separate routes: `/counselor`, `/progress`, `/essays`, `/applications`. Bookmarks, browser history, and external links (e.g., support emails, the dashboard URL printed on Stripe receipts) all reference those URLs. Removing them outright would break every existing path into the app.

## Goals

- Each legacy route still resolves — but to its corresponding tab on `/roadmap`.
- Query params survive the redirect where they're meaningful (`/applications?school=stanford` → `/roadmap?tab=colleges&school=stanford`).
- Browser back button skips the legacy URL — a redirect should be invisible to the user.
- The single nav entry "Roadmap" replaces the four legacy entries.

## Non-goals

- Permanent legacy support. The redirect rules can come out once observed traffic on the old URLs goes to zero.
- Server-side redirects (e.g., Firebase Hosting rules). Client-side via react-router is enough for a SPA.
- Redirecting from external links that include hash fragments — those are best-effort.

## Users

- Anyone arriving via a bookmark, an old email link, the browser's back button, or a copied link.

## User stories

1. *As a student with `/counselor` bookmarked from last semester*, I land on the Plan tab on `/roadmap` and my bookmark still works.
2. *As a student with `/applications?school=stanford` in their browser history*, I land on the Colleges tab with Stanford pre-selected.
3. *As a student using browser back from `/roadmap?tab=plan`*, I return to wherever I was before — not to `/counselor` (because we used `replace`).
4. *As an engineer reading the App.jsx routes file*, the redirect rules are all in one place and clearly mark which legacy URL maps to which tab.

## Success metrics

- Every legacy URL resolves to the correct tab on first navigation.
- Zero user reports of broken bookmarks/links during the rollout window.
- 30-day decay of legacy URL traffic to <1% of initial — at which point we can consider removing the redirect rules.

## Open questions

- How long do we keep the redirects? Default: indefinitely. They cost ~12 lines of code; the benefit of working bookmarks compounds. Revisit only if they ever become a maintenance burden.
