import React, { useState, useEffect, useCallback } from 'react';
import {
    AcademicCapIcon,
    SparklesIcon,
    ArrowPathIcon,
    ArrowLeftIcon,
    ExclamationTriangleIcon,
    CheckBadgeIcon
} from '@heroicons/react/24/outline';
import {
    getCollegeMajorChances,
    rankCollegeMajors,
    checkCredits
} from '../../services/api';
import CreditsUpgradeModal from '../CreditsUpgradeModal';

// ============================================================================
// MAJOR CHANCES VIEW (#302) — per-college view of the majors THIS school
// actually offers that fit the student, ranked into likelihood TIERS
// (Strong / Possible / Reach / Long shot) with a rationale each. Rules:
//   - Likelihood is a TIER, never a fabricated percentage (we lack verified
//     per-major admit rates). A reported rate shows ONLY where the KB has one,
//     labeled "reported (unverified)".
//   - Every rationale is counselor judgment (basis inference) — labeled
//     "Stratia's read". capped_door majors carry the door-lock caveat.
//   - Generation costs 1 credit, billed SERVER-side: no client deduction;
//     hasCredits gate → CreditsUpgradeModal, 402 → modal.
//   - A KB miss ({ranking: null, gaps}) renders honestly: no ranking, no charge.
//   - A stale chip appears when the KB has newer data than the ranking.
// Opened in-place from the Launchpad UniversityCard (same pattern as
// FitAnalysisPage), so it takes an onBack.
// ============================================================================

const ENTRY_PATH_BADGES = {
    direct_admit: { label: 'Direct admit', className: 'bg-green-100 text-green-800 border border-green-200' },
    pre_major: { label: 'Pre-major', className: 'bg-blue-100 text-blue-800 border border-blue-200' },
    secondary_application: { label: 'Secondary application', className: 'bg-orange-100 text-orange-800 border border-orange-200' },
    open_declaration: { label: 'Open declaration', className: 'bg-teal-100 text-teal-800 border border-teal-200' }
};

const TIER_SECTIONS = [
    { key: 'strong', title: 'Strong match', className: 'bg-green-100 text-green-800 border border-green-200' },
    { key: 'possible', title: 'Possible', className: 'bg-blue-100 text-blue-800 border border-blue-200' },
    { key: 'reach', title: 'Reach', className: 'bg-amber-100 text-amber-800 border border-amber-300' },
    { key: 'long_shot', title: 'Long shot', className: 'bg-[#FCEEE8] text-[#C05838] border border-[#E8A090]' }
];

const InferenceChip = () => (
    <span className="stratia-chip bg-purple-100 text-purple-700 border border-purple-200 whitespace-nowrap">
        Stratia's read — inference
    </span>
);

// Hedged rendering for the KB's reported rate — never a fabricated number.
const formatReportedRate = (reportedRate) => {
    if (!reportedRate || reportedRate.value == null) return null;
    const value = String(reportedRate.value).replace(/%\s*$/, '');
    return `Reported ~${value}% — ${reportedRate.label || 'reported (unverified)'}`;
};

const MajorChanceRow = ({ major }) => {
    const pathBadge = ENTRY_PATH_BADGES[major.entry_path];
    const reportedLine = formatReportedRate(major.reported_rate);
    return (
        <li className="py-3 border-b border-[#E0DED8] last:border-b-0" data-testid="chances-major-row">
            <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-[#2C2C2C]">{major.name}</span>
                    {major.college && (
                        <span className="text-xs text-[#6B6B6B]">{major.college}</span>
                    )}
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                    {pathBadge && (
                        <span className={`stratia-chip ${pathBadge.className}`}>{pathBadge.label}</span>
                    )}
                    {major.entry_risk === 'capped_door' && (
                        <span className="stratia-chip bg-red-100 text-red-700 border border-red-200">
                            Door locks
                        </span>
                    )}
                    {major.entry_risk === 'elevated' && (
                        <span className="text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                            Elevated entry risk
                        </span>
                    )}
                </div>
            </div>
            {major.rationale && (
                <div className="flex items-start gap-2 mt-1.5 flex-wrap">
                    <InferenceChip />
                    <p className="text-sm text-gray-700 flex-1 min-w-[200px]">{major.rationale}</p>
                </div>
            )}
            {reportedLine && (
                <p className="mt-1.5 text-xs text-[#9A9A9A] italic" data-testid="chances-reported-rate">
                    {reportedLine}
                </p>
            )}
        </li>
    );
};

const MajorChancesView = ({ userEmail, universityId, universityName, onBack }) => {
    const [ranking, setRanking] = useState(null);
    const [stale, setStale] = useState(false);
    const [currentKbYear, setCurrentKbYear] = useState(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [gaps, setGaps] = useState(null); // KB-miss result — honest, unbilled
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [creditsRemaining, setCreditsRemaining] = useState(0);

    const loadRanking = useCallback(async () => {
        setLoading(true);
        const result = await getCollegeMajorChances(userEmail, universityId);
        if (result?.success) {
            setRanking(result.ranking);
            setStale(Boolean(result.stale));
            setCurrentKbYear(result.current_kb_year ?? null);
        }
        setLoading(false);
    }, [userEmail, universityId]);

    useEffect(() => {
        if (userEmail && universityId) loadRanking();
    }, [userEmail, universityId, loadRanking]);

    const handleGenerate = async () => {
        setError(null);
        setGaps(null);
        const credits = await checkCredits(userEmail, 1);
        if (credits?.error === 'credits_read_failed' || credits?.retryable) {
            // #298: a ledger read blip is our outage, not their balance — never
            // show the upsell for it. The server 503s the same way.
            setError('Credits are temporarily unavailable — please try again in a moment.');
            return;
        }
        if (credits?.has_credits !== true) {
            setCreditsRemaining(credits?.credits_remaining ?? 0);
            setShowUpgradeModal(true);
            return;
        }
        setGenerating(true);
        const result = await rankCollegeMajors(userEmail, universityId);
        setGenerating(false);
        if (result?.success && result.ranking) {
            setRanking(result.ranking);
            setStale(false);
        } else if (result?.success && result.ranking === null) {
            // Never-charged KB miss — render it honestly, never fill it in.
            setGaps(result.gaps || []);
        } else if (result?.insufficientCredits) {
            setCreditsRemaining(result.creditsRemaining ?? 0);
            setShowUpgradeModal(true);
        } else if (result?.retryable || result?.error === 'credits_unavailable_retry') {
            // #305 review F5: a server-side ledger blip (503) is our outage —
            // friendly retry copy, never the raw token or the upsell.
            setError('Credits are temporarily unavailable — please try again in a moment.');
        } else {
            setError(result?.error || 'Ranking generation failed — try again.');
        }
    };

    const tiers = ranking?.tiers || {};
    const rankedCount = TIER_SECTIONS.reduce((n, t) => n + (tiers[t.key]?.length || 0), 0);
    const dataNotes = ranking?.data_notes || [];
    const verified = ranking?.verification_status === 'verified';

    return (
        <div className="max-w-3xl mx-auto p-4 sm:p-6" data-testid="major-chances-view">
            {onBack && (
                <button
                    onClick={onBack}
                    className="inline-flex items-center gap-1.5 text-sm text-[#4A4A4A] hover:text-[#1A4D2E] mb-4"
                >
                    <ArrowLeftIcon className="h-4 w-4" /> Back to schools
                </button>
            )}

            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                    <h2 className="font-bold text-gray-900 flex items-center gap-2">
                        <AcademicCapIcon className="h-5 w-5 text-[#1A4D2E]" />
                        Major Chances{universityName ? ` — ${universityName}` : ''}
                    </h2>
                    <div className="flex items-center gap-2">
                        {ranking && (
                            <span
                                className={`stratia-chip ${verified
                                    ? 'bg-green-100 text-green-800 border border-green-200'
                                    : 'bg-amber-100 text-amber-800 border border-amber-300'}`}
                                data-testid="chances-verification-chip"
                            >
                                {verified
                                    ? (<><CheckBadgeIcon className="h-3.5 w-3.5 inline mr-1" />Verified KB data</>)
                                    : 'Reported (unverified)'}
                            </span>
                        )}
                        {ranking && stale && (
                            <span className="stratia-chip bg-amber-100 text-amber-800 border border-amber-300" data-testid="chances-stale-chip">
                                Built on {ranking.kb_data_year} data{currentKbYear ? ` — ${currentKbYear} available` : ''}
                            </span>
                        )}
                        {/* #305 review F4: a stale ranking is actionable, not just flagged. */}
                        {ranking && stale && (
                            <button
                                onClick={handleGenerate}
                                disabled={generating}
                                className="stratia-chip bg-[#1A4D2E] text-white border border-[#1A4D2E] hover:bg-[#143D24] disabled:opacity-50 inline-flex items-center gap-1"
                                data-testid="chances-rerank"
                            >
                                {generating
                                    ? (<><ArrowPathIcon className="h-3.5 w-3.5 animate-spin" /> Re-ranking…</>)
                                    : (<><ArrowPathIcon className="h-3.5 w-3.5" /> Re-rank — 1 credit</>)}
                            </button>
                        )}
                    </div>
                </div>

                {error && <p className="text-sm text-red-600 mt-1" role="alert">{error}</p>}

                {loading ? (
                    <div className="animate-pulse space-y-3 mt-3" data-testid="chances-loading">
                        <div className="h-5 bg-gray-200 rounded w-1/3" />
                        <div className="h-16 bg-gray-100 rounded" />
                    </div>
                ) : (
                    <>
                        {/* ---- KB miss: honest, unbilled ---- */}
                        {gaps && (
                            <div className="mt-2 bg-[#F8F6F0] border border-[#E0DED8] rounded-lg p-4" data-testid="chances-gaps">
                                <p className="text-sm text-gray-700">
                                    We don't have major data for {universityName || 'this school'} yet —
                                    you weren't charged. We've logged the gap and it's now on our
                                    collection priority list.
                                </p>
                            </div>
                        )}

                        {/* ---- Empty state: explicit, priced CTA ---- */}
                        {!ranking && !gaps && (
                            <div className="mt-2">
                                <p className="text-sm text-gray-700">
                                    See which of {universityName || 'this school'}'s majors fit your record —
                                    ranked into Strong / Possible / Reach / Long shot, with a rationale for each.
                                    Likelihood is a counselor read, not a fabricated percentage.
                                </p>
                                <button
                                    onClick={handleGenerate}
                                    disabled={generating}
                                    className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg text-sm font-medium hover:bg-[#143D24] transition-colors disabled:opacity-50"
                                    data-testid="chances-generate-cta"
                                >
                                    {generating
                                        ? (<><ArrowPathIcon className="h-4 w-4 animate-spin" /> Ranking…</>)
                                        : (<><SparklesIcon className="h-4 w-4" /> Rank my chances — 1 credit</>)}
                                </button>
                            </div>
                        )}

                        {/* ---- Ranking: tiered sections ---- */}
                        {ranking && rankedCount === 0 && (
                            <div className="mt-2 bg-[#F8F6F0] border border-[#E0DED8] rounded-lg p-4" data-testid="chances-empty-ranking">
                                <p className="text-sm text-gray-700">
                                    {ranking.note || 'No majors at this school stood out as a fit right now.'}
                                </p>
                            </div>
                        )}

                        {ranking && rankedCount > 0 && (
                            <div className="mt-3 space-y-5">
                                {TIER_SECTIONS.map(({ key, title, className }) => {
                                    const majors = tiers[key] || [];
                                    if (majors.length === 0) return null;
                                    return (
                                        <div key={key} data-testid={`tier-${key}`}>
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={`stratia-chip ${className}`}>{title}</span>
                                                <span className="text-xs text-[#9A9A9A]">{majors.length}</span>
                                            </div>
                                            <ul className="border border-[#E0DED8] rounded-xl px-4">
                                                {majors.map((major, idx) => (
                                                    <MajorChanceRow key={idx} major={major} />
                                                ))}
                                            </ul>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* ---- data_notes footer ---- */}
                        {ranking && dataNotes.length > 0 && (
                            <ul className="text-xs text-[#9A9A9A] space-y-1 pt-4 mt-4 border-t border-gray-100" data-testid="chances-data-notes">
                                {dataNotes.map((note, idx) => (
                                    <li key={idx}>{note}</li>
                                ))}
                            </ul>
                        )}
                    </>
                )}
            </div>

            <CreditsUpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                creditsRemaining={creditsRemaining}
                feature="major chances"
            />
        </div>
    );
};

export default MajorChancesView;
