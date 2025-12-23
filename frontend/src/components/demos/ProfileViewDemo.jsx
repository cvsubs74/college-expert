import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoStudent } from '../../data/demoData';

const ProfileViewDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.3 });

    const [gpa, setGpa] = useState(0);
    const [sat, setSat] = useState(0);
    const [act, setAct] = useState(0);

    useEffect(() => {
        if (!isInView) return;

        // Animate GPA counting up
        const gpaInterval = setInterval(() => {
            setGpa(prev => {
                const next = prev + 0.05;
                return next >= demoStudent.gpa ? demoStudent.gpa : next;
            });
        }, 30);

        // Animate SAT counting up
        const satInterval = setInterval(() => {
            setSat(prev => {
                const next = prev + 20;
                return next >= demoStudent.satScore ? demoStudent.satScore : next;
            });
        }, 30);

        // Animate ACT counting up
        const actInterval = setInterval(() => {
            setAct(prev => {
                const next = prev + 1;
                return next >= demoStudent.actScore ? demoStudent.actScore : next;
            });
        }, 60);

        return () => {
            clearInterval(gpaInterval);
            clearInterval(satInterval);
            clearInterval(actInterval);
        };
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-3xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5 }}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] px-6 py-8">
                    <div className="flex items-start gap-4">
                        <div className="w-20 h-20 rounded-full bg-white/20 backdrop-blur flex items-center justify-center text-3xl font-bold text-white">
                            {demoStudent.name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <div className="flex-1">
                            <h2 className="text-2xl font-bold text-white mb-1">{demoStudent.name}</h2>
                            <p className="text-white/90 text-sm mb-2">{demoStudent.grade} • {demoStudent.school}</p>
                            <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/20 rounded-full backdrop-blur">
                                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                                </svg>
                                <span className="text-white text-sm font-medium">{demoStudent.state}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 divide-x divide-[#E0DED8] border-b border-[#E0DED8]">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={isInView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: 0.3 }}
                        className="px-6 py-4 text-center"
                    >
                        <p className="text-xs text-[#6B6B6B] mb-1 font-medium">GPA</p>
                        <motion.p className="text-3xl font-bold text-[#1A4D2E]">
                            {gpa.toFixed(2)}
                        </motion.p>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={isInView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: 0.4 }}
                        className="px-6 py-4 text-center"
                    >
                        <p className="text-xs text-[#6B6B6B] mb-1 font-medium">SAT</p>
                        <motion.p className="text-3xl font-bold text-[#C05838]">
                            {Math.round(sat)}
                        </motion.p>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={isInView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: 0.5 }}
                        className="px-6 py-4 text-center"
                    >
                        <p className="text-xs text-[#6B6B6B] mb-1 font-medium">ACT</p>
                        <motion.p className="text-3xl font-bold text-[#FF8C42]">
                            {Math.round(act)}
                        </motion.p>
                    </motion.div>
                </div>

                {/* Activities */}
                <div className="p-6">
                    <h3 className="text-sm font-semibold text-[#4A4A4A] mb-4 flex items-center gap-2">
                        <svg className="w-5 h-5 text-[#1A4D2E]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                        </svg>
                        Activities & Leadership
                    </h3>

                    <div className="space-y-3">
                        {demoStudent.activities.map((activity, index) => (
                            <motion.div
                                key={activity.name}
                                initial={{ opacity: 0, x: -20 }}
                                animate={isInView ? { opacity: 1, x: 0 } : {}}
                                transition={{ delay: 0.6 + index * 0.1 }}
                                className="flex items-start gap-3 p-4 bg-[#F8F6F0] rounded-xl border border-[#E0DED8] hover:border-[#1A4D2E] transition-colors"
                            >
                                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${activity.leadership ? 'bg-[#FFE6D5]' : 'bg-[#D6E8D5]'
                                    }`}>
                                    {activity.leadership ? (
                                        <svg className="w-5 h-5 text-[#FF8C42]" fill="currentColor" viewBox="0 0 20 20">
                                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5 text-[#1A4D2E]" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                                        </svg>
                                    )}
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-[#1A4D2E] mb-1">{activity.name}</p>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-[#6B6B6B]">{activity.years}</span>
                                        {activity.leadership && (
                                            <span className="px-2 py-0.5 bg-[#FF8C42] text-white text-xs font-medium rounded">
                                                Leadership
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    {/* Awards */}
                    <h3 className="text-sm font-semibold text-[#4A4A4A] mb-4 mt-6 flex items-center gap-2">
                        <svg className="w-5 h-5 text-[#1A4D2E]" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                        Awards & Honors
                    </h3>

                    <div className="flex flex-wrap gap-2">
                        {demoStudent.awards.map((award, index) => (
                            <motion.div
                                key={award}
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={isInView ? { opacity: 1, scale: 1 } : {}}
                                transition={{ delay: 0.9 + index * 0.1 }}
                                className="px-3 py-2 bg-gradient-to-r from-[#FFE6D5] to-[#FCEEE8] rounded-lg border border-[#FF8C42]/20"
                            >
                                <p className="text-sm font-medium text-[#C05838]">{award}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default ProfileViewDemo;
