import React from 'react';
import {
    ChartBarIcon,
    AcademicCapIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    RocketLaunchIcon,
    MapPinIcon,
    StarIcon,
    ArrowTrendingUpIcon
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid';

/**
 * FitInfographicView - Renders structured fit analysis data as a beautiful infographic
 * This replaces AI-generated images with a native React component for perfect text rendering
 */
const FitInfographicView = ({ data, onClose }) => {
    if (!data) return null;

    const {
        title,
        subtitle,
        themeColor,
        matchScore,
        fitCategory,
        explanation,
        universityInfo,
        strengths,
        improvements,
        actionPlan,
        gapAnalysis,
        conclusion
    } = data;

    // Theme color mapping
    const themeColors = {
        emerald: {
            bg: 'bg-emerald-500',
            light: 'bg-emerald-50',
            text: 'text-emerald-700',
            border: 'border-emerald-200',
            gradient: 'from-emerald-500 to-green-600'
        },
        amber: {
            bg: 'bg-amber-500',
            light: 'bg-amber-50',
            text: 'text-amber-700',
            border: 'border-amber-200',
            gradient: 'from-amber-500 to-orange-500'
        },
        orange: {
            bg: 'bg-orange-500',
            light: 'bg-orange-50',
            text: 'text-orange-700',
            border: 'border-orange-200',
            gradient: 'from-orange-500 to-red-500'
        },
        rose: {
            bg: 'bg-rose-500',
            light: 'bg-rose-50',
            text: 'text-rose-700',
            border: 'border-rose-200',
            gradient: 'from-rose-500 to-red-600'
        }
    };

    const theme = themeColors[themeColor] || themeColors.amber;

    // Fit category badge colors
    const categoryColors = {
        SAFETY: 'bg-emerald-500 text-white',
        TARGET: 'bg-amber-500 text-white',
        REACH: 'bg-orange-500 text-white',
        SUPER_REACH: 'bg-rose-500 text-white'
    };

    const ScoreGauge = ({ score }) => {
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (score / 100) * circumference;

        return (
            <div className="relative w-32 h-32">
                <svg className="w-full h-full transform -rotate-90">
                    <circle
                        cx="64"
                        cy="64"
                        r="45"
                        fill="none"
                        stroke="#e5e7eb"
                        strokeWidth="10"
                    />
                    <circle
                        cx="64"
                        cy="64"
                        r="45"
                        fill="none"
                        stroke="url(#scoreGradient)"
                        strokeWidth="10"
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        strokeLinecap="round"
                    />
                    <defs>
                        <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#f59e0b" />
                            <stop offset="100%" stopColor="#ea580c" />
                        </linearGradient>
                    </defs>
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-3xl font-bold text-gray-800">{score}%</span>
                </div>
            </div>
        );
    };

    const FactorBar = ({ factor, isStrength }) => {
        const barColor = isStrength ? 'bg-emerald-500' : 'bg-orange-500';
        const bgColor = isStrength ? 'bg-emerald-100' : 'bg-orange-100';

        return (
            <div className="mb-3">
                <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{factor.name}</span>
                    <span className="text-gray-500">{factor.score}/{factor.maxScore}</span>
                </div>
                <div className={`h-2 rounded-full ${bgColor}`}>
                    <div
                        className={`h-full rounded-full ${barColor} transition-all duration-500`}
                        style={{ width: `${factor.percentage}%` }}
                    />
                </div>
            </div>
        );
    };

    return (
        <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className={`bg-gradient-to-r ${theme.gradient} text-white p-6`}>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold">{title}</h1>
                        <p className="text-white/80">{subtitle}</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <ScoreGauge score={matchScore} />
                        <span className={`px-4 py-2 rounded-full font-bold text-sm ${categoryColors[fitCategory] || 'bg-gray-500'}`}>
                            {fitCategory?.replace('_', ' ')}
                        </span>
                    </div>
                </div>
            </div>

            {/* University Info Bar */}
            {universityInfo && (
                <div className="bg-gray-50 border-b border-gray-200 px-6 py-3">
                    <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                        <span className="font-semibold text-gray-800">{universityInfo.name}</span>
                        {universityInfo.location && (
                            <span className="flex items-center gap-1">
                                <MapPinIcon className="w-4 h-4" />
                                {universityInfo.location}
                            </span>
                        )}
                        {universityInfo.acceptanceRate && universityInfo.acceptanceRate !== 'N/A' && (
                            <span className="flex items-center gap-1">
                                <ChartBarIcon className="w-4 h-4" />
                                {universityInfo.acceptanceRate}% acceptance
                            </span>
                        )}
                        {universityInfo.usNewsRank && universityInfo.usNewsRank !== 'N/A' && (
                            <span className="flex items-center gap-1">
                                <StarIcon className="w-4 h-4" />
                                #{universityInfo.usNewsRank} US News
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Main Content Grid */}
            <div className="grid md:grid-cols-3 gap-0">
                {/* Strengths Column */}
                <div className="p-5 border-r border-gray-200">
                    <div className="flex items-center gap-2 mb-4">
                        <div className="p-2 bg-emerald-100 rounded-lg">
                            <CheckCircleSolid className="w-5 h-5 text-emerald-600" />
                        </div>
                        <h3 className="font-bold text-gray-800">Your Strengths</h3>
                    </div>

                    {strengths && strengths.length > 0 ? (
                        strengths.map((strength, idx) => (
                            <div key={idx} className="mb-4">
                                <FactorBar factor={strength} isStrength={true} />
                                {strength.detail && (
                                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{strength.detail}</p>
                                )}
                            </div>
                        ))
                    ) : (
                        <p className="text-gray-500 text-sm">Building your strengths...</p>
                    )}

                    {gapAnalysis?.studentStrengths && gapAnalysis.studentStrengths.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-gray-100">
                            <p className="text-xs font-medium text-emerald-700 mb-2">Key Highlights:</p>
                            <ul className="space-y-1">
                                {gapAnalysis.studentStrengths.slice(0, 3).map((s, i) => (
                                    <li key={i} className="text-xs text-gray-600 flex items-start gap-1">
                                        <CheckCircleIcon className="w-3 h-3 text-emerald-500 mt-0.5 flex-shrink-0" />
                                        <span>{s}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>

                {/* Areas for Improvement Column */}
                <div className="p-5 border-r border-gray-200 bg-orange-50/30">
                    <div className="flex items-center gap-2 mb-4">
                        <div className="p-2 bg-orange-100 rounded-lg">
                            <ExclamationTriangleIcon className="w-5 h-5 text-orange-600" />
                        </div>
                        <h3 className="font-bold text-gray-800">Areas to Improve</h3>
                    </div>

                    {improvements && improvements.length > 0 ? (
                        improvements.map((imp, idx) => (
                            <div key={idx} className="mb-4">
                                <FactorBar factor={imp} isStrength={false} />
                                {imp.detail && (
                                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{imp.detail}</p>
                                )}
                            </div>
                        ))
                    ) : (
                        <p className="text-gray-500 text-sm">No major gaps identified!</p>
                    )}

                    {gapAnalysis?.primaryGap && (
                        <div className="mt-4 pt-4 border-t border-orange-100">
                            <p className="text-xs font-medium text-orange-700 mb-1">Primary Focus:</p>
                            <p className="text-xs text-gray-600">{gapAnalysis.primaryGap}</p>
                        </div>
                    )}
                </div>

                {/* Action Plan Column */}
                <div className="p-5 bg-blue-50/30">
                    <div className="flex items-center gap-2 mb-4">
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <RocketLaunchIcon className="w-5 h-5 text-blue-600" />
                        </div>
                        <h3 className="font-bold text-gray-800">Action Plan</h3>
                    </div>

                    {actionPlan && actionPlan.length > 0 ? (
                        <div className="space-y-4">
                            {actionPlan.map((step, idx) => (
                                <div key={idx} className="relative pl-6">
                                    <div className="absolute left-0 top-0 w-5 h-5 rounded-full bg-blue-500 text-white text-xs flex items-center justify-center font-bold">
                                        {step.step}
                                    </div>
                                    <div>
                                        <p className="text-sm text-gray-700 font-medium leading-tight">
                                            {step.action.length > 150 ? step.action.substring(0, 150) + '...' : step.action}
                                        </p>
                                        {step.timeline && (
                                            <span className="inline-block mt-1 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                                                {step.timeline}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-gray-500 text-sm">Action plan loading...</p>
                    )}
                </div>
            </div>

            {/* Conclusion Footer */}
            {conclusion && (
                <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
                    <div className="flex items-start gap-3">
                        <ArrowTrendingUpIcon className="w-5 h-5 text-gray-400 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-600 leading-relaxed">{conclusion}</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FitInfographicView;
