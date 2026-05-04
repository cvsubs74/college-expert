import React from 'react';
import { XMarkIcon, PlayIcon, SparklesIcon } from '@heroicons/react/24/outline';

// Confirmation modal shown after the user clicks "Run now". Lists what
// the agent has picked + each pick's rationale, and offers a final
// [Run] / [Cancel].
//
// Spec: docs/prd/qa-run-preview-and-running-state.md.
//
// Props:
//   - picked: list of {id, description, business_rationale, surfaces_covered,
//             synthesized, synthesis_rationale, feedback_id}
//   - synthCount, staticCount: numbers shown in the header
//   - busy: boolean — disables Run while the API request is in flight
//   - onConfirm(): user clicked Run
//   - onCancel():  user clicked Cancel or closed the modal

const PreviewModal = ({
    picked = [],
    synthCount = 0,
    staticCount = 0,
    busy = false,
    onConfirm,
    onCancel,
}) => {
    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="preview-modal-title"
        >
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col">
                <div className="flex items-baseline justify-between px-5 py-4 border-b border-[#E0DED8]">
                    <div>
                        <h2 id="preview-modal-title" className="text-lg font-bold text-[#1A4D2E]">
                            Preview: {picked.length} {picked.length === 1 ? 'scenario' : 'scenarios'}
                        </h2>
                        <p className="text-xs text-[#8A8A8A] mt-0.5">
                            {synthCount > 0 && `${synthCount} LLM-generated`}
                            {synthCount > 0 && staticCount > 0 && ' · '}
                            {staticCount > 0 && `${staticCount} from corpus`}
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={onCancel}
                        aria-label="Close preview"
                        className="p-1 rounded-full text-[#8A8A8A] hover:text-[#1A2E1F] hover:bg-[#FBFAF6]"
                    >
                        <XMarkIcon className="h-5 w-5" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                    {picked.length === 0 ? (
                        <p className="text-sm text-[#8A8A8A] italic">
                            No scenarios picked. Try again or check the agent's archetypes.
                        </p>
                    ) : (
                        picked.map((p) => (
                            <div
                                key={p.id}
                                className="border border-[#E0DED8] rounded-lg p-3 bg-[#FBFAF6]"
                            >
                                <div className="flex items-baseline justify-between gap-2 flex-wrap">
                                    <span className="font-mono text-xs font-bold text-[#1A2E1F]">
                                        {p.id}
                                    </span>
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                        {p.synthesized && (
                                            <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full bg-purple-50 border border-purple-200 text-purple-800">
                                                <SparklesIcon className="h-2.5 w-2.5" />
                                                LLM-generated
                                            </span>
                                        )}
                                        {p.feedback_id && (
                                            <span className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 font-mono">
                                                addresses {p.feedback_id}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                {p.description && (
                                    <p className="text-xs text-[#4A4A4A] mt-1">{p.description}</p>
                                )}
                                {p.business_rationale && (
                                    <p className="text-xs text-[#1A2E1F] mt-1.5 italic">
                                        Why this matters: {p.business_rationale}
                                    </p>
                                )}
                                {p.synthesis_rationale && (
                                    <p className="text-[11px] text-[#6B6B6B] mt-1">
                                        {p.synthesis_rationale}
                                    </p>
                                )}
                                {p.surfaces_covered?.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-1.5">
                                        {p.surfaces_covered.map((s) => (
                                            <span
                                                key={s}
                                                className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded bg-white border border-[#E0DED8] text-[#4A4A4A] font-mono"
                                            >
                                                {s}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>

                <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[#E0DED8] bg-[#FBFAF6]">
                    <button
                        type="button"
                        onClick={onCancel}
                        disabled={busy}
                        className="px-4 py-2 text-sm font-semibold rounded-full border border-[#E0DED8] text-[#4A4A4A] hover:bg-white disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        onClick={onConfirm}
                        disabled={busy || picked.length === 0}
                        className="inline-flex items-center gap-1.5 px-5 py-2 text-sm font-semibold rounded-full bg-[#1A4D2E] text-white hover:bg-[#2D6B45] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                        <PlayIcon className="h-4 w-4" />
                        {busy ? 'Starting…' : 'Run'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PreviewModal;
