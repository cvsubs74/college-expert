import React, { useEffect, useState } from 'react';
import { ChartBarIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon, MinusIcon } from '@heroicons/react/24/outline';
import { getSummary } from '../../services/qaAgent';

// Top-of-dashboard executive summary. Fetches qa-agent /summary and
// renders the LLM narrative + 7d/30d pass rates + per-surface health.

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

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getSummary()
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
    }, []);

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

                    {/* Pass-rate row */}
                    <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1 text-sm">
                        <div>
                            <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B]">
                                Last 7 days
                            </span>
                            <div className="text-2xl font-bold text-[#1A4D2E]">
                                {fmtRate(summary.pass_rate_7d)}
                            </div>
                        </div>
                        <div>
                            <span className="text-[10px] uppercase tracking-wider text-[#6B6B6B]">
                                Last 30 days
                            </span>
                            <div className="text-2xl font-bold text-[#1A4D2E]">
                                {fmtRate(summary.pass_rate_30d)}
                            </div>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-[#4A4A4A]">
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
