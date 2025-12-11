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
    StarIcon
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { startSession, sendMessage, extractFullResponse, getCollegeList, updateCollegeList } from '../services/api';
import { useAuth } from '../context/AuthContext';

// API Configuration
const KNOWLEDGE_BASE_UNIVERSITIES_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL ||
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

// --- Badge Component ---
const Badge = ({ children, color }) => {
    const colorClasses = {
        blue: "bg-blue-100 text-blue-800",
        green: "bg-green-100 text-green-800",
        purple: "bg-purple-100 text-purple-800",
        orange: "bg-orange-100 text-orange-800",
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

    // Extract rankings
    let usNewsRank = 'N/A';
    let forbesRank = 'N/A';

    if (Array.isArray(strategic.rankings)) {
        const usNewsObj = strategic.rankings.find(r => r.source === "US News");
        if (usNewsObj) usNewsRank = usNewsObj.rank_overall || 'N/A';

        const forbesObj = strategic.rankings.find(r => r.source === "Forbes");
        if (forbesObj) forbesRank = forbesObj.rank_overall || 'N/A';
    }

    return {
        id: apiData.university_id || profile._id,
        name: apiData.official_name || metadata.official_name || 'Unknown',
        shortName: metadata.official_name?.split(' ').slice(0, 3).join(' ') || apiData.official_name,
        location: apiData.location || metadata.location || { city: 'N/A', state: 'N/A', type: 'N/A' },
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
        summary: strategic.executive_summary || 'No summary available.',
        majors: majors.length > 0 ? majors : ['Information not available'],
        marketPosition: apiData.market_position || strategic.market_position || 'N/A',
        // Keep full profile for detail view
        fullProfile: profile
    };
};

// --- University Card Component ---
const UniversityCard = ({ uni, onSelect, onCompare, isSelectedForCompare, sentiment, onSentimentClick, isInList, onToggleList, fitAnalysis, onAnalyzeFit, isAnalyzing, onShowFitDetails }) => {
    const formatNumber = (num) => {
        if (num === 'N/A' || num === null || num === undefined) return 'N/A';
        return typeof num === 'number' ? num.toLocaleString() : num;
    };

    // Fit category colors
    const fitColors = {
        SAFETY: 'bg-green-100 text-green-800 border-green-300',
        TARGET: 'bg-blue-100 text-blue-800 border-blue-300',
        REACH: 'bg-orange-100 text-orange-800 border-orange-300',
        SUPER_REACH: 'bg-red-100 text-red-800 border-red-300'
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg transition-all duration-300 flex flex-col h-full">
            <div className="p-6 flex-grow">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3
                            onClick={() => onSelect(uni)}
                            className="text-lg font-bold text-gray-900 cursor-pointer hover:text-blue-600 line-clamp-2"
                            title={uni.name}
                        >
                            {uni.name}
                        </h3>
                        <div className="flex items-center text-gray-500 text-sm mt-1">
                            <MapPinIcon className="h-4 w-4 mr-1" />
                            {uni.location.city}, {uni.location.state}
                        </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        <Badge color={uni.location.type === "Private" ? "purple" : "blue"}>{uni.location.type}</Badge>
                        {/* Consistent fit status area - always shows something if in list */}
                        {isInList && (
                            fitAnalysis ? (
                                <button
                                    onClick={(e) => { e.stopPropagation(); onShowFitDetails(fitAnalysis); }}
                                    className={`px-2 py-1 rounded-full text-xs font-bold border cursor-pointer hover:opacity-80 transition-opacity whitespace-nowrap ${fitColors[fitAnalysis.fit_category] || fitColors.TARGET}`}
                                    title={`${fitAnalysis.match_percentage}% match - Click for details`}
                                >
                                    {fitAnalysis.fit_category === 'SUPER_REACH' ? '🎯 Super Reach' :
                                        fitAnalysis.fit_category === 'REACH' ? '🎯 Reach' :
                                            fitAnalysis.fit_category === 'TARGET' ? '🎯 Target' :
                                                '✅ Safety'}
                                </button>
                            ) : isAnalyzing ? (
                                <span className="px-2 py-1 rounded-full text-xs font-bold bg-purple-100 text-purple-600 border border-purple-200 animate-pulse whitespace-nowrap">
                                    ⏳ Analyzing...
                                </span>
                            ) : (
                                <span className="px-2 py-1 rounded-full text-xs font-medium text-green-600 bg-green-50 border border-green-200 whitespace-nowrap">
                                    ✓ In List
                                </span>
                            )
                        )}
                    </div>
                </div>

                <p className="text-gray-600 text-sm mb-4 line-clamp-3">{uni.summary}</p>

                <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-gray-50 p-2 rounded">
                        <div className="text-gray-500 text-xs">Acceptance</div>
                        <div className="font-semibold text-gray-900">
                            {uni.admissions.acceptanceRate !== 'N/A' ? `${uni.admissions.acceptanceRate}%` : 'N/A'}
                        </div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                        <div className="text-gray-500 text-xs">Tuition (In-State)</div>
                        <div className="font-semibold text-gray-900">
                            {uni.financials.inStateTuition !== 'N/A' ? `$${formatNumber(uni.financials.inStateTuition)}` : 'N/A'}
                        </div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                        <div className="text-gray-500 text-xs">US News Rank</div>
                        <div className="font-semibold text-gray-900">
                            {uni.rankings.usNews !== 'N/A' ? `#${uni.rankings.usNews}` : 'N/A'}
                        </div>
                    </div>
                    <div className="bg-gray-50 p-2 rounded">
                        <div className="text-gray-500 text-xs">Median Earnings</div>
                        <div className="font-semibold text-gray-900">
                            {uni.outcomes.medianEarnings !== 'N/A' ? `$${formatNumber(uni.outcomes.medianEarnings)}` : 'N/A'}
                        </div>
                    </div>
                </div>
            </div>

            <div className="p-4 border-t border-gray-100">
                <div className="flex gap-3">
                    <button
                        onClick={() => onSelect(uni)}
                        className="flex-1 bg-white border border-gray-300 text-gray-700 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 flex items-center justify-center gap-2"
                    >
                        Details <ChevronRightIcon className="h-4 w-4" />
                    </button>
                    <button
                        onClick={() => onCompare(uni)}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors ${isSelectedForCompare
                            ? 'bg-blue-600 text-white hover:bg-blue-700'
                            : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                            }`}
                    >
                        {isSelectedForCompare ? 'Added' : 'Compare'}
                        {isSelectedForCompare ? <XMarkIcon className="h-4 w-4" /> : <ScaleIcon className="h-4 w-4" />}
                    </button>
                    <button
                        onClick={(e) => { e.stopPropagation(); onToggleList(uni); }}
                        className={`p-2 rounded-lg transition-all hover:scale-105 ${isInList
                            ? 'bg-green-100 text-green-700 hover:bg-red-100 hover:text-red-600'
                            : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                            }`}
                        title={isInList ? 'Remove from Launchpad' : '🚀 Add to My Launchpad'}
                    >
                        {isInList ? '✓' : '🚀'}
                    </button>
                    {/* Fit analysis is now shown in the header area */}
                    {sentiment && sentiment.sentiment !== 'neutral' && (
                        <button
                            onClick={(e) => { e.stopPropagation(); onSentimentClick(sentiment); }}
                            className={`p-2 rounded-lg transition-all hover:scale-110 ${sentiment.sentiment === 'positive'
                                ? 'bg-green-100 text-green-700 hover:bg-green-200'
                                : 'bg-red-100 text-red-700 hover:bg-red-200'
                                }`}
                            title={sentiment.headline}
                        >
                            {sentiment.sentiment === 'positive' ? '📈' : '⚠️'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- Favorite Card Component (for college list items) ---
const FavoriteCard = ({ college, onRemove, onViewDetails, fitAnalysis }) => {
    const fitColors = {
        SAFETY: 'bg-green-100 text-green-800 border-green-300',
        TARGET: 'bg-blue-100 text-blue-800 border-blue-300',
        REACH: 'bg-orange-100 text-orange-800 border-orange-300',
        SUPER_REACH: 'bg-red-100 text-red-800 border-red-300'
    };

    const fit = fitAnalysis || college.fit_analysis || {};
    const fitCategory = fit.fit_category || 'TARGET';
    const matchPercentage = fit.match_percentage;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg transition-all duration-300 flex flex-col h-full">
            <div className="p-5 flex-grow">
                <div className="flex justify-between items-start mb-3">
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-bold text-gray-900 line-clamp-2">
                            {college.university_name}
                        </h3>
                        <div className="flex items-center text-gray-500 text-sm mt-1">
                            <MapPinIcon className="h-4 w-4 mr-1" />
                            {college.location || 'Location N/A'}
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

                {/* Fit Analysis Info */}
                {fit.factors && fit.factors.length > 0 && (
                    <div className="text-xs text-gray-600 bg-gray-50 rounded p-2 mt-2">
                        <span className="font-medium text-gray-700">Key Factors: </span>
                        {fit.factors.slice(0, 3).map(f => f.name || f).join(' • ')}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-100">
                <div className="flex gap-2">
                    <button
                        onClick={() => onViewDetails && onViewDetails(college)}
                        className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center justify-center gap-1"
                    >
                        View Details
                        <ChevronRightIcon className="h-4 w-4" />
                    </button>
                    <button
                        onClick={() => onRemove(college)}
                        className="px-4 py-2.5 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors flex items-center gap-1"
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
const UniversityDetail = ({ uni, onBack, sentiment, deepResearchData, setDeepResearchData }) => {
    if (!uni) return null;

    const formatNumber = (num) => {
        if (num === 'N/A' || num === null || num === undefined) return 'N/A';
        return typeof num === 'number' ? num.toLocaleString() : num;
    };

    return (
        <div className="bg-white rounded-xl shadow-xl border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 p-8 text-white relative">
                <button
                    onClick={onBack}
                    className="absolute top-6 left-6 p-2 bg-white/20 hover:bg-white/30 rounded-full backdrop-blur-sm transition-colors"
                >
                    <ArrowLeftIcon className="h-5 w-5" />
                </button>
                <div className="mt-8">
                    <div className="flex flex-wrap gap-2 mb-3">
                        <Badge color="white">{uni.location.type}</Badge>
                        <span className="bg-blue-800/50 px-2 py-1 rounded-full text-xs flex items-center gap-1">
                            <MapPinIcon className="h-3 w-3" /> {uni.location.city}, {uni.location.state}
                        </span>
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold mb-2">{uni.name}</h1>
                    <p className="text-blue-100 text-lg max-w-3xl">{uni.summary}</p>
                </div>
            </div>

            {/* Sentiment Banner */}
            {sentiment && sentiment.sentiment !== 'neutral' && (
                <div className={`p-6 ${sentiment.sentiment === 'positive'
                    ? 'bg-green-50 border-b-4 border-green-500'
                    : 'bg-red-50 border-b-4 border-red-500'
                    }`}>
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-2xl">{sentiment.sentiment === 'positive' ? '📈' : '⚠️'}</span>
                        <h3 className={`text-lg font-bold ${sentiment.sentiment === 'positive' ? 'text-green-900' : 'text-red-900'
                            }`}>
                            {sentiment.sentiment === 'positive' ? 'Recent Positive News' : 'Recent Alert'}
                        </h3>
                    </div>
                    <p className={`text-sm mb-4 ${sentiment.sentiment === 'positive' ? 'text-green-800' : 'text-red-800'
                        }`}>
                        {sentiment.headline}
                    </p>
                    <details className="text-sm">
                        <summary className={`cursor-pointer font-medium ${sentiment.sentiment === 'positive' ? 'text-green-700 hover:text-green-900' : 'text-red-700 hover:text-red-900'
                            }`}>
                            ▸ View Full Details
                        </summary>
                        <div className={`mt-4 p-4 rounded-lg prose prose-sm max-w-none ${sentiment.sentiment === 'positive' ? 'bg-white text-gray-700' : 'bg-white text-gray-700'
                            }`}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {sentiment.fullText}
                            </ReactMarkdown>
                        </div>
                    </details>
                </div>
            )}

            <div className="p-6 md:p-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {/* Main Info Column */}
                    <div className="md:col-span-2 space-y-8">

                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                                <div className="text-blue-600 mb-1"><TrophyIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">
                                    {uni.rankings.usNews !== 'N/A' ? `#${uni.rankings.usNews}` : 'N/A'}
                                </div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">US News Rank</div>
                            </div>
                            <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                                <div className="text-green-600 mb-1"><UsersIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">
                                    {uni.admissions.acceptanceRate !== 'N/A' ? `${uni.admissions.acceptanceRate}%` : 'N/A'}
                                </div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Acceptance</div>
                            </div>
                            <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
                                <div className="text-purple-600 mb-1"><BookOpenIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">{uni.admissions.gpa}</div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Avg GPA</div>
                            </div>
                            <div className="p-4 bg-orange-50 rounded-xl border border-orange-100">
                                <div className="text-orange-600 mb-1"><ArrowTrendingUpIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">
                                    {uni.outcomes.medianEarnings !== 'N/A'
                                        ? `$${Math.round(uni.outcomes.medianEarnings / 1000)}k`
                                        : 'N/A'}
                                </div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Median Pay</div>
                            </div>
                        </div>

                        {/* Admissions Section */}
                        <section>
                            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                                <AcademicCapIcon className="h-5 w-5 text-blue-600" /> Admissions Profile
                            </h2>
                            <div className="bg-gray-50 rounded-xl p-6 border border-gray-100">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-700 mb-2">Test Policy</h3>
                                        <p className="text-gray-600">{uni.admissions.testPolicy}</p>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-700 mb-2">Selectivity</h3>
                                        {uni.admissions.acceptanceRate !== 'N/A' && (
                                            <>
                                                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-1">
                                                    <div
                                                        className="bg-blue-600 h-2.5 rounded-full"
                                                        style={{ width: `${100 - uni.admissions.acceptanceRate}%` }}
                                                    ></div>
                                                </div>
                                                <p className="text-xs text-gray-500">
                                                    {uni.admissions.acceptanceRate < 15
                                                        ? "Extremely Selective"
                                                        : uni.admissions.acceptanceRate < 30
                                                            ? "Very Selective"
                                                            : "Selective"}
                                                </p>
                                            </>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Popular Majors */}
                        <section>
                            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                                <BuildingLibraryIcon className="h-5 w-5 text-blue-600" /> Popular Majors
                            </h2>
                            <div className="flex flex-wrap gap-2">
                                {uni.majors.map((major, idx) => {
                                    const colors = [
                                        'bg-blue-100 text-blue-800 border-blue-300',
                                        'bg-green-100 text-green-800 border-green-300',
                                        'bg-purple-100 text-purple-800 border-purple-300',
                                        'bg-amber-100 text-amber-800 border-amber-300',
                                        'bg-pink-100 text-pink-800 border-pink-300',
                                        'bg-indigo-100 text-indigo-800 border-indigo-300'
                                    ];
                                    const colorClass = colors[idx % colors.length];
                                    return (
                                        <span
                                            key={idx}
                                            className={`border px-4 py-2 rounded-lg shadow-sm hover:shadow transition-all font-medium ${colorClass}`}
                                        >
                                            {major}
                                        </span>
                                    );
                                })}
                            </div>
                        </section>
                    </div>

                    {/* Sidebar */}
                    <div className="space-y-6">

                        {/* Financials Widget */}
                        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                                <CurrencyDollarIcon className="h-5 w-5 text-green-600" /> Costs & Aid
                            </h2>
                            <div className="space-y-4">
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-600">In-State Tuition</span>
                                        <span className="font-semibold">
                                            {uni.financials.inStateTuition !== 'N/A' ? `$${formatNumber(uni.financials.inStateTuition)}` : 'N/A'}
                                        </span>
                                    </div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-gray-600">Out-of-State</span>
                                        <span className="font-semibold">
                                            {uni.financials.outStateTuition !== 'N/A' ? `$${formatNumber(uni.financials.outStateTuition)}` : 'N/A'}
                                        </span>
                                    </div>
                                    <div className="pt-3 mt-3 border-t border-gray-100 space-y-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">COA (In-State)</span>
                                            <span className="font-semibold text-blue-700">
                                                {uni.financials.inStateCOA !== 'N/A' ? `$${formatNumber(uni.financials.inStateCOA)}` : 'N/A'}
                                            </span>
                                        </div>
                                        <div className="flex justify-between text-sm">
                                            <span className="text-gray-600">COA (Out-of-State)</span>
                                            <span className="font-semibold text-blue-700">
                                                {uni.financials.outStateCOA !== 'N/A' ? `$${formatNumber(uni.financials.outStateCOA)}` : 'N/A'}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Outcomes Widget */}
                        <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl shadow-sm p-6 text-white">
                            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                                <BriefcaseIcon className="h-5 w-5 text-blue-400" /> Career Outcomes
                            </h2>
                            <div className="mb-6">
                                <div className="text-3xl font-bold text-green-400 mb-1">
                                    {uni.outcomes.medianEarnings !== 'N/A'
                                        ? `$${formatNumber(uni.outcomes.medianEarnings)}`
                                        : 'N/A'}
                                </div>
                                <div className="text-sm text-gray-400">Median 10yr Earnings</div>
                            </div>
                            {uni.outcomes.topEmployers && uni.outcomes.topEmployers.length > 0 && (
                                <div>
                                    <h3 className="text-xs font-semibold uppercase text-gray-500 mb-3 tracking-wider">Top Employers</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {uni.outcomes.topEmployers.slice(0, 5).map((emp, i) => (
                                            <span key={i} className="bg-gray-700/50 text-gray-200 text-xs px-2 py-1 rounded">
                                                {emp}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                    </div>
                </div>

                {/* Deep Dive Research Section */}
                <DeepDiveSection
                    universityId={uni.id}
                    universityName={uni.name}
                    cachedResearch={deepResearchData[uni.id]}
                    onResearchUpdate={(id, result) => {
                        setDeepResearchData(prev => ({
                            ...prev,
                            [id]: result
                        }));
                    }}
                />

            </div>
        </div>
    );
};

// --- Deep Dive Research Component ---
const DeepDiveSection = ({ universityId, universityName, cachedResearch, onResearchUpdate }) => {
    const [isResearching, setIsResearching] = useState(false);
    const [error, setError] = useState(null);

    const handleDeepDive = async () => {
        setIsResearching(true);
        setError(null);

        try {
            // Craft a deep research query
            const query = `Deep research on ${universityName}: Tell me about recent news, notable research labs and professors, campus culture and student life, specific program strengths, and any unique opportunities or hidden gems that prospective students should know about. IMPORTANT: Provide all source URLs from your search results at the end.`;

            // Start session and send the message in one call
            const response = await startSession(query);

            // Extract the full response
            const fullResponse = extractFullResponse(response);
            const resultText = fullResponse.result || fullResponse;

            // Cache the result
            onResearchUpdate(universityId, resultText);
        } catch (err) {
            console.error('Deep research failed:', err);
            setError('Failed to complete research. Please try again.');
        } finally {
            setIsResearching(false);
        }
    };

    return (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-6 border border-purple-200">
            <div className="flex items-start justify-between mb-4">
                <div>
                    <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-purple-600" />
                        Deep Dive Research
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                        Get detailed insights beyond the basic stats
                    </p>
                </div>
            </div>

            {!cachedResearch && (
                <button
                    onClick={handleDeepDive}
                    disabled={isResearching}
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 rounded-lg font-medium hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                >
                    {isResearching ? (
                        <>
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                            Researching...
                        </>
                    ) : (
                        <>
                            <MagnifyingGlassIcon className="h-5 w-5" />
                            Research This University
                        </>
                    )}
                </button>
            )}

            {error && (
                <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
                    {error}
                </div>
            )}

            {cachedResearch && (
                <div className="prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {cachedResearch}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    );
};

// --- Loading Skeleton ---
const LoadingSkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
                <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                        <div className="h-5 bg-gray-200 rounded w-3/4 mb-2"></div>
                        <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                    </div>
                    <div className="h-6 bg-gray-200 rounded-full w-16"></div>
                </div>
                <div className="h-16 bg-gray-200 rounded mb-4"></div>
                <div className="grid grid-cols-2 gap-3">
                    <div className="h-12 bg-gray-200 rounded"></div>
                    <div className="h-12 bg-gray-200 rounded"></div>
                    <div className="h-12 bg-gray-200 rounded"></div>
                    <div className="h-12 bg-gray-200 rounded"></div>
                </div>
            </div>
        ))}
    </div>
);

// --- Main App Component ---
const UniversityExplorer = () => {
    const [universities, setUniversities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [searchTerm, setSearchTerm] = useState("");
    const [selectedType, setSelectedType] = useState("All");
    const [selectedState, setSelectedState] = useState("All");
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

    // Load college list on mount
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

        loadCollegeList();
    }, [currentUser]);

    // Toggle college in list (add/remove)
    const handleToggleCollegeList = async (university) => {
        if (!currentUser?.email) {
            console.warn('[College List] No user logged in');
            return;
        }

        const isInList = myCollegeList.some(c => c.university_id === university.id);
        const action = isInList ? 'remove' : 'add';

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

                // Auto-trigger fit analysis when adding a university
                if (action === 'add') {
                    console.log(`[College List] Auto-triggering fit analysis for: ${university.name}`);
                    // Use setTimeout to allow state to update first
                    setTimeout(() => {
                        handleAnalyzeFit(university);
                    }, 100);
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

    // Get fit analysis for a university from college list
    const getCollegeFitAnalysis = (universityId) => {
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
            // Convert university name to ID format (snake_case)
            const universityId = university.id || university.name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');

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
                            limit: 100,
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

            return matchesSearch && matchesType && matchesState && matchesAcceptance;
        });
    }, [universities, searchTerm, selectedType, selectedState, maxAcceptance]);

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

    // Paginated universities
    const paginatedUniversities = useMemo(() => {
        const start = currentPage * CARDS_PER_PAGE;
        return sortedUniversities.slice(start, start + CARDS_PER_PAGE);
    }, [sortedUniversities, currentPage]);

    const totalPages = Math.ceil(sortedUniversities.length / CARDS_PER_PAGE);

    // Reset page when filters change
    useEffect(() => {
        setCurrentPage(0);
    }, [searchTerm, selectedType, selectedState, maxAcceptance, sortBy]);

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
    useEffect(() => {
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
                    limit: 100,
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
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <BuildingLibraryIcon className="h-7 w-7 text-blue-600" />
                        UniInsight
                    </h1>
                    <p className="text-gray-500 mt-1">
                        Explore and compare top universities
                    </p>
                </div>
                <button
                    onClick={handleRefresh}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                    <ArrowPathIcon className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Refresh
                </button>
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

            {/* Tab Navigation */}
            {!loading && !error && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-1 flex gap-2">
                    <button
                        onClick={() => setActiveView('list')}
                        className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${activeView === 'list'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-gray-600 hover:bg-gray-100'
                            }`}
                    >
                        <BuildingLibraryIcon className="h-5 w-5" />
                        Browse All
                    </button>
                    <button
                        onClick={() => setActiveView('favorites')}
                        className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${activeView === 'favorites'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'text-gray-600 hover:bg-gray-100'
                            }`}
                    >
                        {activeView === 'favorites' ? (
                            <StarIconSolid className="h-5 w-5" />
                        ) : (
                            <StarIcon className="h-5 w-5" />
                        )}
                        My Favorites
                        {myCollegeList.length > 0 && (
                            <span className={`ml-1 px-2 py-0.5 rounded-full text-xs font-semibold ${activeView === 'favorites'
                                ? 'bg-white/20 text-white'
                                : 'bg-blue-100 text-blue-700'
                                }`}>
                                {myCollegeList.length}
                            </span>
                        )}
                    </button>
                </div>
            )}

            {/* Main Content */}
            {!loading && !error && (
                <>
                    {activeView === 'list' && (
                        <div className="space-y-6">
                            {/* Filters */}
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                                <div className="flex flex-col md:flex-row gap-4 justify-between items-start md:items-center mb-6">
                                    <div>
                                        <h2 className="text-lg font-semibold text-gray-900">Find Your Perfect University</h2>
                                        <p className="text-gray-500 text-sm">Compare admission stats, costs, and outcomes</p>
                                    </div>

                                    {/* Search Bar */}
                                    <div className="relative w-full md:w-80">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                                        </div>
                                        <input
                                            type="text"
                                            className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg bg-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
                                            placeholder="Search by name..."
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                        />
                                    </div>
                                </div>

                                {/* Filter Controls */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
                                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                        />
                                    </div>

                                    <div className="space-y-1">
                                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide flex items-center gap-1">
                                            <ArrowsUpDownIcon className="h-3 w-3" /> Sort By
                                        </label>
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

                                {/* Cards Grid */}
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {paginatedUniversities.length > 0 ? (
                                        paginatedUniversities.map(uni => (
                                            <UniversityCard
                                                key={uni.id}
                                                uni={uni}
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
                                            />
                                        ))
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
                    )}

                    {activeView === 'favorites' && (
                        <div className="space-y-6">
                            {/* Favorites Header */}
                            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                                            <StarIconSolid className="h-6 w-6 text-yellow-500" />
                                            My Favorites
                                        </h2>
                                        <p className="text-gray-500 text-sm mt-1">
                                            {myCollegeList.length === 0
                                                ? "You haven't added any universities yet"
                                                : `${myCollegeList.length} ${myCollegeList.length === 1 ? 'university' : 'universities'} saved`}
                                        </p>
                                    </div>
                                    {myCollegeList.length > 0 && (
                                        <button
                                            onClick={() => setActiveView('list')}
                                            className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100 flex items-center gap-2"
                                        >
                                            <BuildingLibraryIcon className="h-4 w-4" />
                                            Browse More
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Empty State */}
                            {myCollegeList.length === 0 && (
                                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-12 text-center border border-blue-100">
                                    <div className="max-w-md mx-auto">
                                        <StarIcon className="h-16 w-16 text-blue-300 mx-auto mb-4" />
                                        <h3 className="text-xl font-semibold text-gray-900 mb-2">
                                            Your favorites list is empty
                                        </h3>
                                        <p className="text-gray-600 mb-6">
                                            Browse universities and click the <span className="inline-flex items-center justify-center w-6 h-6 rounded bg-gray-200 text-gray-700 font-bold text-sm mx-1">+</span> button to add them to your favorites.
                                        </p>
                                        <button
                                            onClick={() => setActiveView('list')}
                                            className="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
                                        >
                                            <BuildingLibraryIcon className="h-5 w-5" />
                                            Browse Universities
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Favorites Grid */}
                            {myCollegeList.length > 0 && (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {myCollegeList.map((college) => (
                                        <FavoriteCard
                                            key={college.university_id}
                                            college={college}
                                            onRemove={(c) => handleToggleCollegeList({
                                                id: c.university_id,
                                                name: c.university_name
                                            })}
                                            onViewDetails={(c) => {
                                                // Try to find the full university data, or create minimal version
                                                const fullUni = universities.find(u => u.id === c.university_id) || {
                                                    id: c.university_id,
                                                    name: c.university_name,
                                                    location: { city: 'N/A', state: 'N/A', type: 'N/A' },
                                                    summary: 'Loading full details...',
                                                    rankings: { usNews: 'N/A' },
                                                    admissions: { acceptanceRate: 'N/A' },
                                                    financials: {},
                                                    outcomes: {},
                                                    majors: []
                                                };
                                                setSelectedUni(fullUni);
                                                setActiveView('detail');
                                            }}
                                            fitAnalysis={college.fit_analysis}
                                        />
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {activeView === 'detail' && selectedUni && (
                        <UniversityDetail
                            uni={selectedUni}
                            onBack={handleBack}
                            sentiment={sentimentData[selectedUni.id]}
                            deepResearchData={deepResearchData}
                            setDeepResearchData={setDeepResearchData}
                        />
                    )}
                </>
            )}

            {/* Sentiment Modal */}
            {showSentimentModal && selectedSentiment && (
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
            )}

            {/* Fit Analysis Modal */}
            {showFitModal && selectedFitData && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                    onClick={() => setShowFitModal(false)}>
                    <div className={`bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto border-t-4 ${selectedFitData.fit_category === 'SAFETY' ? 'border-green-500' :
                        selectedFitData.fit_category === 'TARGET' ? 'border-blue-500' :
                            selectedFitData.fit_category === 'REACH' ? 'border-orange-500' :
                                'border-red-500'
                        }`}
                        onClick={(e) => e.stopPropagation()}>
                        <div className={`p-6 ${selectedFitData.fit_category === 'SAFETY' ? 'bg-green-50' :
                            selectedFitData.fit_category === 'TARGET' ? 'bg-blue-50' :
                                selectedFitData.fit_category === 'REACH' ? 'bg-orange-50' :
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
                                                selectedFitData.fit_category === 'REACH' ? 'text-orange-900' :
                                                    'text-red-900'
                                            }`}>
                                            {selectedFitData.university_name} - {selectedFitData.fit_category.replace('_', ' ')}
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
                                    <div key={idx} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                                        <span className="text-blue-600 font-bold">{idx + 1}.</span>
                                        <span className="text-gray-700">{rec}</span>
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
            )}
        </div>
    );
};

export default UniversityExplorer;
