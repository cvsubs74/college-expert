# PRD: Schedule editor → Cloud Scheduler cron sync

Status: Proposed
Owner: Engineering
Last updated: 2026-05-05

## Problem

The QA agent's admin dashboard at `stratiaadmissions.com/qa-runs?tab=steer` exposes a "Run schedule" editor. When the operator picks "Every N minutes" and clicks Save, the `/schedule` POST handler writes the new shape to `qa_config/schedule` in Firestore. The UI flashes a success state and a footer line that reads "Cloud Scheduler fires the agent every N min. Changes take effect on the next poll."

That second sentence is a lie. The actual cadence is governed by a Cloud Scheduler job (`qa-agent-hourly-poll` in `us-east1`) whose cron lives in Cloud Scheduler's own state, not in Firestore. Saving in the UI does not touch that cron. The agent reads its Firestore schedule on every poll, but if the poll never fires at the user's chosen cadence, the saved schedule is dead text.

Concrete impact observed 2026-05-05: an operator set "every 15 min" in the UI and saved (UI showed success, `qa_config/schedule.interval_minutes = 15`). Runs continued every 30 minutes. The Cloud Scheduler job's cron was still `*/30 * * * *`. Hot-fix: a one-line gcloud `scheduler jobs update http qa-agent-hourly-poll --schedule="*/15 * * * *"` brought reality into line with the UI. The same gap recurs every time anyone edits the schedule until the underlying bug is fixed.

The auto-deploy work in PR #93 means cloud-function changes now reach prod within minutes of merge. That makes this gap more painful, not less: we ship dashboard improvements quickly and operators trust them, then discover hours later that the dashboard's promise is hollow.

## Goals

- **Single source of truth.** Saving in the UI updates Cloud Scheduler in the same request that writes Firestore. No follow-up gcloud command.
- **Loud failure.** If the Cloud Scheduler API call fails, the `/schedule` POST returns an error. Firestore stays updated (the operator's intent is captured), but the UI surfaces "schedule saved but scheduler sync failed: …" so nobody assumes the new cadence is live.
- **Bounded blast radius.** This work touches only `qa_config/schedule` semantics and the `qa-agent-hourly-poll` Cloud Scheduler job. No changes to the agent's polling logic, no changes to `should_run_now`, no changes to how scheduled runs execute.
- **Backward compatibility for time-based modes.** `frequency=daily/twice_daily/weekly` continues to use the agent's `should_run_now` filter — Cloud Scheduler keeps polling at a high cadence (`*/15`) and the agent decides whether each poll is in-window. Only `frequency=interval` and `frequency=off` materially change the cron itself.

## Non-goals

- **Replacing Cloud Scheduler.** Out of scope. Cloud Scheduler is fine; the bug is the missing glue.
- **Per-time-of-day cron derivation for daily/weekly modes.** Theoretically `frequency=daily, times=["06:00"]` could become cron `0 6 * * *` (single fire) instead of `*/15` + agent filter (96 polls, 95 no-ops). Out of scope here — the agent's no-op path already exists and works; optimising poll volume is a separate cleanup.
- **A new IAM model.** Out of scope. We grant `roles/cloudscheduler.admin` on the existing `qa-agent` runtime SA. A future PR can scope it to the single-job resource if security wants tighter blast radius.
- **UI changes beyond an error-state pass-through.** The schedule editor already surfaces save errors; we just route the new failure mode through the same path.

## Users

- **Dashboard operators (today: cvsubs@gmail.com).** The person clicking Save in the schedule editor.
- **The QA agent itself.** Reads `qa_config/schedule` on every poll; gets pinged at the cadence it was promised, not at whatever stale cadence the cron carries.

## User stories

1. *As an operator changing the run cadence*, when I save "every 5 minutes" the agent starts running every 5 minutes within one cron tick (≤5 minutes after save). I do not have to also remember a gcloud command.
2. *As an operator saving an "off" schedule for the weekend*, the Cloud Scheduler job is paused. No invocations fire until I switch back to a non-off mode, at which point the job resumes.
3. *As an operator who saves and then sees a sync error*, the UI tells me exactly which call failed and what to do. I can re-save (the Firestore write is idempotent and the next attempt will retry the scheduler call).
4. *As an engineer deploying a new qa-agent revision*, the schedule sync logic is unit-tested and doesn't require a live GCP call to validate. The IAM grant for the runtime SA is documented in one place.

## Success metrics

- **Save-to-effect lag**: median time from "operator clicks Save with a new interval" to "agent fires at the new cadence" drops from "open until someone runs gcloud" to under one cron tick (≤5 min for interval mode).
- **Hot-fixes**: zero post-this-PR incidents where Cloud Scheduler cron and `qa_config/schedule.interval_minutes` disagree.
- **Test coverage**: every supported `frequency` value has at least one cron-derivation test plus one happy-path sync test. The full backend suite stays green.
- **Operator trust**: after this lands, the dashboard footer "Cloud Scheduler fires the agent every N min" is true by construction.

## Open questions

- **What happens if `roles/cloudscheduler.admin` isn't yet granted on the runtime SA when the first post-merge save happens?** Design doc resolves this: the PR description includes the one-time `gcloud projects add-iam-policy-binding` command. Until that runs, every save returns a sync-error to the UI (and the Firestore write still happens), so operators get loud feedback rather than silent staleness.
- **Should the cron for time-based modes follow the times-of-day exactly?** Tabled as a non-goal for this PR. The agent's `should_run_now` already filters; the only cost of staying with `*/15` is wasted no-op invocations, which are free. Revisit if invocation volume ever shows up on a bill.
- **What if the Cloud Scheduler job goes missing (someone deletes it)?** The sync call returns NOT_FOUND; the operator gets an error and can re-create the job from `docs/qa-agent-setup.md`. Auto-recreation is out of scope — the job's full configuration (HTTP target, headers, retry policy) is non-trivial and shouldn't live in `schedule.py`.
