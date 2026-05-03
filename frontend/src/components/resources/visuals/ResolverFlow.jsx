import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { CalendarDaysIcon, AcademicCapIcon, BuildingLibraryIcon, ClockIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

// Hero infographic for "How Stratia Builds Your Roadmap."
//
// Horizontal flow:
//   [4 input cards] → [Priority cascade box] → [Output card]
//
// The priority rules light up sequentially. The output card materializes
// last with the actual template name highlighted.

const INPUTS = [
    { icon: AcademicCapIcon, label: 'Grade', value: '11th', sub: 'from profile' },
    { icon: CalendarDaysIcon, label: 'Graduation', value: '2027', sub: 'from profile' },
    { icon: BuildingLibraryIcon, label: 'College list', value: '5 schools', sub: '3 UCs · MIT · Stanford' },
    { icon: ClockIcon, label: 'Today', value: 'Apr 2026', sub: 'computed' },
];

const PRIORITIES = [
    { label: 'caller', desc: 'Both grade + semester provided?', match: false },
    { label: 'profile', desc: 'graduation_year present?', match: true },
    { label: 'caller-grade-only', desc: 'Caller passed grade alone?', match: false },
    { label: 'default', desc: 'Fallback (senior_fall)', match: false },
];

const ResolverFlow = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-5xl mx-auto py-6">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1.2fr_auto_1fr] gap-4 lg:gap-3 items-center">
                {/* INPUTS column */}
                <div className="space-y-2">
                    {INPUTS.map((input, i) => {
                        const Icon = input.icon;
                        return (
                            <motion.div
                                key={input.label}
                                className="flex items-center gap-3 bg-white rounded-xl border border-[#E0E2EF] p-3 shadow-sm"
                                initial={{ opacity: 0, x: -16 }}
                                animate={inView ? { opacity: 1, x: 0 } : {}}
                                transition={{ duration: 0.4, delay: i * 0.12 }}
                            >
                                <div className="bg-indigo-100 p-2 rounded-lg flex-shrink-0">
                                    <Icon className="h-4 w-4 text-indigo-700" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="text-[10px] uppercase tracking-wide text-[#8A8A8A] font-semibold">
                                        {input.label}
                                    </div>
                                    <div className="text-sm font-bold text-[#2A2A2A]">{input.value}</div>
                                    <div className="text-[10px] text-[#8A8A8A] truncate">{input.sub}</div>
                                </div>
                            </motion.div>
                        );
                    })}
                </div>

                {/* Arrow 1 */}
                <motion.div
                    className="flex justify-center lg:flex-col items-center text-indigo-400"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 0.6 }}
                >
                    <ArrowRightIcon className="h-6 w-6 lg:rotate-0 rotate-90" />
                </motion.div>

                {/* PRIORITY CASCADE */}
                <motion.div
                    className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-2xl p-5 shadow-lg"
                    initial={{ opacity: 0, scale: 0.92 }}
                    animate={inView ? { opacity: 1, scale: 1 } : {}}
                    transition={{ duration: 0.5, delay: 0.7 }}
                >
                    <div className="text-[10px] uppercase tracking-wider text-indigo-200 font-bold mb-3">
                        Resolver priority cascade
                    </div>
                    <div className="space-y-2">
                        {PRIORITIES.map((p, i) => (
                            <motion.div
                                key={p.label}
                                className={`flex items-start gap-2 p-2 rounded-lg ${
                                    p.match ? 'bg-white/15 ring-1 ring-white/40' : 'bg-white/5'
                                }`}
                                initial={{ opacity: 0, x: 10 }}
                                animate={inView ? { opacity: 1, x: 0 } : {}}
                                transition={{ duration: 0.35, delay: 1.0 + i * 0.18 }}
                            >
                                <div
                                    className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-[10px] font-bold ${
                                        p.match
                                            ? 'bg-emerald-400 text-emerald-900'
                                            : 'bg-white/15 text-white/40'
                                    }`}
                                >
                                    {i + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div
                                        className={`text-xs font-semibold ${
                                            p.match ? 'text-white' : 'text-white/60 line-through'
                                        }`}
                                    >
                                        {p.label}
                                    </div>
                                    <div
                                        className={`text-[11px] ${
                                            p.match ? 'text-indigo-100' : 'text-white/40'
                                        }`}
                                    >
                                        {p.desc}
                                        {p.match && (
                                            <span className="ml-2 text-emerald-300 font-bold">✓ matched</span>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* Arrow 2 */}
                <motion.div
                    className="flex justify-center lg:flex-col items-center text-indigo-400"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 1.8 }}
                >
                    <ArrowRightIcon className="h-6 w-6 lg:rotate-0 rotate-90" />
                </motion.div>

                {/* OUTPUT */}
                <motion.div
                    className="bg-gradient-to-br from-emerald-600 to-teal-700 rounded-2xl p-5 text-white shadow-xl"
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={inView ? { opacity: 1, scale: 1 } : {}}
                    transition={{
                        duration: 0.6,
                        delay: 2.0,
                        type: 'spring',
                        stiffness: 200,
                    }}
                >
                    <div className="text-[10px] uppercase tracking-wider text-emerald-200 font-bold mb-2">
                        Resolved
                    </div>
                    <div className="font-mono text-xl font-bold mb-3">junior_spring</div>
                    <div className="space-y-1 text-xs">
                        <FieldRow label="grade_used" value="junior" />
                        <FieldRow label="semester_used" value="spring" />
                        <FieldRow label="resolution_source" value='"profile"' />
                    </div>
                </motion.div>
            </div>
        </div>
    );
};

const FieldRow = ({ label, value }) => (
    <div className="flex justify-between font-mono text-[11px]">
        <span className="text-emerald-200">{label}</span>
        <span className="text-white">{value}</span>
    </div>
);

export default ResolverFlow;
