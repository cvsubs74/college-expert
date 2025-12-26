import React from 'react';
import {
    ChartBarIcon,
    AcademicCapIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    RocketLaunchIcon,
    QuestionMarkCircleIcon,
    StarIcon,
    SignalIcon,
    ShieldCheckIcon,
    DocumentTextIcon
} from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolid, StarIcon as StarSolid } from '@heroicons/react/24/solid';

/**
 * FitInfographicView - High-contrast, zero-gradient infographic component
 * Design: Modular "Control Center" layout with distinct sections
 */
const FitInfographicView = ({ data, studentName = "Student" }) => {
    if (!data) return null;

    const {
        matchScore,
        fitCategory,
        universityInfo,
        gapAnalysis,
        actionPlan
    } = data;

    // Solid color config per fit category (NO gradients)
    const categoryConfig = {
        SAFETY: { bg: '#059669', text: 'white', label: 'LIKELY', border: '#047857' },
        TARGET: { bg: '#1A4D2E', text: 'white', label: 'TARGET', border: '#143D24' },
        REACH: { bg: '#D97706', text: 'white', label: 'REACH', border: '#B45309' },
        SUPER_REACH: { bg: '#DC2626', text: 'white', label: 'SUPER REACH', border: '#B91C1C' }
    };
    const config = categoryConfig[fitCategory] || categoryConfig.TARGET;

    // Parse factors from data
    const allFactors = [...(data.strengths || []), ...(data.improvements || [])];
    const academicFactor = allFactors.find(f => f.name?.toLowerCase().includes('academic'));
    const holisticFactor = allFactors.find(f => f.name?.toLowerCase().includes('holistic'));
    const majorFactor = allFactors.find(f => f.name?.toLowerCase().includes('major'));
    const selectivityFactor = allFactors.find(f => f.name?.toLowerCase().includes('selectivity'));

    // Get strengths and weaknesses from gap analysis
    const strengths = gapAnalysis?.student_strengths || gapAnalysis?.studentStrengths || [];
    const primaryGap = gapAnalysis?.primary_gap || gapAnalysis?.primaryGap || '';
    const secondaryGap = gapAnalysis?.secondary_gap || gapAnalysis?.secondaryGap || '';

    // Score color helper (Red/Yellow/Green)
    const getScoreColor = (score, max) => {
        const pct = (score / max) * 100;
        if (pct >= 70) return '#059669'; // Green
        if (pct >= 40) return '#D97706'; // Amber
        return '#DC2626'; // Red
    };

    // Selectivity badge helper
    const getSelectivityBadge = (acceptanceRate) => {
        if (!acceptanceRate || acceptanceRate === 'N/A') return { label: 'Unknown', color: '#6B7280' };
        const rate = parseFloat(acceptanceRate);
        if (rate < 10) return { label: 'Extremely Selective', color: '#DC2626' };
        if (rate < 25) return { label: 'Highly Selective', color: '#D97706' };
        if (rate < 50) return { label: 'Moderately Selective', color: '#059669' };
        return { label: 'Less Selective', color: '#059669' };
    };

    const selectivityBadge = getSelectivityBadge(universityInfo?.acceptanceRate);

    // Radial Gauge (Solid stroke, no glow)
    const RadialGauge = ({ score }) => {
        const radius = 40;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (score / 100) * circumference;

        return (
            <div className="relative w-28 h-28">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.25)" strokeWidth="10" />
                    <circle
                        cx="50" cy="50" r={radius} fill="none"
                        stroke="white" strokeWidth="8"
                        strokeDasharray={circumference} strokeDashoffset={offset}
                        strokeLinecap="round"
                    />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
                    <span className="text-2xl font-bold">{score}</span>
                    <span className="text-xs opacity-80">/100</span>
                </div>
            </div>
        );
    };

    // Horizontal Progress Bar Widget
    const ScoreWidget = ({ label, score, maxScore, detail }) => {
        const pct = Math.min((score / maxScore) * 100, 100);
        const color = getScoreColor(score, maxScore);

        return (
            <div className="border-2 border-gray-100 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                <div className="flex justify-between items-center mb-2">
                    <span className="font-semibold text-gray-800 text-sm">{label}</span>
                    <span className="font-bold text-sm" style={{ color }}>{score}/{maxScore}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
                </div>
                {detail && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{detail}</p>}
            </div>
        );
    };

    // Star Rating Widget
    const StarRating = ({ filled, total }) => (
        <div className="flex gap-0.5">
            {[...Array(total)].map((_, i) => (
                i < filled
                    ? <StarSolid key={i} className="w-4 h-4 text-amber-400" />
                    : <StarIcon key={i} className="w-4 h-4 text-gray-300" />
            ))}
        </div>
    );

    // Signal Strength Widget (for Major Fit)
    const SignalStrength = ({ level, isUndecided }) => {
        if (isUndecided) {
            return (
                <div className="flex items-center gap-1 text-amber-600">
                    <QuestionMarkCircleIcon className="w-5 h-5" />
                    <span className="text-xs font-medium">Undecided</span>
                </div>
            );
        }
        const bars = [1, 2, 3, 4];
        return (
            <div className="flex items-end gap-0.5 h-4">
                {bars.map(b => (
                    <div
                        key={b}
                        className={`w-1.5 rounded-sm ${b <= level ? 'bg-emerald-500' : 'bg-gray-200'}`}
                        style={{ height: `${b * 25}%` }}
                    />
                ))}
            </div>
        );
    };

    // Timeline Tag
    const TimelineTag = ({ phase }) => {
        const colors = {
            'Before application': { bg: '#DBEAFE', text: '#1E40AF' },
            'In essays': { bg: '#FEE2E2', text: '#991B1B' },
            'During senior year': { bg: '#D1FAE5', text: '#065F46' }
        };
        const style = colors[phase] || { bg: '#F3F4F6', text: '#374151' };
        return (
            <span className="text-xs px-2 py-0.5 rounded font-medium" style={{ backgroundColor: style.bg, color: style.text }}>
                {phase}
            </span>
        );
    };

    // Calculate star rating from holistic score
    const holisticStars = holisticFactor ? Math.round((holisticFactor.score / (holisticFactor.maxScore || 30)) * 5) : 3;

    // Calculate signal level from major fit
    const majorSignalLevel = majorFactor ? Math.ceil((majorFactor.score / (majorFactor.maxScore || 15)) * 4) : 2;
    const isMajorUndecided = majorFactor?.detail?.toLowerCase().includes('undecided');

    return (
        <div className="bg-white rounded-2xl overflow-hidden border-2 border-gray-100 shadow-[0_8px_30px_rgb(0,0,0,0.12)] hover:shadow-[0_12px_40px_rgb(0,0,0,0.18)] transition-shadow duration-300">

            {/* ===== SECTION A: HEADER ===== */}
            <div className="p-6 flex items-center justify-between" style={{ backgroundColor: config.bg }}>
                <div className="flex-1">
                    <p className="text-sm opacity-80" style={{ color: config.text }}>
                        {studentName}'s Admission Chances
                    </p>
                    <h2 className="text-xl font-bold" style={{ color: config.text }}>
                        {universityInfo?.name || 'University'}
                    </h2>
                    <div className="mt-2 flex items-center gap-3">
                        {/* Classification Badge - Solid Pill */}
                        <span
                            className="px-3 py-1 rounded-full text-sm font-bold border-2"
                            style={{ backgroundColor: 'white', color: config.bg, borderColor: config.border }}
                        >
                            {config.label}
                        </span>
                        {universityInfo?.acceptanceRate && (
                            <span className="text-sm opacity-80" style={{ color: config.text }}>
                                {universityInfo.acceptanceRate}% acceptance
                            </span>
                        )}
                    </div>
                </div>

                {/* Match Score Gauge */}
                <div className="text-center">
                    <p className="text-xs uppercase tracking-wide mb-1 opacity-80" style={{ color: config.text }}>
                        Overall Match
                    </p>
                    <RadialGauge score={matchScore || 0} />
                </div>
            </div>

            {/* ===== SECTION B: SNAPSHOT (2x2 Grid) ===== */}
            <div className="p-5 border-b border-gray-200">
                <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                    <ChartBarIcon className="w-5 h-5 text-gray-600" />
                    Current Standing & Scores
                </h3>
                <div className="grid grid-cols-2 gap-3">
                    {/* Academic Index */}
                    <ScoreWidget
                        label="ACADEMIC"
                        score={academicFactor?.score || 14}
                        maxScore={academicFactor?.maxScore || 40}
                        detail={academicFactor?.detail}
                    />

                    {/* Holistic Review - Star Rating */}
                    <div className="border-2 border-gray-100 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-center mb-2">
                            <span className="font-semibold text-gray-800 text-sm">HOLISTIC</span>
                            <span className="font-bold text-sm text-gray-700">
                                {holisticFactor?.score || 25}/{holisticFactor?.maxScore || 30}
                            </span>
                        </div>
                        <StarRating filled={holisticStars} total={5} />
                        {holisticFactor?.detail && (
                            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{holisticFactor.detail}</p>
                        )}
                    </div>

                    {/* Major Fit - Signal Strength */}
                    <div className="border-2 border-gray-100 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-center mb-2">
                            <span className="font-semibold text-gray-800 text-sm">MAJOR FIT</span>
                            <span className="font-bold text-sm text-gray-700">
                                {majorFactor?.score || 8}/{majorFactor?.maxScore || 15}
                            </span>
                        </div>
                        <SignalStrength level={majorSignalLevel} isUndecided={isMajorUndecided} />
                        {majorFactor?.detail && (
                            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{majorFactor.detail}</p>
                        )}
                    </div>

                    {/* Selectivity - Badge */}
                    <div className="border-2 border-gray-100 rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-center mb-2">
                            <span className="font-semibold text-gray-800 text-sm">SELECTIVITY</span>
                        </div>
                        <span
                            className="inline-block px-2 py-1 rounded text-xs font-bold text-white"
                            style={{ backgroundColor: selectivityBadge.color }}
                        >
                            {selectivityBadge.label}
                        </span>
                        <p className="text-xs text-gray-500 mt-1">
                            {universityInfo?.acceptanceRate ? `${universityInfo.acceptanceRate}% acceptance rate` : 'N/A'}
                        </p>
                    </div>
                </div>
            </div>

            {/* ===== SECTION C: STRATEGY ANALYSIS (Strengths vs Risks) ===== */}
            <div className="p-5 border-b border-gray-200 bg-gray-50">
                <div className="grid md:grid-cols-2 gap-4">
                    {/* Winning Factors */}
                    <div>
                        <h4 className="font-bold text-gray-800 mb-2 flex items-center gap-1">
                            <ShieldCheckIcon className="w-4 h-4 text-emerald-600" />
                            Winning Factors
                        </h4>
                        <ul className="space-y-2">
                            {strengths.length > 0 ? strengths.slice(0, 3).map((s, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm">
                                    <CheckCircleSolid className="w-4 h-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                                    <span className="text-gray-700">{s}</span>
                                </li>
                            )) : (
                                <li className="text-gray-500 text-sm">No specific strengths identified</li>
                            )}
                        </ul>
                    </div>

                    {/* Risk Factors */}
                    <div>
                        <h4 className="font-bold text-gray-800 mb-2 flex items-center gap-1">
                            <ExclamationTriangleIcon className="w-4 h-4 text-amber-500" />
                            Risk Factors
                        </h4>
                        <ul className="space-y-2">
                            {primaryGap && (
                                <li className="flex items-start gap-2 text-sm">
                                    <ExclamationTriangleIcon className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                                    <span><strong className="text-gray-800">{primaryGap}</strong></span>
                                </li>
                            )}
                            {secondaryGap && (
                                <li className="flex items-start gap-2 text-sm">
                                    <ExclamationTriangleIcon className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                                    <span><strong className="text-gray-800">{secondaryGap}</strong></span>
                                </li>
                            )}
                            {!primaryGap && !secondaryGap && (
                                <li className="text-gray-500 text-sm">No major gaps identified</li>
                            )}
                        </ul>
                    </div>
                </div>
            </div>

            {/* ===== SECTION D: PATH TO IMPROVEMENT (Vertical Timeline) ===== */}
            <div className="p-5">
                <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
                    <RocketLaunchIcon className="w-5 h-5 text-gray-600" />
                    Path to Improvement
                </h3>
                <div className="space-y-3">
                    {actionPlan && actionPlan.length > 0 ? (
                        actionPlan.slice(0, 4).map((item, idx) => (
                            <div
                                key={idx}
                                className="flex gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer group"
                            >
                                {/* Step Circle */}
                                <div
                                    className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white text-sm font-bold"
                                    style={{ backgroundColor: config.bg }}
                                >
                                    {item.step || idx + 1}
                                </div>
                                <div className="flex-1">
                                    <p className="text-sm text-gray-800 leading-snug group-hover:text-gray-900">
                                        {item.action}
                                    </p>
                                    {item.timeline && (
                                        <div className="mt-1">
                                            <TimelineTag phase={item.timeline} />
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))
                    ) : (
                        <p className="text-gray-500 text-sm">Action items will appear here</p>
                    )}
                </div>
            </div>

            {/* ===== SECTION E: ESSAY ANGLES (NEW) ===== */}
            {data.essayAngles && data.essayAngles.length > 0 && (
                <div className="p-5 border-b border-gray-200">
                    <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                        <DocumentTextIcon className="w-5 h-5 text-blue-500" />
                        Essay Strategy Highlights
                    </h3>
                    <div className="space-y-2">
                        {data.essayAngles.slice(0, 2).map((essay, idx) => (
                            <div key={idx} className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                                <p className="text-sm text-gray-700 font-medium">{essay.angle}</p>
                                {essay.student_hook && (
                                    <p className="text-xs text-blue-600 mt-1">💡 Your hook: {essay.student_hook}</p>
                                )}
                            </div>
                        ))}
                        {data.essayAngles.length > 2 && (
                            <p className="text-xs text-blue-500 text-center">+{data.essayAngles.length - 2} more essay strategies in Strategy tab</p>
                        )}
                    </div>
                </div>
            )}

            {/* ===== SECTION F: TEST STRATEGY (NEW) ===== */}
            {data.testStrategy && data.testStrategy.recommendation && (
                <div className="p-5 border-b border-gray-200 bg-gray-50">
                    <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                        <AcademicCapIcon className="w-5 h-5 text-purple-500" />
                        Test Strategy
                    </h3>
                    <div className="flex items-center gap-4">
                        <span className={`px-3 py-1.5 rounded-full text-sm font-bold ${data.testStrategy.recommendation === 'Submit' ? 'bg-green-100 text-green-800' :
                            data.testStrategy.recommendation === 'Test Optional' ? 'bg-amber-100 text-amber-800' :
                                'bg-gray-100 text-gray-800'
                            }`}>
                            {data.testStrategy.recommendation}
                        </span>
                        {data.testStrategy.student_score_position && (
                            <span className="text-sm text-gray-600">
                                Your score: <strong className={
                                    data.testStrategy.student_score_position.includes('above') ? 'text-green-600' :
                                        data.testStrategy.student_score_position.includes('below') ? 'text-red-600' :
                                            'text-gray-600'
                                }>{data.testStrategy.student_score_position}</strong>
                            </span>
                        )}
                    </div>
                    {data.testStrategy.rationale && (
                        <p className="text-xs text-gray-500 mt-2 line-clamp-2">{data.testStrategy.rationale}</p>
                    )}
                </div>
            )}

            {/* ===== SECTION G: RED FLAGS (NEW) ===== */}
            {data.redFlags && data.redFlags.length > 0 && (
                <div className="p-5 border-b border-gray-200">
                    <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                        <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />
                        Watch Out For
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {data.redFlags.slice(0, 4).map((flag, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-sm bg-red-50 p-2 rounded-lg border border-red-100">
                                <span className="text-red-500 flex-shrink-0">⚠️</span>
                                <span className="text-red-700 line-clamp-2">{typeof flag === 'string' ? flag : flag.text}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ===== SECTION H: QUICK STATS (NEW) ===== */}
            {(data.scholarshipCount || data.applicationTimeline) && (
                <div className="p-5 border-b border-gray-200 bg-gray-50">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                        {data.scholarshipCount > 0 && (
                            <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-100">
                                <div className="text-2xl font-bold text-emerald-600">{data.scholarshipCount}</div>
                                <div className="text-xs text-gray-600">Scholarship Matches</div>
                            </div>
                        )}
                        {data.applicationTimeline?.recommended_plan && (
                            <div className="bg-amber-50 p-3 rounded-lg border border-amber-100">
                                <div className="text-lg font-bold text-amber-700">{data.applicationTimeline.recommended_plan}</div>
                                <div className="text-xs text-gray-600">Recommended Plan</div>
                            </div>
                        )}
                        {data.applicationTimeline?.deadline && (
                            <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                                <div className="text-sm font-bold text-blue-700">{data.applicationTimeline.deadline}</div>
                                <div className="text-xs text-gray-600">Deadline</div>
                            </div>
                        )}
                        {data.essayAngles && data.essayAngles.length > 0 && (
                            <div className="bg-purple-50 p-3 rounded-lg border border-purple-100">
                                <div className="text-2xl font-bold text-purple-600">{data.essayAngles.length}</div>
                                <div className="text-xs text-gray-600">Essay Strategies</div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ===== FOOTER GOAL BANNER ===== */}
            <div className="px-5 py-3 text-center border-t border-gray-200" style={{ backgroundColor: config.bg }}>
                <p className="text-sm font-semibold" style={{ color: config.text }}>
                    🎯 GOAL: Strengthen application for increased chances at {universityInfo?.name || 'this university'}
                </p>
            </div>
        </div>
    );
};

export default FitInfographicView;
