import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
    SparklesIcon,
    PencilSquareIcon,
    AcademicCapIcon,
    BuildingLibraryIcon,
    ExclamationTriangleIcon,
    PlusIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { fetchStudentRoadmap, fetchUserProfile } from '../services/api';
import { useToast } from '../components/Toast';
import RoadmapView from '../components/counselor/RoadmapView';
import ThisWeekFocusCard from '../components/roadmap/ThisWeekFocusCard';
import FloatingCounselorChat from '../components/roadmap/FloatingCounselorChat';
import AddTaskModal from '../components/roadmap/AddTaskModal';
import EssayDashboard from './EssayDashboard';
import ScholarshipTracker from './ScholarshipTracker';
import ApplicationsPage from './ApplicationsPage';

// Compute the current academic semester client-side using the same rule
// the backend resolver uses (planner.py semester_from_date). Both ends
// must agree on the boundaries so the rendered "Senior Fall" / "Senior
// Spring" label matches what the user actually gets.
const computeCurrentSemester = (now = new Date()) => {
    const m = now.getMonth() + 1; // JS months are 0-indexed
    if (m >= 8 && m <= 12) return 'fall';
    if (m >= 1 && m <= 5) return 'spring';
    return 'summer';
};

// Default grade hint when the user's profile lacks one. We surface a
// one-toast nudge (per-session) prompting them to complete their profile;
// the backend resolver will fall back to graduation_year-based inference
// regardless, so this default is purely a labeling fallback.
const DEFAULT_GRADE_LEVEL = '11th Grade';

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

            {/* Floating counselor chat. Lives at the page level (not inside
                the tab-content render) so its in-component state survives
                tab switches. */}
            <FloatingCounselorChat />
        </div>
    );
};

// PlanTab keeps the roadmap-fetch logic colocated so RoadmapPage stays a
// pure router-of-tabs.
const PlanTab = ({ userEmail }) => {
    const toast = useToast();
    const [roadmap, setRoadmap] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isAddTaskOpen, setIsAddTaskOpen] = useState(false);

    // Bumped after a manual task is saved to force ThisWeekFocusCard to
    // refetch /work-feed so the new task shows up immediately.
    const [focusCardRefreshKey, setFocusCardRefreshKey] = useState(0);

    useEffect(() => {
        if (!userEmail) return;

        let cancelled = false;
        const load = async () => {
            try {
                setLoading(true);

                // Resolve grade and semester client-side. When BOTH are passed,
                // the backend resolver (counselor_agent /roadmap, M1 PR #3)
                // takes the 'caller' path. When grade is missing, we still
                // pass our computed semester — the resolver treats one-of-two
                // as "neither" and falls back to profile.graduation_year, so
                // we don't get a wrong-grade template.
                const profileResult = await fetchUserProfile(userEmail);
                if (cancelled) return;

                const profile = profileResult?.profile || {};
                const grade = (profile.grade || '').trim();
                const semester = computeCurrentSemester();
                let gradeLevel = grade || DEFAULT_GRADE_LEVEL;

                // One-shot warning when the profile has no grade. Per-session
                // flag so we don't badger the user on every Plan-tab visit.
                if (!grade) {
                    const warnedKey = `roadmap_grade_warning_${userEmail}`;
                    if (!sessionStorage.getItem(warnedKey)) {
                        toast.info(
                            'Add your grade to your profile',
                            'Your roadmap is using a default grade. Update your profile so it matches where you actually are.',
                            8000,
                        );
                        sessionStorage.setItem(warnedKey, '1');
                    }
                    // We still send a default grade so the request shape is
                    // consistent; backend will fall back to graduation_year
                    // since (default_grade + computed_semester) is a hint
                    // not a guarantee of correctness.
                    gradeLevel = DEFAULT_GRADE_LEVEL;
                }

                const data = await fetchStudentRoadmap(userEmail, gradeLevel, semester);
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
    }, [userEmail, toast]);

    return (
        <>
            {/* Action row sits above the focus card so users can add a task
                without scrolling past their week's work. */}
            <div className="flex items-center justify-end mb-3">
                <button
                    type="button"
                    onClick={() => setIsAddTaskOpen(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                        text-[#1A4D2E] bg-[#D6E8D5]/40 hover:bg-[#D6E8D5]
                        rounded-full transition-colors"
                >
                    <PlusIcon className="w-4 h-4" />
                    Add task
                </button>
            </div>

            <ThisWeekFocusCard userEmail={userEmail} refreshKey={focusCardRefreshKey} />
            {error ? (
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
            ) : (
                <RoadmapView roadmap={roadmap} isLoading={loading} />
            )}

            <AddTaskModal
                userEmail={userEmail}
                isOpen={isAddTaskOpen}
                onClose={() => setIsAddTaskOpen(false)}
                onSaved={() => setFocusCardRefreshKey((k) => k + 1)}
            />
        </>
    );
};

export default RoadmapPage;
