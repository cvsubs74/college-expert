import React from 'react';

// Per-run pass/fail sparkline at the top of the dashboard.
//
// One bar per run, coloured by that run's `summary.fail`:
//   - any fail → red
//   - all pass → green
// Runs are ordered chronologically (oldest left, newest right) so the
// rightmost bar is the most recent.
//
// Spec: docs/prd/qa-dashboard-visibility-gaps.md +
//       docs/design/qa-dashboard-visibility-gaps.md.
//
// History: this component was originally per-day (each bar = "worst run
// that day"), which produced empty gray buckets when the agent's
// schedule left some days without runs. With ~21 runs across 30 days
// the operator saw "81% green" headline but no green bars. Switching
// to per-run aligns the visual with the headline.
//
// Inline SVG so we don't need a chart library.

const W = 240;
const H = 40;
const GAP = 1;
const MIN_BAR_WIDTH = 4;
// At MIN_BAR_WIDTH + GAP per slot, ~48 bars fit in W. Cap there to
// keep the chart readable; older runs fall off the left edge.
const MAX_VISIBLE_BARS = Math.floor((W + GAP) / (MIN_BAR_WIDTH + GAP));

const SparklineByDay = ({ runs }) => {
    // Filter to runs with a usable timestamp, then sort chronologically.
    const tsRuns = (runs || [])
        .filter((r) => Boolean(r?.started_at))
        .map((r) => ({ run: r, ts: new Date(r.started_at).getTime() }))
        .filter((r) => Number.isFinite(r.ts))
        .sort((a, b) => a.ts - b.ts);

    const totalRuns = tsRuns.length;
    const passedRuns = tsRuns.filter(
        ({ run }) => (run.summary?.fail ?? 0) === 0,
    ).length;
    const passRate = totalRuns > 0
        ? Math.round((100 * passedRuns) / totalRuns)
        : null;

    // Take the most recent N to render so a year of history doesn't
    // produce hairline bars.
    const visible = tsRuns.slice(-MAX_VISIBLE_BARS);
    const truncated = totalRuns - visible.length;

    const colW = visible.length > 0
        ? Math.max(MIN_BAR_WIDTH, (W - GAP * (visible.length - 1)) / visible.length)
        : 0;

    return (
        <div className="flex items-center gap-4">
            <svg
                viewBox={`0 0 ${W} ${H}`}
                width="100%"
                height={H}
                className="max-w-[240px]"
                aria-label="Pass/fail per recent run"
            >
                {visible.map(({ run }, i) => {
                    const x = i * (colW + GAP);
                    const fill = (run.summary?.fail ?? 0) > 0
                        ? '#EF4444'
                        : '#10B981';
                    return (
                        <rect
                            key={run.run_id || `${run.started_at}-${i}`}
                            x={x}
                            y={2}
                            width={colW}
                            height={H - 4}
                            fill={fill}
                            rx={1}
                        />
                    );
                })}
            </svg>
            <div className="text-xs text-[#6B6B6B] whitespace-nowrap">
                <div className="font-semibold text-[#1A4D2E]">
                    {passRate == null ? '—' : `${passRate}% green`}
                </div>
                <div>
                    {totalRuns} runs
                    {truncated > 0 && ` · showing latest ${visible.length}`}
                </div>
            </div>
        </div>
    );
};

export default SparklineByDay;
