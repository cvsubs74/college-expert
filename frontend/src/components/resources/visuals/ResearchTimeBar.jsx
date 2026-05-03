import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

// "By the numbers: what 35 hours actually looks like" — stacked horizontal
// bars. 10 schools, 7 dimensions per school, each segment proportional to
// the per-dimension time. Aggregate label above the chart.
//
// The visual makes the "matrix problem" tangible: the student isn't doing
// 7 things, they're doing 7×10 = 70 things, and each one takes time.

const SCHOOLS = [
    'MIT', 'Stanford', 'UC Berkeley', 'UCLA', 'Tufts',
    'Northeastern', 'NYU', 'Boston U', 'UT Austin', 'Michigan',
];

const DIMENSIONS = [
    { name: 'Degrees', minutes: 25, color: '#1A4D2E' },
    { name: 'Deadlines', minutes: 20, color: '#2D6B45' },
    { name: 'Supplements', minutes: 35, color: '#3F8B5C' },
    { name: 'Aid', minutes: 30, color: '#5BA877' },
    { name: 'Scholarships', minutes: 35, color: '#7DC79B' },
    { name: 'Test policy', minutes: 15, color: '#A3DCB8' },
    { name: 'Demonstrated interest', minutes: 20, color: '#D6E8D5' },
];

const TOTAL_PER_SCHOOL = DIMENSIONS.reduce((s, d) => s + d.minutes, 0); // 180 min = 3h
const TOTAL_HOURS = Math.round((SCHOOLS.length * TOTAL_PER_SCHOOL) / 60); // 30h

const ResearchTimeBar = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-3xl mx-auto py-4">
            {/* Headline number */}
            <div className="flex items-baseline justify-between mb-4 pb-3 border-b border-[#E0DED8]">
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={inView ? { opacity: 1, y: 0 } : {}}
                    transition={{ duration: 0.5 }}
                >
                    <div className="text-4xl font-bold text-[#1A4D2E]">
                        ~{TOTAL_HOURS} hours
                    </div>
                    <div className="text-sm text-[#6B6B6B] mt-1">
                        across {SCHOOLS.length} schools, {DIMENSIONS.length} dimensions each
                    </div>
                </motion.div>
                <motion.div
                    className="text-right text-xs text-[#8A8A8A] hidden sm:block"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ duration: 0.5, delay: 0.3 }}
                >
                    Each segment ≈ research time for one dimension
                </motion.div>
            </div>

            {/* Stacked bars per school */}
            <div className="space-y-2">
                {SCHOOLS.map((school, schoolIdx) => (
                    <div key={school} className="flex items-center gap-3">
                        <div className="w-24 sm:w-28 text-xs sm:text-sm text-[#4A4A4A] truncate text-right">
                            {school}
                        </div>
                        <div className="flex-1 flex h-7 rounded overflow-hidden bg-[#F8F6F0]">
                            {DIMENSIONS.map((dim, dimIdx) => {
                                const widthPct = (dim.minutes / TOTAL_PER_SCHOOL) * 100;
                                const delay = 0.2 + schoolIdx * 0.06 + dimIdx * 0.03;
                                return (
                                    <motion.div
                                        key={`${school}-${dim.name}`}
                                        className="h-full relative group"
                                        style={{ backgroundColor: dim.color }}
                                        initial={{ width: 0 }}
                                        animate={inView ? { width: `${widthPct}%` } : { width: 0 }}
                                        transition={{
                                            duration: 0.5,
                                            delay,
                                            ease: 'easeOut',
                                        }}
                                        title={`${dim.name} — ${dim.minutes} min`}
                                    />
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {/* Legend */}
            <motion.div
                className="mt-6 flex flex-wrap gap-3 justify-center text-xs text-[#4A4A4A]"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ duration: 0.5, delay: 1.2 }}
            >
                {DIMENSIONS.map((dim) => (
                    <div key={dim.name} className="flex items-center gap-1.5">
                        <span
                            className="inline-block w-3 h-3 rounded-sm"
                            style={{ backgroundColor: dim.color }}
                        />
                        <span>{dim.name}</span>
                        <span className="text-[#8A8A8A]">· {dim.minutes}m</span>
                    </div>
                ))}
            </motion.div>
        </div>
    );
};

export default ResearchTimeBar;
