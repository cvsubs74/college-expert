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
import { usePayment } from '../context/PaymentContext';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FitBreakdownPanel from '../components/FitBreakdownPanel';
import CreditsBadge from '../components/CreditsBadge';
import CreditsUpgradeModal from '../components/CreditsUpgradeModal';
import FitChatWidget from '../components/FitChatWidget';
import FitInfographicView from '../components/FitInfographicView';
import FitAnalysisPage from '../components/FitAnalysisPage';
import DeadlineTracker from '../components/DeadlineTracker';
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

// Fit category configuration - Uses Stratia theme colors
const FIT_CATEGORIES = {
    REACH: {
        label: 'Reach',
        emoji: '🎯',
        color: 'terracotta',
        bgGradient: 'from-[#FCEEE8] to-[#FDF8F6]',
        borderColor: 'border-[#E8A090]',
        headerBg: 'bg-[#FCEEE8]',
        textColor: 'text-[#C05838]',
        description: 'Challenging admits',
        icon: LightBulbIcon
    },
    SUPER_REACH: {
        label: 'Super Reach',
        emoji: '🌟',
        color: 'rose',
        bgGradient: 'from-rose-50 to-[#FCEEE8]',
        borderColor: 'border-rose-300',
        headerBg: 'bg-rose-100',
        textColor: 'text-rose-700',
        description: 'Dream schools',
        icon: SparklesIcon
    },
    TARGET: {
        label: 'Target',
        emoji: '✅',
        color: 'blue',
        bgGradient: 'from-blue-50 to-[#F8F6F0]',
        borderColor: 'border-blue-200',
        headerBg: 'bg-blue-50',
        textColor: 'text-blue-700',
        description: 'Good match',
        icon: ArrowTrendingUpIcon
    },
    SAFETY: {
        label: 'Safety',
        emoji: '🛡️',
        color: 'stratia-green',
        bgGradient: 'from-[#D6E8D5] to-[#F8F6F0]',
        borderColor: 'border-[#A8C5A6]',
        headerBg: 'bg-[#D6E8D5]',
        textColor: 'text-[#1A4D2E]',
        description: 'Likely admits',
        icon: CheckCircleIcon
    }
};

// College Card Component for Launchpad - matches UniInsight style
const LaunchpadCard = ({ college, onRemove, isRemoving, onViewDetails, isSelected, onToggleSelect, selectionMode, onOpenChat, canRemove = true }) => {
    const fitAnalysis = college.fit_analysis || {};
    const hasFitAnalysis = fitAnalysis && fitAnalysis.fit_category; // Only true if we have actual fit data
    // Use fit_analysis category first, then fallback to soft_fit_category (pre-computed based on acceptance rate)
    const fitCategory = fitAnalysis.fit_category || college.soft_fit_category || 'TARGET';
    const matchPercentage = fitAnalysis.match_percentage || fitAnalysis.match_score || null;
    const categoryConfig = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;

    // Fit category colors matching Stratia theme
    const fitColors = {
        SAFETY: 'bg-[#D6E8D5] text-[#1A4D2E] border-[#A8C5A6]',
        TARGET: 'bg-blue-100 text-blue-800 border-blue-300',
        REACH: 'bg-[#FCEEE8] text-[#C05838] border-[#E8A090]',
        SUPER_REACH: 'bg-rose-100 text-rose-800 border-rose-300'
    };

    const formatNumber = (num) => {
        if (!num || num === 'N/A') return 'N/A';
        return typeof num === 'number' ? num.toLocaleString() : num;
    };

    return (
        <div className={`group relative bg-white rounded-2xl border border-gray-200 transition-all hover:shadow-md hover:border-gray-300 flex items-center p-4 gap-5 ${isRemoving ? 'opacity-50' : ''}`}>

            {/* Selection Checkbox */}
            {selectionMode && (
                <div className="flex-shrink-0">
                    <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect(college.university_id)}
                        className="h-5 w-5 text-[#C05838] rounded-md border-gray-300 focus:ring-[#1A4D2E] cursor-pointer"
                    />
                </div>
            )}

            {/* Main Info Section */}
            <div className="flex-1 min-w-0 grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                {/* University Details with Logo */}
                <div className="md:col-span-5 flex items-center gap-3">
                    {/* Logo */}
                    <div className="w-11 h-11 rounded-full bg-[#F8F6F0] flex items-center justify-center flex-shrink-0 border border-[#E0DED8] overflow-hidden">
                        {college.logo_url ? (
                            <img src={college.logo_url} alt={`${college.university_name} logo`} className="w-full h-full object-contain p-1" />
                        ) : (
                            <span className="text-lg font-bold text-[#4A4A4A]">{college.university_name?.charAt(0) || 'U'}</span>
                        )}
                    </div>
                    {/* Name and Location */}
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-bold text-gray-900 truncate" title={college.university_name}>
                            {college.university_name}
                        </h3>
                        <div className="flex items-center text-gray-500 text-sm mt-1">
                            <MapPinIcon className="h-4 w-4 mr-1 flex-shrink-0" />
                            <span className="truncate">{college.location || 'Location N/A'}</span>
                        </div>
                    </div>
                </div>

                {/* Fit Status Badge */}
                <div className="md:col-span-4 flex items-center">
                    {hasFitAnalysis ? (
                        <div className={`px-3 py-1.5 rounded-full text-xs font-bold border flex items-center gap-2 ${fitColors[fitCategory] || fitColors.TARGET}`}>
                            <span className="text-base">{categoryConfig.emoji}</span>
                            <span>{categoryConfig.label}</span>
                            <span className="w-px h-3 bg-current opacity-30 mx-1"></span>
                            <span>{matchPercentage ? `${matchPercentage}% Match` : 'N/A'}</span>
                        </div>
                    ) : (
                        <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 flex items-center gap-1.5">
                            <SparklesIcon className="h-3.5 w-3.5" />
                            <span>Pending Analysis</span>
                        </span>
                    )}
                </div>

                {/* Actions */}
                <div className="md:col-span-3 flex items-center justify-end gap-2">
                    <button
                        onClick={() => onViewDetails && onViewDetails(college)}
                        className="p-2 text-gray-600 hover:text-[#1A4D2E] hover:bg-[#D6E8D5] rounded-lg transition-colors flex items-center gap-2"
                        title="View Fit Analysis"
                    >
                        <ChartBarIcon className="h-5 w-5" />
                        <span className="hidden xl:inline text-sm font-medium">Analysis</span>
                    </button>

                    {onOpenChat && (
                        <button
                            onClick={() => onOpenChat(college)}
                            className="p-2 text-gray-600 hover:text-[#1A4D2E] hover:bg-[#D6E8D5] rounded-lg transition-colors"
                            title="Ask AI"
                        >
                            <ChatBubbleLeftRightIcon className="h-5 w-5" />
                        </button>
                    )}

                    {canRemove && (
                        <button
                            onClick={() => onRemove(college)}
                            disabled={isRemoving}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Remove"
                        >
                            <TrashIcon className="h-5 w-5" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

// Category Column Component - Minimalist (Just a list of cards, no blocks)
const CategoryColumn = ({ category, colleges, onRemove, removingId, onViewDetails, selectedColleges, onToggleSelect, selectionMode, onOpenChat, canRemove = true }) => {
    // Hide empty categories to avoid "empty blocks"
    if (!colleges || colleges.length === 0) return null;

    return (
        <div className="space-y-4">
            {colleges.map((college) => (
                <LaunchpadCard
                    key={college.university_id}
                    college={college}
                    onRemove={onRemove}
                    isRemoving={removingId === college.university_id}
                    onViewDetails={onViewDetails}
                    isSelected={selectedColleges.has(college.university_id)}
                    onToggleSelect={onToggleSelect}
                    selectionMode={selectionMode}
                    onOpenChat={onOpenChat}
                    canRemove={canRemove}
                />
            ))}
        </div>
    );
};

// Detailed Fit Analysis Component (shown when clicking "Details" on a college)
const FitAnalysisDetail = ({ college, onBack }) => {
    const { currentUser } = useAuth();

    // Debug: log incoming college data
    console.log('[FitAnalysisDetail] Received college:', college?.university_name, 'fit_analysis:', college?.fit_analysis);

    // Use state for fit analysis so we can update it after fetching
    const [fitAnalysis, setFitAnalysis] = useState(college.fit_analysis || {});
    const [fitLoading, setFitLoading] = useState(false);

    // Fetch fit analysis on-demand if missing
    useEffect(() => {
        const fetchFitAnalysis = async () => {
            // Check if we already have meaningful fit data
            const hasFitData = fitAnalysis &&
                (fitAnalysis.explanation || fitAnalysis.match_score || fitAnalysis.match_percentage || fitAnalysis.factors?.length > 0);

            console.log('[FitAnalysisDetail] hasFitData:', hasFitData, 'fitAnalysis:', fitAnalysis);

            if (!hasFitData && currentUser?.email && college?.university_id) {
                console.log('[FitAnalysisDetail] Fetching fit analysis for', college.university_name);
                setFitLoading(true);
                try {
                    // Use the correct API function that calls POST /get-fits
                    const data = await getPrecomputedFits(currentUser.email, {}, 500);
                    console.log('[FitAnalysisDetail] API response:', data);

                    if (data.success && data.fits) {
                        const fit = data.fits.find(f => f.university_id === college.university_id);
                        if (fit) {
                            console.log('[FitAnalysisDetail] Found fit analysis:', fit.fit_category, 'match_percentage:', fit.match_percentage);
                            setFitAnalysis({
                                fit_category: fit.fit_category,
                                match_score: fit.match_score,
                                match_percentage: fit.match_percentage,
                                explanation: fit.explanation,
                                factors: fit.factors,
                                recommendations: fit.recommendations,
                                gap_analysis: fit.gap_analysis,
                                essay_angles: fit.essay_angles,
                                application_timeline: fit.application_timeline,
                                scholarship_matches: fit.scholarship_matches,
                                test_strategy: fit.test_strategy,
                                major_strategy: fit.major_strategy,
                                demonstrated_interest_tips: fit.demonstrated_interest_tips,
                                red_flags_to_avoid: fit.red_flags_to_avoid,
                                infographic_url: fit.infographic_url
                            });
                        } else {
                            console.log('[FitAnalysisDetail] No fit found for', college.university_id, 'in', data.fits.length, 'fits');
                        }
                    }
                } catch (err) {
                    console.error('[FitAnalysisDetail] Failed to fetch fit:', err);
                } finally {
                    setFitLoading(false);
                }
            }
        };
        fetchFitAnalysis();
    }, [currentUser?.email, college?.university_id]);

    // Show loading indicator while fetching fit data
    if (fitLoading) {
        return (
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden p-8">
                <div className="flex items-center justify-center gap-3 text-gray-500">
                    <ArrowPathIcon className="h-6 w-6 animate-spin" />
                    <span>Loading fit analysis for {college.university_name}...</span>
                </div>
            </div>
        );
    }

    // Use fit_analysis category first, then fallback to soft_fit_category (pre-computed based on acceptance rate)
    const fitCategory = fitAnalysis.fit_category || college.soft_fit_category || 'TARGET';
    const matchScore = fitAnalysis.match_percentage || fitAnalysis.match_score || 50;
    const config = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;

    // Get explanation or generate a default one
    const explanation = fitAnalysis.explanation ||
        `Based on your academic profile, ${college.university_name} is a ${fitCategory.replace('_', ' ').toLowerCase()} school for you with a ${matchScore}% match score.`;

    // Use real factors from backend if available, otherwise use defaults
    const backendFactors = fitAnalysis.factors || [];

    // Helper to parse JSON strings (some fields are stored as JSON strings in ES)
    const parseJsonField = (field) => {
        if (!field) return null;
        if (typeof field === 'object') return field;
        try {
            return JSON.parse(field);
        } catch (e) {
            return null;
        }
    };

    // Extract all rich data from fit analysis
    const essayAngles = parseJsonField(fitAnalysis.essay_angles) || [];
    const applicationTimeline = parseJsonField(fitAnalysis.application_timeline);
    const scholarshipMatches = parseJsonField(fitAnalysis.scholarship_matches) || [];
    const testStrategy = parseJsonField(fitAnalysis.test_strategy);
    const majorStrategy = parseJsonField(fitAnalysis.major_strategy);
    const demonstratedInterestTips = parseJsonField(fitAnalysis.demonstrated_interest_tips) || [];
    const redFlagsToAvoid = parseJsonField(fitAnalysis.red_flags_to_avoid) || [];
    const gapAnalysis = parseJsonField(fitAnalysis.gap_analysis);


    // Student profile state
    const [studentProfile, setStudentProfile] = useState(null);
    const [profileLoading, setProfileLoading] = useState(true);
    const [profileExists, setProfileExists] = useState(false);

    // Fetch student profile
    useEffect(() => {
        if (currentUser?.email) {
            setProfileLoading(true);
            fetch(`https://profile-manager-es-pfnwjfp26a-ue.a.run.app/get-profile?user_email=${encodeURIComponent(currentUser.email)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.profile) {
                        setStudentProfile(data.profile);
                        setProfileExists(true);
                    } else {
                        setProfileExists(false);
                    }
                })
                .catch(err => {
                    console.error('Failed to fetch profile:', err);
                    setProfileExists(false);
                })
                .finally(() => setProfileLoading(false));
        } else {
            setProfileLoading(false);
            setProfileExists(false);
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

    // Prepare infographic data from fit analysis
    const infographicData = {
        title: `Your Fit Analysis: ${college.university_name}`,
        subtitle: `Personalized assessment based on your academic profile`,
        themeColor: fitCategory === 'SAFETY' ? 'emerald' : fitCategory === 'TARGET' ? 'amber' : fitCategory === 'REACH' ? 'orange' : 'rose',
        matchScore: matchScore,
        fitCategory: fitCategory,
        explanation: explanation,
        universityInfo: {
            name: college.university_name,
            location: college.location,
            acceptanceRate: college.acceptance_rate,
            usNewsRank: college.us_news_rank
        },
        strengths: scoreBreakdown.filter(f => f.score > 70).map(f => ({
            name: f.category || f.name,
            score: f.score,
            maxScore: 100,
            percentage: f.score,
            detail: f.description
        })),
        improvements: scoreBreakdown.filter(f => f.score <= 70).map(f => ({
            name: f.category || f.name,
            score: f.score,
            maxScore: 100,
            percentage: f.score,
            detail: f.description
        })),
        actionPlan: recommendations.slice(0, 3).map((rec, idx) => ({
            step: idx + 1,
            action: typeof rec === 'object' ? rec.action : rec,
            timeline: typeof rec === 'object' ? rec.timeline : null
        })),
        gapAnalysis: fitAnalysis.gap_analysis,
        conclusion: fitAnalysis.conclusion || `With the right focus on improvement areas, ${college.university_name} is a ${fitCategory.replace('_', ' ').toLowerCase()} choice for your profile.`
    };

    // Show loading while checking profile
    if (profileLoading) {
        return (
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden p-8">
                <div className="flex items-center justify-center gap-3 text-gray-500">
                    <ArrowPathIcon className="h-6 w-6 animate-spin" />
                    <span>Loading your profile...</span>
                </div>
            </div>
        );
    }

    // Show profile required banner if no profile exists
    if (!profileExists) {
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
                    </div>
                </div>

                {/* Profile Required Banner */}
                <div className="p-8">
                    <div className="bg-gradient-to-r from-[#D6E8D5] to-[#FCEEE8] border-2 border-[#A8C5A6] rounded-xl p-8 text-center">
                        <div className="w-16 h-16 bg-[#D6E8D5] rounded-full flex items-center justify-center mx-auto mb-4">
                            <ExclamationCircleIcon className="h-8 w-8 text-[#1A4D2E]" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            Create Your Profile First
                        </h3>
                        <p className="text-gray-600 mb-6 max-w-md mx-auto">
                            To see your personalized fit analysis for {college.university_name},
                            we need to know about your academic profile, test scores, and activities.
                        </p>
                        <Link
                            to="/profile"
                            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-[#D6E8D5]0 to-[#FCEEE8]0 text-white rounded-xl font-semibold hover:from-[#2D6B45] hover:to-[#3A7D5A] transition-all shadow-lg"
                        >
                            <SparklesIcon className="h-5 w-5" />
                            Create Your Profile
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

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
                {/* Visual Infographic */}
                <FitInfographicView data={infographicData} studentName={studentProfile?.first_name || studentProfile?.name || 'Student'} />

                {/* Fit Explanation */}
                <div className="bg-gradient-to-r from-blue-50 to-[#FCEEE8] rounded-lg p-4 border border-[#E0DED8]">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-[#C05838]" />
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
                        <ChartBarIcon className="h-5 w-5 text-[#1A4D2E]" />
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
                    <div className="mt-4 p-3 bg-[#FCEEE8] rounded-lg border border-[#E8A090]">
                        <p className="text-xs text-[#C05838]">
                            <strong>Fair Mode:</strong> Your match score is calculated based on academic factors only.
                            School selectivity is used as a ceiling for the category (not to reduce your score).
                        </p>
                    </div>
                </div>

                {/* Action Plan - Personalized Recommendations */}
                {recommendations.length > 0 && (
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                            <LightBulbIcon className="h-5 w-5 text-[#1A4D2E]" />
                            Action Plan to Strengthen Your Application
                        </h3>
                        <div className="space-y-2">
                            {recommendations.map((rec, idx) => (
                                <div key={idx} className="flex flex-col gap-2 p-4 bg-blue-50 rounded-lg">
                                    <div className="flex items-start gap-3">
                                        <span className="text-[#C05838] font-bold">{idx + 1}.</span>
                                        <span className="text-gray-700">{typeof rec === 'object' ? rec.action : rec}</span>
                                    </div>
                                    {typeof rec === 'object' && rec.addresses_gap && (
                                        <div className="ml-7 flex flex-wrap gap-2 text-xs">
                                            <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] rounded-full">Addresses: {rec.addresses_gap}</span>
                                            {rec.timeline && <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] rounded-full">Timeline: {rec.timeline}</span>}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Gap Analysis Section */}
                {gapAnalysis && (gapAnalysis.primary_gap || gapAnalysis.secondary_gap || (gapAnalysis.student_strengths && gapAnalysis.student_strengths.length > 0)) && (
                    <div className="bg-gradient-to-r from-orange-50 to-[#D6E8D5] rounded-lg p-4 border border-[#E8A090]">
                        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                            🔍 Gap Analysis
                        </h3>
                        <div className="grid md:grid-cols-2 gap-4">
                            {/* Gaps */}
                            <div className="space-y-3">
                                {gapAnalysis.primary_gap && (
                                    <div className="bg-white rounded-lg p-3 border border-[#E8A090]">
                                        <div className="text-xs font-medium text-[#C05838] mb-1">Primary Gap</div>
                                        <p className="text-sm text-gray-700">{gapAnalysis.primary_gap}</p>
                                    </div>
                                )}
                                {gapAnalysis.secondary_gap && (
                                    <div className="bg-white rounded-lg p-3 border border-[#E0DED8]">
                                        <div className="text-xs font-medium text-[#1A4D2E] mb-1">Secondary Gap</div>
                                        <p className="text-sm text-gray-700">{gapAnalysis.secondary_gap}</p>
                                    </div>
                                )}
                            </div>
                            {/* Strengths */}
                            {gapAnalysis.student_strengths && gapAnalysis.student_strengths.length > 0 && (
                                <div className="bg-white rounded-lg p-3 border border-emerald-100">
                                    <div className="text-xs font-medium text-emerald-700 mb-2">Your Strengths</div>
                                    <ul className="space-y-1">
                                        {gapAnalysis.student_strengths.map((strength, idx) => (
                                            <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                                <span className="text-emerald-500">✓</span>
                                                <span>{strength}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Essay Strategy Section */}
                {essayAngles.length > 0 && (
                    <div className="bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg p-4 border border-purple-200">
                        <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                            ✍️ Essay Strategy
                        </h3>
                        <div className="space-y-4">
                            {essayAngles.map((essay, idx) => (
                                <div key={idx} className="bg-white rounded-lg p-4 border border-purple-100">
                                    <div className="flex items-start justify-between mb-2">
                                        <h4 className="font-medium text-purple-900">{essay.essay_prompt}</h4>
                                        {essay.word_limit && <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">{essay.word_limit} words</span>}
                                    </div>
                                    <p className="text-sm text-gray-700 mb-2">{essay.angle}</p>
                                    <div className="flex flex-wrap gap-2 text-xs">
                                        {essay.student_hook && <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded">Your Hook: {essay.student_hook}</span>}
                                        {essay.school_hook && <span className="px-2 py-1 bg-indigo-50 text-indigo-700 rounded">School Hook: {essay.school_hook}</span>}
                                    </div>
                                    {essay.tip && <p className="text-xs text-gray-500 mt-2 italic">💡 Tip: {essay.tip}</p>}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Application Timeline Section */}
                {applicationTimeline && (
                    <div className="bg-gradient-to-r from-blue-50 to-cyan-50 rounded-lg p-4 border border-blue-200">
                        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                            📅 Application Timeline
                        </h3>
                        <div className="grid md:grid-cols-2 gap-4">
                            <div>
                                <div className="text-sm font-medium text-blue-800 mb-1">Recommended Plan</div>
                                <div className="flex items-center gap-2">
                                    <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full font-semibold">{applicationTimeline.recommended_plan}</span>
                                    {applicationTimeline.is_binding && <span className="text-xs text-red-600 font-medium">Binding</span>}
                                </div>
                                <p className="text-xs text-gray-600 mt-2">{applicationTimeline.rationale}</p>
                            </div>
                            <div>
                                <div className="text-sm font-medium text-blue-800 mb-1">Key Dates</div>
                                <div className="space-y-1 text-sm">
                                    {applicationTimeline.deadline && <div>📌 Deadline: <span className="font-medium">{applicationTimeline.deadline}</span></div>}
                                    {applicationTimeline.financial_aid_deadline && <div>💰 FA Deadline: <span className="font-medium">{applicationTimeline.financial_aid_deadline}</span></div>}
                                </div>
                            </div>
                        </div>
                        {applicationTimeline.key_milestones && applicationTimeline.key_milestones.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-blue-100">
                                <div className="text-sm font-medium text-blue-800 mb-2">Key Milestones</div>
                                <div className="flex flex-wrap gap-2">
                                    {applicationTimeline.key_milestones.map((milestone, idx) => (
                                        <span key={idx} className="px-2 py-1 bg-white border border-blue-200 rounded text-xs text-gray-700">{milestone}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Scholarship Matches Section */}
                {scholarshipMatches.length > 0 && (
                    <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
                        <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                            💰 Scholarship Matches
                        </h3>
                        <div className="space-y-3">
                            {scholarshipMatches.map((scholarship, idx) => (
                                <div key={idx} className="bg-white rounded-lg p-3 border border-green-100">
                                    <div className="flex items-start justify-between">
                                        <h4 className="font-medium text-green-900">{scholarship.name}</h4>
                                        <span className="text-sm font-bold text-green-700">{scholarship.amount}</span>
                                    </div>
                                    <p className="text-xs text-gray-600 mt-1">{scholarship.match_reason}</p>
                                    <div className="flex flex-wrap gap-2 mt-2 text-xs">
                                        {scholarship.deadline && <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded">Deadline: {scholarship.deadline}</span>}
                                        {scholarship.application_method && <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded">{scholarship.application_method}</span>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Test & Major Strategy Section */}
                {(testStrategy || majorStrategy) && (
                    <div className="grid md:grid-cols-2 gap-4">
                        {testStrategy && (
                            <div className="bg-gradient-to-r from-[#D6E8D5] to-yellow-50 rounded-lg p-4 border border-[#A8C5A6]">
                                <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                                    📝 Test Strategy
                                </h3>
                                <div className="flex items-center gap-2 mb-2">
                                    <span className={`px-3 py-1 rounded-full font-bold text-sm ${testStrategy.recommendation === 'Submit' ? 'bg-green-100 text-green-800' : 'bg-[#D6E8D5] text-[#1A4D2E]'}`}>
                                        {testStrategy.recommendation}
                                    </span>
                                    {testStrategy.student_score_position && <span className="text-xs text-gray-500">Score Position: {testStrategy.student_score_position}</span>}
                                </div>
                                <p className="text-xs text-gray-600">{testStrategy.rationale}</p>
                                <div className="mt-2 text-xs text-gray-500 space-y-1">
                                    {testStrategy.student_act && <div>Your ACT: {testStrategy.student_act}</div>}
                                    {testStrategy.student_sat && <div>Your SAT: {testStrategy.student_sat}</div>}
                                    {testStrategy.school_act_middle_50 && <div>School ACT: {testStrategy.school_act_middle_50}</div>}
                                    {testStrategy.school_sat_middle_50 && <div>School SAT: {testStrategy.school_sat_middle_50}</div>}
                                </div>
                            </div>
                        )}
                        {majorStrategy && (
                            <div className="bg-gradient-to-r from-teal-50 to-cyan-50 rounded-lg p-4 border border-teal-200">
                                <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                                    🎓 Major Strategy
                                </h3>
                                <div className="space-y-2 text-sm">
                                    <div><span className="text-gray-500">Intended:</span> <span className="font-medium">{majorStrategy.intended_major}</span></div>
                                    {majorStrategy.backup_major && <div><span className="text-gray-500">Backup:</span> <span className="font-medium">{majorStrategy.backup_major}</span></div>}
                                    {majorStrategy.college_within_university && <div><span className="text-gray-500">College:</span> <span className="text-xs">{majorStrategy.college_within_university}</span></div>}
                                </div>
                                {majorStrategy.strategic_tip && (
                                    <p className="text-xs text-teal-700 mt-2 p-2 bg-teal-100 rounded">💡 {majorStrategy.strategic_tip}</p>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {/* Tips & Red Flags Section */}
                {(demonstratedInterestTips.length > 0 || redFlagsToAvoid.length > 0) && (
                    <div className="grid md:grid-cols-2 gap-4">
                        {demonstratedInterestTips.length > 0 && (
                            <div className="bg-gradient-to-r from-indigo-50 to-violet-50 rounded-lg p-4 border border-indigo-200">
                                <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                                    💡 Demonstrated Interest Tips
                                </h3>
                                <ul className="space-y-2 text-sm">
                                    {demonstratedInterestTips.map((tip, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-gray-700">
                                            <span className="text-indigo-500">✓</span>
                                            <span>{tip}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {redFlagsToAvoid.length > 0 && (
                            <div className="bg-gradient-to-r from-red-50 to-rose-50 rounded-lg p-4 border border-red-200">
                                <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                                    ⚠️ Red Flags to Avoid
                                </h3>
                                <ul className="space-y-2 text-sm">
                                    {redFlagsToAvoid.map((flag, idx) => (
                                        <li key={idx} className="flex items-start gap-2 text-gray-700">
                                            <span className="text-red-500">✗</span>
                                            <span>{flag}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

// Recommendation Card Component - Selectable with checkbox
const RecommendationCard = ({ recommendation, isSelected, onToggleSelect, disabled }) => {
    const fitCategory = recommendation.fit_category || 'TARGET';
    const categoryConfig = FIT_CATEGORIES[fitCategory] || FIT_CATEGORIES.TARGET;
    const Icon = categoryConfig.icon;

    return (
        <div
            onClick={() => !disabled && onToggleSelect(recommendation.id)}
            className={`relative overflow-hidden bg-white rounded-xl shadow-sm border-2 px-4 pb-4 pt-9 cursor-pointer transition-all ${isSelected
                ? 'border-[#1A4D2E] ring-2 ring-[#D6E8D5] shadow-md'
                : disabled
                    ? 'border-gray-100 opacity-60 cursor-not-allowed'
                    : 'border-gray-200 hover:border-purple-300 hover:shadow-md'
                }`}
        >
            {/* Ribbon */}
            <div className={`absolute top-0 left-0 px-3 py-1 bg-gradient-to-r ${categoryConfig.color} text-white text-xs font-bold rounded-br-xl shadow-sm z-10 flex items-center gap-1`}>
                <Icon className="w-3 h-3" />
                {fitCategory.replace('_', ' ')}
            </div>

            <div className="flex justify-between items-start mb-2 mt-1">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                    {/* Checkbox */}
                    <div className={`flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${isSelected
                        ? 'bg-[#1A4D2E] border-amber-600'
                        : disabled
                            ? 'bg-gray-100 border-gray-200'
                            : 'border-gray-300 group-hover:border-[#D6E8D5]'
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
                    Match: <span className="font-semibold text-[#1A4D2E]">{recommendation.matchScore}%</span>
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
    const [processingColleges, setProcessingColleges] = useState({}); // Track colleges being analyzed: { id: 'fit' | 'infographic' | 'done' }

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
    // Generates fit analysis + infographic for each college
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

                    // Track processing status: 'fit' stage
                    setProcessingColleges(prev => ({ ...prev, [rec.id]: 'fit' }));

                    // Trigger fit computation (don't await - run in background)
                    console.log(`[Smart Discovery] Computing fit for: ${rec.name}`);
                    computeSingleFit(currentUser.email, rec.id).then(async fitResult => {
                        if (fitResult.success) {
                            console.log(`[Smart Discovery] Fit computed for ${rec.name}: ${fitResult.fit_analysis?.fit_category}`);
                            // Infographic generation removed - using static CSS template
                            setProcessingColleges(prev => ({ ...prev, [rec.id]: 'done' }));
                        } else {
                            console.warn(`[Smart Discovery] Fit computation failed for ${rec.name}`);
                            setProcessingColleges(prev => ({ ...prev, [rec.id]: 'error' }));
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
            return { status: 'warning', message: '💡 Add more target schools', color: 'text-[#1A4D2E]' };
        }
        return { status: 'info', message: '🎯 Getting balanced...', color: 'text-[#C05838]' };
    };

    const balanceStatus = getBalanceStatus();

    return (
        <div className="bg-gradient-to-r from-[#D6E8D5] to-blue-50 rounded-xl border border-[#A8C5A6] overflow-hidden">
            {/* Header - Always visible */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#D6E8D5]/50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-[#D6E8D5] rounded-lg">
                        <LightBulbIcon className="h-6 w-6 text-[#1A4D2E]" />
                    </div>
                    <div className="text-left">
                        <h3 className="font-bold text-gray-900">Smart Discovery</h3>
                        <p className={`text-sm ${balanceStatus.color}`}>{balanceStatus.message}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-[#1A4D2E] font-medium">
                        {isOpen ? 'Close' : 'Find More Schools'}
                    </span>
                    <XMarkIcon className={`h-5 w-5 text-[#1A4D2E] transition-transform ${isOpen ? 'rotate-0' : 'rotate-45'}`} />
                </div>
            </button>

            {/* Expanded Content */}
            {isOpen && (
                <div className="px-6 pb-6 pt-2 border-t border-[#A8C5A6]">
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
                                className="px-3 py-1.5 bg-white border border-[#A8C5A6] text-[#1A4D2E] rounded-full text-sm font-medium hover:bg-[#D6E8D5] transition-colors disabled:opacity-50"
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
                                className="px-3 py-1.5 bg-white border border-[#E8A090] text-[#C05838] rounded-full text-sm font-medium hover:bg-[#FCEEE8] transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                🎯 More Reach Schools ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter(null, null)}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-[#E8A090] text-[#C05838] rounded-full text-sm font-medium hover:bg-[#FCEEE8] transition-colors disabled:opacity-50"
                                title="Fast: Uses pre-computed fits"
                            >
                                📚 Best Matches ⚡
                            </button>
                            <button
                                onClick={() => handleQuickFilter(null, 'California')}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-white border border-[#A8C5A6] text-[#1A4D2E] rounded-full text-sm font-medium hover:bg-[#D6E8D5] transition-colors disabled:opacity-50"
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
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
                            rows={2}
                        />
                    </div>

                    {/* Get Recommendations Button */}
                    <button
                        onClick={handleQuickBalancedList}
                        disabled={isLoading}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] text-white rounded-xl font-medium hover:from-amber-700 hover:to-blue-700 transition-all shadow-lg disabled:opacity-50 mb-4"
                    >
                        <SparklesIcon className="h-5 w-5" />
                        {recommendations.length > 0 ? 'Get More Recommendations ⚡' : 'Get Smart Recommendations ⚡'}
                    </button>



                    {/* Loading State */}
                    {isLoading && (
                        <div className="text-center py-8">
                            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-amber-600 mx-auto mb-3"></div>
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
                                    <SparklesIcon className="h-4 w-4 text-[#1A4D2E]" />
                                    Recommended For You ({recommendations.length} schools)
                                </h4>
                                <button
                                    onClick={toggleSelectAll}
                                    className="text-sm text-[#C05838] hover:text-blue-800"
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
                                className="w-full text-sm text-[#1A4D2E] hover:text-purple-800 font-medium disabled:opacity-50"
                            >
                                ↻ Get different recommendations ⚡
                            </button>

                            {/* Processing Status Banner */}
                            {Object.entries(processingColleges).filter(([_, status]) => status !== 'done').length > 0 && (
                                <div className="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-xl">
                                    <div className="flex items-center gap-2 text-purple-700 mb-2">
                                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                        <span className="text-sm font-medium">Generating analysis...</span>
                                    </div>
                                    <div className="space-y-1">
                                        {Object.entries(processingColleges).map(([id, status]) => (
                                            status !== 'done' && (
                                                <div key={id} className="text-xs text-purple-600 flex items-center gap-2">
                                                    {status === 'fit' && (
                                                        <>
                                                            <SparklesIcon className="h-3 w-3" />
                                                            <span>Computing fit analysis...</span>
                                                        </>
                                                    )}
                                                    {status === 'infographic' && (
                                                        <>
                                                            <SparklesIcon className="h-3 w-3" />
                                                            <span>Generating infographic...</span>
                                                        </>
                                                    )}
                                                    {status === 'error' && (
                                                        <>
                                                            <ExclamationCircleIcon className="h-3 w-3 text-red-500" />
                                                            <span className="text-red-600">Analysis failed</span>
                                                        </>
                                                    )}
                                                </div>
                                            )
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// Empty State Component - Modern, Engaging Design
const EmptyState = ({ onQuickStart }) => {
    const [hoveredOption, setHoveredOption] = useState(null);

    const quickStartOptions = [
        {
            id: 'balanced',
            icon: '⚖️',
            title: 'Smart Balanced List',
            description: 'AI picks the perfect mix of safety, target, and reach schools tailored to your profile',
            action: 'balanced',
            gradient: 'from-[#D6E8D5]0 via-orange-500 to-rose-500',
            highlight: 'Most Popular'
        },
        {
            id: 'safety',
            icon: '🛡️',
            title: 'Safety Schools',
            description: 'Schools where you have strong admission chances',
            action: 'SAFETY',
            gradient: 'from-emerald-500 to-teal-500',
            highlight: null
        },
        {
            id: 'target',
            icon: '✅',
            title: 'Target Schools',
            description: 'Schools that match your academic profile well',
            action: 'TARGET',
            gradient: 'from-orange-500 to-[#D6E8D5]0',
            highlight: null
        },
        {
            id: 'reach',
            icon: '🚀',
            title: 'Reach Schools',
            description: 'Ambitious choices that push your limits',
            action: 'REACH',
            gradient: 'from-rose-500 to-pink-500',
            highlight: null
        }
    ];

    const steps = [
        { num: '1', text: 'Choose how to start', icon: '👆' },
        { num: '2', text: 'AI analyzes your profile', icon: '🤖' },
        { num: '3', text: 'Review & add schools', icon: '✨' }
    ];

    return (
        <div className="min-h-[70vh] flex flex-col items-center justify-center px-4 py-8">
            {/* Hero Section */}
            <div className="text-center mb-10">
                {/* Animated Rocket Icon */}
                <div className="relative inline-block mb-6">
                    <div className="absolute inset-0 bg-gradient-to-br from-amber-400 to-[#FCEEE8]0 rounded-3xl blur-xl opacity-30 animate-pulse"></div>
                    <div className="relative p-5 bg-gradient-to-br from-amber-400 to-[#FCEEE8]0 rounded-3xl shadow-2xl shadow-amber-200">
                        <RocketLaunchIcon className="h-12 w-12 text-white" />
                    </div>
                </div>

                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-3">
                    Launch Your College Journey
                </h1>
                <p className="text-lg text-gray-600 max-w-xl mx-auto">
                    Our AI will find the perfect schools for you based on your academic profile, interests, and goals.
                </p>
            </div>

            {/* How It Works - Steps */}
            <div className="flex items-center justify-center gap-2 md:gap-6 mb-10 flex-wrap">
                {steps.map((step, idx) => (
                    <div key={step.num} className="flex items-center gap-2 md:gap-4">
                        <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-full shadow-sm border border-gray-100">
                            <span className="w-6 h-6 flex items-center justify-center bg-[#D6E8D5] text-[#1A4D2E] rounded-full text-xs font-bold">
                                {step.num}
                            </span>
                            <span className="text-sm text-gray-600 hidden sm:inline">{step.text}</span>
                            <span className="text-lg">{step.icon}</span>
                        </div>
                        {idx < steps.length - 1 && (
                            <div className="text-gray-300 hidden md:block">→</div>
                        )}
                    </div>
                ))}
            </div>

            {/* Quick Start Cards */}
            <div className="w-full max-w-4xl mb-10 space-y-4">
                {/* Featured Card - Full Width */}
                <button
                    onClick={() => onQuickStart(quickStartOptions[0].action)}
                    onMouseEnter={() => setHoveredOption(quickStartOptions[0].id)}
                    onMouseLeave={() => setHoveredOption(null)}
                    className="group relative overflow-hidden rounded-2xl p-6 text-left transition-all duration-300 transform hover:scale-[1.01] hover:shadow-2xl w-full"
                >
                    <div className={`absolute inset-0 bg-gradient-to-br ${quickStartOptions[0].gradient} opacity-90`}></div>
                    <div className="absolute inset-0 bg-white/10 backdrop-blur-[1px]"></div>
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700"></div>
                    <div className="relative z-10">
                        <span className="inline-block px-3 py-1 bg-white/20 backdrop-blur-sm text-white text-xs font-bold rounded-full mb-3 border border-white/30">
                            ⭐ {quickStartOptions[0].highlight}
                        </span>
                        <div className="flex items-start gap-4">
                            <span className="text-4xl">{quickStartOptions[0].icon}</span>
                            <div className="flex-1">
                                <h3 className="text-xl font-bold text-white mb-2 group-hover:underline underline-offset-2">
                                    {quickStartOptions[0].title}
                                </h3>
                                <p className="text-white/90 text-sm leading-relaxed">
                                    {quickStartOptions[0].description}
                                </p>
                            </div>
                            <div className="text-white/60 group-hover:text-white group-hover:translate-x-1 transition-all">→</div>
                        </div>
                    </div>
                </button>

                {/* 3 Category Cards - Equal Width Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {quickStartOptions.slice(1).map((option) => (
                        <button
                            key={option.id}
                            onClick={() => onQuickStart(option.action)}
                            onMouseEnter={() => setHoveredOption(option.id)}
                            onMouseLeave={() => setHoveredOption(null)}
                            className="group relative overflow-hidden rounded-2xl p-5 text-left transition-all duration-300 transform hover:scale-[1.02] hover:shadow-2xl h-full"
                        >
                            {/* Background Gradient */}
                            <div className={`absolute inset-0 bg-gradient-to-br ${option.gradient} opacity-90`}></div>

                            {/* Glassmorphism overlay */}
                            <div className="absolute inset-0 bg-white/10 backdrop-blur-[1px]"></div>

                            {/* Animated shimmer effect on hover */}
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700"></div>

                            {/* Content - Vertical Layout for smaller cards */}
                            <div className="relative z-10 flex flex-col items-start h-full">
                                <span className="text-3xl mb-3">{option.icon}</span>
                                <h3 className="text-lg font-bold text-white mb-1 group-hover:underline underline-offset-2">
                                    {option.title}
                                </h3>
                                <p className="text-white/80 text-xs leading-relaxed flex-1">
                                    {option.description}
                                </p>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Divider */}
            <div className="flex items-center gap-4 mb-8 w-full max-w-xs">
                <div className="flex-1 h-px bg-gradient-to-r from-transparent to-gray-200"></div>
                <span className="text-gray-400 text-sm font-medium">or explore manually</span>
                <div className="flex-1 h-px bg-gradient-to-l from-transparent to-gray-200"></div>
            </div>

            {/* Manual Browse Button */}
            <a
                href="/universities"
                className="group inline-flex items-center gap-3 px-8 py-4 bg-white border-2 border-gray-200 text-gray-700 rounded-2xl font-semibold hover:border-[#A8C5A6] hover:bg-[#D6E8D5] hover:text-[#1A4D2E] transition-all shadow-sm hover:shadow-lg"
            >
                <SparklesIcon className="h-5 w-5 text-amber-500" />
                Browse All Universities
                <span className="text-gray-400 group-hover:text-amber-500 group-hover:translate-x-1 transition-all">→</span>
            </a>

            {/* Trust indicator */}
            <p className="mt-8 text-sm text-gray-400 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                150+ universities analyzed and ready to match
            </p>
        </div>
    );
};

// Main Component
const MyLaunchpad = () => {
    const { currentUser } = useAuth();
    const { canAccessLaunchpad, isFreeTier, hasFullFitAnalysis, canDeepResearch, creditsRemaining, showCreditsModal, closeCreditsModal, creditsModalFeature, promptCreditsUpgrade, fetchCredits } = usePayment();
    const [collegeList, setCollegeList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [removingId, setRemovingId] = useState(null);
    const [selectedUniversity, setSelectedUniversity] = useState(null);
    const [deepResearchData, setDeepResearchData] = useState({});
    const [recomputingFits, setRecomputingFits] = useState(false);
    const [selectedCategory, setSelectedCategory] = useState('ALL');

    // Multi-select state for bulk removal
    const [selectedColleges, setSelectedColleges] = useState(new Set());
    const [selectionMode, setSelectionMode] = useState(false);
    const [bulkRemoving, setBulkRemoving] = useState(false);

    // Chat widget state
    const [chatCollege, setChatCollege] = useState(null);
    const [isChatOpen, setIsChatOpen] = useState(false);

    // Fit Analysis Modal state
    const [fitModalCollege, setFitModalCollege] = useState(null);
    const [isFitModalOpen, setIsFitModalOpen] = useState(false);

    const handleOpenChat = (college) => {
        setChatCollege(college);
        setIsChatOpen(true);
    };

    const handleCloseChat = () => {
        setIsChatOpen(false);
    };

    const handleOpenFitModal = (college) => {
        setFitModalCollege(college);
        setIsFitModalOpen(true);
    };

    const handleCloseFitModal = () => {
        setIsFitModalOpen(false);
    };

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

            console.log('[Launchpad] College list result:', listResult);
            console.log('[Launchpad] Fits result:', fitsResult);

            if (listResult.success) {
                let colleges = listResult.college_list || [];
                console.log('[Launchpad] Colleges loaded:', colleges.length, colleges.map(c => c.university_id));
                console.log('[Launchpad] Logo URLs:', colleges.map(c => ({ id: c.university_id, logo_url: c.logo_url })));

                // Merge precomputed fits into college list (precomputed takes priority)
                // API returns 'fits' array, not 'results'
                if (fitsResult.success && fitsResult.fits) {
                    console.log('[Launchpad] Fits available:', fitsResult.fits.length, fitsResult.fits.map(f => f.university_id));
                    const fitsMap = {};
                    fitsResult.fits.forEach(fit => {
                        fitsMap[fit.university_id] = {
                            fit_category: fit.fit_category,
                            match_percentage: fit.match_percentage || fit.match_score,
                            match_score: fit.match_percentage || fit.match_score,
                            explanation: fit.explanation,
                            factors: fit.factors || [],
                            recommendations: fit.recommendations || [],
                            gap_analysis: fit.gap_analysis || {},
                            essay_angles: fit.essay_angles || [],
                            application_timeline: fit.application_timeline || {},
                            scholarship_matches: fit.scholarship_matches || [],
                            test_strategy: fit.test_strategy || {},
                            major_strategy: fit.major_strategy || {},
                            demonstrated_interest_tips: fit.demonstrated_interest_tips || [],
                            red_flags_to_avoid: fit.red_flags_to_avoid || [],
                            infographic_url: fit.infographic_url
                        };
                    });

                    console.log('[Launchpad] FitsMap keys:', Object.keys(fitsMap));

                    // Merge precomputed fits into college list items
                    colleges = colleges.map(college => {
                        const precomputed = fitsMap[college.university_id];
                        console.log('[Launchpad] Merge check:', college.university_id, '-> precomputed:', !!precomputed);
                        if (precomputed) {
                            return {
                                ...college,
                                fit_analysis: precomputed,  // Override with fresh precomputed data
                                infographic_url: precomputed.infographic_url // Lift to top level for FitAnalysisPage
                            };
                        }
                        return college;
                    });
                    console.log('[Launchpad] Merged precomputed fits for', Object.keys(fitsMap).length, 'universities');
                }

                setCollegeList(colleges);

                // Infographic backfill removed - using static CSS template instead
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

        // Free tier: colleges are PERMANENT - cannot be removed
        if (!canAccessLaunchpad) {
            alert('Free tier colleges are permanent. Upgrade to Pro to modify your list.');
            return;
        }

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
            const addPromises = selectedRecs.map(rec =>
                updateCollegeList(currentUser.email, 'add', { id: rec.id, name: rec.name }, '')
            );
            await Promise.all(addPromises);

            // Trigger fit computation in background for all new colleges
            // We don't await this so the UI updates immediately
            selectedRecs.forEach(rec => {
                console.log(`[Quick Start] Triggering fit computation for: ${rec.name}`);
                computeSingleFit(currentUser.email, rec.id)
                    .then(res => console.log(`[Quick Start] Fit computed for ${rec.name}:`, res.success))
                    .catch(err => console.error(`[Quick Start] Fit computation failed for ${rec.name}:`, err));
            });

            // Clear quick start state and refresh college list immediately
            setQuickStartPrompt(null);
            setQuickStartRecommendations([]);
            setQuickStartSelected({});

            // Short delay to allow DB propagation before fetching
            setTimeout(() => fetchCollegeList(), 500);
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
                // Deduplicate results by university_id
                const seenIds = new Set();
                const uniqueResults = result.results.filter(fit => {
                    const id = fit.university_id;
                    if (id && seenIds.has(id)) {
                        return false;
                    }
                    if (id) seenIds.add(id);
                    return true;
                });

                // Transform to recommendation format and sort by match score descending
                let recs = uniqueResults.map((fit, idx) => ({
                    id: fit.university_id || `rec-${idx}`,
                    name: fit.university_name || fit.official_name || 'Unknown',
                    fit_category: fit.fit_category,
                    matchScore: fit.match_percentage || fit.match_score || 0,
                    location: fit.location ? `${fit.location.city}, ${fit.location.state}` : null,
                    reason: `${fit.fit_category?.replace('_', ' ')} school with ${fit.match_percentage || fit.match_score || 0}% match`,
                    selected: true
                })).sort((a, b) => b.matchScore - a.matchScore);  // Sort by match score descending

                // Free tier limit: show all, but only pre-select top 3
                if (!canAccessLaunchpad) {
                    recs = recs.map((rec, idx) => ({
                        ...rec,
                        selected: idx < 3 // Only first 3 are selected by default for free tier
                    }));
                    console.log(`[Quick Start] Free tier: showing all but pre-selecting only top 3`);
                }

                setQuickStartRecommendations(recs);
                console.log(`[Quick Start] Loaded ${recs.length} recommendations (deduplicated from ${result.results.length})`);
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
            // Use fit_analysis category first, then fallback to soft_fit_category from university data
            // soft_fit_category is pre-computed based on acceptance rate
            const fitCategory = college.fit_analysis?.fit_category
                || college.soft_fit_category
                || 'TARGET';
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
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#1A4D2E] mx-auto mb-4"></div>
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
                        <div className="p-2 bg-gradient-to-br from-amber-400 to-[#FCEEE8]0 rounded-xl shadow-lg shadow-amber-200">
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
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#1A4D2E]"></div>
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
                                    disabled={!canAccessLaunchpad && !quickStartSelected[rec.id] && Object.values(quickStartSelected).filter(Boolean).length >= 3}
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
                                    className="px-6 py-3 bg-gradient-to-r from-[#D6E8D5]0 to-[#FCEEE8]0 text-white rounded-xl font-medium hover:from-[#2D6B45] hover:to-[#3A7D5A] transition-all shadow-lg shadow-amber-200 disabled:opacity-50 flex items-center gap-2"
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
                <div className="bg-[#D6E8D5] border-l-4 border-[#1A4D2E] text-[#1A4D2E] p-4 rounded shadow-sm" role="alert">
                    <div className="flex items-center">
                        <div className="py-1">
                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-[#1A4D2E]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
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
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-amber-400 to-[#FCEEE8]0 rounded-xl shadow-lg shadow-amber-200">
                            <RocketLaunchIcon className="h-6 w-6 text-white" />
                        </div>
                        My Launchpad
                    </h1>
                </div>
            </div>

            {/* Stats Bar */}
            {/* Category Filter Tabs */}
            <div className="flex overflow-x-auto pb-4 gap-3 mb-6 scrollbar-hide">
                <button
                    onClick={() => setSelectedCategory('ALL')}
                    className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap flex items-center gap-2 border shadow-sm ${selectedCategory === 'ALL'
                        ? 'bg-gray-900 text-white border-gray-900 shadow-md transform scale-105'
                        : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                        }`}
                >
                    <span>🏫 All Schools</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${selectedCategory === 'ALL' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-600'}`}>
                        {collegeList.length}
                    </span>
                </button>
                {Object.entries(FIT_CATEGORIES).map(([key, config]) => (
                    <button
                        key={key}
                        onClick={() => setSelectedCategory(key)}
                        className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all whitespace-nowrap flex items-center gap-2 border shadow-sm ${selectedCategory === key
                            ? `bg-gradient-to-r ${config.bgGradient} ${config.borderColor} ${config.textColor} ring-2 ring-offset-1 ring-${config.color}-200 transform scale-105`
                            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                            }`}
                    >
                        <span>{config.emoji} {config.label}</span>
                        <span className={`px-2 py-0.5 rounded-full text-xs ${selectedCategory === key ? 'bg-white/60' : 'bg-gray-100 text-gray-600'}`}>
                            {categorizedColleges[key]?.length || 0}
                        </span>
                    </button>
                ))}
            </div>

            {/* Deadline Tracker - Prominent position at top */}
            <div className="mb-6">
                <DeadlineTracker
                    onSchoolClick={(universityId) => {
                        const college = collegeList.find(c => c.university_id === universityId);
                        if (college) handleOpenFitModal(college);
                    }}
                />
            </div>

            {/* Smart Discovery Panel */}
            <SmartDiscoveryPanel
                currentUser={currentUser}
                categorizedColleges={categorizedColleges}
                onCollegeAdded={fetchCollegeList}
            />

            {/* Full-Page Fit Analysis View (no tabs, just fit analysis) */}
            {fitModalCollege && (
                <FitAnalysisDetail
                    college={fitModalCollege}
                    onBack={handleCloseFitModal}
                />
            )}

            {/* Four-Column Layout (hidden when viewing full-page fit analysis) */}
            {/* Four-Column Layout (hidden when viewing full-page fit analysis) */}
            {!fitModalCollege && (
                <div className="grid grid-cols-1 gap-4">
                    {/* Reach Column */}
                    {(selectedCategory === 'ALL' || selectedCategory === 'REACH') && (
                        <CategoryColumn
                            category="REACH"
                            colleges={categorizedColleges.REACH}
                            onRemove={handleRemove}
                            removingId={removingId}
                            onViewDetails={handleOpenFitModal}
                            selectedColleges={selectedColleges}
                            onToggleSelect={toggleSelection}
                            selectionMode={selectionMode}
                            onOpenChat={handleOpenChat}
                            canRemove={canAccessLaunchpad}
                        />
                    )}
                    {/* Super Reach Column */}
                    {(selectedCategory === 'ALL' || selectedCategory === 'SUPER_REACH') && (
                        <CategoryColumn
                            category="SUPER_REACH"
                            colleges={categorizedColleges.SUPER_REACH}
                            onRemove={handleRemove}
                            removingId={removingId}
                            onViewDetails={handleOpenFitModal}
                            selectedColleges={selectedColleges}
                            onToggleSelect={toggleSelection}
                            selectionMode={selectionMode}
                            onOpenChat={handleOpenChat}
                            canRemove={canAccessLaunchpad}
                        />
                    )}
                    {/* Target Column */}
                    {(selectedCategory === 'ALL' || selectedCategory === 'TARGET') && (
                        <CategoryColumn
                            category="TARGET"
                            colleges={categorizedColleges.TARGET}
                            onRemove={handleRemove}
                            removingId={removingId}
                            onViewDetails={handleOpenFitModal}
                            selectedColleges={selectedColleges}
                            onToggleSelect={toggleSelection}
                            selectionMode={selectionMode}
                            onOpenChat={handleOpenChat}
                            canRemove={canAccessLaunchpad}
                        />
                    )}
                    {/* Safety Column */}
                    {(selectedCategory === 'ALL' || selectedCategory === 'SAFETY') && (
                        <CategoryColumn
                            category="SAFETY"
                            colleges={categorizedColleges.SAFETY}
                            onRemove={handleRemove}
                            removingId={removingId}
                            onViewDetails={handleOpenFitModal}
                            selectedColleges={selectedColleges}
                            onToggleSelect={toggleSelection}
                            selectionMode={selectionMode}
                            onOpenChat={handleOpenChat}
                            canRemove={canAccessLaunchpad}
                        />
                    )}
                </div>
            )}

            {/* Credits Upgrade Modal */}
            <CreditsUpgradeModal
                isOpen={showCreditsModal}
                onClose={closeCreditsModal}
                creditsRemaining={creditsRemaining}
                feature={creditsModalFeature}
            />

            {/* Floating Chat Button - Fixed to bottom-right (Only in Detail View) */}
            {fitModalCollege && !isChatOpen && (
                <button
                    onClick={() => handleOpenChat(fitModalCollege)}
                    className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-[#D6E8D5]0 to-orange-600 text-white rounded-full shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-300 font-medium group"
                >
                    <div className="relative">
                        <ChatBubbleLeftRightIcon className="h-6 w-6" />
                        <SparklesIcon className="h-3 w-3 absolute -top-1 -right-1 text-yellow-200 animate-pulse" />
                    </div>
                    <span className="font-bold">Ask AI</span>
                </button>
            )}

            {/* Fit Chat Widget */}
            <FitChatWidget
                universityId={chatCollege?.university_id}
                universityName={chatCollege?.university_name}
                isOpen={isChatOpen}
                onClose={handleCloseChat}
            />
        </div>
    );
};

export default MyLaunchpad;
