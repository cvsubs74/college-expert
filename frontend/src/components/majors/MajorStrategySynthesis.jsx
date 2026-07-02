import React, { useState, useEffect, useCallback } from 'react';
import {
    LightBulbIcon,
    SparklesIcon,
    ArrowPathIcon,
    DocumentTextIcon,
    ClipboardDocumentCheckIcon
} from '@heroicons/react/24/outline';
import {
    getMajorStrategy,
    generateMajorStrategy,
    checkCredits
} from '../../services/api';
import CreditsUpgradeModal from '../CreditsUpgradeModal';

// ============================================================================
// MAJOR STRATEGY SYNTHESIS (#284) — the strategy layer below the phase-1
// facts panel on the Majors tab. Rules this component holds:
//   - Every synthesis section is labeled "Stratia's read" (inference chip) —
//     it is counselor judgment over the labeled facts, never school data.
//   - Generation costs 1 credit, billed SERVER-side; 402 → upgrade modal.
//   - A KB miss ({strategy: null, gaps}) is rendered honestly: no strategy,
//     no charge, gap logged.
//   - A stale chip appears when the KB has newer data than the strategy.
// ============================================================================

const InferenceChip = () => (
    <span className="stratia-chip bg-purple-100 text-purple-700 border border-purple-200 whitespace-nowrap">
        Stratia's read
    </span>
);

const SECTIONS = [
    { key: 'primary_call', title: 'Primary call' },
    { key: 'second_choice_play', title: 'Second-choice play' },
    { key: 'backup_rationale', title: 'Backup rationale' },
    { key: 'undeclared_tactic', title: 'Undeclared tactic' }
];

const MajorStrategySynthesis = ({ userEmail, universityId }) => {
    const [strategy, setStrategy] = useState(null);
    const [stale, setStale] = useState(false);
    const [currentKbYear, setCurrentKbYear] = useState(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [gaps, setGaps] = useState(null); // KB-miss result — honest, unbilled
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [creditsRemaining, setCreditsRemaining] = useState(0);

    const loadStrategy = useCallback(async () => {
        setLoading(true);
        const result = await getMajorStrategy(userEmail, universityId);
        if (result?.success) {
            setStrategy(result.strategy);
            setStale(Boolean(result.stale));
            setCurrentKbYear(result.current_kb_year ?? null);
        }
        setLoading(false);
    }, [userEmail, universityId]);

    useEffect(() => {
        if (userEmail && universityId) loadStrategy();
    }, [userEmail, universityId, loadStrategy]);

    const handleGenerate = async () => {
        setError(null);
        setGaps(null);
        const credits = await checkCredits(userEmail, 1);
        if (credits?.has_credits !== true) {
            setCreditsRemaining(credits?.credits_remaining ?? 0);
            setShowUpgradeModal(true);
            return;
        }
        setGenerating(true);
        const result = await generateMajorStrategy(userEmail, universityId);
        setGenerating(false);
        if (result?.success && result.strategy) {
            setStrategy(result.strategy);
            setStale(false);
        } else if (result?.success && result.strategy === null) {
            // Never-charged KB miss — render it honestly, never fill it in.
            setGaps(result.gaps || []);
        } else if (result?.insufficientCredits) {
            setCreditsRemaining(result.creditsRemaining ?? 0);
            setShowUpgradeModal(true);
        } else {
            setError(result?.error || 'Strategy generation failed — try again.');
        }
    };

    if (loading) {
        return (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100" data-testid="strategy-loading">
                <div className="animate-pulse space-y-3">
                    <div className="h-5 bg-gray-200 rounded w-1/3" />
                    <div className="h-16 bg-gray-100 rounded" />
                </div>
            </div>
        );
    }

    const synthesis = strategy?.synthesis || {};
    const verifyList = synthesis.what_to_verify_yourself || [];
    const dataNotes = strategy?.data_notes || [];

    return (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100" data-testid="major-strategy-synthesis">
            <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                <h2 className="font-bold text-gray-900 flex items-center gap-2">
                    <LightBulbIcon className="h-5 w-5 text-[#1A4D2E]" />
                    Major strategy
                </h2>
                <div className="flex items-center gap-2">
                    {strategy && <InferenceChip />}
                    {strategy && stale && (
                        <span className="stratia-chip bg-amber-100 text-amber-800 border border-amber-300" data-testid="strategy-stale-chip">
                            Built on {strategy.kb_data_year} data{currentKbYear ? ` — ${currentKbYear} available` : ''}
                        </span>
                    )}
                </div>
            </div>

            {error && <p className="text-sm text-red-600 mt-1" role="alert">{error}</p>}

            {/* ---- KB miss: honest, unbilled ---- */}
            {gaps && (
                <div className="mt-2 bg-[#F8F6F0] border border-[#E0DED8] rounded-lg p-4" data-testid="strategy-gaps">
                    <p className="text-sm text-gray-700">
                        We don't have entry-path data for{' '}
                        <span className="font-medium">{gaps.join(', ') || 'these majors'}</span>{' '}
                        at this school yet — you weren't charged. We've logged the gap
                        and it's now on our collection priority list.
                    </p>
                </div>
            )}

            {/* ---- Empty state: explicit, priced CTA ---- */}
            {!strategy && !gaps && (
                <div className="mt-2">
                    <p className="text-sm text-gray-700">
                        Turn the facts above into a read: which major to list here, the
                        second-choice play, backups, and what it means for your essays.
                    </p>
                    <button
                        onClick={handleGenerate}
                        disabled={generating}
                        className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg text-sm font-medium hover:bg-[#143D24] transition-colors disabled:opacity-50"
                    >
                        {generating
                            ? (<><ArrowPathIcon className="h-4 w-4 animate-spin" /> Generating…</>)
                            : (<><SparklesIcon className="h-4 w-4" /> Generate strategy — 1 credit</>)}
                    </button>
                </div>
            )}

            {/* ---- Saved strategy: labeled synthesis sections ---- */}
            {strategy && (
                <div className="mt-3 space-y-4">
                    {SECTIONS.map(({ key, title }) => (
                        synthesis[key] ? (
                            <div key={key} data-testid={`section-${key}`}>
                                <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
                                <p className="text-sm text-gray-700 mt-0.5">{synthesis[key]}</p>
                            </div>
                        ) : null
                    ))}

                    {synthesis.essay_implication && (
                        <div className="bg-[#D6E8D5] border border-[#1A4D2E]/20 rounded-lg p-3" data-testid="section-essay_implication">
                            <h3 className="text-sm font-semibold text-[#1A4D2E] flex items-center gap-1.5">
                                <DocumentTextIcon className="h-4 w-4" />
                                ESSAY IMPLICATION
                            </h3>
                            <p className="text-sm text-gray-800 mt-1">{synthesis.essay_implication}</p>
                        </div>
                    )}

                    {verifyList.length > 0 && (
                        <div data-testid="section-verify">
                            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-1.5">
                                <ClipboardDocumentCheckIcon className="h-4 w-4 text-[#1A4D2E]" />
                                What to verify yourself
                            </h3>
                            <ul className="mt-1 space-y-1">
                                {verifyList.map((item, idx) => (
                                    <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                        <span className="text-[#1A4D2E] mt-0.5">☐</span>{item}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {dataNotes.length > 0 && (
                        <ul className="text-xs text-[#9A9A9A] space-y-1 pt-2 border-t border-gray-100" data-testid="strategy-data-notes">
                            {dataNotes.map((note, idx) => (
                                <li key={idx}>{note}</li>
                            ))}
                        </ul>
                    )}
                </div>
            )}

            <CreditsUpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                creditsRemaining={creditsRemaining}
                feature="major strategy"
            />
        </div>
    );
};

export default MajorStrategySynthesis;
