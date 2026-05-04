import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { collection, query, orderBy, limit, getDocs } from 'firebase/firestore';
import {
    ChartBarIcon,
    QueueListIcon,
    ChatBubbleLeftRightIcon,
    AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import { db } from '../firebase';
import RunNowPanel from '../components/qa/RunNowPanel';
import RunsTable from '../components/qa/RunsTable';
import ExecutiveSummary from '../components/qa/ExecutiveSummary';
import ScheduleEditor from '../components/qa/ScheduleEditor';
import ChatPanel from '../components/qa/ChatPanel';
import CoverageCard from '../components/qa/CoverageCard';
import ResolvedIssuesCard from '../components/qa/ResolvedIssuesCard';
import FeedbackPanel from '../components/qa/FeedbackPanel';
import DashboardHeader from '../components/qa/DashboardHeader';
import TabBar from '../components/qa/TabBar';
import { getSummary } from '../services/qaAgent';

// /qa-runs — admin-only QA dashboard.
//
// Reorganized 2026-05-04 into a tabbed layout (docs/prd/
// qa-dashboard-tabbed-layout.md). Tab state lives in the URL
// (?tab=overview|runs|ask|steer) so refresh and shared links land on
// the right tab. Each tab's content is lazy-mounted so non-visible
// tabs don't fire /summary or /feedback fetches on every page load.

const TAB_IDS = ['overview', 'runs', 'ask', 'steer'];
const DEFAULT_TAB = 'overview';

const QaRunsListPage = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const rawTab = searchParams.get('tab');
    const activeTab = TAB_IDS.includes(rawTab) ? rawTab : DEFAULT_TAB;

    const [runs, setRuns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    // /summary response — shared by ExecutiveSummary, CoverageCard,
    // ResolvedIssuesCard so all three render from a single Gemini-billable
    // fetch instead of three parallel ones.
    const [summaryResp, setSummaryResp] = useState(null);

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
            // Don't block run-list rendering on the summary fetch.
            getSummary().then((resp) => {
                if (resp?.success) setSummaryResp(resp);
            }).catch(() => {});
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

    const setTab = (tabId) => {
        // preserveExistingParams in case future query params get added.
        const next = new URLSearchParams(searchParams);
        next.set('tab', tabId);
        setSearchParams(next, { replace: false });
    };

    const runningCount = runs.filter((r) => r.status === 'running').length;

    const tabs = [
        { id: 'overview', label: 'Overview', icon: ChartBarIcon },
        { id: 'runs', label: 'Runs', icon: QueueListIcon, badge: runningCount },
        { id: 'ask', label: 'Ask', icon: ChatBubbleLeftRightIcon },
        { id: 'steer', label: 'Steer', icon: AdjustmentsHorizontalIcon },
    ];

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            <DashboardHeader runs={runs} />
            <TabBar tabs={tabs} activeId={activeTab} onChange={setTab} />

            <main className="max-w-6xl mx-auto px-6 py-6">
                {error && (
                    <div className="mb-4 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                        {error}
                    </div>
                )}

                {activeTab === 'overview' && (
                    <div
                        role="tabpanel"
                        id="tab-panel-overview"
                        aria-labelledby="tab-overview"
                        className="space-y-4"
                    >
                        <RunNowPanel onComplete={refresh} />
                        <ExecutiveSummary />
                        <CoverageCard coverage={summaryResp?.coverage} />
                        <ResolvedIssuesCard
                            resolvedIssues={summaryResp?.resolved_issues}
                        />
                    </div>
                )}

                {activeTab === 'runs' && (
                    <div
                        role="tabpanel"
                        id="tab-panel-runs"
                        aria-labelledby="tab-runs"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <h2 className="text-lg font-semibold text-[#1A2E1F]">
                                Recent runs
                                {runningCount > 0 && (
                                    <span className="ml-2 text-xs font-normal text-amber-700">
                                        ({runningCount} running)
                                    </span>
                                )}
                            </h2>
                            <button
                                type="button"
                                onClick={refresh}
                                className="text-sm font-semibold text-[#1A4D2E] hover:text-[#2D6B45] disabled:opacity-50"
                                disabled={loading}
                            >
                                {loading ? 'Refreshing…' : 'Refresh'}
                            </button>
                        </div>

                        {loading && runs.length === 0 ? (
                            <div className="bg-white rounded-xl border border-[#E0DED8] p-8 text-center text-sm text-[#8A8A8A]">
                                Loading…
                            </div>
                        ) : (
                            <RunsTable runs={runs} />
                        )}
                    </div>
                )}

                {activeTab === 'ask' && (
                    <div
                        role="tabpanel"
                        id="tab-panel-ask"
                        aria-labelledby="tab-ask"
                    >
                        <ChatPanel />
                    </div>
                )}

                {activeTab === 'steer' && (
                    <div
                        role="tabpanel"
                        id="tab-panel-steer"
                        aria-labelledby="tab-steer"
                        className="space-y-4"
                    >
                        <FeedbackPanel />
                        <RunNowPanel onComplete={refresh} />
                        <ScheduleEditor />
                    </div>
                )}
            </main>
        </div>
    );
};

export default QaRunsListPage;
