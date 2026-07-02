import React, { useState, useEffect } from 'react';
import { AcademicCapIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { fetchStructuredProfile } from '../services/api';
import MajorMapCard from '../components/majors/MajorMapCard';

// ============================================================================
// MAJOR MAP PAGE (#302) — promotes the Major Map from a card buried in the
// Profile page to its own sidebar route. It loads the student's structured
// profile (same fetch Profile.jsx uses) so MajorMapCard can render its
// readiness-aware empty state, then hands off to the card unchanged — all the
// generate / stale / credit-gate behavior still lives in MajorMapCard.
// ============================================================================

const MajorMap = () => {
    const { currentUser } = useAuth();
    const [profile, setProfile] = useState(null);
    const [loadingProfile, setLoadingProfile] = useState(true);

    useEffect(() => {
        let cancelled = false;
        const load = async () => {
            if (!currentUser?.email) {
                setLoadingProfile(false);
                return;
            }
            setLoadingProfile(true);
            try {
                const result = await fetchStructuredProfile(currentUser.email);
                if (!cancelled && result?.success && result.profile) {
                    setProfile(result.profile);
                }
            } catch (err) {
                console.error('[MajorMap] Failed to load profile:', err);
            } finally {
                if (!cancelled) setLoadingProfile(false);
            }
        };
        load();
        return () => { cancelled = true; };
    }, [currentUser?.email]);

    return (
        <div className="max-w-4xl mx-auto p-4 sm:p-6">
            <div className="flex items-center gap-3 mb-2">
                <div className="h-10 w-10 rounded-xl bg-[#D6E8D5] flex items-center justify-center">
                    <AcademicCapIcon className="h-6 w-6 text-[#1A4D2E]" />
                </div>
                <div>
                    <h1 className="font-serif text-2xl font-semibold text-[#2C2C2C]">Major Map</h1>
                    <p className="text-sm text-[#6B6B6B]">
                        Career-theme clusters built from your own record — Stratia's read, not school facts.
                    </p>
                </div>
            </div>

            {loadingProfile ? (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mt-6" data-testid="major-map-page-loading">
                    <div className="animate-pulse space-y-3">
                        <div className="h-5 bg-gray-200 rounded w-1/3" />
                        <div className="h-20 bg-gray-100 rounded" />
                    </div>
                </div>
            ) : (
                currentUser?.email && (
                    <MajorMapCard userEmail={currentUser.email} profile={profile} />
                )
            )}
        </div>
    );
};

export default MajorMap;
