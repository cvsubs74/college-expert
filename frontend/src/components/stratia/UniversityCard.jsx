import React, { useState } from 'react';
import { MapPinIcon } from '@heroicons/react/24/outline';

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
 */
const UniversityCard = ({
    university,
    onViewAnalysis,
    onViewNotes,
    onOpenChat
}) => {
    const [activeAction, setActiveAction] = useState(null);

    const {
        university_name,
        location,
        fit_category = 'TARGET',
        match_score = 0,
        image_url,
        acceptance_rate,
        us_news_rank
    } = university || {};

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

    const actions = [
        { key: 'analysis', label: 'View Analysis', onClick: onViewAnalysis },
        { key: 'notes', label: 'Notes', onClick: onViewNotes },
        { key: 'chat', label: 'Chat', onClick: onOpenChat }
    ];

    return (
        <div className="stratia-card-outlined p-4 group animate-fade-up">
            <div className="flex items-center gap-4">
                {/* Left: Campus Image (Squircle) */}
                <div className="flex-shrink-0">
                    <div
                        className="squircle w-20 h-20 bg-gradient-to-br from-[#D6E8D5] to-[#FCEEE8] overflow-hidden"
                        style={{
                            backgroundImage: image_url ? `url(${image_url})` : undefined,
                            backgroundSize: 'cover',
                            backgroundPosition: 'center'
                        }}
                    >
                        {!image_url && (
                            <div className="w-full h-full flex items-center justify-center">
                                <span className="text-2xl font-serif font-bold text-[#1A4D2E]">
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

            {/* Action Buttons - Segmented Button Group */}
            <div className="mt-4 pt-4 border-t border-[#E0DED8] flex justify-end">
                <div className="stratia-segmented-group">
                    {actions.map((action) => (
                        <button
                            key={action.key}
                            className={`stratia-segment ${activeAction === action.key ? 'stratia-segment-active' : ''}`}
                            onClick={() => {
                                setActiveAction(action.key);
                                action.onClick?.(university);
                            }}
                        >
                            {action.label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default UniversityCard;
