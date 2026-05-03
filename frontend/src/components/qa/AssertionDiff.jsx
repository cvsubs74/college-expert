import React from 'react';

// Renders a single assertion result. For cross-reference assertions
// (those with `expected` + `actual` fields), shows a side-by-side
// diff so the reviewer can see exactly what we expected vs what the
// API returned.
//
// Standard assertions render as a single-line bullet, same as before.
// Cross-reference assertions get the expanded diff treatment.

const formatVal = (v) => {
    if (v == null) return '(none)';
    if (typeof v === 'string') return v;
    return JSON.stringify(v);
};

const AssertionDiff = ({ result }) => {
    if (!result) return null;
    const hasDiff =
        Object.prototype.hasOwnProperty.call(result, 'expected') ||
        Object.prototype.hasOwnProperty.call(result, 'actual');
    const dotColor = result.skipped
        ? 'bg-gray-400'
        : result.passed
            ? 'bg-emerald-500'
            : 'bg-rose-500';

    return (
        <li className="flex items-start gap-2">
            <span className={`inline-block w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${dotColor}`} />
            <div className="flex-1 min-w-0">
                <div className="font-mono text-[11px] text-[#2A2A2A]">
                    {result.skipped && (
                        <span className="text-[10px] uppercase tracking-wider mr-2 text-gray-600 font-semibold">
                            SKIP
                        </span>
                    )}
                    <span className={result.passed || result.skipped ? 'text-[#4A4A4A]' : 'text-rose-700'}>
                        {result.name}
                    </span>
                    {result.message && (
                        <span className="text-[#8A8A8A] ml-2">— {result.message}</span>
                    )}
                </div>
                {hasDiff && (result.expected !== undefined || result.actual !== undefined) && (
                    <div className="mt-1 ml-1 grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-[11px] font-mono">
                        <span className="text-emerald-700 font-semibold">expected:</span>
                        <span className="text-[#4A4A4A] break-all">{formatVal(result.expected)}</span>
                        <span className="text-rose-700 font-semibold">actual:</span>
                        <span className="text-[#4A4A4A] break-all">{formatVal(result.actual)}</span>
                    </div>
                )}
            </div>
        </li>
    );
};

export default AssertionDiff;
