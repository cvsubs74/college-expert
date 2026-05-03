import React from 'react';
import { CheckCircleIcon, ExclamationTriangleIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline';

// Outcome card at the BOTTOM of a run-detail page. Renders the
// LLM-authored narrative + verdict chip + a "first-look-at" pointer
// that anchors at the most-load-bearing failure.
//
// Verdict is computed deterministically by the agent from pass/fail
// counts; narrative is LLM-authored. Both are pre-baked into the run
// report; this component is pure render.

const VERDICT_DISPLAY = {
    all_pass: { label: 'All pass', cls: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: CheckCircleIcon },
    minor_flake: { label: 'Minor flake', cls: 'bg-amber-100 text-amber-800 border-amber-200', icon: ExclamationTriangleIcon },
    regression_likely: { label: 'Regression likely', cls: 'bg-rose-100 text-rose-800 border-rose-200', icon: ExclamationTriangleIcon },
    no_data: { label: 'No data', cls: 'bg-gray-100 text-gray-700 border-gray-200', icon: ArrowDownTrayIcon },
};

const scrollToScenario = (scenarioId) => {
    const el = document.getElementById(`scenario-${scenarioId}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
};

const OutcomeCard = ({ outcome }) => {
    if (!outcome) return null;

    const verdict = VERDICT_DISPLAY[outcome.verdict] || VERDICT_DISPLAY.no_data;
    const VerdictIcon = verdict.icon;

    const baseCls = outcome.verdict === 'all_pass'
        ? 'bg-emerald-50/60 border-emerald-200'
        : outcome.verdict === 'minor_flake'
            ? 'bg-amber-50/70 border-amber-200'
            : 'bg-rose-50/60 border-rose-200';

    return (
        <div className={`border rounded-xl p-5 mt-4 ${baseCls}`}>
            <div className="flex items-start gap-3">
                <VerdictIcon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${
                    outcome.verdict === 'all_pass' ? 'text-emerald-600' : 'text-rose-600'
                }`} />
                <div className="flex-1 min-w-0">
                    <div className="flex items-baseline gap-2 flex-wrap mb-2">
                        <h2 className="text-sm font-bold uppercase tracking-wider text-[#1A2E1F]">
                            Outcome
                        </h2>
                        <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border font-semibold ${verdict.cls}`}>
                            {verdict.label}
                        </span>
                    </div>
                    <p className="text-sm text-[#2A2A2A] leading-relaxed">
                        {outcome.narrative}
                    </p>

                    {outcome.first_look_at && outcome.first_look_at.length > 0 && (
                        <div className="mt-3 text-xs text-[#4A4A4A]">
                            <span className="font-semibold uppercase tracking-wider text-[10px]">
                                First look at:
                            </span>{' '}
                            {outcome.first_look_at.map((entry, i) => (
                                <button
                                    key={i}
                                    type="button"
                                    onClick={() => scrollToScenario(entry.scenario_id)}
                                    className="ml-1 inline-flex items-center gap-1 text-rose-700 hover:text-rose-900 underline-offset-2 hover:underline"
                                >
                                    <span className="font-mono">{entry.scenario_id}</span>
                                    {' → '}
                                    <span className="font-mono">{entry.step}</span>
                                </button>
                            ))}
                        </div>
                    )}

                    <div className="mt-3 text-[10px] text-[#8A8A8A] italic">
                        AI-generated; verify against the failing step before acting.
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OutcomeCard;
