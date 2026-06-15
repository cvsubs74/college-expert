import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { EyeIcon, BoltIcon, BookmarkIcon } from '@heroicons/react/24/outline';

// The MCP tool surface, grouped into three families: Read (20), Act (writes),
// Remember (research notebook). A curated subset of tools shows per family,
// with badges for the safety-relevant ones (destructive, spends a credit).
// Reinforces the paper's "31 tools, three families" framing.

const FAMILIES = [
    {
        key: 'read',
        title: 'Read',
        count: '20 tools · read-only',
        blurb: 'See everything the app sees.',
        icon: EyeIcon,
        accent: 'violet',
        tools: [
            { name: 'get_profile' },
            { name: 'get_college_list' },
            { name: 'get_fit_analysis' },
            { name: 'get_deadlines' },
            { name: 'search_universities' },
            { name: 'get_essays' },
            { name: 'get_scholarships' },
            { name: '+13 more', muted: true },
        ],
    },
    {
        key: 'act',
        title: 'Act',
        count: 'safe writes',
        blurb: 'Make changes you could make yourself.',
        icon: BoltIcon,
        accent: 'fuchsia',
        tools: [
            { name: 'add_college' },
            { name: 'remove_college', badge: 'asks first' },
            { name: 'recompute_fit', badge: '1 credit' },
            { name: 'update_profile_field' },
            { name: 'update_student_profile' },
            { name: 'set_application_status' },
        ],
    },
    {
        key: 'remember',
        title: 'Remember',
        count: 'research notebook',
        blurb: 'Keep the work, and act on it.',
        icon: BookmarkIcon,
        accent: 'indigo',
        tools: [
            { name: 'save_research' },
            { name: 'search_research' },
            { name: 'research_overview' },
            { name: 'pin_research' },
            { name: 'research_to_tasks' },
            { name: 'list_stale_research' },
        ],
    },
];

// Per-accent class lookups (kept static so Tailwind keeps them in the build).
const ACCENT = {
    violet: { strip: 'from-violet-500 to-violet-700', icon: 'bg-violet-100 text-violet-700', chip: 'text-violet-800' },
    fuchsia: { strip: 'from-fuchsia-500 to-fuchsia-700', icon: 'bg-fuchsia-100 text-fuchsia-700', chip: 'text-fuchsia-800' },
    indigo: { strip: 'from-indigo-500 to-indigo-700', icon: 'bg-indigo-100 text-indigo-700', chip: 'text-indigo-800' },
};

const ToolSurfaceGrid = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-4xl mx-auto py-4">
            <div className="text-xs uppercase tracking-wider text-[#8A8A8A] font-semibold mb-4 text-center">
                31 tools · three families
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {FAMILIES.map((fam, col) => {
                    const Icon = fam.icon;
                    const a = ACCENT[fam.accent];
                    return (
                        <motion.div
                            key={fam.key}
                            className="bg-white rounded-2xl border border-[#E6DEF2] shadow-sm overflow-hidden flex flex-col"
                            initial={{ opacity: 0, y: 16 }}
                            animate={inView ? { opacity: 1, y: 0 } : {}}
                            transition={{ duration: 0.45, delay: col * 0.15 }}
                        >
                            <div className={`h-1.5 bg-gradient-to-r ${a.strip}`} />
                            <div className="p-4 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <div className={`p-1.5 rounded-lg ${a.icon}`}>
                                        <Icon className="h-4 w-4" />
                                    </div>
                                    <div className="text-base font-bold text-[#1A2E1F]">{fam.title}</div>
                                </div>
                                <div className="text-[10px] uppercase tracking-wide text-[#8A8A8A] font-semibold">
                                    {fam.count}
                                </div>
                                <div className="text-xs text-[#6B6B6B] mt-1 mb-3">{fam.blurb}</div>

                                <div className="flex flex-wrap gap-1.5">
                                    {fam.tools.map((t, i) => (
                                        <motion.span
                                            key={t.name}
                                            className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-mono font-medium ${
                                                t.muted
                                                    ? 'bg-[#F2EFE6] text-[#8A8A8A] italic'
                                                    : `bg-[#F6F2FB] ${a.chip}`
                                            }`}
                                            initial={{ opacity: 0, scale: 0.9 }}
                                            animate={inView ? { opacity: 1, scale: 1 } : {}}
                                            transition={{ duration: 0.25, delay: 0.3 + col * 0.15 + i * 0.05 }}
                                        >
                                            {t.name}
                                            {t.badge && (
                                                <span className="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-sans font-bold uppercase tracking-wide bg-amber-100 text-amber-900">
                                                    {t.badge}
                                                </span>
                                            )}
                                        </motion.span>
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    );
                })}
            </div>

            <motion.div
                className="mt-4 text-xs text-[#6B6B6B] text-center italic max-w-2xl mx-auto"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ delay: 1.0 }}
            >
                Every tool is annotated for the agent's host: read-only tools can't change anything,
                and the destructive or credit-spending ones are flagged so the agent confirms first.
            </motion.div>
        </div>
    );
};

export default ToolSurfaceGrid;
