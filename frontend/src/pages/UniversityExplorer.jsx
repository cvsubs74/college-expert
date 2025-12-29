import React, { useState, useMemo, useEffect } from 'react';
import {
    MagnifyingGlassIcon,
    MapPinIcon,
    TrophyIcon,
    CurrencyDollarIcon,
    BookOpenIcon,
    UsersIcon,
    ArrowTrendingUpIcon,
    FunnelIcon,
    XMarkIcon,
    ChevronRightIcon,
    ChevronLeftIcon,
    ArrowLeftIcon,
    AcademicCapIcon,
    ScaleIcon,
    BriefcaseIcon,
    BuildingLibraryIcon,
    ArrowPathIcon,
    ExclamationTriangleIcon,
    SparklesIcon,
    GlobeAltIcon,
    ArrowsUpDownIcon,
    StarIcon,
    CalendarIcon,
    LightBulbIcon,
    FlagIcon,
    CheckCircleIcon,
    ChartBarIcon,
    EyeIcon,
    BanknotesIcon,
    RocketLaunchIcon,
    LockClosedIcon
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid, FilmIcon } from '@heroicons/react/24/solid';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { startSession, sendMessage, extractFullResponse, getCollegeList, updateCollegeList, getPrecomputedFits, checkFitRecomputationNeeded, computeAllFits, computeSingleFit } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';
import { useToast } from '../components/Toast';
import FitBreakdownPanel from '../components/FitBreakdownPanel';
import FitAnalysisModal from '../components/FitAnalysisModal';
import UniversityProfilePage from '../components/UniversityProfilePage';
import {
    TabOverview, TabAcademics, TabAdmissions,
    TabFinancials, TabCampus, TabOutcomes
} from '../components/UniversityDetailTabs';
import MediaGallery from '../components/MediaGallery';
import UniversityDetailPage from '../components/UniversityDetailPage';
import CreditsUpgradeModal from '../components/CreditsUpgradeModal';
import UniversityChatWidget from '../components/UniversityChatWidget';
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

// API Configuration
const KNOWLEDGE_BASE_UNIVERSITIES_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL ||
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

// --- Badge Component ---
const Badge = ({ children, color }) => {
    const colorClasses = {
        blue: "bg-blue-100 text-blue-800",
        green: "bg-green-100 text-green-800",
        purple: "bg-purple-100 text-purple-800",
        orange: "bg-[#FCEEE8] text-[#C05838]",
        red: "bg-red-100 text-red-800",
        gray: "bg-gray-100 text-gray-800",
        white: "bg-white/20 text-white backdrop-blur-sm",
    };
    return (
        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${colorClasses[color] || colorClasses.gray}`}>
            {children}
        </span>
    );
};

// --- Transform API data to component format ---
const transformUniversityData = (apiData) => {
    const profile = apiData.profile || {};
    const metadata = profile.metadata || {};
    const admissions = profile.admissions_data || {};
    const currentStatus = admissions.current_status || {};
    const financials = profile.financials || {};
    const outcomes = profile.outcomes || {};
    const strategic = profile.strategic_profile || {};
    const academicStructure = profile.academic_structure || {};

    // Extract financials from cost_of_attendance_breakdown
    const coaBreakdown = financials.cost_of_attendance_breakdown || {};
    const inStateData = coaBreakdown.in_state || {};
    const outStateData = coaBreakdown.out_of_state || {};

    // Extract popular majors from colleges
    const majors = [];
    if (academicStructure.colleges) {
        academicStructure.colleges.forEach(college => {
            (college.majors || []).slice(0, 3).forEach(major => {
                if (major.name && majors.length < 6) {
                    majors.push(major.name);
                }
            });
        });
    }

    // Use pre-extracted US News rank from backend API (already parsed during ingest)
    // Backend extracts from strategic_profile.rankings[] with proper fallback logic
    const usNewsRank = apiData.us_news_rank || 'N/A';

    // Forbes rank: extract from nested array only if needed (not pre-extracted by backend)
    let forbesRank = 'N/A';
    if (Array.isArray(strategic.rankings)) {
        const forbesObj = strategic.rankings.find(r => r.source === "Forbes");
        if (forbesObj) forbesRank = forbesObj.rank_overall || forbesObj.rank_in_category || 'N/A';
    }

    // FIXED: Use exact university_id from ES (no longer normalizing to lowercase)
    // The backend KB stores IDs with mixed case (e.g., University_of_Chicago)
    // We must preserve the exact ID for fit analysis to work correctly
    const rawId = apiData.university_id || profile._id || '';
    const exactId = rawId
        .replace(/_slug$/, '')            // Remove _slug suffix only
        .replace(/[-\s]+/g, '_');         // Replace hyphens and spaces with underscores

    return {
        id: exactId,
        name: apiData.official_name || metadata.official_name || 'Unknown',
        shortName: metadata.official_name?.split(' ').slice(0, 3).join(' ') || apiData.official_name,
        location: apiData.location || metadata.location || { city: 'N/A', state: 'N/A', type: 'N/A' },
        logoUrl: apiData.logo_url || profile.logo_url || null,
        rankings: {
            usNews: usNewsRank,
            forbes: forbesRank
        },
        admissions: {
            acceptanceRate: currentStatus.overall_acceptance_rate || apiData.acceptance_rate || 'N/A',
            gpa: admissions.admitted_student_profile?.gpa?.average_gpa_admitted ||
                admissions.admitted_student_profile?.average_gpa ||
                currentStatus.gpa_requirements?.average_gpa_admitted ||
                'N/A',
            testPolicy: currentStatus.test_policy_details || 'N/A'
        },
        financials: {
            inStateTuition: inStateData.tuition || financials.in_state_tuition || 'N/A',
            outStateTuition: outStateData.tuition || financials.out_of_state_tuition || 'N/A',
            inStateCOA: inStateData.total_coa || financials.in_state_total_coa || 'N/A',
            outStateCOA: outStateData.total_coa || financials.out_of_state_total_coa || financials.estimated_coa || 'N/A'
        },
        outcomes: {
            medianEarnings: outcomes.median_earnings_10yr || apiData.median_earnings_10yr || 'N/A',
            topEmployers: outcomes.top_employers || []
        },
        // Use top-level summary from ES (AI-generated) first, fallback to profile executive_summary
        summary: apiData.summary || strategic.executive_summary || 'No summary available.',
        majors: majors.length > 0 ? majors : ['Information not available'],
        marketPosition: apiData.market_position || strategic.market_position || 'N/A',
        // Soft fit category (acceptance-rate based, computed at ingest)
        softFitCategory: apiData.soft_fit_category || null,
        // Visual content (infographics, slides, videos)
        media: apiData.media || null,
        // Keep full profile for detail view
        fullProfile: profile
    };
};

// --- University Card Component ---
const UniversityCard = ({ uni, onSelect, onCompare, isSelectedForCompare, sentiment, onSentimentClick, isInList, onToggleList, fitAnalysis, onAnalyzeFit, isAnalyzing, onShowFitDetails, onOpenChat }) => {
    // Fit category ribbon styling
    const fitConfig = {
        SAFETY: { gradient: 'from-[#1A4D2E] to-[#2D6B45]', label: 'Safety', icon: '🛡️' },
        TARGET: { gradient: 'from-blue-500 to-indigo-600', label: 'Target', icon: '🎯' },
        REACH: { gradient: 'from-[#C05838] to-[#D4704F]', label: 'Reach', icon: '🔼' },
        SUPER_REACH: { gradient: 'from-red-500 to-rose-600', label: 'Super Reach', icon: '🚀' }
    };

    const currentFit = fitAnalysis?.fit_category || uni.softFitCategory || 'TARGET';
    const fit = fitConfig[currentFit] || fitConfig.TARGET;
    const matchPercentage = fitAnalysis?.match_percentage;

    return (
        <div className="relative bg-white rounded-2xl border border-[#E0DED8] shadow-sm hover:shadow-lg transition-all overflow-hidden">
            {/* Fit Category Ribbon */}
            <div className={`absolute top-0 left-0 px-4 py-1.5 bg-gradient-to-r ${fit.gradient} text-white text-xs font-bold rounded-br-xl shadow-sm z-10 flex items-center gap-1.5`}>
                <span>{fit.icon}</span>
                {matchPercentage ? (
                    <span>{matchPercentage}% {fit.label}</span>
                ) : (
                    <span>{fit.label}</span>
                )}
            </div>

            {/* Single Column Layout */}
            <div className="p-5 pt-10">
                {/* Header Row: Avatar + Name + Action Buttons */}
                <div className="flex items-start gap-3 mb-3">
                    {/* Avatar */}
                    <div className="w-11 h-11 rounded-full bg-[#F8F6F0] flex items-center justify-center flex-shrink-0 border border-[#E0DED8] overflow-hidden">
                        {uni.logoUrl ? (
                            <img src={uni.logoUrl} alt={`${uni.name} logo`} className="w-full h-full object-contain p-1" />
                        ) : (
                            <span className="text-lg font-bold text-[#4A4A4A]">{uni.name?.charAt(0) || 'U'}</span>
                        )}
                    </div>
                    <div className="flex-1 min-w-0">
                        <h3
                            onClick={() => onSelect(uni)}
                            className="font-serif text-lg font-bold text-[#2C2C2C] hover:text-[#1A4D2E] cursor-pointer transition-colors"
                        >
                            {uni.name}
                        </h3>
                        <div className="flex items-center gap-2 text-sm text-[#4A4A4A]">
                            <MapPinIcon className="h-4 w-4" />
                            <span>{uni.location.city}, {uni.location.state}</span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${uni.location.type === 'Private' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                                }`}>
                                {uni.location.type}
                            </span>
                        </div>
                    </div>
                    {/* Inline Action Buttons (moved from right panel) */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                        <button
                            onClick={() => onSelect(uni)}
                            className="px-3 py-2 rounded-xl text-sm font-medium bg-[#1A4D2E] text-white hover:bg-[#2D6B45] transition-all shadow-sm flex items-center gap-1.5"
                        >
                            <EyeIcon className="h-4 w-4" />
                            Explore
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                if (uni.isLimitReached) {
                                    // Navigate to upgrade page
                                    window.location.href = '/payment';
                                } else {
                                    onToggleList(uni);
                                }
                            }}
                            className={`px-3 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-1.5 ${isInList
                                ? 'bg-green-100 text-green-700 hover:bg-red-100 hover:text-red-700'
                                : uni.isLimitReached
                                    ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 cursor-pointer'
                                    : 'bg-[#D6E8D5] text-[#1A4D2E] hover:bg-[#A8C5A6]'
                                }`}
                        >
                            {isInList ? (
                                <><CheckCircleIcon className="h-4 w-4" /> Saved</>
                            ) : uni.isLimitReached ? (
                                <><SparklesIcon className="h-4 w-4" /> Upgrade</>
                            ) : (
                                <><RocketLaunchIcon className="h-4 w-4" /> Save</>
                            )}
                        </button>
                        <button
                            onClick={() => onCompare(uni)}
                            className={`p-2 rounded-xl transition-all ${isSelectedForCompare
                                ? 'bg-[#1A4D2E] text-white'
                                : 'bg-[#F8F6F0] text-[#4A4A4A] hover:bg-[#E0DED8]'
                                }`}
                            title="Compare"
                        >
                            <ScaleIcon className="h-4 w-4" />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); onOpenChat(uni); }}
                            className="p-2 rounded-xl bg-[#F8F6F0] text-[#4A4A4A] hover:bg-[#E0DED8] transition-all"
                            title="Ask AI"
                        >
                            <ChatBubbleLeftRightIcon className="h-4 w-4" />
                        </button>
                    </div>
                </div>

                {/* Stats Row */}
                <div className="flex flex-wrap gap-2 mb-3">
                    <div className="flex items-center gap-1.5 bg-[#D6E8D5] px-3 py-1.5 rounded-lg">
                        <ChartBarIcon className="h-4 w-4 text-[#1A4D2E]" />
                        <span className="text-xs font-medium text-[#1A4D2E]">
                            {uni.admissions.acceptanceRate !== 'N/A' ? `${uni.admissions.acceptanceRate}%` : 'N/A'} Accept
                        </span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-blue-50 px-3 py-1.5 rounded-lg">
                        <TrophyIcon className="h-4 w-4 text-blue-600" />
                        <span className="text-xs font-medium text-blue-700">
                            #{uni.rankings.usNews !== 'N/A' ? uni.rankings.usNews : '—'} US News
                        </span>
                    </div>
                    {uni.financials?.inStateTuition && uni.financials.inStateTuition !== 'N/A' && (
                        <div className="flex items-center gap-1.5 bg-green-50 px-3 py-1.5 rounded-lg">
                            <CurrencyDollarIcon className="h-4 w-4 text-green-600" />
                            <span className="text-xs font-medium text-green-700">
                                ${uni.financials.inStateTuition.toLocaleString()}
                            </span>
                        </div>
                    )}
                </div>

                {/* Summary */}
                {uni.summary && uni.summary !== 'No summary available.' && (
                    <p className="text-sm text-[#4A4A4A] line-clamp-2">{uni.summary}</p>
                )}
            </div>
        </div>
    );
};

// --- Favorite Card Component (for college list items) ---
const FavoriteCard = ({ college, onRemove, onViewDetails, fitAnalysis, fullUniversityData }) => {
    const formatNumber = (num) => {
        if (num === 'N/A' || num === null || num === undefined) return 'N/A';
        return typeof num === 'number' ? num.toLocaleString() : num;
    };

    const fitColors = {
        SAFETY: 'bg-green-100 text-green-800 border-green-300',
        TARGET: 'bg-blue-100 text-blue-800 border-blue-300',
        REACH: 'bg-[#FCEEE8] text-[#C05838] border-[#E8A090]',
        SUPER_REACH: 'bg-red-100 text-red-800 border-red-300'
    };

    const fit = fitAnalysis || college.fit_analysis || {};
    const fitCategory = fit.fit_category || 'TARGET';
    const matchPercentage = fit.match_percentage;

    // Use full university data if available, otherwise use what's in college object
    const uni = fullUniversityData || {};
    const acceptanceRate = uni.admissions?.acceptanceRate || college.acceptance_rate || 'N/A';
    const tuition = uni.financials?.inStateTuition || college.tuition || 'N/A';
    const rank = uni.rankings?.usNews || college.rank || 'N/A';
    const earnings = uni.outcomes?.medianEarnings || 'N/A';
    const location = uni.location ? `${uni.location.city}, ${uni.location.state}` : (college.location || 'Location N/A');

    // Extract logo from full university data
    const logoUrl = fullUniversityData?.logoUrl || null;

    return (
        <div className="bg-white rounded-2xl shadow-lg shadow-sm border border-gray-100 hover:shadow-xl transition-all duration-300 flex flex-col h-full">
            <div className="p-4 flex-grow">
                <div className="flex justify-between items-start mb-3">
                    {/* Logo */}
                    {logoUrl && (
                        <div className="w-12 h-12 rounded-full bg-[#F8F6F0] flex items-center justify-center flex-shrink-0 border border-[#E0DED8] overflow-hidden mr-3">
                            <img src={logoUrl} alt={`${college.university_name} logo`} className="w-full h-full object-contain p-1" />
                        </div>
                    )}
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-bold text-gray-900 line-clamp-2">
                            {college.university_name}
                        </h3>
                        <div className="flex items-center text-gray-500 text-sm mt-1">
                            <MapPinIcon className="h-4 w-4 mr-1" />
                            {location}
                        </div>
                    </div>
                    {/* Fit Badge */}
                    {fit.fit_category && (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-bold border whitespace-nowrap ${fitColors[fitCategory]}`}>
                            {fitCategory === 'SUPER_REACH' ? '🎯 Super Reach' :
                                fitCategory === 'REACH' ? '🎯 Reach' :
                                    fitCategory === 'TARGET' ? '🎯 Target' :
                                        '✅ Safety'}
                            {matchPercentage && ` ${matchPercentage}%`}
                        </span>
                    )}
                </div>

                {/* Stats Grid - Same as UniversityCard */}
                <div className="grid grid-cols-2 gap-2 text-sm mb-3">
                    <div className="bg-[#D6E8D5] p-2 rounded-xl">
                        <div className="text-gray-500 text-xs">Acceptance</div>
                        <div className="font-semibold text-gray-900">
                            {acceptanceRate !== 'N/A' ? `${acceptanceRate}%` : 'N/A'}
                        </div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                        <div className="text-gray-500 text-xs">Tuition</div>
                        <div className="font-semibold text-gray-900">
                            {tuition !== 'N/A' ? `$${formatNumber(tuition)}` : 'N/A'}
                        </div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                        <div className="text-gray-500 text-xs">US News Rank</div>
                        <div className="font-semibold text-gray-900">
                            {rank !== 'N/A' ? `#${rank}` : 'N/A'}
                        </div>
                    </div>
                    <div className="bg-[#D6E8D5] p-2 rounded-xl">
                        <div className="text-gray-500 text-xs">Median Earnings</div>
                        <div className="font-semibold text-gray-900">
                            {earnings !== 'N/A' ? `$${formatNumber(earnings)}` : 'N/A'}
                        </div>
                    </div>
                </div>

                {/* Fit Explanation (from LLM justification) - condensed */}
                {fit.explanation && (
                    <div className="text-xs text-gray-600 bg-blue-50 rounded p-2 border border-blue-100 line-clamp-2">
                        <span className="font-medium text-blue-700">✨ </span>
                        {fit.explanation.substring(0, 100)}...
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-100">
                <div className="flex gap-2">
                    <button
                        onClick={() => onViewDetails && onViewDetails(college)}
                        className="flex-1 bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] text-white py-2 rounded-xl text-sm font-medium hover:from-amber-400 hover:to-orange-400 flex items-center justify-center gap-1 shadow-lg shadow-md"
                    >
                        View Details
                        <ChevronRightIcon className="h-4 w-4" />
                    </button>
                    <button
                        onClick={() => onRemove(college)}
                        className="px-4 py-2 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors flex items-center gap-1"
                    >
                        <XMarkIcon className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};

// --- Comparison View Component ---
const ComparisonView = ({ universities, onRemove }) => {
    if (universities.length === 0) return null;

    const formatNumber = (num) => {
        if (num === 'N/A' || num === null || num === undefined) return 'N/A';
        return typeof num === 'number' ? num.toLocaleString() : num;
    };

    return (
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden mb-8">
            <div className="p-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                    <ScaleIcon className="h-5 w-5 text-blue-600" /> Comparison
                </h2>
                <span className="text-sm text-gray-500">{universities.length} of 3 selected</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead>
                        <tr className="bg-gray-50 border-b border-gray-200">
                            <th className="p-4 text-gray-500 font-medium w-40 bg-gray-50 sticky left-0">Metric</th>
                            {universities.map(uni => (
                                <th key={uni.id} className="p-4 min-w-[200px] relative">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="font-bold text-lg text-gray-900">{uni.shortName || uni.name}</div>
                                            <div className="text-xs text-gray-500 font-normal">{uni.location.city}, {uni.location.state}</div>
                                        </div>
                                        <button
                                            onClick={() => onRemove(uni)}
                                            className="text-gray-400 hover:text-red-500 p-1"
                                        >
                                            <XMarkIcon className="h-4 w-4" />
                                        </button>
                                    </div>
                                </th>
                            ))}
                            {[...Array(3 - universities.length)].map((_, i) => (
                                <th key={`placeholder-${i}`} className="p-4 min-w-[200px] text-gray-300 font-normal italic border-l">
                                    Select a university to compare
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">Type</td>
                            {universities.map(uni => <td key={uni.id} className="p-4 border-l">{uni.location.type}</td>)}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">US News Rank</td>
                            {universities.map(uni => (
                                <td key={uni.id} className="p-4 border-l">
                                    <div className="font-semibold text-blue-600">
                                        {uni.rankings.usNews !== 'N/A' ? `#${uni.rankings.usNews}` : 'N/A'}
                                    </div>
                                </td>
                            ))}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">Acceptance Rate</td>
                            {universities.map(uni => (
                                <td key={uni.id} className="p-4 border-l">
                                    <div className="flex items-center gap-2">
                                        {uni.admissions.acceptanceRate !== 'N/A' && (
                                            <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                                                <div className="h-full bg-green-500" style={{ width: `${uni.admissions.acceptanceRate}%` }}></div>
                                            </div>
                                        )}
                                        {uni.admissions.acceptanceRate !== 'N/A' ? `${uni.admissions.acceptanceRate}%` : 'N/A'}
                                    </div>
                                </td>
                            ))}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">Avg GPA</td>
                            {universities.map(uni => <td key={uni.id} className="p-4 border-l">{uni.admissions.gpa}</td>)}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">Tuition (In-State)</td>
                            {universities.map(uni => (
                                <td key={uni.id} className="p-4 border-l">
                                    {uni.financials.inStateTuition !== 'N/A' ? `$${formatNumber(uni.financials.inStateTuition)}` : 'N/A'}
                                </td>
                            ))}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">Tuition (Out-State)</td>
                            {universities.map(uni => (
                                <td key={uni.id} className="p-4 border-l">
                                    {uni.financials.outStateTuition !== 'N/A' ? `$${formatNumber(uni.financials.outStateTuition)}` : 'N/A'}
                                </td>
                            ))}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                        <tr>
                            <td className="p-4 font-medium text-gray-700 bg-gray-50 sticky left-0">Median Earnings</td>
                            {universities.map(uni => (
                                <td key={uni.id} className="p-4 border-l text-green-700 font-semibold">
                                    {uni.outcomes.medianEarnings !== 'N/A' ? `$${formatNumber(uni.outcomes.medianEarnings)}` : 'N/A'}
                                </td>
                            ))}
                            {[...Array(3 - universities.length)].map((_, i) => <td key={i} className="p-4 border-l"></td>)}
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// --- University Detail Component ---
const UniversityDetail = ({ uni, onBack, sentiment, fitAnalysis }) => {
    const [activeTab, setActiveTab] = useState('overview');
    const [isFitModalOpen, setIsFitModalOpen] = useState(false);

    if (!uni) return null;

    const tabs = [
        { id: 'overview', label: 'Overview', icon: SparklesIcon },
        { id: 'media', label: 'Visual Guide', icon: FilmIcon },
        { id: 'academics', label: 'Academics', icon: AcademicCapIcon },
        { id: 'admissions', label: 'Admissions', icon: CheckCircleIcon },
        { id: 'financials', label: 'Cost & Aid', icon: CurrencyDollarIcon },
        { id: 'campus', label: 'Campus Life', icon: MapPinIcon },
        { id: 'outcomes', label: 'Outcomes', icon: ChartBarIcon },
    ];

    return (
        <div className="bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden flex flex-col min-h-screen">
            <FitAnalysisModal
                isOpen={isFitModalOpen}
                onClose={() => setIsFitModalOpen(false)}
                fitAnalysis={fitAnalysis}
                uniName={uni.name}
                softFitCategory={uni.softFitCategory}
            />

            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-8 text-white relative">
                <button
                    onClick={onBack}
                    className="absolute top-6 left-6 p-2 bg-white/20 hover:bg-white/30 rounded-full backdrop-blur-sm transition-colors text-white"
                >
                    <ArrowLeftIcon className="h-5 w-5" />
                </button>
                <div className="mt-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
                    <div>
                        <div className="flex flex-wrap gap-2 mb-3">
                            <span className="px-2 py-1 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-sm">{uni.location.type}</span>
                            <span className="bg-blue-800/50 px-2 py-1 rounded-full text-xs flex items-center gap-1 text-white">
                                <MapPinIcon className="h-3 w-3" /> {uni.location.city}, {uni.location.state}
                            </span>
                        </div>
                        <h1 className="text-3xl md:text-5xl font-bold mb-2">{uni.name}</h1>
                        <p className="text-blue-100 text-lg font-medium">{uni.market_position}</p>
                    </div>

                </div>
            </div>

            {/* Tabs Navigation */}
            <div className="border-b border-gray-200 px-6 sticky top-0 bg-white z-20 overflow-x-auto">
                <nav className="flex space-x-8" aria-label="Tabs">
                    {tabs.map((tab) => {
                        const Icon = tab.icon;
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`
                                    group inline-flex items-center gap-2 py-4 border-b-2 font-medium text-sm whitespace-nowrap transition-all outline-none
                                    ${isActive
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }
                                `}
                            >
                                <Icon className={`h-5 w-5 ${isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}`} />
                                {tab.label}
                            </button>
                        );
                    })}
                </nav>
            </div>

            {/* Content Area */}
            <div className="p-6 md:p-8 bg-gray-50 flex-grow min-h-[500px]">
                {activeTab === 'overview' && <TabOverview uni={uni} sentiment={sentiment} />}
                {activeTab === 'media' && <MediaGallery media={uni.media} />}
                {activeTab === 'academics' && <TabAcademics uni={uni} />}
                {activeTab === 'admissions' && <TabAdmissions uni={uni} />}
                {activeTab === 'financials' && <TabFinancials uni={uni} />}
                {activeTab === 'campus' && <TabCampus uni={uni} />}
                {activeTab === 'outcomes' && <TabOutcomes uni={uni} />}

                <div className="h-12"></div>
            </div>
        </div>
    );
};

// --- Deep Dive Research Component ---




// --- Loading Skeleton ---
const LoadingSkeleton = () => (
    <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
                <div className="flex justify-between items-start">
                    <div className="flex-1">
                        <div className="h-6 bg-gray-200 rounded w-1/3 mb-3"></div>
                        <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
                        <div className="h-16 bg-gray-200 rounded w-full mb-4"></div>
                        <div className="flex gap-4">
                            <div className="h-10 bg-gray-200 rounded w-24"></div>
                            <div className="h-10 bg-gray-200 rounded w-24"></div>
                        </div>
                    </div>
                    <div className="ml-6 flex flex-col items-end gap-2">
                        <div className="h-8 bg-gray-200 rounded-full w-20"></div>
                        <div className="h-6 bg-gray-200 rounded w-16"></div>
                    </div>
                </div>
            </div>
        ))}
    </div>
);

// --- Main App Component ---
const UniversityExplorer = () => {
    const { canAccessLaunchpad, isFreeTier, promptUpgrade, promptCreditsUpgrade, creditsRemaining, showCreditsModal, closeCreditsModal, creditsModalFeature } = usePayment();
    const toast = useToast();
    const [universities, setUniversities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [searchTerm, setSearchTerm] = useState("");
    const [selectedType, setSelectedType] = useState("All");
    const [selectedState, setSelectedState] = useState("All");
    const [selectedFitCategory, setSelectedFitCategory] = useState("All");
    const [maxAcceptance, setMaxAcceptance] = useState(100);

    const [activeView, setActiveView] = useState("list");
    const [selectedUni, setSelectedUni] = useState(null);
    const [comparisonList, setComparisonList] = useState([]);

    // Pagination and sorting
    const [currentPage, setCurrentPage] = useState(0);
    const [sortBy, setSortBy] = useState("usNews"); // Default sort by US News rank
    const CARDS_PER_PAGE = 6;

    // News sentiment tracking with localStorage persistence
    const [sentimentData, setSentimentData] = useState(() => {
        try {
            const cached = localStorage.getItem('universitySentiments');
            return cached ? JSON.parse(cached) : {};
        } catch (e) {
            console.error('Error loading cached sentiments:', e);
            return {};
        }
    });
    const [scanningBatch, setScanningBatch] = useState(false);
    const [selectedSentiment, setSelectedSentiment] = useState(null);
    const [showSentimentModal, setShowSentimentModal] = useState(false);

    // Deep research tracking with localStorage persistence
    const [deepResearchData, setDeepResearchData] = useState(() => {
        try {
            const cached = localStorage.getItem('universityDeepResearch');
            return cached ? JSON.parse(cached) : {};
        } catch (e) {
            console.error('Error loading cached deep research:', e);
            return {};
        }
    });

    // Persist sentiment data to localStorage
    useEffect(() => {
        try {
            localStorage.setItem('universitySentiments', JSON.stringify(sentimentData));
        } catch (e) {
            console.error('Error saving sentiments:', e);
        }
    }, [sentimentData]);

    // Persist deep research data to localStorage
    useEffect(() => {
        try {
            localStorage.setItem('universityDeepResearch', JSON.stringify(deepResearchData));
        } catch (e) {
            console.error('Error saving deep research:', e);
        }
    }, [deepResearchData]);

    // Get current user from auth context
    const { currentUser } = useAuth();

    // College list management
    const [myCollegeList, setMyCollegeList] = useState([]);
    const [collegeListLoading, setCollegeListLoading] = useState(false);

    // Pre-computed fits for ALL universities (from college_fits field)
    const [precomputedFits, setPrecomputedFits] = useState({});
    const [fitsLoading, setFitsLoading] = useState(false);

    // Chat widget state
    const [chatUniversity, setChatUniversity] = useState(null);
    const [isChatOpen, setIsChatOpen] = useState(false);

    const handleOpenChat = (uni) => {
        setChatUniversity(uni);
        setIsChatOpen(true);
    };

    const handleCloseChat = () => {
        setIsChatOpen(false);
    };

    // Load college list and pre-computed fits on mount
    useEffect(() => {
        const loadCollegeList = async () => {
            if (!currentUser?.email) return;

            try {
                setCollegeListLoading(true);
                const result = await getCollegeList(currentUser.email);
                if (result.success) {
                    setMyCollegeList(result.college_list || []);
                    console.log('[College List] Loaded:', result.college_list?.length || 0, 'colleges');
                }
            } catch (err) {
                console.error('[College List] Error loading:', err);
            } finally {
                setCollegeListLoading(false);
            }
        };

        const loadPrecomputedFits = async () => {
            if (!currentUser?.email) return;

            try {
                setFitsLoading(true);

                // First, check if recomputation is needed
                const recomputeStatus = await checkFitRecomputationNeeded(currentUser.email);
                if (recomputeStatus.needs_recomputation) {
                    console.log('[Pre-computed Fits] Recomputation needed:', recomputeStatus.reason);
                    setRecomputingFits(true);

                    // Trigger recomputation
                    await computeAllFits(currentUser.email);
                    setRecomputingFits(false);
                }

                // Fetch all pre-computed fits (no filtering, get all)
                const result = await getPrecomputedFits(currentUser.email, {}, 500, 'rank');
                // API returns 'fits' array, not 'results'
                if (result.success && result.fits) {
                    // Convert array to object keyed by university_id for quick lookup
                    const fitsMap = {};
                    result.fits.forEach(fit => {
                        /* fit mapping updated */
                        fitsMap[fit.university_id] = {
                            fit_category: fit.fit_category,
                            match_percentage: fit.match_percentage || fit.match_score,
                            university_name: fit.university_name,
                            explanation: fit.explanation,
                            factors: fit.factors,
                            // Core recommendations
                            recommendations: typeof fit.recommendations === 'string' ? JSON.parse(fit.recommendations) : (fit.recommendations || []),
                            gap_analysis: typeof fit.gap_analysis === 'string' ? JSON.parse(fit.gap_analysis) : (fit.gap_analysis || {}),
                            // Rich new fields
                            essay_angles: typeof fit.essay_angles === 'string' ? JSON.parse(fit.essay_angles) : (fit.essay_angles || []),
                            application_timeline: typeof fit.application_timeline === 'string' ? JSON.parse(fit.application_timeline) : (fit.application_timeline || {}),
                            scholarship_matches: typeof fit.scholarship_matches === 'string' ? JSON.parse(fit.scholarship_matches) : (fit.scholarship_matches || []),
                            test_strategy: typeof fit.test_strategy === 'string' ? JSON.parse(fit.test_strategy) : (fit.test_strategy || {}),
                            major_strategy: typeof fit.major_strategy === 'string' ? JSON.parse(fit.major_strategy) : (fit.major_strategy || {}),
                            demonstrated_interest_tips: typeof fit.demonstrated_interest_tips === 'string' ? JSON.parse(fit.demonstrated_interest_tips) : (fit.demonstrated_interest_tips || []),
                            red_flags_to_avoid: typeof fit.red_flags_to_avoid === 'string' ? JSON.parse(fit.red_flags_to_avoid) : (fit.red_flags_to_avoid || []),
                            // Metadata
                            us_news_rank: fit.us_news_rank,
                            location: fit.location,
                            acceptance_rate: fit.acceptance_rate,
                            market_position: fit.market_position,
                            infographic_url: fit.infographic_url
                        };
                    });
                    setPrecomputedFits(fitsMap);
                    console.log('[Pre-computed Fits] Loaded:', Object.keys(fitsMap).length, 'fits');
                }
            } catch (err) {
                console.error('[Pre-computed Fits] Error loading:', err);
                setRecomputingFits(false);
            } finally {
                setFitsLoading(false);
            }
        };

        loadCollegeList();
        loadPrecomputedFits();
    }, [currentUser]);

    // Toggle college in list (add/remove)
    // Track which university is having fit computed
    const [computingFitFor, setComputingFitFor] = useState(null);

    // Analysis progress modal state
    const [analysisModal, setAnalysisModal] = useState({
        isOpen: false,
        universityName: '',
        step: '', // 'fit', 'infographic', 'complete'
        progress: 0
    });

    const handleToggleCollegeList = async (university) => {
        if (!currentUser?.email) {
            console.warn('[College List] No user logged in');
            return;
        }

        const isInList = myCollegeList.some(c => c.university_id === university.id);
        const action = isInList ? 'remove' : 'add';

        // Free tier: 3 colleges maximum, PERMANENT (no removal)
        const FREE_TIER_MAX_COLLEGES = 3;
        const isFreeTier = !canAccessLaunchpad;

        if (isFreeTier) {
            // Block removal for free tier - colleges are permanent
            if (action === 'remove') {
                alert('Free tier colleges are permanent. Upgrade to Pro to modify your list.');
                return;
            }
            // Block adding if already at limit
            if (action === 'add' && myCollegeList.length >= FREE_TIER_MAX_COLLEGES) {
                promptCreditsUpgrade('adding more colleges (free tier limit: 3 permanent colleges)');
                return;
            }
        }

        try {
            const result = await updateCollegeList(
                currentUser.email,
                action,
                { id: university.id, name: university.name },
                '' // intended major - could be passed from profile
            );

            if (result.success) {
                setMyCollegeList(result.college_list || []);
                console.log(`[College List] ${action === 'add' ? 'Added' : 'Removed'}: ${university.name}`);

                // Compute fit on add
                if (action === 'add') {
                    setComputingFitFor(university.id);

                    // Show analysis modal instead of toast
                    setAnalysisModal({
                        isOpen: true,
                        universityName: university.name,
                        step: 'fit',
                        progress: 0
                    });

                    try {
                        console.log(`[Fit] Computing fit for ${university.name}...`);
                        setAnalysisModal(prev => ({ ...prev, step: 'fit', progress: 25 }));

                        const fitResult = await computeSingleFit(currentUser.email, university.id);

                        // Handle insufficient credits (402 response)
                        if (fitResult.insufficientCredits) {
                            console.warn('[Fit] Insufficient credits for fit analysis');
                            setAnalysisModal(prev => ({ ...prev, isOpen: false }));
                            promptCreditsUpgrade('fit analysis');
                            return;
                        }

                        console.log(`[Fit] Computed: ${university.name} -> ${fitResult?.fit_analysis?.fit_category || 'N/A'}`);
                        // Infographic generation removed - using static CSS template instead
                        setAnalysisModal(prev => ({ ...prev, step: 'refreshing', progress: 75 }));

                        // Refresh precomputed fits to get the new fit
                        const fitsResult = await getPrecomputedFits(currentUser.email, {}, 500, 'rank');
                        // API returns 'fits' array, not 'results'
                        if (fitsResult.success && fitsResult.fits) {
                            const fitsMap = {};
                            fitsResult.fits.forEach(fit => {
                                fitsMap[fit.university_id] = {
                                    fit_category: fit.fit_category,
                                    match_percentage: fit.match_percentage || fit.match_score,
                                    university_name: fit.university_name,
                                    explanation: fit.explanation,
                                    factors: fit.factors,
                                    infographic_url: fit.infographic_url
                                };
                            });
                            setPrecomputedFits(fitsMap);
                            console.log(`[Fit] Refreshed fits: ${Object.keys(fitsMap).length} total`);
                        }

                        // Show complete status
                        setAnalysisModal(prev => ({ ...prev, step: 'complete', progress: 100 }));

                        // Auto-close modal after 1.5 seconds
                        setTimeout(() => {
                            setAnalysisModal(prev => ({ ...prev, isOpen: false }));
                        }, 1500);

                    } catch (fitErr) {
                        console.error('[Fit] Error computing fit:', fitErr);
                        setAnalysisModal(prev => ({ ...prev, step: 'error', progress: 0 }));
                        setTimeout(() => {
                            setAnalysisModal(prev => ({ ...prev, isOpen: false }));
                        }, 2000);
                    } finally {
                        setComputingFitFor(null);
                    }
                }
            }
        } catch (err) {
            console.error('[College List] Error updating:', err);
        }
    };

    // Check if university is in user's list
    const isInCollegeList = (universityId) => {
        return myCollegeList.some(c => c.university_id === universityId);
    };

    // Get fit analysis for a university - prioritize pre-computed fits (has current profile data)
    const getCollegeFitAnalysis = (universityId) => {
        // First check pre-computed fits - these are recomputed when profile changes
        // so they always have the most accurate, up-to-date analysis
        if (precomputedFits[universityId]) {
            return precomputedFits[universityId];
        }
        // Fall back to college list (for universities added before fits were computed)
        const college = myCollegeList.find(c => c.university_id === universityId);
        return college?.fit_analysis || null;
    };

    // State for fit analysis
    const [analyzingFit, setAnalyzingFit] = useState(null); // university ID being analyzed
    const [showFitModal, setShowFitModal] = useState(false);
    const [selectedFitData, setSelectedFitData] = useState(null);

    // Analyze fit for a university
    const handleAnalyzeFit = async (university) => {
        if (!currentUser?.email) {
            console.warn('[Fit Analysis] No user logged in');
            return;
        }

        setAnalyzingFit(university.id);
        console.log(`[Fit Analysis] Starting analysis for ${university.name}`);

        try {
            // Use exact university ID - fallback to name with underscores (preserving case)
            const universityId = university.id || university.name.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');

            // Build query that tells agent to use the calculate_college_fit tool
            const query = `Analyze my fit for ${university.name}. Use the calculate_college_fit tool with university_id="${universityId}" to get the deterministic fit analysis.`;

            // Pass the user email so agent can use it for profile lookup
            const response = await startSession(query, currentUser.email);
            const fullResponse = extractFullResponse(response);
            const resultText = fullResponse.result || fullResponse;

            // Parse the fit analysis from response
            const fitAnalysis = parseFitAnalysis(resultText, university);

            console.log(`[Fit Analysis] Completed for ${university.name}:`, fitAnalysis.fit_category);

            // Refresh the college list from server to get the stored fit analysis
            // This ensures we have the latest data including the fit stored in ES
            try {
                const refreshResult = await getCollegeList(currentUser.email);
                if (refreshResult.success) {
                    setMyCollegeList(refreshResult.college_list || []);
                    console.log('[Fit Analysis] Refreshed college list from server');
                }
            } catch (refreshErr) {
                console.warn('[Fit Analysis] Could not refresh list, using local update', refreshErr);
                // Fallback to local update if server refresh fails
                const updatedList = myCollegeList.map(c => {
                    if (c.university_id === university.id) {
                        return { ...c, fit_analysis: fitAnalysis, fit_analyzed_at: new Date().toISOString() };
                    }
                    return c;
                });
                setMyCollegeList(updatedList);
            }

        } catch (err) {
            console.error('[Fit Analysis] Error:', err);
        } finally {
            setAnalyzingFit(null);
        }
    };

    // Parse fit analysis from agent response
    const parseFitAnalysis = (responseText, university) => {
        // First, try to extract structured JSON from the response
        // The tool returns: {success, fit_category, match_percentage, factors, recommendations, ...}
        try {
            // Look for JSON object in the response
            const jsonMatch = responseText.match(/\{[\s\S]*"fit_category"[\s\S]*\}/);
            if (jsonMatch) {
                const jsonData = JSON.parse(jsonMatch[0]);
                if (jsonData.success && jsonData.fit_category) {
                    return {
                        fit_category: jsonData.fit_category.toUpperCase(),
                        match_percentage: jsonData.match_percentage || 50,
                        factors: jsonData.factors || [],
                        recommendations: jsonData.recommendations || [],
                        explanation: jsonData.explanation || '',
                        university_name: jsonData.university_name || university.name,
                        raw_response: responseText
                    };
                }
            }
        } catch (e) {
            console.log('[Fit Parser] JSON parsing failed, trying regex', e);
        }

        // Try to find fit category and percentage in different formats
        let categoryMatch = responseText.match(/fit[_\s]*category[:\s]*["']?(SAFETY|TARGET|REACH|SUPER_REACH)["']?/i);
        if (!categoryMatch) {
            categoryMatch = responseText.match(/\*\*FIT_CATEGORY:\*\*\s*(SAFETY|TARGET|REACH|SUPER_REACH)/i);
        }
        if (!categoryMatch) {
            // Look for category words in context
            if (responseText.toLowerCase().includes('safety')) categoryMatch = [null, 'SAFETY'];
            else if (responseText.toLowerCase().includes('target')) categoryMatch = [null, 'TARGET'];
            else if (responseText.toLowerCase().includes('reach')) categoryMatch = [null, 'REACH'];
        }

        let percentageMatch = responseText.match(/match[_\s]*percentage[:\s]*(\d+)/i);
        if (!percentageMatch) {
            percentageMatch = responseText.match(/\*\*MATCH_PERCENTAGE:\*\*\s*(\d+)/i);
        }
        if (!percentageMatch) {
            percentageMatch = responseText.match(/(\d+)%?\s*match/i);
        }

        // Extract factors - look for score patterns
        const factors = [];
        const factorPatterns = [
            /GPA[^\n]*?(\d+)\/40/i,
            /Test[^\n]*?(\d+)\/25/i,
            /Acceptance[^\n]*?(\d+)\/25/i,
            /Course[^\n]*?(\d+)\/20/i,
            /Major[^\n]*?(\d+)\/15/i,
            /Activit[^\n]*?(\d+)\/15/i,
            /Early[^\n]*?(\d+)\/10/i
        ];

        const factorNames = ['GPA Match', 'Test Scores', 'Acceptance Rate', 'Course Rigor', 'Major Fit', 'Activities', 'Early Action'];
        const factorMax = [40, 25, 25, 20, 15, 15, 10];

        factorPatterns.forEach((pattern, i) => {
            const match = responseText.match(pattern);
            if (match) {
                factors.push({
                    name: factorNames[i],
                    score: parseInt(match[1]),
                    max: factorMax[i],
                    detail: `Score: ${match[1]}/${factorMax[i]}`
                });
            }
        });

        // Extract recommendations
        const recommendations = [];
        const recMatches = responseText.match(/(?:recommend|suggestion|improve)[^\n]*?(?:\n[-•*\d].*)+/gi);
        if (recMatches) {
            recMatches.forEach(section => {
                const lines = section.match(/[-•*\d]\.\s*(.+)/g);
                if (lines) {
                    lines.forEach(line => {
                        const text = line.replace(/^[-•*\d]\.?\s*/, '').trim();
                        if (text && !recommendations.includes(text)) {
                            recommendations.push(text);
                        }
                    });
                }
            });
        }

        return {
            fit_category: categoryMatch ? categoryMatch[1].toUpperCase() : 'TARGET',
            match_percentage: percentageMatch ? parseInt(percentageMatch[1]) : 50,
            factors: factors.length > 0 ? factors : [
                { name: 'Analysis', score: 0, max: 100, detail: 'See detailed response below' }
            ],
            recommendations: recommendations.length > 0 ? recommendations : ['Review the detailed analysis for recommendations'],
            raw_response: responseText,
            university_name: university.name
        };
    };

    // Fetch universities from API
    useEffect(() => {
        const fetchUniversities = async () => {
            try {
                setLoading(true);
                setError(null);

                // Fetch all universities (list endpoint)
                const response = await fetch(KNOWLEDGE_BASE_UNIVERSITIES_URL, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (!response.ok) {
                    throw new Error(`Failed to fetch universities: ${response.status}`);
                }

                const data = await response.json();

                if (data.success && data.universities) {
                    // For list view, we have basic info - need to fetch full profiles
                    // Or use search to get full profiles
                    const searchResponse = await fetch(KNOWLEDGE_BASE_UNIVERSITIES_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            query: "university",
                            limit: 1000,
                            search_type: "keyword"
                        })
                    });

                    const searchData = await searchResponse.json();

                    if (searchData.success && searchData.results) {
                        const transformedData = searchData.results.map(transformUniversityData);
                        setUniversities(transformedData);
                    } else {
                        throw new Error('Failed to load university profiles');
                    }
                }
            } catch (err) {
                console.error('Error fetching universities:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchUniversities();
    }, []);

    // Get unique states from data
    const uniqueStates = useMemo(() => {
        const states = [...new Set(universities.map(u => u.location?.state).filter(Boolean))];
        return states.sort();
    }, [universities]);

    // Filter Data
    const filteredUniversities = useMemo(() => {
        return universities.filter(uni => {
            const matchesSearch = uni.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                uni.shortName?.toLowerCase().includes(searchTerm.toLowerCase());
            const matchesType = selectedType === "All" || uni.location?.type === selectedType;
            const matchesState = selectedState === "All" || uni.location?.state === selectedState;
            const acceptanceRate = uni.admissions?.acceptanceRate;
            const matchesAcceptance = acceptanceRate === 'N/A' ||
                acceptanceRate === null ||
                acceptanceRate <= maxAcceptance;

            // Fit category filter - uses precomputedFits if available, falls back to softFitCategory
            let matchesFitCategory = true;
            if (selectedFitCategory !== "All") {
                const fitData = precomputedFits[uni.id];
                if (fitData) {
                    matchesFitCategory = fitData.fit_category === selectedFitCategory;
                } else if (uni.softFitCategory) {
                    // Fall back to soft fit category from university data
                    matchesFitCategory = uni.softFitCategory === selectedFitCategory;
                } else {
                    // No fit data at all - don't match when filtering by category
                    matchesFitCategory = false;
                }
            }

            return matchesSearch && matchesType && matchesState && matchesAcceptance && matchesFitCategory;
        });
    }, [universities, searchTerm, selectedType, selectedState, maxAcceptance, selectedFitCategory, precomputedFits]);

    // Sort filtered universities
    const sortedUniversities = useMemo(() => {
        const sorted = [...filteredUniversities].sort((a, b) => {
            switch (sortBy) {
                case 'usNews':
                    const rankA = a.rankings?.usNews === 'N/A' ? 999 : (a.rankings?.usNews || 999);
                    const rankB = b.rankings?.usNews === 'N/A' ? 999 : (b.rankings?.usNews || 999);
                    return rankA - rankB;
                case 'acceptance':
                    const accA = a.admissions?.acceptanceRate === 'N/A' ? 100 : (a.admissions?.acceptanceRate || 100);
                    const accB = b.admissions?.acceptanceRate === 'N/A' ? 100 : (b.admissions?.acceptanceRate || 100);
                    return accA - accB;
                case 'tuition':
                    const tuitionA = a.financials?.inStateTuition === 'N/A' ? 999999 : (a.financials?.inStateTuition || 999999);
                    const tuitionB = b.financials?.inStateTuition === 'N/A' ? 999999 : (b.financials?.inStateTuition || 999999);
                    return tuitionA - tuitionB;
                case 'name':
                    return (a.name || '').localeCompare(b.name || '');
                default:
                    return 0;
            }
        });
        return sorted;
    }, [filteredUniversities, sortBy]);

    // Paginated universities - all tiers can browse
    const paginatedUniversities = useMemo(() => {
        const start = currentPage * CARDS_PER_PAGE;
        return sortedUniversities.slice(start, start + CARDS_PER_PAGE);
    }, [sortedUniversities, currentPage]);

    const totalPages = Math.ceil(sortedUniversities.length / CARDS_PER_PAGE);

    // Reset page when filters change
    useEffect(() => {
        setCurrentPage(0);
    }, [searchTerm, selectedType, selectedState, maxAcceptance, sortBy, selectedFitCategory]);

    // Parse sentiment from research response
    const parseSentiment = (responseText) => {
        const sentimentMatch = responseText.match(/\*\*SENTIMENT:\s*(POSITIVE|NEGATIVE|NEUTRAL)\*\*/i);
        const headlineMatch = responseText.match(/\*\*HEADLINE:\*\*\s*(.+?)(?=\n\n|$)/i);

        // Clean up the full text by removing the metadata markers
        let cleanedText = responseText;

        // Remove UNIVERSITY marker line
        cleanedText = cleanedText.replace(/###\s*UNIVERSITY:\s*.+?\n/i, '',);

        // Remove SENTIMENT marker
        cleanedText = cleanedText.replace(/\*\*SENTIMENT:\s*(POSITIVE|NEGATIVE|NEUTRAL)\*\*/i, '');

        // Remove HEADLINE marker and the headline itself
        cleanedText = cleanedText.replace(/\*\*HEADLINE:\*\*\s*.+?(?=\n\n)/i, '');

        // Remove source/citation links (often hallucinated by LLM)
        // Matches patterns like [Source](http://...), [1](http://...), (Source: http://...)
        cleanedText = cleanedText.replace(/\[([^\]]+)\]\(https?:\/\/[^\)]+\)/gi, '$1');
        cleanedText = cleanedText.replace(/\(Source:?\s*https?:\/\/[^\)]+\)/gi, '');
        // Remove standalone URLs (on their own line or inline)
        cleanedText = cleanedText.replace(/^https?:\/\/\S+$/gim, '');
        cleanedText = cleanedText.replace(/https?:\/\/\S+/gi, '');
        // Remove "Sources:" section at the end (with various formats)
        cleanedText = cleanedText.replace(/\n\*\*Sources?:?\*\*[\s\S]*$/i, '');
        cleanedText = cleanedText.replace(/\nSources?:\s*\n[\s\S]*$/i, '');
        cleanedText = cleanedText.replace(/\nSources?:?[\s\S]*$/i, '');
        // Remove any remaining empty lines with just whitespace
        cleanedText = cleanedText.replace(/\n\s*\n\s*\n/g, '\n\n');

        // Clean up extra whitespace
        cleanedText = cleanedText.trim();

        return {
            sentiment: sentimentMatch ? sentimentMatch[1].toLowerCase() : 'neutral',
            headline: headlineMatch ? headlineMatch[1].trim() : 'No significant recent news found',
            fullText: cleanedText
        };
    };

    // Parse batch sentiment response
    const parseBatchSentiment = (responseText) => {
        const results = {};
        const sections = responseText.split('---').filter(s => s.trim());

        sections.forEach(section => {
            const uniMatch = section.match(/###\s*UNIVERSITY:\s*(.+?)(?=\n|$)/i);
            if (!uniMatch) return;

            const universityName = uniMatch[1].trim();
            const sentiment = parseSentiment(section);

            // Store by university name (will map to ID later)
            results[universityName] = sentiment;
        });

        return results;
    };

    // Batch scan all visible universities
    const handleBatchScanNews = async (universities) => {
        if (scanningBatch || universities.length === 0) return;

        // Filter to only universities not yet scanned
        const unscanned = universities.filter(uni => !sentimentData[uni.id]);
        if (unscanned.length === 0) {
            console.log('[Batch Scan] All universities already scanned');
            return;
        }

        setScanningBatch(true);
        console.log(`[Batch Scan] Scanning ${unscanned.length} universities in one call`);

        try {
            const universityNames = unscanned.map(uni => uni.name).join(', ');
            const query = `BATCH NEWS SCAN: Analyze recent news (past 6 months) for the following universities: [${universityNames}]. For each university, identify major positive achievements or negative events and provide sentiment analysis.`;

            const response = await startSession(query);
            const fullResponse = extractFullResponse(response);
            const resultText = fullResponse.result || fullResponse;

            const batchResults = parseBatchSentiment(resultText);

            // Map results to university IDs
            const updatedSentiments = {};
            unscanned.forEach(uni => {
                const result = batchResults[uni.name];
                if (result) {
                    updatedSentiments[uni.id] = result;
                }
            });

            setSentimentData(prev => ({
                ...prev,
                ...updatedSentiments
            }));
        } catch (err) {
            console.error('Batch news scan failed:', err);
        } finally {
            setScanningBatch(false);
        }
    };

    // Auto-scan visible universities on page change
    // DISABLED: This was making too many API calls. Users can manually scan with button.
    useEffect(() => {
        // Feature disabled - return early
        return;

        /* Original code - kept for reference
        if (scanningBatch || paginatedUniversities.length === 0) {
            console.log('[Auto-Scan] Skipped:', { scanningBatch, universitiesCount: paginatedUniversities.length });
            return;
        }

        console.log(`[Auto-Scan] Triggered for page ${currentPage + 1} with ${paginatedUniversities.length} universities`);

        // Delay auto-scan slightly to avoid initial load conflicts
        const timer = setTimeout(() => {
            handleBatchScanNews(paginatedUniversities);
        }, 1000);

        return () => clearTimeout(timer);
        */
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentPage, scanningBatch, sentimentData]);

    // Handlers
    const handleSelectUni = (uni) => {
        setSelectedUni(uni);
        setActiveView('detail');
        window.scrollTo(0, 0);
    };

    const handleBack = () => {
        setSelectedUni(null);
        setActiveView("list");
    };

    const handleCompareToggle = (uni) => {
        setComparisonList(prev => {
            const isSelected = prev.find(u => u.id === uni.id);
            if (isSelected) {
                return prev.filter(u => u.id !== uni.id);
            } else {
                if (prev.length >= 3) {
                    return prev;
                }
                return [...prev, uni];
            }
        });
    };

    const handleRefresh = async () => {
        setLoading(true);
        try {
            const searchResponse = await fetch(KNOWLEDGE_BASE_UNIVERSITIES_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: "university",
                    limit: 1000,
                    search_type: "keyword"
                })
            });

            const searchData = await searchResponse.json();

            if (searchData.success && searchData.results) {
                const transformedData = searchData.results.map(transformUniversityData);
                setUniversities(transformedData);
                setError(null);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">

            {/* Full-Page University Profile View */}
            {activeView === 'detail' && selectedUni && (
                <UniversityProfilePage
                    university={selectedUni}
                    fitAnalysis={getCollegeFitAnalysis(selectedUni.id)}
                    onBack={handleBack}
                />
            )}

            {/* Main List/Favorites View */}
            {activeView !== 'detail' && (
                <>
                    {/* Hero Header - Like Profile Page */}
                    <div className="bg-white rounded-2xl p-6 shadow-lg border border-[#E0DED8] mb-6">
                        <div className="flex items-start gap-5">
                            <div className="w-14 h-14 rounded-2xl bg-[#1A4D2E] flex items-center justify-center flex-shrink-0">
                                <BuildingLibraryIcon className="h-7 w-7 text-white" />
                            </div>
                            <div>
                                <h1 className="font-serif text-2xl font-bold text-[#2C2C2C]">
                                    Discover Universities
                                </h1>
                                <p className="text-[#4A4A4A] mt-1">
                                    Explore 150+ universities with AI-powered fit analysis. Find your perfect match based on your academic profile.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
                            <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
                            <span className="text-red-700">{error}</span>
                            <button
                                onClick={handleRefresh}
                                className="ml-auto text-red-600 hover:text-red-800 font-medium"
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {/* Loading State */}
                    {loading && <LoadingSkeleton />}

                    {/* Fit Computation Status Bar */}
                    {computingFitFor && (
                        <div className="bg-gradient-to-r from-[#D6E8D5] to-[#A8C5A6] border border-[#1A4D2E]/20 rounded-xl p-4 flex items-center gap-3 mb-4 animate-pulse">
                            <div className="h-5 w-5 border-2 border-[#1A4D2E] border-t-transparent rounded-full animate-spin" />
                            <span className="text-[#1A4D2E] font-medium">
                                Computing personalized fit analysis...
                            </span>
                            <span className="text-[#2D6B45] text-sm">
                                This may take a few seconds
                            </span>
                        </div>
                    )}

                    {/* Tab navigation removed - My Schools page now handles favorites */}

                    {/* Main Content */}
                    {!loading && !error && (
                        <>
                            {/* University List - always shown */}
                            <div className="space-y-6">
                                {/* Filters */}
                                <div className="bg-white rounded-2xl p-4 shadow-sm border border-[#E0DED8]">
                                    {/* Combined Search + Filters Row */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 items-end">
                                        {/* Search Bar */}
                                        <div className="lg:col-span-2 relative">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-1">Search</label>
                                            <div className="relative">
                                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                                    <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                                                </div>
                                                <input
                                                    type="text"
                                                    className="block w-full pl-10 pr-3 py-2 border border-[#E0DED8] rounded-lg bg-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#1A4D2E] focus:border-[#1A4D2E] text-sm"
                                                    placeholder="University name..."
                                                    value={searchTerm}
                                                    onChange={(e) => setSearchTerm(e.target.value)}
                                                />
                                            </div>
                                        </div>

                                        {/* Filter Controls */}
                                        <div className="space-y-1">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Type</label>
                                            <select
                                                value={selectedType}
                                                onChange={(e) => setSelectedType(e.target.value)}
                                                className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                                            >
                                                <option value="All">All Types</option>
                                                <option value="Public">Public</option>
                                                <option value="Private">Private</option>
                                            </select>
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Location</label>
                                            <select
                                                value={selectedState}
                                                onChange={(e) => setSelectedState(e.target.value)}
                                                className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                                            >
                                                <option value="All">All States</option>
                                                {uniqueStates.map(state => (
                                                    <option key={state} value={state}>{state}</option>
                                                ))}
                                            </select>
                                        </div>

                                        <div className="space-y-1">
                                            <div className="flex justify-between">
                                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                                                    Max Acceptance Rate
                                                </label>
                                                <span className="text-xs font-bold text-blue-600">{maxAcceptance}%</span>
                                            </div>
                                            <input
                                                type="range"
                                                min="0"
                                                max="100"
                                                value={maxAcceptance}
                                                onChange={(e) => setMaxAcceptance(Number(e.target.value))}
                                                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 mt-2"
                                            />
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Fit Category</label>
                                            <select
                                                value={selectedFitCategory}
                                                onChange={(e) => setSelectedFitCategory(e.target.value)}
                                                className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                                            >
                                                <option value="All">All Fit Categories</option>
                                                <option value="SAFETY">🛡️ Safety</option>
                                                <option value="TARGET">🎯 Target</option>
                                                <option value="REACH">🔼 Reach</option>
                                                <option value="SUPER_REACH">🚀 Super Reach</option>
                                            </select>
                                        </div>

                                        <div className="space-y-1">
                                            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sort By</label>
                                            <select
                                                value={sortBy}
                                                onChange={(e) => setSortBy(e.target.value)}
                                                className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                                            >
                                                <option value="usNews">US News Rank</option>
                                                <option value="acceptance">Acceptance Rate</option>
                                                <option value="tuition">Tuition (Low to High)</option>
                                                <option value="name">Name (A-Z)</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>

                                {/* Comparison Section */}
                                {comparisonList.length > 0 && (
                                    <ComparisonView
                                        universities={comparisonList}
                                        onRemove={handleCompareToggle}
                                    />
                                )}

                                {/* Grid Results with Carousel */}
                                <div className="relative">
                                    {/* Carousel Navigation */}
                                    {totalPages > 1 && (
                                        <div className="flex items-center justify-between mb-4">
                                            <p className="text-sm text-gray-600">
                                                Showing {currentPage * CARDS_PER_PAGE + 1}-{Math.min((currentPage + 1) * CARDS_PER_PAGE, sortedUniversities.length)} of {sortedUniversities.length} universities
                                            </p>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                                                    disabled={currentPage === 0}
                                                    className="p-2 rounded-full bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
                                                >
                                                    <ChevronLeftIcon className="h-5 w-5" />
                                                </button>
                                                <span className="text-sm font-medium text-gray-700 min-w-[80px] text-center">
                                                    Page {currentPage + 1} of {totalPages}
                                                </span>
                                                <button
                                                    onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                                                    disabled={currentPage >= totalPages - 1}
                                                    className="p-2 rounded-full bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
                                                >
                                                    <ChevronRightIcon className="h-5 w-5" />
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Cards Grid - One per row */}
                                    <div className="grid grid-cols-1 gap-6">
                                        {paginatedUniversities.length > 0 ? (
                                            paginatedUniversities.map((uni) => {
                                                // Free tier: limit reached when 3 colleges already added (and this uni not in list)
                                                const isInList = isInCollegeList(uni.id);
                                                const isLimitReached = !canAccessLaunchpad && !isInList && myCollegeList.length >= 3;
                                                return (
                                                    <UniversityCard
                                                        key={uni.id}
                                                        uni={{ ...uni, isLimitReached }}
                                                        onSelect={handleSelectUni}
                                                        onCompare={handleCompareToggle}
                                                        isSelectedForCompare={comparisonList.some(u => u.id === uni.id)}
                                                        sentiment={sentimentData[uni.id]}
                                                        onSentimentClick={(sent) => {
                                                            setSelectedSentiment(sent);
                                                            setShowSentimentModal(true);
                                                        }}
                                                        isInList={isInCollegeList(uni.id)}
                                                        onToggleList={handleToggleCollegeList}
                                                        fitAnalysis={getCollegeFitAnalysis(uni.id)}
                                                        onAnalyzeFit={handleAnalyzeFit}
                                                        isAnalyzing={analyzingFit === uni.id}
                                                        onShowFitDetails={(fit) => {
                                                            setSelectedFitData(fit);
                                                            setShowFitModal(true);
                                                        }}
                                                        onOpenChat={handleOpenChat}
                                                    />
                                                );
                                            })
                                        ) : (
                                            <div className="col-span-full py-12 text-center text-gray-500 bg-white rounded-xl border border-dashed border-gray-300">
                                                <FunnelIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                                                <p className="text-lg font-medium">No universities found matching your criteria.</p>
                                                <button
                                                    onClick={() => {
                                                        setSearchTerm("");
                                                        setSelectedType("All");
                                                        setSelectedState("All");
                                                        setMaxAcceptance(100);
                                                    }}
                                                    className="mt-4 text-blue-600 font-medium hover:underline"
                                                >
                                                    Clear all filters
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* Bottom Carousel Navigation */}
                                    {totalPages > 1 && paginatedUniversities.length > 0 && (
                                        <div className="flex justify-center mt-6">
                                            <div className="flex items-center gap-1">
                                                {Array.from({ length: totalPages }, (_, i) => (
                                                    <button
                                                        key={i}
                                                        onClick={() => setCurrentPage(i)}
                                                        className={`w-2.5 h-2.5 rounded-full transition-all ${i === currentPage
                                                            ? 'bg-blue-600 w-6'
                                                            : 'bg-gray-300 hover:bg-gray-400'
                                                            }`}
                                                    />
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {activeView === 'detail' && selectedUni && (
                                <UniversityDetailPage
                                    uni={selectedUni}
                                    onBack={handleBack}
                                    sentiment={sentimentData[selectedUni.id]}
                                    fitAnalysis={getCollegeFitAnalysis(selectedUni.id)}
                                />
                            )}
                        </>
                    )
                    }

                    {/* Sentiment Modal */}
                    {
                        showSentimentModal && selectedSentiment && (
                            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                                onClick={() => setShowSentimentModal(false)}>
                                <div className={`bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto border-t-4 ${selectedSentiment.sentiment === 'positive' ? 'border-green-500' : 'border-red-500'
                                    }`}
                                    onClick={(e) => e.stopPropagation()}>
                                    <div className={`p-6 ${selectedSentiment.sentiment === 'positive' ? 'bg-green-50' : 'bg-red-50'
                                        }`}>
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center gap-3">
                                                <span className="text-3xl">
                                                    {selectedSentiment.sentiment === 'positive' ? '📈' : '⚠️'}
                                                </span>
                                                <div>
                                                    <h3 className={`text-xl font-bold ${selectedSentiment.sentiment === 'positive' ? 'text-green-900' : 'text-red-900'
                                                        }`}>
                                                        {selectedSentiment.sentiment === 'positive' ? 'Positive News' : 'Important Alert'}
                                                    </h3>
                                                    <p className={`text-sm mt-1 ${selectedSentiment.sentiment === 'positive' ? 'text-green-700' : 'text-red-700'
                                                        }`}>
                                                        {selectedSentiment.headline}
                                                    </p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => setShowSentimentModal(false)}
                                                className="text-gray-400 hover:text-gray-600"
                                            >
                                                <XMarkIcon className="h-6 w-6" />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="p-6 prose prose-sm max-w-none">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {selectedSentiment.fullText}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </div>
                        )
                    }

                    {/* Fit Analysis Modal */}
                    {
                        showFitModal && selectedFitData && (
                            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                                onClick={() => setShowFitModal(false)}>
                                <div className={`bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto border-t-4 ${selectedFitData.fit_category === 'SAFETY' ? 'border-green-500' :
                                    selectedFitData.fit_category === 'TARGET' ? 'border-blue-500' :
                                        selectedFitData.fit_category === 'REACH' ? 'border-[#E8A090]' :
                                            'border-red-500'
                                    }`}
                                    onClick={(e) => e.stopPropagation()}>
                                    <div className={`p-6 ${selectedFitData.fit_category === 'SAFETY' ? 'bg-green-50' :
                                        selectedFitData.fit_category === 'TARGET' ? 'bg-blue-50' :
                                            selectedFitData.fit_category === 'REACH' ? 'bg-[#FCEEE8]' :
                                                'bg-red-50'
                                        }`}>
                                        <div className="flex items-start justify-between">
                                            <div className="flex items-center gap-3">
                                                <span className="text-3xl">
                                                    {selectedFitData.fit_category === 'SAFETY' ? '✅' :
                                                        selectedFitData.fit_category === 'TARGET' ? '🎯' :
                                                            selectedFitData.fit_category === 'REACH' ? '🔼' : '🚀'}
                                                </span>
                                                <div>
                                                    <h3 className={`text-xl font-bold ${selectedFitData.fit_category === 'SAFETY' ? 'text-green-900' :
                                                        selectedFitData.fit_category === 'TARGET' ? 'text-blue-900' :
                                                            selectedFitData.fit_category === 'REACH' ? 'text-[#C05838]' :
                                                                'text-red-900'
                                                        }`}>
                                                        {selectedFitData.university_name} - {(selectedFitData.fit_category || '').replace('_', ' ')}
                                                    </h3>
                                                    <p className="text-gray-600 text-sm mt-1">
                                                        {selectedFitData.match_percentage}% Match
                                                    </p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => setShowFitModal(false)}
                                                className="text-gray-400 hover:text-gray-600"
                                            >
                                                <XMarkIcon className="h-6 w-6" />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="p-6">
                                        {/* Factors Section */}
                                        <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                                            <SparklesIcon className="h-5 w-5 text-purple-500" />
                                            Fit Factors
                                        </h4>
                                        <div className="space-y-3 mb-6">
                                            {selectedFitData.factors?.map((factor, idx) => (
                                                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                                    <div className="flex items-center gap-2">
                                                        <span className={`text-lg font-bold ${factor.score >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                                            {factor.score >= 0 ? '+' : ''}{factor.score}
                                                        </span>
                                                        <span className="font-medium text-gray-700">{factor.name}</span>
                                                    </div>
                                                    <span className="text-sm text-gray-500 max-w-[200px] text-right">{factor.detail}</span>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Recommendations Section */}
                                        <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                                            <ArrowTrendingUpIcon className="h-5 w-5 text-blue-500" />
                                            Recommendations to Improve
                                        </h4>
                                        <div className="space-y-2">
                                            {selectedFitData.recommendations?.map((rec, idx) => (
                                                <div key={idx} className="flex flex-col gap-2 p-4 bg-blue-50 rounded-lg">
                                                    <div className="flex items-start gap-3">
                                                        <span className="text-blue-600 font-bold">{idx + 1}.</span>
                                                        <span className="text-gray-700">{typeof rec === 'object' ? rec.action : rec}</span>
                                                    </div>
                                                    {typeof rec === 'object' && rec.addresses_gap && (
                                                        <div className="ml-7 flex flex-wrap gap-2 text-xs">
                                                            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">Addresses: {rec.addresses_gap}</span>
                                                            {rec.timeline && <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] rounded-full">Timeline: {rec.timeline}</span>}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>

                                        {/* Detailed Explanation Section */}
                                        {selectedFitData.explanation && (
                                            <>
                                                <h4 className="font-bold text-gray-800 mb-4 mt-6 flex items-center gap-2">
                                                    📋 Detailed Analysis
                                                </h4>
                                                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                                                    <ReactMarkdown
                                                        className="prose prose-sm max-w-none prose-blue text-gray-700"
                                                        remarkPlugins={[remarkGfm]}
                                                        components={{
                                                            p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                                                            strong: ({ node, ...props }) => <strong className="font-bold text-gray-900" {...props} />
                                                        }}
                                                    >
                                                        {selectedFitData.explanation}
                                                    </ReactMarkdown>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )
                    }
                </>
            )}

            {/* Credits Upgrade Modal */}
            <CreditsUpgradeModal
                isOpen={showCreditsModal}
                onClose={closeCreditsModal}
                creditsRemaining={creditsRemaining}
                feature={creditsModalFeature}
            />

            {/* Analysis Progress Modal */}
            {analysisModal.isOpen && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 text-center">
                        {/* Icon */}
                        <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-6 ${analysisModal.step === 'complete'
                            ? 'bg-green-100'
                            : analysisModal.step === 'error'
                                ? 'bg-red-100'
                                : 'bg-[#D6E8D5]'
                            }`}>
                            {analysisModal.step === 'complete' ? (
                                <CheckCircleIcon className="w-10 h-10 text-green-600" />
                            ) : analysisModal.step === 'error' ? (
                                <ExclamationTriangleIcon className="w-10 h-10 text-red-600" />
                            ) : (
                                <SparklesIcon className="w-10 h-10 text-[#1A4D2E] animate-pulse" />
                            )}
                        </div>

                        {/* Title */}
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            {analysisModal.step === 'complete'
                                ? 'Analysis Complete!'
                                : analysisModal.step === 'error'
                                    ? 'Analysis Failed'
                                    : 'Analyzing Your Fit'
                            }
                        </h3>

                        {/* University Name */}
                        <p className="text-gray-600 mb-6">{analysisModal.universityName}</p>

                        {/* Progress Steps */}
                        {analysisModal.step !== 'complete' && analysisModal.step !== 'error' && (
                            <div className="mb-6">
                                <div className="flex justify-between text-sm text-gray-500 mb-2">
                                    <span className={analysisModal.step === 'fit' ? 'text-[#1A4D2E] font-medium' : 'text-gray-400'}>
                                        {analysisModal.step === 'fit' ? '⏳' : '✓'} Computing Fit
                                    </span>
                                    <span className={analysisModal.step === 'refreshing' ? 'text-[#1A4D2E] font-medium' : 'text-gray-400'}>
                                        {analysisModal.progress >= 75 ? '✓' : analysisModal.step === 'refreshing' ? '⏳' : '○'} Refreshing
                                    </span>
                                    <span className={analysisModal.step === 'saving' || analysisModal.progress >= 90 ? 'text-[#1A4D2E] font-medium' : 'text-gray-400'}>
                                        {analysisModal.progress >= 95 ? '✓' : analysisModal.progress >= 90 ? '⏳' : '○'} Saving
                                    </span>
                                </div>

                                {/* Progress Bar */}
                                <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] transition-all duration-500"
                                        style={{ width: `${analysisModal.progress}%` }}
                                    />
                                </div>
                            </div>
                        )}

                        {/* Success Message */}
                        {analysisModal.step === 'complete' && (
                            <p className="text-green-600 font-medium">
                                ✓ Added to your Launchpad with personalized fit analysis
                            </p>
                        )}

                        {/* Error Message */}
                        {analysisModal.step === 'error' && (
                            <p className="text-red-600 font-medium">
                                Something went wrong. Please try again.
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* University Chat Widget */}
            <UniversityChatWidget
                universityId={chatUniversity?.id}
                universityName={chatUniversity?.name}
                isOpen={isChatOpen}
                onClose={handleCloseChat}
            />
        </div>
    );
};

export default UniversityExplorer;
