import React from 'react';
import { usePayment } from '../context/PaymentContext';
import { SparklesIcon, BoltIcon } from '@heroicons/react/24/outline';

/**
 * CreditsBadge - Displays user's credit balance
 * Shows remaining credits and tier info with visual feedback
 */
const CreditsBadge = ({ showTier = false, compact = false }) => {
    const { creditsRemaining, creditsTier, creditsLoading, hasCredits } = usePayment();

    if (creditsLoading) {
        return (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-800 animate-pulse">
                <div className="w-14 h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
        );
    }

    // Color based on credits remaining - using solid backgrounds for high visibility
    const getColorClasses = () => {
        if (creditsRemaining <= 0) {
            // Solid red with white text for maximum visibility
            return 'bg-red-500 text-white border-red-600 shadow-md';
        }
        if (creditsRemaining <= 5) {
            // Solid amber with white text
            return 'bg-amber-500 text-white border-amber-600 shadow-md';
        }
        if (creditsTier === 'pro') {
            return 'bg-purple-600 text-white border-purple-700 shadow-md';
        }
        // Default: dark slate for high contrast on light background
        return 'bg-slate-700 text-white border-slate-800 shadow-md';
    };

    if (compact) {
        return (
            <div className="relative group">
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border cursor-help ${getColorClasses()}`}>
                    <BoltIcon className="w-3.5 h-3.5" />
                    <span>{creditsRemaining} AI {creditsRemaining === 1 ? 'query' : 'queries'}</span>
                </div>
                {/* Tooltip on hover */}
                <div className="hidden group-hover:block absolute top-full right-0 mt-2 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl w-56 z-50">
                    <p className="font-medium mb-1">AI Query Credits</p>
                    <p className="text-gray-300 leading-relaxed">
                        Credits are used for fit analysis, profile updates via chat, and AI-powered recommendations.
                    </p>
                    {creditsRemaining <= 3 && (
                        <p className="mt-2 text-amber-400">
                            Running low! Upgrade for more credits.
                        </p>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium border ${getColorClasses()}`}>
            <BoltIcon className="w-4 h-4" />
            <span>{creditsRemaining} credit{creditsRemaining !== 1 ? 's' : ''}</span>
            {showTier && creditsTier === 'pro' && (
                <span className="flex items-center gap-1 ml-1">
                    <SparklesIcon className="w-3 h-3" />
                    Pro
                </span>
            )}
            {!hasCredits && (
                <span className="text-xs opacity-75">(need more)</span>
            )}
        </div>
    );
};

export default CreditsBadge;
