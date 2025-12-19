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

    // Color based on credits remaining
    const getColorClasses = () => {
        if (creditsRemaining <= 0) {
            return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800';
        }
        if (creditsRemaining <= 5) {
            return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800';
        }
        if (creditsTier === 'pro') {
            return 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800';
        }
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800';
    };

    if (compact) {
        return (
            <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${getColorClasses()}`}>
                <BoltIcon className="w-3 h-3" />
                <span>{creditsRemaining}</span>
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
