# PRD: Knowledge base v2 migration

Status: Approved (shipped in PR #15, doc backfilled 2026-05-03)
Owner: Engineering
Last updated: 2026-05-03

## Problem

The frontend was wired to `knowledge_base_manager_universities` (v1), a Cloud Run service backed by an Elasticsearch cluster. The cluster has been deleted; v1 returns 5xx errors. The Discover tab and any other surface that reads university data shows "Failed to fetch."

Meanwhile, `knowledge_base_manager_universities_v2` exists and is healthy: it's a Firestore-backed Cloud Function with the same logical contract. It was deployed alongside v1 as a planned successor but never had its callers cut over.

This is an outage, not a refactor. The migration consists of pointing live callers at the working backend.

## Goals

- Every live caller reads from `knowledge_base_manager_universities_v2`.
- Discover tab and college-card data come back online.
- The migration is atomic from the user's perspective — one deploy moves all callers at once.
- The legacy v1 cloud function and its env wiring can be deleted (or left dormant) after the migration sticks.

## Non-goals

- Schema changes. v2's response shape is intentionally compatible with v1's; the migration is wire-only.
- New university data. The Firestore collection v2 reads from already has the data we need.
- Bringing v1 back online. The ES cluster is gone; v1 stays dead.

## Users

- Every user of the app; the Discover tab and any cross-tab use of university data was broken.

## User stories

1. *As a student opening the Discover tab*, I see university search results instead of "Failed to fetch."
2. *As a student viewing a college card on the Colleges tab that needs canonical university metadata (mascot, location, etc.)*, the data populates as before.
3. *As an engineer reading the codebase*, every reference to the knowledge base resolves to the v2 URL — no dead pointers to v1.

## Success metrics

- Zero 5xx errors from the frontend's knowledge-base calls within 24 hours of deploy.
- Discover tab loads and renders results.
- All `VITE_KNOWLEDGE_BASE_*` env entries point at v2 URLs.

## Open questions

- Do we delete v1 immediately? Decision: leave dormant for two weeks (it's already returning 5xx, so traffic is zero), then delete. Avoids any "oh, it's still being called from a script we forgot about" surprise.
