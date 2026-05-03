import React, { useEffect, useState } from 'react';
import { PlayIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { listScenarios, triggerRun } from '../../services/qaAgent';
import { useAuth } from '../../context/AuthContext';

// "Run now" widget. Lets an admin kick off a fresh batch or pick a
// single archetype. Disabled while a request is in flight (single-flight
// per tab).

const RunNowPanel = ({ onComplete }) => {
    const { currentUser } = useAuth();
    const [scenarios, setScenarios] = useState([]);
    const [scenarioId, setScenarioId] = useState('');
    const [busy, setBusy] = useState(false);
    const [lastResult, setLastResult] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        listScenarios()
            .then((data) => {
                if (!cancelled) setScenarios(data?.scenarios || []);
            })
            .catch(() => {
                /* non-fatal — picker just stays empty */
            });
        return () => { cancelled = true; };
    }, []);

    const handleRun = async () => {
        setBusy(true);
        setError(null);
        try {
            const result = await triggerRun({
                scenarioId: scenarioId || null,
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
            <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-lg font-semibold text-[#1A4D2E]">Run now</h2>
                <span className="text-xs text-[#8A8A8A]">
                    {scenarios.length
                        ? `${scenarios.length} scenarios available`
                        : 'loading scenarios…'}
                </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                <select
                    className="flex-1 border border-[#E0DED8] rounded-lg px-3 py-2 text-sm bg-[#FBFAF6] focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/30"
                    value={scenarioId}
                    onChange={(e) => setScenarioId(e.target.value)}
                    disabled={busy}
                >
                    <option value="">All scenarios (random batch)</option>
                    {scenarios.map((s) => (
                        <option key={s.id} value={s.id}>
                            {s.id} — {s.description.slice(0, 60)}
                        </option>
                    ))}
                </select>

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
