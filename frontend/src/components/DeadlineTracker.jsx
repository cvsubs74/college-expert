import React, { useState, useEffect } from 'react';
import {
    CalendarDaysIcon,
    ClockIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    ArrowPathIcon,
    ChevronDownIcon,
    AcademicCapIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';

// API Configuration
const PROFILE_MANAGER_ES_URL = import.meta.env.VITE_PROFILE_MANAGER_ES_URL ||
    'https://profile-manager-es-pfnwjfp26a-ue.a.run.app';

// Application plan options
const APPLICATION_PLANS = [
    { value: null, label: 'Not Set', color: 'gray' },
    { value: 'ED', label: 'Early Decision', color: 'purple', binding: true },
    { value: 'ED2', label: 'Early Decision II', color: 'purple', binding: true },
    { value: 'EA', label: 'Early Action', color: 'blue', binding: false },
    { value: 'REA', label: 'Restrictive EA', color: 'indigo', binding: false },
    { value: 'RD', label: 'Regular Decision', color: 'green', binding: false },
];

/**
 * DeadlineTracker - Timeline view of application deadlines for saved schools.
 * Shows countdown timers and allows users to set their application plan per school.
 */
const DeadlineTracker = ({ onSchoolClick }) => {
    const { currentUser } = useAuth();
    const [deadlines, setDeadlines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all'); // 'all', 'upcoming', 'myplan'
    const [updatingPlan, setUpdatingPlan] = useState(null);

    // Fetch deadlines on mount
    useEffect(() => {
        if (currentUser?.email) {
            fetchDeadlines();
        }
    }, [currentUser?.email]);

    const fetchDeadlines = async () => {
        if (!currentUser?.email) return;
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/get-deadlines`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_email: currentUser.email })
            });
            const data = await response.json();

            if (data.success) {
                setDeadlines(data.deadlines || []);
            } else {
                setError(data.error || 'Failed to load deadlines');
            }
        } catch (err) {
            setError('Network error loading deadlines');
            console.error('[DeadlineTracker] Error:', err);
        }
        setLoading(false);
    };

    const updatePlan = async (universityId, newPlan) => {
        if (!currentUser?.email) return;
        setUpdatingPlan(universityId);

        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/update-application-plan`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    application_plan: newPlan
                })
            });
            const data = await response.json();

            if (data.success) {
                // Refresh deadlines to get updated data
                fetchDeadlines();
            }
        } catch (err) {
            console.error('[DeadlineTracker] Update error:', err);
        }
        setUpdatingPlan(null);
    };

    // Calculate days until deadline
    const getDaysUntil = (dateStr) => {
        if (!dateStr) return null;
        const deadline = new Date(dateStr);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        deadline.setHours(0, 0, 0, 0);
        const diff = Math.ceil((deadline - today) / (1000 * 60 * 60 * 24));
        return diff;
    };

    // Get urgency level for styling
    const getUrgency = (daysUntil) => {
        if (daysUntil === null) return 'unknown';
        if (daysUntil < 0) return 'passed';
        if (daysUntil <= 7) return 'urgent';
        if (daysUntil <= 30) return 'soon';
        return 'normal';
    };

    // Get status colors
    const getStatusColors = (urgency, isUserPlan) => {
        const base = {
            passed: { bg: 'bg-gray-100', border: 'border-gray-300', text: 'text-gray-500', badge: 'bg-gray-200' },
            urgent: { bg: 'bg-red-50', border: 'border-red-300', text: 'text-red-700', badge: 'bg-red-100' },
            soon: { bg: 'bg-amber-50', border: 'border-amber-300', text: 'text-amber-700', badge: 'bg-amber-100' },
            normal: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100' },
            unknown: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', badge: 'bg-gray-100' }
        };
        const colors = base[urgency] || base.unknown;
        if (isUserPlan) {
            colors.ring = 'ring-2 ring-blue-400';
        }
        return colors;
    };

    // Format date for display
    const formatDate = (dateStr) => {
        if (!dateStr) return 'TBD';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric'
            });
        } catch {
            return dateStr;
        }
    };

    // Filter deadlines
    const filteredDeadlines = deadlines.filter(d => {
        if (filter === 'upcoming') {
            const days = getDaysUntil(d.date);
            return days !== null && days >= 0;
        }
        if (filter === 'myplan') {
            return d.is_user_plan;
        }
        return true;
    });

    // Group by university for display
    const groupedByUniversity = {};
    filteredDeadlines.forEach(d => {
        if (!groupedByUniversity[d.university_id]) {
            groupedByUniversity[d.university_id] = {
                university_name: d.university_name,
                university_id: d.university_id,
                user_application_plan: d.user_application_plan,
                deadlines: []
            };
        }
        groupedByUniversity[d.university_id].deadlines.push(d);
    });

    if (loading) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-center gap-3 text-gray-500">
                    <ArrowPathIcon className="h-5 w-5 animate-spin" />
                    <span>Loading deadlines...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="text-center text-red-500">
                    <ExclamationTriangleIcon className="h-8 w-8 mx-auto mb-2" />
                    <p>{error}</p>
                    <button
                        onClick={fetchDeadlines}
                        className="mt-3 text-sm text-blue-600 hover:underline"
                    >
                        Try again
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="px-5 py-4 border-b border-gray-200 bg-gradient-to-r from-indigo-50 to-purple-50">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-100 rounded-lg">
                            <CalendarDaysIcon className="h-5 w-5 text-indigo-600" />
                        </div>
                        <div>
                            <h2 className="font-semibold text-gray-900">Application Deadlines</h2>
                            <p className="text-xs text-gray-500">{deadlines.length} deadlines from {Object.keys(groupedByUniversity).length} schools</p>
                        </div>
                    </div>
                    <button
                        onClick={fetchDeadlines}
                        className="p-2 hover:bg-white/50 rounded-lg transition-colors"
                        title="Refresh"
                    >
                        <ArrowPathIcon className="h-4 w-4 text-gray-500" />
                    </button>
                </div>

                {/* Filter tabs */}
                <div className="flex gap-2 mt-3">
                    {[
                        { key: 'all', label: 'All' },
                        { key: 'upcoming', label: 'Upcoming' },
                        { key: 'myplan', label: 'My Plans' },
                    ].map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => setFilter(tab.key)}
                            className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${filter === tab.key
                                    ? 'bg-indigo-600 text-white'
                                    : 'bg-white text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Deadline list */}
            <div className="divide-y divide-gray-100 max-h-[500px] overflow-y-auto">
                {Object.keys(groupedByUniversity).length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <CalendarDaysIcon className="h-10 w-10 mx-auto mb-3 opacity-50" />
                        <p>No deadlines found</p>
                        <p className="text-xs mt-1">Save some schools to see their deadlines</p>
                    </div>
                ) : (
                    Object.values(groupedByUniversity).map(uni => (
                        <div key={uni.university_id} className="p-4">
                            {/* University header */}
                            <div className="flex items-center justify-between mb-3">
                                <div
                                    className="flex items-center gap-2 cursor-pointer hover:text-indigo-600 transition-colors"
                                    onClick={() => onSchoolClick?.(uni.university_id)}
                                >
                                    <AcademicCapIcon className="h-4 w-4 text-gray-400" />
                                    <span className="font-medium text-gray-800 text-sm">{uni.university_name}</span>
                                </div>

                                {/* Plan selector */}
                                <div className="relative">
                                    <select
                                        value={uni.user_application_plan || ''}
                                        onChange={(e) => updatePlan(uni.university_id, e.target.value || null)}
                                        disabled={updatingPlan === uni.university_id}
                                        className={`text-xs pl-2 pr-6 py-1 rounded border appearance-none cursor-pointer transition-colors ${uni.user_application_plan
                                                ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                                                : 'bg-gray-50 border-gray-200 text-gray-500'
                                            } ${updatingPlan === uni.university_id ? 'opacity-50' : ''}`}
                                    >
                                        {APPLICATION_PLANS.map(plan => (
                                            <option key={plan.value || 'none'} value={plan.value || ''}>
                                                {plan.label}
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDownIcon className="h-3 w-3 absolute right-1.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                                </div>
                            </div>

                            {/* Deadlines for this university */}
                            <div className="space-y-2 ml-6">
                                {uni.deadlines.map((deadline, idx) => {
                                    const daysUntil = getDaysUntil(deadline.date);
                                    const urgency = getUrgency(daysUntil);
                                    const colors = getStatusColors(urgency, deadline.is_user_plan);

                                    return (
                                        <div
                                            key={idx}
                                            className={`flex items-center justify-between px-3 py-2 rounded-lg border ${colors.bg} ${colors.border} ${colors.ring || ''}`}
                                        >
                                            <div className="flex items-center gap-3">
                                                {urgency === 'passed' ? (
                                                    <CheckCircleIcon className="h-4 w-4 text-gray-400" />
                                                ) : (
                                                    <ClockIcon className={`h-4 w-4 ${colors.text}`} />
                                                )}
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className={`text-sm font-medium ${urgency === 'passed' ? 'text-gray-500' : 'text-gray-800'}`}>
                                                            {deadline.plan_type}
                                                        </span>
                                                        {deadline.is_binding && (
                                                            <span className="text-[10px] px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded font-medium">
                                                                BINDING
                                                            </span>
                                                        )}
                                                        {deadline.is_user_plan && (
                                                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded font-medium">
                                                                YOUR PLAN
                                                            </span>
                                                        )}
                                                    </div>
                                                    <span className="text-xs text-gray-500">{formatDate(deadline.date)}</span>
                                                </div>
                                            </div>

                                            {/* Countdown */}
                                            <div className={`text-right ${colors.text}`}>
                                                {daysUntil !== null && (
                                                    <div className="text-sm font-bold">
                                                        {daysUntil < 0
                                                            ? 'Passed'
                                                            : daysUntil === 0
                                                                ? 'Today!'
                                                                : `${daysUntil}d`
                                                        }
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default DeadlineTracker;
