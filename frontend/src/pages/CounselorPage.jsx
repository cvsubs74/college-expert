
import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchStudentRoadmap } from '../services/api';
import RoadmapView from '../components/counselor/RoadmapView';
import CounselorChat from '../components/counselor/CounselorChat';
import { BackgroundBlobs } from '../components/stratia';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const CounselorPage = () => {
    const { currentUser } = useAuth();
    const [roadmap, setRoadmap] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const getRoadmap = async () => {
            if (!currentUser?.email) return;

            try {
                setLoading(true);
                // Default to '11th Grade' to trigger Junior Sprint if not in profile
                // In real app, would fetch profile first to get grade
                const data = await fetchStudentRoadmap(currentUser.email, '11th Grade');

                if (data.success) {
                    setRoadmap(data.roadmap);
                } else {
                    setError(data.error || 'Failed to load roadmap');
                }
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        getRoadmap();
    }, [currentUser]);

    return (
        <div className="min-h-screen bg-[#FDFCF7] relative font-sans overflow-hidden">
            <BackgroundBlobs />

            <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-screen flex flex-col">
                {/* Page Header */}
                <div className="mb-6 z-10">
                    <h1 className="text-3xl font-serif font-medium text-[#1A4D2E]">
                        Your Intelligent Counselor
                    </h1>
                    <p className="mt-1 text-stone-600">
                        A proactive guide to navigate your college admissions journey.
                    </p>
                </div>

                {/* Content Grid */}
                <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0 z-10 pb-6">
                    {/* Main Content - Roadmap (2/3 width) */}
                    <div className="lg:col-span-2 min-h-0">
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
                            <RoadmapView
                                roadmap={roadmap}
                                isLoading={loading}
                            />
                        )}
                    </div>

                    {/* Sidebar - Chat (1/3 width) */}
                    <div className="lg:col-span-1 min-h-0">
                        <CounselorChat />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CounselorPage;
