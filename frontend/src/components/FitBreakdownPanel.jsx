import React, { useState } from 'react';
import {
    ChartBarIcon,
    SparklesIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    InformationCircleIcon
} from '@heroicons/react/24/outline';

/**
 * FitBreakdownPanel - Reusable component to show fit analysis breakdown
 * Can be used in UniversityExplorer and MyLaunchpad
 */
const FitBreakdownPanel = ({
    fitAnalysis,
    universityName = 'University',
    compact = false,
    defaultExpanded = false
}) => {
    const [isExpanded, setIsExpanded] = useState(defaultExpanded);

    if (!fitAnalysis) return null;

    const fitCategory = fitAnalysis.fit_category || 'TARGET';
    const matchScore = fitAnalysis.match_percentage || fitAnalysis.match_score || 50;
    const factors = fitAnalysis.factors || [];
    const recommendations = fitAnalysis.recommendations || [];

    // Category config
    const categoryConfig = {
        SAFETY: {
            label: 'Safety',
            emoji: '🛡️',
            color: 'green',
            bgColor: 'bg-green-50',
            borderColor: 'border-green-200',
            textColor: 'text-green-700',
            badgeBg: 'bg-green-100'
        },
        TARGET: {
            label: 'Target',
            emoji: '🎯',
            color: 'blue',
            bgColor: 'bg-blue-50',
            borderColor: 'border-blue-200',
            textColor: 'text-blue-700',
            badgeBg: 'bg-blue-100'
        },
        REACH: {
            label: 'Reach',
            emoji: '🔼',
            color: 'orange',
            bgColor: 'bg-orange-50',
            borderColor: 'border-orange-200',
            textColor: 'text-orange-700',
            badgeBg: 'bg-orange-100'
        },
        SUPER_REACH: {
            label: 'Super Reach',
            emoji: '🚀',
            color: 'red',
            bgColor: 'bg-red-50',
            borderColor: 'border-red-200',
            textColor: 'text-red-700',
            badgeBg: 'bg-red-100'
        }
    };

    const config = categoryConfig[fitCategory] || categoryConfig.TARGET;

    // Map factor names to icons
    const getFactorIcon = (name) => {
        const iconMap = {
            'GPA Match': '📚',
            'Test Scores': '📝',
            'Selectivity Context': '🏛️',
            'Course Rigor': '📈',
            'Major Fit': '🎓',
            'Activities': '🏆',
            'Early Action': '⏰'
        };
        return iconMap[name] || '📊';
    };

    // Get selectivity context (display only, not part of score)
    const selectivityFactor = factors.find(f => f.name === 'Selectivity Context');
    const scoringFactors = factors.filter(f => f.max > 0);

    return (
        <div className={`rounded-lg border ${config.borderColor} ${config.bgColor} overflow-hidden transition-all duration-300`}>
            {/* Header - Always visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/30 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-full ${config.badgeBg} flex items-center justify-center`}>
                        <span className="text-xl">{config.emoji}</span>
                    </div>
                    <div className="text-left">
                        <div className="flex items-center gap-2">
                            <span className={`font-bold ${config.textColor}`}>{config.label}</span>
                            <span className="text-sm text-gray-500">•</span>
                            <span className="font-semibold text-gray-800">{matchScore}% Match</span>
                        </div>
                        <p className="text-xs text-gray-500 flex items-center gap-1">
                            <InformationCircleIcon className="w-3 h-3" />
                            {isExpanded ? 'Click to collapse' : 'Click to see factor breakdown'}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${config.textColor}`}>
                        {isExpanded ? 'Hide Details' : 'View Fit Analysis'}
                    </span>
                    {isExpanded ? (
                        <ChevronUpIcon className={`w-5 h-5 ${config.textColor}`} />
                    ) : (
                        <ChevronDownIcon className={`w-5 h-5 ${config.textColor}`} />
                    )}
                </div>
            </button>

            {/* Expanded Content */}
            {isExpanded && (
                <div className="px-4 pb-4 pt-2 border-t border-white/50 bg-white/50">
                    {/* Selectivity Context */}
                    {selectivityFactor && (
                        <div className="mb-4 px-3 py-2 bg-slate-100 rounded-lg flex items-center gap-2">
                            <span className="text-lg">🏛️</span>
                            <span className="text-sm text-slate-700">
                                <strong>School Selectivity:</strong> {selectivityFactor.detail}
                            </span>
                        </div>
                    )}

                    {/* Factor Breakdown */}
                    <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                            <ChartBarIcon className="w-4 h-4" />
                            Score Breakdown (Fair Mode)
                        </h4>

                        {scoringFactors.length > 0 ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {scoringFactors.map((factor, idx) => {
                                    const pct = factor.max > 0 ? Math.round((factor.score / factor.max) * 100) : 0;
                                    return (
                                        <div
                                            key={idx}
                                            className="bg-white rounded-lg p-3 border border-gray-100 shadow-sm"
                                        >
                                            <div className="flex items-center justify-between mb-1">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm">{getFactorIcon(factor.name)}</span>
                                                    <span className="text-xs font-medium text-gray-700">{factor.name}</span>
                                                </div>
                                                <div className="text-right">
                                                    <span className={`text-sm font-bold ${pct >= 70 ? 'text-green-600' :
                                                            pct >= 50 ? 'text-yellow-600' : 'text-red-600'
                                                        }`}>
                                                        {pct}%
                                                    </span>
                                                    <span className="text-xs text-gray-400 ml-1">
                                                        ({factor.score}/{factor.max})
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="w-full bg-gray-200 rounded-full h-1.5">
                                                <div
                                                    className={`h-1.5 rounded-full transition-all duration-500 ${pct >= 70 ? 'bg-green-500' :
                                                            pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                                        }`}
                                                    style={{ width: `${pct}%` }}
                                                ></div>
                                            </div>
                                            <p className="text-xs text-gray-500 mt-1 line-clamp-1">{factor.detail}</p>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="text-sm text-gray-500 italic">No detailed factors available</p>
                        )}
                    </div>

                    {/* Algorithm Explanation */}
                    <div className="mt-3 p-2 bg-indigo-50 rounded-lg">
                        <p className="text-xs text-indigo-700 flex items-start gap-2">
                            <SparklesIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
                            <span>
                                <strong>Fair Mode:</strong> Match score based on your academic profile only.
                                Selectivity caps the category but doesn't reduce your score.
                            </span>
                        </p>
                    </div>

                    {/* Recommendations Preview */}
                    {recommendations.length > 0 && (
                        <div className="mt-3">
                            <h4 className="text-xs font-semibold text-gray-600 mb-1">💡 Top Recommendations:</h4>
                            <ul className="text-xs text-gray-600 space-y-1">
                                {recommendations.slice(0, 2).map((rec, idx) => (
                                    <li key={idx} className="flex items-start gap-1">
                                        <span className="text-amber-500">•</span>
                                        <span>{rec}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default FitBreakdownPanel;
