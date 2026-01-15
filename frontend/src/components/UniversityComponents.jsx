import React, { useState } from 'react';
import {
    MapPinIcon,
    TrophyIcon,
    CurrencyDollarIcon,
    BookOpenIcon,
    UsersIcon,
    ArrowTrendingUpIcon,
    ArrowLeftIcon,
    AcademicCapIcon,
    BriefcaseIcon,
    BuildingLibraryIcon,
    SparklesIcon,
    MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { startSession, extractFullResponse } from '../services/api';

// --- Badge Component ---
export const Badge = ({ children, color }) => {
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



// --- University Detail Component ---
export const UniversityDetail = ({ uni, onBack, sentiment, fitAnalysis }) => {
    if (!uni) return null;

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
                        <Badge color="white">{uni.location?.type || 'N/A'}</Badge>
                        <span className="bg-blue-800/50 px-2 py-1 rounded-full text-xs flex items-center gap-1">
                            <MapPinIcon className="h-3 w-3" /> {uni.location?.city || 'N/A'}, {uni.location?.state || 'N/A'}
                        </span>
                        {/* Fit Badge */}
                        {fitAnalysis?.fit_category && (
                            <span className={`px-2 py-1 rounded-full text-xs font-bold border ${fitColors[fitAnalysis.fit_category] || fitColors.TARGET}`}>
                                {fitAnalysis.fit_category === 'SUPER_REACH' ? '🎯 Super Reach' :
                                    fitAnalysis.fit_category === 'REACH' ? '🎯 Reach' :
                                        fitAnalysis.fit_category === 'TARGET' ? '🎯 Target' :
                                            '✅ Safety'}
                            </span>
                        )}
                    </div>
                    <h1 className="text-3xl md:text-4xl font-bold mb-2">{uni.name || uni.university_name}</h1>
                    {uni.market_position && (
                        <p className="text-blue-100 text-lg font-medium">{uni.market_position}</p>
                    )}
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
                        <div className="mt-4 p-4 rounded-lg prose prose-sm max-w-none bg-white text-gray-700">
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
                                    {uni.rankings?.usNews !== 'N/A' && uni.rankings?.usNews ? `#${uni.rankings.usNews}` : 'N/A'}
                                </div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">US News Rank</div>
                            </div>
                            <div className="p-4 bg-green-50 rounded-xl border border-green-100">
                                <div className="text-green-600 mb-1"><UsersIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">
                                    {uni.admissions?.acceptanceRate !== 'N/A' && uni.admissions?.acceptanceRate ? `${uni.admissions.acceptanceRate}%` : 'N/A'}
                                </div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Acceptance</div>
                            </div>
                            <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
                                <div className="text-purple-600 mb-1"><BookOpenIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">{uni.admissions?.gpa || 'N/A'}</div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Avg GPA</div>
                            </div>
                            <div className="p-4 bg-orange-50 rounded-xl border border-orange-100">
                                <div className="text-orange-600 mb-1"><ArrowTrendingUpIcon className="h-5 w-5" /></div>
                                <div className="text-2xl font-bold text-gray-900">
                                    {uni.outcomes?.medianEarnings !== 'N/A' && uni.outcomes?.medianEarnings
                                        ? `$${Math.round(uni.outcomes.medianEarnings / 1000)}k`
                                        : 'N/A'}
                                </div>
                                <div className="text-xs text-gray-500 uppercase tracking-wide">Median Pay</div>
                            </div>
                        </div>

                        {/* Fit Analysis Section (for Launchpad) */}
                        {fitAnalysis && (
                            <section>
                                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <AcademicCapIcon className="h-5 w-5 text-blue-600" /> Fit Analysis
                                </h2>
                                <div className="bg-gray-50 rounded-xl p-6 border border-gray-100">
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                        <div>
                                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Fit Category</h3>
                                            <span className={`inline-block px-3 py-1.5 rounded-full text-sm font-bold ${fitColors[fitAnalysis.fit_category] || fitColors.TARGET}`}>
                                                {fitAnalysis.fit_category}
                                            </span>
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Match Score</h3>
                                            <div className="text-2xl font-bold text-gray-900">
                                                {fitAnalysis.match_percentage ? `${fitAnalysis.match_percentage}%` : 'N/A'}
                                            </div>
                                        </div>
                                    </div>
                                    {fitAnalysis.factors && fitAnalysis.factors.length > 0 && (
                                        <div className="mt-4 pt-4 border-t border-gray-200">
                                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Key Factors</h3>
                                            <div className="flex flex-wrap gap-2">
                                                {fitAnalysis.factors.map((factor, idx) => (
                                                    <span key={idx} className="bg-white px-3 py-1 rounded-lg border border-gray-200 text-sm text-gray-700">
                                                        {factor.name || factor}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </section>
                        )}

                        {/* Admissions Section */}
                        {uni.admissions && (
                            <section>
                                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <AcademicCapIcon className="h-5 w-5 text-blue-600" /> Admissions Profile
                                </h2>
                                <div className="bg-gray-50 rounded-xl p-6 border border-gray-100">
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                        <div>
                                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Test Policy</h3>
                                            <p className="text-gray-600">{uni.admissions.testPolicy || 'N/A'}</p>
                                        </div>
                                        <div>
                                            <h3 className="text-sm font-semibold text-gray-700 mb-2">Selectivity</h3>
                                            {uni.admissions.acceptanceRate !== 'N/A' && uni.admissions.acceptanceRate && (
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
                        )}

                        {/* Popular Majors */}
                        {uni.majors && uni.majors.length > 0 && (
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
                        )}
                    </div>

                    {/* Sidebar */}
                    <div className="space-y-6">

                        {/* Financials Widget */}
                        {uni.financials && (
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
                        )}

                        {/* Outcomes Widget */}
                        {uni.outcomes && (
                            <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl shadow-sm p-6 text-white">
                                <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                                    <BriefcaseIcon className="h-5 w-5 text-blue-400" /> Career Outcomes
                                </h2>
                                <div className="mb-6">
                                    <div className="text-3xl font-bold text-green-400 mb-1">
                                        {uni.outcomes.medianEarnings !== 'N/A' && uni.outcomes.medianEarnings
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
                        )}

                    </div>
                </div>

                {/* University Overview Section */}
                {(uni.summary || uni.description) && (
                    <div className="mt-8 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <SparklesIcon className="h-5 w-5 text-purple-600" />
                            University Overview
                        </h2>
                        <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {uni.summary || uni.description}
                            </ReactMarkdown>
                        </div>
                    </div>
                )}

            </div>
        </div>
    );
};
