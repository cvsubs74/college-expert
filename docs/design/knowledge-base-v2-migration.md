# Design: Knowledge base v2 migration

Status: Approved (shipped in PR #15, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/knowledge-base-v2-migration.md](../prd/knowledge-base-v2-migration.md)

## Context

Two functions, one logical service:

| Name | Backend | Status |
|---|---|---|
| `knowledge_base_manager_universities` (v1) | Elasticsearch (cluster deleted) | Dead |
| `knowledge_base_manager_universities_v2` | Firestore | Live |

v2 is a drop-in successor. The migration is wire-only — no schema work.

## Surface area to update

### Frontend env

`frontend/.env*` (and the `cloudbuild.yaml` placeholder block):

```diff
- VITE_KNOWLEDGE_BASE_URL=https://<v1 url>
- VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL=https://<v1 url>
+ VITE_KNOWLEDGE_BASE_URL=https://<v2 url>
+ VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL=https://<v2 url>
```

Both vars exist; both were pointing at v1; both move to v2.

### Backend env (counselor_agent)

`cloud_functions/counselor_agent/env.yaml`:

```diff
- KNOWLEDGE_BASE_UNIVERSITIES_URL=https://<v1 url>
+ KNOWLEDGE_BASE_UNIVERSITIES_URL=https://<v2 url>
```

`counselor_agent` is the only backend caller (used by `fetch_aggregated_deadlines` for per-university deadline lookups).

### deploy.sh

The deploy targets list and any health-check URLs need to match. Specifically: any `--update-env-vars` block that pinned `KNOWLEDGE_BASE_UNIVERSITIES_URL` for `counselor_agent` flips to v2.

## Compatibility

v2's response shape was designed to match v1's at the call sites that matter:

- `GET /search?q=...` returns `{ results: [{ university_id, name, ... }] }` — same.
- `GET /university/<id>` returns the per-university record — same.
- Per-university deadline fields under `application_deadlines` — same field names and shapes.

Where v2 differs (ES-specific operators that don't translate) it falls back to a Firestore-equivalent semantics. We've hand-tested the call paths used by the live frontend; nothing in our code relied on the ES-specific bits.

## Rollout

Single PR. The frontend `.env` and the `counselor_agent` deploy update happen together. Because the frontend reads its env at build time (Vite), the cutover is atomic on the next frontend deploy + the next `counselor_agent` deploy.

Order:
1. Deploy `counselor_agent` with the v2 URL.
2. Deploy frontend with the new `.env`.

If step 2 fails, rolling back the frontend (Firebase Hosting rollback) is one click; the backend can stay on v2 in either case.

## Verification

Post-deploy:

```bash
# Discover tab renders results
curl https://<frontend>/discover  # → 200 + results

# College deadlines come back
curl -X POST https://<counselor_agent>/deadlines \
  -d '{"user_email": "<test user>"}' \
  -H "Authorization: Bearer <token>" \
  | jq '.deadlines | length'
```

## Testing strategy

- No new automated tests; the migration changes URLs, not logic.
- Existing frontend Vitest + Playwright runs verify nothing else broke.
- Existing backend pytest stubs `KNOWLEDGE_BASE_UNIVERSITIES_URL` calls (it tests `counselor_agent` in isolation), so changing the URL value doesn't move tests.
- Manual smoke: load Discover, load Colleges tab, expand a card.

## Risks

- **A response-shape edge case we missed**. Mitigation: v2 has been running in parallel with v1 for weeks; we've hand-spot-checked every endpoint our code actually calls.
- **Cold start on v2**. v2 is a Cloud Function (not Cloud Run); cold starts are real. Mitigation: deploy with `--min-instances=1` if observed latency hurts. Not done in the migration PR; can be added later if needed.
- **A future caller forgets to use v2**. Mitigation: the project memory (`project_live_components_scope.md`) names v2 as the canonical version; any new caller that consults it will pick v2.

## Alternatives considered

- **Resurrect v1's ES cluster.** Rejected: cost + ops burden for a service v2 already replaces.
- **Stand up v3** with new schema. Rejected: out of scope. v2 works today; we use it.
- **Proxy v1 → v2 transparently** (keep the v1 URL alive but route to v2). Rejected: extra hop for no gain. Update the wires.
