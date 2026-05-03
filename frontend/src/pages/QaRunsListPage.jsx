import React, { useEffect, useState, useCallback } from 'react';
import { collection, query, orderBy, limit, getDocs } from 'firebase/firestore';
import { db } from '../firebase';
import SparklineByDay from '../components/qa/SparklineByDay';
import RunNowPanel from '../components/qa/RunNowPanel';
import RunsTable from '../components/qa/RunsTable';

// /qa-runs — admin-only list of recent QA runs.
//
// Reads directly from Firestore via the Firebase SDK, gated by
// security rules on qa_runs/. The frontend's AdminGate already 404s
// non-admins; the rules are the hard gate at the data layer.

const QaRunsListPage = () => {
    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const refresh = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const q = query(
                collection(db, 'qa_runs'),
                orderBy('started_at', 'desc'),
                limit(50),
            );
            const snap = await getDocs(q);
            const data = snap.docs.map((d) => d.data());
            setRuns(data);
        } catch (err) {
            setError(err.message || 'Failed to load runs');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        document.title = 'QA Runs — Stratia Admin';
        refresh();
    }, [refresh]);

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            <header className="bg-white border-b border-[#E0DED8] sticky top-0 z-40">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div>
                        <h1 className="text-xl font-bold text-[#1A4D2E]">QA Agent</h1>
                        <p className="text-xs text-[#8A8A8A]">Internal — synthetic monitoring runs</p>
                    </div>
                    <SparklineByDay runs={runs} />
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-6 space-y-6">
                <RunNowPanel onComplete={refresh} />

                <div>
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="text-lg font-semibold text-[#1A2E1F]">Recent runs</h2>
                        <button
                            type="button"
                            onClick={refresh}
                            className="text-sm font-semibold text-[#1A4D2E] hover:text-[#2D6B45]"
                            disabled={loading}
                        >
                            {loading ? 'Refreshing…' : 'Refresh'}
                        </button>
                    </div>

                    {error && (
                        <div className="mb-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                            {error}
                        </div>
                    )}

                    {loading && runs.length === 0 ? (
                        <div className="bg-white rounded-xl border border-[#E0DED8] p-8 text-center text-sm text-[#8A8A8A]">
                            Loading…
                        </div>
                    ) : (
                        <RunsTable runs={runs} />
                    )}
                </div>
            </main>
        </div>
    );
};

export default QaRunsListPage;
