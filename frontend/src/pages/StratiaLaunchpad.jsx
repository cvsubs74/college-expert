import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';
import { getPrecomputedFits, getUniversitiesByCategory, updateCollegeList, computeSingleFit, addCollegeAnalysis, checkCredits, checkFitRecomputationNeeded, setMajorChoice } from '../services/api';
import { useToast } from '../components/Toast';
import KbRefreshBanner from '../components/KbRefreshBanner';
import KbRefreshReviewModal from '../components/KbRefreshReviewModal';
import { kbUpdateFor } from '../utils/kbVintage';
import {
    BackgroundBlobs,
    HeroSection,
    SmartDiscoveryAlert,
    UniversityCard
} from '../components/stratia';
import BalanceRing from '../components/stratia/BalanceRing';
import { collegeFitCategory, isEstimatedFit } from '../utils/listBalance';
import { askLinks } from '../utils/mcpClients';

// Existing components for modals and widgets
import FitChatWidget from '../components/FitChatWidget';
import CreditsUpgradeModal from '../components/CreditsUpgradeModal';
import FitAnalysisPage from '../components/FitAnalysisPage';
import MajorChancesView from '../components/majors/MajorChancesView';
import { Link, useNavigate } from 'react-router-dom';

// Icons
import {
    PlusIcon,
    MagnifyingGlassIcon,
    FunnelIcon,
    ArrowPathIcon,
    RocketLaunchIcon
} from '@heroicons/react/24/outline';

// Hand-off prompt for "Fix my balance" — explicitly tells the agent to fill the
// gap with safeties/targets WITHOUT recomputing fits (so it can't silently burn
// the student's credits), then capture the change as a strategy note.
const FIX_BALANCE_PROMPT = "Look at my Stratia college list and its reach/target/safety balance. If it's unbalanced, search for and add 1–2 schools that fill the gap — especially a safety I'd genuinely be happy to attend — using my profile. Do NOT recompute any fits or spend credits. Then save a short strategy note explaining what you changed and why.";

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
    const { isFreeTier, fetchCredits, hasCredits } = usePayment();
    const toast = useToast();
    const navigate = useNavigate();
    const FREE_TIER_SCHOOL_LIMIT = 3;

    // State
    const [collegeList, setCollegeList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedCategory, setSelectedCategory] = useState('ALL');
    const [searchQuery, setSearchQuery] = useState('');
    // KB-staleness entries (design §2) — refresh banner + vintage chips
    const [kbUpdates, setKbUpdates] = useState([]);
    const [kbReviewOpen, setKbReviewOpen] = useState(false);

    // Modal states
    const [fitModalCollege, setFitModalCollege] = useState(null);
    const [majorChancesCollege, setMajorChancesCollege] = useState(null);
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

    // Analysis progress modal state
    const [analysisModal, setAnalysisModal] = useState({
        isOpen: false,
        universityName: '',
        step: '', // 'adding', 'fit', 'saving', 'complete', 'error'
        progress: 0
    });

    // Fetch college list AND precomputed fits, then merge
    const fetchCollegeList = async () => {
        if (!currentUser?.email) return;

        setLoading(true);
        try {
            // Fetch college list, precomputed fits, and KB-staleness in parallel
            const [listResponse, fitsResult, recomputeStatus] = await Promise.all([
                fetch(`${import.meta.env.VITE_PROFILE_MANAGER_V2_URL}/get-college-list?user_email=${encodeURIComponent(currentUser.email)}`),
                getPrecomputedFits(currentUser.email, {}, 200),
                checkFitRecomputationNeeded(currentUser.email)
            ]);
            setKbUpdates(recomputeStatus.kb_updates || []);

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
                            // Which major this fit was actually computed for (#283) —
                            // drives the explicit "Recompute with {new}?" offer.
                            intended_major_used: fit.intended_major_used,
                            intended_major_source: fit.intended_major_source,
                            infographic_url: fit.infographic_url,
                            logo_url: fit.logo_url,
                            // KB provenance (design §1) — drives vintage chips
                            kb_data_year: fit.kb_data_year,
                            university_id: fit.university_id
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
                                infographic_url: precomputed.infographic_url,
                                logo_url: college.logo_url || precomputed.logo_url,
                                location: college.location || precomputed.location
                            };
                        }
                        console.log('[StratiaLaunchpad] Logo for', college.university_id, ':', college.logo_url || (precomputed && precomputed.logo_url));
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

    // Scroll to last viewed school when returning from detail pages
    useEffect(() => {
        if (collegeList.length > 0 && !loading) {
            const lastSchoolId = sessionStorage.getItem('lastViewedSchool');
            if (lastSchoolId) {
                setTimeout(() => {
                    const element = document.getElementById(`school-${lastSchoolId}`);
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    sessionStorage.removeItem('lastViewedSchool');
                }, 300);
            }
        }
    }, [collegeList, loading]);

    // Categorize colleges by fit
    const categorizedColleges = useMemo(() => {
        const categories = {
            SUPER_REACH: [],
            REACH: [],
            TARGET: [],
            SAFETY: []
        };

        collegeList.forEach(college => {
            const fitCategory = collegeFitCategory(college) || 'TARGET';
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

    // How many colleges fall back to admit-rate categories rather than a
    // personalized fit (so the balance ring can be honest about it).
    const estimatedFits = useMemo(
        () => collegeList.filter(isEstimatedFit).length,
        [collegeList]
    );
    // "Fix my balance" hand-off to the connected agent (computed once).
    const fixBalanceLinks = useMemo(() => askLinks(FIX_BALANCE_PROMPT), []);

    // Decision Ledger moved to its own page (/decision-ledger, #312) — the
    // calibration fetch/handlers that lived here went with it.

    // Filter colleges based on category and search
    const filteredColleges = useMemo(() => {
        let colleges = [];

        if (selectedCategory === 'ALL') {
            colleges = collegeList;
        } else if (selectedCategory === 'REACH') {
            // Combine SUPER_REACH and REACH schools
            colleges = [...(categorizedColleges.SUPER_REACH || []), ...(categorizedColleges.REACH || [])];
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

    // Recompute one fit from the KB-refresh review modal (design §3b/c).
    // The replaced analysis is archived server-side before overwrite.
    // force=true: this is an explicit recompute — the server charges 1 credit
    // and answers 402 when the balance is out (#285).
    const handleKbUpdateFit = async (universityId) => {
        const result = await computeSingleFit(currentUser.email, universityId, true);
        if (result?.insufficientCredits) {
            setShowCreditsModal(true);
            throw new Error('Not enough credits to update this fit');
        }
        if (!result?.success) {
            throw new Error(result?.error || 'Fit update failed');
        }
        await fetchCredits(); // refresh balance after the server-side charge
        const fresh = result.fit_analysis || {};
        setCollegeList(prev => prev.map(college =>
            college.university_id === universityId
                ? { ...college, fit_analysis: { ...college.fit_analysis, ...fresh, match_score: fresh.match_percentage ?? college.fit_analysis?.match_score } }
                : college
        ));
        setKbUpdates(prev => prev.filter(u => u.university_id !== universityId));
    };

    // "Update Fit" on a card: regenerate BOTH the fit AND the major-chances
    // against the current KB cycle via the bundle (#310), then open the
    // refreshed analysis. Prior fit + chances are archived server-side.
    // force=true: explicit regenerate — server charges 1 credit for the bundle,
    // 402 when out. The free agent route is offered on the card itself.
    const handleUpdateFit = async (university) => {
        const universityId = university.university_id;
        const result = await addCollegeAnalysis(currentUser.email, universityId, true);
        if (result?.insufficientCredits) {
            setShowCreditsModal(true);
            throw new Error('Not enough credits to update this fit');
        }
        if (!result?.success) {
            throw new Error(result?.error || 'Fit update failed');
        }
        await fetchCredits(); // refresh balance after the server-side charge
        const fresh = result.fit_analysis || {};
        const current = collegeList.find(c => c.university_id === universityId) || university;
        const refreshed = {
            ...current,
            fit_analysis: { ...current.fit_analysis, ...fresh, match_score: fresh.match_percentage ?? current.fit_analysis?.match_score }
        };
        setCollegeList(prev => prev.map(college =>
            college.university_id === universityId ? refreshed : college
        ));
        setKbUpdates(prev => prev.filter(u => u.university_id !== universityId));
        // Surface the freshly recomputed analysis.
        setFitModalCollege(refreshed);
    };

    // Handlers
    const handleViewAnalysis = (college) => {
        // Store scroll position before navigating
        const element = document.getElementById(`school-${college.university_id}`);
        if (element) {
            sessionStorage.setItem('lastViewedSchool', college.university_id);
        }
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
        // Scroll back to the school after a brief delay to let the list render
        setTimeout(() => {
            const lastSchoolId = sessionStorage.getItem('lastViewedSchool');
            if (lastSchoolId) {
                const element = document.getElementById(`school-${lastSchoolId}`);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                sessionStorage.removeItem('lastViewedSchool');
            }
        }, 100);
    };

    const handleMajorChances = (college) => {
        sessionStorage.setItem('lastViewedSchool', college.university_id);
        setMajorChancesCollege(college);
    };

    const handleCloseMajorChances = () => {
        setMajorChancesCollege(null);
        setTimeout(() => {
            const lastSchoolId = sessionStorage.getItem('lastViewedSchool');
            if (lastSchoolId) {
                const element = document.getElementById(`school-${lastSchoolId}`);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                sessionStorage.removeItem('lastViewedSchool');
            }
        }, 100);
    };

    const handleEssayHelp = (college) => {
        // Store scroll position before navigating 
        sessionStorage.setItem('lastViewedSchool', college.university_id);
        navigate(`/essay-help/${college.university_id}`);
    };

    // Handle removing a college from the list
    const handleRemoveCollege = async (college) => {
        if (!currentUser?.email) return;

        try {
            const result = await updateCollegeList(currentUser.email, 'remove', {
                id: college.university_id,
                name: college.university_name
            });

            if (result.success) {
                // Remove from local state immediately
                setCollegeList(prev => prev.filter(c => c.university_id !== college.university_id));
                console.log(`[StratiaLaunchpad] Removed ${college.university_name} from list`);
            }
        } catch (err) {
            console.error('[StratiaLaunchpad] Error removing college:', err);
        }
    };

    // Handle major change — persist the decision via set-major-choice (free).
    // Optimistic UI: reflect the pick immediately, revert + toast on failure.
    // NEVER recomputes the fit here — that's an explicit, separately-priced
    // action offered by the mismatch chip on the card (handleRecomputeWithMajor).
    const handleMajorChange = async (universityId, newMajor) => {
        if (!currentUser?.email) return;

        console.log(`[StratiaLaunchpad] Saving major for ${universityId}: ${newMajor}`);

        const college = collegeList.find(c => c.university_id === universityId);
        if (!college) return;
        const prevSelectedMajor = college.selected_major;
        const prevMajorChoice = college.major_choice;
        const prevNote = college.major_choice_note;

        // Optimistic update
        setCollegeList(prev => prev.map(c =>
            c.university_id === universityId
                ? {
                    ...c,
                    selected_major: newMajor,
                    major_choice: { ...(c.major_choice || {}), primary: newMajor, matched: true },
                    major_choice_note: null
                }
                : c
        ));

        try {
            const result = await setMajorChoice(currentUser.email, universityId, newMajor);
            if (!result?.success) {
                throw new Error(result?.error || 'Failed to save major choice');
            }
            // Adopt the server's canonical decision (matched flag, KB spelling,
            // kb_year, updated_at) + any unmatched-name note.
            setCollegeList(prev => prev.map(c =>
                c.university_id === universityId
                    ? {
                        ...c,
                        selected_major: result.major_choice?.primary || newMajor,
                        major_choice: result.major_choice || { primary: newMajor },
                        major_choice_note: result.note || null
                    }
                    : c
            ));
            console.log(`[StratiaLaunchpad] Major saved for ${universityId}:`, result.major_choice);
        } catch (err) {
            console.error('[StratiaLaunchpad] Error saving major choice:', err);
            // Revert the optimistic update
            setCollegeList(prev => prev.map(c =>
                c.university_id === universityId
                    ? { ...c, selected_major: prevSelectedMajor, major_choice: prevMajorChoice, major_choice_note: prevNote }
                    : c
            ));
            toast.error("Couldn't save your major", err.message || 'Please try again.');
        }
    };

    // Explicit recompute with the newly chosen major (from the mismatch chip on
    // the card). Reuses the existing credit-check + progress-modal flow and
    // passes intended_major so the fit is computed for the right major.
    const handleRecomputeWithMajor = async (university, newMajor) => {
        if (!currentUser?.email) return;

        // Credit gate — same pattern as the other paid actions on this page.
        if (!hasCredits) {
            setShowCreditsModal(true);
            return;
        }

        setAnalysisModal({
            isOpen: true,
            universityName: university.university_name || university.university_id,
            step: 'fit',
            progress: 30
        });

        try {
            // The server charges 1 credit for the compute and answers 402
            // when the balance is out (#285) — no client-side deduct.
            const result = await computeSingleFit(currentUser.email, university.university_id, true, newMajor);
            if (result?.insufficientCredits) {
                setAnalysisModal(prev => ({ ...prev, isOpen: false }));
                setShowCreditsModal(true);
                return;
            }
            if (!result?.success) {
                throw new Error(result?.error || 'Fit recompute failed');
            }

            setAnalysisModal(prev => ({ ...prev, step: 'saving', progress: 70 }));
            await fetchCredits(); // refresh global credits after the paid compute

            // Small delay for the fit doc to be readable, then refresh
            await new Promise(resolve => setTimeout(resolve, 600));
            await fetchCollegeList();

            setAnalysisModal(prev => ({ ...prev, step: 'complete', progress: 100 }));
            setTimeout(() => {
                setAnalysisModal(prev => ({ ...prev, isOpen: false }));
            }, 1500);

            console.log(`[StratiaLaunchpad] Fit recomputed for ${university.university_id} with major ${newMajor}`);
        } catch (err) {
            console.error('[StratiaLaunchpad] Error recomputing fit with major:', err);
            setAnalysisModal(prev => ({ ...prev, step: 'error', progress: 0 }));
            setTimeout(() => {
                setAnalysisModal(prev => ({ ...prev, isOpen: false }));
            }, 2000);
        }
    };

    // Discovery panel functions
    const fetchDiscoverySchools = async (category = 'SAFETY') => {
        if (!currentUser?.email) return;

        setDiscoveryLoading(true);
        setDiscoveryCategory(category);
        try {
            // Get existing college IDs to exclude
            const existingIds = collegeList.map(c => c.university_id);

            // Fetch from universities knowledge base (uses soft_fit_category based on acceptance rate)
            // This is more reliable than precomputed fits which may have personalized category overrides
            const result = await getUniversitiesByCategory(category, existingIds, 100);

            if (result.success) {
                // API returns 'universities' array from KB
                let schools = result.universities || [];

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

        // Show analysis progress modal
        setAnalysisModal({
            isOpen: true,
            universityName: school.university_name,
            step: 'adding',
            progress: 10
        });

        try {
            // Step 1: Add to college list (free — the fit compute is the paid step)
            setAnalysisModal(prev => ({ ...prev, step: 'adding', progress: 20 }));
            const addResult = await updateCollegeList(currentUser.email, 'add', {
                id: school.university_id,
                name: school.university_name
            });

            if (addResult.success) {
                // Step 2: Bundled analysis (#310) — ONE credit generates BOTH
                // the fit AND the major-chances ranking. The server charges the
                // single credit and answers 402 when the balance is out.
                setAnalysisModal(prev => ({ ...prev, step: 'fit', progress: 40 }));
                const fitResult = await addCollegeAnalysis(currentUser.email, school.university_id, false);
                if (fitResult?.insufficientCredits) {
                    setShowCreditsModal(true);
                    setAnalysisModal(prev => ({ ...prev, isOpen: false }));
                    return;
                }
                await fetchCredits(); // Refresh global credits after the server-side charge

                // Step 3: Saving
                setAnalysisModal(prev => ({ ...prev, step: 'saving', progress: 70 }));

                // Small delay to allow Elasticsearch to index the new fit document
                await new Promise(resolve => setTimeout(resolve, 600));

                // Refresh college list with new fit data
                await fetchCollegeList();

                setAnalysisModal(prev => ({ ...prev, progress: 90 }));

                // Remove from discovery results
                setDiscoveryResults(prev => prev.filter(s => s.university_id !== school.university_id));

                // Step 4: Complete
                setAnalysisModal(prev => ({ ...prev, step: 'complete', progress: 100 }));

                console.log(`[Discovery] Added ${school.university_name} to launchpad`);

                // Auto-close after 1.5 seconds
                setTimeout(() => {
                    setAnalysisModal(prev => ({ ...prev, isOpen: false }));
                }, 1500);
            }
        } catch (err) {
            console.error('[Discovery] Error adding school:', err);
            setAnalysisModal(prev => ({ ...prev, step: 'error', progress: 0 }));
            setTimeout(() => {
                setAnalysisModal(prev => ({ ...prev, isOpen: false }));
            }, 2000);
        } finally {
            setAddingSchoolId(null);
        }
    };

    // Filter tabs
    const filterTabs = [
        { key: 'ALL', label: 'All Schools', count: collegeList.length },
        { key: 'REACH', label: 'Reach', count: stats.superReach },
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

    // Major Chances Full Page View (#302) — opened in place like Fit Analysis.
    if (majorChancesCollege) {
        return (
            <MajorChancesView
                userEmail={currentUser?.email}
                universityId={majorChancesCollege.university_id}
                universityName={majorChancesCollege.university_name}
                onBack={handleCloseMajorChances}
            />
        );
    }

    // Fit Analysis Full Page View
    if (fitModalCollege) {
        return (
            <div>
                <FitAnalysisPage
                    college={fitModalCollege}
                    onBack={handleCloseFitModal}
                    kbUpdate={kbUpdateFor(kbUpdates, fitModalCollege.university_id)}
                    onUpdateFit={handleUpdateFit}
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
                    intendedMajor={chatCollege?.selected_major || chatCollege?.fit_analysis?.major_strategy?.intended_major}
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

            {/* Reach/Target/Safety balance at a glance (needs a few schools to be meaningful) */}
            {stats.total >= 3 && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                    <BalanceRing
                        reach={stats.superReach}
                        target={stats.target}
                        safety={stats.safety}
                        estimated={estimatedFits}
                        fixLinks={fixBalanceLinks}
                    />
                </div>
            )}

            {/* Decision Ledger moved to its own page: /decision-ledger (#312) */}
            {/* Yearly KB refresh moment (design §3a) */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
                <KbRefreshBanner kbUpdates={kbUpdates} onReview={() => setKbReviewOpen(true)} />
            </div>
            <KbRefreshReviewModal
                isOpen={kbReviewOpen}
                onClose={() => setKbReviewOpen(false)}
                kbUpdates={kbUpdates}
                onUpdateFit={handleKbUpdateFit}
                onAllUpdated={() => setKbReviewOpen(false)}
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

                            {/* Add School / Upgrade Button */}
                            {/* Show Upgrade if: (1) no credits remaining, OR (2) free tier and at school limit */}
                            <button
                                onClick={() => !hasCredits || (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT)
                                    ? navigate('/pricing')
                                    : handleOpenDiscovery('SAFETY')}
                                className={`flex items-center gap-2 ${!hasCredits || (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT)
                                    ? 'bg-[#C05838] hover:bg-[#A04828] text-white px-4 py-2 rounded-full font-medium transition-colors'
                                    : 'stratia-btn-filled'
                                    }`}
                            >
                                {!hasCredits || (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT) ? (
                                    <>
                                        <RocketLaunchIcon className="w-5 h-5" />
                                        <span className="hidden sm:inline">{isFreeTier ? 'Upgrade' : 'Get Credits'}</span>
                                    </>
                                ) : (
                                    <>
                                        <PlusIcon className="w-5 h-5" />
                                        <span className="hidden sm:inline">Add School</span>
                                    </>
                                )}
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
                                        onClick={() => handleOpenDiscovery('SAFETY')}
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
                                    id={`school-${college.university_id}`}
                                    style={{ animationDelay: `${index * 50}ms` }}
                                >
                                    <UniversityCard
                                        university={{
                                            ...college,
                                            // Map location from object if needed (handle null)
                                            location: college.location
                                                ? (typeof college.location === 'object'
                                                    ? `${college.location.city || ''}${college.location.city && college.location.state ? ', ' : ''}${college.location.state || ''}`
                                                    : college.location)
                                                : null,
                                            // Pass stats from college data
                                            acceptance_rate: college.acceptance_rate || college.fit_analysis?.acceptance_rate,
                                            us_news_rank: college.us_news_rank || college.fit_analysis?.us_news_rank,
                                            fit_category: college.fit_analysis?.fit_category || college.soft_fit_category || 'TARGET',
                                            match_score: college.fit_analysis?.match_score || 0,
                                            // Major data — major_choice is the persisted
                                            // per-school decision; selected_major the legacy mirror
                                            selected_major: college.selected_major,
                                            major_choice: college.major_choice || null,
                                            major_choice_note: college.major_choice_note || null,
                                            available_majors: college.available_majors || [],
                                            // Application status
                                            application_status: college.application_status || null,
                                            // KB vintage (design §3e)
                                            kb_data_year: college.fit_analysis?.kb_data_year,
                                            kb_update: kbUpdateFor(kbUpdates, college.university_id)
                                        }}
                                        onViewAnalysis={handleViewAnalysis}
                                        onOpenChat={handleOpenChat}
                                        onEssayHelp={handleEssayHelp}
                                        onUpdateFit={handleUpdateFit}
                                        onMajorChange={handleMajorChange}
                                        onMajorChances={handleMajorChances}
                                        onRecomputeWithMajor={handleRecomputeWithMajor}
                                        canRemove={!isFreeTier}
                                        onRemove={handleRemoveCollege}
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
                                                onClick={() => !hasCredits || (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT)
                                                    ? navigate('/pricing')
                                                    : handleAddDiscoverySchool(school)}
                                                disabled={addingSchoolId === school.university_id}
                                                className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${addingSchoolId === school.university_id
                                                    ? 'bg-gray-200 text-gray-500 cursor-wait'
                                                    : !hasCredits || (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT)
                                                        ? 'bg-[#FCEEE8] text-[#C05838] hover:bg-[#C05838] hover:text-white'
                                                        : 'bg-[#D6E8D5] text-[#1A4D2E] hover:bg-[#1A4D2E] hover:text-white'
                                                    }`}
                                            >
                                                {addingSchoolId === school.university_id ? (
                                                    <>
                                                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                                                        Adding...
                                                    </>
                                                ) : !hasCredits || (isFreeTier && collegeList.length >= FREE_TIER_SCHOOL_LIMIT) ? (
                                                    <>
                                                        <RocketLaunchIcon className="h-4 w-4" />
                                                        {isFreeTier ? 'Upgrade' : 'Get Credits'}
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

            {/* Analysis Progress Modal */}
            {analysisModal.isOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl p-8 max-w-sm w-full mx-4 text-center shadow-2xl">
                        <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-6 ${analysisModal.step === 'complete'
                            ? 'bg-green-100'
                            : analysisModal.step === 'error'
                                ? 'bg-red-100'
                                : 'bg-[#E8F5E9]'
                            }`}>
                            {analysisModal.step === 'complete' ? (
                                <svg className="w-10 h-10 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                            ) : analysisModal.step === 'error' ? (
                                <svg className="w-10 h-10 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            ) : (
                                <div className="w-10 h-10 border-4 border-[#D6E8D5] border-t-[#1A4D2E] rounded-full animate-spin" />
                            )}
                        </div>
                        <h3 className="text-xl font-bold text-gray-900 mb-2">
                            {analysisModal.step === 'complete'
                                ? 'Added Successfully!'
                                : analysisModal.step === 'error'
                                    ? 'Something went wrong'
                                    : 'Analyzing Fit...'}
                        </h3>
                        <p className="text-gray-600 mb-6">{analysisModal.universityName}</p>

                        {/* Progress Steps */}
                        {analysisModal.step !== 'complete' && analysisModal.step !== 'error' && (
                            <div className="space-y-2 text-left text-sm mb-4">
                                <div className="flex items-center gap-2">
                                    <span className={analysisModal.step === 'adding' ? 'text-[#1A4D2E] font-medium' : 'text-gray-400'}>
                                        {analysisModal.progress >= 20 && analysisModal.step !== 'adding' ? '✓' : '⏳'} Adding to list
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={analysisModal.step === 'fit' ? 'text-[#1A4D2E] font-medium' : 'text-gray-400'}>
                                        {analysisModal.progress >= 60 ? '✓' : analysisModal.step === 'fit' ? '⏳' : '○'} Computing fit analysis
                                    </span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={analysisModal.step === 'saving' ? 'text-[#1A4D2E] font-medium' : 'text-gray-400'}>
                                        {analysisModal.progress >= 90 ? '✓' : analysisModal.step === 'saving' ? '⏳' : '○'} Saving results
                                    </span>
                                </div>
                            </div>
                        )}

                        {/* Progress Bar */}
                        {analysisModal.step !== 'error' && (
                            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                <div
                                    className="h-full bg-[#1A4D2E] transition-all duration-500 ease-out"
                                    style={{ width: `${analysisModal.progress}%` }}
                                />
                            </div>
                        )}

                        {analysisModal.step === 'complete' && (
                            <p className="text-sm text-green-600 mt-4">Your personalized fit analysis is ready!</p>
                        )}
                        {analysisModal.step === 'error' && (
                            <p className="text-sm text-red-600 mt-4">Please try again later.</p>
                        )}
                    </div>
                </div>
            )}

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
