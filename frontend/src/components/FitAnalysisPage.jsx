import React, { useState, useEffect, useCallback } from 'react';
import {
    ArrowLeftIcon,
    SparklesIcon,
    ChartBarIcon,
    DocumentTextIcon,
    CalendarIcon,
    AcademicCapIcon,
    CurrencyDollarIcon,
    LightBulbIcon,
    ExclamationTriangleIcon,
    CheckCircleIcon,
    ArrowPathIcon,
    BeakerIcon,
    BookOpenIcon,
    ClipboardDocumentCheckIcon,
    PhotoIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { generateFitInfographic, checkCredits, deductCredit } from '../services/api';

// ============================================================================
// FIT ANALYSIS PAGE - Complete display of all fit analysis data
// ============================================================================
const FitAnalysisPage = ({ college, onBack }) => {
    const { currentUser } = useAuth();
    const [infographicUrl, setInfographicUrl] = useState(null);
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationError, setGenerationError] = useState(null);
    const [hasCredits, setHasCredits] = useState(false);

    // Check credits on mount
    useEffect(() => {
        const checkUserCredits = async () => {
            if (currentUser?.email) {
                const result = await checkCredits(currentUser.email, 1);
                setHasCredits(result.has_credits === true);
            }
        };
        checkUserCredits();
    }, [currentUser?.email]);

    // Generate infographic
    const handleGenerateInfographic = useCallback(async (forceRegenerate = false) => {
        if (!currentUser?.email || !college?.university_id) return;

        if (forceRegenerate) {
            const creditCheck = await checkCredits(currentUser.email, 1);
            if (!creditCheck.has_credits) {
                setGenerationError('Insufficient credits. Regenerating costs 1 credit.');
                return;
            }
            const confirmed = window.confirm('Regenerating will use 1 credit. Continue?');
            if (!confirmed) return;
            await deductCredit(currentUser.email, 1, 'infographic_regeneration');
        }

        setIsGenerating(true);
        setGenerationError(null);

        try {
            const result = await generateFitInfographic(currentUser.email, college.university_id, forceRegenerate);
            if (result.success && result.infographic_url) {
                setInfographicUrl(result.infographic_url);
            } else {
                setGenerationError(result.error || 'Failed to generate infographic');
            }
        } catch (err) {
            setGenerationError(err.message);
        } finally {
            setIsGenerating(false);
        }
    }, [currentUser?.email, college?.university_id]);

    // Auto-load infographic on mount
    useEffect(() => {
        if (college?.fit_analysis && currentUser?.email && !infographicUrl && !isGenerating) {
            // Check if infographic URL already exists in the data
            if (college.infographic_url) {
                setInfographicUrl(college.infographic_url);
            } else {
                handleGenerateInfographic(false);
            }
        }
    }, [college, currentUser?.email, infographicUrl, isGenerating, handleGenerateInfographic]);

    if (!college || !college.fit_analysis) {
        return (
            <div className="text-center py-12 text-gray-400">
                <SparklesIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No fit analysis available.</p>
            </div>
        );
    }

    const fitAnalysis = college.fit_analysis;

    // Parse JSON strings if needed (backend sometimes sends stringified JSON)
    const parseIfString = (data) => {
        if (typeof data === 'string') {
            try {
                return JSON.parse(data);
            } catch {
                return data;
            }
        }
        return data;
    };

    const factors = parseIfString(fitAnalysis.factors) || [];
    const recommendations = parseIfString(fitAnalysis.recommendations) || [];
    const gapAnalysis = parseIfString(fitAnalysis.gap_analysis) || {};
    const essayAngles = parseIfString(fitAnalysis.essay_angles) || [];
    const applicationTimeline = parseIfString(fitAnalysis.application_timeline) || {};
    const scholarshipMatches = parseIfString(fitAnalysis.scholarship_matches) || [];
    const testStrategy = parseIfString(fitAnalysis.test_strategy) || {};
    const majorStrategy = parseIfString(fitAnalysis.major_strategy) || {};
    const demonstratedInterestTips = parseIfString(fitAnalysis.demonstrated_interest_tips) || [];
    const redFlags = parseIfString(fitAnalysis.red_flags_to_avoid) || [];

    // Category badge color
    const getCategoryStyle = (category) => {
        const styles = {
            'TARGET': 'bg-green-100 text-green-800 border-green-200',
            'REACH': 'bg-amber-100 text-amber-800 border-amber-200',
            'SUPER_REACH': 'bg-red-100 text-red-800 border-red-200',
            'SAFETY': 'bg-blue-100 text-blue-800 border-blue-200'
        };
        return styles[category] || 'bg-gray-100 text-gray-800';
    };

    return (
        <div className="bg-gray-50 min-h-screen">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
                <button
                    onClick={onBack}
                    className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-2"
                >
                    <ArrowLeftIcon className="h-5 w-5" />
                    Back to Launchpad
                </button>
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">{college.university_name}</h1>
                        <p className="text-gray-500">{college.location}</p>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className={`px-4 py-2 rounded-full text-sm font-bold border ${getCategoryStyle(fitAnalysis.fit_category || college.soft_fit_category)}`}>
                            {(fitAnalysis.fit_category || college.soft_fit_category || 'UNKNOWN').replace('_', ' ')}
                        </span>
                        <div className="text-center">
                            <div className="text-3xl font-bold text-purple-600">{fitAnalysis.match_score || fitAnalysis.match_percentage || 0}</div>
                            <div className="text-xs text-gray-500">Match Score</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">

                {/* Infographic Section */}
                <div className="bg-gradient-to-br from-purple-50 via-indigo-50 to-blue-50 rounded-2xl overflow-hidden border border-purple-100 shadow-sm">
                    {infographicUrl ? (
                        <div>
                            <img
                                src={infographicUrl}
                                alt={`Fit Analysis Infographic for ${college.university_name}`}
                                className="w-full h-auto max-h-[800px] object-contain bg-white"
                            />
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
                                    <a href="/pricing" className="flex items-center gap-1 text-sm text-amber-600 hover:text-amber-700">
                                        <CurrencyDollarIcon className="h-4 w-4" />
                                        Purchase credits to regenerate
                                    </a>
                                )}
                            </div>
                        </div>
                    ) : isGenerating ? (
                        <div className="p-12 text-center">
                            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg animate-pulse">
                                <PhotoIcon className="h-10 w-10 text-white" />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">Generating Your Personalized Infographic...</h3>
                            <p className="text-gray-600">This may take 15-30 seconds.</p>
                            <div className="flex justify-center mt-4">
                                <ArrowPathIcon className="h-5 w-5 animate-spin text-purple-600" />
                            </div>
                        </div>
                    ) : generationError ? (
                        <div className="p-8 text-center">
                            <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-3" />
                            <p className="text-red-600 mb-4">{generationError}</p>
                            <button
                                onClick={() => handleGenerateInfographic(false)}
                                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                            >
                                Try Again
                            </button>
                        </div>
                    ) : null}
                </div>

                {/* Executive Summary */}
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <h2 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-purple-500" />
                        Executive Summary
                    </h2>
                    <p className="text-gray-700 leading-relaxed">{fitAnalysis.explanation}</p>
                </div>

                {/* Factor Breakdown */}
                {factors.length > 0 && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <ChartBarIcon className="h-5 w-5 text-indigo-500" />
                            Factor Breakdown
                        </h2>
                        <div className="space-y-4">
                            {factors.map((factor, idx) => (
                                <div key={idx}>
                                    <div className="flex justify-between items-center mb-1">
                                        <span className="font-medium text-gray-700">{factor.name}</span>
                                        <span className={`font-bold ${factor.score >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                            {factor.score >= 0 ? '+' : ''}{factor.score}/{factor.max}
                                        </span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                                        <div
                                            className={`h-2 rounded-full ${factor.score >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                                            style={{ width: `${Math.min(100, Math.abs(factor.score) / Math.abs(factor.max) * 100)}%` }}
                                        />
                                    </div>
                                    <p className="text-sm text-gray-500">{factor.detail}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Gap Analysis */}
                {(gapAnalysis.primary_gap || gapAnalysis.student_strengths) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-red-50 rounded-xl p-5 border border-red-100">
                            <h3 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                                <ExclamationTriangleIcon className="h-5 w-5" />
                                Areas to Address
                            </h3>
                            <ul className="space-y-2 text-sm text-red-700">
                                {gapAnalysis.primary_gap && <li>• <strong>Primary:</strong> {gapAnalysis.primary_gap}</li>}
                                {gapAnalysis.secondary_gap && <li>• <strong>Secondary:</strong> {gapAnalysis.secondary_gap}</li>}
                            </ul>
                        </div>
                        <div className="bg-green-50 rounded-xl p-5 border border-green-100">
                            <h3 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
                                <CheckCircleIcon className="h-5 w-5" />
                                Your Strengths
                            </h3>
                            <ul className="space-y-1 text-sm text-green-700">
                                {(gapAnalysis.student_strengths || []).map((s, i) => (
                                    <li key={i}>• {s}</li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )}

                {/* Action Plan / Recommendations */}
                {recommendations.length > 0 && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <LightBulbIcon className="h-5 w-5 text-amber-500" />
                            Strategic Action Plan
                        </h2>
                        <div className="space-y-4">
                            {recommendations.map((rec, idx) => (
                                <div key={idx} className="bg-amber-50 p-4 rounded-lg border border-amber-100">
                                    <div className="flex items-start gap-3">
                                        <span className="flex-shrink-0 w-8 h-8 bg-amber-200 text-amber-800 rounded-full flex items-center justify-center font-bold text-sm">
                                            {idx + 1}
                                        </span>
                                        <div className="flex-1">
                                            <p className="text-gray-800 font-medium">{rec.action}</p>
                                            {rec.school_specific_context && (
                                                <p className="text-sm text-gray-600 mt-1"><em>{rec.school_specific_context}</em></p>
                                            )}
                                            <div className="flex flex-wrap gap-2 mt-2">
                                                {rec.addresses_gap && (
                                                    <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">
                                                        Addresses: {rec.addresses_gap}
                                                    </span>
                                                )}
                                                {rec.timeline && (
                                                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium flex items-center gap-1">
                                                        <CalendarIcon className="h-3 w-3" />
                                                        {rec.timeline}
                                                    </span>
                                                )}
                                                {rec.impact && (
                                                    <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                                                        Impact: {rec.impact}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Test Strategy */}
                {testStrategy.recommendation && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <BeakerIcon className="h-5 w-5 text-blue-500" />
                            Test Strategy
                        </h2>
                        <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                            <div className="flex items-center gap-4 mb-3">
                                <span className={`px-4 py-2 rounded-full text-sm font-bold ${testStrategy.recommendation === 'Submit' ? 'bg-green-100 text-green-800' :
                                    testStrategy.recommendation === 'Test Optional' ? 'bg-amber-100 text-amber-800' :
                                        'bg-gray-100 text-gray-800'
                                    }`}>
                                    {testStrategy.recommendation}
                                </span>
                                {testStrategy.student_score_position && (
                                    <span className="text-sm text-gray-600">
                                        Your score is <strong>{testStrategy.student_score_position}</strong> the middle 50%
                                    </span>
                                )}
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                                {testStrategy.student_sat && (
                                    <div className="text-center">
                                        <div className="text-xl font-bold text-blue-700">{testStrategy.student_sat}</div>
                                        <div className="text-xs text-gray-500">Your SAT</div>
                                    </div>
                                )}
                                {testStrategy.student_act && (
                                    <div className="text-center">
                                        <div className="text-xl font-bold text-blue-700">{testStrategy.student_act}</div>
                                        <div className="text-xs text-gray-500">Your ACT</div>
                                    </div>
                                )}
                                {testStrategy.school_sat_middle_50 && (
                                    <div className="text-center">
                                        <div className="text-lg font-bold text-gray-700">{testStrategy.school_sat_middle_50}</div>
                                        <div className="text-xs text-gray-500">School SAT Range</div>
                                    </div>
                                )}
                                {testStrategy.school_act_middle_50 && (
                                    <div className="text-center">
                                        <div className="text-lg font-bold text-gray-700">{testStrategy.school_act_middle_50}</div>
                                        <div className="text-xs text-gray-500">School ACT Range</div>
                                    </div>
                                )}
                            </div>
                            <p className="text-sm text-gray-700">{testStrategy.rationale}</p>
                            {testStrategy.school_submission_rate && (
                                <p className="text-xs text-gray-500 mt-2">
                                    {testStrategy.school_submission_rate}% of applicants submit scores
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {/* Major Strategy */}
                {majorStrategy.intended_major && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <BookOpenIcon className="h-5 w-5 text-purple-500" />
                            Major Strategy
                        </h2>
                        <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                <div>
                                    <span className="text-xs text-gray-500">Intended Major</span>
                                    <div className="font-bold text-purple-800">{majorStrategy.intended_major}</div>
                                </div>
                                {majorStrategy.college_within_university && (
                                    <div>
                                        <span className="text-xs text-gray-500">College/School</span>
                                        <div className="font-medium text-gray-700">{majorStrategy.college_within_university}</div>
                                    </div>
                                )}
                            </div>
                            <div className="flex flex-wrap gap-2 mb-3">
                                {majorStrategy.is_available !== undefined && (
                                    <span className={`px-2 py-1 rounded text-xs font-medium ${majorStrategy.is_available ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                        {majorStrategy.is_available ? '✓ Available' : '✗ Not Available'}
                                    </span>
                                )}
                                {majorStrategy.is_impacted && (
                                    <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">
                                        ⚠ Impacted Major
                                    </span>
                                )}
                                {majorStrategy.internal_transfer_difficulty && (
                                    <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                        Transfer: {majorStrategy.internal_transfer_difficulty}
                                    </span>
                                )}
                            </div>
                            {majorStrategy.backup_major && (
                                <p className="text-sm text-gray-700 mb-2">
                                    <strong>Backup Major:</strong> {majorStrategy.backup_major}
                                </p>
                            )}
                            {majorStrategy.strategic_tip && (
                                <p className="text-sm text-purple-700 bg-purple-100 p-2 rounded">
                                    💡 {majorStrategy.strategic_tip}
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {/* Essay Strategies */}
                {essayAngles.length > 0 && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <DocumentTextIcon className="h-5 w-5 text-blue-500" />
                            Essay Strategies
                        </h2>
                        <div className="space-y-4">
                            {essayAngles.map((essay, idx) => (
                                <div key={idx} className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                                    {essay.essay_prompt && (
                                        <p className="text-sm text-blue-800 font-medium mb-2 italic">"{essay.essay_prompt}"</p>
                                    )}
                                    <p className="text-gray-700 mb-2"><strong>Angle:</strong> {essay.angle}</p>
                                    {essay.student_hook && (
                                        <p className="text-sm text-gray-600"><strong>Your Hook:</strong> {essay.student_hook}</p>
                                    )}
                                    {essay.school_hook && (
                                        <p className="text-sm text-gray-600"><strong>School Connection:</strong> {essay.school_hook}</p>
                                    )}
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {essay.word_limit && (
                                            <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded">
                                                {essay.word_limit} words
                                            </span>
                                        )}
                                    </div>
                                    {essay.tip && (
                                        <p className="text-xs text-blue-600 mt-2 bg-blue-100 p-2 rounded">
                                            💡 Tip: {essay.tip}
                                        </p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Application Timeline */}
                {applicationTimeline.recommended_plan && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <CalendarIcon className="h-5 w-5 text-orange-500" />
                            Application Timeline
                        </h2>
                        <div className="bg-orange-50 p-4 rounded-lg border border-orange-100">
                            <div className="flex items-center gap-4 mb-3">
                                <div className="text-2xl font-bold text-orange-600">{applicationTimeline.recommended_plan}</div>
                                {applicationTimeline.is_binding && (
                                    <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-bold">BINDING</span>
                                )}
                            </div>
                            <p className="text-sm text-gray-700 mb-3">{applicationTimeline.rationale}</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {applicationTimeline.deadline && (
                                    <div className="bg-white p-3 rounded-lg">
                                        <span className="text-xs text-gray-500">Application Deadline</span>
                                        <div className="font-bold text-gray-800">{applicationTimeline.deadline}</div>
                                    </div>
                                )}
                                {applicationTimeline.financial_aid_deadline && (
                                    <div className="bg-white p-3 rounded-lg">
                                        <span className="text-xs text-gray-500">Financial Aid Deadline</span>
                                        <div className="font-bold text-gray-800">{applicationTimeline.financial_aid_deadline}</div>
                                    </div>
                                )}
                            </div>
                            {applicationTimeline.key_milestones && applicationTimeline.key_milestones.length > 0 && (
                                <div className="mt-4">
                                    <span className="text-xs text-gray-500 font-medium">Key Milestones</span>
                                    <ul className="mt-2 space-y-1">
                                        {applicationTimeline.key_milestones.map((m, i) => (
                                            <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                                                <CheckCircleIcon className="h-4 w-4 text-orange-500" />
                                                {m}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Scholarship Matches */}
                {scholarshipMatches.length > 0 && (
                    <div className="bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl p-6 border border-emerald-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <CurrencyDollarIcon className="h-5 w-5 text-emerald-600" />
                            Scholarship Matches
                            <span className="ml-2 px-2 py-0.5 bg-emerald-200 text-emerald-800 rounded-full text-xs font-medium">
                                {scholarshipMatches.length} found
                            </span>
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {scholarshipMatches.map((sch, idx) => (
                                <div key={idx} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100">
                                    <h4 className="font-semibold text-gray-900">{sch.name}</h4>
                                    <div className="mt-2">
                                        <span className="inline-block px-3 py-1 bg-emerald-100 text-emerald-800 rounded text-sm font-bold">
                                            {sch.amount}
                                        </span>
                                    </div>
                                    {sch.match_reason && (
                                        <p className="text-sm text-gray-600 mt-2">{sch.match_reason}</p>
                                    )}
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {sch.deadline && (
                                            <span className="text-xs text-orange-600 bg-orange-50 px-2 py-0.5 rounded">
                                                Deadline: {sch.deadline}
                                            </span>
                                        )}
                                        {sch.application_method && (
                                            <span className="text-xs text-gray-600 bg-gray-100 px-2 py-0.5 rounded">
                                                {sch.application_method}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Demonstrated Interest Tips */}
                {demonstratedInterestTips.length > 0 && (
                    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                        <h2 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                            <ClipboardDocumentCheckIcon className="h-5 w-5 text-indigo-500" />
                            Demonstrated Interest Tips
                        </h2>
                        <ul className="space-y-2">
                            {demonstratedInterestTips.map((tip, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                    <CheckCircleIcon className="h-4 w-4 text-indigo-500 mt-0.5 flex-shrink-0" />
                                    {tip}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Red Flags to Avoid */}
                {redFlags.length > 0 && (
                    <div className="bg-red-50 rounded-xl p-6 border border-red-100">
                        <h2 className="font-semibold text-red-800 mb-4 flex items-center gap-2">
                            <ExclamationTriangleIcon className="h-5 w-5" />
                            Red Flags to Avoid
                        </h2>
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
        </div>
    );
};

export default FitAnalysisPage;
