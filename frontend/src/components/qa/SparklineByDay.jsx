import React from 'react';

// 30-day pass/fail sparkline. For each day, a column whose colour
// reflects the worst run of that day:
//   - all green → green
//   - any red → red
//   - no runs → blank
// Inline SVG so we don't need a chart library.

const SparklineByDay = ({ runs, days = 30 }) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const buckets = new Array(days).fill(null);
    for (const run of runs || []) {
        if (!run.started_at) continue;
        const ts = new Date(run.started_at);
        const dayOffset = Math.floor((today - ts) / (1000 * 60 * 60 * 24));
        if (dayOffset < 0 || dayOffset >= days) continue;
        const idx = days - 1 - dayOffset;
        const fail = run.summary?.fail ?? 0;
        const cur = buckets[idx];
        if (!cur) {
            buckets[idx] = { worst: fail > 0 ? 'fail' : 'pass', count: 1 };
        } else {
            cur.count += 1;
            if (fail > 0) cur.worst = 'fail';
        }
    }

    const W = 240, H = 40, gap = 1;
    const colW = (W - gap * (days - 1)) / days;

    const totalRuns = buckets.reduce((s, b) => s + (b?.count || 0), 0);
    const greenDays = buckets.filter(b => b?.worst === 'pass').length;
    const redDays = buckets.filter(b => b?.worst === 'fail').length;
    const passRate = (greenDays + redDays > 0)
        ? Math.round(100 * greenDays / (greenDays + redDays))
        : null;

    return (
        <div className="flex items-center gap-4">
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} className="max-w-[240px]" aria-label="30-day pass/fail by day">
                {buckets.map((b, i) => {
                    const x = i * (colW + gap);
                    const fill = !b
                        ? '#E5E7EB'
                        : b.worst === 'pass'
                            ? '#10B981'
                            : '#EF4444';
                    return <rect key={i} x={x} y={2} width={colW} height={H - 4} fill={fill} rx={1} />;
                })}
            </svg>
            <div className="text-xs text-[#6B6B6B] whitespace-nowrap">
                <div className="font-semibold text-[#1A4D2E]">
                    {passRate == null ? '—' : `${passRate}% green`}
                </div>
                <div>{totalRuns} runs · last {days} days</div>
            </div>
        </div>
    );
};

export default SparklineByDay;
