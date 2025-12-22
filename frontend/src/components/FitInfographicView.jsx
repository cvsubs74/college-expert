import React from 'react';
import {
    ChartBarIcon,
    AcademicCapIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    RocketLaunchIcon,
    MapPinIcon,
    StarIcon,
    ArrowTrendingUpIcon,
    UserCircleIcon,
    SparklesIcon,
    LightBulbIcon
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid';

/**
 * FitInfographicView - Renders structured fit analysis data as a beautiful Stratia-themed infographic
 * Replaces AI-generated images with a native React component for perfect text rendering
 */
const FitInfographicView = ({ data, studentName = "Student", onClose }) => {
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

    // Stratia theme colors based on fit category
    const fitConfig = {
        SAFETY: {
            gradient: 'from-[#1A4D2E] to-[#2D6B45]',
            bg: 'bg-[#1A4D2E]',
            light: 'bg-[#D6E8D5]',
            text: 'text-[#1A4D2E]',
            border: 'border-[#A8C5A6]',
            label: 'SAFETY',
            emoji: '✓',
            tagline: 'Strong fit with high admission probability'
        },
        TARGET: {
            gradient: 'from-[#1A4D2E] to-[#2D6B45]',
            bg: 'bg-[#1A4D2E]',
            light: 'bg-[#D6E8D5]',
            text: 'text-[#1A4D2E]',
            border: 'border-[#A8C5A6]',
            label: 'TARGET',
            emoji: '🎯',
            tagline: 'Accessible, but improvements needed for higher certainty'
        },
        REACH: {
            gradient: 'from-[#C05838] to-[#D4704F]',
            bg: 'bg-[#C05838]',
            light: 'bg-[#FCEEE8]',
            text: 'text-[#C05838]',
            border: 'border-[#E8A090]',
            label: 'REACH',
            emoji: '🔥',
            tagline: 'Competitive, requires strategic positioning'
        },
        SUPER_REACH: {
            gradient: 'from-[#C05838] to-[#A04020]',
            bg: 'bg-[#C05838]',
            light: 'bg-[#FCEEE8]',
            text: 'text-[#C05838]',
            border: 'border-[#E8A090]',
            label: 'SUPER REACH',
            emoji: '⭐',
            tagline: 'Highly competitive, exceptional positioning required'
        }
    };

    const config = fitConfig[fitCategory] || fitConfig.TARGET;

    // Circular Score Gauge Component
    const ScoreGauge = ({ score }) => {
        const radius = 50;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (score / 100) * circumference;

        return (
            <div className="relative w-28 h-28">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 120 120">
                    {/* Background circle */}
                    <circle
                        cx="60"
                        cy="60"
                        r={radius}
                        fill="none"
                        stroke="rgba(255,255,255,0.3)"
                        strokeWidth="8"
                    />
                    {/* Progress circle */}
                    <circle
                        cx="60"
                        cy="60"
                        r={radius}
                        fill="none"
                        stroke="white"
                        strokeWidth="8"
                        strokeDasharray={circumference}
                        strokeDashoffset={offset}
                        strokeLinecap="round"
                        className="transition-all duration-1000"
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
                    <span className="text-2xl font-bold">{score}</span>
                    <span className="text-xs opacity-80">/ 100</span>
                </div>
            </div>
        );
    };

    // Factor Score Bar
    const FactorBar = ({ name, score, maxScore, detail, isPositive }) => {
        const percentage = Math.min((score / maxScore) * 100, 100);
        const barColor = isPositive ? 'bg-[#1A4D2E]' : 'bg-[#C05838]';
        const bgColor = isPositive ? 'bg-[#D6E8D5]' : 'bg-[#FCEEE8]';

        return (
            <div className="mb-4">
                <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-gray-800 text-sm">{name}</span>
                    <span className={`text-sm font-bold ${isPositive ? 'text-[#1A4D2E]' : 'text-[#C05838]'}`}>
                        {score}/{maxScore}
                    </span>
                </div>
                <div className={`h-2.5 rounded-full ${bgColor}`}>
                    <div
                        className={`h-full rounded-full ${barColor} transition-all duration-700`}
                        style={{ width: `${percentage}%` }}
                    />
                </div>
                {detail && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{detail}</p>
                )}
            </div>
        );
    };

    // Parse factors from data
    const factors = data.strengths?.concat(data.improvements || []) || [];

    // Calculate section scores from factors
    const academicFactor = factors.find(f => f.name?.toLowerCase().includes('academic'));
    const holisticFactor = factors.find(f => f.name?.toLowerCase().includes('holistic'));
    const majorFactor = factors.find(f => f.name?.toLowerCase().includes('major'));
    const selectivityFactor = factors.find(f => f.name?.toLowerCase().includes('selectivity'));

    return (
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-200">
            {/* Header Section with Gradient */}
            <div className={`bg-gradient-to-r ${config.gradient} text-white p-6`}>
                <div className="flex items-center justify-between">
                    <div className="flex-1">
                        <h2 className="text-xl font-bold mb-1">
                            {studentName}'s Admission Chances
                        </h2>
                        <h3 className="text-lg opacity-90">
                            {universityInfo?.name || 'University'}
                        </h3>
                        <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 bg-white/20 rounded-full text-sm">
                            <span>{config.emoji}</span>
                            <span className="font-semibold">{config.label}</span>
                        </div>
                        <p className="text-sm opacity-80 mt-2">{config.tagline}</p>
                    </div>

                    <div className="flex flex-col items-center gap-2">
                        <div className="text-center">
                            <span className="text-xs uppercase tracking-wider opacity-80">Overall Match</span>
                        </div>
                        <ScoreGauge score={matchScore || 0} />
                        <span className="text-xs opacity-80">
                            {universityInfo?.acceptanceRate && `${universityInfo.acceptanceRate}% acceptance`}
                        </span>
                    </div>
                </div>
            </div>

            {/* Main Content Grid */}
            <div className="grid md:grid-cols-2 gap-0">
                {/* Left Column: Current Standing */}
                <div className="p-5 border-r border-gray-100">
                    <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                        <ChartBarIcon className="h-5 w-5 text-[#1A4D2E]" />
                        Current Standing & Scores
                    </h4>

                    {/* Academic Score */}
                    <FactorBar
                        name="ACADEMIC"
                        score={academicFactor?.score || 25}
                        maxScore={40}
                        detail={academicFactor?.detail || "GPA and test scores vs admitted students"}
                        isPositive={(academicFactor?.score || 25) > 20}
                    />

                    {/* Holistic Score */}
                    <FactorBar
                        name="HOLISTIC"
                        score={holisticFactor?.score || 25}
                        maxScore={30}
                        detail={holisticFactor?.detail || "Leadership, activities, service, awards"}
                        isPositive={(holisticFactor?.score || 25) > 15}
                    />

                    {/* Major Fit */}
                    <FactorBar
                        name="MAJOR FIT"
                        score={majorFactor?.score || 8}
                        maxScore={15}
                        detail={majorFactor?.detail || "Alignment with intended field of study"}
                        isPositive={(majorFactor?.score || 8) > 7}
                    />

                    {/* Selectivity */}
                    <FactorBar
                        name="SELECTIVITY"
                        score={Math.max(0, selectivityFactor?.score || 5)}
                        maxScore={5}
                        detail={selectivityFactor?.detail || `${universityInfo?.acceptanceRate || 'N/A'}% acceptance rate adjustment`}
                        isPositive={true}
                    />

                    {/* Gap Summary */}
                    {gapAnalysis && (
                        <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <p className="text-xs font-medium text-gray-700">
                                <strong>Primary Gap:</strong> {gapAnalysis.primary_gap || gapAnalysis.primaryGap || 'N/A'}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                                <strong>Secondary Gap:</strong> {gapAnalysis.secondary_gap || gapAnalysis.secondaryGap || 'N/A'}
                            </p>
                        </div>
                    )}
                </div>

                {/* Right Column: Action Items */}
                <div className="p-5 bg-gradient-to-b from-gray-50 to-white">
                    <h4 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                        <RocketLaunchIcon className="h-5 w-5 text-[#C05838]" />
                        Path to Improvement
                    </h4>

                    <div className="space-y-4">
                        {actionPlan && actionPlan.length > 0 ? (
                            actionPlan.slice(0, 4).map((item, idx) => (
                                <div key={idx} className="flex gap-3">
                                    <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white text-sm font-bold ${idx < 2 ? 'bg-[#1A4D2E]' : 'bg-[#C05838]'}`}>
                                        {item.step || idx + 1}
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-800 font-medium leading-snug">
                                            {item.action?.length > 120 ? item.action.substring(0, 120) + '...' : item.action}
                                        </p>
                                        {item.timeline && (
                                            <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded ${idx < 2 ? 'bg-[#D6E8D5] text-[#1A4D2E]' : 'bg-[#FCEEE8] text-[#C05838]'}`}>
                                                {item.timeline}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className="text-gray-500 text-sm">Action items loading...</p>
                        )}
                    </div>

                    {/* Student Strengths */}
                    {gapAnalysis?.studentStrengths && gapAnalysis.studentStrengths.length > 0 && (
                        <div className="mt-5 p-3 bg-[#D6E8D5] rounded-lg border border-[#A8C5A6]">
                            <p className="text-xs font-bold text-[#1A4D2E] mb-2 flex items-center gap-1">
                                <SparklesIcon className="h-4 w-4" />
                                YOUR STRENGTHS
                            </p>
                            <p className="text-xs text-[#1A4D2E]">
                                {gapAnalysis.studentStrengths.slice(0, 3).join(' • ')}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Footer: Goal Banner */}
            <div className={`bg-gradient-to-r ${config.gradient} text-white py-3 px-6 text-center`}>
                <p className="text-sm font-semibold">
                    🎯 GOAL: Strengthen application for increased chances at {universityInfo?.name || 'this university'}
                </p>
            </div>
        </div>
    );
};

export default FitInfographicView;
