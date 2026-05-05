# Design: Schedule editor → Cloud Scheduler cron sync

Status: Proposed
Last updated: 2026-05-05
Related PRD: [docs/prd/qa-agent-schedule-cron-sync.md](../prd/qa-agent-schedule-cron-sync.md)

## Architecture

The change is concentrated in `cloud_functions/qa_agent/`:

```
POST /schedule (admin)
  ├─ schedule.validate_schedule(body)        ← unchanged
  ├─ schedule.save_schedule(body, actor=…)   ← unchanged (writes Firestore)
  └─ schedule.sync_to_cloud_scheduler(body)  ← NEW: pushes cron to GCP
```

`sync_to_cloud_scheduler` derives the right cron + paused-state for the input schedule and calls the Cloud Scheduler v1 API to update the existing `qa-agent-hourly-poll` job. It does not create or delete jobs.

If the Cloud Scheduler call fails, `_handle_post_schedule` returns `{success: False, error: …, schedule_saved: True, scheduler_synced: False}` — the Firestore write stands but the operator sees a clear "saved, but not yet active" signal.

## Cron derivation

`schedule.cron_for_schedule(schedule_dict) -> CronSpec` is a pure function. `CronSpec` is a `dataclass` with:

```python
@dataclass(frozen=True)
class CronSpec:
    cron: str          # cron string, e.g. "*/15 * * * *"
    paused: bool       # True iff frequency=="off" (job should be paused)
```

Mapping by frequency:

| Frequency | Output cron | Paused |
|---|---|---|
| `off` | `*/15 * * * *` (placeholder, never fires while paused) | `True` |
| `interval`, `interval_minutes ∈ {1,2,3,4,5,6,10,12,15,20,30}` | `*/N * * * *` | `False` |
| `interval`, `interval_minutes == 60` | `0 * * * *` | `False` |
| `interval`, `interval_minutes ∈ {120,180,240,360,720}` (multiple of 60, divides 24·60) | `0 */(N/60) * * *` | `False` |
| `interval`, `interval_minutes == 1440` | `0 0 * * *` | `False` |
| `interval`, anything else (e.g. 7, 25, 45) | nearest valid value, with a `logger.warning` | `False` |
| `daily`, `twice_daily`, `weekly` | `*/15 * * * *` | `False` |

Time-based modes (`daily`/`twice_daily`/`weekly`) keep the high-frequency `*/15` poll because the agent's `should_run_now` already filters by time-of-day and timezone. Folding times-of-day into the cron itself is a non-goal (PRD §Non-goals): the only cost of `*/15` is no-op invocations, which are free.

Why a frozen dataclass instead of a tuple? It self-documents the field meanings at every call site and lets pytest assert equality cleanly without positional ordering.

### Why round invalid intervals instead of erroring?

`validate_schedule` already accepts any `interval_minutes` in `[1, 1440]`. Tightening that range now would reject schedules that work today (the agent runs every poll in interval mode, so non-divisor values aren't broken — just imprecise). Rounding + a warning preserves the existing contract while making the cron behavior visible.

`cron_for_schedule(interval_minutes=25)` rounds to the nearest divisor of 60 (in this case 30) and emits `*/30 * * * *`. The mismatch is logged at WARN level so a human reading the function logs sees what happened. The UI can show the same warning as a follow-up PR.

## Cloud Scheduler integration

`sync_to_cloud_scheduler(schedule_dict)` lives in `schedule.py`. It uses the official Google client library `google-cloud-scheduler`:

```python
from google.cloud import scheduler_v1

JOB_PATH = (
    "projects/college-counselling-478115"
    "/locations/us-east1"
    "/jobs/qa-agent-hourly-poll"
)

def sync_to_cloud_scheduler(schedule_dict, *, client=None) -> None:
    client = client or scheduler_v1.CloudSchedulerClient()
    spec = cron_for_schedule(schedule_dict)
    if spec.paused:
        client.pause_job(name=JOB_PATH)
        return
    job = scheduler_v1.Job(
        name=JOB_PATH,
        schedule=spec.cron,
        time_zone="UTC",
    )
    update_mask = {"paths": ["schedule", "time_zone"]}
    client.update_job(job=job, update_mask=update_mask)
    client.resume_job(name=JOB_PATH)
```

A few choices worth calling out:

- **Job name is hard-coded.** The job lives at a fixed path; only one qa-agent monitor runs in this project. Putting the path in code (not env) makes the IAM blast radius obvious — we know exactly which resource the function can touch.
- **`time_zone="UTC"`.** Cron runs in UTC; the agent's `should_run_now` does timezone conversion in Python. Keeping the cron in UTC removes a confounding variable. Operators see a UTC cron in the gcloud console; the dashboard shows local-time targets.
- **`pause_job` for `off`, `resume_job` always when not-off.** Two API calls in the resume case (update + resume), but `resume_job` on an already-RUNNING job is a no-op. Net effect: idempotent. Going from `off` → not-off goes through update + resume; not-off → `off` is a single pause.
- **`client` parameter for tests.** Unit tests pass a stubbed client (no GCP auth needed) and assert on the call args. Same plumbing pattern as `save_schedule`'s `db=` parameter.

### Failure semantics

Three failure modes inside `_handle_post_schedule`:

1. **Validation fails** → return `{success: False, error: …}`, no Firestore write, no scheduler call. (Existing behaviour.)
2. **Firestore save fails** → return `{success: False, error: …, scheduler_synced: False}`. Existing behaviour, plus the new explicit `scheduler_synced` field for UI clarity.
3. **Scheduler sync fails** (NEW) → return `{success: False, error: f"saved to Firestore but Cloud Scheduler update failed: {exc}", schedule_saved: True, scheduler_synced: False}`. Firestore write is NOT rolled back (operator's intent is durably captured). The next save attempt re-syncs.

The `success: False` keeps the UI's existing error path lit up — no new UI work needed beyond the operator now seeing a longer message. The `schedule_saved` / `scheduler_synced` booleans are an extra signal a future UI pass could surface ("schedule was saved but the cron didn't update — retry?").

## IAM

The qa-agent runtime SA (`qa-agent@college-counselling-478115.iam.gserviceaccount.com`) currently has roles for Firestore, Secret Manager, IAM service account user, and similar function-runtime essentials. It does NOT have any Cloud Scheduler roles.

This PR's one-time grant, documented in the PR description for the operator to run after merge:

```bash
gcloud projects add-iam-policy-binding college-counselling-478115 \
    --member=serviceAccount:qa-agent@college-counselling-478115.iam.gserviceaccount.com \
    --role=roles/cloudscheduler.admin \
    --account=cvsubs@gmail.com \
    --project=college-counselling-478115
```

`roles/cloudscheduler.admin` is broader than the minimum (`update`, `pause`, `resume`). A future hardening PR can scope to a custom role or a per-job binding once we're past v1 — the project has a single Cloud Scheduler job, so blast radius is already bounded.

Until the grant is in place, the first post-merge save returns the new `scheduler_synced: False` error — loud, not silent.

## Dependency

Add to `cloud_functions/qa_agent/requirements.txt`:

```
google-cloud-scheduler>=2.14.0
```

The library is small (~200 KB) and shares transitive deps with `google-cloud-firestore` already in use, so the cold-start cost increase is negligible.

## Test plan

`tests/cloud_functions/qa_agent/test_schedule.py` — extends the existing file with two new test classes (plus a small change to the existing handler test class).

### `class TestCronForSchedule`

Pure-function tests, no mocks, no GCP:

| Frequency | Input | Expected `(cron, paused)` |
|---|---|---|
| off | `{"frequency":"off",…}` | `("*/15 * * * *", True)` |
| interval (clean) | `interval_minutes=15` | `("*/15 * * * *", False)` |
| interval (clean) | `interval_minutes=5` | `("*/5 * * * *", False)` |
| interval (60) | `interval_minutes=60` | `("0 * * * *", False)` |
| interval (hour-multiple) | `interval_minutes=120` | `("0 */2 * * *", False)` |
| interval (daily) | `interval_minutes=1440` | `("0 0 * * *", False)` |
| interval (rounded) | `interval_minutes=25` | `("*/30 * * * *", False)` + log captures the warning |
| interval (rounded) | `interval_minutes=45` | nearest valid value (e.g. 30 or 60); test asserts the cadence is one of `{*/30, 0 *}` |
| daily | `frequency="daily"` | `("*/15 * * * *", False)` |
| twice_daily | `frequency="twice_daily"` | `("*/15 * * * *", False)` |
| weekly | `frequency="weekly"` | `("*/15 * * * *", False)` |

### `class TestSyncToCloudScheduler`

Stubbed `CloudSchedulerClient`. The test passes a fake whose methods record calls.

- `test_off_calls_pause_only` — frequency=off → `pause_job` called once with the right job name; `update_job`/`resume_job` not called.
- `test_interval_15_calls_update_and_resume` — verifies `update_job` was called with `Job(name=…, schedule="*/15 * * * *", time_zone="UTC")` and update_mask covering `schedule` + `time_zone`; `resume_job` called after.
- `test_daily_calls_update_with_15min_cron` — same as above but with `*/15` regardless of times-of-day in the schedule.
- `test_propagates_client_error` — fake raises `GoogleAPIError`; sync re-raises so `_handle_post_schedule` can convert it to a 200-with-`success:False`.

### `class TestPostScheduleHandler`

Updates the existing handler tests:

- `test_post_calls_sync_after_save` — happy path; both Firestore and scheduler stubs see the new schedule.
- `test_post_returns_error_when_sync_fails` — sync stub raises; response has `success: False`, `schedule_saved: True`, `scheduler_synced: False`, and the original Firestore write is preserved (assert via the stub's saved doc).
- `test_post_does_not_sync_when_validation_fails` — neither save nor sync runs.

Coverage target: every code path through `cron_for_schedule` (11 cases above) + every error path through `sync_to_cloud_scheduler` (4 cases) + every error path through `_handle_post_schedule` (3 cases).

## Smoke verification

Once the PR merges and the IAM grant is in place:

1. Save "Every N minutes" with `N=20` in the dashboard.
2. `gcloud scheduler jobs describe qa-agent-hourly-poll --location=us-east1` → cron should read `*/20 * * * *`.
3. Save "Off".
4. Same describe → `state: PAUSED`.
5. Save "Daily at 06:00 PT".
6. Same describe → `*/15 * * * *`, `state: ENABLED`.

If any of these fail, check the qa-agent function logs for the `sync_to_cloud_scheduler` failure message; the IAM binding is the most likely culprit.

## Risks

- **IAM grant lag**: if the operator merges the PR but forgets the IAM command, every save returns `scheduler_synced: False` until the binding lands. The PR description calls this out prominently.
- **Cron rounding surprises**: an operator who picks 25 min may not expect to land on 30. The function logs a WARN and the UI can surface it later. Out of scope for v1.
- **Concurrent saves**: two operators saving at the same instant could race on the scheduler API. Cloud Scheduler's `update_job` is last-writer-wins; the operator who clicks Save second sees their cron win. Acceptable — there's only one human admin today.
- **Pause/resume not atomic with Firestore write**: in theory a save could write Firestore and crash before the scheduler call. The current behaviour (no scheduler call at all) is strictly worse; the new behaviour at least surfaces the inconsistency to the operator.
