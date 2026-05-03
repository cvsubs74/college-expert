import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ArrowDownIcon, BuildingLibraryIcon } from '@heroicons/react/24/outline';

// "Generic template task → translated per-school tasks" diagram.
//
// Top: a single generic task ("Submit RD Applications").
// Middle: an arrow labeled "translate against college list = [...]".
// Bottom: three task pills, including the UC group treatment.

const COLLEGE_LIST = ['MIT', 'Stanford', 'UC Berkeley', 'UC Davis', 'UCLA'];

const TRANSLATED = [
    {
        title: 'Submit MIT app',
        deadline: 'Jan 5, 2027',
        artifactLabel: 'Open MIT',
        gradient: 'from-emerald-500 to-teal-600',
    },
    {
        title: 'Submit Stanford app',
        deadline: 'Jan 2, 2027',
        artifactLabel: 'Open Stanford',
        gradient: 'from-emerald-500 to-teal-600',
    },
    {
        title: 'Submit UC Application',
        deadline: 'Nov 30, 2026',
        artifactLabel: 'Open UC Berkeley, UC Davis, UCLA',
        gradient: 'from-amber-500 to-orange-600',
        group: true,
    },
];

const TranslationDiagram = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-4xl mx-auto py-4">
            {/* TOP — generic template task */}
            <motion.div
                className="max-w-md mx-auto bg-[#F8F6F0] border-2 border-dashed border-[#C0BFB8] rounded-xl p-4 text-center"
                initial={{ opacity: 0, y: -10 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.4 }}
            >
                <div className="text-[10px] uppercase tracking-wider text-[#8A8A8A] font-semibold mb-1">
                    Template task · generic
                </div>
                <div className="font-mono text-base font-semibold text-[#4A4A4A]">
                    "Submit RD Applications"
                </div>
                <div className="text-[11px] text-[#8A8A8A] italic mt-1">
                    abstract · no school context · not actionable yet
                </div>
            </motion.div>

            {/* MIDDLE — arrow + college list */}
            <div className="my-6 flex flex-col items-center">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 0.6 }}
                >
                    <ArrowDownIcon className="h-8 w-8 text-indigo-500" />
                </motion.div>
                <motion.div
                    className="mt-2 inline-flex items-center gap-2 bg-indigo-50 border border-indigo-200 px-4 py-2 rounded-full text-xs text-indigo-900"
                    initial={{ opacity: 0, scale: 0.85 }}
                    animate={inView ? { opacity: 1, scale: 1 } : {}}
                    transition={{ delay: 0.8 }}
                >
                    <BuildingLibraryIcon className="h-3.5 w-3.5" />
                    <span className="font-semibold">translate against college list:</span>
                    <span className="font-mono">[{COLLEGE_LIST.join(', ')}]</span>
                </motion.div>
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 1.0 }}
                    className="mt-2"
                >
                    <ArrowDownIcon className="h-8 w-8 text-indigo-500" />
                </motion.div>
            </div>

            {/* BOTTOM — translated task pills */}
            <div className="space-y-3">
                {TRANSLATED.map((task, i) => (
                    <motion.div
                        key={task.title}
                        className="bg-white rounded-xl border border-[#E0E2EF] shadow-sm overflow-hidden"
                        initial={{ opacity: 0, x: -16 }}
                        animate={inView ? { opacity: 1, x: 0 } : {}}
                        transition={{ duration: 0.4, delay: 1.2 + i * 0.15 }}
                    >
                        <div className="flex items-stretch">
                            {/* Left accent stripe */}
                            <div className={`bg-gradient-to-b ${task.gradient} w-1.5 flex-shrink-0`} />
                            <div className="flex-1 p-3 flex flex-col sm:flex-row sm:items-center gap-3">
                                <div className="flex-1 min-w-0">
                                    <div className="font-semibold text-[#1A4D2E]">{task.title}</div>
                                    <div className="text-xs text-[#8A8A8A] mt-0.5">
                                        Due {task.deadline}
                                        {task.group && (
                                            <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900">
                                                UC GROUP
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <button
                                    className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[11px] font-semibold text-white bg-gradient-to-r ${task.gradient} shadow-sm flex-shrink-0`}
                                    type="button"
                                >
                                    {task.artifactLabel}
                                    <span>›</span>
                                </button>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>

            <motion.div
                className="mt-4 text-xs text-[#6B6B6B] text-center italic max-w-2xl mx-auto"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ delay: 2.0 }}
            >
                Each pill is an <span className="font-mono">artifact_ref</span> — a typed pointer
                back to the right place to do the task. UCs share one application, so the translator
                emits one group task, not three.
            </motion.div>
        </div>
    );
};

export default TranslationDiagram;
