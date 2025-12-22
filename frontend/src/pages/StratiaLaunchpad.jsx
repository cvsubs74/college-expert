import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';
import { getPrecomputedFits, getFitsByCategory, updateCollegeList, computeSingleFit } from '../services/api';
import {
    BackgroundBlobs,
    HeroSection,
    SmartDiscoveryAlert,
    UniversityCard
} from '../components/stratia';

// Existing components for modals and widgets
import FitChatWidget from '../components/FitChatWidget';
import CreditsUpgradeModal from '../components/CreditsUpgradeModal';
import FitAnalysisPage from '../components/FitAnalysisPage';
import { Link, useNavigate } from 'react-router-dom';

// Icons
import {
    PlusIcon,
    MagnifyingGlassIcon,
    FunnelIcon,
    ArrowPathIcon
} from '@heroicons/react/24/outline';

/**
 * StratiaLaunchpad - Main dashboard with Digital Ivy M3 design
 * 
 * "Ivy League Library meets Modern Tech" aesthetic
 * - Warm cream backgrounds
 * - Serif headlines (Playfair Display)
 * - Organic blob shapes
 * - M3 state layers and elevation
 */
const StratiaLaunchpad = () => {
    const { currentUser } = useAuth();
    const { isFreeTier } = usePayment();
    const FREE_TIER_SCHOOL_LIMIT = 3;

    // State
    const [collegeList, setCollegeList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedCategory, setSelectedCategory] = useState('ALL');
    const [searchQuery, setSearchQuery] = useState('');

    // Modal states
    const [fitModalCollege, setFitModalCollege] = useState(null);
    const [chatCollege, setChatCollege] = useState(null);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [showDiscoveryPanel, setShowDiscoveryPanel] = useState(false);
    const [showCreditsModal, setShowCreditsModal] = useState(false);
    const [creditsRemaining, setCreditsRemaining] = useState(10);

    // Discovery panel state
    const [discoveryCategory, setDiscoveryCategory] = useState('SAFETY');
    const [discoveryResults, setDiscoveryResults] = useState([]);
    const [discoveryLoading, setDiscoveryLoading] = useState(false);
    const [addingSchoolId, setAddingSchoolId] = useState(null);

    // Fetch college list AND precomputed fits, then merge
    const fetchCollegeList = async () => {
        if (!currentUser?.email) return;

        setLoading(true);
        try {
            // Fetch both college list and precomputed fits in parallel
            const [listResponse, fitsResult] = await Promise.all([
                fetch(`${import.meta.env.VITE_PROFILE_MANAGER_ES_URL}/get-college-list?user_email=${encodeURIComponent(currentUser.email)}`),
                getPrecomputedFits(currentUser.email, {}, 200)
            ]);

            const listData = await listResponse.json();
            console.log('[StratiaLaunchpad] College list result:', listData);
            console.log('[StratiaLaunchpad] Fits result:', fitsResult);

            if (listData.success) {
                let colleges = listData.college_list || [];
                console.log('[StratiaLaunchpad] Colleges loaded:', colleges.length, colleges.map(c => c.university_id));

                // Merge precomputed fits into college list
                // API returns 'results' array (or 'fits' for backwards compat)
                const fitsArray = fitsResult.results || fitsResult.fits || [];
                if (fitsResult.success && fitsArray.length > 0) {
                    console.log('[StratiaLaunchpad] Fits available:', fitsArray.length, fitsArray.map(f => f.university_id));
                    const fitsMap = {};
                    fitsArray.forEach(fit => {
                        fitsMap[fit.university_id] = {
                            fit_category: fit.fit_category,
                            match_percentage: fit.match_percentage || fit.match_score,
                            match_score: fit.match_percentage || fit.match_score,
                            explanation: fit.explanation,
                            factors: fit.factors || [],
                            recommendations: fit.recommendations || [],
                            gap_analysis: fit.gap_analysis || {},
                            essay_angles: fit.essay_angles || [],
                            application_timeline: fit.application_timeline || {},
                            scholarship_matches: fit.scholarship_matches || [],
                            test_strategy: fit.test_strategy || {},
                            major_strategy: fit.major_strategy || {},
                            infographic_url: fit.infographic_url
                        };
                    });

                    console.log('[StratiaLaunchpad] FitsMap keys:', Object.keys(fitsMap));

                    // Merge fits into colleges
                    colleges = colleges.map(college => {
                        const precomputed = fitsMap[college.university_id];
                        console.log('[StratiaLaunchpad] Merge check:', college.university_id, '-> precomputed:', !!precomputed);
                        if (precomputed) {
                            return {
                                ...college,
                                fit_analysis: precomputed,
                                infographic_url: precomputed.infographic_url
                            };
                        }
                        return college;
                    });
                    console.log('[StratiaLaunchpad] Merged:', colleges.filter(c => c.fit_analysis?.fit_category).length, 'colleges with fit data');
                }

                setCollegeList(colleges);
            } else {
                setError(listData.error || 'Failed to load colleges');
            }
        } catch (err) {
            console.error('[StratiaLaunchpad] Error fetching college list:', err);
            setError('Failed to load your college list');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCollegeList();
    }, [currentUser?.email]);

    // Categorize colleges by fit
    const categorizedColleges = useMemo(() => {
        const categories = {
            SUPER_REACH: [],
            REACH: [],
            TARGET: [],
            SAFETY: []
        };

        collegeList.forEach(college => {
            const fitCategory = college.fit_analysis?.fit_category
                || college.soft_fit_category
                || 'TARGET';
            if (categories[fitCategory]) {
                categories[fitCategory].push(college);
            } else {
                categories.TARGET.push(college);
            }
        });

        return categories;
    }, [collegeList]);

    // Stats for hero section
    const stats = useMemo(() => ({
        total: collegeList.length,
        superReach: categorizedColleges.SUPER_REACH.length + categorizedColleges.REACH.length,
        target: categorizedColleges.TARGET.length,
        safety: categorizedColleges.SAFETY.length
    }), [collegeList, categorizedColleges]);

    // Filter colleges based on category and search
    const filteredColleges = useMemo(() => {
        let colleges = [];

        if (selectedCategory === 'ALL') {
            colleges = collegeList;
        } else {
            colleges = categorizedColleges[selectedCategory] || [];
        }

        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            colleges = colleges.filter(c =>
                c.university_name?.toLowerCase().includes(query) ||
                c.location?.toLowerCase().includes(query)
            );
        }

        return colleges;
    }, [collegeList, categorizedColleges, selectedCategory, searchQuery]);

    // Handlers
    const handleViewAnalysis = (college) => {
        setFitModalCollege(college);
    };

    const handleOpenChat = (college) => {
        setChatCollege(college);
        setIsChatOpen(true);
    };

    const handleCloseChat = () => {
        setIsChatOpen(false);
        setChatCollege(null);
    };

    const handleCloseFitModal = () => {
        setFitModalCollege(null);
    };

    // Discovery panel functions
    const fetchDiscoverySchools = async (category = 'SAFETY') => {
        if (!currentUser?.email) return;

        setDiscoveryLoading(true);
        setDiscoveryCategory(category);
        try {
            // Get existing college IDs to exclude
            const existingIds = collegeList.map(c => c.university_id);
            const result = await getFitsByCategory(currentUser.email, category, null, existingIds, 10);

            if (result.success) {
                // API returns 'results' array
                let schools = result.results || result.fits || [];

                // Get existing college IDs AND names for matching
                const existingNames = collegeList.map(c =>
                    (c.university_name || '').toLowerCase().replace(/[^a-z0-9]/g, '')
                );

                // Client-side filter: exclude schools already in user's list (by ID or name)
                // Also deduplicate by university_id
                const seenIds = new Set();
                schools = schools.filter(s => {
                    // Skip if we've already seen this ID (dedupe)
                    if (seenIds.has(s.university_id)) return false;
                    seenIds.add(s.university_id);

                    // Skip if ID matches existing
                    if (existingIds.includes(s.university_id)) return false;

                    // Skip if name matches existing (handles ID mismatches)
                    const normalizedName = (s.university_name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                    if (existingNames.some(existingName =>
                        existingName.includes(normalizedName) || normalizedName.includes(existingName)
                    )) return false;

                    return true;
                });

                setDiscoveryResults(schools);
                console.log(`[Discovery] Found ${schools.length} ${category} schools (after filtering existing + dedupe)`);
            } else {
                setDiscoveryResults([]);
            }
        } catch (err) {
            console.error('[Discovery] Error fetching schools:', err);
            setDiscoveryResults([]);
        } finally {
            setDiscoveryLoading(false);
        }
    };

    const handleOpenDiscovery = (category = 'SAFETY') => {
        setShowDiscoveryPanel(true);
        fetchDiscoverySchools(category);
    };

    const handleAddDiscoverySchool = async (school) => {
        if (!currentUser?.email || addingSchoolId) return;

        // Free tier limit check
        if (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT) {
            setShowCreditsModal(true);
            return;
        }

        setAddingSchoolId(school.university_id);
        try {
            // Add to college list
            const addResult = await updateCollegeList(currentUser.email, 'add', {
                id: school.university_id,
                name: school.university_name
            });

            if (addResult.success) {
                // Compute fit analysis
                await computeSingleFit(currentUser.email, school.university_id, false);

                // Refresh college list
                await fetchCollegeList();

                // Remove from discovery results
                setDiscoveryResults(prev => prev.filter(s => s.university_id !== school.university_id));

                console.log(`[Discovery] Added ${school.university_name} to launchpad`);
            }
        } catch (err) {
            console.error('[Discovery] Error adding school:', err);
        } finally {
            setAddingSchoolId(null);
        }
    };

    // Filter tabs
    const filterTabs = [
        { key: 'ALL', label: 'All Schools', count: collegeList.length },
        { key: 'SUPER_REACH', label: 'Reach', count: stats.superReach },
        { key: 'TARGET', label: 'Target', count: stats.target },
        { key: 'SAFETY', label: 'Safety', count: stats.safety }
    ];

    // Get user's first name
    const userName = currentUser?.displayName?.split(' ')[0]
        || currentUser?.email?.split('@')[0]
        || 'Student';

    // Loading state
    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="text-center space-y-4 animate-fade-up">
                    <div className="w-16 h-16 border-4 border-[#D6E8D5] border-t-[#1A4D2E] rounded-full animate-spin mx-auto" />
                    <p className="text-[#4A4A4A] font-sans">Loading your schools...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <div className="stratia-card p-8 text-center max-w-md animate-fade-up">
                    <div className="w-16 h-16 bg-[#FCEEE8] rounded-full flex items-center justify-center mx-auto mb-4">
                        <span className="text-2xl">⚠️</span>
                    </div>
                    <h3 className="font-serif text-xl font-semibold text-[#2C2C2C] mb-2">
                        Unable to Load
                    </h3>
                    <p className="text-[#4A4A4A] mb-4">{error}</p>
                    <button
                        onClick={fetchCollegeList}
                        className="stratia-btn-filled"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    // Fit Analysis Full Page View
    if (fitModalCollege) {
        return (
            <div>
                <FitAnalysisPage
                    college={fitModalCollege}
                    onBack={handleCloseFitModal}
                />

                {/* Chat FAB */}
                {!isChatOpen && (
                    <button
                        onClick={() => handleOpenChat(fitModalCollege)}
                        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-5 py-3 
                            bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] text-white 
                            rounded-full shadow-lg hover:shadow-xl hover:scale-105 
                            transition-all duration-300 font-medium"
                    >
                        <span className="text-lg">💬</span>
                        <span className="font-sans font-semibold">Ask AI</span>
                    </button>
                )}

                <FitChatWidget
                    universityId={chatCollege?.university_id}
                    universityName={chatCollege?.university_name}
                    fitCategory={chatCollege?.fit_analysis?.fit_category}
                    isOpen={isChatOpen}
                    onClose={handleCloseChat}
                />
            </div>
        );
    }

    // Main Dashboard View
    return (
        <div>
            {/* Hero Section */}
            <HeroSection userName={userName} stats={stats} />

            {/* Smart Discovery Alert */}
            <SmartDiscoveryAlert
                hasNoSafety={stats.safety === 0 && stats.total > 0}
                isTooAmbitious={stats.superReach > stats.target + stats.safety && stats.total > 2}
                onFindSchools={() => handleOpenDiscovery('SAFETY')}
            />

            {/* Main Content */}
            <section className="py-6">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    {/* Header Row: Title + Actions */}
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                        <h2 className="font-serif text-2xl font-semibold text-[#2C2C2C]">
                            Your College List
                        </h2>

                        <div className="flex items-center gap-3">
                            {/* Search */}
                            <div className="relative">
                                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[#6B6B6B]" />
                                <input
                                    type="text"
                                    placeholder="Search schools..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10 pr-4 py-2 w-48 sm:w-64 rounded-full border border-[#E0DED8] 
                                        bg-white font-sans text-sm focus:outline-none focus:border-[#1A4D2E]
                                        focus:ring-2 focus:ring-[#D6E8D5] transition-all"
                                />
                            </div>

                            {/* Add School Button */}
                            <button
                                onClick={() => setShowDiscoveryPanel(true)}
                                className="stratia-btn-filled flex items-center gap-2"
                            >
                                <PlusIcon className="w-5 h-5" />
                                <span className="hidden sm:inline">Add School</span>
                            </button>
                        </div>
                    </div>

                    {/* Filter Tabs */}
                    <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
                        {filterTabs.map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setSelectedCategory(tab.key)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-full font-sans text-sm font-medium transition-all whitespace-nowrap
                                    ${selectedCategory === tab.key
                                        ? 'bg-[#1A4D2E] text-white'
                                        : 'bg-white text-[#4A4A4A] border border-[#E0DED8] hover:border-[#1A4D2E] hover:text-[#1A4D2E]'
                                    }`}
                            >
                                {tab.label}
                                <span className={`text-xs px-1.5 py-0.5 rounded-full 
                                    ${selectedCategory === tab.key
                                        ? 'bg-white/20'
                                        : 'bg-[#F8F6F0]'
                                    }`}>
                                    {tab.count}
                                </span>
                            </button>
                        ))}
                    </div>

                    {/* College List */}
                    {filteredColleges.length === 0 ? (
                        <div className="stratia-card p-12 text-center">
                            <div className="max-w-md mx-auto space-y-4">
                                <div className="w-20 h-20 bg-[#D6E8D5] rounded-full flex items-center justify-center mx-auto">
                                    <span className="text-3xl">🎓</span>
                                </div>
                                <h3 className="font-serif text-xl font-semibold text-[#2C2C2C]">
                                    {searchQuery ? 'No matches found' : 'Start Building Your List'}
                                </h3>
                                <p className="text-[#4A4A4A]">
                                    {searchQuery
                                        ? `No schools match "${searchQuery}"`
                                        : 'Discover schools that match your profile and add them to your list.'
                                    }
                                </p>
                                {!searchQuery && (
                                    <button
                                        onClick={() => setShowDiscoveryPanel(true)}
                                        className="stratia-btn-filled mt-2"
                                    >
                                        Discover Schools
                                    </button>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {filteredColleges.map((college, index) => (
                                <div
                                    key={college.university_id}
                                    style={{ animationDelay: `${index * 50}ms` }}
                                >
                                    <UniversityCard
                                        university={{
                                            ...college,
                                            fit_category: college.fit_analysis?.fit_category || college.soft_fit_category || 'TARGET',
                                            match_score: college.fit_analysis?.match_score || 0
                                        }}
                                        onViewAnalysis={handleViewAnalysis}
                                        onOpenChat={handleOpenChat}
                                        onViewNotes={() => {/* TODO: Notes modal */ }}
                                    />
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </section>

            {/* Discovery Panel - Inline School Recommendations */}
            {showDiscoveryPanel && (
                <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
                    <div className="stratia-card p-6 max-w-3xl w-full max-h-[80vh] overflow-hidden animate-fade-up">
                        {/* Header */}
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h3 className="font-serif text-xl font-semibold text-[#2C2C2C]">
                                    {discoveryCategory === 'SAFETY' ? '🛡️ Safety School Recommendations' :
                                        discoveryCategory === 'TARGET' ? '🎯 Target School Recommendations' :
                                            '🚀 Reach School Recommendations'}
                                </h3>
                                <p className="text-sm text-[#4A4A4A]">
                                    Based on your profile, we recommend these schools
                                </p>
                            </div>
                            <button
                                onClick={() => setShowDiscoveryPanel(false)}
                                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                <span className="text-xl">×</span>
                            </button>
                        </div>

                        {/* Category Tabs */}
                        <div className="flex gap-2 mb-4">
                            {['SAFETY', 'TARGET', 'REACH'].map(cat => (
                                <button
                                    key={cat}
                                    onClick={() => fetchDiscoverySchools(cat)}
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${discoveryCategory === cat
                                        ? 'bg-[#1A4D2E] text-white'
                                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                        }`}
                                >
                                    {cat === 'SAFETY' ? '🛡️ Safety' : cat === 'TARGET' ? '🎯 Target' : '🚀 Reach'}
                                </button>
                            ))}
                        </div>

                        {/* Results Grid */}
                        <div className="overflow-y-auto max-h-[50vh] pr-2">
                            {discoveryLoading ? (
                                <div className="flex items-center justify-center py-12">
                                    <ArrowPathIcon className="h-8 w-8 animate-spin text-[#1A4D2E]" />
                                    <span className="ml-3 text-gray-600">Finding recommendations...</span>
                                </div>
                            ) : discoveryResults.length === 0 ? (
                                <div className="text-center py-12 text-gray-500">
                                    <p>No additional {discoveryCategory.toLowerCase()} schools found.</p>
                                    <p className="text-sm mt-2">Try a different category or explore all universities.</p>
                                </div>
                            ) : (
                                <div className="grid gap-3">
                                    {discoveryResults.map(school => (
                                        <div
                                            key={school.university_id}
                                            className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl hover:shadow-md transition-shadow"
                                        >
                                            <div className="flex-1">
                                                <h4 className="font-semibold text-[#2C2C2C]">
                                                    {school.university_name}
                                                </h4>
                                                <div className="flex items-center gap-3 text-sm text-gray-500 mt-1">
                                                    {school.location && (
                                                        <span>📍 {typeof school.location === 'object'
                                                            ? `${school.location.city || ''}${school.location.city && school.location.state ? ', ' : ''}${school.location.state || ''}`
                                                            : school.location}
                                                        </span>
                                                    )}
                                                    {school.us_news_rank && <span>#{school.us_news_rank} US News</span>}
                                                    {school.match_percentage && (
                                                        <span className="text-[#1A4D2E] font-medium">
                                                            {school.match_percentage}% Match
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => handleAddDiscoverySchool(school)}
                                                disabled={addingSchoolId === school.university_id}
                                                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${addingSchoolId === school.university_id
                                                    ? 'bg-gray-200 text-gray-500 cursor-wait'
                                                    : 'bg-[#D6E8D5] text-[#1A4D2E] hover:bg-[#1A4D2E] hover:text-white'
                                                    }`}
                                            >
                                                {addingSchoolId === school.university_id ? (
                                                    <>
                                                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                                        Adding...
                                                    </>
                                                ) : (
                                                    <>
                                                        <PlusIcon className="h-4 w-4" />
                                                        Add
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="flex justify-between items-center mt-4 pt-4 border-t border-gray-200">
                            <Link
                                to="/universities"
                                className="text-sm text-[#1A4D2E] hover:underline"
                            >
                                Explore all universities →
                            </Link>
                            <button
                                onClick={() => setShowDiscoveryPanel(false)}
                                className="stratia-btn-outlined"
                            >
                                Done
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Credits Modal */}
            <CreditsUpgradeModal
                isOpen={showCreditsModal}
                onClose={() => setShowCreditsModal(false)}
                creditsRemaining={creditsRemaining}
            />

            {/* Chat Widget */}
            <FitChatWidget
                universityId={chatCollege?.university_id}
                universityName={chatCollege?.university_name}
                fitCategory={chatCollege?.fit_analysis?.fit_category}
                isOpen={isChatOpen}
                onClose={handleCloseChat}
            />
        </div>
    );
};

export default StratiaLaunchpad;
