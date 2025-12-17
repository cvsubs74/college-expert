import React from 'react';
import {
    XMarkIcon,
    PrinterIcon,
    ChartBarIcon,
    AcademicCapIcon,
    CalendarIcon,
    CurrencyDollarIcon,
    ExclamationTriangleIcon,
    LightBulbIcon,
    PencilSquareIcon,
    FlagIcon,
    UserCircleIcon,
    ArrowRightIcon,
    RocketLaunchIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useNavigate } from 'react-router-dom';

const FitAnalysisModal = ({ isOpen, onClose, fitAnalysis, uniName, softFitCategory }) => {
    const navigate = useNavigate();

    if (!isOpen) return null;

    const printAnalysis = () => {
        window.print();
    };

    const fitColors = {
        SAFETY: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', badge: 'bg-green-100' },
        TARGET: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', badge: 'bg-blue-100' },
        REACH: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-800', badge: 'bg-orange-100' },
        SUPER_REACH: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', badge: 'bg-red-100' }
    };

    // Empty state when no fit analysis computed
    if (!fitAnalysis) {
        const softConfig = softFitCategory ? fitColors[softFitCategory] : null;

        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
                    <div className="flex items-center justify-between p-6 border-b border-gray-100">
                        <h2 className="text-xl font-bold text-gray-900">Fit Analysis</h2>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                        >
                            <XMarkIcon className="h-5 w-5" />
                        </button>
                    </div>

                    <div className="p-8 text-center">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 mb-4">
                            <UserCircleIcon className="h-8 w-8 text-amber-500" />
                        </div>

                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            Personalized Analysis for {uniName}
                        </h3>

                        {softFitCategory && (
                            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full mb-4 ${softConfig?.bg} ${softConfig?.border} border`}>
                                <span className={`text-sm font-medium ${softConfig?.text}`}>
                                    Fit: {softFitCategory === 'SUPER_REACH' ? 'Super Reach' :
                                        softFitCategory === 'REACH' ? 'Reach' :
                                            softFitCategory === 'TARGET' ? 'Target' : 'Safety'}
                                </span>
                                <span className="text-xs text-gray-500">(based on acceptance rate)</span>
                            </div>
                        )}

                        <p className="text-gray-600 mb-6 max-w-sm mx-auto">
                            To get a detailed, personalized fit analysis, complete your profile and add this university to your Launchpad.
                        </p>

                        <div className="flex flex-col gap-3">
                            <button
                                onClick={() => { onClose(); navigate('/profile'); }}
                                className="flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-200 hover:shadow-xl transition-all"
                            >
                                Complete Profile
                                <ArrowRightIcon className="h-4 w-4" />
                            </button>
                            <button
                                onClick={() => { onClose(); navigate('/launchpad'); }}
                                className="flex items-center justify-center gap-2 px-6 py-2.5 text-gray-600 hover:text-gray-800 font-medium transition-colors"
                            >
                                <RocketLaunchIcon className="h-4 w-4" />
                                Go to Launchpad
                            </button>
                        </div>

                        <p className="text-xs text-gray-400 mt-6">
                            Deep fit analysis uses AI to compare your profile against university requirements, majors, culture, and more.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    const categoryConfig = fitColors[fitAnalysis.fit_category] || fitColors.TARGET;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto">
            <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl my-8 flex flex-col max-h-[90vh]">

                {/* Modal Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-100 bg-white rounded-t-2xl sticky top-0 z-10">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                            <span className="text-3xl">✨</span>
                            Fit Analysis Report
                        </h2>
                        <p className="text-gray-500 mt-1">Strategic insights for <span className="font-semibold text-gray-800">{uniName}</span></p>
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={printAnalysis}
                            className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-colors hidden md:block"
                            title="Print Report"
                        >
                            <PrinterIcon className="h-6 w-6" />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                        >
                            <XMarkIcon className="h-6 w-6" />
                        </button>
                    </div>
                </div>

                {/* Modal Content - Scrollable */}
                <div className="overflow-y-auto p-6 md:p-8 space-y-8 print:overflow-visible">

                    {/* 1. Top Level Match Score */}
                    <div className={`p-6 rounded-xl border ${categoryConfig.border} ${categoryConfig.bg} flex flex-col md:flex-row items-center justify-between gap-6`}>
                        <div className="flex items-center gap-6">
                            <div className="relative">
                                <svg className="w-24 h-24 transform -rotate-90">
                                    <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/50" />
                                    <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="8" fill="transparent"
                                        strokeDasharray={251.2}
                                        strokeDashoffset={251.2 - (251.2 * fitAnalysis.match_percentage / 100)}
                                        className={categoryConfig.text}
                                    />
                                </svg>
                                <span className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-xl font-bold">
                                    {fitAnalysis.match_percentage}%
                                </span>
                            </div>
                            <div>
                                <h3 className={`text-2xl font-bold ${categoryConfig.text}`}>
                                    {fitAnalysis.fit_category === 'SUPER_REACH' ? 'Super Reach' :
                                        fitAnalysis.fit_category === 'REACH' ? 'Reach' :
                                            fitAnalysis.fit_category === 'TARGET' ? 'Target' : 'Safety'}
                                </h3>
                                <p className="text-gray-600 mt-1 max-w-lg">
                                    Based on your academic profile, test scores, and major selection.
                                </p>
                            </div>
                        </div>

                        {/* Factors Mini-Grid */}
                        {fitAnalysis.factors && fitAnalysis.factors.length > 0 && (
                            <div className="flex gap-2">
                                {fitAnalysis.factors.slice(0, 3).map((f, i) => (
                                    <div key={i} className="bg-white/60 p-2 rounded shadow-sm border border-white/50 text-center w-20">
                                        <div className="text-[10px] uppercase text-gray-500 font-bold mb-1 truncate">{f.name}</div>
                                        <div className="text-lg font-bold text-gray-800">{f.score}/{f.max}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* 2. Executive Summary / Explanation */}
                    {fitAnalysis.explanation && (
                        <div className="bg-white">
                            <h3 className="text-lg font-bold text-gray-900 mb-3 flex items-center gap-2">
                                <LightBulbIcon className="h-5 w-5 text-yellow-500" /> Executive Summary
                            </h3>
                            <div className="prose prose-blue max-w-none text-gray-600 bg-gray-50 p-5 rounded-lg border border-gray-100">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {fitAnalysis.explanation}
                                </ReactMarkdown>
                            </div>
                        </div>
                    )}

                    {/* 3. Strategic Recommendations (The Action Plan) */}
                    {fitAnalysis.recommendations && fitAnalysis.recommendations.length > 0 && (
                        <div>
                            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                                <FlagIcon className="h-5 w-5 text-blue-600" /> Strategic Action Plan
                            </h3>
                            <div className="grid grid-cols-1 gap-4">
                                {fitAnalysis.recommendations.map((rec, idx) => (
                                    <div key={idx} className="bg-white rounded-xl border border-blue-100 shadow-sm p-5 hover:shadow-md transition-shadow relative overflow-hidden group">
                                        <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
                                        <div className="flex gap-4">
                                            <div className="bg-blue-50 text-blue-600 rounded-full w-8 h-8 flex items-center justify-center flex-shrink-0 font-bold border border-blue-100">
                                                {idx + 1}
                                            </div>
                                            <div>
                                                <h4 className="font-bold text-gray-900 text-lg mb-1">{typeof rec === 'object' ? rec.action : rec}</h4>
                                                {typeof rec === 'object' && (
                                                    <div className="text-sm text-gray-600 space-y-2 mt-2">
                                                        <p><span className="font-semibold text-blue-700">Why it matters:</span> {rec.impact}</p>
                                                        <p className="bg-gray-50 p-2 rounded text-gray-500 italic border-l-2 border-gray-300">
                                                            "{rec.school_specific_context}"
                                                        </p>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 4. Gap Analysis (Strengths vs Weaknesses) */}
                    {fitAnalysis.gap_analysis && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="bg-green-50 rounded-xl p-5 border border-green-100">
                                <h4 className="font-bold text-green-900 mb-4 flex items-center gap-2 text-lg">
                                    <ChartBarIcon className="h-5 w-5" /> Your Competitive Advantage
                                </h4>
                                <ul className="space-y-3">
                                    {fitAnalysis.gap_analysis.student_strengths?.map((str, i) => (
                                        <li key={i} className="flex gap-2 items-start text-green-800 text-sm">
                                            <span className="text-green-500 mt-0.5">✓</span>
                                            {str}
                                        </li>
                                    )) || <li className="text-green-800 italic">No specific strengths listed</li>}
                                </ul>
                            </div>
                            <div className="bg-orange-50 rounded-xl p-5 border border-orange-100">
                                <h4 className="font-bold text-orange-900 mb-4 flex items-center gap-2 text-lg">
                                    <ExclamationTriangleIcon className="h-5 w-5" /> Gaps to Address
                                </h4>
                                <div className="space-y-4 text-sm text-orange-900">
                                    <div>
                                        <span className="text-xs font-bold uppercase tracking-wider text-orange-600 mb-1 block">Primary Gap</span>
                                        <p>{fitAnalysis.gap_analysis.primary_gap || 'None identified'}</p>
                                    </div>
                                    {fitAnalysis.gap_analysis.secondary_gap && (
                                        <div>
                                            <span className="text-xs font-bold uppercase tracking-wider text-orange-600 mb-1 block">Secondary Focus</span>
                                            <p>{fitAnalysis.gap_analysis.secondary_gap}</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* 5. Essay Strategy & Hooks */}
                    {fitAnalysis.essay_angles && fitAnalysis.essay_angles.length > 0 && (
                        <div>
                            <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                                <PencilSquareIcon className="h-5 w-5 text-purple-600" /> Essay Strategy
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {fitAnalysis.essay_angles.map((angle, idx) => (
                                    <div key={idx} className="bg-purple-50 rounded-xl p-4 border border-purple-100 hover:shadow-md transition-shadow">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="bg-purple-200 text-purple-700 text-xs font-bold px-2 py-1 rounded">Angle {idx + 1}</span>
                                        </div>
                                        <h5 className="font-bold text-gray-900 mb-2 leading-tight">{angle.angle}</h5>

                                        <div className="space-y-2 mt-3">
                                            <div className="bg-white/60 p-2 rounded">
                                                <span className="text-xs font-bold text-purple-600 block mb-1">Your Hook</span>
                                                <p className="text-xs text-gray-600 leading-snug">{angle.student_hook}</p>
                                            </div>
                                            <div className="bg-white/60 p-2 rounded">
                                                <span className="text-xs font-bold text-blue-600 block mb-1">School Correlation</span>
                                                <p className="text-xs text-gray-600 leading-snug">{angle.school_hook}</p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 6. Timeline & Academic Strategy */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Timeline */}
                        {fitAnalysis.application_timeline && (
                            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
                                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                                    <CalendarIcon className="h-5 w-5 text-indigo-500" /> Timeline Strategy
                                </h3>

                                <div className="space-y-4">
                                    <div className="flex items-center justify-between bg-indigo-50 p-3 rounded-lg border border-indigo-100">
                                        <span className="text-sm font-medium text-gray-700">Recommended Plan</span>
                                        <span className="text-sm font-bold text-indigo-700">{fitAnalysis.application_timeline.recommended_plan}</span>
                                    </div>

                                    <div>
                                        <h5 className="text-xs font-bold text-gray-500 uppercase mb-1">Rationale</h5>
                                        <p className="text-sm text-gray-600">{fitAnalysis.application_timeline.rationale}</p>
                                    </div>

                                    {fitAnalysis.application_timeline.deadline && (
                                        <div className="flex items-center gap-2 text-sm text-indigo-600 font-medium">
                                            <CalendarIcon className="h-4 w-4" />
                                            Target Deadline: {fitAnalysis.application_timeline.deadline}
                                        </div>
                                    )}

                                    {/* Demonstrated Interest */}
                                    {fitAnalysis.demonstrated_interest_tips && fitAnalysis.demonstrated_interest_tips.length > 0 && (
                                        <div className="pt-3 border-t border-gray-100">
                                            <h5 className="text-xs font-bold text-gray-500 uppercase mb-2">Interest Optimization</h5>
                                            <ul className="text-xs text-gray-600 space-y-1 list-disc list-inside">
                                                {fitAnalysis.demonstrated_interest_tips.map((tip, i) => (
                                                    <li key={i}>{tip}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Academics */}
                        {(fitAnalysis.major_strategy || fitAnalysis.test_strategy) && (
                            <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
                                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                                    <AcademicCapIcon className="h-5 w-5 text-teal-500" /> Academic Strategy
                                </h3>

                                <div className="space-y-5">
                                    {/* Major */}
                                    {fitAnalysis.major_strategy && (
                                        <div>
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm font-semibold text-gray-800">{fitAnalysis.major_strategy.intended_major}</span>
                                                {fitAnalysis.major_strategy.is_impacted ?
                                                    <span className="text-[10px] font-bold bg-orange-100 text-orange-700 px-2 py-0.5 rounded">IMPACTED</span> :
                                                    <span className="text-[10px] font-bold bg-teal-100 text-teal-700 px-2 py-0.5 rounded">OPEN</span>
                                                }
                                            </div>
                                            <p className="text-xs text-gray-600 mb-2">
                                                Backup: <span className="font-medium">{fitAnalysis.major_strategy.backup_major || 'None needed'}</span>
                                            </p>
                                        </div>
                                    )}

                                    {/* Testing */}
                                    {fitAnalysis.test_strategy && (
                                        <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                                            <h5 className="text-xs font-bold text-gray-500 uppercase mb-2">Testing Strategy</h5>
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm font-bold text-gray-900">{fitAnalysis.test_strategy.recommendation}</span>
                                                {/* <span className="text-xs text-gray-500">Mid 50%: {fitAnalysis.test_strategy.school_sat_middle_50}</span> */}
                                            </div>
                                            <p className="text-xs text-gray-600 italic">
                                                "{fitAnalysis.test_strategy.rationale}"
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* 7. Financials / Scholarships */}
                    {fitAnalysis.scholarship_matches && fitAnalysis.scholarship_matches.length > 0 && (
                        <div className="bg-yellow-50 rounded-xl border border-yellow-200 overflow-hidden">
                            <div className="px-6 py-4 border-b border-yellow-100 flex items-center gap-2">
                                <CurrencyDollarIcon className="h-6 w-6 text-yellow-600" />
                                <h3 className="text-lg font-bold text-yellow-900">Scholarship Matches</h3>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left">
                                    <thead className="text-xs text-yellow-800 uppercase bg-yellow-100/50">
                                        <tr>
                                            <th className="px-6 py-3">Scholarship Name</th>
                                            <th className="px-6 py-3">Amount</th>
                                            <th className="px-6 py-3">Deadline</th>
                                            <th className="px-6 py-3 hidden md:table-cell">Requirements</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-yellow-100">
                                        {fitAnalysis.scholarship_matches.map((sch, i) => (
                                            <tr key={i} className="hover:bg-yellow-100/30">
                                                <td className="px-6 py-4 font-medium text-gray-900">{sch.name}</td>
                                                <td className="px-6 py-4 text-gray-700">{sch.amount}</td>
                                                <td className="px-6 py-4 text-gray-700">{sch.deadline}</td>
                                                <td className="px-6 py-4 text-gray-500 text-xs hidden md:table-cell max-w-xs truncate">{sch.requirements}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* 8. Red Flags */}
                    {fitAnalysis.red_flags_to_avoid && fitAnalysis.red_flags_to_avoid.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
                            <h3 className="text-lg font-bold text-red-900 mb-4 flex items-center gap-2">
                                <ExclamationTriangleIcon className="h-5 w-5" /> Risk Factors
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {fitAnalysis.red_flags_to_avoid.map((flag, i) => (
                                    <div key={i} className="bg-white/80 p-3 rounded-lg border border-red-100 flex gap-3 items-start">
                                        <span className="text-red-500 font-bold mt-0.5">✕</span>
                                        <p className="text-sm text-red-800">{flag}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="h-4"></div> {/* Bottom spacer */}
                </div>
            </div>
        </div>
    );
};

export default FitAnalysisModal;
