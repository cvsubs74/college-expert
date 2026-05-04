import React from 'react';
import { CheckBadgeIcon } from '@heroicons/react/24/outline';
import { fmtRelative } from '../../utils/fmtRelative';

// "What's validated" card — surfaces both:
//   1. End-to-end user journeys (surfaces tuple)
//   2. The specific feature-level test bullets aggregated across recent
//      passing scenarios (e.g., "Resolver picks junior_spring template",
//      "UC group task covers all UCs in single entry").
//
// Spec: docs/prd/qa-dashboard-insights.md, docs/design/qa-dashboard-insights.md.
//
// Data shape (from /summary):
//   {
//     journeys: [{id, surfaces[], summary, scenarios, verified_count}],
//     total_journeys: N,
//     validated_features: [{text, count}],   // PR-K
//     total_features: M
//   }

const CoverageCard = ({ coverage }) => {
    if (!coverage || !coverage.journeys || coverage.journeys.length === 0) {
        return null;
    }
    const features = coverage.validated_features || [];
    const totalFeatures = coverage.total_features || features.length;

    return (
        <div className="bg-white border border-[#E0DED8] rounded-xl p-5">
            <div className="flex items-baseline justify-between mb-3 gap-2 flex-wrap">
                <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A4D2E] flex items-center gap-2">
                    <CheckBadgeIcon className="h-4 w-4" />
                    What's validated
                </h2>
                <span className="text-xs text-[#8A8A8A]">
                    {coverage.total_journeys} {coverage.total_journeys === 1 ? 'journey' : 'journeys'}
                    {totalFeatures > 0 && ` · ${totalFeatures} ${totalFeatures === 1 ? 'feature' : 'features'}`}
                </span>
            </div>

            <p className="text-xs text-[#6B6B6B] mb-3">
                End-to-end user journeys + specific behaviors the QA agent has verified across recent runs.
            </p>

            <div className="text-[10px] uppercase tracking-wider text-[#6B6B6B] font-semibold mb-2">
                Journeys
            </div>
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

            {features.length > 0 && (
                <div className="mt-4">
                    <div className="text-[10px] uppercase tracking-wider text-[#6B6B6B] font-semibold mb-2 flex items-baseline justify-between">
                        <span>Features verified</span>
                        {totalFeatures > features.length && (
                            <span className="text-[10px] normal-case tracking-normal text-[#8A8A8A] italic font-normal">
                                showing top {features.length} of {totalFeatures}
                            </span>
                        )}
                    </div>
                    <ul className="space-y-1.5">
                        {features.map((f, i) => (
                            <li
                                key={`${i}-${f.text}`}
                                className="flex items-start gap-2 text-xs text-[#2A2A2A]"
                            >
                                <span
                                    className="text-emerald-700 font-bold mt-0.5 flex-shrink-0"
                                    aria-label="verified"
                                >
                                    ✓
                                </span>
                                <span className="flex-1 min-w-0">{f.text}</span>
                                <span className="flex-shrink-0 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
                                    {f.count}×
                                </span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default CoverageCard;
