# Design: QA Agent admin dashboard

Status: Draft (awaiting approval)
Last updated: 2026-05-03
Related PRD: [docs/prd/qa-agent-dashboard.md](../prd/qa-agent-dashboard.md)

## Architecture

```
        admin browser
        ┌───────────────────────────────────────────┐
        │  /qa-runs       /qa-runs/<run_id>         │
        │  React pages, Firebase ID token in        │
        │  Authorization header                     │
        └────────┬────────────────────┬─────────────┘
                 │                    │
                 ▼                    ▼
        ┌─────────────────┐    ┌──────────────────────┐
        │ Firestore SDK   │    │  qa-agent function   │
        │ (read qa_runs/) │    │  POST /run            │
        │ rules: admin    │    │  POST /suggest-cause  │
        │ allowlist only  │    │  GET  /github-issue   │
        └─────────────────┘    └──────────────────────┘
```

Two read paths: Firestore directly (for the run list + detail) and qa-agent endpoints (for actions: trigger, suggest, build issue payload). The split keeps reads fast and stateless while keeping action mutations behind the agent's auth boundary.

## Authentication

### qa-agent: dual auth

Today: `X-Admin-Token` only.

After this PR: accept *either* of:
- `X-Admin-Token: <token>` — for curl + Cloud Scheduler (existing path, unchanged).
- `Authorization: Bearer <firebase ID token>` AND the verified email is in `QA_ADMIN_EMAILS` env var (default: `cvsubs@gmail.com`) — for browser users.

Both are mutually exclusive on a single request — present one or the other. Token check happens first; ID-token verification (via `firebase_admin.auth.verify_id_token`) only if token absent.

### Firestore: security rules

Add to `firestore.rules`:

```
match /qa_runs/{runId} {
  allow read: if request.auth != null
              && request.auth.token.email in ['cvsubs@gmail.com'];
  allow write: if false; // only the qa-agent SA writes; SA bypasses rules
}
match /qa_scenarios/{archetypeId} {
  allow read: if request.auth != null
              && request.auth.token.email in ['cvsubs@gmail.com'];
  allow write: if false;
}
```

The qa-agent service account writes via Admin SDK and bypasses rules entirely. Frontend reads through the user's signed-in Firebase Auth session.

## Frontend

### Routes

```jsx
<Route path="/qa-runs"           element={<AdminGate><QaRunsListPage /></AdminGate>} />
<Route path="/qa-runs/:runId"    element={<AdminGate><QaRunDetailPage /></AdminGate>} />
```

`AdminGate` is a small wrapper that:
- Reads `currentUser.email`
- If not in the local `ADMIN_EMAILS` constant (mirrors the backend list), renders a 403-shaped page
- Otherwise renders children

This is a soft gate — the hard gate is the Firestore security rule.

### Pages

**`QaRunsListPage`**
- Top: 30-day pass-rate sparkline (`<SparklineByDay runs={runs} />`)
- Below: a "Run now" panel with a button + a single-scenario dropdown
- Below: a sortable / filterable table of recent runs (default sort: most recent first)
- Each row: time, trigger, actor, pass/fail badge with counts, duration, click to detail

**`QaRunDetailPage`**
- Top: run header (id, time, trigger, actor, summary)
- Per scenario card:
  - Scenario id + description + variation
  - Pass/fail badge + duration
  - "Suggest cause" button (failing scenarios only)
  - "Report bug" button (failing scenarios only)
  - Expand → list of steps; each step shows endpoint + status + elapsed + per-assertion check + redacted request + response excerpt

### Components

```
frontend/src/pages/
  QaRunsListPage.jsx
  QaRunDetailPage.jsx

frontend/src/components/qa/
  AdminGate.jsx            ← email allowlist + 403 fallback
  RunsTable.jsx            ← sortable list
  PassFailBadge.jsx        ← coloured chip
  SparklineByDay.jsx       ← 30-day mini chart from runs[].started_at + summary
  RunNowPanel.jsx          ← Run now button + single-scenario picker
  ScenarioCard.jsx         ← per-scenario expandable card
  StepRow.jsx              ← a single step's display with assertions
  AssertionList.jsx        ← list of {name, passed, message}
  SuggestCauseModal.jsx    ← LLM analysis modal
  ReportBugButton.jsx      ← opens pre-filled GitHub issue
```

### Data fetching

Use the existing Firebase SDK (`firebase/firestore`) for reads — the project already has Firebase Auth wired and an `app` instance.

```js
import { getFirestore, collection, query, orderBy, limit, getDocs, doc, getDoc } from 'firebase/firestore';

// list page
const db = getFirestore();
const q = query(
  collection(db, 'qa_runs'),
  orderBy('started_at', 'desc'),
  limit(30),
);
const snap = await getDocs(q);
const runs = snap.docs.map(d => d.data());
```

```js
// detail page
const ref = doc(db, 'qa_runs', runId);
const snap = await getDoc(ref);
const run = snap.exists() ? snap.data() : null;
```

### "Run now" trigger

POST to qa-agent `/run` with `Authorization: Bearer <ID token>` instead of `X-Admin-Token`. Response shape unchanged (`{run_id, summary, success}`).

### Sparkline

A 30-day-wide canvas. For each day, count runs where `summary.fail == 0` (green) vs. `summary.fail > 0` (red). Render a simple stacked bar per day. No external chart library — build inline with SVG.

### Single-scenario picker

The dropdown lists archetype IDs. The QA agent already exposes scenarios at JSON deploy time, but the browser doesn't have access. Two options:
- **A new GET `/scenarios` endpoint on qa-agent**: returns the list of archetype IDs (no auth needed; just metadata). Cheap and clean.
- **Hardcode the list in the frontend**: drift risk.

Recommend **A** — added in the same PR, returns `{scenarios: [{id, description}, ...]}`.

## Backend additions to `qa_agent/main.py`

### Dual auth

Refactor `_check_admin_token` into `_check_auth` that accepts either gate:

```python
def _check_auth(request, expected_token, admin_emails):
    # Path 1: admin token
    provided_token = request.headers.get('X-Admin-Token', '')
    if expected_token and secrets.compare_digest(provided_token, expected_token):
        return {'ok': True, 'actor': 'token'}
    # Path 2: Firebase ID token + email allowlist
    auth_hdr = request.headers.get('Authorization', '')
    if auth_hdr.startswith('Bearer '):
        try:
            from firebase_admin import auth as _fa
            decoded = _fa.verify_id_token(auth_hdr.removeprefix('Bearer '))
            email = decoded.get('email', '')
            if email and email in admin_emails:
                return {'ok': True, 'actor': email}
        except Exception:
            pass
    return {'ok': False, 'actor': None}
```

`QA_ADMIN_EMAILS` env var is comma-separated; default `cvsubs@gmail.com`.

### `GET /scenarios`

```python
elif request.method == 'GET' and path == 'scenarios':
    archetypes = corpus.load_archetypes()
    return _cors({
        'scenarios': [
            {'id': a['id'], 'description': a.get('description', '')}
            for a in archetypes
        ],
    })
```

No auth — the list is metadata, not sensitive.

### `POST /suggest-cause`

```
Request body: { "run_id": "...", "scenario_id": "..." }
Response:    { "suggestion": "<2-3 paragraph string>" }
```

Pulls the run from Firestore, finds the named scenario's failing steps, sends a focused prompt to Gemini Flash:

> Given this failing scenario, distinguish "agent bug" from "app regression" and propose a likely root cause. Be concrete; cite specific request/response fields.

In-memory dedup per `run_id+scenario_id` for the lifetime of the function instance — repeat clicks return the cached suggestion.

### `POST /github-issue`

```
Request body: { "run_id": "...", "scenario_id": "..." }
Response:    { "issue_url": "...", "issue_title": "...", "issue_body": "..." }
```

Two output modes (controlled by env `QA_ISSUE_MODE`):
- **`url`** (default): construct a `https://github.com/<repo>/issues/new?title=...&body=...` URL. Browser opens it in a new tab; user reviews + submits manually.
- **`api`** (future): use a `GH_TOKEN` secret to create the issue directly. Out of scope for this PR.

Body template:

```
**QA agent run**: {run_id}
**Scenario**: {scenario_id}
**Status**: FAIL ({pass}/{total} steps passed)
**Trigger**: {trigger} by {actor}

### Failing step
- Endpoint: {endpoint}
- Status: {status_code}
- Elapsed: {elapsed_ms}ms

### Failing assertions
{assertion list}

### Request
```json
{request}
```

### Response (excerpt)
```
{response_excerpt}
```

(Generated automatically; please add reproduction context.)
```

## Adding tests

- Vitest for the React pages: list renders runs from a mocked Firestore call; detail expands a scenario; admin gate redirects when email isn't in the allowlist.
- pytest for the new qa-agent endpoints: `/scenarios` returns the corpus; `/suggest-cause` calls Gemini (stubbed) and returns the response; `/github-issue` returns a properly URL-encoded link.

## Phasing

| PR | Scope |
|---|---|
| 1 | Dual auth on qa-agent (X-Admin-Token OR Firebase ID token + email allowlist). `GET /scenarios`. Firestore security rules. |
| 2 | Frontend `/qa-runs` list + detail page + AdminGate + RunNowPanel. Direct Firestore reads. |
| 3 | `POST /suggest-cause` (LLM analysis) + the `SuggestCauseModal` component. |
| 4 | `POST /github-issue` (URL builder) + the `ReportBugButton`. |
| 5 | Sparkline + per-archetype history panel on the list page. |

Each PR is independently shippable. PR 1 unblocks PR 2; the rest can land in any order.

## Risks

- **Firestore security rules misconfigured** — soft gate alone (frontend `AdminGate`) is not enough. Mitigation: rules-deploy step in `deploy.sh` + a one-shot test run that confirms a non-admin email gets denied.
- **LLM "Suggest cause" generates plausible but wrong analysis** — that's already the state of the art; we surface the suggestion with a "this is a guess, verify before acting" disclaimer. No autonomous decisions.
- **GitHub URL length limits** — `?body=...` URLs cap at ~8KB. Mitigation: truncate request/response excerpts; if over limit, fall back to opening a blank new-issue page with title only.
- **Trigger spam** — "Run now" + LLM costs scale with clicks. Mitigation: a single-flight per-tab so the same user can't have two pending runs.

## Alternatives considered

- **Server-rendered admin page** instead of SPA — more code; no advantage given we already have a React app.
- **Push notification on failure** — useful but orthogonal; can ship as a separate effort once the dashboard is in.
- **Use Datadog Synthetics** for the dashboard layer — proper monitoring tool, but requires importing data and gives up bespoke integration with our scenario shape. Stick with custom for v1.
