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
    XMarkIcon
} from '@heroicons/react/24/outline';
import { getCollegeList, updateCollegeList, startSession, extractFullResponse } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { UniversityDetail } from '../components/UniversityComponents';

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
const LaunchpadCard = ({ college, onRemove, isRemoving, onViewDetails }) => {
    const fitAnalysis = college.fit_analysis || {};
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
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg transition-all duration-300 flex flex-col h-full">
            <div className="p-5 flex-grow">
                {/* Header */}
                <div className="flex justify-between items-start mb-3">
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-bold text-gray-900 line-clamp-2" title={college.university_name}>
                            {college.university_name}
                        </h3>
                        <div className="flex items-center text-gray-500 text-sm mt-1">
                            <MapPinIcon className="h-4 w-4 mr-1 flex-shrink-0" />
                            <span className="truncate">{college.location || 'Location N/A'}</span>
                        </div>
                    </div>
                    {/* Fit Badge */}
                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold border whitespace-nowrap ${fitColors[fitCategory] || fitColors.TARGET}`}>
                        {categoryConfig.emoji} {categoryConfig.label}
                        {matchPercentage && ` ${matchPercentage}%`}
                    </span>
                </div>

                {/* Stats Grid - similar to UniInsight */}
                <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                    <div className="bg-gray-50 p-2 rounded">
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

                {/* Key Factors */}
                {fitAnalysis.key_factors && fitAnalysis.key_factors.length > 0 && (
                    <div className="text-xs text-gray-600 bg-gray-50 rounded p-2">
                        <span className="font-medium text-gray-700">Key Factors: </span>
                        {fitAnalysis.key_factors.slice(0, 3).join(' • ')}
                    </div>
                )}
                {fitAnalysis.factors && fitAnalysis.factors.length > 0 && !fitAnalysis.key_factors && (
                    <div className="text-xs text-gray-600 bg-gray-50 rounded p-2">
                        <span className="font-medium text-gray-700">Key Factors: </span>
                        {fitAnalysis.factors.slice(0, 3).map(f => f.name || f).join(' • ')}
                    </div>
                )}
            </div>

            {/* Footer with action buttons - matches UniInsight */}
            <div className="p-4 border-t border-gray-100">
                <div className="flex gap-2">
                    <button
                        onClick={() => onViewDetails && onViewDetails(college)}
                        className="flex-1 bg-white border border-gray-300 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center justify-center gap-1"
                    >
                        View Details
                        <ArrowTrendingUpIcon className="h-4 w-4" />
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
const CategoryColumn = ({ category, colleges, onRemove, removingId, onViewDetails }) => {
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
                        />
                    ))
                )}
            </div>
        </div>
    );
};

// Recommendation Card Component
const RecommendationCard = ({ recommendation, onAdd, isAdding }) => {
    const fitCategory = recommendation.fit_category || 'TARGET';
    const categoryConfig = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 hover:shadow-md transition-all">
            <div className="flex justify-between items-start mb-2">
                <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-gray-900 truncate">{recommendation.name}</h4>
                    <div className="flex items-center text-gray-500 text-xs mt-0.5">
                        <MapPinIcon className="h-3 w-3 mr-1" />
                        <span>{recommendation.location || 'Location N/A'}</span>
                    </div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${categoryConfig.headerBg} ${categoryConfig.textColor}`}>
                    {categoryConfig.emoji} {categoryConfig.label}
                </span>
            </div>
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">{recommendation.reason}</p>
            <button
                type="button"
                onClick={(e) => { e.preventDefault(); e.stopPropagation(); onAdd(recommendation); }}
                disabled={isAdding}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-purple-100 text-purple-700 rounded-lg text-sm font-medium hover:bg-purple-200 transition-colors disabled:opacity-50"
            >
                {isAdding ? (
                    <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-700"></div>
                        Adding...
                    </>
                ) : (
                    <>
                        <PlusCircleIcon className="h-4 w-4" />
                        Add to Launchpad
                    </>
                )}
            </button>
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
            const uniNameMatch = line.match(/^[\s\-\*\d\.]*\**([A-Z][A-Za-z\s&]+(?:University|College|Institute|MIT|UCLA|USC|Caltech|Stanford|Princeton|Harvard|Yale)[\w\s]*)\**[\s\-:,]*(.*)/i);
            if (uniNameMatch && uniNameMatch[1].length > 5 && uniNameMatch[1].length < 80) {
                const universityName = uniNameMatch[1].replace(/\*+/g, '').trim();
                const rest = uniNameMatch[2] || '';

                // Check if this looks like a university name (not a description)
                if (!/^\s*(is|are|has|the|a|an|this)\s/i.test(universityName)) {
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

    // Auto-trigger with initialPrompt on first render
    useEffect(() => {
        if (initialPrompt && !hasAutoTriggered && currentUser?.email) {
            setHasAutoTriggered(true);
            handleGetRecommendations(`[USER_EMAIL: ${currentUser.email}]\n\n${initialPrompt}`);
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
                // Use updateCollegeList API directly
                const result = await updateCollegeList(
                    currentUser.email,
                    'add',
                    { id: rec.name.toLowerCase().replace(/\s+/g, '_'), name: rec.name },
                    '' // intended major
                );

                if (result.success) {
                    addedCount++;
                    console.log(`[Smart Discovery] Added: ${rec.name}`);
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
                                onClick={() => handleGetRecommendations("Build me a balanced college list with safety, target, and reach schools that match my academic profile")}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-purple-200 text-purple-700 rounded-full text-sm font-medium hover:bg-purple-50 transition-colors disabled:opacity-50"
                            >
                                ⚖️ Balanced List
                            </button>
                            <button
                                onClick={() => handleGetRecommendations("Find me safety schools where I have a very strong chance of admission based on my GPA and test scores")}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-green-200 text-green-700 rounded-full text-sm font-medium hover:bg-green-50 transition-colors disabled:opacity-50"
                            >
                                🛡️ More Safety Schools
                            </button>
                            <button
                                onClick={() => handleGetRecommendations("Recommend target schools where my profile is a good match for admission and academic programs")}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-blue-200 text-blue-700 rounded-full text-sm font-medium hover:bg-blue-50 transition-colors disabled:opacity-50"
                            >
                                ✅ More Target Schools
                            </button>
                            <button
                                onClick={() => handleGetRecommendations("Find reach schools including top-ranked universities where I could be competitive based on my profile")}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-orange-200 text-orange-700 rounded-full text-sm font-medium hover:bg-orange-50 transition-colors disabled:opacity-50"
                            >
                                🎯 More Reach Schools
                            </button>
                            <button
                                onClick={() => handleGetRecommendations("Find schools with strong programs for my intended major that match my academic profile")}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-indigo-200 text-indigo-700 rounded-full text-sm font-medium hover:bg-indigo-50 transition-colors disabled:opacity-50"
                            >
                                📚 Strong in My Major
                            </button>
                            <button
                                onClick={() => handleGetRecommendations("Find universities in California that match my profile")}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-amber-200 text-amber-700 rounded-full text-sm font-medium hover:bg-amber-50 transition-colors disabled:opacity-50"
                            >
                                🌴 California Schools
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
                        onClick={handleGetRecommendations}
                        disabled={isLoading}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-xl font-medium hover:from-purple-700 hover:to-blue-700 transition-all shadow-lg disabled:opacity-50 mb-4"
                    >
                        <SparklesIcon className="h-5 w-5" />
                        {recommendations.length > 0 ? 'Get More Recommendations' : 'Get AI Recommendations'}
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
                                onClick={handleGetRecommendations}
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

                            {/* List with checkboxes */}
                            <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
                                {recommendations.map(rec => (
                                    <label key={rec.id} className="p-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50">
                                        <input
                                            type="checkbox"
                                            checked={!!selectedRecs[rec.id]}
                                            onChange={() => toggleSelection(rec.id)}
                                            className="h-4 w-4 text-green-600 rounded border-gray-300 focus:ring-green-500"
                                        />
                                        <div className="flex-1">
                                            <span className="font-medium text-gray-900">{rec.name}</span>
                                            <span className="ml-2 text-xs text-gray-500">{rec.location}</span>
                                        </div>
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${rec.fit_category === 'SAFETY' ? 'bg-green-100 text-green-700' :
                                            rec.fit_category === 'TARGET' ? 'bg-blue-100 text-blue-700' :
                                                'bg-orange-100 text-orange-700'
                                            }`}>
                                            {rec.fit_category}
                                        </span>
                                    </label>
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
                                onClick={handleGetRecommendations}
                                disabled={isAddingAll}
                                className="w-full text-sm text-purple-600 hover:text-purple-800 font-medium disabled:opacity-50"
                            >
                                ↻ Get different recommendations
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
            prompt: 'Build me a balanced college list with 2 safety schools, 3 target schools, and 2 reach schools that match my academic profile and interests.',
            color: 'from-purple-600 to-blue-600'
        },
        {
            id: 'safety',
            emoji: '🛡️',
            title: 'Find Safety Schools',
            description: 'Schools where you\'re likely to be admitted',
            prompt: 'Find me 5 good safety schools where I have a strong chance of admission based on my academic profile.',
            color: 'from-green-600 to-emerald-600'
        },
        {
            id: 'reach',
            emoji: '🎯',
            title: 'Find Reach Schools',
            description: 'Ambitious choices to aim high',
            prompt: 'Find me 5 reach and super-reach schools that would be ambitious but possible based on my profile.',
            color: 'from-orange-600 to-red-600'
        },
        {
            id: 'top20',
            emoji: '🏆',
            title: 'Top 20 Schools For Me',
            description: 'Best-ranked schools that fit your profile',
            prompt: 'Find me schools from the US News Top 50 that best match my academic profile and interests.',
            color: 'from-yellow-600 to-orange-600'
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
                        onClick={() => onQuickStart(option.prompt)}
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

    // Fetch college list
    const fetchCollegeList = async () => {
        if (!currentUser?.email) return;

        setLoading(true);
        setError(null);

        try {
            const result = await getCollegeList(currentUser.email);
            if (result.success) {
                setCollegeList(result.college_list || []);
            } else {
                setError(result.error || 'Failed to load college list');
            }
        } catch (err) {
            console.error('Error fetching college list:', err);
            setError('Unable to load your college list. Please try again.');
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

    // Quick-start handler - triggers Smart Discovery with preset prompt
    const [quickStartPrompt, setQuickStartPrompt] = useState(null);
    const handleQuickStart = (prompt) => {
        setQuickStartPrompt(prompt);
        // Redirect to show the normal view with Smart Discovery open
        // This is a bit of a hack - we'll render normally and let SmartDiscoveryPanel auto-trigger
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
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
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

    // If quick-start was triggered, show a special view with Smart Discovery
    if (totalColleges === 0 && quickStartPrompt) {
        return (
            <div className="space-y-6">
                <div className="text-center py-6">
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center justify-center gap-3">
                        <RocketLaunchIcon className="h-7 w-7 text-purple-600" />
                        Building Your College List
                    </h1>
                    <p className="text-gray-500 mt-2">Finding the best schools for your profile...</p>
                </div>
                <SmartDiscoveryPanel
                    currentUser={currentUser}
                    categorizedColleges={categorizedColleges}
                    onCollegeAdded={() => {
                        setQuickStartPrompt(null);
                        fetchCollegeList();
                    }}
                    initialPrompt={quickStartPrompt}
                />
                <button
                    onClick={() => setQuickStartPrompt(null)}
                    className="w-full text-gray-500 hover:text-gray-700 text-sm"
                >
                    ← Back to options
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                        <RocketLaunchIcon className="h-7 w-7 text-purple-600" />
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
                    <UniversityDetail
                        uni={{
                            id: selectedUniversity.university_id,
                            name: selectedUniversity.university_name,
                            university_id: selectedUniversity.university_id,
                            university_name: selectedUniversity.university_name,
                            location: selectedUniversity.location ? {
                                city: selectedUniversity.location.split(',')[0]?.trim() || 'N/A',
                                state: selectedUniversity.location.split(',')[1]?.trim() || 'N/A',
                                type: 'N/A'
                            } : { city: 'N/A', state: 'N/A', type: 'N/A' },
                            summary: 'View full details in UniInsight for complete information.',
                            rankings: { usNews: 'N/A', forbes: 'N/A' },
                            admissions: { acceptanceRate: 'N/A', gpa: 'N/A', testPolicy: 'N/A' },
                            financials: {},
                            outcomes: {},
                            majors: []
                        }}
                        onBack={() => setSelectedUniversity(null)}
                        sentiment={null}
                        deepResearchData={deepResearchData}
                        setDeepResearchData={setDeepResearchData}
                        fitAnalysis={selectedUniversity.fit_analysis}
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
                    />
                    <CategoryColumn
                        category="TARGET"
                        colleges={categorizedColleges.TARGET}
                        onRemove={handleRemove}
                        removingId={removingId}
                        onViewDetails={(college) => setSelectedUniversity(college)}
                    />
                    <CategoryColumn
                        category="SAFETY"
                        colleges={categorizedColleges.SAFETY}
                        onRemove={handleRemove}
                        removingId={removingId}
                        onViewDetails={(college) => setSelectedUniversity(college)}
                    />
                </div>
            )}
        </div>
    );
};

export default MyLaunchpad;
