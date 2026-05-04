import React, { useEffect, useState } from 'react';
import { ChartBarIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, MinusIcon } from '@heroicons/react/24/outline';
import { getSummary, getDashboardPrefs, saveDashboardPrefs } from '../../services/qaAgent';

// Top-of-dashboard executive summary. Fetches qa-agent /summary and
// renders the LLM narrative + the recent-N pass rate (PRIMARY) +
// 7d/30d pass rates (secondary) + per-surface health.
//
// "Recent N" is a configurable window — admin picks how many of the
// most recent runs to summarize. The 30-day average lags too long
// after a fix lands, so the recent-N pill is the at-a-glance signal.

const RECENT_N_PRESETS = [5, 10, 20, 50, 100];

const TREND_ICON = {
    improving: ArrowTrendingUpIcon,
    degrading: ArrowTrendingDownIcon,
    steady: MinusIcon,
};

const SURFACE_COLOR = {
    green: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    yellow: 'bg-amber-100 text-amber-800 border-amber-200',
    red: 'bg-rose-100 text-rose-800 border-rose-200',
};

const fmtRate = (n) => (n == null ? '—' : `${n}%`);

const ExecutiveSummary = () => {
    const [loading, setLoading] = useState(true);
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState(null);
    const [recentN, setRecentN] = useState(20);

    // Load saved prefs first, then fetch summary with that N.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const prefsResp = await getDashboardPrefs();
                if (!cancelled && prefsResp?.success && prefsResp.prefs?.recent_n) {
                    setRecentN(prefsResp.prefs.recent_n);
                }
            } catch {
                // non-fatal — fall back to default 20
            }
        })();
        return () => { cancelled = true; };
    }, []);

    // Refetch the summary when recent_n changes.
    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getSummary({ recentN })
            .then((resp) => {
                if (cancelled) return;
                if (resp?.success && resp.summary) {
                    setSummary(resp.summary);
                } else {
                    setError(resp?.error || "couldn't load summary");
                }
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || "couldn't load summary");
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [recentN]);

    const handleNChange = async (newN) => {
        setRecentN(newN);
        // Persist so subsequent loads (and the backend default) use it.
        try {
            await saveDashboardPrefs({ recent_n: newN });
        } catch {
            // non-fatal — the local state still drives the displayed pill;
            // the user can change it again next session.
        }
    };

    if (loading) {
        return (
            <div className="bg-white border border-[#E0DED8] rounded-xl p-5 mb-4 text-sm text-[#8A8A8A]">
                Loading executive summary…
            </div>
        );
    }
    if (error) {
        return (
            <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 mb-4 text-sm text-rose-700">
                {error}
            </div>
        );
    }
    if (!summary) return null;

    const TrendIcon = TREND_ICON[summary.trend] || MinusIcon;
    const surfaces = summary.surfaces && typeof summary.surfaces === 'object'
        ? Object.entries(summary.surfaces)
        : [];

    return (
        <div className="bg-gradient-to-br from-emerald-50/70 to-white border border-emerald-200/70 rounded-xl p-5 mb-5">
            <div className="flex items-start gap-3">
                <ChartBarIcon className="h-5 w-5 text-emerald-700 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                    <h2 className="text-sm font-bold uppercase tracking-wider text-emerald-900 mb-2">
                        System health
                    </h2>
                    <p className="text-sm text-[#1A2E1F] leading-relaxed mb-3">
                        {summary.narrative}
                    </p>

                    {/* Pass-rate row — recent-N is primary, 7d/30d are secondary */}
                    <div className="flex flex-wrap items-end gap-x-5 gap-y-2 text-sm">
                        <div className="min-w-0">
                            <div className="flex items-baseline gap-2">
                                <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B]">
                                    Last
                                </span>
                                <select
                                    value={summary.recent_n ?? recentN}
                                    onChange={(e) => handleNChange(Number(e.target.value))}
                                    aria-label="Number of recent runs to summarize"
                                    className="text-[11px] border border-[#E0DED8] rounded px-1 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-[#1A4D2E]/40"
                                >
                                    {RECENT_N_PRESETS.map((n) => (
                                        <option key={n} value={n}>{n}</option>
                                    ))}
                                </select>
                                <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B]">
                                    runs
                                </span>
                            </div>
                            <div className="text-3xl font-bold text-[#1A4D2E]">
                                {fmtRate(summary.pass_rate_recent)}
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B]">
                                Last 7 days
                            </span>
                            <div className="text-lg font-semibold text-[#4A4A4A]">
                                {fmtRate(summary.pass_rate_7d)}
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B]">
                                Last 30 days
                            </span>
                            <div className="text-lg font-semibold text-[#4A4A4A]">
                                {fmtRate(summary.pass_rate_30d)}
                            </div>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-[#4A4A4A] mb-1">
                            <TrendIcon className="h-4 w-4" />
                            {summary.trend}
                        </div>
                    </div>

                    {/* Surface health badges */}
                    {surfaces.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                            <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B] font-semibold mr-1 self-center">
                                Surfaces:
                            </span>
                            {surfaces.map(([surface, slot]) => (
                                <span
                                    key={surface}
                                    className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border ${
                                        SURFACE_COLOR[slot?.status] || SURFACE_COLOR.green
                                    }`}
                                >
                                    <span className="font-mono">{surface}</span>
                                    <span className="opacity-70">
                                        {slot.fails || 0}/{slot.total || 0} fails
                                    </span>
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ExecutiveSummary;
