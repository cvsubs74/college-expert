import React, { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon, LightBulbIcon } from '@heroicons/react/24/outline';
import StepRow from './StepRow';
import PassFailBadge from './PassFailBadge';
import ReportBugButton from './ReportBugButton';
import SuggestCauseModal from './SuggestCauseModal';
import SynthesizedBadge from './SynthesizedBadge';

// One scenario inside a run. Header shows pass/fail + summary; expand
// to see steps. Failing scenarios get "Suggest cause" + "Report bug"
// action buttons.

const fmtMs = (ms) => (ms == null ? '—' : ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`);

const ScenarioCard = ({ runId, scenario }) => {
    const stepCount = scenario.steps?.length || 0;
    const passedSteps = (scenario.steps || []).filter((s) => s.passed).length;
    const summary = { total: stepCount, pass: passedSteps, fail: stepCount - passedSteps };

    const [open, setOpen] = useState(!scenario.passed);
    const [showSuggest, setShowSuggest] = useState(false);

    return (
        <div className={`bg-white rounded-xl border ${scenario.passed ? 'border-[#E0DED8]' : 'border-rose-200'}`}>
            <button
                type="button"
                className="w-full flex items-center gap-4 px-5 py-4 text-left"
                onClick={() => setOpen(!open)}
            >
                <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-3 flex-wrap">
                        <span className="font-mono text-sm font-bold text-[#1A2E1F]">
                            {scenario.scenario_id}
                        </span>
                        <PassFailBadge summary={summary} />
                        <span className="text-xs text-[#8A8A8A]">{fmtMs(scenario.duration_ms)}</span>
                    </div>
                    <p className="text-xs text-[#6B6B6B] mt-1 truncate">{scenario.description}</p>
                    {scenario.variation && Object.keys(scenario.variation).length > 0 && (
                        <p className="text-[11px] text-[#8A8A8A] mt-1 font-mono truncate">
                            {scenario.variation.student_name || ''}
                            {scenario.variation.intended_major
                                ? ` · ${scenario.variation.intended_major}`
                                : ''}
                            {scenario.variation.gpa_delta != null
                                ? ` · gpa Δ ${scenario.variation.gpa_delta > 0 ? '+' : ''}${scenario.variation.gpa_delta}`
                                : ''}
                        </p>
                    )}
                </div>
                {open ? (
                    <ChevronUpIcon className="h-5 w-5 text-[#8A8A8A]" />
                ) : (
                    <ChevronDownIcon className="h-5 w-5 text-[#8A8A8A]" />
                )}
            </button>

            {open && (
                <div className="border-t border-[#E0DED8] px-5 py-4 space-y-3">
                    {!scenario.passed && (
                        <div className="flex items-center gap-2 flex-wrap">
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setShowSuggest(true);
                                }}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-full border border-amber-200 text-amber-800 bg-amber-50 hover:bg-amber-100"
                            >
                                <LightBulbIcon className="h-3.5 w-3.5" />
                                Suggest cause
                            </button>
                            <ReportBugButton
                                runId={runId}
                                scenarioId={scenario.scenario_id}
                            />
                        </div>
                    )}

                    <SynthesizedBadge
                        synthesized={scenario.synthesized}
                        rationale={scenario.synthesis_rationale}
                    />

                    {scenario.tests && scenario.tests.length > 0 && (
                        <div className="bg-[#FBFAF6] border border-[#E0DED8] rounded-lg p-3 mb-2">
                            <div className="text-[10px] uppercase tracking-wider text-[#6B6B6B] font-semibold mb-1.5">
                                What this scenario tests
                            </div>
                            <ul className="space-y-1 text-xs text-[#2A2A2A]">
                                {scenario.tests.map((t, i) => (
                                    <li key={i} className="flex items-start gap-2">
                                        <span className="text-[#1A4D2E] mt-0.5">•</span>
                                        <span>{t}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <div className="space-y-2">
                        {(scenario.steps || []).map((step, i) => (
                            <StepRow key={`${scenario.scenario_id}-${i}-${step.name}`} step={step} />
                        ))}
                    </div>
                </div>
            )}

            {showSuggest && (
                <SuggestCauseModal
                    runId={runId}
                    scenarioId={scenario.scenario_id}
                    onClose={() => setShowSuggest(false)}
                />
            )}
        </div>
    );
};

export default ScenarioCard;
