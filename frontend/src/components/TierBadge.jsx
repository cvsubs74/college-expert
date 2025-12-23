import React from 'react';
import { Link } from 'react-router-dom';
import { StarIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { usePayment } from '../context/PaymentContext';

/**
 * TierBadge - Shows user's current tier
 * Displays in the navigation/header area
 */
const TierBadge = () => {
    const {
        currentTier,
        isFreeTier,
        isMonthly,
        isSeasonal,
        aiMessagesAvailable,
        loading
    } = usePayment();

    if (loading) {
        return (
            <div className="px-3 py-1.5 bg-gray-100 rounded-full animate-pulse">
                <span className="text-xs text-gray-400">Loading...</span>
            </div>
        );
    }

    if (isSeasonal) {
        return (
            <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-3 py-1.5 bg-gradient-to-r from-green-100 to-emerald-100 text-green-800 text-xs font-bold rounded-full border border-green-200">
                    <StarIcon className="h-3.5 w-3.5 mr-1" />
                    SEASON PASS
                </span>
            </div>
        );
    }

    if (isMonthly) {
        return (
            <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-3 py-1.5 bg-gradient-to-r from-amber-100 to-orange-100 text-amber-800 text-xs font-bold rounded-full border border-amber-200">
                    <SparklesIcon className="h-3.5 w-3.5 mr-1" />
                    MONTHLY
                </span>
            </div>
        );
    }

    // Free tier - show remaining messages and upgrade button
    return (
        <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-full border border-gray-200">
                <span className="text-xs font-medium text-gray-600">Free</span>
                <span className="text-gray-300">|</span>
                <span className="text-xs text-gray-500">
                    {aiMessagesAvailable === 'unlimited' ? '∞' : aiMessagesAvailable} msgs left
                </span>
            </div>
            <Link
                to="/pricing"
                className="inline-flex items-center px-2.5 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-bold rounded-full hover:from-amber-400 hover:to-orange-400 transition-all"
            >
                <StarIcon className="h-3 w-3 mr-1" />
                Upgrade
            </Link>
        </div>
    );
};

export default TierBadge;
