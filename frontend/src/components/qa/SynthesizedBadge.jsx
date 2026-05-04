import React from 'react';
import { CpuChipIcon } from '@heroicons/react/24/outline';

// Marks an LLM-synthesized scenario in the dashboard. Renders a small
// "🤖 LLM-generated" pill + a rationale block explaining what gap or
// risk the scenario targets.
//
// Returns null when scenario is static — keeps the component cheap to
// drop into the existing ScenarioCard.

const SynthesizedBadge = ({ synthesized, rationale }) => {
    if (!synthesized) return null;

    return (
        <div className="bg-violet-50/70 border border-violet-200 rounded-lg p-3 my-2">
            <div className="flex items-start gap-2">
                <CpuChipIcon className="h-4 w-4 text-violet-700 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-100 text-violet-900 font-bold">
                            🤖 LLM-generated
                        </span>
                    </div>
                    {rationale && (
                        <p className="text-xs text-[#2A2A2A] leading-relaxed">
                            <span className="font-semibold text-violet-900">
                                Why this was generated:
                            </span>{' '}
                            {rationale}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SynthesizedBadge;
