# Design: /work-feed endpoint

Status: Approved (shipped in PR #3, doc backfilled 2026-05-03)
Last updated: 2026-05-03
Related PRD: [docs/prd/work-feed-endpoint.md](../prd/work-feed-endpoint.md)

## Where it lives

`counselor_agent` is the read-side BFF for the Roadmap surface. It already has wired URLs for `profile_manager_v2` and `knowledge_base_manager_universities` in its env, and it owns `fetch_aggregated_deadlines()` for the deadline-merge logic. Adding `/work-feed` here keeps `profile_manager_v2` focused on user-document CRUD and avoids it sprouting cross-domain logic — the pattern memo'd in `feedback_no_code_duplication.md`.

## Contract

```
GET /work-feed?user_email=<email>&limit=<int, default 8>
```

Response:

```json
{
  "success": true,
  "total": 7,
  "items": [
    {
      "id": "task-abc",
      "source": "roadmap_task" | "essay" | "scholarship" | "college_deadline",
      "title": "Submit MIT app",
      "subtitle": "MIT — Regular Decision",
      "due_date": "2027-01-05",
      "days_until": 5,
      "urgency": "overdue" | "urgent" | "soon" | "later",
      "university_id": "mit",
      "university_name": "MIT",
      "status": "pending",
      "notes": "Talk to mom about merit aid",
      "deep_link": "/roadmap?tab=plan&task_id=task-abc"
    }
  ]
}
```

Field notes:
- `source` tells the UI which icon and which `update-notes` collection to use.
- `days_until` is the integer number of days from today (negative if overdue).
- `urgency` thresholds: `overdue` < 0, `urgent` ≤ 7, `soon` ≤ 30, `later` > 30. Items without a `due_date` are always `later`.
- `deep_link` is a fully-formed URL the client can route to without any conditional logic.

## Aggregation pipeline

```
GET /work-feed
  │
  ├─ parallel:
  │     fetch /get-tasks               from profile_manager_v2
  │     fetch /get-essay-tracker       from profile_manager_v2
  │     fetch /get-scholarship-tracker from profile_manager_v2
  │     fetch /get-college-list        from profile_manager_v2
  │
  ├─ in-process: fetch_aggregated_deadlines()  (already lives here)
  │
  ├─ filter each source to active items (status NOT in {completed, final, received})
  ├─ normalize each into the unified shape above
  ├─ sort by (due_date asc, items without due_date last)
  ├─ truncate to limit
  └─ return
```

The 4 HTTP calls into `profile_manager_v2` are issued in parallel using `concurrent.futures.ThreadPoolExecutor`. At expected user volumes (~1 request per page-load) that's fine. If `profile_manager_v2` traffic ever gets hot, we add a `/get-trackers` bundling endpoint there and switch to one call.

## Caching

Per-instance in-memory dict, keyed by `user_email`, TTL 60–120s. The cache:
- Is not a correctness boundary — cache misses for stale data are tolerable; the focus card is a "what's next" hint.
- Is best-effort and per-instance — distributing this would dwarf the cost of just refetching.
- Gets invalidated nowhere; TTL alone is sufficient.

## Cold-start mitigation

`counselor_agent` deploys with `--min-instances=1` (matching the hybrid agent). The focus card is on the most-trafficked surface and we don't want it to land on a cold start.

## Endpoint registration

In `cloud_functions/counselor_agent/main.py`, the `/work-feed` route is added alongside the existing `/roadmap`, `/deadlines`, etc. Auth: same as the other routes — pulls `user_email` from the JSON body or query string and trusts the deploy's CORS + Firebase-auth filter (as established for the other endpoints in this function).

## Data model

No new collections. Pure read aggregator.

## Testing strategy

- Unit tests in `tests/cloud_functions/counselor_agent/test_work_feed.py` cover:
  - Empty user (no items in any source).
  - Single-source user (only essays, only tasks, etc.).
  - All-sources user with mixed urgencies.
  - Urgency threshold boundaries (0 days, 7 days, 30 days exactly).
  - `due_date` missing — bucketed to `later`.
  - `limit` clamps the result.
  - Notes pass through.
- All `profile_manager_v2` HTTP calls are stubbed via `unittest.mock`.

## Risks

- **Fan-out to `profile_manager_v2`**. 4 parallel calls per work-feed request. If we add another tab or another source, this grows. Mitigation: monitor; add a bundling endpoint there if it becomes a problem.
- **Cache key**. We key by `user_email` only. If a future field affects what's returned (e.g., a `?include=…` filter), we'd need to expand the key. Easy to handle when needed.
- **Sort stability across cached and fresh responses**. The sort is deterministic given the inputs, so a cache hit and a cache miss should produce the same order — but only if the source endpoints return items in deterministic order. They do today; if any starts returning unsorted items, we'd see UI flicker on cache flips. Acceptable risk; would be caught fast in manual testing.

## Alternatives considered

- **Compute on the client**. Rejected: forces every client to re-implement the same urgency logic, and four HTTP calls per page load.
- **Put the aggregation in `profile_manager_v2`**. Rejected: that function owns user-document CRUD and shouldn't grow knowledge-base awareness. `counselor_agent` already has both wires; aggregation belongs here.
- **Persist the aggregate in Firestore as a denormalized "feed" collection**. Rejected: write amplification on every source mutation, plus stale-feed-on-failed-write hazards. Live aggregation is simpler.
