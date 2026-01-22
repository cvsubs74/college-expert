import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { syncScholarshipTracker, getScholarshipTracker, updateScholarshipStatus } from '../services/api';
import {
    BanknotesIcon,
    CheckCircleIcon,
    ClockIcon,
    XCircleIcon,
    ArrowPathIcon,
    AcademicCapIcon,
    SparklesIcon,
    CalendarIcon,
    ChevronDownIcon,
    ChevronRightIcon,
    InformationCircleIcon
} from '@heroicons/react/24/outline';

// Status configurations
const STATUS_CONFIG = {
    not_applied: { label: 'Not Applied', bg: 'bg-stone-100', text: 'text-stone-600', icon: ClockIcon },
    applied: { label: 'Applied', bg: 'bg-blue-100', text: 'text-blue-700', icon: CheckCircleIcon },
    received: { label: 'Received', bg: 'bg-emerald-100', text: 'text-emerald-700', icon: BanknotesIcon },
    not_eligible: { label: 'Not Eligible', bg: 'bg-red-100', text: 'text-red-600', icon: XCircleIcon }
};

// Eligibility indicator configurations
const ELIGIBILITY_CONFIG = {
    likely_eligible: { label: 'Likely Eligible', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    may_qualify: { label: 'May Qualify', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
    unknown: { label: 'Check Eligibility', bg: 'bg-stone-50', text: 'text-stone-600', border: 'border-stone-200' }
};

// Type configurations
const TYPE_CONFIG = {
    Need: { label: 'Need-Based', icon: BanknotesIcon, color: 'text-blue-600' },
    Merit: { label: 'Merit-Based', icon: AcademicCapIcon, color: 'text-purple-600' },
    Specific: { label: 'Specific', icon: SparklesIcon, color: 'text-amber-600' }
};

const ScholarshipTracker = ({ embedded = false }) => {
    const { currentUser: user } = useAuth();
    const [scholarships, setScholarships] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSyncing, setIsSyncing] = useState(false);
    const [filter, setFilter] = useState('all');
    const [expandedSchools, setExpandedSchools] = useState({});

    useEffect(() => {
        if (user?.email) {
            syncAndLoad();
        }
    }, [user]);

    const syncAndLoad = async () => {
        if (!user?.email) return;
        setIsLoading(true);
        setIsSyncing(true);
        try {
            const syncResult = await syncScholarshipTracker(user.email);
            if (syncResult.success && syncResult.scholarships) {
                setScholarships(syncResult.scholarships);
                // Auto-expand all schools
                const schools = [...new Set(syncResult.scholarships.map(s => s.university_id))];
                setExpandedSchools(Object.fromEntries(schools.map(s => [s, true])));
            } else {
                const result = await getScholarshipTracker(user.email);
                if (result.success && result.scholarships) {
                    setScholarships(result.scholarships);
                }
            }
        } catch (error) {
            console.error('Failed to sync scholarships:', error);
        } finally {
            setIsLoading(false);
            setIsSyncing(false);
        }
    };

    const handleStatusChange = async (scholarshipId, newStatus) => {
        if (!user?.email) return;

        setScholarships(prev => prev.map(s =>
            s.scholarship_id === scholarshipId ? { ...s, status: newStatus } : s
        ));

        const result = await updateScholarshipStatus(user.email, scholarshipId, newStatus);
        if (!result.success) {
            syncAndLoad();
        }
    };

    const toggleSchool = (schoolId) => {
        setExpandedSchools(prev => ({ ...prev, [schoolId]: !prev[schoolId] }));
    };

    // Group by university
    const groupedBySchool = scholarships.reduce((acc, s) => {
        const key = s.university_id || 'general';
        if (!acc[key]) {
            acc[key] = { name: s.university_name || key, scholarships: [] };
        }
        acc[key].scholarships.push(s);
        return acc;
    }, {});

    // Filter
    const filterScholarships = (list) => {
        return list.filter(s => filter === 'all' || s.status === filter);
    };

    // Stats
    const stats = {
        total: scholarships.length,
        not_applied: scholarships.filter(s => s.status === 'not_applied' || !s.status).length,
        applied: scholarships.filter(s => s.status === 'applied').length,
        received: scholarships.filter(s => s.status === 'received').length
    };

    return (
        <div className={embedded ? '' : 'min-h-screen bg-gradient-to-b from-[#FDFCF7] to-stone-50'}>
            <div className={embedded ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
                {!embedded && (
                    <div className="mb-8">
                        <h1 className="text-3xl font-serif font-medium text-[#1A4D2E]">Available Scholarships</h1>
                        <p className="text-stone-600 mt-2">Scholarships from your selected colleges, auto-synced from our database.</p>
                    </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                    <div className="bg-white rounded-xl p-4 border border-stone-200 shadow-sm">
                        <div className="text-2xl font-bold text-stone-800">{stats.total}</div>
                        <div className="text-sm text-stone-500">Total Available</div>
                    </div>
                    <div className="bg-stone-50 rounded-xl p-4 border border-stone-200">
                        <div className="text-2xl font-bold text-stone-600">{stats.not_applied}</div>
                        <div className="text-sm text-stone-500">To Review</div>
                    </div>
                    <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
                        <div className="text-2xl font-bold text-blue-700">{stats.applied}</div>
                        <div className="text-sm text-blue-600">Applied</div>
                    </div>
                    <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200">
                        <div className="text-2xl font-bold text-emerald-700">{stats.received}</div>
                        <div className="text-sm text-emerald-600">Received</div>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-3 mb-6">
                    <div className="flex gap-2">
                        {['all', 'not_applied', 'applied', 'received'].map((f) => (
                            <button
                                key={f}
                                onClick={() => setFilter(f)}
                                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors
                                    ${filter === f
                                        ? 'bg-[#1A4D2E] text-white'
                                        : 'bg-white border border-stone-300 text-stone-600 hover:bg-stone-50'}`}
                            >
                                {f === 'all' ? 'All' : STATUS_CONFIG[f]?.label || f}
                            </button>
                        ))}
                    </div>
                    <button
                        onClick={syncAndLoad}
                        disabled={isSyncing}
                        className="p-2 text-stone-500 hover:text-[#1A4D2E] hover:bg-stone-100 rounded-lg disabled:opacity-50 ml-auto"
                        title="Sync from college list"
                    >
                        <ArrowPathIcon className={`h-5 w-5 ${isSyncing ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                {/* Scholarships by School */}
                {isLoading ? (
                    <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1A4D2E] mx-auto"></div>
                        <p className="text-stone-500 mt-4">{isSyncing ? 'Syncing scholarships...' : 'Loading...'}</p>
                    </div>
                ) : scholarships.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-stone-200">
                        <BanknotesIcon className="h-12 w-12 text-stone-300 mx-auto" />
                        <h3 className="mt-4 text-lg font-medium text-stone-700">No Scholarships Yet</h3>
                        <p className="text-stone-500 mt-2 max-w-md mx-auto">
                            Add universities to your college list and their available scholarships will appear here.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {Object.entries(groupedBySchool).map(([schoolId, school]) => {
                            const filtered = filterScholarships(school.scholarships);
                            if (filtered.length === 0) return null;

                            const isExpanded = expandedSchools[schoolId] !== false;

                            return (
                                <div key={schoolId} className="bg-white rounded-xl border border-stone-200 overflow-hidden">
                                    <button
                                        onClick={() => toggleSchool(schoolId)}
                                        className="w-full flex items-center justify-between p-4 bg-stone-50 hover:bg-stone-100 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <AcademicCapIcon className="h-5 w-5 text-[#1A4D2E]" />
                                            <span className="font-medium text-stone-800">{school.name}</span>
                                            <span className="text-xs bg-stone-200 text-stone-600 px-2 py-0.5 rounded-full">
                                                {filtered.length} scholarship{filtered.length !== 1 ? 's' : ''}
                                            </span>
                                        </div>
                                        {isExpanded ? (
                                            <ChevronDownIcon className="h-5 w-5 text-stone-400" />
                                        ) : (
                                            <ChevronRightIcon className="h-5 w-5 text-stone-400" />
                                        )}
                                    </button>

                                    {isExpanded && (
                                        <div className="p-4 border-t border-stone-100 space-y-3">
                                            {filtered.map((scholarship) => {
                                                const status = scholarship.status || 'not_applied';
                                                const statusConfig = STATUS_CONFIG[status];
                                                const eligibility = ELIGIBILITY_CONFIG[scholarship.eligibility_indicator] || ELIGIBILITY_CONFIG.unknown;
                                                const typeConfig = TYPE_CONFIG[scholarship.type] || TYPE_CONFIG.Need;
                                                const TypeIcon = typeConfig.icon;

                                                return (
                                                    <div
                                                        key={scholarship.scholarship_id}
                                                        className="bg-white rounded-lg p-4 border border-stone-200 hover:border-stone-300 transition-all"
                                                    >
                                                        <div className="flex items-start justify-between gap-4">
                                                            <div className="flex-1 min-w-0">
                                                                <div className="flex items-center gap-2">
                                                                    <TypeIcon className={`h-4 w-4 ${typeConfig.color}`} />
                                                                    <h3 className="font-medium text-stone-800">
                                                                        {scholarship.scholarship_name}
                                                                    </h3>
                                                                </div>

                                                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                                                    <span className={`text-xs px-2 py-0.5 rounded-full ${eligibility.bg} ${eligibility.text} border ${eligibility.border}`}>
                                                                        {eligibility.label}
                                                                    </span>
                                                                    <span className="text-xs px-2 py-0.5 rounded-full bg-stone-100 text-stone-600">
                                                                        {typeConfig.label}
                                                                    </span>
                                                                    {scholarship.deadline && (
                                                                        <span className="text-xs text-stone-500 flex items-center gap-1">
                                                                            <CalendarIcon className="h-3 w-3" />
                                                                            {scholarship.deadline}
                                                                        </span>
                                                                    )}
                                                                </div>

                                                                {scholarship.amount && (
                                                                    <p className="text-sm text-emerald-700 font-medium mt-2">
                                                                        {scholarship.amount}
                                                                    </p>
                                                                )}

                                                                {scholarship.application_method && (
                                                                    <p className="text-xs text-stone-500 mt-2">
                                                                        <span className="font-medium">How to apply:</span> {scholarship.application_method}
                                                                    </p>
                                                                )}
                                                            </div>

                                                            <select
                                                                value={status}
                                                                onChange={(e) => handleStatusChange(scholarship.scholarship_id, e.target.value)}
                                                                className={`text-xs font-medium px-2 py-1 rounded-md border-0 ${statusConfig.bg} ${statusConfig.text} cursor-pointer focus:ring-2 focus:ring-offset-1 flex-shrink-0`}
                                                            >
                                                                <option value="not_applied">Not Applied</option>
                                                                <option value="applied">Applied</option>
                                                                <option value="received">Received</option>
                                                                <option value="not_eligible">Not Eligible</option>
                                                            </select>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default ScholarshipTracker;
