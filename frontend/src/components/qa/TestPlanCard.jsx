import React from 'react';
import { LightBulbIcon } from '@heroicons/react/24/outline';

// Test plan card at the TOP of a run-detail page. Shows the
// LLM-authored narrative + a rationale chip + per-surface coverage.
//
// The narrative answers "what does this run test, and why these
// scenarios?" — the dashboard's pre-run context that lifts the report
// from "table of pass/fail" to "thoughtful test pass."

const RATIONALE_LABELS = {
    recently_failed: 'Re-testing recent failure',
    untried_recently: 'Untried recently',
    coverage_gap: 'Coverage gap',
    rotation: 'Rotation',
};

const TestPlanCard = ({ testPlan }) => {
    if (!testPlan) return null;

    const rationaleLabel = RATIONALE_LABELS[testPlan.rationale] || testPlan.rationale;
    const coverage = testPlan.coverage || {};
    const coverageEntries = Object.entries(coverage)
        .sort((a, b) => b[1] - a[1]);

    return (
        <div className="bg-amber-50/70 border border-amber-200 rounded-xl p-5 mb-4">
            <div className="flex items-start gap-3">
                <LightBulbIcon className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 flex-wrap mb-2">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-amber-900">
                            Test plan
                        </h2>
                        {testPlan.rationale && (
                            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 font-semibold">
                                {rationaleLabel}
                            </span>
                        )}
                    </div>
                    <p className="text-sm text-[#2A2A2A] leading-relaxed">
                        {testPlan.narrative}
                    </p>
                    {coverageEntries.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1.5">
                            <span className="text-[10px] uppercase tracking-wider text-amber-900 font-semibold mr-1 self-center">
                                Surfaces:
                            </span>
                            {coverageEntries.map(([surface, count]) => (
                                <span
                                    key={surface}
                                    className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-white border border-amber-200 text-amber-900"
                                >
                                    <span className="font-mono">{surface}</span>
                                    {count > 1 && (
                                        <span className="text-amber-700">×{count}</span>
                                    )}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TestPlanCard;
