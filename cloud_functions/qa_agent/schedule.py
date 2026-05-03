"""
User-configurable run schedule.

The dashboard's ScheduleEditor writes to qa_config/schedule. An hourly
Cloud Scheduler job pings qa-agent /run with trigger=schedule_check;
the agent calls should_run_now() to decide whether to actually execute
or no-op for this hour.

Document shape (qa_config/schedule):
    {
      "frequency": "daily" | "twice_daily" | "weekly" | "off",
      "times":     ["06:00", "13:00"],            # HH:MM strings, local TZ
      "days":      ["mon", "tue", ..., "sun"],
      "timezone":  "America/Los_Angeles",
      "updated_at": <iso>,
      "updated_by": <email>
    }

Defaults (no doc): daily at 06:00 PT every day of the week.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

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
VALID_FREQUENCIES = {"daily", "twice_daily", "weekly", "off"}

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
    schedule time on a matching day in the schedule's timezone."""
    if schedule.get("frequency") == "off":
        return False
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
