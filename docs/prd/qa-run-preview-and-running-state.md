# PRD — Run Preview + Running State

## Problem

Today the "Run now" button is opaque:
- The user clicks → button shows "Running…" → 2-3 minutes pass with no signal of what's happening → eventually the run completes and shows up in Recent Runs.

The user has no idea what's going to be tested before committing, and no way to see what's in flight while it runs. If they navigate away or refresh, they lose the "Running…" state entirely.

## Goal

Make the run lifecycle visible:

1. **Pre-run preview**: when the user clicks Run now, show them what the agent picked (scenarios, surfaces, why each was chosen) before they commit.
2. **Running indicator in Recent Runs**: as soon as a run starts (manual OR scheduler-triggered), it appears in the Recent Runs table with a `Running` badge.
3. **In-progress detail page**: clicking the running entry shows the picked scenarios + a progress indicator (which scenarios are done, which are next).

## Non-goals

- Live per-step streaming — too complex; per-scenario granularity is enough.
- Cancelling an in-flight run — out of scope for v1.
- Showing real-time logs — the existing run report is enough; just needs to render while status is `running`.

## Users & jobs

Single user: the admin.

Jobs:
1. **Confirm intent**: "Before I burn 2-3 min waiting, what's this run going to do?"
2. **See in-flight work**: "I clicked Run an hour ago — did it finish? Is it stuck?"
3. **Watch progress**: Click the running entry, see "3 of 4 scenarios passed so far" rather than waiting blind.
4. **Survive refresh**: If I close the tab and come back, I can still see what's running.

## Success criteria

- Click Run now → preview modal appears with picked scenarios + rationale within 1-2 seconds.
- After confirming, the Recent Runs row appears within 2 seconds with a `Running` badge.
- Refreshing the page does not lose the running indicator (state lives in Firestore, not browser memory).
- Detail page for a running run shows the scenarios the agent picked + their states (`pending` / `passing` / `failing`) as the run progresses.
- When the run finishes, the badge flips to `pass`/`fail` automatically (Firestore listener picks up the doc update).

## Constraints

- Cloud Functions Gen 2 are synchronous request/response. Background continuation isn't free. We'll write a `running` Firestore doc at the START of `/run` so the dashboard can render it before the function returns.
- The frontend already reads runs directly from Firestore (no admin-auth required for those reads — security rules gate it). This means we don't need a new "list runs" endpoint; we just need the writes to happen earlier.
- Same auth model as today.

## Open questions (resolved here)

- **Preview persists or recomputed?** Recomputed every click. The preview shows the agent's CURRENT pick; if the user waits 30 min and comes back, the picks may have changed (new feedback, new history) and that's correct.
- **Confirm step required?** Yes — preview modal with explicit Run / Cancel. Otherwise we'd lose the value of the preview.
- **What if the user closes the modal mid-pick?** No state lost — the preview was just a cheap pre-pick. If they re-open it later, we re-pick.
- **What if scheduler-triggered runs render in the table?** Same way — the scheduler also goes through `/run`, so writing the `running` doc applies there too. The badge appears for scheduled runs too, which is the correct behavior.

## Test plan

- Unit (backend): `_handle_run_preview` returns picked scenarios without writing anything to Firestore or running anything; `_handle_run` writes a `running` doc before scenarios start and updates to `complete` after.
- Frontend: RunNowPanel renders preview modal on click; submits to `/run` only after confirm. RunsTable shows `Running` badge for `status === "running"` rows. Detail page renders picked scenarios as `pending` until they complete.
- Integration: trigger a run, observe Firestore — see the `running` doc within ~1 sec; see it flip to `complete` 2-3 min later.
