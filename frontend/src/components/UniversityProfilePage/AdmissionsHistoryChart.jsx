import React, { useState, useEffect } from 'react';
import { ChartBarIcon } from '@heroicons/react/24/outline';
import { getUniversityHistory } from '../../services/api';

// ============================================================================
// AdmissionsHistoryChart (#286)
//
// Draws the acceptance-rate history from the KB's `action=history` endpoint
// as TWO deliberately separate groups:
//   1. "Stratia KB snapshots" — per-cycle rows (application-CYCLE year axis,
//      authoritative; `vintage_estimated` rows get an "estimated year" marker)
//   2. "School-reported (unverified)" — the school's own trend rows
//      (entering-class year axis), rendered visually secondary.
// The two use DIFFERENT year conventions and are never merged into one
// timeline or one selectivity computation.
//
// If the history fetch fails, the old profile-baked longitudinal_trends
// rendering (LegacyTrendsChart) is the fallback path.
// ============================================================================

// History API values are already percent-style; legacy profile trends (the
// fallback path) can be decimals (0.48 = 48%). Same guard as the old chart.
const normalizeRate = (raw) => (raw < 1 ? raw * 100 : raw);

// rates: newest-first array of percent values from ONE series only.
const SelectivityIndicator = ({ rates, sourceLabel }) => {
    if (!rates || rates.length < 2) return null;
    const change = rates[0] - rates[rates.length - 1];
    const isMoreSelective = change < 0;
    return (
        <div className="mt-4 pt-4 border-t border-gray-100">
            <p className={`text-sm flex items-center gap-2 ${isMoreSelective ? 'text-red-600' : 'text-green-600'}`}>
                {isMoreSelective ? '📉' : '📈'}
                <span className="font-medium">
                    {isMoreSelective ? 'Getting more selective' : 'Getting less selective'}
                </span>
                <span className="text-gray-500">
                    ({change > 0 ? '+' : ''}{change.toFixed(1)}% across {rates.length} {sourceLabel})
                </span>
            </p>
        </div>
    );
};

const ChartCard = ({ children }) => (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <ChartBarIcon className="h-5 w-5" style={{ color: 'var(--stratia-primary)' }} />
            Acceptance Rate Trends
        </h3>
        {children}
    </div>
);

// The pre-#286 rendering, kept verbatim as the fallback when the history
// fetch fails: profile-baked longitudinal_trends, single blue series.
export const LegacyTrendsChart = ({ trends }) => {
    if (!trends || trends.length === 0) return null;
    const validTrends = trends.filter(t => t.acceptance_rate_overall && t.acceptance_rate_overall > 0);

    return (
        <ChartCard>
            <div className="flex items-end justify-between gap-2 h-40">
                {trends
                    .slice(0, 5)
                    .reverse()
                    .filter(t => t.acceptance_rate_overall && t.acceptance_rate_overall > 0)
                    .map((t, i) => {
                        const normalizedRate = normalizeRate(t.acceptance_rate_overall);
                        return (
                            <div key={i} className="flex-1 flex flex-col items-center">
                                <div
                                    className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t transition-all hover:from-blue-700 hover:to-blue-500"
                                    style={{ height: `${(normalizedRate / 100) * 100}%`, minHeight: '20px' }}
                                ></div>
                                <span className="text-xs text-gray-500 mt-2">{t.year}</span>
                                <span className="text-sm font-bold text-blue-600">{normalizedRate.toFixed(1)}%</span>
                            </div>
                        );
                    })}
            </div>
            <SelectivityIndicator
                rates={validTrends.map(t => normalizeRate(t.acceptance_rate_overall))}
                sourceLabel="years"
            />
        </ChartCard>
    );
};

// One bar group. rows arrive oldest → newest (newest last).
const BarGroup = ({ rows, variant }) => {
    const isPrimary = variant === 'primary';
    return (
        <div className="flex items-end gap-2 h-36">
            {rows.map((row, i) => (
                <div key={i} className="flex-1 flex flex-col items-center min-w-0">
                    <div
                        className="w-full rounded-t transition-all"
                        style={{
                            height: `${Math.min(normalizeRate(row.rate), 100)}%`,
                            minHeight: '8px',
                            ...(isPrimary
                                ? { backgroundColor: 'var(--stratia-primary)' }
                                : {
                                    backgroundColor: 'var(--stratia-surface)',
                                    border: '1px dashed var(--stratia-outline)',
                                }),
                        }}
                    ></div>
                    <span className="text-xs text-gray-500 mt-2 truncate max-w-full">{row.label}</span>
                    <span
                        className="text-sm font-bold"
                        style={{ color: isPrimary ? 'var(--stratia-primary)' : 'var(--stratia-on-surface-variant)' }}
                    >
                        {normalizeRate(row.rate).toFixed(1)}%
                    </span>
                    {row.estimated && (
                        <span className="text-[10px]" style={{ color: 'var(--stratia-tertiary)' }}>
                            estimated year
                        </span>
                    )}
                </div>
            ))}
        </div>
    );
};

const AdmissionsHistoryChart = ({ universityId, fallbackTrends }) => {
    const [loading, setLoading] = useState(Boolean(universityId));
    const [history, setHistory] = useState(null);
    const [failed, setFailed] = useState(!universityId);

    useEffect(() => {
        if (!universityId) {
            setLoading(false);
            setFailed(true);
            return undefined;
        }
        let cancelled = false;
        setLoading(true);
        setFailed(false);
        setHistory(null);
        getUniversityHistory(universityId)
            .then((res) => {
                if (cancelled) return;
                if (res && res.success) {
                    setHistory(res);
                } else {
                    setFailed(true);
                }
                setLoading(false);
            })
            .catch(() => {
                if (cancelled) return;
                setFailed(true);
                setLoading(false);
            });
        return () => { cancelled = true; };
    }, [universityId]);

    if (loading) {
        return (
            <div data-testid="history-loading" className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                <div className="animate-pulse space-y-3">
                    <div className="h-4 w-48 rounded" style={{ backgroundColor: 'var(--stratia-outline-variant)' }}></div>
                    <div className="h-32 rounded" style={{ backgroundColor: 'var(--stratia-surface)' }}></div>
                </div>
            </div>
        );
    }

    // History unavailable → the old profile-baked rendering (or nothing).
    if (failed || !history) {
        return <LegacyTrendsChart trends={fallbackTrends} />;
    }

    // Drawable rows only; each series keeps the API's newest-first order.
    const snapshotRows = (history.snapshots || [])
        .filter(s => typeof s.acceptance_rate === 'number' && s.acceptance_rate > 0);
    const reportedRows = (history.reported_trends || [])
        .filter(t => typeof t.acceptance_rate_overall === 'number' && t.acceptance_rate_overall > 0);
    const totalRows = snapshotRows.length + reportedRows.length;

    if (totalRows === 0) {
        return <LegacyTrendsChart trends={fallbackTrends} />;
    }

    if (totalRows === 1) {
        const snap = snapshotRows[0];
        const rate = snap ? snap.acceptance_rate : reportedRows[0].acceptance_rate_overall;
        const label = snap
            ? `${snap.cycle_label || snap.year || 'current'} cycle (Stratia KB)`
            : `${reportedRows[0].year || 'undated'} (school-reported, unverified)`;
        return (
            <ChartCard>
                <p className="text-3xl font-bold" style={{ color: 'var(--stratia-primary)' }}>
                    {normalizeRate(rate).toFixed(1)}%
                </p>
                <p className="text-sm text-gray-500">Acceptance rate — {label}</p>
                <p className="text-sm text-gray-400 mt-2">
                    Year-over-year history builds up each admission cycle.
                </p>
            </ChartCard>
        );
    }

    // Selectivity is computed within ONE series only — the two groups use
    // different year conventions, so a cross-series delta is meaningless.
    const indicator = reportedRows.length >= 2
        ? { rates: reportedRows.map(t => normalizeRate(t.acceptance_rate_overall)), label: 'school-reported years' }
        : (snapshotRows.length >= 2
            ? { rates: snapshotRows.map(s => normalizeRate(s.acceptance_rate)), label: 'KB cycles' }
            : null);

    return (
        <ChartCard>
            <div className="space-y-6">
                {snapshotRows.length > 0 && (
                    <div>
                        <p className="text-sm font-semibold" style={{ color: 'var(--stratia-primary)' }}>
                            Stratia KB snapshots
                        </p>
                        <p className="text-xs text-gray-500 mb-3">
                            Acceptance rate by application cycle, verified at collection time.
                        </p>
                        <BarGroup
                            variant="primary"
                            rows={[...snapshotRows].reverse().map(s => ({
                                rate: s.acceptance_rate,
                                label: s.cycle_label || s.year || '—',
                                estimated: Boolean(s.vintage_estimated),
                            }))}
                        />
                    </div>
                )}
                {reportedRows.length > 0 && (
                    <div>
                        <p className="text-sm font-semibold" style={{ color: 'var(--stratia-on-surface-variant)' }}>
                            School-reported (unverified)
                        </p>
                        <p className="text-xs text-gray-500 mb-3">
                            Figures the school reports for prior classes. These use a
                            different year axis (entering class) than the cycle snapshots
                            above and are not verified by Stratia — shown separately, never
                            merged.
                        </p>
                        <BarGroup
                            variant="secondary"
                            rows={[...reportedRows].reverse().map(t => ({
                                rate: t.acceptance_rate_overall,
                                label: t.year || t.cycle_name || '—',
                                estimated: false,
                            }))}
                        />
                    </div>
                )}
            </div>
            {indicator && (
                <SelectivityIndicator rates={indicator.rates} sourceLabel={indicator.label} />
            )}
        </ChartCard>
    );
};

export default AdmissionsHistoryChart;
