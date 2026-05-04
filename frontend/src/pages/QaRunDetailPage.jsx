import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { doc, getDoc } from 'firebase/firestore';
import { ArrowLeftIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { db } from '../firebase';
import PassFailBadge from '../components/qa/PassFailBadge';
import ScenarioCard from '../components/qa/ScenarioCard';
import TestPlanCard from '../components/qa/TestPlanCard';
import OutcomeCard from '../components/qa/OutcomeCard';

// /qa-runs/:runId — drill-down for a single run.
//
// When the run's status is "running", this page polls Firestore every
// 5 seconds so the operator can watch results land. Once the doc
// flips to status="complete", polling stops and the existing
// rendering (pass/fail badge + outcome card) takes over.

const POLL_INTERVAL_MS = 5000;

const RunningHeaderBadge = () => (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full bg-amber-50 border border-amber-200 text-amber-800">
        <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />
        Running
    </span>
);

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
        let pollTimer = null;

        const fetchOnce = async () => {
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
        };

        const tick = async () => {
            await fetchOnce();
            if (cancelled) return;
            // Continue polling only while the run is in flight. Once
            // status flips off "running" we stop — Firestore writes are
            // expensive and we don't need updates after completion.
            // Read latest state via the closure-captured setRun callback
            // — we can't trust `run` here because of stale-closure.
            const refreshed = await getDoc(doc(db, 'qa_runs', runId));
            if (cancelled) return;
            if (refreshed.exists() && refreshed.data().status === 'running') {
                pollTimer = setTimeout(tick, POLL_INTERVAL_MS);
            }
        };

        fetchOnce().then(() => {
            if (cancelled) return;
            // Schedule the first poll only if the doc loaded as running.
            getDoc(doc(db, 'qa_runs', runId)).then((snap) => {
                if (cancelled || !snap.exists()) return;
                if (snap.data().status === 'running') {
                    pollTimer = setTimeout(tick, POLL_INTERVAL_MS);
                }
            }).catch(() => {});
        });

        return () => {
            cancelled = true;
            if (pollTimer) clearTimeout(pollTimer);
        };
    }, [runId]);

    const isRunning = run?.status === 'running';

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
                        {run && (
                            isRunning
                                ? <RunningHeaderBadge />
                                : <PassFailBadge summary={run.summary} size="lg" />
                        )}
                    </div>
                    {run && (
                        <div className="text-xs text-[#6B6B6B] mt-1">
                            {fmtDate(run.started_at)} · {run.trigger || '—'} by{' '}
                            <span className="font-mono">{run.actor || '—'}</span>
                            {!isRunning && ` · ${fmtDuration(run.duration_ms)}`}
                            {isRunning && ' · (in progress, refreshing every 5s)'}
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
