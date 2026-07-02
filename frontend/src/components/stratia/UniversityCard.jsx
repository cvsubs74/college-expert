import React, { useState } from 'react';
import { MapPinIcon, TrashIcon, ChartBarIcon, PencilSquareIcon, ChatBubbleLeftRightIcon, AcademicCapIcon, ClockIcon, CheckCircleIcon, PaperAirplaneIcon, DocumentCheckIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import FitVintageChip from '../FitVintageChip';
import { fitUpdateAvailable, updateTooltip } from '../../utils/kbVintage';

/**
 * UniversityCard - Rich, interactive M3 card for university listings
 * 
 * Features:
 * - Squircle campus thumbnail
 * - Serif university name
 * - M3 AssistChips for fit category
 * - Circular progress match score
 * - SegmentedButtonGroup for actions
 * - M3 State Layer hover effects
 * - Remove button for paid plans
 * - Major dropdown persists via set-major-choice (free); recompute is a
 *   separate, explicit 1-credit action (never silent)
 */
const UniversityCard = ({
    university,
    onViewAnalysis,
    onViewNotes,
    onOpenChat,
    onEssayHelp,
    onUpdateFit,
    onRemove,
    onMajorChange,
    onRecomputeWithMajor,
    canRemove = false
}) => {
    const [isRemoving, setIsRemoving] = useState(false);
    const [isUpdatingFit, setIsUpdatingFit] = useState(false);
    const [updateFailed, setUpdateFailed] = useState(false);

    const {
        university_name,
        university_id,
        location,
        fit_category = 'TARGET',
        match_score = 0,
        image_url,
        logo_url,  // From API
        acceptance_rate,
        us_news_rank,
        selected_major,
        major_choice = null,        // per-school decision: {primary, backup, matched, ...}
        major_choice_note = null,   // transient server note (e.g. unmatched name)
        available_majors = [],
        application_status = null,  // planning, in_progress, submitted, decision_pending, decision
        kb_data_year = null,        // KB cycle year the saved fit was computed on
        kb_update = null,           // staleness entry from check-fit-recomputation
        fit_analysis = null
    } = university || {};

    // The student's current per-school major decision. major_choice.primary is
    // authoritative (persisted via set-major-choice); selected_major is the
    // legacy mirror kept for older list items.
    const currentMajor = major_choice?.primary || selected_major || '';

    // Persist immediately on change — saving the decision is free. Recomputing
    // the fit is a separate, explicit action below (never triggered silently).
    const handleMajorSelect = (e) => {
        const newMajor = e.target.value;
        if (newMajor && newMajor !== currentMajor && onMajorChange) {
            onMajorChange(university_id, newMajor);
        }
    };

    // The saved fit was computed for a different major than the current
    // decision → offer an explicit, clearly-priced recompute. Never automatic.
    const fitMajor = fit_analysis?.intended_major_used
        || fit_analysis?.major_strategy?.intended_major
        || null;
    const fitMajorMismatch = Boolean(
        onRecomputeWithMajor && currentMajor && fitMajor
        && fitMajor.trim().toLowerCase() !== currentMajor.trim().toLowerCase()
    );

    // The saved fit was computed on superseded KB data. The Fit Analysis
    // control becomes a split button: the green segment always opens the
    // CURRENT analysis; an attached amber segment recomputes against the new
    // KB data. The action lives on the button (not just a passive chip), while
    // viewing the existing analysis stays one click away.
    const updateAvailable = fitUpdateAvailable(kb_update);

    const handleUpdateClick = async () => {
        if (isUpdatingFit) return;
        setUpdateFailed(false);
        setIsUpdatingFit(true);
        try {
            // onUpdateFit recomputes the fit and opens the refreshed analysis;
            // on success this card unmounts, so we only reset state on failure.
            await onUpdateFit?.(university);
        } catch (err) {
            console.error('[UniversityCard] Fit update failed:', err);
            setIsUpdatingFit(false);
            setUpdateFailed(true);
        }
    };

    // Use logo_url (from API) or image_url as fallback
    const displayImage = logo_url || image_url;

    // Chip styles based on fit category
    const chipStyles = {
        SUPER_REACH: 'stratia-chip-reach',
        REACH: 'stratia-chip-reach',
        TARGET: 'stratia-chip-target',
        SAFETY: 'stratia-chip-safety'
    };

    const chipLabels = {
        SUPER_REACH: 'Super Reach',
        REACH: 'Reach',
        TARGET: 'Target',
        SAFETY: 'Safety'
    };

    // Calculate circular progress
    const circumference = 2 * Math.PI * 24; // radius = 24
    const strokeDashoffset = circumference - (match_score / 100) * circumference;

    // Get match score color based on percentage
    const getMatchColor = (score) => {
        if (score >= 70) return '#1A4D2E'; // Primary green
        if (score >= 40) return '#2D6B45'; // Light forest
        return '#C05838'; // Terracotta
    };

    return (
        <>
            <div className="stratia-card-outlined p-4 group animate-fade-up">
                <div className="flex items-center gap-4">
                    {/* Left: Campus Image (Squircle) */}
                    <div className="flex-shrink-0">
                        <div
                            className="squircle w-12 h-12 bg-gradient-to-br from-[#D6E8D5] to-[#FCEEE8] overflow-hidden"
                            style={{
                                backgroundImage: displayImage ? `url(${displayImage})` : undefined,
                                backgroundSize: 'cover',
                                backgroundPosition: 'center'
                            }}
                        >
                            {!displayImage && (
                                <div className="w-full h-full flex items-center justify-center">
                                    <span className="text-lg font-serif font-bold text-[#1A4D2E]">
                                        {university_name?.charAt(0) || 'U'}
                                    </span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Middle: University Info */}
                    <div className="flex-1 min-w-0">
                        {/* University Name - Serif */}
                        <h3 className="font-serif text-lg font-semibold text-[#2C2C2C] truncate group-hover:text-[#1A4D2E] transition-colors">
                            {university_name}
                        </h3>

                        {/* Location */}
                        <div className="flex items-center gap-1 text-sm text-[#4A4A4A] mt-0.5">
                            <MapPinIcon className="w-4 h-4 flex-shrink-0" />
                            <span className="truncate">{location || 'Location N/A'}</span>
                        </div>

                        {/* Tags */}
                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                            {/* Fit Category Chip */}
                            <span className={`stratia-chip ${chipStyles[fit_category] || chipStyles.TARGET}`}>
                                {chipLabels[fit_category] || 'Target'}
                            </span>

                            {/* Fit vintage — which cycle's data produced the fit.
                                vintageOnly: the "update available" CTA lives on
                                the Fit Analysis button below, so the chip just
                                states the data cycle here. */}
                            <FitVintageChip fit={{ kb_data_year }} kbUpdate={kb_update} vintageOnly />

                            {/* Application Status Badge */}
                            {application_status && (
                                <span className={`stratia-chip flex items-center gap-1 ${application_status === 'decision' ? 'bg-emerald-100 text-emerald-700 border border-emerald-300' :
                                        application_status === 'submitted' ? 'bg-blue-100 text-blue-700 border border-blue-300' :
                                            application_status === 'decision_pending' ? 'bg-purple-100 text-purple-700 border border-purple-300' :
                                                application_status === 'in_progress' ? 'bg-amber-100 text-amber-700 border border-amber-300' :
                                                    'bg-gray-100 text-gray-600 border border-gray-300'
                                    }`}>
                                    {application_status === 'decision' && <CheckCircleIcon className="w-3.5 h-3.5" />}
                                    {application_status === 'submitted' && <PaperAirplaneIcon className="w-3.5 h-3.5" />}
                                    {application_status === 'decision_pending' && <DocumentCheckIcon className="w-3.5 h-3.5" />}
                                    {application_status === 'in_progress' && <ClockIcon className="w-3.5 h-3.5" />}
                                    {application_status === 'planning' && <ClockIcon className="w-3.5 h-3.5" />}
                                    {application_status === 'decision' ? 'Decision' :
                                        application_status === 'submitted' ? 'Submitted' :
                                            application_status === 'decision_pending' ? 'Awaiting Decision' :
                                                application_status === 'in_progress' ? 'In Progress' :
                                                    'Planning'}
                                </span>
                            )}

                            {/* Additional info chips */}
                            {us_news_rank && (
                                <span className="stratia-chip bg-[#F8F6F0] text-[#4A4A4A] border border-[#E0DED8]">
                                    #{us_news_rank} US News
                                </span>
                            )}
                            {acceptance_rate && (
                                <span className="stratia-chip bg-[#F8F6F0] text-[#4A4A4A] border border-[#E0DED8]">
                                    {acceptance_rate}% Accept
                                </span>
                            )}
                        </div>

                        {/* Major Selection Dropdown — persists on change (free) */}
                        {available_majors.length > 0 && onMajorChange && (
                            <div className="flex items-center gap-2 mt-2">
                                <AcademicCapIcon className="w-4 h-4 text-[#4A7C59]" />
                                <select
                                    value={currentMajor}
                                    onChange={handleMajorSelect}
                                    aria-label="Intended major"
                                    className="text-sm border border-[#E0DED8] rounded-lg px-2 py-1 bg-white text-[#2C2C2C] focus:ring-2 focus:ring-[#4A7C59] focus:border-[#4A7C59] max-w-[200px]"
                                >
                                    <option value="">Select intended major...</option>
                                    {/* Unmatched names are stored as given — keep them selectable */}
                                    {currentMajor && !available_majors.includes(currentMajor) && (
                                        <option value={currentMajor}>{currentMajor}</option>
                                    )}
                                    {available_majors.map((major, idx) => (
                                        <option key={idx} value={major}>{major}</option>
                                    ))}
                                </select>
                                {currentMajor && major_choice?.matched !== false && (
                                    <span className="text-xs text-[#6B6B6B]">✓</span>
                                )}
                                {/* The saved name couldn't be bound to the KB's official
                                    major list — stored as given, flagged, never rewritten. */}
                                {major_choice?.matched === false && (
                                    <span className="relative group/unmatched" data-testid="major-unmatched-dot">
                                        <span className="block w-2.5 h-2.5 rounded-full bg-amber-500 border border-amber-600 cursor-help" aria-label="Major name not matched" />
                                        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover/unmatched:opacity-100 transition-opacity pointer-events-none whitespace-normal w-56 z-10">
                                            We couldn't match this name to {university_name || 'this school'}'s official major list{major_choice_note ? ` — ${major_choice_note}` : ''}
                                        </span>
                                    </span>
                                )}
                            </div>
                        )}

                        {/* Impacted-major callout (#284) — deterministic, zero LLM.
                            Rendered only when set-major-choice stamped door_flags
                            with the KB's structural capped_door signal. */}
                        {currentMajor && major_choice?.door_flags?.entry_risk === 'capped_door' && (
                            <div
                                className="mt-2 bg-amber-50 border border-amber-300 rounded-lg px-3 py-2 text-xs text-amber-900"
                                role="note"
                                data-testid="impacted-major-callout"
                            >
                                <span className="font-semibold">Heads up:</span> {currentMajor} at {university_name || 'this school'} is
                                direct-admit only — if you're not admitted to it directly, you can't
                                switch in later. Your essays must make the case for this major.
                            </div>
                        )}

                        {/* Explicit recompute offer — the saved fit was computed for a
                            different major. Never recompute silently; 1 credit. */}
                        {fitMajorMismatch && (
                            <button
                                onClick={() => onRecomputeWithMajor(university, currentMajor)}
                                className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-300 hover:bg-amber-100 transition-colors"
                            >
                                <ArrowPathIcon className="w-3.5 h-3.5" />
                                Fit was computed for {fitMajor} — Recompute with {currentMajor}? (1 credit)
                            </button>
                        )}
                    </div>

                    {/* Right: Match Score & Actions */}
                    <div className="flex-shrink-0 flex flex-col items-end gap-3">
                        {/* Circular Match Score */}
                        <div className="match-circle">
                            <svg width="60" height="60" viewBox="0 0 60 60">
                                {/* Track */}
                                <circle
                                    className="match-circle-track"
                                    cx="30"
                                    cy="30"
                                    r="24"
                                />
                                {/* Progress */}
                                <circle
                                    className="match-circle-progress"
                                    cx="30"
                                    cy="30"
                                    r="24"
                                    style={{
                                        strokeDasharray: circumference,
                                        strokeDashoffset: strokeDashoffset,
                                        stroke: getMatchColor(match_score)
                                    }}
                                />
                            </svg>
                            <div
                                className="match-circle-text"
                                style={{ color: getMatchColor(match_score) }}
                            >
                                {match_score}%
                            </div>
                        </div>
                        <span className="text-xs text-[#6B6B6B] font-sans">Match</span>
                    </div>
                </div>

                {/* Action Buttons - Colored Buttons with Icons and Tooltips */}
                <div className="mt-4 pt-4 border-t border-[#E0DED8] flex justify-between items-center">
                    {/* Action Buttons - Colored with Icons & Tooltips */}
                    <div className="flex items-center gap-2">
                        {/* Fit Analysis — split control. Green segment always
                            opens the CURRENT analysis; when the fit is stale an
                            attached amber segment recomputes against new KB data. */}
                        <div className="relative">
                            <div className="flex items-stretch rounded-lg shadow-sm">
                                {/* View segment — always available */}
                                <div className="relative group/view">
                                    <button
                                        onClick={() => onViewAnalysis?.(university)}
                                        aria-label="View fit analysis"
                                        className={`h-full px-3 py-2 bg-[#4A7C59] text-white hover:bg-[#3D6B4A] transition-all flex items-center gap-2 ${updateAvailable ? 'rounded-l-lg' : 'rounded-lg'}`}
                                    >
                                        <ChartBarIcon className="h-5 w-5" />
                                        <span className="text-sm font-medium">Fit Analysis</span>
                                    </button>
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover/view:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                        {updateAvailable ? 'View your current fit analysis' : 'View detailed fit analysis and recommendations'}
                                        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                                    </div>
                                </div>

                                {/* Update segment — only when the fit is stale */}
                                {updateAvailable && (
                                    <div className="relative group/update">
                                        <button
                                            onClick={handleUpdateClick}
                                            disabled={isUpdatingFit}
                                            aria-label="Update fit analysis with new data"
                                            className="h-full px-2.5 py-2 bg-[#1A4D2E] text-white hover:bg-[#143D24] rounded-r-lg border-l border-white/20 transition-all flex items-center gap-1.5 disabled:cursor-wait"
                                        >
                                            <ArrowPathIcon className={`h-5 w-5 ${isUpdatingFit ? 'animate-spin' : ''}`} />
                                            {isUpdatingFit && <span className="text-sm font-medium">Updating…</span>}
                                        </button>
                                        {/* Pulsing terracotta "update available" dot */}
                                        {!isUpdatingFit && (
                                            <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5" aria-hidden="true">
                                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#C05838] opacity-75"></span>
                                                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#C05838] border border-white"></span>
                                            </span>
                                        )}
                                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover/update:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                            {updateTooltip(kb_update)}
                                            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                                        </div>
                                    </div>
                                )}
                            </div>
                            {updateFailed && (
                                <p className="absolute top-full left-0 mt-1 text-[11px] text-red-600 whitespace-nowrap" role="alert">
                                    Update failed — try again.
                                </p>
                            )}
                        </div>

                        {/* Essay Help Button */}
                        {onEssayHelp && (
                            <div className="relative group/tooltip">
                                <button
                                    onClick={() => onEssayHelp?.(university)}
                                    className="px-3 py-2 bg-amber-500/80 text-white hover:bg-amber-600/80 rounded-lg transition-all shadow-sm flex items-center gap-2"
                                >
                                    <PencilSquareIcon className="h-5 w-5" />
                                    <span className="text-sm font-medium">Essay Help</span>
                                </button>
                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                    Get help with supplemental essays
                                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                                </div>
                            </div>
                        )}

                        {/* Chat Button */}
                        {onOpenChat && (
                            <div className="relative group/tooltip">
                                <button
                                    onClick={() => onOpenChat?.(university)}
                                    className="px-3 py-2 bg-blue-500/80 text-white hover:bg-blue-600/80 rounded-lg transition-all shadow-sm flex items-center gap-2"
                                >
                                    <ChatBubbleLeftRightIcon className="h-5 w-5" />
                                    <span className="text-sm font-medium">Chat</span>
                                </button>
                                {/* Tooltip */}
                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                    Ask AI questions about this university
                                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Remove Button (paid plans only) - Right side, single click */}
                    {canRemove && onRemove && (
                        <button
                            onClick={() => onRemove(university)}
                            className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-all"
                            title="Remove from list"
                        >
                            <TrashIcon className="w-5 h-5" />
                        </button>
                    )}
                </div>
            </div>
        </>
    );
};

export default UniversityCard;
