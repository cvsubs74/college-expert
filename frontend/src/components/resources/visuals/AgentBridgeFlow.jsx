import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
    PuzzlePieceIcon,
    ArrowsRightLeftIcon,
    UserIcon,
    BuildingLibraryIcon,
    ChartBarIcon,
    MapIcon,
    BookmarkIcon,
} from '@heroicons/react/24/outline';

// Hero infographic for "How Stratia Works With AI Agents."
//
// Horizontal bridge:
//   [Any MCP agent] ⇄ [Stratia MCP connector] ⇄ [Your Stratia data]
//
// The agent chips slide in from the left, the connector box materializes in
// the middle, and the data chips slide in from the right. The two double-arrows
// between them carry "read" / "write back" labels so the round trip reads at a
// glance — the agent doesn't just pull data, it writes results back.

const AGENTS = [
    { label: 'Claude', dot: 'bg-orange-400' },
    { label: 'ChatGPT', dot: 'bg-emerald-400' },
    { label: 'Cursor', dot: 'bg-sky-400' },
    { label: 'any MCP agent', dot: 'bg-violet-300', muted: true },
];

const DATA = [
    { icon: UserIcon, label: 'Profile' },
    { icon: BuildingLibraryIcon, label: 'College list' },
    { icon: ChartBarIcon, label: 'Fit analyses' },
    { icon: MapIcon, label: 'Roadmap' },
    { icon: BookmarkIcon, label: 'Research notebook' },
];

const CONNECTOR_ROWS = [
    { k: 'Sign in', v: 'Google' },
    { k: 'Tools', v: '31' },
    { k: 'Scope', v: 'just you' },
];

const Bridge = ({ inView, delay }) => (
    <motion.div
        className="flex flex-row lg:flex-col items-center justify-center gap-1 text-violet-400"
        initial={{ opacity: 0 }}
        animate={inView ? { opacity: 1 } : {}}
        transition={{ delay }}
    >
        <ArrowsRightLeftIcon className="h-6 w-6 lg:rotate-90 rotate-0" />
        <div className="flex lg:flex-col items-center gap-x-2 text-[9px] font-semibold uppercase tracking-wide leading-tight">
            <span className="text-violet-600">read</span>
            <span className="text-fuchsia-600">write&nbsp;back</span>
        </div>
    </motion.div>
);

const AgentBridgeFlow = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-5xl mx-auto py-6">
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1.15fr_auto_1fr] gap-4 lg:gap-3 items-center">
                {/* AGENTS */}
                <div className="space-y-2">
                    <div className="text-[10px] uppercase tracking-wider text-[#8A8A8A] font-semibold mb-1 text-center lg:text-left">
                        The agent you already use
                    </div>
                    {AGENTS.map((a, i) => (
                        <motion.div
                            key={a.label}
                            className={`flex items-center gap-3 bg-white rounded-xl border p-3 shadow-sm ${
                                a.muted ? 'border-dashed border-[#D6CFE6]' : 'border-[#E6DEF2]'
                            }`}
                            initial={{ opacity: 0, x: -16 }}
                            animate={inView ? { opacity: 1, x: 0 } : {}}
                            transition={{ duration: 0.4, delay: i * 0.12 }}
                        >
                            <span className={`h-2.5 w-2.5 rounded-full flex-shrink-0 ${a.dot}`} />
                            <span
                                className={`text-sm font-bold ${
                                    a.muted ? 'text-[#8A8A8A] italic' : 'text-[#2A2A2A]'
                                }`}
                            >
                                {a.label}
                            </span>
                        </motion.div>
                    ))}
                </div>

                <Bridge inView={inView} delay={0.55} />

                {/* CONNECTOR */}
                <motion.div
                    className="bg-gradient-to-br from-violet-600 to-fuchsia-700 rounded-2xl p-5 shadow-xl text-white"
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={inView ? { opacity: 1, scale: 1 } : {}}
                    transition={{ duration: 0.5, delay: 0.65 }}
                >
                    <div className="flex items-center gap-2 mb-3">
                        <div className="bg-white/15 p-2 rounded-lg">
                            <PuzzlePieceIcon className="h-5 w-5 text-white" />
                        </div>
                        <div>
                            <div className="text-[10px] uppercase tracking-wider text-violet-200 font-bold">
                                Remote MCP server
                            </div>
                            <div className="text-sm font-bold leading-tight">Stratia connector</div>
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        {CONNECTOR_ROWS.map((row, i) => (
                            <motion.div
                                key={row.k}
                                className="flex justify-between items-baseline bg-white/10 rounded-lg px-2.5 py-1.5"
                                initial={{ opacity: 0, y: 6 }}
                                animate={inView ? { opacity: 1, y: 0 } : {}}
                                transition={{ duration: 0.3, delay: 0.9 + i * 0.15 }}
                            >
                                <span className="text-[11px] text-violet-200 font-semibold uppercase tracking-wide">
                                    {row.k}
                                </span>
                                <span className="text-sm font-bold">{row.v}</span>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                <Bridge inView={inView} delay={1.5} />

                {/* DATA */}
                <div className="space-y-2">
                    <div className="text-[10px] uppercase tracking-wider text-[#8A8A8A] font-semibold mb-1 text-center lg:text-left">
                        Your Stratia data
                    </div>
                    {DATA.map((d, i) => {
                        const Icon = d.icon;
                        return (
                            <motion.div
                                key={d.label}
                                className="flex items-center gap-3 bg-white rounded-xl border border-[#E6DEF2] p-2.5 shadow-sm"
                                initial={{ opacity: 0, x: 16 }}
                                animate={inView ? { opacity: 1, x: 0 } : {}}
                                transition={{ duration: 0.4, delay: 1.7 + i * 0.1 }}
                            >
                                <div className="bg-fuchsia-100 p-1.5 rounded-lg flex-shrink-0">
                                    <Icon className="h-4 w-4 text-fuchsia-700" />
                                </div>
                                <span className="text-sm font-semibold text-[#2A2A2A]">{d.label}</span>
                            </motion.div>
                        );
                    })}
                </div>
            </div>

            <motion.div
                className="mt-6 text-xs text-[#6B6B6B] text-center italic max-w-2xl mx-auto"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ delay: 2.2 }}
            >
                One connector, every MCP-capable agent. You sign in with Google once; the verified
                email is your Stratia identity, so every tool call is scoped to your data alone.
            </motion.div>
        </div>
    );
};

export default AgentBridgeFlow;
