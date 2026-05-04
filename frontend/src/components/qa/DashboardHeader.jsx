import React from 'react';
import SparklineByDay from './SparklineByDay';

// Persistent header for the QA dashboard. Stays visible across tab
// switches so health context (sparkline + recent-N pill) never
// disappears.
//
// Spec: docs/prd/qa-dashboard-tabbed-layout.md.

const DashboardHeader = ({ runs }) => (
    <header className="bg-white border-b border-[#E0DED8] sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
            <div>
                <h1 className="text-xl font-bold text-[#1A4D2E]">QA Agent</h1>
                <p className="text-[11px] text-[#8A8A8A]">
                    Internal — synthetic monitoring runs
                </p>
            </div>
            <SparklineByDay runs={runs} />
        </div>
    </header>
);

export default DashboardHeader;
