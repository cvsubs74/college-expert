import React, { useState } from 'react';
import { MapPinIcon, TrashIcon, ChartBarIcon, PencilSquareIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

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
 */
const UniversityCard = ({
    university,
    onViewAnalysis,
    onViewNotes,
    onOpenChat,
    onEssayHelp,
    onRemove,
    canRemove = false
}) => {
    const [isRemoving, setIsRemoving] = useState(false);

    const {
        university_name,
        location,
        fit_category = 'TARGET',
        match_score = 0,
        image_url,
        logo_url,  // From API
        acceptance_rate,
        us_news_rank
    } = university || {};

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
                    <div className="flex items-center gap-2 mt-2">
                        {/* Fit Category Chip */}
                        <span className={`stratia-chip ${chipStyles[fit_category] || chipStyles.TARGET}`}>
                            {chipLabels[fit_category] || 'Target'}
                        </span>

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
                    {/* Fit Analysis Button */}
                    <div className="relative group/tooltip">
                        <button
                            onClick={() => onViewAnalysis?.(university)}
                            className="px-3 py-2 bg-[#1A4D2E] text-white hover:bg-[#2D6B45] rounded-lg transition-all shadow-sm flex items-center gap-2"
                        >
                            <ChartBarIcon className="h-5 w-5" />
                            <span className="text-sm font-medium">Fit Analysis</span>
                        </button>
                        {/* Tooltip */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg opacity-0 group-hover/tooltip:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                            View detailed fit analysis and recommendations
                            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
                        </div>
                    </div>

                    {/* Essay Help Button */}
                    {onEssayHelp && (
                        <div className="relative group/tooltip">
                            <button
                                onClick={() => onEssayHelp?.(university)}
                                className="px-3 py-2 bg-amber-600 text-white hover:bg-amber-700 rounded-lg transition-all shadow-sm flex items-center gap-2"
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
                                className="px-3 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-lg transition-all shadow-sm flex items-center gap-2"
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
    );
};

export default UniversityCard;
