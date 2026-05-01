import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    SparklesIcon,
    PencilSquareIcon,
    AcademicCapIcon,
    BuildingLibraryIcon,
    ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { fetchStudentRoadmap } from '../services/api';
import RoadmapView from '../components/counselor/RoadmapView';
import EssayDashboard from './EssayDashboard';
import ScholarshipTracker from './ScholarshipTracker';
import ApplicationsPage from './ApplicationsPage';

// Tabs for the consolidated Roadmap surface. Order matches the design doc:
// Plan / Essays / Scholarships / Colleges. The This Week focus card lands
// inside the Plan tab in M1 PR #5; for now Plan just renders the existing
// semester roadmap timeline. Notes affordances land in M1 PR #6.
const TABS = [
    { id: 'plan', label: 'Plan', icon: SparklesIcon },
    { id: 'essays', label: 'Essays', icon: PencilSquareIcon },
    { id: 'scholarships', label: 'Scholarships', icon: AcademicCapIcon },
    { id: 'colleges', label: 'Colleges', icon: BuildingLibraryIcon },
];
const TAB_IDS = TABS.map((t) => t.id);
const DEFAULT_TAB = 'plan';

const RoadmapPage = () => {
    const { currentUser } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();

    // URL is the source of truth for which tab is active. Unknown / missing
    // values fall back to the default tab. Tab clicks use `replace` so the
    // back button doesn't have to traverse every visit.
    const requestedTab = searchParams.get('tab');
    const activeTab = TAB_IDS.includes(requestedTab) ? requestedTab : DEFAULT_TAB;

    const handleTabClick = (tabId) => {
        const next = new URLSearchParams(searchParams);
        next.set('tab', tabId);
        setSearchParams(next, { replace: true });
    };

    return (
        <div className="min-h-screen">
            {/* Page Header */}
            <div className="mb-6">
                <h1 className="font-serif text-3xl font-bold text-[#2C2C2C]">Roadmap</h1>
                <p className="text-[#6B6B6B] mt-1">
                    Your plan, essays, scholarships, and per-college progress in one place.
                </p>
            </div>

            {/* Tab Navigation — pattern lifted from the existing ProgressPage so
                the active-state styling stays consistent across the app. */}
            <div className="border-b border-[#E0DED8] mb-6">
                <nav className="flex gap-1" aria-label="Roadmap sections">
                    {TABS.map((tab) => {
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                onClick={() => handleTabClick(tab.id)}
                                aria-current={isActive ? 'page' : undefined}
                                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all relative
                                    ${isActive
                                        ? 'text-[#1A4D2E]'
                                        : 'text-[#6B6B6B] hover:text-[#4A4A4A]'
                                    }`}
                            >
                                <tab.icon className="w-5 h-5" />
                                {tab.label}
                                {isActive && (
                                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1A4D2E] rounded-full" />
                                )}
                            </button>
                        );
                    })}
                </nav>
            </div>

            {/* Tab Content. Mounting/unmounting per-tab is intentional —
                each subview owns its own data fetch and we want a fresh fetch
                when the user lands on a tab, not a stale render. */}
            <div className="animate-fade-up">
                {activeTab === 'plan' && <PlanTab userEmail={currentUser?.email} />}
                {activeTab === 'essays' && <EssayDashboard embedded />}
                {activeTab === 'scholarships' && <ScholarshipTracker embedded />}
                {activeTab === 'colleges' && <ApplicationsPage embedded />}
            </div>
        </div>
    );
};

// PlanTab keeps the roadmap-fetch logic colocated so RoadmapPage stays a
// pure router-of-tabs. The "This Week" focus card slots in above
// <RoadmapView> in M1 PR #5; until then this is just the existing
// semester roadmap timeline.
const PlanTab = ({ userEmail }) => {
    const [roadmap, setRoadmap] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!userEmail) return;

        let cancelled = false;
        const load = async () => {
            try {
                setLoading(true);
                // Note: still passing only the legacy '11th Grade' hint here.
                // M1 PR #7 wires this to profile.grade_level + computed semester
                // so the backend's new resolver (PR #3) takes the caller path.
                const data = await fetchStudentRoadmap(userEmail, '11th Grade');
                if (cancelled) return;
                if (data.success) {
                    setRoadmap(data.roadmap);
                    setError(null);
                } else {
                    setError(data.error || 'Failed to load roadmap');
                }
            } catch (err) {
                if (!cancelled) setError(err.message);
            } finally {
                if (!cancelled) setLoading(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [userEmail]);

    if (error) {
        return (
            <div className="bg-red-50 p-4 rounded-xl border border-red-100 flex items-start gap-3">
                <ExclamationTriangleIcon className="h-5 w-5 text-red-600 mt-0.5" />
                <div>
                    <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                    <p className="text-sm text-red-600 mt-1">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="mt-2 text-xs font-medium text-red-700 hover:text-red-900 underline"
                    >
                        Retry Connection
                    </button>
                </div>
            </div>
        );
    }

    return <RoadmapView roadmap={roadmap} isLoading={loading} />;
};

export default RoadmapPage;
