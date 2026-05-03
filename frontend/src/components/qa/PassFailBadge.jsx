import React from 'react';

// Coloured badge for a run or scenario's pass/fail state.
const PassFailBadge = ({ summary, size = 'md' }) => {
    const total = summary?.total ?? 0;
    const fail = summary?.fail ?? 0;
    const pass = summary?.pass ?? 0;

    // Empty state (e.g., a run that errored before scenarios ran).
    if (total === 0) {
        return (
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 ${size === 'lg' ? 'text-sm px-3 py-1.5' : ''}`}>
                no scenarios
            </span>
        );
    }

    const allPass = fail === 0;
    const cls = allPass
        ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
        : 'bg-rose-100 text-rose-800 border border-rose-200';
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold ${cls} ${size === 'lg' ? 'text-sm px-3 py-1.5' : ''}`}>
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${allPass ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            {pass}/{total} pass
        </span>
    );
};

export default PassFailBadge;
