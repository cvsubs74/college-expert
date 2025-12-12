import React, { useState, useEffect, useMemo } from 'react';
import {
    AcademicCapIcon,
    ChartBarIcon,
    SparklesIcon,
    ArrowTrendingUpIcon,
    ShieldCheckIcon
} from '@heroicons/react/24/outline';

/**
 * FitVisualizer Component
 * Interactive tool to understand how the fit calculation algorithm works.
 * Shows the difference between "Fair Mode" (current) and "Strict Mode" (legacy).
 */
const FitVisualizer = () => {
    // Student State
    const [student, setStudent] = useState({
        gpa: 3.9,
        testScore: 1450,
        apCount: 6,
        leadership: true,
        testOptional: false
    });

    // University State
    const [uni, setUni] = useState({
        name: "Example University",
        acceptanceRate: 15,
        gpa75: 4.0,
        sat75: 1500,
        testOptionalAllowed: true
    });

    const [mode, setMode] = useState('fair'); // 'fair' or 'strict'
    const [result, setResult] = useState(null);

    // Simulation Logic
    useEffect(() => {
        calculateFit();
    }, [student, uni, mode]);

    const calculateFit = () => {
        let score = 0;
        let maxScore = 0;
        let factors = [];
        let category = "";

        if (mode === 'strict') {
            // STRICT MODE (Legacy - has issues)
            maxScore = 150;

            // 1. GPA (Strict: Needs +0.1 buffer)
            let gpaScore = 5;
            if (student.gpa >= uni.gpa75 + 0.1) gpaScore = 40;
            else if (student.gpa >= uni.gpa75) gpaScore = 36;
            else if (student.gpa >= uni.gpa75 - 0.2) gpaScore = 28;
            else if (student.gpa >= uni.gpa75 - 0.5) gpaScore = 20;
            score += gpaScore;
            factors.push({ name: "GPA", score: gpaScore, max: 40 });

            // 2. Test Scores (Strict: Harsh penalty for Test Opt)
            let testScore = 0;
            if (!student.testOptional) {
                if (student.testScore >= uni.sat75) testScore = 25;
                else if (student.testScore >= uni.sat75 - 100) testScore = 20;
                else testScore = 12;
            } else {
                testScore = 15; // Capped at 60%
            }
            score += testScore;
            factors.push({ name: "Testing", score: testScore, max: 25 });

            // 3. Acceptance Rate (Strict: Penalizes score for selectivity)
            let rateScore = 2;
            if (uni.acceptanceRate > 60) rateScore = 25;
            else if (uni.acceptanceRate > 40) rateScore = 20;
            else if (uni.acceptanceRate > 25) rateScore = 16;
            else if (uni.acceptanceRate > 15) rateScore = 12;
            else if (uni.acceptanceRate > 10) rateScore = 8;
            score += rateScore;
            factors.push({ name: "Selectivity Score", score: rateScore, max: 25 });

            // Other Factors (Simplified)
            let rigor = Math.min(20, student.apCount * 1.2);
            score += rigor;
            factors.push({ name: "Rigor", score: Math.floor(rigor), max: 20 });

            let activities = student.leadership ? 15 : 5;
            score += activities;
            factors.push({ name: "Activities", score: activities, max: 15 });

            score += 15; // Major fit assumed perfect
            factors.push({ name: "Major", score: 15, max: 15 });

            // Strict Categorization
            let pct = (score / maxScore) * 100;
            if (pct >= 60) category = 'SAFETY';
            else if (pct >= 50) category = 'TARGET';
            else if (pct >= 35) category = 'REACH';
            else category = 'SUPER REACH';

            // Strict Guard Rails
            if (uni.acceptanceRate < 7) category = 'SUPER REACH';
            else if (uni.acceptanceRate < 15 && category === 'SAFETY') category = 'REACH';

        } else {
            // FAIR MODE (Current - balanced approach)
            maxScore = 100;

            // 1. GPA (Fair: No buffer, normalized)
            let gpaScore = 10;
            if (student.gpa >= uni.gpa75) gpaScore = 40;
            else if (student.gpa >= uni.gpa75 - 0.2) gpaScore = 35;
            else if (student.gpa >= uni.gpa75 - 0.5) gpaScore = 25;
            score += gpaScore;
            factors.push({ name: "GPA", score: gpaScore, max: 40 });

            // 2. Test Scores (Fair: Test Opt handled smartly)
            let testScore = 0;
            if (!student.testOptional) {
                if (student.testScore >= uni.sat75) testScore = 25;
                else if (student.testScore >= uni.sat75 - 100) testScore = 22;
                else testScore = 15;
            } else {
                // If GPA is strong, assume strong student
                testScore = gpaScore >= 35 ? 22 : 15;
            }
            score += testScore;
            factors.push({ name: "Testing", score: testScore, max: 25 });

            // 3. Rigor (Fair)
            let rigor = Math.min(15, student.apCount * 2.5);
            score += rigor;
            factors.push({ name: "Rigor", score: Math.floor(rigor), max: 15 });

            // 4. Activities (Fair)
            let activities = student.leadership ? 20 : 10;
            score += activities;
            factors.push({ name: "Activities", score: activities, max: 20 });

            // Calculate Percent
            let pct = (score / maxScore) * 100;

            // Categorize based on score first
            if (pct >= 85) category = 'SAFETY';
            else if (pct >= 70) category = 'TARGET';
            else if (pct >= 50) category = 'REACH';
            else category = 'SUPER REACH';

            // Apply Reality Check (Cap category, don't reduce score)
            if (uni.acceptanceRate < 10 && (category === 'SAFETY' || category === 'TARGET')) category = 'REACH';
            if (uni.acceptanceRate < 25 && category === 'SAFETY') category = 'TARGET';
        }

        setResult({ score, maxScore, factors, category, pct: Math.round((score / maxScore) * 100) });
    };

    const getCategoryColor = (cat) => {
        switch (cat) {
            case 'SAFETY': return 'bg-green-100 text-green-800 border-green-200';
            case 'TARGET': return 'bg-blue-100 text-blue-800 border-blue-200';
            case 'REACH': return 'bg-orange-100 text-orange-800 border-orange-200';
            default: return 'bg-red-100 text-red-800 border-red-200';
        }
    };

    const getCategoryEmoji = (cat) => {
        switch (cat) {
            case 'SAFETY': return '🛡️';
            case 'TARGET': return '🎯';
            case 'REACH': return '🔼';
            default: return '🚀';
        }
    };

    return (
        <div className="p-6 max-w-6xl mx-auto bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen font-sans">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-2">
                    <AcademicCapIcon className="w-8 h-8 text-indigo-600" />
                    College Fit Algorithm Explorer
                </h1>
                <p className="text-slate-600 mt-2">
                    Understand how we calculate your fit. Compare <strong>Fair Mode</strong> (current) vs <strong>Strict Mode</strong> (legacy).
                </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Controls */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 space-y-6">
                    {/* Mode Toggle */}
                    <div className="flex bg-slate-100 p-1 rounded-lg mb-6">
                        <button
                            onClick={() => setMode('strict')}
                            className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${mode === 'strict' ? 'bg-white shadow text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Strict Mode
                        </button>
                        <button
                            onClick={() => setMode('fair')}
                            className={`flex-1 py-2 rounded-md text-sm font-medium transition-all ${mode === 'fair' ? 'bg-white shadow text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                            Fair Mode ✨
                        </button>
                    </div>

                    {/* University Stats */}
                    <div>
                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">University Stats</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1">
                                    Acceptance Rate: <span className="font-bold text-indigo-600">{uni.acceptanceRate}%</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="90"
                                    value={uni.acceptanceRate}
                                    onChange={(e) => setUni({ ...uni, acceptanceRate: Number(e.target.value) })}
                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1">75th Percentile GPA</label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="3.0"
                                    max="4.0"
                                    value={uni.gpa75}
                                    onChange={(e) => setUni({ ...uni, gpa75: Number(e.target.value) })}
                                    className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1">75th Percentile SAT</label>
                                <input
                                    type="number"
                                    step="10"
                                    min="1000"
                                    max="1600"
                                    value={uni.sat75}
                                    onChange={(e) => setUni({ ...uni, sat75: Number(e.target.value) })}
                                    className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Student Stats */}
                    <div className="border-t pt-6">
                        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Your Stats</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1">
                                    Your GPA: <span className="font-bold text-indigo-600">{student.gpa}</span>
                                </label>
                                <input
                                    type="range"
                                    min="2.5"
                                    max="4.0"
                                    step="0.05"
                                    value={student.gpa}
                                    onChange={(e) => setStudent({ ...student, gpa: Number(e.target.value) })}
                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <label className="text-sm text-slate-700">Test Optional?</label>
                                <input
                                    type="checkbox"
                                    checked={student.testOptional}
                                    onChange={(e) => setStudent({ ...student, testOptional: e.target.checked })}
                                    className="w-5 h-5 accent-indigo-600 rounded"
                                />
                            </div>
                            {!student.testOptional && (
                                <div>
                                    <label className="block text-xs font-medium text-slate-600 mb-1">
                                        SAT Score: <span className="font-bold text-indigo-600">{student.testScore}</span>
                                    </label>
                                    <input
                                        type="range"
                                        min="800"
                                        max="1600"
                                        step="10"
                                        value={student.testScore}
                                        onChange={(e) => setStudent({ ...student, testScore: Number(e.target.value) })}
                                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                    />
                                </div>
                            )}
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1">
                                    AP Courses: <span className="font-bold text-indigo-600">{student.apCount}</span>
                                </label>
                                <input
                                    type="range"
                                    min="0"
                                    max="15"
                                    value={student.apCount}
                                    onChange={(e) => setStudent({ ...student, apCount: Number(e.target.value) })}
                                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                />
                            </div>
                            <div className="flex items-center justify-between">
                                <label className="text-sm text-slate-700">Leadership Roles?</label>
                                <input
                                    type="checkbox"
                                    checked={student.leadership}
                                    onChange={(e) => setStudent({ ...student, leadership: e.target.checked })}
                                    className="w-5 h-5 accent-indigo-600 rounded"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Results */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Main Result Card */}
                    <div className="bg-white p-8 rounded-xl shadow-lg border border-slate-200">
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h2 className="text-2xl font-bold text-slate-800 mb-1">Fit Analysis Result</h2>
                                <p className="text-slate-500">
                                    Algorithm: <span className="font-semibold capitalize">{mode} Mode</span>
                                    {mode === 'fair' && <span className="ml-2 text-indigo-600 text-xs">(Current)</span>}
                                </p>
                            </div>
                            <div className={`px-4 py-2 rounded-full border-2 text-lg font-bold flex items-center gap-2 ${getCategoryColor(result?.category)}`}>
                                <span>{getCategoryEmoji(result?.category)}</span>
                                {result?.category}
                            </div>
                        </div>

                        <div className="flex items-end gap-2 mb-2">
                            <span className="text-6xl font-bold text-slate-800">{result?.pct}%</span>
                            <span className="text-xl text-slate-400 mb-2">Match Score</span>
                        </div>

                        <div className="w-full bg-slate-100 rounded-full h-3 mb-8 overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${result?.pct >= 85 ? 'bg-green-500' : result?.pct >= 70 ? 'bg-blue-500' : result?.pct >= 50 ? 'bg-orange-500' : 'bg-red-500'}`}
                                style={{ width: `${result?.pct}%` }}
                            ></div>
                        </div>

                        {/* Factor Breakdown */}
                        <div className="grid grid-cols-2 gap-4">
                            {result?.factors.map((f, i) => (
                                <div key={i} className="bg-slate-50 p-4 rounded-lg border border-slate-100 relative overflow-hidden">
                                    <div
                                        className="absolute top-0 left-0 h-full bg-indigo-100 transition-all duration-500"
                                        style={{ width: `${(f.score / f.max) * 100}%` }}
                                    ></div>
                                    <div className="relative z-10 flex justify-between items-center">
                                        <span className="text-sm font-medium text-slate-700">{f.name}</span>
                                        <span className="font-bold text-slate-900">
                                            {f.score} <span className="text-slate-400 text-xs font-normal">/ {f.max}</span>
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Explanation */}
                    <div className={`p-6 rounded-xl border ${mode === 'fair' ? 'bg-indigo-50 border-indigo-100' : 'bg-orange-50 border-orange-100'}`}>
                        <h3 className={`font-bold mb-2 flex items-center gap-2 ${mode === 'fair' ? 'text-indigo-900' : 'text-orange-900'}`}>
                            <ArrowTrendingUpIcon className="w-5 h-5" />
                            Why this score?
                        </h3>
                        {mode === 'strict' ? (
                            <ul className="list-disc ml-5 space-y-2 text-orange-800 text-sm">
                                <li>Strict mode <strong>penalizes the score</strong> if the school has a low acceptance rate.</li>
                                <li>It requires your GPA to be <strong>0.1 higher</strong> than the 75th percentile for full points.</li>
                                <li>If Test Optional, it caps your testing score at 60%, even with a perfect GPA.</li>
                                <li className="font-semibold">Result: Most selective schools become REACH even for strong students.</li>
                            </ul>
                        ) : (
                            <ul className="list-disc ml-5 space-y-2 text-indigo-800 text-sm">
                                <li>Fair mode uses acceptance rate <strong>only as a ceiling</strong> for the category, not to lower your score.</li>
                                <li>Meeting the 75th percentile yields max points—no need to exceed it.</li>
                                <li>If Test Optional, it infers your potential based on GPA strength.</li>
                                <li className="font-semibold">Result: Strong students can achieve TARGET at selective schools.</li>
                            </ul>
                        )}
                    </div>

                    {/* Legend */}
                    <div className="bg-white p-4 rounded-xl border border-slate-200">
                        <h3 className="font-semibold text-slate-700 mb-3">Category Thresholds ({mode === 'fair' ? 'Fair' : 'Strict'} Mode)</h3>
                        <div className="grid grid-cols-4 gap-2 text-center text-sm">
                            <div className="bg-green-100 p-2 rounded-lg">
                                <div className="font-bold text-green-700">🛡️ SAFETY</div>
                                <div className="text-green-600">{mode === 'fair' ? '≥85%' : '≥60%'}</div>
                            </div>
                            <div className="bg-blue-100 p-2 rounded-lg">
                                <div className="font-bold text-blue-700">🎯 TARGET</div>
                                <div className="text-blue-600">{mode === 'fair' ? '≥70%' : '≥50%'}</div>
                            </div>
                            <div className="bg-orange-100 p-2 rounded-lg">
                                <div className="font-bold text-orange-700">🔼 REACH</div>
                                <div className="text-orange-600">{mode === 'fair' ? '≥50%' : '≥35%'}</div>
                            </div>
                            <div className="bg-red-100 p-2 rounded-lg">
                                <div className="font-bold text-red-700">🚀 SUPER REACH</div>
                                <div className="text-red-600">&lt;{mode === 'fair' ? '50%' : '35%'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FitVisualizer;
