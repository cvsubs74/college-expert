import React, { useState } from 'react';
import { XMarkIcon, UserCircleIcon, ArrowRightIcon } from '@heroicons/react/24/outline';
import { useNavigate } from 'react-router-dom';

/**
 * Contextual banner prompting users to complete their profile
 * Shows on pages like UniInsight, Launchpad when profile is incomplete
 */
const ProfileBanner = ({ onDismiss, variant = 'default' }) => {
    const navigate = useNavigate();
    const [isVisible, setIsVisible] = useState(true);

    const handleDismiss = () => {
        setIsVisible(false);
        // Remember dismissal for this session
        sessionStorage.setItem('profileBannerDismissed', 'true');
        if (onDismiss) onDismiss();
    };

    const handleCompleteProfile = () => {
        navigate('/profile');
    };

    // Check if already dismissed this session
    if (!isVisible || sessionStorage.getItem('profileBannerDismissed') === 'true') {
        return null;
    }

    // Compact variant for sidebars/cards
    if (variant === 'compact') {
        return (
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-4 border border-amber-100">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg shadow-sm">
                        <UserCircleIcon className="h-5 w-5 text-amber-500" />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium text-gray-700">Complete your profile</p>
                        <p className="text-xs text-gray-500">Get personalized fit analysis</p>
                    </div>
                    <button
                        onClick={handleCompleteProfile}
                        className="px-3 py-1.5 bg-amber-500 text-white text-sm font-medium rounded-lg hover:bg-amber-600 transition-colors"
                    >
                        Start
                    </button>
                </div>
            </div>
        );
    }

    // Inline variant for fit analysis modal
    if (variant === 'inline') {
        return (
            <div className="text-center py-12 px-6">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 mb-4">
                    <UserCircleIcon className="h-8 w-8 text-amber-500" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Personalized Analysis Awaits</h3>
                <p className="text-gray-600 mb-6 max-w-sm mx-auto">
                    Complete your profile and add this university to your Launchpad to see detailed fit analysis.
                </p>
                <div className="flex items-center justify-center gap-3">
                    <button
                        onClick={handleCompleteProfile}
                        className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-medium rounded-xl shadow-lg shadow-amber-200 hover:shadow-xl transition-all"
                    >
                        Complete Profile
                        <ArrowRightIcon className="h-4 w-4" />
                    </button>
                </div>
            </div>
        );
    }

    // Default full-width banner
    return (
        <div className="relative bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl p-4 mb-6 shadow-lg shadow-amber-200/50">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-2.5 bg-white/20 rounded-xl backdrop-blur-sm">
                        <UserCircleIcon className="h-6 w-6 text-white" />
                    </div>
                    <div>
                        <h3 className="text-white font-semibold">Complete your profile for personalized matches</h3>
                        <p className="text-amber-100 text-sm">See how well you fit each university based on your academics and activities</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleCompleteProfile}
                        className="flex items-center gap-2 px-5 py-2.5 bg-white text-amber-600 font-semibold rounded-xl shadow-md hover:shadow-lg transition-all"
                    >
                        Complete Profile
                        <ArrowRightIcon className="h-4 w-4" />
                    </button>
                    <button
                        onClick={handleDismiss}
                        className="p-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <XMarkIcon className="h-5 w-5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ProfileBanner;
