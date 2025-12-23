import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoFitAnalysis } from '../../data/demoData';

const FitAnalysisDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.5 });

    const [score, setScore] = useState(0);
    const [academics, setAcademics] = useState(0);
    const [testScores, setTestScores] = useState(0);
    const [extracurriculars, setExtracurriculars] = useState(0);

    useEffect(() => {
        if (!isInView) return;

        // Animate scores counting up
        const scoreInterval = setInterval(() => {
            setScore(prev => {
                const next = prev + 2;
                return next >= demoFitAnalysis.matchScore ? demoFitAnalysis.matchScore : next;
            });
        }, 40);

        const academicsInterval = setInterval(() => {
            setAcademics(prev => {
                const next = prev + 2;
                return next >= demoFitAnalysis.breakdown.academics ? demoFitAnalysis.breakdown.academics : next;
            });
        }, 40);

        const testScoresInterval = setInterval(() => {
            setTestScores(prev => {
                const next = prev + 2;
                return next >= demoFitAnalysis.breakdown.testScores ? demoFitAnalysis.breakdown.testScores : next;
            });
        }, 40);

        const extrasInterval = setInterval(() => {
            setExtracurriculars(prev => {
                const next = prev + 2;
                return next >= demoFitAnalysis.breakdown.extracurriculars ? demoFitAnalysis.breakdown.extracurriculars : next;
            });
        }, 40);

        return () => {
            clearInterval(scoreInterval);
            clearInterval(academicsInterval);
            clearInterval(testScoresInterval);
            clearInterval(extrasInterval);
        };
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-2xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header with university name */}
                <div className="bg-gradient-to-r from-[#FF8C42] to-[#E67A2E] px-6 py-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-white font-bold text-2xl mb-1">{demoFitAnalysis.university}</h3>
                            <p className="text-white/90 text-sm">Match Analysis</p>
                        </div>
                        <div className="text-right">
                            <motion.div
                                className="text-5xl font-bold text-white mb-1"
                                style={{ fontVariantNumeric: 'tabular-nums' }}
                            >
                                {score}%
                            </motion.div>
                            <span className="inline-block px-3 py-1 bg-white/20 backdrop-blur rounded-full text-white text-sm font-semibold">
                                {demoFitAnalysis.fitCategory}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Breakdown */}
                <div className="p-6">
                    <h4 className="text-sm font-semibold text-[#4A4A4A] mb-4">Score Breakdown</h4>

                    <div className="space-y-4 mb-6">
                        {/* Academics */}
                        <div>
                            <div className="flex justify-between mb-2">
                                <span className="text-sm font-medium text-[#1A4D2E]">Academics</span>
                                <motion.span className="text-sm font-bold text-[#1A4D2E]">
                                    {academics}%
                                </motion.span>
                            </div>
                            <div className="h-2 bg-[#E0DED8] rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-gradient-to-r from-[#2E7D32] to-[#4CAF50]"
                                    initial={{ width: 0 }}
                                    animate={isInView ? { width: `${demoFitAnalysis.breakdown.academics}%` } : {}}
                                    transition={{ duration: 1.5, delay: 0.5 }}
                                />
                            </div>
                        </div>

                        {/* Test Scores */}
                        <div>
                            <div className="flex justify-between mb-2">
                                <span className="text-sm font-medium text-[#1A4D2E]">Test Scores</span>
                                <motion.span className="text-sm font-bold text-[#1A4D2E]">
                                    {testScores}%
                                </motion.span>
                            </div>
                            <div className="h-2 bg-[#E0DED8] rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-gradient-to-r from-[#FF8C42] to-[#FFB366]"
                                    initial={{ width: 0 }}
                                    animate={isInView ? { width: `${demoFitAnalysis.breakdown.testScores}%` } : {}}
                                    transition={{ duration: 1.5, delay: 0.7 }}
                                />
                            </div>
                        </div>

                        {/* Extracurriculars */}
                        <div>
                            <div className="flex justify-between mb-2">
                                <span className="text-sm font-medium text-[#1A4D2E]">Extracurriculars</span>
                                <motion.span className="text-sm font-bold text-[#1A4D2E]">
                                    {extracurriculars}%
                                </motion.span>
                            </div>
                            <div className="h-2 bg-[#E0DED8] rounded-full overflow-hidden">
                                <motion.div
                                    className="h-full bg-gradient-to-r from-[#C05838] to-[#D97A5F]"
                                    initial={{ width: 0 }}
                                    animate={isInView ? { width: `${demoFitAnalysis.breakdown.extracurriculars}%` } : {}}
                                    transition={{ duration: 1.5, delay: 0.9 }}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Insights */}
                    <h4 className="text-sm font-semibold text-[#4A4A4A] mb-3">Key Insights</h4>
                    <div className="space-y-2 mb-6">
                        {demoFitAnalysis.insights.map((insight, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, x: -20 }}
                                animate={isInView ? { opacity: 1, x: 0 } : {}}
                                transition={{ delay: 1.2 + index * 0.1 }}
                                className="flex items-start gap-2 text-sm text-[#4A4A4A]"
                            >
                                <svg className="w-5 h-5 text-[#2E7D32] mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                <span>{insight}</span>
                            </motion.div>
                        ))}
                    </div>

                    {/* Recommendation */}
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={isInView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: 1.5 }}
                        className="bg-gradient-to-r from-[#FFE6D5] to-[#FFF3E6] border border-[#FF8C42]/20 rounded-xl p-4"
                    >
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-lg bg-[#FF8C42] flex items-center justify-center flex-shrink-0">
                                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-[#C05838] mb-1">Our Recommendation</p>
                                <p className="text-sm text-[#4A4A4A] leading-relaxed">{demoFitAnalysis.recommendation}</p>
                            </div>
                        </div>
                    </motion.div>
                </div>
            </motion.div>
        </div>
    );
};

export default FitAnalysisDemo;
