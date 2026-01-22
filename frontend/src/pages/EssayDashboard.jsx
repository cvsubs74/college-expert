import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { syncEssayTracker, getEssayTracker, updateEssayProgress } from '../services/api';
import {
    DocumentTextIcon,
    CheckCircleIcon,
    PencilSquareIcon,
    EyeIcon,
    ArrowPathIcon,
    AcademicCapIcon,
    BuildingLibraryIcon,
    InformationCircleIcon,
    ChevronDownIcon,
    ChevronRightIcon
} from '@heroicons/react/24/outline';

// Essay status configurations
const STATUS_CONFIG = {
    not_started: { label: 'Not Started', color: 'stone', bg: 'bg-stone-100', text: 'text-stone-600', icon: DocumentTextIcon },
    draft: { label: 'Draft', color: 'blue', bg: 'bg-blue-100', text: 'text-blue-700', icon: PencilSquareIcon },
    review: { label: 'In Review', color: 'amber', bg: 'bg-amber-100', text: 'text-amber-700', icon: EyeIcon },
    final: { label: 'Final', color: 'emerald', bg: 'bg-emerald-100', text: 'text-emerald-700', icon: CheckCircleIcon }
};

const EssayDashboard = ({ embedded = false }) => {
    const { currentUser: user } = useAuth();
    const [essays, setEssays] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isSyncing, setIsSyncing] = useState(false);
    const [filter, setFilter] = useState('all');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedGroups, setExpandedGroups] = useState({ uc_piq: true, common_app: true, supplements: true });

    useEffect(() => {
        if (user?.email) {
            syncAndLoadEssays();
        }
    }, [user]);

    const syncAndLoadEssays = async () => {
        if (!user?.email) return;
        setIsLoading(true);
        setIsSyncing(true);
        try {
            // Sync from college list (auto-populate)
            const syncResult = await syncEssayTracker(user.email);
            if (syncResult.success && syncResult.essays) {
                setEssays(syncResult.essays);
            } else {
                // Fallback to just getting existing essays
                const result = await getEssayTracker(user.email);
                if (result.success && result.essays) {
                    setEssays(result.essays);
                }
            }
        } catch (error) {
            console.error('Failed to sync/load essays:', error);
        } finally {
            setIsLoading(false);
            setIsSyncing(false);
        }
    };

    const handleStatusChange = async (essayId, newStatus) => {
        if (!user?.email) return;

        // Optimistic update
        setEssays(prev => prev.map(e =>
            e.essay_id === essayId ? { ...e, status: newStatus } : e
        ));

        const result = await updateEssayProgress(user.email, essayId, { status: newStatus });
        if (!result.success) {
            syncAndLoadEssays();
        }
    };

    const toggleGroup = (group) => {
        setExpandedGroups(prev => ({ ...prev, [group]: !prev[group] }));
    };

    // Group essays by university
    const groupedByUniversity = {};
    essays.forEach(essay => {
        const uniName = essay.university_name || essay.university_id || 'Other';
        if (!groupedByUniversity[uniName]) {
            groupedByUniversity[uniName] = [];
        }
        groupedByUniversity[uniName].push(essay);
    });

    // Sort universities: UC Application first, then alphabetically
    const sortedUniversities = Object.keys(groupedByUniversity).sort((a, b) => {
        if (a.startsWith('UC Application')) return -1;
        if (b.startsWith('UC Application')) return 1;
        return a.localeCompare(b);
    });

    // Check if UC PIQs exist
    const hasUcPiqs = sortedUniversities.some(u => u.startsWith('UC Application'));

    // Filter essays
    const filterEssays = (essayList) => {
        return essayList.filter(essay => {
            const matchesFilter = filter === 'all' || essay.status === filter;
            const matchesSearch = !searchQuery ||
                essay.prompt_text?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                essay.university_name?.toLowerCase().includes(searchQuery.toLowerCase());
            return matchesFilter && matchesSearch;
        });
    };

    // Calculate stats
    const stats = {
        total: essays.length,
        not_started: essays.filter(e => e.status === 'not_started' || !e.status).length,
        draft: essays.filter(e => e.status === 'draft').length,
        review: essays.filter(e => e.status === 'review').length,
        final: essays.filter(e => e.status === 'final').length
    };

    // UC PIQ selection rule
    const ucPiqEssays = essays.filter(e => e.university_id === 'uc_system');
    const ucPiqStats = {
        total: ucPiqEssays.length,
        completed: ucPiqEssays.filter(e => e.status === 'final' || e.status === 'review' || e.status === 'draft').length,
        required: 4
    };

    const progressPercent = stats.total > 0 ? Math.round((stats.final / stats.total) * 100) : 0;

    const renderEssayList = (essayList, showSelectionRule = null) => {
        const filtered = filterEssays(essayList);
        if (filtered.length === 0) {
            return (
                <div className="text-center py-6 text-stone-500 text-sm">
                    No essays match your filters
                </div>
            );
        }

        return (
            <div className="space-y-3">
                {filtered.map((essay) => {
                    const status = essay.status || 'not_started';
                    const config = STATUS_CONFIG[status] || STATUS_CONFIG.not_started;
                    const StatusIcon = config.icon;
                    const wordLimit = parseInt(essay.word_limit) || 0;
                    const wordProgress = wordLimit ? Math.min(100, Math.round((essay.word_count || 0) / wordLimit * 100)) : 0;

                    return (
                        <div
                            key={essay.essay_id}
                            className="bg-white rounded-lg p-4 border border-stone-200 hover:border-stone-300 transition-all"
                        >
                            <div className="flex items-start gap-3">
                                <div className={`p-2 rounded-lg ${config.bg} flex-shrink-0`}>
                                    <StatusIcon className={`h-4 w-4 ${config.text}`} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium text-stone-800 text-sm line-clamp-2">
                                                {essay.prompt_text || essay.prompt || 'Essay Prompt'}
                                            </h3>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className="text-xs text-stone-500">
                                                    {essay.university_name || essay.university_id || 'General'}
                                                </span>
                                                {essay.word_limit && (
                                                    <span className="text-xs text-stone-400">
                                                        • {essay.word_limit}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <select
                                            value={status}
                                            onChange={(e) => handleStatusChange(essay.essay_id, e.target.value)}
                                            className={`text-xs font-medium px-2 py-1 rounded-md border-0 ${config.bg} ${config.text} cursor-pointer focus:ring-2 focus:ring-offset-1 flex-shrink-0`}
                                        >
                                            <option value="not_started">Not Started</option>
                                            <option value="draft">Draft</option>
                                            <option value="review">In Review</option>
                                            <option value="final">Final</option>
                                        </select>
                                    </div>

                                    {wordLimit > 0 && essay.word_count > 0 && (
                                        <div className="mt-2">
                                            <div className="flex justify-between text-xs text-stone-500 mb-1">
                                                <span>{essay.word_count} / {wordLimit} words</span>
                                            </div>
                                            <div className="h-1 bg-stone-200 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full transition-all ${wordProgress > 100 ? 'bg-red-500' :
                                                        wordProgress >= 80 ? 'bg-emerald-500' :
                                                            wordProgress >= 50 ? 'bg-blue-500' : 'bg-stone-400'
                                                        }`}
                                                    style={{ width: `${Math.min(100, wordProgress)}%` }}
                                                />
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    };

    const renderGroupHeader = (title, icon, group, count, isUcPiq = false) => {
        const Icon = icon;
        const isExpanded = expandedGroups[group];

        return (
            <button
                onClick={() => toggleGroup(group)}
                className="w-full flex items-center justify-between p-3 bg-stone-50 rounded-lg hover:bg-stone-100 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <Icon className="h-5 w-5 text-[#1A4D2E]" />
                    <span className="font-medium text-stone-800">{title}</span>
                    <span className="text-xs bg-stone-200 text-stone-600 px-2 py-0.5 rounded-full">
                        {count}
                    </span>
                    {isUcPiq && ucPiqStats.total > 0 && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${ucPiqStats.completed >= ucPiqStats.required
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-amber-100 text-amber-700'
                            }`}>
                            {ucPiqStats.completed} of {ucPiqStats.required} selected
                        </span>
                    )}
                </div>
                {isExpanded ? (
                    <ChevronDownIcon className="h-5 w-5 text-stone-400" />
                ) : (
                    <ChevronRightIcon className="h-5 w-5 text-stone-400" />
                )}
            </button>
        );
    };

    return (
        <div className={embedded ? '' : 'min-h-screen bg-gradient-to-b from-[#FDFCF7] to-stone-50'}>
            <div className={embedded ? '' : 'max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8'}>
                {/* Header - hidden when embedded */}
                {!embedded && (
                    <div className="mb-8">
                        <h1 className="text-3xl font-serif font-medium text-[#1A4D2E]">Essay Progress</h1>
                        <p className="text-stone-600 mt-2">Essays auto-populated from your college list.</p>
                    </div>
                )}

                {/* Stats Cards */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
                    <div className="bg-white rounded-xl p-4 border border-stone-200 shadow-sm">
                        <div className="text-2xl font-bold text-stone-800">{stats.total}</div>
                        <div className="text-sm text-stone-500">Total Essays</div>
                    </div>
                    <div className="bg-stone-50 rounded-xl p-4 border border-stone-200">
                        <div className="text-2xl font-bold text-stone-600">{stats.not_started}</div>
                        <div className="text-sm text-stone-500">Not Started</div>
                    </div>
                    <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
                        <div className="text-2xl font-bold text-blue-700">{stats.draft}</div>
                        <div className="text-sm text-blue-600">Drafts</div>
                    </div>
                    <div className="bg-amber-50 rounded-xl p-4 border border-amber-200">
                        <div className="text-2xl font-bold text-amber-700">{stats.review}</div>
                        <div className="text-sm text-amber-600">In Review</div>
                    </div>
                    <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200">
                        <div className="text-2xl font-bold text-emerald-700">{stats.final}</div>
                        <div className="text-sm text-emerald-600">Finalized</div>
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="bg-white rounded-xl p-4 border border-stone-200 shadow-sm mb-6">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-stone-700">Overall Progress</span>
                        <span className="text-sm font-bold text-[#1A4D2E]">{progressPercent}% Complete</span>
                    </div>
                    <div className="h-2.5 bg-stone-200 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-[#1A4D2E] to-emerald-500 transition-all duration-500"
                            style={{ width: `${progressPercent}%` }}
                        />
                    </div>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-3 mb-6">
                    <div className="flex-1 min-w-[200px]">
                        <input
                            type="text"
                            placeholder="Search essays..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full px-4 py-2 border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20 text-sm"
                        />
                    </div>
                    <div className="flex gap-2">
                        {['all', 'not_started', 'draft', 'review', 'final'].map((f) => (
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
                        onClick={syncAndLoadEssays}
                        disabled={isSyncing}
                        className="p-2 text-stone-500 hover:text-[#1A4D2E] hover:bg-stone-100 rounded-lg disabled:opacity-50"
                        title="Sync from college list"
                    >
                        <ArrowPathIcon className={`h-5 w-5 ${isSyncing ? 'animate-spin' : ''}`} />
                    </button>
                </div>

                {/* Essays by Group */}
                {isLoading ? (
                    <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#1A4D2E] mx-auto"></div>
                        <p className="text-stone-500 mt-4">{isSyncing ? 'Syncing essays from your colleges...' : 'Loading essays...'}</p>
                    </div>
                ) : essays.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-stone-200">
                        <DocumentTextIcon className="h-12 w-12 text-stone-300 mx-auto" />
                        <h3 className="mt-4 text-lg font-medium text-stone-700">No Essays Yet</h3>
                        <p className="text-stone-500 mt-2 max-w-md mx-auto">
                            Add universities to your college list and their essay prompts will automatically appear here.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {sortedUniversities.map((universityName) => {
                            const universityEssays = groupedByUniversity[universityName] || [];
                            const isUcApplication = universityName.startsWith('UC Application');
                            const groupKey = universityName.replace(/\s+/g, '_').toLowerCase();
                            const isExpanded = expandedGroups[groupKey] !== false; // Default to expanded

                            return (
                                <div key={universityName} className="bg-white rounded-xl border border-stone-200 overflow-hidden">
                                    {renderGroupHeader(
                                        universityName,
                                        isUcApplication ? AcademicCapIcon : BuildingLibraryIcon,
                                        groupKey,
                                        universityEssays.length,
                                        isUcApplication
                                    )}
                                    {isExpanded && (
                                        <div className="p-4 border-t border-stone-100">
                                            {isUcApplication && (
                                                <div className="flex items-start gap-2 mb-4 p-3 bg-blue-50 rounded-lg">
                                                    <InformationCircleIcon className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                                                    <p className="text-sm text-blue-700">
                                                        Select <strong>4 of 8</strong> prompts to answer. Each response should be 350 words max.
                                                    </p>
                                                </div>
                                            )}
                                            {renderEssayList(universityEssays)}
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

export default EssayDashboard;
