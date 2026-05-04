import React from 'react';
import { CheckBadgeIcon } from '@heroicons/react/24/outline';

// "What's validated" card — lists the end-to-end user journeys the QA
// agent has confirmed are working across recent runs. Positive
// counterpart to the System Health failures.
//
// Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.
//
// Data shape (from /summary):
//   {
//     journeys: [
//       { id, surfaces[], summary, scenarios: [{id, verified_at}], verified_count }
//     ],
//     total_journeys: N
//   }

const fmtRelative = (iso) => {
    if (!iso) return '';
    try {
        const dt = new Date(iso);
        const diffMs = Date.now() - dt.getTime();
        const minutes = Math.floor(diffMs / 60000);
        if (minutes < 1) return 'just now';
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        return `${days}d ago`;
    } catch {
        return '';
    }
};

const CoverageCard = ({ coverage }) => {
    if (!coverage || !coverage.journeys || coverage.journeys.length === 0) {
        return null;
    }

    return (
        <div className="bg-white border border-[#E0DED8] rounded-xl p-5">
            <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E] flex items-center gap-2">
                    <CheckBadgeIcon className="h-4 w-4" />
                    What's validated
                </h2>
                <span className="text-xs text-[#8A8A8A]">
                    {coverage.total_journeys} {coverage.total_journeys === 1 ? 'journey' : 'journeys'}
                </span>
            </div>

            <p className="text-xs text-[#6B6B6B] mb-3">
                End-to-end user journeys the QA agent has verified across recent runs.
            </p>

            <ul className="space-y-2.5">
                {coverage.journeys.map((j) => (
                    <li
                        key={j.id}
                        className="border border-[#E0DED8] rounded-lg p-3 bg-[#FBFAF6]"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold text-[#1A2E1F]">
                                    {j.summary}
                                </p>
                                <div className="flex flex-wrap gap-1 mt-1">
                                    {j.surfaces.map((s) => (
                                        <span
                                            key={s}
                                            className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 font-mono"
                                        >
                                            {s}
                                        </span>
                                    ))}
                                </div>
                                {j.scenarios.length > 0 && (
                                    <p className="text-[11px] text-[#6B6B6B] mt-1.5 truncate">
                                        Verified by: {j.scenarios.slice(0, 3).map((s) => s.id).join(', ')}
                                        {j.scenarios.length > 3 && ` + ${j.scenarios.length - 3} more`}
                                    </p>
                                )}
                            </div>
                            <div className="text-right flex-shrink-0">
                                <div className="text-lg font-bold text-emerald-700">
                                    {j.verified_count}
                                </div>
                                <div className="text-[9px] uppercase tracking-wider text-[#6B6B6B]">
                                    passes
                                </div>
                                {j.scenarios[0]?.verified_at && (
                                    <div className="text-[10px] text-[#8A8A8A] mt-0.5">
                                        {fmtRelative(j.scenarios[0].verified_at)}
                                    </div>
                                )}
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default CoverageCard;
