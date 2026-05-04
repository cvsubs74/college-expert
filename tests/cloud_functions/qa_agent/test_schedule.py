"""
Tests for schedule.py — the user-configurable run cadence stored at
qa_config/schedule. Written before implementation per the workflow rule.

The hourly Cloud Scheduler poll calls qa-agent /run with
trigger=schedule_check; the agent calls schedule.should_run_now() to
decide whether to actually execute or no-op for this hour.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


# ---- load_schedule + defaults ---------------------------------------------


class TestLoadSchedule:
    def test_returns_defaults_when_no_doc(self):
        import schedule
        # Stub Firestore client returning a non-existent doc.
        class _Snap:
            exists = False
            def to_dict(self):
                return None

        class _Doc:
            def get(self):
                return _Snap()

        class _Coll:
            def document(self, _id):
                return _Doc()

        class _DB:
            def collection(self, _name):
                return _Coll()

        result = schedule.load_schedule(db=_DB())
        # Defaults: daily at 06:00 PT, every weekday + weekend.
        assert result["frequency"] == "daily"
        assert "06:00" in result["times"]
        assert result["timezone"] == "America/Los_Angeles"

    def test_returns_stored_schedule(self):
        import schedule
        stored = {
            "frequency": "twice_daily",
            "times": ["08:00", "16:00"],
            "days": ["mon", "wed", "fri"],
            "timezone": "America/New_York",
        }
        class _Snap:
            exists = True
            def to_dict(self):
                return stored

        class _Doc:
            def get(self):
                return _Snap()

        class _Coll:
            def document(self, _id):
                return _Doc()

        class _DB:
            def collection(self, _name):
                return _Coll()

        result = schedule.load_schedule(db=_DB())
        assert result["frequency"] == "twice_daily"
        assert result["times"] == ["08:00", "16:00"]
        assert "mon" in result["days"]


# ---- should_run_now -------------------------------------------------------


class TestShouldRunNow:
    def _sched(self, **overrides):
        base = {
            "frequency": "daily",
            "times": ["06:00"],
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "timezone": "America/Los_Angeles",
        }
        base.update(overrides)
        return base

    def test_off_never_runs(self):
        import schedule
        s = self._sched(frequency="off")
        # 06:00 PT on a Monday — would be a hit if frequency wasn't off.
        now = datetime(2026, 5, 4, 13, 0, 0, tzinfo=timezone.utc)  # 06:00 PT
        assert schedule.should_run_now(s, now) is False

    def test_daily_matches_at_target_time(self):
        import schedule
        s = self._sched(times=["06:00"], timezone="America/Los_Angeles")
        # 06:02 PT = 13:02 UTC on Monday May 4 2026
        now = datetime(2026, 5, 4, 13, 2, 0, tzinfo=timezone.utc)
        assert schedule.should_run_now(s, now) is True

    def test_daily_misses_outside_window(self):
        import schedule
        s = self._sched(times=["06:00"], timezone="America/Los_Angeles")
        # 07:00 PT = 14:00 UTC — well outside the ±5min window
        now = datetime(2026, 5, 4, 14, 0, 0, tzinfo=timezone.utc)
        assert schedule.should_run_now(s, now) is False

    def test_5min_window_lower_edge(self):
        import schedule
        s = self._sched(times=["06:00"], timezone="America/Los_Angeles")
        # 05:54 PT — outside the ±5 min window centered on 06:00 PT
        # 05:54 PT = 12:54 UTC (PDT in May = UTC-7)
        now = datetime(2026, 5, 4, 12, 54, 0, tzinfo=timezone.utc)
        assert schedule.should_run_now(s, now) is False
        # 05:56 PT (4 min before) — inside
        now = datetime(2026, 5, 4, 12, 56, 0, tzinfo=timezone.utc)
        assert schedule.should_run_now(s, now) is True

    def test_twice_daily_both_times_match(self):
        import schedule
        s = self._sched(
            frequency="twice_daily",
            times=["06:00", "13:00"],
            timezone="America/Los_Angeles",
        )
        # Morning slot
        morning = datetime(2026, 5, 4, 13, 0, 0, tzinfo=timezone.utc)  # 06:00 PT
        # Afternoon slot
        afternoon = datetime(2026, 5, 4, 20, 0, 0, tzinfo=timezone.utc)  # 13:00 PT
        # In between — should miss
        between = datetime(2026, 5, 4, 16, 30, 0, tzinfo=timezone.utc)  # 09:30 PT

        assert schedule.should_run_now(s, morning) is True
        assert schedule.should_run_now(s, afternoon) is True
        assert schedule.should_run_now(s, between) is False

    def test_weekly_only_on_listed_days(self):
        import schedule
        s = self._sched(
            frequency="weekly",
            times=["06:00"],
            days=["mon", "wed", "fri"],
            timezone="America/Los_Angeles",
        )
        # 06:00 PT on Monday — match
        monday = datetime(2026, 5, 4, 13, 0, 0, tzinfo=timezone.utc)
        # 06:00 PT on Tuesday — miss (not in listed days)
        tuesday = datetime(2026, 5, 5, 13, 0, 0, tzinfo=timezone.utc)
        # 06:00 PT on Wednesday — match
        wednesday = datetime(2026, 5, 6, 13, 0, 0, tzinfo=timezone.utc)

        assert schedule.should_run_now(s, monday) is True
        assert schedule.should_run_now(s, tuesday) is False
        assert schedule.should_run_now(s, wednesday) is True

    def test_dst_aware_timezone(self):
        import schedule
        # DST handled correctly by zoneinfo — 06:00 LA time is 13:00 UTC
        # in standard time and 13:00 UTC in daylight time too because LA
        # observes DST. Just verify the function uses the right local time.
        s = self._sched(times=["06:00"], timezone="America/Los_Angeles")
        # July is DST — 06:00 PT = 13:00 UTC
        july = datetime(2026, 7, 1, 13, 0, 0, tzinfo=timezone.utc)
        assert schedule.should_run_now(s, july) is True


# ---- save_schedule -------------------------------------------------------


class TestSaveSchedule:
    def test_writes_to_qa_config_doc(self):
        import schedule

        captured = {}

        class _Doc:
            def set(self, data, merge=False):
                captured["data"] = data
                captured["merge"] = merge

        class _Coll:
            def document(self, _id):
                captured["doc_id"] = _id
                return _Doc()

        class _DB:
            def collection(self, name):
                captured["collection"] = name
                return _Coll()

        new_sched = {
            "frequency": "daily",
            "times": ["07:00"],
            "days": ["mon", "tue", "wed", "thu", "fri"],
            "timezone": "America/Los_Angeles",
        }
        schedule.save_schedule(new_sched, actor="admin@example.com", db=_DB())
        assert captured["collection"] == "qa_config"
        assert captured["doc_id"] == "schedule"
        # Saved doc should include the new fields + updated_at + updated_by.
        saved = captured["data"]
        assert saved["frequency"] == "daily"
        assert saved["times"] == ["07:00"]
        assert saved["updated_by"] == "admin@example.com"
        assert "updated_at" in saved
