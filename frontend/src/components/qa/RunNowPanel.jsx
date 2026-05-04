import React, { useState } from 'react';
import { PlayIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { triggerRun } from '../../services/qaAgent';
import { useAuth } from '../../context/AuthContext';

// "Run now" — kicks off a fresh batch the synthesizer + corpus picks
// on each call. The previous version had a single-archetype dropdown,
// but the agent's job is to choose intelligently across past runs and
// system context; manual selection cut against that goal. Removed
// 2026-05 — backend still accepts {scenario: <id>} if needed for
// debugging, but it's no longer surfaced in the UI.

const RunNowPanel = ({ onComplete }) => {
    const { currentUser } = useAuth();
    const [busy, setBusy] = useState(false);
    const [lastResult, setLastResult] = useState(null);
    const [error, setError] = useState(null);

    const handleRun = async () => {
        setBusy(true);
        setError(null);
        try {
            const result = await triggerRun({
                scenarioId: null,
                actor: currentUser?.email || '',
            });
            setLastResult(result);
            if (onComplete) onComplete(result);
        } catch (err) {
            setError(err.message || 'Run failed');
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="bg-white rounded-xl border border-[#E0DED8] p-5">
            <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
                <div>
                    <h2 className="text-lg font-semibold text-[#1A4D2E]">Run now</h2>
                    <p className="text-xs text-[#8A8A8A] mt-0.5">
                        Agent picks scenarios based on recent runs + system context.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={handleRun}
                    disabled={busy}
                    className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#1A4D2E] text-white text-sm font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {busy ? (
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
    );
};

export default RunNowPanel;
