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


# ---- interval frequency ----------------------------------------------------
#
# The "interval" frequency runs every N minutes. It bypasses the time-of-day
# and day-of-week match — Cloud Scheduler's cron is the gate, and qa-agent
# always runs when poked by an interval-mode poll.
#
# Why a separate frequency rather than a clever times[] list? Because
# Cloud Scheduler must also be set to fire every N minutes for the runs
# to actually happen — interval mode makes that contract explicit, and
# means we don't have to pre-populate 48 entries in `times` for every-30m.
# ---------------------------------------------------------------------------


class TestIntervalFrequency:
    def test_validate_accepts_interval_with_minutes(self):
        import schedule
        err = schedule.validate_schedule({
            "frequency": "interval",
            "interval_minutes": 30,
            "timezone": "America/Los_Angeles",
        })
        assert err is None

    def test_validate_rejects_interval_without_minutes(self):
        import schedule
        err = schedule.validate_schedule({
            "frequency": "interval",
            "timezone": "America/Los_Angeles",
        })
        assert err is not None
        assert "interval_minutes" in err

    @pytest.mark.parametrize("bad_value", [0, -1, 1441, "abc", None, 1.5])
    def test_validate_rejects_bad_interval_minutes(self, bad_value):
        import schedule
        err = schedule.validate_schedule({
            "frequency": "interval",
            "interval_minutes": bad_value,
            "timezone": "America/Los_Angeles",
        })
        assert err is not None

    def test_should_run_now_always_true_for_interval(self):
        import schedule
        sched = {
            "frequency": "interval",
            "interval_minutes": 30,
            "timezone": "UTC",
        }
        # Any time of day / any day of week should trigger.
        for hour in (0, 6, 13, 23):
            for minute in (0, 15, 30, 45):
                now = datetime(2026, 5, 15, hour, minute, tzinfo=timezone.utc)
                assert schedule.should_run_now(sched, now) is True, (
                    f"interval mode should always fire; got False at {hour}:{minute:02d}"
                )

    def test_load_returns_interval_schedule_intact(self):
        import schedule
        stored = {
            "frequency": "interval",
            "interval_minutes": 30,
            "timezone": "America/Los_Angeles",
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
        assert result["frequency"] == "interval"
        assert result["interval_minutes"] == 30

    def test_off_still_overrides_interval(self):
        """Frequency=off must short-circuit even if interval_minutes is set
        — defensive: a malformed save shouldn't keep firing."""
        import schedule
        sched = {
            "frequency": "off",
            "interval_minutes": 30,
            "timezone": "UTC",
        }
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        assert schedule.should_run_now(sched, now) is False


# ---- cron_for_schedule -----------------------------------------------------
#
# Pure mapping from a schedule dict to a Cloud Scheduler cron + paused flag.
# Spec: docs/prd/qa-agent-schedule-cron-sync.md +
#       docs/design/qa-agent-schedule-cron-sync.md.
#
# Frequency=off pauses the job (cron value irrelevant). Interval mode emits
# a precise cron when interval_minutes divides 60 cleanly (or 1440 for daily
# multiples); anything else rounds to the nearest divisor and logs a WARN.
# Time-based modes (daily/twice_daily/weekly) keep the high-frequency */15
# poll because the agent's should_run_now already filters by time-of-day.


class TestCronForSchedule:
    def test_off_returns_paused(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "off",
            "timezone": "America/Los_Angeles",
        })
        assert spec.paused is True

    def test_interval_15_emits_div15_cron(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "interval",
            "interval_minutes": 15,
            "timezone": "America/Los_Angeles",
        })
        assert spec.paused is False
        assert spec.cron == "*/15 * * * *"

    def test_interval_5_emits_div5_cron(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "interval",
            "interval_minutes": 5,
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "*/5 * * * *"
        assert spec.paused is False

    def test_interval_60_emits_top_of_hour_cron(self):
        """`*/60` is illegal in cron (max minute=59); use `0 * * * *`."""
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "interval",
            "interval_minutes": 60,
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "0 * * * *"
        assert spec.paused is False

    def test_interval_120_emits_every_2h_cron(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "interval",
            "interval_minutes": 120,
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "0 */2 * * *"
        assert spec.paused is False

    def test_interval_1440_emits_once_a_day_cron(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "interval",
            "interval_minutes": 1440,
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "0 0 * * *"
        assert spec.paused is False

    def test_interval_25_rounds_to_nearest_divisor(self, caplog):
        """25 doesn't divide 60; the closest divisors are 20 and 30.
        Either choice is acceptable; we want a WARN log so it's visible."""
        import schedule
        with caplog.at_level("WARNING"):
            spec = schedule.cron_for_schedule({
                "frequency": "interval",
                "interval_minutes": 25,
                "timezone": "America/Los_Angeles",
            })
        assert spec.paused is False
        # Must emit one of the valid divisor crons.
        assert spec.cron in ("*/20 * * * *", "*/30 * * * *")
        # And must have logged about the rounding.
        assert any(
            "interval_minutes" in record.message and "25" in record.message
            for record in caplog.records
        ), f"expected WARN about rounding, saw {[r.message for r in caplog.records]}"

    def test_interval_45_rounds_within_hour(self, caplog):
        import schedule
        with caplog.at_level("WARNING"):
            spec = schedule.cron_for_schedule({
                "frequency": "interval",
                "interval_minutes": 45,
                "timezone": "America/Los_Angeles",
            })
        # 45 → 30 or 60 (top-of-hour). Both are acceptable rounds.
        assert spec.cron in ("*/30 * * * *", "0 * * * *")
        assert spec.paused is False

    def test_daily_emits_15min_poll(self):
        """Time-based modes always emit the high-frequency poll cron;
        the agent's should_run_now does the time-of-day gate."""
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "daily",
            "times": ["06:00"],
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "*/15 * * * *"
        assert spec.paused is False

    def test_twice_daily_emits_15min_poll(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "twice_daily",
            "times": ["06:00", "13:00"],
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "*/15 * * * *"
        assert spec.paused is False

    def test_weekly_emits_15min_poll(self):
        import schedule
        spec = schedule.cron_for_schedule({
            "frequency": "weekly",
            "times": ["09:00"],
            "days": ["mon"],
            "timezone": "America/Los_Angeles",
        })
        assert spec.cron == "*/15 * * * *"
        assert spec.paused is False


# ---- sync_to_cloud_scheduler -----------------------------------------------
#
# Calls the Cloud Scheduler v1 API to update qa-agent-hourly-poll. Tests pass
# a stubbed client that records call args; no real GCP traffic.


class _FakeSchedulerClient:
    """Records call args for verification. Methods accept whatever
    google-cloud-scheduler accepts; we don't introspect, just record."""

    def __init__(self, *, fail_on=None):
        self.update_calls = []
        self.pause_calls = []
        self.resume_calls = []
        self._fail_on = fail_on  # method name to raise from

    def _maybe_fail(self, method):
        if self._fail_on == method:
            raise RuntimeError(f"simulated {method} failure")

    def update_job(self, *, job, update_mask):
        self._maybe_fail("update_job")
        self.update_calls.append({"job": job, "update_mask": update_mask})

    def pause_job(self, *, name):
        self._maybe_fail("pause_job")
        self.pause_calls.append({"name": name})

    def resume_job(self, *, name):
        self._maybe_fail("resume_job")
        self.resume_calls.append({"name": name})


_EXPECTED_JOB_NAME = (
    "projects/college-counselling-478115"
    "/locations/us-east1"
    "/jobs/qa-agent-hourly-poll"
)


class TestSyncToCloudScheduler:
    def test_off_calls_pause_only(self):
        import schedule
        client = _FakeSchedulerClient()
        schedule.sync_to_cloud_scheduler({
            "frequency": "off",
            "timezone": "America/Los_Angeles",
        }, client=client)
        assert len(client.pause_calls) == 1
        assert client.pause_calls[0]["name"] == _EXPECTED_JOB_NAME
        assert client.update_calls == []
        assert client.resume_calls == []

    def test_interval_15_calls_update_and_resume(self):
        import schedule
        client = _FakeSchedulerClient()
        schedule.sync_to_cloud_scheduler({
            "frequency": "interval",
            "interval_minutes": 15,
            "timezone": "America/Los_Angeles",
        }, client=client)
        assert len(client.update_calls) == 1
        upd = client.update_calls[0]
        # Job object can be the google-cloud-scheduler dataclass or a dict-
        # equivalent stub; we just need to see the schedule + name fields.
        job = upd["job"]
        # google-cloud-scheduler Job has .name, .schedule, .time_zone attrs;
        # the impl may build it via a constructor or dict — accept both.
        sched_str = getattr(job, "schedule", None) or job["schedule"]
        name_str = getattr(job, "name", None) or job["name"]
        tz_str = (
            getattr(job, "time_zone", None) or job["time_zone"]
        )
        assert sched_str == "*/15 * * * *"
        assert name_str == _EXPECTED_JOB_NAME
        assert tz_str == "UTC"

        # update_mask covers schedule + time_zone
        mask = upd["update_mask"]
        paths = mask["paths"] if isinstance(mask, dict) else list(mask.paths)
        assert set(paths) == {"schedule", "time_zone"}

        assert len(client.resume_calls) == 1
        assert client.resume_calls[0]["name"] == _EXPECTED_JOB_NAME
        assert client.pause_calls == []

    def test_daily_calls_update_with_15min_cron(self):
        import schedule
        client = _FakeSchedulerClient()
        schedule.sync_to_cloud_scheduler({
            "frequency": "daily",
            "times": ["06:00"],
            "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "timezone": "America/Los_Angeles",
        }, client=client)
        assert len(client.update_calls) == 1
        job = client.update_calls[0]["job"]
        sched_str = getattr(job, "schedule", None) or job["schedule"]
        assert sched_str == "*/15 * * * *"

    def test_propagates_client_error(self):
        """If the scheduler API raises, sync re-raises so the handler
        can convert to 200-with-success-False."""
        import schedule
        client = _FakeSchedulerClient(fail_on="update_job")
        with pytest.raises(RuntimeError, match="simulated update_job"):
            schedule.sync_to_cloud_scheduler({
                "frequency": "interval",
                "interval_minutes": 30,
                "timezone": "UTC",
            }, client=client)


# ---- _handle_post_schedule (handler glue) ----------------------------------


class TestPostScheduleHandler:
    """The handler in main.py orchestrates validate → save → sync. Test
    that all three are exercised, that the response shape includes the
    new schedule_saved/scheduler_synced flags, and that a sync failure
    does NOT roll back the Firestore write."""

    def _setup_main_with_stubs(self, *, save_raises=None, sync_raises=None):
        """Builds a callable that returns (response_dict, captured_state).
        Uses real main._handle_post_schedule but with schedule.* stubbed."""
        import main
        import schedule as sched_mod

        captured = {"saved": None, "synced_with": None}

        def _save(new_sched, *, actor="", db=None):
            if save_raises:
                raise save_raises
            captured["saved"] = {"sched": dict(new_sched), "actor": actor}

        def _sync(new_sched, *, client=None):
            if sync_raises:
                raise sync_raises
            captured["synced_with"] = dict(new_sched)

        # Monkey-patch on the main module so the test exercises the real
        # handler control flow but doesn't touch GCP.
        orig_save = sched_mod.save_schedule
        orig_sync = getattr(sched_mod, "sync_to_cloud_scheduler", None)
        sched_mod.save_schedule = _save
        sched_mod.sync_to_cloud_scheduler = _sync
        try:
            return main._handle_post_schedule, captured, orig_save, orig_sync
        finally:
            pass  # caller restores after asserting

    def _restore(self, orig_save, orig_sync):
        import schedule as sched_mod
        sched_mod.save_schedule = orig_save
        if orig_sync is not None:
            sched_mod.sync_to_cloud_scheduler = orig_sync
        else:
            try:
                del sched_mod.sync_to_cloud_scheduler
            except AttributeError:
                pass

    def test_post_calls_save_and_sync_on_happy_path(self):
        handler, captured, orig_save, orig_sync = self._setup_main_with_stubs()
        try:
            body = {
                "frequency": "interval",
                "interval_minutes": 15,
                "timezone": "America/Los_Angeles",
            }
            resp = handler(body, "admin@example.com")
            assert resp["success"] is True
            assert captured["saved"]["sched"]["interval_minutes"] == 15
            assert captured["synced_with"]["interval_minutes"] == 15
        finally:
            self._restore(orig_save, orig_sync)

    def test_post_returns_error_when_sync_fails_but_save_completes(self):
        sync_err = RuntimeError("scheduler down")
        handler, captured, orig_save, orig_sync = self._setup_main_with_stubs(
            sync_raises=sync_err,
        )
        try:
            body = {
                "frequency": "interval",
                "interval_minutes": 15,
                "timezone": "America/Los_Angeles",
            }
            resp = handler(body, "admin@example.com")
            assert resp["success"] is False
            assert resp.get("schedule_saved") is True
            assert resp.get("scheduler_synced") is False
            assert "scheduler" in resp.get("error", "").lower() or \
                "sync" in resp.get("error", "").lower()
            # Firestore stub still saw the save call.
            assert captured["saved"] is not None
        finally:
            self._restore(orig_save, orig_sync)

    def test_post_does_not_sync_when_validation_fails(self):
        handler, captured, orig_save, orig_sync = self._setup_main_with_stubs()
        try:
            body = {
                "frequency": "interval",
                # missing interval_minutes — validation rejects.
                "timezone": "America/Los_Angeles",
            }
            resp = handler(body, "admin@example.com")
            assert resp["success"] is False
            assert captured["saved"] is None
            assert captured["synced_with"] is None
        finally:
            self._restore(orig_save, orig_sync)
