import React from 'react';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';
import { fmtRelative } from '../../utils/fmtRelative';

// "Issues caught and fixed" card — lists recent FAIL → PASS transitions
// with the failing-assertion message preserved as evidence of what was
// broken before the fix landed.
//
// Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.
//
// Data shape (from /summary):
//   {
//     fixes: [
//       { scenario_id, step_name, failing_message, failed_at_run, fixed_at_run, fixed_at_time }
//     ],
//     total_fixes: N,
//     lookback_runs: M
//   }

const ResolvedIssuesCard = ({ resolvedIssues }) => {
    if (!resolvedIssues || !resolvedIssues.fixes || resolvedIssues.fixes.length === 0) {
        return null;
    }
    const { fixes, total_fixes: totalFixes, lookback_runs: lookbackRuns } = resolvedIssues;

    return (
        <div className="bg-white border border-[#E0DED8] rounded-xl p-5">
            <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E] flex items-center gap-2">
                    <ShieldCheckIcon className="h-4 w-4" />
                    Issues caught & fixed
                </h2>
                <span className="text-xs text-[#8A8A8A]">
                    {totalFixes} {totalFixes === 1 ? 'fix' : 'fixes'} across last {lookbackRuns} runs
                </span>
            </div>

            <p className="text-xs text-[#6B6B6B] mb-3">
                Bugs the QA agent caught that have since been resolved (verified by a
                subsequent passing run).
            </p>

            <ul className="space-y-2.5">
                {fixes.map((f, i) => (
                    <li
                        key={`${f.scenario_id}/${f.step_name}/${i}`}
                        className="border border-[#E0DED8] rounded-lg p-3 bg-[#FBFAF6]"
                    >
                        <div className="flex items-baseline justify-between gap-3 mb-1">
                            <div className="font-mono text-xs font-semibold text-[#1A2E1F] truncate">
                                {f.scenario_id} <span className="text-[#8A8A8A]">/</span> {f.step_name}
                            </div>
                            <span className="text-[10px] text-emerald-700 font-semibold whitespace-nowrap">
                                fixed {fmtRelative(f.fixed_at_time)}
                            </span>
                        </div>
                        <p className="text-[11px] text-[#4A4A4A] italic font-mono break-words">
                            was failing: {f.failing_message || '<no message>'}
                        </p>
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 text-[10px] text-[#8A8A8A]">
                            <span>caught in <span className="font-mono">{f.failed_at_run}</span></span>
                            <span>→</span>
                            <span>resolved in <span className="font-mono">{f.fixed_at_run}</span></span>
                        </div>
                    </li>
                ))}
            </ul>

            {totalFixes > fixes.length && (
                <p className="mt-3 text-[11px] text-[#8A8A8A] italic">
                    Showing {fixes.length} most-recent fixes; {totalFixes - fixes.length} more across the lookback window.
                </p>
            )}
        </div>
    );
};

export default ResolvedIssuesCard;
