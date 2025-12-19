import React from 'react';
import { useNavigate } from 'react-router-dom';
import { XMarkIcon, BoltIcon, SparklesIcon, RocketLaunchIcon } from '@heroicons/react/24/outline';

/**
 * CreditsUpgradeModal - Shown when user runs out of credits
 * Prompts user to buy credits or upgrade to Pro
 */
const CreditsUpgradeModal = ({ isOpen, onClose, creditsRemaining = 0, feature = 'fit analysis' }) => {
    const navigate = useNavigate();

    if (!isOpen) return null;

    const handleUpgrade = () => {
        onClose();
        navigate('/pricing');
    };

    const handleBuyCredits = () => {
        onClose();
        navigate('/pricing?tab=credits');
    };

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="flex min-h-full items-center justify-center p-4">
                <div className="relative w-full max-w-md transform overflow-hidden rounded-2xl bg-white shadow-2xl transition-all">
                    {/* Close button */}
                    <button
                        onClick={onClose}
                        className="absolute right-4 top-4 p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <XMarkIcon className="w-5 h-5 text-gray-400" />
                    </button>

                    {/* Header */}
                    <div className="bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-8 text-center">
                        <div className="mx-auto w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-4">
                            <BoltIcon className="w-8 h-8 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-white">Need More Credits</h2>
                        <p className="text-white/80 mt-2">
                            You have <span className="font-bold">{creditsRemaining}</span> credits remaining
                        </p>
                    </div>

                    {/* Content */}
                    <div className="px-6 py-6">
                        <p className="text-gray-600 text-center mb-6">
                            Running {feature} requires credits. Choose an option below to continue:
                        </p>

                        {/* Options */}
                        <div className="space-y-3">
                            {/* Pro Subscription */}
                            <button
                                onClick={handleUpgrade}
                                className="w-full flex items-center gap-4 p-4 bg-gradient-to-r from-purple-50 to-blue-50 border-2 border-purple-200 rounded-xl hover:border-purple-400 transition-colors text-left"
                            >
                                <div className="p-3 bg-purple-100 rounded-lg">
                                    <SparklesIcon className="w-6 h-6 text-purple-600" />
                                </div>
                                <div className="flex-1">
                                    <div className="font-semibold text-gray-900">Upgrade to Pro</div>
                                    <div className="text-sm text-gray-500">50 credits + unlimited colleges</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-bold text-purple-600">$99</div>
                                    <div className="text-xs text-gray-400">/year</div>
                                </div>
                            </button>

                            {/* Credit Pack */}
                            <button
                                onClick={handleBuyCredits}
                                className="w-full flex items-center gap-4 p-4 bg-amber-50 border-2 border-amber-200 rounded-xl hover:border-amber-400 transition-colors text-left"
                            >
                                <div className="p-3 bg-amber-100 rounded-lg">
                                    <BoltIcon className="w-6 h-6 text-amber-600" />
                                </div>
                                <div className="flex-1">
                                    <div className="font-semibold text-gray-900">Buy Credit Pack</div>
                                    <div className="text-sm text-gray-500">50 credits for analysis</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-bold text-amber-600">$10</div>
                                    <div className="text-xs text-gray-400">one-time</div>
                                </div>
                            </button>
                        </div>

                        {/* Footer note */}
                        <p className="text-xs text-gray-400 text-center mt-6">
                            Each fit analysis (including infographic) uses 1 credit.
                            <br />Cache hits are free!
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CreditsUpgradeModal;
