import React, { useState } from 'react';
import { PlayIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { triggerRun, getRunPreview } from '../../services/qaAgent';
import { useAuth } from '../../context/AuthContext';
import PreviewModal from './PreviewModal';

// "Run now" — clicking previews the picks first via /run/preview, then
// on confirm fires the actual /run. The agent's choices are surfaced in
// the modal so the user can see what's about to be tested before
// committing 2-3 minutes of test-user state churn.
//
// Spec: docs/prd/qa-run-preview-and-running-state.md.

const RunNowPanel = ({ onComplete }) => {
    const { currentUser } = useAuth();
    // 'idle' → 'previewing' → 'preview-ready' (modal open) → 'running'
    // → back to 'idle' on completion/error.
    const [phase, setPhase] = useState('idle');
    const [preview, setPreview] = useState(null);
    const [lastResult, setLastResult] = useState(null);
    const [error, setError] = useState(null);

    const handleRunClick = async () => {
        setPhase('previewing');
        setError(null);
        try {
            const resp = await getRunPreview({});
            if (resp?.success) {
                setPreview(resp);
                setPhase('preview-ready');
            } else {
                setError(resp?.error || 'Preview failed');
                setPhase('idle');
            }
        } catch (err) {
            setError(err.message || 'Preview failed');
            setPhase('idle');
        }
    };

    const handleConfirm = async () => {
        setPhase('running');
        setError(null);
        try {
            // Refresh the run list immediately so the new "running" doc
            // shows up in the table while /run is still in flight.
            // The 200-300ms delay before the doc appears is hidden by
            // the modal's "Starting…" state.
            if (onComplete) {
                // Optimistic refresh after a short delay so the running
                // doc has time to be written.
                setTimeout(() => onComplete && onComplete(null), 800);
            }
            const result = await triggerRun({
                scenarioId: null,
                actor: currentUser?.email || '',
            });
            setLastResult(result);
            setPreview(null);
            // Final refresh once /run completes so the row flips to
            // pass/fail and the table re-orders.
            if (onComplete) onComplete(result);
        } catch (err) {
            setError(err.message || 'Run failed');
        } finally {
            setPhase('idle');
        }
    };

    const handleCancel = () => {
        setPreview(null);
        setPhase('idle');
    };

    const busy = phase === 'previewing' || phase === 'running';

    return (
        <>
            <div className="bg-white rounded-xl border border-[#E0DED8] p-5">
                <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
                    <div>
                        <h2 className="text-lg font-semibold text-[#1A4D2E]">Run now</h2>
                        <p className="text-xs text-[#8A8A8A] mt-0.5">
                            Agent picks scenarios based on recent runs + system context.
                            You'll see the picks before committing.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={handleRunClick}
                        disabled={busy}
                        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#1A4D2E] text-white text-sm font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {phase === 'previewing' ? (
                            <>
                                <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                Loading preview…
                            </>
                        ) : phase === 'running' ? (
                            <>
                                <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                Running…
                            </>
                        ) : (
                            <>
                                <PlayIcon className="h-4 w-4" />
                                Run now
                            </>
                        )}
                    </button>
                </div>

                {error && (
                    <div className="mt-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                        {error}
                    </div>
                )}
                {lastResult && (
                    <div className="mt-3 text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                        <span className="font-semibold">Run {lastResult.run_id}</span>: {lastResult.summary?.pass}/{lastResult.summary?.total} passed
                    </div>
                )}
            </div>

            {phase === 'preview-ready' && preview && (
                <PreviewModal
                    picked={preview.picked || []}
                    synthCount={preview.synth_count || 0}
                    staticCount={preview.static_count || 0}
                    busy={false}
                    onConfirm={handleConfirm}
                    onCancel={handleCancel}
                />
            )}
        </>
    );
};

export default RunNowPanel;
