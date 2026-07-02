import React, { useState, useEffect, useCallback } from 'react';
import {
    MapIcon,
    SparklesIcon,
    ArrowPathIcon,
    ExclamationTriangleIcon,
    CheckIcon
} from '@heroicons/react/24/outline';
import {
    getMajorMap,
    generateMajorMap,
    setIntendedMajors,
    checkCredits
} from '../../services/api';
import CreditsUpgradeModal from '../CreditsUpgradeModal';

// ============================================================================
// MAJOR MAP CARD (#284) — the Profile page's discovery artifact.
// Career-theme clusters generated from the student's OWN record (counselor
// inference, basis 'inference' — never school facts). Rules this card holds:
//   - Generation costs 1 credit, billed SERVER-side: no client deduction;
//     402 → CreditsUpgradeModal.
//   - Staleness (profile changed since generation) shows a banner and NEVER
//     auto-regenerates.
//   - "Set as my majors" persists up to 5 selected majors via
//     set-intended-majors (free).
// ============================================================================

const RELATION_BADGES = {
    core: { label: 'Core', className: 'bg-green-100 text-green-800 border border-green-200' },
    adjacent: { label: 'Adjacent', className: 'bg-blue-100 text-blue-800 border border-blue-200' },
    strategic_alternative: { label: 'Strategic alternative', className: 'bg-[#FCEEE8] text-[#C05838] border border-[#E8A090]' }
};

const MAX_SELECTED = 5;

// Client-side mirror of the server's readiness guard (grade + >=2 of
// {courses, extracurriculars, gpa_*}) so the empty state can coach instead
// of letting the CTA bounce off a 422.
export const mapReadiness = (profile) => {
    const p = profile || {};
    const missing = [];
    if (!p.grade && !p.grade_level) missing.push('grade');
    const present = [];
    if (Array.isArray(p.courses) && p.courses.length > 0) present.push('courses');
    if (Array.isArray(p.extracurriculars) && p.extracurriculars.length > 0) present.push('extracurriculars');
    if (Object.keys(p).some(k => k.startsWith('gpa_') && p[k])) present.push('gpa');
    if (present.length < 2) {
        ['courses', 'extracurriculars', 'gpa'].forEach(s => {
            if (!present.includes(s)) missing.push(s);
        });
    }
    return missing;
};

const MISSING_LABELS = {
    grade: 'your grade level',
    courses: 'your courses',
    extracurriculars: 'your activities',
    gpa: 'a GPA'
};

const MajorMapCard = ({ userEmail, profile = null }) => {
    const [map, setMap] = useState(null);
    const [stale, setStale] = useState(false);
    const [staleReasons, setStaleReasons] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [missing, setMissing] = useState(null); // server-confirmed 422 detail
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [creditsRemaining, setCreditsRemaining] = useState(0);
    const [selected, setSelected] = useState([]);
    const [savingMajors, setSavingMajors] = useState(false);
    const [savedNote, setSavedNote] = useState(null);

    const loadMap = useCallback(async () => {
        setLoading(true);
        const result = await getMajorMap(userEmail);
        if (result?.success) {
            setMap(result.map);
            setStale(Boolean(result.stale));
            setStaleReasons(result.stale_reasons || []);
        }
        setLoading(false);
    }, [userEmail]);

    useEffect(() => {
        if (userEmail) loadMap();
    }, [userEmail, loadMap]);

    const handleGenerate = async (force = false) => {
        setError(null);
        setMissing(null);
        setSavedNote(null);
        // Credit gate (reused fit UX): pre-check, then trust the server's 402.
        const credits = await checkCredits(userEmail, 1);
        if (credits?.has_credits !== true) {
            setCreditsRemaining(credits?.credits_remaining ?? 0);
            setShowUpgradeModal(true);
            return;
        }
        setGenerating(true);
        const result = await generateMajorMap(userEmail, force);
        setGenerating(false);
        if (result?.success) {
            setMap(result.map);
            setStale(false);
            setStaleReasons([]);
            setSelected([]);
        } else if (result?.insufficientCredits) {
            setCreditsRemaining(result.creditsRemaining ?? 0);
            setShowUpgradeModal(true);
        } else if (result?.profileIncomplete) {
            setMissing(result.missing || []);
        } else {
            setError(result?.error || 'Map generation failed — try again.');
        }
    };

    const toggleSelect = (name) => {
        setSavedNote(null);
        setSelected(prev => {
            if (prev.includes(name)) return prev.filter(n => n !== name);
            if (prev.length >= MAX_SELECTED) return prev;
            return [...prev, name];
        });
    };

    const handleSetMajors = async () => {
        if (selected.length === 0) return;
        setSavingMajors(true);
        const result = await setIntendedMajors(userEmail, selected);
        setSavingMajors(false);
        if (result?.success) {
            setSavedNote(`Saved as your intended majors: ${result.intended_majors.join(', ')}`);
            setSelected([]);
        } else {
            setError(result?.error || 'Could not save majors — try again.');
        }
    };

    const clientMissing = profile ? mapReadiness(profile) : null;
    const notReady = missing || (clientMissing && clientMissing.length > 0 ? clientMissing : null);

    if (loading) {
        return (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6" data-testid="major-map-loading">
                <div className="animate-pulse space-y-3">
                    <div className="h-5 bg-gray-200 rounded w-1/3" />
                    <div className="h-20 bg-gray-100 rounded" />
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6" data-testid="major-map-card">
            <div className="flex items-start justify-between gap-3 flex-wrap mb-1">
                <h2 className="font-bold text-gray-900 flex items-center gap-2">
                    <MapIcon className="h-5 w-5 text-[#1A4D2E]" />
                    Your Major Map
                </h2>
                {map && (
                    <span className="stratia-chip bg-purple-100 text-purple-700 border border-purple-200">
                        Stratia's read — inference, not school facts
                    </span>
                )}
            </div>

            {error && (
                <p className="text-sm text-red-600 mt-2" role="alert">{error}</p>
            )}

            {/* ---- Empty state (readiness-aware) ---- */}
            {!map && (
                <div className="mt-3">
                    {notReady ? (
                        <>
                            <p className="text-gray-700 text-sm">
                                Tell us a bit more first — the map is built from your own record.
                            </p>
                            <p className="text-sm text-gray-500 mt-1" data-testid="map-missing">
                                Still needed: {notReady.map(m => MISSING_LABELS[m] || m).join(', ')}.
                            </p>
                        </>
                    ) : (
                        <p className="text-gray-700 text-sm">
                            You've told us about your courses and activities. Let's turn that
                            into a map of majors worth considering.
                        </p>
                    )}
                    <button
                        onClick={() => handleGenerate(false)}
                        disabled={generating || Boolean(notReady)}
                        className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg text-sm font-medium hover:bg-[#143D24] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {generating
                            ? (<><ArrowPathIcon className="h-4 w-4 animate-spin" /> Mapping…</>)
                            : (<><SparklesIcon className="h-4 w-4" /> Map my majors — 1 credit</>)}
                    </button>
                </div>
            )}

            {/* ---- Staleness banner — informative, never auto-regenerates ---- */}
            {map && stale && (
                <div className="mt-3 bg-amber-50 border border-amber-300 rounded-lg p-3 flex items-start justify-between gap-3 flex-wrap" role="note" data-testid="map-stale-banner">
                    <div className="flex items-start gap-2">
                        <ExclamationTriangleIcon className="h-4 w-4 text-amber-700 mt-0.5 flex-shrink-0" />
                        <div>
                            <p className="text-sm text-amber-900 font-medium">
                                Your profile changed since this map — regenerate when ready.
                            </p>
                            {staleReasons.length > 0 && (
                                <p className="text-xs text-amber-800 mt-0.5">{staleReasons.join(' · ')}</p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={() => handleGenerate(true)}
                        disabled={generating}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-100 text-amber-900 border border-amber-300 hover:bg-amber-200 transition-colors disabled:opacity-50"
                    >
                        <ArrowPathIcon className={`h-3.5 w-3.5 ${generating ? 'animate-spin' : ''}`} />
                        Regenerate — 1 credit
                    </button>
                </div>
            )}

            {/* ---- Generated state: cluster cards ---- */}
            {map && (
                <div className="mt-4 space-y-4">
                    {(map.clusters || []).map((cluster, idx) => (
                        <div key={idx} className="border border-[#E0DED8] rounded-xl p-4" data-testid="map-cluster">
                            <h3 className="font-semibold text-gray-900">{cluster.theme}</h3>
                            {cluster.why_you && (
                                <p className="text-sm text-gray-700 mt-1">{cluster.why_you}</p>
                            )}
                            {(cluster.evidence || []).length > 0 && (
                                <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                                    <span className="text-xs text-[#6B6B6B]">Based on:</span>
                                    {cluster.evidence.map((ev, eIdx) => (
                                        <span key={eIdx} className="stratia-chip bg-[#F8F6F0] text-[#4A4A4A] border border-[#E0DED8]" data-testid="evidence-chip">
                                            {ev}
                                        </span>
                                    ))}
                                </div>
                            )}
                            <ul className="mt-3 space-y-2">
                                {(cluster.majors || []).map((major, mIdx) => {
                                    const badge = RELATION_BADGES[major.relation] || RELATION_BADGES.adjacent;
                                    const isSelected = selected.includes(major.name);
                                    return (
                                        <li key={mIdx} className="flex items-start gap-2 flex-wrap" data-testid="map-major">
                                            <button
                                                onClick={() => toggleSelect(major.name)}
                                                aria-pressed={isSelected}
                                                aria-label={`Select ${major.name}`}
                                                className={`stratia-chip transition-colors ${isSelected
                                                    ? 'bg-[#1A4D2E] text-white border border-[#1A4D2E]'
                                                    : 'bg-white text-[#2C2C2C] border border-[#E0DED8] hover:border-[#1A4D2E]'}`}
                                            >
                                                {isSelected && <CheckIcon className="h-3 w-3 inline mr-1" />}
                                                {major.name}
                                            </button>
                                            <span className={`stratia-chip ${badge.className}`}>{badge.label}</span>
                                            {major.why && (
                                                <span className="text-xs text-[#6B6B6B] mt-1">{major.why}</span>
                                            )}
                                            {major.watch_out && (
                                                <details className="w-full ml-1">
                                                    <summary className="text-xs text-amber-700 cursor-pointer select-none">
                                                        Watch out
                                                    </summary>
                                                    <p className="text-xs text-amber-800 mt-1">{major.watch_out}</p>
                                                </details>
                                            )}
                                        </li>
                                    );
                                })}
                            </ul>
                        </div>
                    ))}

                    {(map.questions_to_explore || []).length > 0 && (
                        <div className="border border-[#E0DED8] rounded-xl p-4 bg-[#F8F6F0]">
                            <h3 className="font-semibold text-gray-900 text-sm">Questions to explore next</h3>
                            <ul className="mt-2 space-y-1">
                                {map.questions_to_explore.map((q, idx) => (
                                    <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                        <span className="text-[#1A4D2E] mt-0.5">•</span>{q}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Set-as-my-majors action bar */}
                    <div className="flex items-center gap-3 flex-wrap pt-1">
                        <button
                            onClick={handleSetMajors}
                            disabled={selected.length === 0 || savingMajors}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg text-sm font-medium hover:bg-[#143D24] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {savingMajors ? 'Saving…' : `Set as my majors${selected.length ? ` (${selected.length})` : ''}`}
                        </button>
                        <span className="text-xs text-[#6B6B6B]">
                            Pick up to {MAX_SELECTED} majors from the map.
                        </span>
                        {savedNote && (
                            <span className="text-xs text-[#1A4D2E] font-medium" data-testid="majors-saved-note">
                                {savedNote}
                            </span>
                        )}
                    </div>
                </div>
            )}

            <CreditsUpgradeModal
                isOpen={showUpgradeModal}
                onClose={() => setShowUpgradeModal(false)}
                creditsRemaining={creditsRemaining}
                feature="major map"
            />
        </div>
    );
};

export default MajorMapCard;
