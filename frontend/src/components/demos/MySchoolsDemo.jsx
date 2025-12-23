import React, { useEffect, useState } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoUniversities } from '../../data/demoData';

const MySchoolsDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.3 });

    const [visibleSchools, setVisibleSchools] = useState([]);

    useEffect(() => {
        if (!isInView) return;

        // Add schools one by one
        demoUniversities.forEach((_, index) => {
            setTimeout(() => {
                setVisibleSchools(prev => [...prev, index]);
            }, index * 300);
        });
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-3xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] px-6 py-6">
                    <h2 className="text-2xl font-bold text-white mb-1">My Schools</h2>
                    <p className="text-white/90 text-sm">Your balanced college list with fit analysis</p>
                </div>

                {/* School list */}
                <div className="p-6">
                    <div className="space-y-3">
                        {demoUniversities.map((university, index) => (
                            visibleSchools.includes(index) && (
                                <UniversityRowWithScore
                                    key={university.id}
                                    university={university}
                                    index={index}
                                    isInView={isInView}
                                />
                            )
                        ))}
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

const UniversityRowWithScore = ({ university, index, isInView }) => {
    const [score, setScore] = useState(0);

    useEffect(() => {
        if (!isInView) return;

        const interval = setInterval(() => {
            setScore(prev => {
                const next = prev + 2;
                return next >= university.matchScore ? university.matchScore : next;
            });
        }, 30);

        return () => clearInterval(interval);
    }, [isInView, university.matchScore]);

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className="flex items-center gap-4 p-4 bg-[#F8F6F0] rounded-xl border border-[#E0DED8] hover:border-[#1A4D2E] transition-all group"
        >
            {/* University logo */}
            <div className="w-16 h-16 rounded-lg overflow-hidden bg-white flex items-center justify-center p-2 flex-shrink-0 border border-[#E0DED8]">
                <img
                    src={university.logoUrl}
                    alt={university.name}
                    className="max-h-full max-w-full object-contain"
                />
            </div>

            {/* University info */}
            <div className="flex-1 min-w-0">
                <h3 className="font-bold text-lg text-[#1A4D2E] mb-1 truncate">{university.name}</h3>
                <div className="flex items-center gap-3 text-sm text-[#6B6B6B]">
                    <span className="flex items-center gap-1">
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                        </svg>
                        {university.location}
                    </span>
                    <span>•</span>
                    <span>{university.acceptanceRate}% acceptance</span>
                </div>
            </div>

            {/* Match score */}
            <div className="flex flex-col items-center gap-2">
                <div className="relative w-20 h-20">
                    {/* Progress ring */}
                    <svg className="w-20 h-20 transform -rotate-90">
                        <circle
                            cx="40"
                            cy="40"
                            r="34"
                            stroke="#E0DED8"
                            strokeWidth="6"
                            fill="none"
                        />
                        <motion.circle
                            cx="40"
                            cy="40"
                            r="34"
                            stroke={
                                university.fitCategory === 'Safety' ? '#2E7D32' :
                                    university.fitCategory === 'Target' ? '#FF8C42' :
                                        '#C05838'
                            }
                            strokeWidth="6"
                            fill="none"
                            strokeLinecap="round"
                            initial={{ strokeDasharray: '0 214' }}
                            animate={isInView ? {
                                strokeDasharray: `${(university.matchScore / 100) * 214} 214`
                            } : {}}
                            transition={{ duration: 1.5, delay: index * 0.1 }}
                        />
                    </svg>

                    {/* Score number */}
                    <div className="absolute inset-0 flex items-center justify-center">
                        <motion.span className="text-xl font-bold text-[#1A4D2E]">
                            {Math.round(score)}
                        </motion.span>
                    </div>
                </div>

                {/* Category badge */}
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${university.fitCategory === 'Safety'
                    ? 'bg-[#E8F5E9] text-[#2E7D32]'
                    : university.fitCategory === 'Target'
                        ? 'bg-[#FFE6D5] text-[#FF8C42]'
                        : 'bg-[#FCEEE8] text-[#C05838]'
                    }`}>
                    {university.fitCategory}
                </span>
            </div>

            {/* View Analysis button */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg hover:bg-[#2D6B45] transition-colors opacity-0 group-hover:opacity-100"
            >
                View Analysis
            </motion.button>
        </motion.div>
    );
};

export default MySchoolsDemo;
