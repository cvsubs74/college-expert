import React from 'react';
import { AcademicCapIcon } from '@heroicons/react/24/outline';

// "Universities tested" card — answers "what schools has the QA agent
// actually exercised?".
//
// Spec: docs/prd/qa-universities-tracking.md,
//       docs/design/qa-universities-tracking.md.
//
// Data shape (from /summary's `coverage` block):
//   {
//     universities_tested: [{id, count, last_tested_at}],
//     total_universities_tested: N,
//     universities_untested: [id, ...],   // capped at 25 server-side
//     allowlist_size: M,
//   }
//
// The Coverage card next to this one already covers journeys + features.
// This card is the missing university dimension.

const VISIBLE_TESTED_CAP = 15;

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

const UniversitiesCard = ({ universities }) => {
    if (!universities) return null;
    const tested = universities.universities_tested || [];
    const untested = universities.universities_untested || [];
    const totalTested = universities.total_universities_tested ?? tested.length;
    const allowlistSize = universities.allowlist_size ?? 0;

    // Hide the card entirely when we have neither tested data nor an
    // allowlist — there's nothing meaningful to show.
    if (tested.length === 0 && allowlistSize === 0) return null;

    const visibleTested = tested.slice(0, VISIBLE_TESTED_CAP);
    const hiddenTestedCount = tested.length - visibleTested.length;

    return (
        <div className="bg-white border border-[#E0DED8] rounded-xl p-5">
            <div className="flex items-baseline justify-between mb-3 gap-2 flex-wrap">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E] flex items-center gap-2">
                    <AcademicCapIcon className="h-4 w-4" />
                    Universities tested
                </h2>
                {allowlistSize > 0 && (
                    <span className="text-xs text-[#8A8A8A]">
                        {totalTested} of {allowlistSize} covered
                    </span>
                )}
            </div>

            <p className="text-xs text-[#6B6B6B] mb-3">
                Schools the QA agent has exercised in recent passing scenarios.
            </p>

            {tested.length === 0 ? (
                <p className="text-xs text-[#8A8A8A] italic">
                    No university coverage yet — schedule a run to start tracking.
                </p>
            ) : (
                <ul className="space-y-1.5">
                    {visibleTested.map((u) => (
                        <li
                            key={u.id}
                            className="flex items-center justify-between gap-2 text-xs text-[#2A2A2A]"
                        >
                            <span className="font-mono truncate flex-1 min-w-0">
                                {u.id}
                            </span>
                            <span className="flex-shrink-0 text-[10px] text-[#8A8A8A]">
                                {fmtRelative(u.last_tested_at)}
                            </span>
                            <span className="flex-shrink-0 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
                                {u.count}×
                            </span>
                        </li>
                    ))}
                </ul>
            )}
            {hiddenTestedCount > 0 && (
                <p className="mt-2 text-[11px] text-[#8A8A8A] italic">
                    + {hiddenTestedCount} more
                </p>
            )}

            {untested.length > 0 && (
                <div className="mt-4 pt-3 border-t border-[#E0DED8]">
                    <div className="text-[10px] uppercase tracking-wider text-[#6B6B6B] font-semibold mb-1.5">
                        Not yet tested ({untested.length})
                    </div>
                    <p className="text-[11px] text-[#6B6B6B] font-mono leading-relaxed break-words">
                        {untested.join(', ')}
                    </p>
                </div>
            )}
        </div>
    );
};

export default UniversitiesCard;
