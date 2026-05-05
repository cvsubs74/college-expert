"""
User-configurable run schedule.

The dashboard's ScheduleEditor writes to qa_config/schedule. A Cloud
Scheduler job pings qa-agent /run with trigger=schedule_check; the
agent calls should_run_now() to decide whether to actually execute or
no-op for this poll.

Document shape (qa_config/schedule):
    {
      "frequency": "daily" | "twice_daily" | "weekly" | "interval" | "off",
      "times":     ["06:00", "13:00"],            # HH:MM strings, local TZ
      "days":      ["mon", "tue", ..., "sun"],
      "interval_minutes": 30,                      # required iff frequency=interval
      "timezone":  "America/Los_Angeles",
      "updated_at": <iso>,
      "updated_by": <email>
    }

The "interval" frequency runs every N minutes regardless of time-of-day
or day-of-week — Cloud Scheduler's cron is the gate, and qa-agent always
runs when poked by an interval-mode poll. For this to actually fire every
N minutes, Cloud Scheduler MUST be set to fire at that cadence
(e.g., `*/30 * * * *` for every-30-min); the agent itself doesn't poll.

Defaults (no doc): daily at 06:00 PT every day of the week.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover — Python <3.9 has backports.zoneinfo
    from backports.zoneinfo import ZoneInfo  # type: ignore

logger = logging.getLogger(__name__)

# Match window: ±5 minutes around each target time. The hourly Cloud
# Scheduler poll fires at the top of each hour, so a 5-min window
# accommodates jitter without missing or double-firing.
WINDOW_MINUTES = 5

# Recognized frequencies.
VALID_FREQUENCIES = {"daily", "twice_daily", "weekly", "interval", "off"}

# Bounds for interval mode: 1 minute to 24 hours (1440 min). Anything
# outside is almost certainly a typo (negative, zero, or so large that
# the user meant something else). Keep the upper bound below the daily
# breakpoint so users with that intent get steered to frequency=daily.
INTERVAL_MIN_MINUTES = 1
INTERVAL_MAX_MINUTES = 1440

# All-week default for daily/twice-daily. Weekly explicitly lists days.
ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

DEFAULT_SCHEDULE = {
    "frequency": "daily",
    "times": ["06:00"],
    "days": list(ALL_DAYS),
    "timezone": "America/Los_Angeles",
}


# ---- Firestore I/O ----------------------------------------------------------


def _client():
    from google.cloud import firestore
    return firestore.Client()


def load_schedule(db=None) -> dict:
    """Read qa_config/schedule. Returns DEFAULT_SCHEDULE if the doc
    doesn't exist or fields are missing."""
    db = db or _client()
    snap = db.collection("qa_config").document("schedule").get()
    stored = snap.to_dict() if snap.exists else None
    if not stored:
        return dict(DEFAULT_SCHEDULE)

    # Merge stored over defaults so a partial doc still works.
    merged = dict(DEFAULT_SCHEDULE)
    merged.update({k: v for k, v in stored.items() if v is not None})
    return merged


def save_schedule(new_schedule: dict, *, actor: str = "", db=None) -> None:
    """Write qa_config/schedule. Caller is responsible for validating
    the schedule shape before calling."""
    db = db or _client()
    payload = dict(new_schedule)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_by"] = actor
    db.collection("qa_config").document("schedule").set(payload, merge=False)


def validate_schedule(new_schedule: dict) -> Optional[str]:
    """Returns an error string if the shape is bad, None if OK."""
    freq = new_schedule.get("frequency")
    if freq not in VALID_FREQUENCIES:
        return f"frequency must be one of {sorted(VALID_FREQUENCIES)}"

    # Interval mode is structurally simpler — only interval_minutes and
    # timezone are required. We don't reject a stray times[]/days[] in
    # the payload (UI may send empties) but they're ignored by
    # should_run_now.
    if freq == "interval":
        raw = new_schedule.get("interval_minutes")
        # Reject bool because bool is a subclass of int but it's never
        # what the caller meant.
        if not isinstance(raw, int) or isinstance(raw, bool):
            return (
                f"interval_minutes must be an integer in "
                f"[{INTERVAL_MIN_MINUTES}, {INTERVAL_MAX_MINUTES}], got {raw!r}"
            )
        if not (INTERVAL_MIN_MINUTES <= raw <= INTERVAL_MAX_MINUTES):
            return (
                f"interval_minutes must be in "
                f"[{INTERVAL_MIN_MINUTES}, {INTERVAL_MAX_MINUTES}], got {raw}"
            )
    else:
        times = new_schedule.get("times") or []
        if not isinstance(times, list):
            return "times must be a list of HH:MM strings"
        for t in times:
            if not isinstance(t, str) or len(t) != 5 or t[2] != ":":
                return f"times entries must be HH:MM strings, got {t!r}"
            try:
                h, m = int(t[:2]), int(t[3:])
                if not (0 <= h < 24 and 0 <= m < 60):
                    return f"times entry out of range: {t!r}"
            except ValueError:
                return f"times entry not numeric: {t!r}"
        days = new_schedule.get("days") or []
        if not isinstance(days, list):
            return "days must be a list"
        for d in days:
            if d not in ALL_DAYS:
                return f"day must be one of {ALL_DAYS}, got {d!r}"

    tz = new_schedule.get("timezone")
    if not isinstance(tz, str) or not tz:
        return "timezone is required"
    try:
        ZoneInfo(tz)
    except Exception:  # noqa: BLE001
        return f"unknown timezone: {tz!r}"
    return None


# ---- should_run_now --------------------------------------------------------


def should_run_now(schedule: dict, now: datetime) -> bool:
    """Returns True iff `now` falls within ±WINDOW_MINUTES of any
    schedule time on a matching day in the schedule's timezone.

    Special case: frequency="interval" returns True unconditionally —
    Cloud Scheduler's cron is the gate, the agent always runs when
    poked in interval mode.
    """
    freq = schedule.get("frequency")
    if freq == "off":
        return False
    if freq == "interval":
        # Cloud Scheduler controls the cadence; we trust each ping.
        return True
    if not schedule.get("times"):
        return False

    tz = ZoneInfo(schedule.get("timezone") or "America/Los_Angeles")
    local = now.astimezone(tz)

    # Day-of-week match. ALL_DAYS index matches local.weekday() with mon=0.
    weekday_label = ALL_DAYS[local.weekday()]
    days = schedule.get("days") or []
    if days and weekday_label not in days:
        return False

    window = timedelta(minutes=WINDOW_MINUTES)
    for t in schedule["times"]:
        try:
            target_h, target_m = int(t[:2]), int(t[3:])
        except (ValueError, TypeError):
            continue
        target = local.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        if abs(local - target) <= window:
            return True
    return False


# ---- Cloud Scheduler cron sync ---------------------------------------------
#
# The schedule editor in the dashboard saves user intent to Firestore, but
# the actual cadence is governed by the Cloud Scheduler job
# `qa-agent-hourly-poll`. This pair of helpers translates a saved schedule
# into the cron string + paused-state the job should hold, and pushes that
# state to Cloud Scheduler. Without this glue, saving a new interval in the
# UI is a no-op until someone runs `gcloud scheduler jobs update http ...`.
#
# Spec: docs/prd/qa-agent-schedule-cron-sync.md
#       docs/design/qa-agent-schedule-cron-sync.md


# Hard-coded job path. Only one qa-agent monitor exists in this project,
# and putting the path in code (not env) keeps the IAM blast radius
# obvious — we know exactly which resource the function can touch.
SCHEDULER_JOB_NAME = (
    "projects/college-counselling-478115"
    "/locations/us-east1"
    "/jobs/qa-agent-hourly-poll"
)

# High-frequency poll cron used for time-based modes (daily/twice_daily/
# weekly) and as a placeholder when the job is paused. The agent's
# should_run_now does the actual time-of-day filtering for these modes,
# so the only cost of polling at this cadence is no-op invocations.
_DEFAULT_POLL_CRON = "*/15 * * * *"

# Interval values that map to a clean `*/N * * * *` cron (N divides 60).
_VALID_SUB_HOUR_DIVISORS = (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30)

# Multi-hour intervals that map to `0 */H * * *` (H divides 24).
_VALID_HOUR_DIVISORS = (1, 2, 3, 4, 6, 8, 12, 24)


@dataclass(frozen=True)
class CronSpec:
    """Resolved Cloud Scheduler state for a saved schedule.

    Always provide a cron string (Cloud Scheduler requires one even when
    the job is paused — pausing doesn't clear the schedule field).
    """
    cron: str
    paused: bool


def _round_to_nearest_divisor(n: int) -> int:
    """Round n minutes to the nearest cron-representable interval.

    Returns one of the values in _VALID_SUB_HOUR_DIVISORS (for n <= 60),
    or 60 * H for some H in _VALID_HOUR_DIVISORS (for n > 60), choosing
    whichever is closest to n. Ties go to the smaller value (more
    frequent polling — fail safer).
    """
    candidates: list[int] = list(_VALID_SUB_HOUR_DIVISORS)
    candidates.append(60)  # */60 → "0 * * * *"
    for h in _VALID_HOUR_DIVISORS[1:]:  # 2, 3, 4, 6, 8, 12, 24
        candidates.append(h * 60)
    # Pick min by (distance, value) so ties prefer smaller.
    return min(candidates, key=lambda c: (abs(c - n), c))


def cron_for_schedule(schedule_dict: dict) -> CronSpec:
    """Derive the Cloud Scheduler cron + paused flag for a saved schedule.

    See the design doc for the full mapping table. Off → paused. Interval
    with a clean divisor → exact cron. Interval with an awkward value
    (e.g. 25, 45) → nearest divisor with a WARN log. Time-based modes
    (daily/twice_daily/weekly) → `*/15 * * * *` and let the agent's
    should_run_now do the time-of-day gate.
    """
    freq = (schedule_dict or {}).get("frequency")

    if freq == "off":
        return CronSpec(cron=_DEFAULT_POLL_CRON, paused=True)

    if freq == "interval":
        raw = schedule_dict.get("interval_minutes")
        try:
            n = int(raw)
        except (TypeError, ValueError):
            logger.warning(
                "schedule.cron_for_schedule: non-int interval_minutes %r; "
                "defaulting to %s",
                raw, _DEFAULT_POLL_CRON,
            )
            return CronSpec(cron=_DEFAULT_POLL_CRON, paused=False)

        # Round invalid values to the nearest divisor; log loudly.
        original = n
        if n in _VALID_SUB_HOUR_DIVISORS:
            return CronSpec(cron=f"*/{n} * * * *", paused=False)
        if n == 60:
            return CronSpec(cron="0 * * * *", paused=False)
        # Multi-hour: must be a multiple of 60 AND the hour-count must
        # divide 24 (so the cron repeats cleanly day to day).
        if n % 60 == 0 and (n // 60) in _VALID_HOUR_DIVISORS:
            h = n // 60
            if h == 24:
                return CronSpec(cron="0 0 * * *", paused=False)
            return CronSpec(cron=f"0 */{h} * * *", paused=False)

        # Awkward value — round and warn.
        rounded = _round_to_nearest_divisor(n)
        logger.warning(
            "schedule.cron_for_schedule: interval_minutes=%s does not divide "
            "60 (or 60*H for valid H); rounding to %s minute(s)",
            original, rounded,
        )
        # Recursive call into a clean value — guaranteed to hit one of
        # the precise branches above.
        return cron_for_schedule({
            "frequency": "interval",
            "interval_minutes": rounded,
        })

    # Time-based modes: high-frequency poll, agent filters.
    return CronSpec(cron=_DEFAULT_POLL_CRON, paused=False)


def _scheduler_client():
    """Lazy import + construct the Cloud Scheduler client. Kept lazy so
    the import cost only hits requests that actually save a schedule;
    every other qa-agent endpoint is unaffected."""
    from google.cloud import scheduler_v1  # noqa: WPS433
    return scheduler_v1.CloudSchedulerClient()


def sync_to_cloud_scheduler(
    schedule_dict: dict,
    *,
    client: Any = None,
) -> None:
    """Push the resolved cron + paused state to the Cloud Scheduler job.

    Off → pause_job. Otherwise update_job with the new schedule + UTC
    time_zone, then resume_job (idempotent if already running).

    Errors propagate; callers convert them into a `success: False`
    response with `scheduler_synced: False`.
    """
    spec = cron_for_schedule(schedule_dict)
    cli = client or _scheduler_client()

    if spec.paused:
        cli.pause_job(name=SCHEDULER_JOB_NAME)
        return

    # Lazy import for the Job dataclass; tests pass a stub that doesn't
    # need the real lib so the import lives inside the non-paused branch.
    try:
        from google.cloud import scheduler_v1  # noqa: WPS433
        Job = scheduler_v1.Job
    except ImportError:
        # Test path: callers can pass a stub client and skip the import.
        Job = dict  # type: ignore[misc,assignment]

    if Job is dict:
        job = {
            "name": SCHEDULER_JOB_NAME,
            "schedule": spec.cron,
            "time_zone": "UTC",
        }
    else:
        job = Job(
            name=SCHEDULER_JOB_NAME,
            schedule=spec.cron,
            time_zone="UTC",
        )

    cli.update_job(job=job, update_mask={"paths": ["schedule", "time_zone"]})
    cli.resume_job(name=SCHEDULER_JOB_NAME)
