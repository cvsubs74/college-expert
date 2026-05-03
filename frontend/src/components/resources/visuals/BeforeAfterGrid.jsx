import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
    DocumentTextIcon,
    TableCellsIcon,
    EnvelopeIcon,
    GlobeAltIcon,
    BookmarkIcon,
    PhotoIcon,
    SparklesIcon,
} from '@heroicons/react/24/outline';

// Side-by-side workflow comparison.
// Left: 6 small "fragment" cards floating in a chaotic grid (representing
//   the surfaces a manual researcher uses).
// Right: a single Stratia-shaped panel summarizing the same data.
// Animation: on view, the left fragments shake/bounce briefly to signal
//   chaos; the right panel fades in clean and steady.

const FRAGMENTS = [
    { icon: GlobeAltIcon, label: 'mit.edu/admissions', sub: 'browser tab', color: 'bg-blue-50 border-blue-200' },
    { icon: DocumentTextIcon, label: 'Notion · Tufts notes', sub: 'half-finished', color: 'bg-gray-50 border-gray-200' },
    { icon: TableCellsIcon, label: 'Sheet · deadlines', sub: 'last updated October', color: 'bg-emerald-50 border-emerald-200' },
    { icon: EnvelopeIcon, label: 'Email · aid math', sub: 'from Mom', color: 'bg-amber-50 border-amber-200' },
    { icon: BookmarkIcon, label: 'Bookmark · UC PIQs', sub: 'never reopened', color: 'bg-purple-50 border-purple-200' },
    { icon: PhotoIcon, label: 'Photo · campus board', sub: 'on phone', color: 'bg-rose-50 border-rose-200' },
];

const BeforeAfterGrid = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-5xl mx-auto py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 items-stretch">
                {/* LEFT — chaos */}
                <div className="relative">
                    <div className="text-xs uppercase tracking-wider text-[#8A8A8A] mb-3 font-semibold">
                        Today · scattered
                    </div>
                    <div className="bg-[#FBFAF6] rounded-2xl p-6 border border-[#E0DED8] min-h-[260px] relative overflow-hidden">
                        {FRAGMENTS.map((frag, i) => {
                            // Pseudo-scattered positions
                            const positions = [
                                { top: '12%', left: '8%', rot: -3 },
                                { top: '18%', left: '52%', rot: 4 },
                                { top: '46%', left: '20%', rot: -2 },
                                { top: '54%', left: '60%', rot: 3 },
                                { top: '74%', left: '12%', rot: 2 },
                                { top: '78%', left: '50%', rot: -4 },
                            ];
                            const pos = positions[i];
                            const Icon = frag.icon;
                            return (
                                <motion.div
                                    key={frag.label}
                                    className={`absolute inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border shadow-sm ${frag.color}`}
                                    style={{
                                        top: pos.top,
                                        left: pos.left,
                                        transform: `rotate(${pos.rot}deg)`,
                                    }}
                                    initial={{ opacity: 0, scale: 0.7, y: 10 }}
                                    animate={
                                        inView
                                            ? {
                                                  opacity: 1,
                                                  scale: 1,
                                                  y: 0,
                                              }
                                            : {}
                                    }
                                    transition={{
                                        duration: 0.4,
                                        delay: 0.1 + i * 0.1,
                                    }}
                                >
                                    <Icon className="h-4 w-4 text-[#4A4A4A]" />
                                    <div>
                                        <div className="text-xs font-medium text-[#2A2A2A]">
                                            {frag.label}
                                        </div>
                                        <div className="text-[10px] text-[#8A8A8A]">{frag.sub}</div>
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                    <div className="text-xs text-[#8A8A8A] mt-2 italic">
                        6 surfaces, 0 of them complete on their own.
                    </div>
                </div>

                {/* RIGHT — Stratia */}
                <div className="relative">
                    <div className="text-xs uppercase tracking-wider text-[#1A4D2E] mb-3 font-semibold flex items-center gap-1">
                        <SparklesIcon className="h-3.5 w-3.5" />
                        With Stratia · one screen
                    </div>
                    <motion.div
                        className="bg-gradient-to-br from-[#FDFCF7] to-[#F2EFE6] rounded-2xl p-6 border border-[#1A4D2E]/20 min-h-[260px] shadow-md"
                        initial={{ opacity: 0, y: 20 }}
                        animate={inView ? { opacity: 1, y: 0 } : {}}
                        transition={{ duration: 0.6, delay: 0.8 }}
                    >
                        {/* Mock card */}
                        <div className="flex items-center justify-between pb-3 border-b border-[#1A4D2E]/10">
                            <div className="font-semibold text-[#1A4D2E]">MIT</div>
                            <div className="text-[10px] px-2 py-0.5 rounded-full bg-[#D6E8D5] text-[#1A4D2E] font-medium">
                                Expanded
                            </div>
                        </div>
                        <dl className="mt-3 space-y-2 text-xs">
                            <Row label="Deadline" value="Jan 5, 2027 · Regular Decision" />
                            <Row label="Supplements" value="2 · 250 + 200 words" />
                            <Row label="Aid" value="Need-blind · ~$57k avg package" />
                            <Row label="Scholarships" value="1 match · Presidential" />
                            <Row label="Test policy" value="Optional" />
                            <Row label="Notes" value="Mom: ask about merit aid before Nov 1" notes />
                        </dl>
                    </motion.div>
                    <div className="text-xs text-[#1A4D2E] mt-2 italic">
                        One card. Same answers. Live data.
                    </div>
                </div>
            </div>

            {/* Bottom callout — savings */}
            <motion.div
                className="mt-8 text-center"
                initial={{ opacity: 0, y: 10 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: 1.4 }}
            >
                <div className="inline-flex items-baseline gap-2 bg-[#1A4D2E] text-white px-6 py-3 rounded-full shadow-lg">
                    <span className="text-2xl font-bold">~30 hours</span>
                    <span className="text-sm opacity-90">reclaimed per applicant</span>
                </div>
            </motion.div>
        </div>
    );
};

const Row = ({ label, value, notes }) => (
    <div className="flex justify-between gap-3">
        <dt className="text-[#6B6B6B] flex-shrink-0 w-24">{label}</dt>
        <dd className={`text-right text-[#2A2A2A] ${notes ? 'italic text-[#1A4D2E]' : ''}`}>
            {value}
        </dd>
    </div>
);

export default BeforeAfterGrid;
