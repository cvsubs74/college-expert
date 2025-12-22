import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { generateFitInfographic, checkCredits, deductCredit } from '../../services/api';
import {
    ArrowLeftIcon,
    AcademicCapIcon,
    BuildingLibraryIcon,
    CurrencyDollarIcon,
    HomeIcon,
    SparklesIcon,
    LightBulbIcon,
    MapPinIcon,
    TrophyIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    ArrowPathIcon,
    PhotoIcon,
    CalendarIcon,
    DocumentTextIcon,
    ChartBarIcon,
    FilmIcon
} from '@heroicons/react/24/outline';
import { StarIcon } from '@heroicons/react/24/solid';
import MediaGallery from '../MediaGallery';
import UniversityChatWidget from '../UniversityChatWidget';
import { ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

// ============================================================================
// HERO SECTION
// ============================================================================
const HeroSection = ({ university, fitAnalysis, onAskAI }) => {
    const fitColors = {
        SAFETY: { bg: 'bg-green-500', text: 'text-green-100', border: 'border-green-400' },
        TARGET: { bg: 'bg-blue-500', text: 'text-blue-100', border: 'border-blue-400' },
        REACH: { bg: 'bg-orange-500', text: 'text-orange-100', border: 'border-orange-400' },
        SUPER_REACH: { bg: 'bg-red-500', text: 'text-red-100', border: 'border-red-400' }
    };

    const fitColor = fitColors[fitAnalysis?.fit_category] || fitColors.TARGET;

    return (
        <div className={`${fitColor.bg} text-white p-8 rounded-t-2xl relative overflow-hidden`}>
            {/* Background pattern */}
            <div className="absolute inset-0 opacity-10">
                <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full -translate-y-1/2 translate-x-1/2"></div>
                <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y-1/2 -translate-x-1/2"></div>
            </div>

            <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                {/* Left side: University info */}
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                        <span className={`px-3 py-1 rounded-full text-sm font-bold ${fitColor.text} bg-white/20`}>
                            #{university?.rankings?.usNews || 'N/A'} US News
                        </span>
                        <span className="px-3 py-1 rounded-full text-sm font-medium bg-white/20">
                            {university?.location?.type}
                        </span>
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold mb-2">
                        {university?.name}
                    </h1>
                    <div className="flex items-center gap-2 text-white/80">
                        <MapPinIcon className="h-5 w-5" />
                        <span>{university?.location?.city}, {university?.location?.state}</span>
                    </div>
                    {university?.summary && (
                        <p className="mt-4 text-white/90 max-w-2xl line-clamp-2">
                            {university.summary}
                        </p>
                    )}
                </div>

                {/* Right side: Fit Score Ring */}
                {fitAnalysis && (
                    <div className="flex flex-col items-center">
                        <div className="relative w-32 h-32">
                            {/* Background ring */}
                            <svg className="w-full h-full transform -rotate-90">
                                <circle
                                    cx="64"
                                    cy="64"
                                    r="56"
                                    fill="none"
                                    stroke="rgba(255,255,255,0.2)"
                                    strokeWidth="12"
                                />
                                <circle
                                    cx="64"
                                    cy="64"
                                    r="56"
                                    fill="none"
                                    stroke="white"
                                    strokeWidth="12"
                                    strokeLinecap="round"
                                    strokeDasharray={`${(fitAnalysis.match_percentage / 100) * 352} 352`}
                                    className="transition-all duration-1000 ease-out"
                                />
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className="text-3xl font-bold">{fitAnalysis.match_percentage}%</span>
                                <span className="text-xs uppercase tracking-wide opacity-80">Match</span>
                            </div>
                        </div>
                        <span className="mt-2 px-4 py-1 bg-white/20 rounded-full text-sm font-bold">
                            {(fitAnalysis.fit_category || '').replace('_', ' ')}
                        </span>
                    </div>
                )}
            </div>
        </div>
    );
};

// ============================================================================
// ACTION CENTER (Above the fold - most prominent)
// ============================================================================
const ActionCenter = ({ fitAnalysis }) => {
    if (!fitAnalysis) return null;

    const recommendations = fitAnalysis.recommendations || [];
    const gapAnalysis = fitAnalysis.gap_analysis || {};

    return (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 p-6 border-b border-gray-200">
            <div className="flex items-center gap-2 mb-4">
                <LightBulbIcon className="h-6 w-6 text-purple-600" />
                <h2 className="text-xl font-bold text-gray-900">Your Action Plan</h2>
            </div>

            {/* Top 3 Recommendations */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {recommendations.slice(0, 3).map((rec, idx) => (
                    <div key={idx} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                        <div className="flex items-start gap-3">
                            <span className="flex-shrink-0 w-8 h-8 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center font-bold text-sm">
                                {idx + 1}
                            </span>
                            <div className="flex-1">
                                <p className="text-gray-800 font-medium text-sm leading-relaxed">
                                    {typeof rec === 'string' ? rec : rec.action}
                                </p>
                                {rec.timeline && (
                                    <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
                                        <CalendarIcon className="h-3 w-3" />
                                        {rec.timeline}
                                    </div>
                                )}
                                {rec.addresses_gap && (
                                    <span className="inline-block mt-2 px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">
                                        Addresses: {rec.addresses_gap}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Gap Analysis Summary */}
            {(gapAnalysis.primary_gap || gapAnalysis.student_strengths) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Gaps */}
                    <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                        <h3 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
                            <ExclamationTriangleIcon className="h-5 w-5" />
                            Areas to Address
                        </h3>
                        <ul className="space-y-1 text-sm text-red-700">
                            {gapAnalysis.primary_gap && <li>• <strong>Primary:</strong> {gapAnalysis.primary_gap}</li>}
                            {gapAnalysis.secondary_gap && <li>• <strong>Secondary:</strong> {gapAnalysis.secondary_gap}</li>}
                        </ul>
                    </div>
                    {/* Strengths */}
                    <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                        <h3 className="font-semibold text-green-800 mb-2 flex items-center gap-2">
                            <CheckCircleIcon className="h-5 w-5" />
                            Your Strengths
                        </h3>
                        <ul className="space-y-1 text-sm text-green-700">
                            {(gapAnalysis.student_strengths || []).slice(0, 3).map((s, i) => (
                                <li key={i}>• {s}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}
        </div>
    );
};

// ============================================================================
// TAB NAVIGATION
// ============================================================================
const TabNavigation = ({ activeTab, setActiveTab, tabs }) => {
    return (
        <div className="bg-white border-b border-gray-200 sticky top-0 z-20">
            <nav className="flex overflow-x-auto px-6" aria-label="Tabs">
                {tabs.map((tab) => {
                    const isFitTab = tab.id === 'fit';
                    const isActive = activeTab === tab.id;

                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`group inline-flex items-center gap-2 py-4 px-6 border-b-2 font-medium text-sm whitespace-nowrap transition-all ${isActive
                                ? isFitTab
                                    ? 'border-purple-500 text-purple-600 bg-purple-50'
                                    : 'border-blue-500 text-blue-600'
                                : isFitTab
                                    ? 'border-transparent text-purple-600 hover:text-purple-700 hover:border-purple-300 hover:bg-purple-50'
                                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                        >
                            <tab.icon className={`h-5 w-5 ${isActive
                                ? isFitTab ? 'text-purple-500' : 'text-blue-500'
                                : isFitTab ? 'text-purple-400' : 'text-gray-400 group-hover:text-gray-500'
                                }`} />
                            {tab.label}
                            {isFitTab && (
                                <span className="ml-1 px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs font-bold animate-pulse">
                                    ✨
                                </span>
                            )}
                        </button>
                    );
                })}
            </nav>
        </div>
    );
};


// ============================================================================
// TAB CONTENT COMPONENTS
// ============================================================================

// Campus Life Tab
const CampusLifeTab = ({ university }) => {
    const fullProfile = university?.fullProfile || {};
    const campusDynamics = fullProfile?.strategic_profile?.campus_dynamics || {};
    const takeaways = fullProfile?.strategic_profile?.analyst_takeaways || [];

    return (
        <div className="space-y-6">
            {/* Campus Dynamics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {campusDynamics.social_environment && (
                    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-2xl">🎉</span>
                            <h3 className="font-semibold text-gray-900">Social Life</h3>
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-4">{campusDynamics.social_environment}</p>
                    </div>
                )}
                {campusDynamics.transportation_impact && (
                    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-2xl">🚌</span>
                            <h3 className="font-semibold text-gray-900">Transportation</h3>
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-4">{campusDynamics.transportation_impact}</p>
                    </div>
                )}
                {campusDynamics.research_impact && (
                    <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-2xl">🔬</span>
                            <h3 className="font-semibold text-gray-900">Research Culture</h3>
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-4">{campusDynamics.research_impact}</p>
                    </div>
                )}
            </div>

            {/* Analyst Takeaways */}
            {takeaways.length > 0 && (
                <div>
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-yellow-500" />
                        Analyst Insights
                    </h3>
                    <div className="space-y-3">
                        {takeaways.map((t, i) => (
                            <div key={i} className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg">
                                <span className="inline-block px-2 py-0.5 bg-yellow-200 text-yellow-800 rounded text-xs font-medium mb-2">
                                    {t.category}
                                </span>
                                <p className="text-sm text-gray-700 mb-1"><strong>Insight:</strong> {t.insight}</p>
                                <p className="text-sm text-gray-600"><strong>Implication:</strong> {t.implication}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {!campusDynamics.social_environment && takeaways.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                    <HomeIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No campus life details available yet.</p>
                </div>
            )}
        </div>
    );
};

// Academics Tab
const AcademicsTab = ({ university }) => {
    const fullProfile = university?.fullProfile || {};
    const academicStructure = fullProfile?.academic_structure || {};
    const colleges = academicStructure?.colleges || [];
    const [expandedCollege, setExpandedCollege] = useState(null);

    return (
        <div className="space-y-4">
            <p className="text-gray-600 mb-4">
                Structure: <span className="font-medium">{academicStructure.structure_type || 'Colleges and Schools'}</span>
            </p>

            {colleges.map((college, idx) => (
                <div key={idx} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <button
                        onClick={() => setExpandedCollege(expandedCollege === idx ? null : idx)}
                        className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
                    >
                        <div className="flex items-center gap-3">
                            <AcademicCapIcon className="h-6 w-6 text-blue-600" />
                            <div className="text-left">
                                <h3 className="font-semibold text-gray-900">{college.name}</h3>
                                <p className="text-sm text-gray-500">
                                    {college.admissions_model} • {college.majors?.length || 0} majors
                                </p>
                            </div>
                        </div>
                        <span className="text-gray-400">{expandedCollege === idx ? '▲' : '▼'}</span>
                    </button>

                    {expandedCollege === idx && (
                        <div className="border-t border-gray-100 p-4 bg-gray-50">
                            {college.strategic_fit_advice && (
                                <p className="text-sm text-blue-700 bg-blue-50 p-3 rounded-lg mb-4">
                                    💡 {college.strategic_fit_advice}
                                </p>
                            )}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {(college.majors || []).map((major, mIdx) => (
                                    <div key={mIdx} className="bg-white p-3 rounded-lg border border-gray-100">
                                        <div className="flex items-center justify-between mb-1">
                                            <span className="font-medium text-gray-900">{major.name}</span>
                                            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{major.degree_type}</span>
                                        </div>
                                        {major.is_impacted && (
                                            <span className="inline-block px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">
                                                ⚠️ Impacted/Competitive
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            ))}

            {colleges.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                    <AcademicCapIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No academic structure details available yet.</p>
                </div>
            )}
        </div>
    );
};

// Admissions Tab
const AdmissionsTab = ({ university }) => {
    const fullProfile = university?.fullProfile || {};
    const admissionsData = fullProfile?.admissions_data || {};
    const currentStatus = admissionsData?.current_status || {};
    const admittedProfile = admissionsData?.admitted_student_profile || {};
    const trends = admissionsData?.longitudinal_trends || [];

    return (
        <div className="space-y-6">
            {/* Key Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
                    <p className="text-3xl font-bold text-blue-600">{currentStatus.overall_acceptance_rate || university?.admissions?.acceptanceRate || 'N/A'}%</p>
                    <p className="text-sm text-gray-500">Acceptance Rate</p>
                </div>
                <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
                    <p className="text-3xl font-bold text-purple-600">{currentStatus.is_test_optional ? 'Yes' : 'No'}</p>
                    <p className="text-sm text-gray-500">Test Optional</p>
                </div>
                <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
                    <p className="text-xl font-bold text-green-600">{admittedProfile?.testing?.sat_composite_middle_50 || 'N/A'}</p>
                    <p className="text-sm text-gray-500">SAT Range</p>
                </div>
                <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
                    <p className="text-xl font-bold text-orange-600">{admittedProfile?.gpa?.unweighted_middle_50 || 'N/A'}</p>
                    <p className="text-sm text-gray-500">GPA Range</p>
                </div>
            </div>

            {/* Trends */}
            {trends.length > 0 && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <ChartBarIcon className="h-5 w-5 text-blue-500" />
                        Acceptance Rate Trends
                    </h3>
                    <div className="flex items-end justify-between gap-2 h-40">
                        {trends
                            .slice(0, 5)
                            .reverse()
                            .filter(t => t.acceptance_rate_overall && t.acceptance_rate_overall > 0)
                            .map((t, i) => {
                                // Normalize: if value < 1, it's a decimal (0.48 = 48%), otherwise it's already a percentage
                                const rawRate = t.acceptance_rate_overall;
                                const normalizedRate = rawRate < 1 ? rawRate * 100 : rawRate;
                                const displayRate = normalizedRate.toFixed(1);

                                return (
                                    <div key={i} className="flex-1 flex flex-col items-center">
                                        <div
                                            className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t transition-all hover:from-blue-700 hover:to-blue-500"
                                            style={{ height: `${(normalizedRate / 100) * 100}%`, minHeight: '20px' }}
                                        ></div>
                                        <span className="text-xs text-gray-500 mt-2">{t.year}</span>
                                        <span className="text-sm font-bold text-blue-600">{displayRate}%</span>
                                    </div>
                                );
                            })}
                    </div>
                    {/* Trend indicator */}
                    {trends.length >= 2 && (
                        <div className="mt-4 pt-4 border-t border-gray-100">
                            {(() => {
                                const validTrends = trends.filter(t => t.acceptance_rate_overall && t.acceptance_rate_overall > 0);
                                if (validTrends.length < 2) return null;
                                const latest = validTrends[0].acceptance_rate_overall < 1
                                    ? validTrends[0].acceptance_rate_overall * 100
                                    : validTrends[0].acceptance_rate_overall;
                                const oldest = validTrends[validTrends.length - 1].acceptance_rate_overall < 1
                                    ? validTrends[validTrends.length - 1].acceptance_rate_overall * 100
                                    : validTrends[validTrends.length - 1].acceptance_rate_overall;
                                const change = latest - oldest;
                                const isMoreSelective = change < 0;
                                return (
                                    <p className={`text-sm flex items-center gap-2 ${isMoreSelective ? 'text-red-600' : 'text-green-600'}`}>
                                        {isMoreSelective ? '📉' : '📈'}
                                        <span className="font-medium">
                                            {isMoreSelective ? 'Getting more selective' : 'Getting less selective'}
                                        </span>
                                        <span className="text-gray-500">
                                            ({change > 0 ? '+' : ''}{change.toFixed(1)}% over {validTrends.length} years)
                                        </span>
                                    </p>
                                );
                            })()}
                        </div>
                    )}
                </div>
            )}

            {/* Holistic Factors */}
            {fullProfile?.application_process?.holistic_factors && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-3">What They Value</h3>
                    <div className="flex flex-wrap gap-2">
                        {(fullProfile.application_process.holistic_factors.primary_factors || []).map((f, i) => (
                            <span key={i} className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                                {f}
                            </span>
                        ))}
                        {(fullProfile.application_process.holistic_factors.secondary_factors || []).map((f, i) => (
                            <span key={i} className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                                {f}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// Financials Tab
const FinancialsTab = ({ university }) => {
    const fullProfile = university?.fullProfile || {};
    const financials = fullProfile?.financials || {};
    const coa = financials?.cost_of_attendance || {};
    const scholarships = financials?.scholarships || [];

    return (
        <div className="space-y-6">
            {/* Cost of Attendance */}
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <CurrencyDollarIcon className="h-5 w-5 text-green-600" />
                    Cost of Attendance
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">${(coa.tuition_in_state || university?.financials?.inStateTuition || 0).toLocaleString()}</p>
                        <p className="text-sm text-gray-500">In-State Tuition</p>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">${(coa.tuition_out_of_state || university?.financials?.outOfStateTuition || 0).toLocaleString()}</p>
                        <p className="text-sm text-gray-500">Out-of-State</p>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-2xl font-bold text-gray-900">${(coa.room_and_board || 0).toLocaleString()}</p>
                        <p className="text-sm text-gray-500">Room & Board</p>
                    </div>
                    <div className="text-center p-3 bg-purple-50 rounded-lg">
                        <p className="text-2xl font-bold text-purple-700">${(coa.total_estimated || 0).toLocaleString()}</p>
                        <p className="text-sm text-purple-600">Total Estimated</p>
                    </div>
                </div>
            </div>

            {/* Scholarships */}
            {scholarships.length > 0 && (
                <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-6 border border-emerald-100">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                        <span className="p-2 bg-emerald-100 rounded-lg">🎓</span>
                        Available Scholarships
                        <span className="ml-2 px-2 py-0.5 bg-emerald-200 text-emerald-800 rounded-full text-xs font-medium">
                            {scholarships.length} found
                        </span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {scholarships.map((s, i) => {
                            // Determine scholarship type for styling
                            const isFullRide = s.amount?.toLowerCase()?.includes('full') || s.name?.toLowerCase()?.includes('full');
                            const isNeedBased = s.eligibility?.toLowerCase()?.includes('need') || s.name?.toLowerCase()?.includes('need');
                            const isMerit = s.eligibility?.toLowerCase()?.includes('merit') || s.name?.toLowerCase()?.includes('merit');
                            const isExternal = s.name?.toLowerCase()?.includes('external') || s.name?.toLowerCase()?.includes('questbridge');

                            return (
                                <div
                                    key={i}
                                    className={`relative overflow-hidden rounded-xl p-5 shadow-md border transition-all hover:shadow-lg hover:-translate-y-0.5 ${isFullRide
                                        ? 'bg-gradient-to-br from-amber-50 to-yellow-50 border-amber-200'
                                        : 'bg-white border-gray-100'
                                        }`}
                                >
                                    {/* Full Ride Badge */}
                                    {isFullRide && (
                                        <div className="absolute top-0 right-0 bg-gradient-to-l from-amber-400 to-yellow-400 text-white px-3 py-1 text-xs font-bold rounded-bl-lg">
                                            ⭐ FULL RIDE
                                        </div>
                                    )}

                                    {/* Header */}
                                    <div className="flex items-start gap-3 mb-3">
                                        <div className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-lg ${isFullRide ? 'bg-amber-100' :
                                            isNeedBased ? 'bg-blue-100' :
                                                isMerit ? 'bg-purple-100' :
                                                    isExternal ? 'bg-pink-100' :
                                                        'bg-emerald-100'
                                            }`}>
                                            {isFullRide ? '🏆' :
                                                isNeedBased ? '💙' :
                                                    isMerit ? '⭐' :
                                                        isExternal ? '🌐' :
                                                            '💰'}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="font-semibold text-gray-900 text-sm leading-tight">{s.name}</h4>
                                            {/* Type Tags */}
                                            <div className="flex flex-wrap gap-1 mt-1">
                                                {isNeedBased && (
                                                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">Need-Based</span>
                                                )}
                                                {isMerit && (
                                                    <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs">Merit</span>
                                                )}
                                                {isExternal && (
                                                    <span className="px-2 py-0.5 bg-pink-100 text-pink-700 rounded text-xs">External</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Amount */}
                                    <div className={`inline-block px-3 py-1.5 rounded-lg mb-3 ${isFullRide
                                        ? 'bg-gradient-to-r from-amber-400 to-yellow-400 text-white'
                                        : 'bg-emerald-100 text-emerald-800'
                                        }`}>
                                        <span className="font-bold text-sm">{s.amount}</span>
                                    </div>

                                    {/* Description */}
                                    {s.eligibility && (
                                        <p className="text-sm text-gray-600 mb-3 line-clamp-2">{s.eligibility}</p>
                                    )}

                                    {/* Deadline */}
                                    {s.deadline && (
                                        <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
                                            <CalendarIcon className="h-4 w-4 text-orange-500" />
                                            <span className="text-xs text-gray-500">Deadline:</span>
                                            <span className="text-xs font-medium text-orange-600">{s.deadline}</span>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {!coa.tuition_in_state && scholarships.length === 0 && (
                <div className="text-center py-12 text-gray-400">
                    <CurrencyDollarIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>No financial details available yet.</p>
                </div>
            )}
        </div>
    );
};

// Fit Analysis Tab
const FitAnalysisTab = ({ fitAnalysis }) => {
    if (!fitAnalysis) {
        return (
            <div className="text-center py-12 text-gray-400">
                <SparklesIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No fit analysis available. Upload your profile to get personalized insights!</p>
            </div>
        );
    }

    const factors = fitAnalysis.factors || [];
    const essayAngles = fitAnalysis.essay_angles || [];
    const timeline = fitAnalysis.application_timeline || {};
    const scholarshipMatches = fitAnalysis.scholarship_matches || [];
    const redFlags = fitAnalysis.red_flags_to_avoid || [];

    return (
        <div className="space-y-6">
            {/* Factor Breakdown */}
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <ChartBarIcon className="h-5 w-5 text-purple-500" />
                    Fit Factor Breakdown
                </h3>
                <div className="space-y-4">
                    {factors.map((factor, idx) => (
                        <div key={idx}>
                            <div className="flex justify-between items-center mb-1">
                                <span className="font-medium text-gray-700">{factor.name}</span>
                                <span className={`font-bold ${factor.score >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                    {factor.score >= 0 ? '+' : ''}{factor.score}/{factor.max}
                                </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                    className={`h-2 rounded-full ${factor.score >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                                    style={{ width: `${Math.abs(factor.score) / Math.abs(factor.max) * 100}%` }}
                                ></div>
                            </div>
                            <p className="text-sm text-gray-500 mt-1">{factor.detail}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Essay Angles */}
            {essayAngles.length > 0 && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <DocumentTextIcon className="h-5 w-5 text-blue-500" />
                        Essay Strategies
                    </h3>
                    <div className="space-y-3">
                        {essayAngles.map((essay, idx) => (
                            <div key={idx} className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                                {essay.essay_prompt && (
                                    <p className="text-sm text-blue-800 font-medium mb-2">"{essay.essay_prompt}"</p>
                                )}
                                <p className="text-sm text-gray-700"><strong>Angle:</strong> {essay.angle}</p>
                                {essay.student_hook && <p className="text-sm text-gray-600 mt-1"><strong>Your hook:</strong> {essay.student_hook}</p>}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Application Timeline */}
            {timeline.recommended_plan && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <CalendarIcon className="h-5 w-5 text-orange-500" />
                        Recommended Application Plan
                    </h3>
                    <div className="flex items-center gap-4 p-4 bg-orange-50 rounded-lg">
                        <div className="text-4xl font-bold text-orange-600">{timeline.recommended_plan}</div>
                        <div>
                            <p className="text-sm text-gray-700">{timeline.rationale}</p>
                            {timeline.deadline && <p className="text-sm text-orange-600 font-medium mt-1">Deadline: {timeline.deadline}</p>}
                            {timeline.is_binding && <span className="inline-block mt-1 px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">Binding</span>}
                        </div>
                    </div>
                </div>
            )}

            {/* Red Flags */}
            {redFlags.length > 0 && (
                <div className="bg-red-50 rounded-xl p-5 border border-red-100">
                    <h3 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                        <ExclamationTriangleIcon className="h-5 w-5" />
                        Red Flags to Avoid
                    </h3>
                    <ul className="space-y-2">
                        {redFlags.map((flag, idx) => (
                            <li key={idx} className="text-sm text-red-700 flex items-start gap-2">
                                <span className="text-red-500">⚠️</span>
                                {flag}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

// ============================================================================
// DETAILS TAB - Combines Media + All University Info
// ============================================================================
const DetailsTab = ({ university }) => {
    return (
        <div className="space-y-8">
            {/* Media Gallery at Top */}
            {university?.media && (university.media.infographics?.length > 0 || university.media.videos?.length > 0) && (
                <MediaGallery media={university.media} />
            )}

            {/* Campus Life Section */}
            <div className="border-t border-gray-200 pt-8">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                    <HomeIcon className="h-5 w-5 text-purple-600" />
                    Campus Life
                </h3>
                <CampusLifeTab university={university} />
            </div>

            {/* Academics Section */}
            <div className="border-t border-gray-200 pt-8">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                    <AcademicCapIcon className="h-5 w-5 text-indigo-600" />
                    Academics
                </h3>
                <AcademicsTab university={university} />
            </div>

            {/* Admissions Section */}
            <div className="border-t border-gray-200 pt-8">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                    <BuildingLibraryIcon className="h-5 w-5 text-green-600" />
                    Admissions
                </h3>
                <AdmissionsTab university={university} />
            </div>

            {/* Financials Section */}
            <div className="border-t border-gray-200 pt-8">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                    <CurrencyDollarIcon className="h-5 w-5 text-amber-600" />
                    Financials & Scholarships
                </h3>
                <FinancialsTab university={university} />
            </div>
        </div>
    );
};

// ============================================================================
// UPDATED FIT ANALYSIS TAB - Uses Nano Banana Pro AI-generated infographic images
// ============================================================================
const UpdatedFitAnalysisTab = ({ fitAnalysis, university }) => {
    const { currentUser } = useAuth();
    const [infographicUrl, setInfographicUrl] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationError, setGenerationError] = useState(null);
    const [hasCredits, setHasCredits] = useState(false); // Default to false - hide regenerate until confirmed
    const [creditsRemaining, setCreditsRemaining] = useState(0);

    // Check credits on mount
    useEffect(() => {
        const checkUserCredits = async () => {
            if (currentUser?.email) {
                console.log('[Credits] Checking credits for:', currentUser.email);
                const result = await checkCredits(currentUser.email, 1);
                console.log('[Credits] Result:', result);
                const hasCreds = result.has_credits === true;
                setHasCredits(hasCreds);
                setCreditsRemaining(result.credits_remaining || 0);
                console.log('[Credits] hasCredits set to:', hasCreds, 'remaining:', result.credits_remaining);
            }
        };
        checkUserCredits();
    }, [currentUser?.email]);

    // Generate infographic on mount if not already cached
    // forceRegenerate = true costs 1 credit (regeneration)
    // forceRegenerate = false is free (initial load or cached)
    const handleGenerateInfographic = useCallback(async (forceRegenerate = false) => {
        if (!currentUser?.email || !university?.id) {
            console.log('[Infographic] Missing user or university ID');
            return;
        }

        // If regenerating (forceRegenerate=true), check and deduct credits first
        if (forceRegenerate) {
            const creditCheck = await checkCredits(currentUser.email, 1);
            if (!creditCheck.has_credits) {
                setGenerationError('Insufficient credits. Regenerating an infographic costs 1 credit.');
                return;
            }

            // Confirm with user
            const confirmed = window.confirm(
                'Regenerating the infographic will use 1 credit. Continue?'
            );
            if (!confirmed) {
                return;
            }

            // Deduct credit before regeneration
            const deductResult = await deductCredit(currentUser.email, 1, 'infographic_regeneration');
            if (!deductResult.success) {
                setGenerationError('Failed to deduct credit. Please try again.');
                return;
            }
            console.log(`[Infographic] Deducted 1 credit. Remaining: ${deductResult.credits_remaining}`);
        }

        setIsGenerating(true);
        setGenerationError(null);

        try {
            const universityId = university.id || university.name?.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
            console.log(`[Infographic] Generating for ${universityId} (force=${forceRegenerate})...`);

            const result = await generateFitInfographic(currentUser.email, universityId, forceRegenerate);

            if (result.success && result.infographic_url) {
                setInfographicUrl(result.infographic_url);
                console.log(`[Infographic] Generated (cached=${result.from_cache}):`, result.infographic_url);
            } else {
                setGenerationError(result.error || 'Failed to generate infographic');
            }
        } catch (err) {
            console.error('[Infographic] Error:', err);
            setGenerationError(err.message || 'Failed to generate infographic');
        } finally {
            setIsGenerating(false);
        }
    }, [currentUser?.email, university?.id, university?.name]);

    // Auto-generate on mount
    useEffect(() => {
        if (fitAnalysis && currentUser?.email && university?.id && !infographicUrl && !isGenerating) {
            handleGenerateInfographic(false);
        }
    }, [fitAnalysis, currentUser?.email, university?.id]);

    if (!fitAnalysis) {
        return (
            <div className="text-center py-12 text-gray-400">
                <SparklesIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No fit analysis available. Upload your profile to get personalized insights!</p>
            </div>
        );
    }

    const factors = fitAnalysis.factors || [];
    const essayAngles = fitAnalysis.essay_angles || [];
    const timeline = fitAnalysis.application_timeline || {};
    const scholarshipMatches = fitAnalysis.scholarship_matches || [];
    const redFlags = fitAnalysis.red_flags_to_avoid || [];
    const recommendations = fitAnalysis.recommendations || [];
    const gapAnalysis = fitAnalysis.gap_analysis || {};

    return (
        <div className="space-y-8">
            {/* Fit Infographic Section - Uses Nano Banana Pro AI */}
            <div className="bg-gradient-to-br from-purple-50 via-indigo-50 to-blue-50 rounded-2xl overflow-hidden border border-purple-100 shadow-sm">
                {infographicUrl ? (
                    // Display the generated infographic with regenerate link below
                    <div>
                        <img
                            src={infographicUrl}
                            alt={`Fit Analysis Infographic for ${university?.name || 'University'}`}
                            className="w-full h-auto max-h-[800px] object-contain bg-white"
                        />
                        {/* Regenerate section - show action or purchase prompt based on credits */}
                        <div className="flex justify-end p-3 bg-gray-50 border-t border-gray-100">
                            {hasCredits ? (
                                <button
                                    onClick={() => handleGenerateInfographic(true)}
                                    disabled={isGenerating}
                                    className="flex items-center gap-1 text-sm text-purple-600 hover:text-purple-800 transition-colors disabled:opacity-50"
                                >
                                    <ArrowPathIcon className={`h-4 w-4 ${isGenerating ? 'animate-spin' : ''}`} />
                                    {isGenerating ? 'Regenerating...' : 'Regenerate (1 credit)'}
                                </button>
                            ) : (
                                <a
                                    href="/pricing"
                                    className="flex items-center gap-1 text-sm text-amber-600 hover:text-amber-700 transition-colors"
                                >
                                    <CurrencyDollarIcon className="h-4 w-4" />
                                    Purchase credits to regenerate
                                </a>
                            )}
                        </div>
                    </div>
                ) : isGenerating ? (
                    // Loading state
                    <div className="p-12 text-center">
                        <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg animate-pulse">
                            <PhotoIcon className="h-10 w-10 text-white" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Generating Your Personalized Infographic...</h3>
                        <p className="text-gray-600 max-w-md mx-auto mb-4">
                            Our AI (Nano Banana Pro) is creating a high-resolution visual report. This may take 15-30 seconds.
                        </p>
                        <div className="flex justify-center">
                            <div className="flex items-center gap-2 text-purple-600">
                                <ArrowPathIcon className="h-5 w-5 animate-spin" />
                                <span className="text-sm font-medium">Creating infographic...</span>
                            </div>
                        </div>
                    </div>
                ) : generationError ? (
                    // Error state
                    <div className="p-8 text-center">
                        <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                            <ExclamationTriangleIcon className="h-8 w-8 text-red-500" />
                        </div>
                        <h3 className="text-lg font-bold text-gray-900 mb-2">Could not generate infographic</h3>
                        <p className="text-gray-600 text-sm mb-4">{generationError}</p>
                        <button
                            onClick={() => handleGenerateInfographic(true)}
                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors text-sm font-medium"
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    // Initial placeholder (waiting for auto-generate)
                    <div className="p-8 text-center">
                        <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                            <SparklesIcon className="h-10 w-10 text-white" />
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">Your Personal Fit Infographic</h3>
                        <p className="text-gray-600 max-w-md mx-auto">
                            {currentUser?.email
                                ? 'Click below to generate your personalized fit infographic.'
                                : 'Sign in to generate your personalized fit infographic.'}
                        </p>
                        <div className="mt-6 flex items-center justify-center gap-4 mb-6">
                            <div className="text-center">
                                <div className="text-4xl font-bold text-purple-600">{fitAnalysis.match_percentage || 0}%</div>
                                <div className="text-sm text-gray-500">Match Score</div>
                            </div>
                            <div className="w-px h-12 bg-gray-200"></div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-indigo-600">{(fitAnalysis.fit_category || 'N/A').replace('_', ' ')}</div>
                                <div className="text-sm text-gray-500">Category</div>
                            </div>
                        </div>
                        {currentUser?.email && (
                            <button
                                onClick={() => handleGenerateInfographic(false)}
                                disabled={isGenerating}
                                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl transition-all font-medium shadow-lg shadow-purple-200"
                            >
                                <PhotoIcon className="h-5 w-5 inline mr-2" />
                                Generate Infographic
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Action Plan Cards */}
            {recommendations.length > 0 && (
                <div>
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                        <LightBulbIcon className="h-5 w-5 text-purple-600" />
                        Your Action Plan
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {recommendations.slice(0, 3).map((rec, idx) => (
                            <div key={idx} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                                <div className="flex items-start gap-3">
                                    <span className="flex-shrink-0 w-8 h-8 bg-purple-100 text-purple-700 rounded-full flex items-center justify-center font-bold text-sm">
                                        {idx + 1}
                                    </span>
                                    <div className="flex-1">
                                        <p className="text-gray-800 font-medium text-sm leading-relaxed">
                                            {typeof rec === 'string' ? rec : rec.action}
                                        </p>
                                        {rec.timeline && (
                                            <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
                                                <CalendarIcon className="h-3 w-3" />
                                                {rec.timeline}
                                            </div>
                                        )}
                                        {rec.addresses_gap && (
                                            <span className="inline-block mt-2 px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">
                                                Addresses: {rec.addresses_gap}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Gaps & Strengths */}
            {(gapAnalysis.primary_gap || gapAnalysis.student_strengths) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                        <h3 className="font-semibold text-red-800 mb-2 flex items-center gap-2">
                            <ExclamationTriangleIcon className="h-5 w-5" />
                            Areas to Address
                        </h3>
                        <ul className="space-y-1 text-sm text-red-700">
                            {gapAnalysis.primary_gap && <li>• <strong>Primary:</strong> {gapAnalysis.primary_gap}</li>}
                            {gapAnalysis.secondary_gap && <li>• <strong>Secondary:</strong> {gapAnalysis.secondary_gap}</li>}
                        </ul>
                    </div>
                    <div className="bg-green-50 rounded-xl p-4 border border-green-100">
                        <h3 className="font-semibold text-green-800 mb-2 flex items-center gap-2">
                            <CheckCircleIcon className="h-5 w-5" />
                            Your Strengths
                        </h3>
                        <ul className="space-y-1 text-sm text-green-700">
                            {(gapAnalysis.student_strengths || []).slice(0, 3).map((s, i) => (
                                <li key={i}>• {s}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            {/* Factor Breakdown */}
            {factors.length > 0 && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <ChartBarIcon className="h-5 w-5 text-purple-500" />
                        Fit Factor Breakdown
                    </h3>
                    <div className="space-y-4">
                        {factors.map((factor, idx) => (
                            <div key={idx}>
                                <div className="flex justify-between items-center mb-1">
                                    <span className="font-medium text-gray-700">{factor.name}</span>
                                    <span className={`font-bold ${factor.score >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                        {factor.score >= 0 ? '+' : ''}{factor.score}/{factor.max}
                                    </span>
                                </div>
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className={`h-2 rounded-full ${factor.score >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                                        style={{ width: `${Math.abs(factor.score) / Math.abs(factor.max) * 100}%` }}
                                    ></div>
                                </div>
                                <p className="text-sm text-gray-500 mt-1">{factor.detail}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Essay Angles */}
            {essayAngles.length > 0 && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <DocumentTextIcon className="h-5 w-5 text-blue-500" />
                        Essay Strategies
                    </h3>
                    <div className="space-y-3">
                        {essayAngles.map((essay, idx) => (
                            <div key={idx} className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                                {essay.essay_prompt && (
                                    <p className="text-sm text-blue-800 font-medium mb-2">"{essay.essay_prompt}"</p>
                                )}
                                <p className="text-sm text-gray-700"><strong>Angle:</strong> {essay.angle}</p>
                                {essay.student_hook && <p className="text-sm text-gray-600 mt-1"><strong>Your hook:</strong> {essay.student_hook}</p>}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Application Timeline */}
            {timeline.recommended_plan && (
                <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
                    <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                        <CalendarIcon className="h-5 w-5 text-orange-500" />
                        Recommended Application Plan
                    </h3>
                    <div className="flex items-center gap-4 p-4 bg-orange-50 rounded-lg">
                        <div className="text-4xl font-bold text-orange-600">{timeline.recommended_plan}</div>
                        <div>
                            <p className="text-sm text-gray-700">{timeline.rationale}</p>
                            {timeline.deadline && <p className="text-sm text-orange-600 font-medium mt-1">Deadline: {timeline.deadline}</p>}
                            {timeline.is_binding && <span className="inline-block mt-1 px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">Binding</span>}
                        </div>
                    </div>
                </div>
            )}

            {/* Red Flags */}
            {redFlags.length > 0 && (
                <div className="bg-red-50 rounded-xl p-5 border border-red-100">
                    <h3 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                        <ExclamationTriangleIcon className="h-5 w-5" />
                        Red Flags to Avoid
                    </h3>
                    <ul className="space-y-2">
                        {redFlags.map((flag, idx) => (
                            <li key={idx} className="text-sm text-red-700 flex items-start gap-2">
                                <span className="text-red-500">⚠️</span>
                                {flag}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================
const UniversityProfilePage = ({ university, fitAnalysis, onBack }) => {
    const [activeTab, setActiveTab] = useState('details');
    const [showChat, setShowChat] = useState(false);

    const tabs = [
        { id: 'details', label: 'University Details', icon: BuildingLibraryIcon },
        ...(fitAnalysis ? [{ id: 'fit', label: 'Your Fit Analysis', icon: SparklesIcon }] : []),
    ];

    if (!university) return null;

    return (
        <div className="bg-gray-50 min-h-screen">
            {/* Back Button */}
            <div className="bg-white border-b border-gray-200 px-6 py-3">
                <button
                    onClick={onBack}
                    className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
                >
                    <ArrowLeftIcon className="h-5 w-5" />
                    Back to Universities
                </button>
            </div>

            {/* Hero Section */}
            <div className="max-w-6xl mx-auto px-4 py-6">
                <div className="bg-white rounded-2xl shadow-lg overflow-hidden relative">
                    <HeroSection
                        university={university}
                        fitAnalysis={fitAnalysis}
                        onAskAI={() => setShowChat(true)}
                    />

                    {/* Tab Navigation - Only 2 Tabs */}
                    <TabNavigation activeTab={activeTab} setActiveTab={setActiveTab} tabs={tabs} />

                    {/* Tab Content */}
                    <div className="p-6 min-h-[400px]">
                        {activeTab === 'details' && <DetailsTab university={university} />}
                        {activeTab === 'fit' && <UpdatedFitAnalysisTab fitAnalysis={fitAnalysis} university={university} />}
                    </div>
                </div>
            </div>

            {/* Ask AI Floating Action Button */}
            {!showChat && (
                <button
                    onClick={() => setShowChat(true)}
                    className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-5 py-3 bg-[#1A4D2E] text-white rounded-full shadow-lg hover:shadow-xl hover:bg-[#2D6B45] hover:scale-105 transition-all duration-300 font-medium group"
                >
                    <div className="relative">
                        <ChatBubbleLeftRightIcon className="h-6 w-6" />
                        <SparklesIcon className="h-3 w-3 absolute -top-1 -right-1 text-[#D6E8D5] animate-pulse" />
                    </div>
                    <span className="font-bold">Ask AI</span>
                </button>
            )}

            {/* Floating Chat Widget */}
            <UniversityChatWidget
                universityId={university.id}
                universityName={university.name}
                isOpen={showChat}
                onClose={() => setShowChat(false)}
            />
        </div>
    );
};

export default UniversityProfilePage;

