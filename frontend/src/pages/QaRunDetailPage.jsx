import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { doc, getDoc } from 'firebase/firestore';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { db } from '../firebase';
import PassFailBadge from '../components/qa/PassFailBadge';
import ScenarioCard from '../components/qa/ScenarioCard';
import TestPlanCard from '../components/qa/TestPlanCard';
import OutcomeCard from '../components/qa/OutcomeCard';

// /qa-runs/:runId — drill-down for a single run.

const fmtDate = (iso) => {
    if (!iso) return '—';
    try {
        return new Date(iso).toLocaleString();
    } catch {
        return iso;
    }
};

const fmtDuration = (ms) => {
    if (!ms) return '—';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
};

const QaRunDetailPage = () => {
    const { runId } = useParams();
    const [run, setRun] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        document.title = `QA Run ${runId} — Stratia Admin`;
        let cancelled = false;
        (async () => {
            try {
                const ref = doc(db, 'qa_runs', runId);
                const snap = await getDoc(ref);
                if (cancelled) return;
                if (!snap.exists()) {
                    setError('Run not found.');
                } else {
                    setRun(snap.data());
                }
            } catch (err) {
                if (!cancelled) setError(err.message || 'Failed to load run');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [runId]);

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            <header className="bg-white border-b border-[#E0DED8] sticky top-0 z-40">
                <div className="max-w-5xl mx-auto px-6 py-4">
                    <Link
                        to="/qa-runs"
                        className="inline-flex items-center gap-1 text-xs font-semibold text-[#1A4D2E] hover:text-[#2D6B45] mb-2"
                    >
                        <ArrowLeftIcon className="h-3.5 w-3.5" />
                        All runs
                    </Link>
                    <div className="flex items-baseline gap-3 flex-wrap">
                        <h1 className="text-xl font-bold text-[#1A2E1F] font-mono">
                            {runId}
                        </h1>
                        {run && <PassFailBadge summary={run.summary} size="lg" />}
                    </div>
                    {run && (
                        <div className="text-xs text-[#6B6B6B] mt-1">
                            {fmtDate(run.started_at)} · {run.trigger || '—'} by{' '}
                            <span className="font-mono">{run.actor || '—'}</span> ·{' '}
                            {fmtDuration(run.duration_ms)}
                        </div>
                    )}
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-6 py-6 space-y-3">
                {loading && (
                    <div className="bg-white rounded-xl border border-[#E0DED8] p-6 text-sm text-[#8A8A8A]">
                        Loading…
                    </div>
                )}
                {error && (
                    <div className="bg-rose-50 border border-rose-200 rounded-lg px-4 py-3 text-sm text-rose-700">
                        {error}
                    </div>
                )}
                {run?.test_plan && <TestPlanCard testPlan={run.test_plan} />}

                {run && run.scenarios?.map((scenario) => (
                    <div
                        key={scenario.scenario_id}
                        id={`scenario-${scenario.scenario_id}`}
                    >
                        <ScenarioCard runId={runId} scenario={scenario} />
                    </div>
                ))}
                {run && (!run.scenarios || run.scenarios.length === 0) && (
                    <div className="bg-white rounded-xl border border-[#E0DED8] p-6 text-sm text-[#8A8A8A]">
                        No scenarios in this run.
                    </div>
                )}

                {run?.outcome && <OutcomeCard outcome={run.outcome} />}
            </main>
        </div>
    );
};

export default QaRunDetailPage;
