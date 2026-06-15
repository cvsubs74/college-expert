import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
    ChatBubbleLeftRightIcon,
    EyeIcon,
    SparklesIcon,
    ArrowDownTrayIcon,
    ArrowRightIcon,
    ArrowUturnLeftIcon,
    BookmarkIcon,
    CheckCircleIcon,
} from '@heroicons/react/24/outline';

// "The round trip" — analysis an agent does flows back into the app.
//
// Top: a four-step pipeline (Ask → Read → Reason → Save back).
// Bottom: the durable artifact that lands in the student's app — a Research
// Notebook note stamped with provenance + linked colleges, plus a roadmap task
// the agent spun out of it. A return arrow ties the loop closed.

const STEPS = [
    { icon: ChatBubbleLeftRightIcon, label: 'You ask', sub: '"Compare Duke & UCSD for CS"' },
    { icon: EyeIcon, label: 'Agent reads', sub: 'get_profile · get_fit_analysis' },
    { icon: SparklesIcon, label: 'Agent reasons', sub: 'builds the comparison' },
    { icon: ArrowDownTrayIcon, label: 'Saves back', sub: 'save_research' },
];

const ClosedLoopDiagram = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-4xl mx-auto py-4">
            {/* PIPELINE */}
            <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-center gap-2">
                {STEPS.map((step, i) => {
                    const Icon = step.icon;
                    const last = i === STEPS.length - 1;
                    return (
                        <React.Fragment key={step.label}>
                            <motion.div
                                className={`flex-1 rounded-xl border p-3 text-center ${
                                    last
                                        ? 'bg-gradient-to-br from-violet-600 to-fuchsia-700 text-white border-transparent shadow-md'
                                        : 'bg-white border-[#E6DEF2] shadow-sm'
                                }`}
                                initial={{ opacity: 0, y: 12 }}
                                animate={inView ? { opacity: 1, y: 0 } : {}}
                                transition={{ duration: 0.4, delay: i * 0.18 }}
                            >
                                <div className="flex justify-center mb-1.5">
                                    <div className={`p-1.5 rounded-lg ${last ? 'bg-white/15' : 'bg-violet-100'}`}>
                                        <Icon className={`h-4 w-4 ${last ? 'text-white' : 'text-violet-700'}`} />
                                    </div>
                                </div>
                                <div className={`text-xs font-bold ${last ? 'text-white' : 'text-[#1A2E1F]'}`}>
                                    {step.label}
                                </div>
                                <div className={`text-[10px] mt-0.5 font-mono ${last ? 'text-violet-100' : 'text-[#8A8A8A]'}`}>
                                    {step.sub}
                                </div>
                            </motion.div>
                            {!last && (
                                <motion.div
                                    className="flex justify-center items-center text-violet-400"
                                    initial={{ opacity: 0 }}
                                    animate={inView ? { opacity: 1 } : {}}
                                    transition={{ delay: 0.1 + i * 0.18 }}
                                >
                                    <ArrowRightIcon className="h-5 w-5 lg:rotate-0 rotate-90" />
                                </motion.div>
                            )}
                        </React.Fragment>
                    );
                })}
            </div>

            {/* RETURN ARROW */}
            <motion.div
                className="flex items-center justify-center gap-2 my-3 text-fuchsia-600"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ delay: 0.9 }}
            >
                <ArrowUturnLeftIcon className="h-5 w-5 rotate-90" />
                <span className="text-[11px] font-semibold uppercase tracking-wide">
                    …and it lands back in your app
                </span>
            </motion.div>

            {/* ARTIFACT — the saved note + spun-out task */}
            <motion.div
                className="bg-white rounded-2xl border border-[#E6DEF2] shadow-md overflow-hidden"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={inView ? { opacity: 1, scale: 1 } : {}}
                transition={{ duration: 0.5, delay: 1.05 }}
            >
                <div className="h-1.5 bg-gradient-to-r from-violet-500 to-fuchsia-600" />
                <div className="p-4">
                    <div className="flex items-start gap-2 mb-2">
                        <BookmarkIcon className="h-5 w-5 text-fuchsia-700 flex-shrink-0 mt-0.5" />
                        <div className="flex-1 min-w-0">
                            <div className="font-bold text-[#1A2E1F] leading-tight">
                                Duke vs. UCSD — CS reality check
                            </div>
                            <div className="text-xs text-[#6B6B6B] mt-0.5">
                                In your Research Notebook · linked to both schools' cards
                            </div>
                        </div>
                    </div>

                    {/* provenance + linked colleges */}
                    <div className="flex flex-wrap gap-1.5 mb-3">
                        <Badge tone="violet">comparison</Badge>
                        <Badge tone="slate">by Claude</Badge>
                        <Badge tone="slate">2026 cycle</Badge>
                        <Badge tone="fuchsia">Duke</Badge>
                        <Badge tone="fuchsia">UCSD</Badge>
                    </div>

                    {/* spun-out roadmap task */}
                    <div className="flex items-center gap-2 bg-[#F6F2FB] rounded-lg px-3 py-2">
                        <CheckCircleIcon className="h-4 w-4 text-violet-600 flex-shrink-0" />
                        <span className="text-xs text-[#4A4A4A] flex-1">
                            <span className="font-semibold text-[#1A2E1F]">Draft UCSD CS supplement</span>{' '}
                            — added to your Roadmap
                        </span>
                        <span className="text-[10px] font-mono text-[#8A8A8A] hidden sm:inline">
                            research_to_tasks
                        </span>
                    </div>
                </div>
            </motion.div>

            <motion.div
                className="mt-4 text-xs text-[#6B6B6B] text-center italic max-w-2xl mx-auto"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ delay: 1.4 }}
            >
                The analysis doesn't evaporate into a chat log. It's a tracked note — stamped with
                who made it and which data cycle it used — and its recommendations become tasks on
                your Plan.
            </motion.div>
        </div>
    );
};

const TONE = {
    violet: 'bg-violet-100 text-violet-800',
    fuchsia: 'bg-fuchsia-100 text-fuchsia-800',
    slate: 'bg-[#EEF0F2] text-[#4A5568]',
};

const Badge = ({ tone, children }) => (
    <span
        className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold ${TONE[tone]}`}
    >
        {children}
    </span>
);

export default ClosedLoopDiagram;
