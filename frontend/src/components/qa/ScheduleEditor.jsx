import React, { useEffect, useState } from 'react';
import { ClockIcon } from '@heroicons/react/24/outline';
import { getSchedule, saveSchedule } from '../../services/qaAgent';

// User-configurable schedule for the hourly Cloud Scheduler poll.
// Reads/writes qa-agent's GET/POST /schedule. Schedule changes take
// effect within ~1 hour (next hourly poll).

const ALL_DAYS = [
    { id: 'mon', label: 'M' },
    { id: 'tue', label: 'T' },
    { id: 'wed', label: 'W' },
    { id: 'thu', label: 'T' },
    { id: 'fri', label: 'F' },
    { id: 'sat', label: 'S' },
    { id: 'sun', label: 'S' },
];

const TIMEZONE_PRESETS = [
    'America/Los_Angeles',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'UTC',
    'Asia/Kolkata',
    'Europe/London',
];

const FREQUENCIES = [
    { id: 'daily', label: 'Daily' },
    { id: 'twice_daily', label: 'Twice daily' },
    { id: 'weekly', label: 'Weekly' },
    { id: 'off', label: 'Off' },
];

const ScheduleEditor = () => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);
    const [updatedAt, setUpdatedAt] = useState(null);
    const [updatedBy, setUpdatedBy] = useState(null);

    const [frequency, setFrequency] = useState('daily');
    const [times, setTimes] = useState(['06:00']);
    const [days, setDays] = useState(ALL_DAYS.map((d) => d.id));
    const [timezone, setTimezone] = useState('America/Los_Angeles');

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getSchedule()
            .then((resp) => {
                if (cancelled) return;
                if (resp?.success && resp.schedule) {
                    const s = resp.schedule;
                    setFrequency(s.frequency || 'daily');
                    setTimes(Array.isArray(s.times) && s.times.length ? s.times : ['06:00']);
                    setDays(Array.isArray(s.days) && s.days.length ? s.days : ALL_DAYS.map((d) => d.id));
                    setTimezone(s.timezone || 'America/Los_Angeles');
                    setUpdatedAt(s.updated_at || null);
                    setUpdatedBy(s.updated_by || null);
                } else {
                    setError(resp?.error || "couldn't load schedule");
                }
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || "couldn't load schedule");
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, []);

    // Adjust times array length when frequency changes.
    useEffect(() => {
        if (frequency === 'twice_daily' && times.length === 1) {
            setTimes([times[0], '13:00']);
        } else if (frequency !== 'twice_daily' && times.length > 1) {
            setTimes([times[0]]);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [frequency]);

    const toggleDay = (day) => {
        setDays((prev) =>
            prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
        );
    };

    const handleSave = async (e) => {
        e?.preventDefault?.();
        setSaving(true);
        setError(null);
        setSaved(false);
        try {
            const payload = { frequency, times, days, timezone };
            await saveSchedule(payload);
            setSaved(true);
            // Brief success indicator; clear after a few seconds.
            setTimeout(() => setSaved(false), 3000);
        } catch (err) {
            setError(err.message || "couldn't save schedule");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="bg-white border border-[#E0DED8] rounded-xl p-5 mb-4 text-sm text-[#8A8A8A]">
                Loading schedule…
            </div>
        );
    }

    return (
        <form
            onSubmit={handleSave}
            className="bg-white border border-[#E0DED8] rounded-xl p-5 mb-4"
        >
            <div className="flex items-baseline justify-between mb-3 flex-wrap gap-2">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E] flex items-center gap-2">
                    <ClockIcon className="h-4 w-4" />
                    Run schedule
                </h2>
                {updatedAt && (
                    <span className="text-[10px] text-[#8A8A8A]">
                        Last edit: {new Date(updatedAt).toLocaleString()}{updatedBy ? ` by ${updatedBy}` : ''}
                    </span>
                )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Frequency */}
                <label className="text-xs">
                    <span className="block text-[10px] uppercase tracking-wider text-[#6B6B6B] mb-1">
                        Frequency
                    </span>
                    <select
                        className="w-full border border-[#E0DED8] rounded-lg px-3 py-2 text-sm bg-[#FBFAF6] focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30"
                        value={frequency}
                        onChange={(e) => setFrequency(e.target.value)}
                    >
                        {FREQUENCIES.map((f) => (
                            <option key={f.id} value={f.id}>{f.label}</option>
                        ))}
                    </select>
                </label>

                {/* Times */}
                <label className="text-xs">
                    <span className="block text-[10px] uppercase tracking-wider text-[#6B6B6B] mb-1">
                        Time(s)
                    </span>
                    <div className="flex gap-2">
                        {times.map((t, i) => (
                            <input
                                key={i}
                                type="time"
                                value={t}
                                onChange={(e) => {
                                    const next = [...times];
                                    next[i] = e.target.value;
                                    setTimes(next);
                                }}
                                disabled={frequency === 'off'}
                                className="flex-1 border border-[#E0DED8] rounded-lg px-3 py-2 text-sm bg-[#FBFAF6] focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30 disabled:opacity-50"
                            />
                        ))}
                    </div>
                </label>

                {/* Timezone */}
                <label className="text-xs">
                    <span className="block text-[10px] uppercase tracking-wider text-[#6B6B6B] mb-1">
                        Timezone
                    </span>
                    <select
                        className="w-full border border-[#E0DED8] rounded-lg px-3 py-2 text-sm bg-[#FBFAF6] focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30"
                        value={timezone}
                        onChange={(e) => setTimezone(e.target.value)}
                    >
                        {TIMEZONE_PRESETS.map((tz) => (
                            <option key={tz} value={tz}>{tz}</option>
                        ))}
                    </select>
                </label>
            </div>

            {/* Days of week (only shown for weekly) */}
            <div className="mt-3">
                <span className="block text-[10px] uppercase tracking-wider text-[#6B6B6B] mb-1">
                    Days {frequency !== 'weekly' && <span className="opacity-50">(applies to weekly)</span>}
                </span>
                <div className="flex gap-1.5">
                    {ALL_DAYS.map((d) => (
                        <button
                            key={d.id}
                            type="button"
                            onClick={() => toggleDay(d.id)}
                            disabled={frequency !== 'weekly' && frequency !== 'off'}
                            className={`w-8 h-8 text-xs font-semibold rounded-full border transition-all ${
                                days.includes(d.id)
                                    ? 'bg-[#1A4D2E] text-white border-transparent'
                                    : 'bg-white text-[#6B6B6B] border-[#E0DED8] hover:border-[#1A4D2E]'
                            } ${frequency !== 'weekly' && frequency !== 'off' ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {d.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mt-4 flex items-center gap-3">
                <button
                    type="submit"
                    disabled={saving}
                    className="px-5 py-2 bg-[#1A4D2E] text-white text-sm font-semibold rounded-full hover:bg-[#2D6B45] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                    {saving ? 'Saving…' : 'Save schedule'}
                </button>
                {saved && (
                    <span className="text-sm text-emerald-700">✓ Saved. Takes effect within ~1 hour.</span>
                )}
                {error && (
                    <span className="text-sm text-rose-700">{error}</span>
                )}
            </div>

            <p className="mt-3 text-[11px] text-[#8A8A8A] italic">
                The hourly poll fires at the top of each hour. Changes take effect within 1 hour.
            </p>
        </form>
    );
};

export default ScheduleEditor;
