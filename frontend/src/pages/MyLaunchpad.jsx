import React, { useState, useEffect, useMemo } from 'react';
import {
    RocketLaunchIcon,
    MapPinIcon,
    TrashIcon,
    ArrowPathIcon,
    ChartBarIcon,
    ExclamationCircleIcon,
    CheckCircleIcon,
    ArrowTrendingUpIcon,
    SparklesIcon,
    LightBulbIcon,
    PlusCircleIcon,
    XMarkIcon,
    AcademicCapIcon
} from '@heroicons/react/24/outline';
import { getCollegeList, updateCollegeList, checkFitRecomputationNeeded, computeAllFits, computeSingleFit, getFitsByCategory, getPrecomputedFits, getBalancedList } from '../services/api';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FitBreakdownPanel from '../components/FitBreakdownPanel';

// Fit category configuration
const FIT_CATEGORIES = {
    REACH: {
        label: 'Reach',
        emoji: '🎯',
        color: 'orange',
        bgGradient: 'from-orange-50 to-amber-50',
        borderColor: 'border-orange-200',
        headerBg: 'bg-orange-100',
        textColor: 'text-orange-700',
        description: 'Challenging admits'
    },
    SUPER_REACH: {
        label: 'Super Reach',
        emoji: '🌟',
        color: 'red',
        bgGradient: 'from-red-50 to-pink-50',
        borderColor: 'border-red-200',
        headerBg: 'bg-red-100',
        textColor: 'text-red-700',
        description: 'Dream schools'
    },
    TARGET: {
        label: 'Target',
        emoji: '✅',
        color: 'blue',
        bgGradient: 'from-blue-50 to-indigo-50',
        borderColor: 'border-blue-200',
        headerBg: 'bg-blue-100',
        textColor: 'text-blue-700',
        description: 'Good match'
    },
    SAFETY: {
        label: 'Safety',
        emoji: '🛡️',
        color: 'green',
        bgGradient: 'from-green-50 to-emerald-50',
        borderColor: 'border-green-200',
        headerBg: 'bg-green-100',
        textColor: 'text-green-700',
        description: 'Likely admits'
    }
};

// College Card Component for Launchpad - matches UniInsight style
const LaunchpadCard = ({ college, onRemove, isRemoving, onViewDetails, isSelected, onToggleSelect, selectionMode }) => {
    const fitAnalysis = college.fit_analysis || {};
    const hasFitAnalysis = fitAnalysis && fitAnalysis.fit_category; // Only true if we have actual fit data
    const fitCategory = fitAnalysis.fit_category || 'TARGET';
    const matchPercentage = fitAnalysis.match_percentage || null;
    const categoryConfig = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;

    // Fit category colors matching UniInsight
    const fitColors = {
        SAFETY: 'bg-green-100 text-green-800 border-green-300',
        TARGET: 'bg-blue-100 text-blue-800 border-blue-300',
        REACH: 'bg-orange-100 text-orange-800 border-orange-300',
        SUPER_REACH: 'bg-red-100 text-red-800 border-red-300'
    };

    const formatNumber = (num) => {
        if (!num || num === 'N/A') return 'N/A';
        return typeof num === 'number' ? num.toLocaleString() : num;
    };

    return (
        <div className="bg-white rounded-2xl shadow-lg shadow-amber-50 border border-gray-100 hover:shadow-xl transition-all duration-300 flex flex-col h-full">
            <div className="p-5 flex-grow">
                {/* Header with optional checkbox */}
                <div className="flex justify-between items-start mb-3">
                    {selectionMode && (
                        <div className="mr-3 flex-shrink-0">
                            <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => onToggleSelect(college.university_id)}
                                className="h-5 w-5 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 cursor-pointer"
                            />
                        </div>
                    )}
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-bold text-gray-900 line-clamp-2" title={college.university_name}>
                            {college.university_name}
                        </h3>
                        <div className="flex items-center text-gray-500 text-sm mt-1">
                            <MapPinIcon className="h-4 w-4 mr-1 flex-shrink-0" />
                            <span className="truncate">{college.location || 'Location N/A'}</span>
                        </div>
                    </div>
                    {/* Fit Badge - only show if we have actual fit analysis */}
                    {hasFitAnalysis ? (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold border whitespace-nowrap ${fitColors[fitCategory] || fitColors.TARGET}`}>
                            {categoryConfig.emoji} {categoryConfig.label}
                            {matchPercentage && ` ${matchPercentage}%`}
                        </span>
                    ) : (
                        <span className="px-2.5 py-1 rounded-full text-xs font-medium border whitespace-nowrap bg-gray-100 text-gray-500 border-gray-200">
                            Pending
                        </span>
                    )}
                </div>

                {/* Stats Grid - only show if we have fit analysis */}
                {hasFitAnalysis ? (
                    <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                        <div className="bg-amber-50 p-2 rounded-xl">
                            <div className="text-gray-500 text-xs">Fit Category</div>
                            <div className={`font-semibold ${categoryConfig.textColor}`}>
                                {categoryConfig.label}
                            </div>
                        </div>
                        <div className="bg-gray-50 p-2 rounded">
                            <div className="text-gray-500 text-xs">Match Score</div>
                            <div className="font-semibold text-gray-900">
                                {matchPercentage ? `${matchPercentage}%` : 'N/A'}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 mb-3">
                        <div className="text-amber-800 text-sm flex items-center gap-2">
                            <SparklesIcon className="h-4 w-4" />
                            <span>Upload your profile to get personalized fit analysis</span>
                        </div>
                    </div>
                )}

                {/* LLM Explanation (if available) - brief version */}
                {fitAnalysis.explanation && (
                    <div className="text-sm text-gray-600 bg-blue-50 rounded p-3 border border-blue-100">
                        <span className="font-medium text-blue-700">✨ Why This Fit: </span>
                        <span className="line-clamp-2">{fitAnalysis.explanation}</span>
                    </div>
                )}
            </div>

            {/* Footer with action buttons - matches UniInsight */}
            <div className="p-4 border-t border-gray-100">
                <div className="flex gap-2">
                    <button
                        onClick={() => onViewDetails && onViewDetails(college)}
                        className="flex-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white py-2 rounded-xl text-sm font-medium hover:from-amber-400 hover:to-orange-400 flex items-center justify-center gap-1 shadow-lg shadow-amber-200"
                    >
                        {hasFitAnalysis ? '📊 Fit Analysis' : '📝 Add Profile'}
                    </button>
                    <button
                        onClick={() => onRemove(college)}
                        disabled={isRemoving}
                        className="px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                        <TrashIcon className="h-4 w-4" />
                        {isRemoving ? '...' : 'Remove'}
                    </button>
                </div>
            </div>
        </div>
    );
};

// Category Column Component
const CategoryColumn = ({ category, colleges, onRemove, removingId, onViewDetails, selectedColleges, onToggleSelect, selectionMode }) => {
    const config = FIT_CATEGORIES[category] || FIT_CATEGORIES.TARGET;

    return (
        <div className={`rounded-xl border ${config.borderColor} bg-gradient-to-b ${config.bgGradient} overflow-hidden`}>
            {/* Header */}
            <div className={`${config.headerBg} px-4 py-3 border-b ${config.borderColor}`}>
                <div className="flex items-center justify-between">
                    <h3 className={`font-bold ${config.textColor} flex items-center gap-2`}>
                        <span className="text-lg">{config.emoji}</span>
                        {config.label}
                    </h3>
                    <span className={`text-xs ${config.textColor} bg-white/50 px-2 py-0.5 rounded-full`}>
                        {colleges.length} school{colleges.length !== 1 ? 's' : ''}
                    </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{config.description}</p>
            </div>

            {/* Cards */}
            <div className="p-3 space-y-3 min-h-[200px]">
                {colleges.length === 0 ? (
                    <div className="text-center py-8 text-gray-400 text-sm">
                        No {config.label.toLowerCase()} schools yet
                    </div>
                ) : (
                    colleges.map((college) => (
                        <LaunchpadCard
                            key={college.university_id}
                            college={college}
                            onRemove={onRemove}
                            isRemoving={removingId === college.university_id}
                            onViewDetails={onViewDetails}
                            isSelected={selectedColleges.has(college.university_id)}
                            onToggleSelect={onToggleSelect}
                            selectionMode={selectionMode}
                        />
                    ))
                )}
            </div>
        </div>
    );
};

// Detailed Fit Analysis Component (shown when clicking "Details" on a college)
const FitAnalysisDetail = ({ college, onBack }) => {
    const fitAnalysis = college.fit_analysis || {};
    const fitCategory = fitAnalysis.fit_category || 'TARGET';
    const matchScore = fitAnalysis.match_percentage || fitAnalysis.match_score || 50;
    const config = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;

    // Get explanation or generate a default one
    const explanation = fitAnalysis.explanation ||
        `Based on your academic profile, ${college.university_name} is a ${fitCategory.replace('_', ' ').toLowerCase()} school for you with a ${matchScore}% match score.`;

    // Use real factors from backend if available, otherwise use defaults
    const backendFactors = fitAnalysis.factors || [];

    // Get the { currentUser } = useAuth() to fetch profile
    const { currentUser } = useAuth();
    const [studentProfile, setStudentProfile] = useState(null);

    // Fetch student profile
    useEffect(() => {
        if (currentUser?.email) {
            fetch(`https://profile-manager-es-pfnwjfp26a-ue.a.run.app/get-profile?user_email=${encodeURIComponent(currentUser.email)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.profile) {
                        setStudentProfile(data.profile);
                    }
                })
                .catch(err => console.error('Failed to fetch profile:', err));
        }
    }, [currentUser]);


    // Map backend factors to display format with icons
    const getFactorIcon = (name) => {
        const iconMap = {
            'GPA Match': '📚',
            'Test Scores': '📝',
            'Selectivity Context': '🎯',
            'Course Rigor': '📈',
            'Major Fit': '🎓',
            'Activities': '🏆',
            'Early Action': '⏰'
        };
        return iconMap[name] || '📊';
    };

    // Convert backend factors to display format
    const scoreBreakdown = backendFactors.length > 0
        ? backendFactors
            .filter(f => f.max > 0) // Skip display-only factors like Selectivity Context
            .map(factor => ({
                category: factor.name,
                score: factor.max > 0 ? Math.round((factor.score / factor.max) * 100) : 0,
                rawScore: factor.score,
                maxScore: factor.max,
                description: factor.detail || `${factor.name} score`,
                icon: getFactorIcon(factor.name)
            }))
        : [
            // Fallback to estimated scores if no backend factors
            {
                category: 'Academic Match',
                score: Math.min(matchScore + 10, 100),
                description: 'GPA and test scores compared to admitted student profile',
                icon: '📚'
            },
            {
                category: 'Selectivity Fit',
                score: matchScore,
                description: 'Your competitiveness relative to acceptance rate',
                icon: '🎯'
            },
            {
                category: 'Program Strength',
                score: Math.max(matchScore - 5, 0),
                description: 'Alignment with your intended major/field',
                icon: '🔬'
            }
        ];

    // Get selectivity context for display (not part of score)
    const selectivityFactor = backendFactors.find(f => f.name === 'Selectivity Context');
    const selectivityDetail = selectivityFactor?.detail || null;

    // Use actual recommendations from backend fit analysis if available
    // This provides personalized, specific action items based on the student's actual gaps
    const recommendations = fitAnalysis.recommendations || [];

    return (
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className={`${config.headerBg} px-6 py-4 border-b ${config.borderColor}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={onBack}
                            className="p-2 hover:bg-white/50 rounded-lg transition-colors"
                        >
                            ← Back
                        </button>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">{college.university_name}</h2>
                            <p className="text-sm text-gray-600 flex items-center gap-1">
                                <MapPinIcon className="h-4 w-4" />
                                {college.location || 'Location N/A'}
                            </p>
                        </div>
                    </div>
                    <div className="text-right">
                        <span className={`px-4 py-2 rounded-full text-sm font-bold ${config.headerBg} ${config.textColor} border ${config.borderColor}`}>
                            {config.emoji} {config.label}
                        </span>
                        <p className="text-2xl font-bold text-gray-900 mt-2">{matchScore}% Match</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
                {/* University Overview (from pre-computed summary) */}
                {college.summary && (
                    <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                        <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                            <AcademicCapIcon className="h-5 w-5 text-gray-600" />
                            University Overview
                        </h3>
                        <div className="prose prose-sm max-w-none text-gray-700">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {college.summary}
                            </ReactMarkdown>
                        </div>
                    </div>
                )}

                {/* Fit Explanation */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-100">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-blue-600" />
                        Why This Fit Category?
                    </h3>
                    <div className="text-gray-700 prose prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {explanation}
                        </ReactMarkdown>
                    </div>
                </div>


                {/* Score Breakdown */}
                <div>
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <ChartBarIcon className="h-5 w-5 text-purple-600" />
                        Score Breakdown (Fair Mode - 100pt Scale)
                    </h3>

                    {/* Selectivity Context Badge */}
                    {selectivityDetail && (
                        <div className="mb-4 px-4 py-2 bg-slate-100 rounded-lg border border-slate-200 flex items-center gap-2">
                            <span className="text-lg">🏛️</span>
                            <span className="text-sm text-slate-700"><strong>School Selectivity:</strong> {selectivityDetail}</span>
                        </div>
                    )}

                    <div className="space-y-4">
                        {scoreBreakdown.map((item, idx) => (
                            <div key={idx} className="bg-gray-50 rounded-lg p-4">
                                <div className="flex justify-between items-center mb-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">{item.icon}</span>
                                        <span className="font-medium text-gray-900">{item.category}</span>
                                    </div>
                                    <div className="text-right">
                                        <span className={`font-bold ${item.score >= 70 ? 'text-green-600' : item.score >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                                            {item.score}%
                                        </span>
                                        {item.rawScore !== undefined && (
                                            <span className="text-xs text-gray-400 ml-1">
                                                ({item.rawScore}/{item.maxScore} pts)
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                                    <div
                                        className={`h-2 rounded-full transition-all duration-300 ${item.score >= 70 ? 'bg-green-500' : item.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                        style={{ width: `${item.score}%` }}
                                    ></div>
                                </div>
                                <p className="text-sm text-gray-500">{item.description}</p>
                            </div>
                        ))}
                    </div>

                    {/* Fair Mode Explanation */}
                    <div className="mt-4 p-3 bg-indigo-50 rounded-lg border border-indigo-100">
                        <p className="text-xs text-indigo-700">
                            <strong>Fair Mode:</strong> Your match score is calculated based on academic factors only.
                            School selectivity is used as a ceiling for the category (not to reduce your score).
                        </p>
                    </div>
                </div>

                {/* Action Plan - Personalized Recommendations */}
                {recommendations.length > 0 && (
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                            <LightBulbIcon className="h-5 w-5 text-amber-600" />
                            Action Plan to Strengthen Your Application
                        </h3>
                        <div className="space-y-2">
                            {recommendations.map((rec, idx) => (
                                <div key={idx} className="flex flex-col gap-2 p-4 bg-blue-50 rounded-lg">
                                    <div className="flex items-start gap-3">
                                        <span className="text-blue-600 font-bold">{idx + 1}.</span>
                                        <span className="text-gray-700">{typeof rec === 'object' ? rec.action : rec}</span>
                                    </div>
                                    {typeof rec === 'object' && rec.addresses_gap && (
                                        <div className="ml-7 flex flex-wrap gap-2 text-xs">
                                            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">Addresses: {rec.addresses_gap}</span>
                                            {rec.timeline && <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full">Timeline: {rec.timeline}</span>}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

// Recommendation Card Component - Selectable with checkbox
const RecommendationCard = ({ recommendation, isSelected, onToggleSelect }) => {
    const fitCategory = recommendation.fit_category || 'TARGET';
    const categoryConfig = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;

    return (
        <div
            onClick={() => onToggleSelect(recommendation.id)}
            className={`bg-white rounded-xl shadow-sm border-2 p-4 cursor-pointer transition-all ${isSelected
                ? 'border-purple-500 ring-2 ring-purple-200 shadow-md'
                : 'border-gray-200 hover:border-purple-300 hover:shadow-md'
                }`}
        >
            <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* Checkbox */}
                    <div className={`flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center ${isSelected
                        ? 'bg-purple-600 border-purple-600'
                        : 'border-gray-300'
                        }`}>
                        {isSelected && (
                            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                            </svg>
                        )}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-900 truncate">{recommendation.name}</h4>
                        <div className="flex items-center text-gray-500 text-xs mt-0.5">
                            <MapPinIcon className="h-3 w-3 mr-1" />
                            <span>{recommendation.location || 'Location N/A'}</span>
                        </div>
                    </div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${categoryConfig.headerBg} ${categoryConfig.textColor}`}>
                    {categoryConfig.emoji} {categoryConfig.label}
                </span>
            </div>
            <div className="ml-8">
                <p className="text-sm text-gray-600 line-clamp-2">{recommendation.reason}</p>
                <div className="mt-2 text-xs text-gray-500">
                    Match: <span className="font-semibold text-purple-600">{recommendation.matchScore}%</span>
                </div>
            </div>
        </div>
    );
};

// Smart Discovery Panel Component
const SmartDiscoveryPanel = ({ currentUser, categorizedColleges, onCollegeAdded, initialPrompt }) => {
    const [isOpen, setIsOpen] = useState(!!initialPrompt);
    const [isLoading, setIsLoading] = useState(false);
    const [recommendations, setRecommendations] = useState([]);
    const [error, setError] = useState(null);
    const [hasAutoTriggered, setHasAutoTriggered] = useState(false);
    const [preferences, setPreferences] = useState('');

    // Analyze current list balance
    const listAnalysis = useMemo(() => {
        const reachCount = (categorizedColleges.SUPER_REACH?.length || 0) + (categorizedColleges.REACH?.length || 0);
        const targetCount = categorizedColleges.TARGET?.length || 0;
        const safetyCount = categorizedColleges.SAFETY?.length || 0;
        const total = reachCount + targetCount + safetyCount;

        // Determine what's needed for a balanced list (ideal: 2-3 reach, 3-4 target, 2-3 safety)
        const gaps = [];
        if (safetyCount < 2) gaps.push({ category: 'SAFETY', needed: 2 - safetyCount, priority: 1 });
        if (targetCount < 3) gaps.push({ category: 'TARGET', needed: 3 - targetCount, priority: 2 });
        if (reachCount < 2) gaps.push({ category: 'REACH', needed: 2 - reachCount, priority: 3 });

        return { reachCount, targetCount, safetyCount, total, gaps };
    }, [categorizedColleges]);

    // Build smart prompt - agent will fetch profile using [USER_EMAIL] tag
    const buildSmartPrompt = () => {
        const { reachCount, targetCount, safetyCount, gaps } = listAnalysis;

        // Get names of current schools
        const reachNames = [...(categorizedColleges.SUPER_REACH || []), ...(categorizedColleges.REACH || [])]
            .map(c => c.university_name).join(', ') || 'none';
        const targetNames = (categorizedColleges.TARGET || []).map(c => c.university_name).join(', ') || 'none';
        const safetyNames = (categorizedColleges.SAFETY || []).map(c => c.university_name).join(', ') || 'none';

        // Determine priority category
        const priorityCategory = gaps.length > 0 ? gaps[0].category : 'TARGET';
        const neededCount = gaps.reduce((sum, g) => sum + g.needed, 0) || 3;

        // Build preferences section if provided
        const preferencesSection = preferences.trim() ? `
MY PREFERENCES (VERY IMPORTANT - use these):
${preferences.trim()}
` : '';

        console.log('[Smart Discovery] Building prompt with preferences:', preferences.trim() || '(none)');


        return `[USER_EMAIL: ${currentUser.email}]

IMPORTANT: You have my full academic profile loaded. USE IT NOW. Do not ask me any questions - use the data you already have.

I'm building a balanced college application list. Here's my current list:
- Reach/Super Reach schools: ${reachCount} (${reachNames})
- Target schools: ${targetCount} (${targetNames})
- Safety schools: ${safetyCount} (${safetyNames})
${preferencesSection}
TASK: Recommend ${Math.min(neededCount, 5)} colleges to balance my list. I especially need more ${priorityCategory.toLowerCase()} schools.

INSTRUCTIONS (FOLLOW EXACTLY):
1. Use my GPA, test scores, extracurriculars, and intended major from my loaded profile
2. Search for universities in your knowledge base that match my profile
3. Do NOT ask me any questions - use all data from my profile
4. Prioritize top-50 and top-100 ranked schools
5. If I specified location preferences above, prioritize schools in those areas
6. Do NOT recommend schools already in my list

OUTPUT FORMAT (one school per line):
SCHOOL: [University Name] | LOCATION: [City, State] | FIT: [REACH/TARGET/SAFETY] | REASON: [Why this fits my profile]

IMMEDIATELY search and provide recommendations. No clarifying questions.`;
    };

    // Parse recommendations from agent response - handles multiple formats
    const parseRecommendations = (responseText) => {
        const recs = [];
        const lines = responseText.split('\n');

        for (const line of lines) {
            // Skip empty lines
            if (!line.trim()) continue;

            // Try Format 1: SCHOOL: ... | LOCATION: ... | FIT: ... | REASON: ...
            const schoolMatch = line.match(/SCHOOL:\s*([^|]+)/i);
            if (schoolMatch) {
                const locationMatch = line.match(/LOCATION:\s*([^|]+)/i);
                const fitMatch = line.match(/FIT:\s*(REACH|TARGET|SAFETY|SUPER_REACH)/i);
                const reasonMatch = line.match(/REASON:\s*(.+)/i);

                recs.push({
                    id: `rec_${recs.length}_${Date.now()}`,
                    name: schoolMatch[1].trim(),
                    location: locationMatch ? locationMatch[1].trim() : 'Unknown',
                    fit_category: fitMatch ? fitMatch[1].trim().toUpperCase() : 'TARGET',
                    reason: reasonMatch ? reasonMatch[1].trim() : 'Recommended for your profile'
                });
                continue;
            }

            // Try Format 2: Numbered list like "1. University of X" or "**University of X**"
            const numberedMatch = line.match(/^\s*[\d\.\-\*]+\s*\**([A-Z][A-Za-z\s&]+(?:University|College|Institute|School)[A-Za-z\s]*)\**[\s\-:,]*(.*)/i);
            if (numberedMatch) {
                const universityName = numberedMatch[1].replace(/\*+/g, '').trim();
                const rest = numberedMatch[2] || '';

                // Try to extract fit category from the rest
                let fitCategory = 'TARGET';
                if (/safety/i.test(rest) || /safety/i.test(line)) fitCategory = 'SAFETY';
                else if (/super.?reach/i.test(rest) || /super.?reach/i.test(line)) fitCategory = 'SUPER_REACH';
                else if (/reach/i.test(rest) || /reach/i.test(line)) fitCategory = 'REACH';
                else if (/target/i.test(rest) || /target/i.test(line)) fitCategory = 'TARGET';

                recs.push({
                    id: `rec_${recs.length}_${Date.now()}`,
                    name: universityName,
                    location: 'Unknown',
                    fit_category: fitCategory,
                    reason: rest.trim() || 'Recommended for your profile'
                });
                continue;
            }

            // Try Format 3: Just a university name on its own line (contains "University", "College", etc.)
            // But skip category header lines like "Safety Schools", "Target Schools", "Reach Schools"
            const isCategoryHeader = /^[\s\*\-#]*(?:safety|target|reach|super.?reach)\s+schools?[\s:]*$/i.test(line);
            if (isCategoryHeader) continue;

            const uniNameMatch = line.match(/^[\s\-\*\d\.]*\**([A-Z][A-Za-z\s&]+(?:University|College|Institute|MIT|UCLA|USC|Caltech|Stanford|Princeton|Harvard|Yale)[\w\s]*)\**[\s\-:,]*(.*)/i);
            if (uniNameMatch && uniNameMatch[1].length > 5 && uniNameMatch[1].length < 80) {
                const universityName = uniNameMatch[1].replace(/\*+/g, '').trim();
                const rest = uniNameMatch[2] || '';

                // Check if this looks like a university name (not a description or category header)
                if (!/^\s*(is|are|has|the|a|an|this)\s/i.test(universityName) &&
                    !/^(safety|target|reach)\s+schools?$/i.test(universityName)) {
                    let fitCategory = 'TARGET';
                    if (/safety/i.test(rest) || /safety/i.test(line)) fitCategory = 'SAFETY';
                    else if (/super.?reach/i.test(rest) || /super.?reach/i.test(line)) fitCategory = 'SUPER_REACH';
                    else if (/reach/i.test(rest) || /reach/i.test(line)) fitCategory = 'REACH';

                    recs.push({
                        id: `rec_${recs.length}_${Date.now()}`,
                        name: universityName,
                        location: 'Unknown',
                        fit_category: fitCategory,
                        reason: rest.trim() || 'Recommended for your profile'
                    });
                }
            }
        }

        // Dedupe by name
        const uniqueRecs = [];
        const seen = new Set();
        for (const rec of recs) {
            const key = rec.name.toLowerCase().replace(/\s+/g, ' ');
            if (!seen.has(key)) {
                seen.add(key);
                uniqueRecs.push(rec);
            }
        }

        console.log('[Smart Discovery] Parsed', uniqueRecs.length, 'recommendations from response');
        return uniqueRecs;
    };

    // Get recommendations - can accept custom prompt for quick-start
    // Note: When called from onClick, an event object is passed - we need to handle that
    const handleGetRecommendations = async (customPromptOrEvent = null) => {
        setIsLoading(true);
        setError(null);
        setRecommendations([]);

        try {
            // If called from button click, customPromptOrEvent is the event object, not a string
            const customPrompt = (typeof customPromptOrEvent === 'string') ? customPromptOrEvent : null;

            // Use custom prompt if provided (and valid), otherwise build smart prompt
            const prompt = customPrompt || buildSmartPrompt();
            console.log('[Smart Discovery] Prompt type:', typeof prompt);
            console.log('[Smart Discovery] Prompt length:', prompt?.length);
            console.log('[Smart Discovery] Prompt first 200 chars:', String(prompt || '').substring(0, 200));
            console.log('[Smart Discovery] Sending prompt to agent...');


            const response = await startSession(prompt, currentUser?.email);
            const fullResponse = extractFullResponse(response);
            const responseText = fullResponse.result || fullResponse;

            console.log('[Smart Discovery] Response:', responseText);

            // Parse recommendations
            const recs = parseRecommendations(responseText);

            if (recs.length === 0) {
                // Try a simpler parsing if structured format fails
                setError('Could not parse recommendations. The AI may have responded in an unexpected format.');
            } else {
                setRecommendations(recs);
            }
        } catch (err) {
            console.error('[Smart Discovery] Error:', err);
            setError('Failed to get recommendations. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // Optimized quick filter handler - uses direct API calls instead of LLM
    // Much faster (1s vs 5-10s) and more reliable for predefined filters
    const handleQuickFilter = async (category = null, state = null) => {
        setIsLoading(true);
        setError(null);
        setRecommendations([]);

        try {
            if (!currentUser?.email) {
                setError('Please log in to use this feature.');
                return;
            }

            // Get existing college IDs to exclude
            const existingIds = [];
            Object.values(categorizedColleges).forEach(colleges => {
                colleges.forEach(c => {
                    if (c.university_id) existingIds.push(c.university_id);
                });
            });

            console.log(`[Smart Discovery] Quick filter: category=${category}, state=${state}, excluding ${existingIds.length} existing colleges`);

            // Direct API call - much faster than LLM
            const result = await getFitsByCategory(currentUser.email, category, state, existingIds, 8);

            if (result.success && result.results?.length > 0) {
                // Transform API results to recommendation format and sort by match score descending
                const recs = result.results.map((fit, idx) => ({
                    id: fit.university_id || `rec-${idx}`,
                    name: fit.university_name || fit.official_name || 'Unknown',
                    fit_category: fit.fit_category,
                    matchScore: fit.match_percentage || 0,
                    location: fit.location ? `${fit.location.city}, ${fit.location.state}` : null,
                    reason: `${fit.fit_category?.replace('_', ' ')} school with ${fit.match_percentage}% match`,
                    selected: true
                })).sort((a, b) => b.matchScore - a.matchScore);
                setRecommendations(recs);
                // Auto-select all
                const allSelected = {};
                recs.forEach(r => { allSelected[r.id] = true; });
                setSelectedRecs(allSelected);
            } else if (result.results?.length === 0) {
                setError(`No additional ${category || 'matching'} schools found. Try a different filter or use the AI-powered discovery.`);
            } else {
                setError('Failed to load recommendations. Please try again.');
            }
        } catch (err) {
            console.error('[Smart Discovery] Quick filter error:', err);
            setError('Failed to load recommendations. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // Get balanced list (safety + target + reach) via direct API calls
    const handleQuickBalancedList = async () => {
        setIsLoading(true);
        setError(null);
        setRecommendations([]);

        try {
            if (!currentUser?.email) {
                setError('Please log in to use this feature.');
                return;
            }

            // Get existing college IDs to exclude
            const existingIds = [];
            Object.values(categorizedColleges).forEach(colleges => {
                colleges.forEach(c => {
                    if (c.university_id) existingIds.push(c.university_id);
                });
            });

            console.log(`[Smart Discovery] Getting balanced list, excluding ${existingIds.length} existing colleges`);

            // Call new API function - fetches 3 categories in parallel
            const result = await getBalancedList(currentUser.email, existingIds);

            if (result.success && result.results?.length > 0) {
                // Transform to recommendation format and sort by match score descending
                const recs = result.results.map((fit, idx) => ({
                    id: fit.university_id || `rec-${idx}`,
                    name: fit.university_name || fit.official_name || 'Unknown',
                    fit_category: fit.fit_category,
                    matchScore: fit.match_percentage || 0,
                    location: fit.location ? `${fit.location.city}, ${fit.location.state}` : null,
                    reason: `${fit.fit_category?.replace('_', ' ')} school with ${fit.match_percentage}% match`,
                    selected: true
                })).sort((a, b) => b.matchScore - a.matchScore);
                setRecommendations(recs);

                // Auto-select all
                const allSelected = {};
                recs.forEach(r => { allSelected[r.id] = true; });
                setSelectedRecs(allSelected);

                console.log(`[Smart Discovery] Balanced list: ${result.breakdown.safety} safety, ${result.breakdown.target} target, ${result.breakdown.reach} reach`);
            } else if (result.results?.length === 0) {
                setError('No additional schools found for a balanced list. Try adding different filters or use AI-powered discovery.');
            } else {
                setError('Failed to load balanced list. Please try again.');
            }
        } catch (err) {
            console.error('[Smart Discovery] Balanced list error:', err);
            setError('Failed to load balanced list. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };


    // Auto-open panel when initialPrompt is provided (but don't auto-fetch)
    useEffect(() => {
        if (initialPrompt && !hasAutoTriggered && currentUser?.email) {
            setHasAutoTriggered(true);
            setIsOpen(true);  // Just open the panel, don't auto-fetch
            // Let user click the buttons to fetch recommendations
        }
    }, [initialPrompt, hasAutoTriggered, currentUser]);

    // Track if adding is in progress
    const [isAddingAll, setIsAddingAll] = useState(false);
    const [selectedRecs, setSelectedRecs] = useState({});

    // Toggle selection of a recommendation
    const toggleSelection = (recId) => {
        setSelectedRecs(prev => ({
            ...prev,
            [recId]: !prev[recId]
        }));
    };

    // Select/deselect all
    const toggleSelectAll = () => {
        if (Object.keys(selectedRecs).filter(k => selectedRecs[k]).length === recommendations.length) {
            setSelectedRecs({});
        } else {
            const all = {};
            recommendations.forEach(r => { all[r.id] = true; });
            setSelectedRecs(all);
        }
    };

    // Get selected recommendations
    const getSelectedRecs = () => {
        return recommendations.filter(r => selectedRecs[r.id]);
    };

    // Add selected recommendations using direct API calls
    const handleAddSelected = async () => {
        const toAdd = getSelectedRecs();
        if (!currentUser?.email || toAdd.length === 0) return;

        setIsAddingAll(true);
        console.log('[Smart Discovery] Adding selected recommendations:', toAdd.map(r => r.name));

        let addedCount = 0;
        for (const rec of toAdd) {
            try {
                // Use updateCollegeList API directly with the correct university_id
                const result = await updateCollegeList(
                    currentUser.email,
                    'add',
                    { id: rec.id, name: rec.name },  // rec.id already contains the correct university_id
                    '' // intended major
                );

                if (result.success) {
                    addedCount++;
                    console.log(`[Smart Discovery] Added: ${rec.name}`);

                    // Trigger lazy fit computation for this university (don't await - run in background)
                    console.log(`[Smart Discovery] Computing fit for: ${rec.name}`);
                    computeSingleFit(currentUser.email, rec.id).then(fitResult => {
                        if (fitResult.success) {
                            console.log(`[Smart Discovery] Fit computed for ${rec.name}: ${fitResult.fit_analysis?.fit_category}`);
                        } else {
                            console.warn(`[Smart Discovery] Fit computation failed for ${rec.name}`);
                        }
                    });
                } else {
                    console.error(`[Smart Discovery] Failed to add ${rec.name}:`, result.error);
                }
            } catch (err) {
                console.error(`[Smart Discovery] Error adding ${rec.name}:`, err);
            }
        }

        // Clear selections and refresh
        if (addedCount > 0) {
            setRecommendations(prev => prev.filter(r => !selectedRecs[r.id]));
            setSelectedRecs({});
            if (onCollegeAdded) {
                onCollegeAdded();
            }
        }

        setIsAddingAll(false);

        if (addedCount > 0) {
            setError(null);
        } else {
            setError('Failed to add schools. Please try again.');
        }
    };

    // Balance indicator
    const getBalanceStatus = () => {
        const { safetyCount, targetCount, reachCount } = listAnalysis;
        if (safetyCount >= 2 && targetCount >= 3 && reachCount >= 2) {
            return { status: 'balanced', message: 'Your list is well-balanced! 🎉', color: 'text-green-600' };
        }
        if (safetyCount === 0) {
            return { status: 'warning', message: '⚠️ You need safety schools!', color: 'text-red-600' };
        }
        if (targetCount < 2) {
            return { status: 'warning', message: '💡 Add more target schools', color: 'text-amber-600' };
        }
        return { status: 'info', message: '🎯 Getting balanced...', color: 'text-blue-600' };
    };

    const balanceStatus = getBalanceStatus();

    return (
        <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-200 overflow-hidden">
            {/* Header - Always visible */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-purple-100/50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                        <LightBulbIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div className="text-left">
                        <h3 className="font-bold text-gray-900">Smart Discovery</h3>
                        <p className={`text-sm ${balanceStatus.color}`}>{balanceStatus.message}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-purple-600 font-medium">
                        {isOpen ? 'Close' : 'Find More Schools'}
                    </span>
                    <XMarkIcon className={`h-5 w-5 text-purple-600 transition-transform ${isOpen ? 'rotate-0' : 'rotate-45'}`} />
                </div>
            </button>

            {/* Expanded Content */}
            {isOpen && (
                <div className="px-6 pb-6 pt-2 border-t border-purple-200">
                    {/* List Balance Summary */}
                    <div className="flex gap-4 mb-4 text-sm">
                        <div className="flex items-center gap-1">
                            <span className="text-orange-500">🎯</span>
                            <span>Reach: {listAnalysis.reachCount}</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="text-blue-500">✅</span>
                            <span>Target: {listAnalysis.targetCount}</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="text-green-500">🛡️</span>
                            <span>Safety: {listAnalysis.safetyCount}</span>
                        </div>
                    </div>

                    {/* Quick Prompt Suggestions - Always Visible */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Quick Prompts
                        </label>
                        <div className="flex flex-wrap gap-2">
                            <button
                                onClick={() => handleQuickBalancedList()}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-purple-200 text-purple-700 rounded-full text-sm font-medium hover:bg-purple-50 transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                ⚖️ Balanced List ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter('SAFETY', null)}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-green-200 text-green-700 rounded-full text-sm font-medium hover:bg-green-50 transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                🛡️ More Safety Schools ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter('TARGET', null)}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-blue-200 text-blue-700 rounded-full text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                ✅ More Target Schools ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter('REACH', null)}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-orange-200 text-orange-700 rounded-full text-sm font-medium hover:bg-orange-50 transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                🎯 More Reach Schools ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter(null, null)}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-indigo-200 text-indigo-700 rounded-full text-sm font-medium hover:bg-indigo-50 transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                📚 Best Matches ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter(null, 'California')}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-amber-200 text-amber-700 rounded-full text-sm font-medium hover:bg-amber-50 transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                🌴 California Schools ⚡
                            </button>
                        </div>
                    </div>

                    {/* Custom Preferences Input - Always Visible */}
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Your Preferences (optional)
                        </label>
                        <textarea
                            value={preferences}
                            onChange={(e) => setPreferences(e.target.value)}
                            placeholder="E.g., Prefer East Coast schools, want a large campus with strong research programs, need good financial aid, interested in business/psychology programs..."
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                            rows={2}
                        />
                    </div>

                    {/* Get Recommendations Button */}
                    <button
                        onClick={handleQuickBalancedList}
                        disabled={isLoading}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-medium hover:from-purple-700 hover:to-blue-700 transition-all shadow-lg disabled:opacity-50 mb-4"
                    >
                        <SparklesIcon className="h-5 w-5" />
                        {recommendations.length > 0 ? 'Get More Recommendations ⚡' : 'Get Smart Recommendations ⚡'}
                    </button>



                    {/* Loading State */}
                    {isLoading && (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600 mx-auto mb-3"></div>
                            <p className="text-gray-600">Analyzing your profile and finding schools...</p>
                            <p className="text-sm text-gray-400 mt-1">This may take a few seconds</p>
                        </div>
                    )}

                    {/* Error */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm mb-4">
                            {error}
                            <button
                                onClick={handleQuickBalancedList}
                                className="ml-2 underline hover:no-underline"
                            >
                                Try again
                            </button>
                        </div>
                    )}

                    {/* Recommendations */}
                    {recommendations.length > 0 && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h4 className="font-semibold text-gray-800 flex items-center gap-2">
                                    <SparklesIcon className="h-4 w-4 text-purple-600" />
                                    Recommended For You ({recommendations.length} schools)
                                </h4>
                                <button
                                    onClick={toggleSelectAll}
                                    className="text-sm text-blue-600 hover:text-blue-800"
                                >
                                    {getSelectedRecs().length === recommendations.length ? 'Deselect All' : 'Select All'}
                                </button>
                            </div>

                            {/* Card Grid - Consistent with Quick Start */}
                            <p className="text-sm text-gray-500 mb-3">
                                Click to select schools, then add to your launchpad
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {recommendations.map(rec => (
                                    <RecommendationCard
                                        key={rec.id}
                                        recommendation={rec}
                                        isSelected={!!selectedRecs[rec.id]}
                                        onToggleSelect={toggleSelection}
                                    />
                                ))}
                            </div>

                            {/* Add Selected Button */}
                            <button
                                onClick={handleAddSelected}
                                disabled={isAddingAll || getSelectedRecs().length === 0}
                                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl font-medium hover:from-green-700 hover:to-emerald-700 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {isAddingAll ? (
                                    <>
                                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                                        Adding schools...
                                    </>
                                ) : getSelectedRecs().length === 0 ? (
                                    <>
                                        <CheckCircleIcon className="h-5 w-5" />
                                        Select schools to add
                                    </>
                                ) : (
                                    <>
                                        <RocketLaunchIcon className="h-5 w-5" />
                                        Add {getSelectedRecs().length} School{getSelectedRecs().length > 1 ? 's' : ''} to Launchpad
                                    </>
                                )}
                            </button>

                            <button
                                onClick={handleQuickBalancedList}
                                disabled={isAddingAll}
                                className="w-full text-sm text-purple-600 hover:text-purple-800 font-medium disabled:opacity-50"
                            >
                                ↻ Get different recommendations ⚡
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// Empty State Component with Quick-Start Options
const EmptyState = ({ onQuickStart }) => {
    const quickStartOptions = [
        {
            id: 'balanced',
            emoji: '⚖️',
            title: 'Build a Balanced List',
            description: 'Get a mix of safety, target, and reach schools based on your profile',
            action: 'balanced',
            color: 'from-purple-600 to-blue-600'
        },
        {
            id: 'safety',
            emoji: '🛡️',
            title: 'Find Safety Schools',
            description: 'Schools where you\'re likely to be admitted',
            action: 'SAFETY',
            color: 'from-green-600 to-emerald-600'
        },
        {
            id: 'reach',
            emoji: '🎯',
            title: 'Find Reach Schools',
            description: 'Ambitious choices to aim high',
            action: 'REACH',
            color: 'from-orange-600 to-red-600'
        },
        {
            id: 'target',
            emoji: '✅',
            title: 'Find Target Schools',
            description: 'Schools where you have good chances',
            action: 'TARGET',
            color: 'from-blue-600 to-indigo-600'
        }
    ];

    return (
        <div className="text-center py-12 px-4">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-purple-100 to-blue-100 mb-6">
                <RocketLaunchIcon className="h-10 w-10 text-purple-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Build Your College List</h2>
            <p className="text-gray-600 max-w-md mx-auto mb-8">
                Let AI help you discover the right schools based on your profile
            </p>

            {/* Quick Start Options Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto mb-8">
                {quickStartOptions.map((option) => (
                    <button
                        key={option.id}
                        onClick={() => onQuickStart(option.action)}
                        className={`p-4 rounded-xl text-left transition-all hover:scale-105 hover:shadow-lg bg-gradient-to-br ${option.color} text-white`}
                    >
                        <div className="text-2xl mb-2">{option.emoji}</div>
                        <h3 className="font-bold text-lg mb-1">{option.title}</h3>
                        <p className="text-sm text-white/80">{option.description}</p>
                    </button>
                ))}
            </div>

            <div className="text-gray-400 text-sm mb-4">— or —</div>

            <a
                href="/universities"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-all"
            >
                <SparklesIcon className="h-5 w-5" />
                Browse Universities Manually
            </a>
        </div>
    );
};

// Main Component
const MyLaunchpad = () => {
    const { currentUser } = useAuth();
    const [collegeList, setCollegeList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [removingId, setRemovingId] = useState(null);
    const [selectedUniversity, setSelectedUniversity] = useState(null);
    const [deepResearchData, setDeepResearchData] = useState({});
    const [recomputingFits, setRecomputingFits] = useState(false);

    // Multi-select state for bulk removal
    const [selectedColleges, setSelectedColleges] = useState(new Set());
    const [selectionMode, setSelectionMode] = useState(false);
    const [bulkRemoving, setBulkRemoving] = useState(false);

    // Fetch college list
    const fetchCollegeList = async () => {
        if (!currentUser?.email) return;

        setLoading(true);
        setError(null);

        try {
            // Check for recomputation first
            if (!recomputingFits) {
                const recomputeStatus = await checkFitRecomputationNeeded(currentUser.email);
                if (recomputeStatus.needs_recomputation) {
                    console.log('[Launchpad] Recomputation needed:', recomputeStatus.reason);
                    setRecomputingFits(true);

                    // Trigger recomputation
                    await computeAllFits(currentUser.email);
                    setRecomputingFits(false);
                }
            }

            // Fetch both college list and precomputed fits
            const [listResult, fitsResult] = await Promise.all([
                getCollegeList(currentUser.email),
                getPrecomputedFits(currentUser.email, {}, 200)  // Increased limit to get all fits for college list merge
            ]);

            if (listResult.success) {
                let colleges = listResult.college_list || [];

                // Merge precomputed fits into college list (precomputed takes priority)
                if (fitsResult.success && fitsResult.results) {
                    const fitsMap = {};
                    fitsResult.results.forEach(fit => {
                        fitsMap[fit.university_id] = {
                            fit_category: fit.fit_category,
                            match_percentage: fit.match_percentage || fit.match_score,
                            match_score: fit.match_percentage || fit.match_score,
                            explanation: fit.explanation,
                            factors: fit.factors || [],
                            recommendations: fit.recommendations || []
                        };
                    });

                    // Merge precomputed fits into college list items
                    colleges = colleges.map(college => {
                        const precomputed = fitsMap[college.university_id];
                        if (precomputed) {
                            return {
                                ...college,
                                fit_analysis: precomputed  // Override with fresh precomputed data
                            };
                        }
                        return college;
                    });
                    console.log('[Launchpad] Merged precomputed fits for', Object.keys(fitsMap).length, 'universities');
                }

                setCollegeList(colleges);
            } else {
                setError(listResult.error || 'Failed to load college list');
            }
        } catch (err) {
            console.error('Error fetching college list:', err);
            setError('Unable to load your college list. Please try again.');
            setRecomputingFits(false);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCollegeList();
    }, [currentUser]);

    // Remove college from list
    const handleRemove = async (college) => {
        if (!currentUser?.email) return;

        setRemovingId(college.university_id);
        console.log('[Launchpad] Removing college:', college.university_name, college.university_id);

        try {
            // updateCollegeList signature: (userEmail, action, university, intendedMajor)
            const result = await updateCollegeList(
                currentUser.email,
                'remove',
                { id: college.university_id, name: college.university_name },
                ''
            );

            console.log('[Launchpad] Remove result:', result);

            if (result.success) {
                setCollegeList(prev =>
                    prev.filter(c => c.university_id !== college.university_id)
                );
            } else {
                console.error('Failed to remove:', result.error);
            }
        } catch (err) {
            console.error('Error removing college:', err);
        } finally {
            setRemovingId(null);
        }
    };

    // Quick-start handler - directly calls API based on action
    const [quickStartPrompt, setQuickStartPrompt] = useState(null);
    const [quickStartLoading, setQuickStartLoading] = useState(false);
    const [quickStartRecommendations, setQuickStartRecommendations] = useState([]);
    const [quickStartSelected, setQuickStartSelected] = useState({});  // {id: true/false}
    const [quickStartAdding, setQuickStartAdding] = useState(false);

    // Toggle selection of a quick start recommendation
    const toggleQuickStartSelection = (id) => {
        setQuickStartSelected(prev => ({ ...prev, [id]: !prev[id] }));
    };

    // Confirm and add all selected quick start recommendations
    const handleQuickStartConfirm = async () => {
        const selectedRecs = quickStartRecommendations.filter(r => quickStartSelected[r.id]);
        if (selectedRecs.length === 0) return;

        setQuickStartAdding(true);
        try {
            // Add all selected colleges
            for (const rec of selectedRecs) {
                console.log(`[Quick Start] Adding: ${rec.name} as ${rec.fit_category}`);
                await updateCollegeList(currentUser.email, 'add', { id: rec.id, name: rec.name }, '');
            }
            // Clear quick start state and refresh college list
            setQuickStartPrompt(null);
            setQuickStartRecommendations([]);
            setQuickStartSelected({});
            fetchCollegeList();
        } catch (err) {
            console.error('[Quick Start] Error adding colleges:', err);
        } finally {
            setQuickStartAdding(false);
        }
    };

    const handleQuickStart = async (action) => {
        if (!currentUser?.email) return;

        setQuickStartLoading(true);
        setQuickStartPrompt(action);  // This triggers the special view

        try {
            // Get existing college IDs to exclude
            const existingIds = collegeList.map(c => c.university_id).filter(Boolean);
            console.log(`[Quick Start] Action: ${action}, excluding ${existingIds.length} existing colleges`);

            let result;

            if (action === 'balanced') {
                result = await getBalancedList(currentUser.email, existingIds);
            } else if (action === 'REACH') {
                // For REACH, also include SUPER_REACH schools
                const [reachResult, superReachResult] = await Promise.all([
                    getFitsByCategory(currentUser.email, 'REACH', null, existingIds, 10),
                    getFitsByCategory(currentUser.email, 'SUPER_REACH', null, existingIds, 5)
                ]);
                const combined = [
                    ...(reachResult.results || []),
                    ...(superReachResult.results || [])
                ];
                result = { success: true, results: combined };
            } else {
                // SAFETY or TARGET
                result = await getFitsByCategory(currentUser.email, action, null, existingIds, 10);
            }

            if (result.success && result.results?.length > 0) {
                // Transform to recommendation format and sort by match score descending
                const recs = result.results.map((fit, idx) => ({
                    id: fit.university_id || `rec-${idx}`,
                    name: fit.university_name || fit.official_name || 'Unknown',
                    fit_category: fit.fit_category,
                    matchScore: fit.match_percentage || fit.match_score || 0,
                    location: fit.location ? `${fit.location.city}, ${fit.location.state}` : null,
                    reason: `${fit.fit_category?.replace('_', ' ')} school with ${fit.match_percentage || fit.match_score || 0}% match`,
                    selected: true
                })).sort((a, b) => b.matchScore - a.matchScore);  // Sort by match score descending
                setQuickStartRecommendations(recs);
                console.log(`[Quick Start] Loaded ${recs.length} recommendations`);
            }
        } catch (err) {
            console.error('[Quick Start] Error:', err);
        } finally {
            setQuickStartLoading(false);
        }
    };

    // Toggle selection of a college
    const toggleSelection = (universityId) => {
        setSelectedColleges(prev => {
            const newSet = new Set(prev);
            if (newSet.has(universityId)) {
                newSet.delete(universityId);
            } else {
                newSet.add(universityId);
            }
            return newSet;
        });
    };

    // Select all / Deselect all
    const toggleSelectAll = () => {
        if (selectedColleges.size === collegeList.length) {
            setSelectedColleges(new Set());
        } else {
            setSelectedColleges(new Set(collegeList.map(c => c.university_id)));
        }
    };

    // Bulk remove selected colleges
    const handleBulkRemove = async () => {
        if (selectedColleges.size === 0) return;

        const confirmRemove = window.confirm(
            `Are you sure you want to remove ${selectedColleges.size} college${selectedColleges.size > 1 ? 's' : ''} from your list?`
        );

        if (!confirmRemove) return;

        setBulkRemoving(true);
        try {
            const response = await fetch(`${import.meta.env.VITE_PROFILE_MANAGER_ES_URL}/bulk-remove-colleges`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_ids: Array.from(selectedColleges)
                })
            });

            const data = await response.json();

            if (data.success) {
                setCollegeList(data.college_list || []);
                setSelectedColleges(new Set());
                setSelectionMode(false);
            } else {
                setError(data.error || 'Failed to remove colleges');
            }
        } catch (err) {
            console.error('Bulk remove error:', err);
            setError('Failed to remove colleges');
        } finally {
            setBulkRemoving(false);
        }
    };


    // Categorize colleges by fit
    const categorizedColleges = useMemo(() => {
        const categories = {
            SUPER_REACH: [],
            REACH: [],
            TARGET: [],
            SAFETY: []
        };

        collegeList.forEach(college => {
            const fitCategory = college.fit_analysis?.fit_category || 'TARGET';
            if (categories[fitCategory]) {
                categories[fitCategory].push(college);
            } else {
                categories.TARGET.push(college);
            }
        });

        return categories;
    }, [collegeList]);

    // Stats
    const totalColleges = collegeList.length;
    const analyzedCount = collegeList.filter(c => c.fit_analysis).length;

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500 mx-auto mb-4"></div>
                    <p className="text-gray-500">Loading your college list...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
                <ExclamationCircleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-red-700 mb-2">Unable to Load</h3>
                <p className="text-red-600 mb-4">{error}</p>
                <button
                    onClick={fetchCollegeList}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                >
                    <ArrowPathIcon className="h-4 w-4" />
                    Try Again
                </button>
            </div>
        );
    }

    if (totalColleges === 0 && !quickStartPrompt) {
        return <EmptyState onQuickStart={handleQuickStart} />;
    }

    // If quick-start was triggered, show recommendations directly (no SmartDiscoveryPanel needed)
    if (totalColleges === 0 && quickStartPrompt) {
        return (
            <div className="space-y-6">
                <div className="text-center py-6">
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center justify-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg shadow-amber-200">
                            <RocketLaunchIcon className="h-6 w-6 text-white" />
                        </div>
                        Building Your College List
                    </h1>
                    <p className="text-gray-500 mt-2">
                        {quickStartLoading ? 'Finding the best schools for your profile...' : `Found ${quickStartRecommendations.length} schools for you!`}
                    </p>
                </div>

                {/* Loading State */}
                {quickStartLoading && (
                    <div className="flex justify-center py-8">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500"></div>
                    </div>
                )}

                {/* Recommendations Grid - Card View with Selection */}
                {!quickStartLoading && quickStartRecommendations.length > 0 && (
                    <>
                        <p className="text-sm text-gray-500 text-center mb-2">
                            Click to select schools, then add to your launchpad
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {quickStartRecommendations.map((rec) => (
                                <RecommendationCard
                                    key={rec.id}
                                    recommendation={rec}
                                    isSelected={!!quickStartSelected[rec.id]}
                                    onToggleSelect={toggleQuickStartSelection}
                                />
                            ))}
                        </div>

                        {/* Selection Summary and Confirm Button */}
                        {Object.values(quickStartSelected).filter(Boolean).length > 0 && (
                            <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center items-center">
                                <span className="text-sm text-gray-600">
                                    {Object.values(quickStartSelected).filter(Boolean).length} school(s) selected
                                </span>
                                <button
                                    onClick={handleQuickStartConfirm}
                                    disabled={quickStartAdding}
                                    className="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-medium hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200 disabled:opacity-50 flex items-center gap-2"
                                >
                                    {quickStartAdding ? (
                                        <>
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                            Adding...
                                        </>
                                    ) : (
                                        <>
                                            <PlusCircleIcon className="h-5 w-5" />
                                            Add to Launchpad
                                        </>
                                    )}
                                </button>
                            </div>
                        )}
                    </>
                )}

                <button
                    onClick={() => { setQuickStartPrompt(null); setQuickStartRecommendations([]); setQuickStartSelected({}); }}
                    className="w-full text-gray-500 hover:text-gray-700 text-sm mt-4"
                >
                    ← Back to options
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Recomputation Banner */}
            {recomputingFits && (
                <div className="bg-purple-100 border-l-4 border-purple-500 text-purple-700 p-4 rounded shadow-sm" role="alert">
                    <div className="flex items-center">
                        <div className="py-1">
                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-purple-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        </div>
                        <div>
                            <p className="font-bold">Updating your matches</p>
                            <p className="text-sm">We noticed changes in your profile. Recalculating your fit scores for all universities...</p>
                        </div>
                    </div>
                </div>
            )}
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg shadow-amber-200">
                            <RocketLaunchIcon className="h-6 w-6 text-white" />
                        </div>
                        My Launchpad
                    </h1>
                    <p className="text-gray-500 mt-1">
                        {totalColleges} school{totalColleges !== 1 ? 's' : ''} in your list
                        {analyzedCount < totalColleges && (
                            <span className="ml-2 text-amber-600">
                                ({totalColleges - analyzedCount} pending analysis)
                            </span>
                        )}
                    </p>
                </div>

                {/* Selection Mode Controls */}
                <div className="flex items-center gap-2">
                    {selectionMode ? (
                        <>
                            <button
                                onClick={toggleSelectAll}
                                className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                            >
                                {selectedColleges.size === collegeList.length ? 'Deselect All' : 'Select All'}
                            </button>
                            <button
                                onClick={handleBulkRemove}
                                disabled={selectedColleges.size === 0 || bulkRemoving}
                                className="px-3 py-2 text-sm bg-red-600 hover:bg-red-700 disabled:bg-gray-300 text-white rounded-lg transition-colors flex items-center gap-2"
                            >
                                {bulkRemoving ? (
                                    <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                ) : (
                                    <TrashIcon className="h-4 w-4" />
                                )}
                                Remove ({selectedColleges.size})
                            </button>
                            <button
                                onClick={() => {
                                    setSelectionMode(false);
                                    setSelectedColleges(new Set());
                                }}
                                className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700"
                            >
                                Cancel
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={() => setSelectionMode(true)}
                            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors flex items-center gap-2"
                        >
                            <TrashIcon className="h-4 w-4" />
                            Bulk Remove
                        </button>
                    )}
                </div>
                <button
                    onClick={fetchCollegeList}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors shadow-sm"
                >
                    <ArrowPathIcon className="h-4 w-4" />
                    Refresh
                </button>
            </div>

            {/* Stats Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {Object.entries(FIT_CATEGORIES).map(([key, config]) => (
                    <div
                        key={key}
                        className={`bg-gradient-to-r ${config.bgGradient} rounded-xl p-4 border ${config.borderColor}`}
                    >
                        <div className="flex items-center gap-2 mb-1">
                            <span className="text-lg">{config.emoji}</span>
                            <span className={`text-sm font-medium ${config.textColor}`}>{config.label}</span>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">
                            {categorizedColleges[key]?.length || 0}
                        </div>
                    </div>
                ))}
            </div>

            {/* Smart Discovery Panel */}
            <SmartDiscoveryPanel
                currentUser={currentUser}
                categorizedColleges={categorizedColleges}
                onCollegeAdded={fetchCollegeList}
            />

            {/* Detail View (when a university is selected) */}
            {selectedUniversity && (
                <div className="mt-6">
                    <FitAnalysisDetail
                        college={selectedUniversity}
                        onBack={() => setSelectedUniversity(null)}
                    />
                </div>
            )}

            {/* Three-Column Layout (hidden when viewing details) */}
            {!selectedUniversity && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Combine Super Reach + Reach into one column */}
                    <CategoryColumn
                        category="REACH"
                        colleges={[...categorizedColleges.SUPER_REACH, ...categorizedColleges.REACH]}
                        onRemove={handleRemove}
                        removingId={removingId}
                        onViewDetails={(college) => setSelectedUniversity(college)}
                        selectedColleges={selectedColleges}
                        onToggleSelect={toggleSelection}
                        selectionMode={selectionMode}
                    />
                    <CategoryColumn
                        category="TARGET"
                        colleges={categorizedColleges.TARGET}
                        onRemove={handleRemove}
                        removingId={removingId}
                        onViewDetails={(college) => setSelectedUniversity(college)}
                        selectedColleges={selectedColleges}
                        onToggleSelect={toggleSelection}
                        selectionMode={selectionMode}
                    />
                    <CategoryColumn
                        category="SAFETY"
                        colleges={categorizedColleges.SAFETY}
                        onRemove={handleRemove}
                        removingId={removingId}
                        onViewDetails={(college) => setSelectedUniversity(college)}
                        selectedColleges={selectedColleges}
                        onToggleSelect={toggleSelection}
                        selectionMode={selectionMode}
                    />
                </div>
            )}
        </div>
    );
};

export default MyLaunchpad;
