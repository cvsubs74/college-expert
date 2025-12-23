import React from 'react';
import { useNavigate } from 'react-router-dom';
import { XMarkIcon, BoltIcon, SparklesIcon, RocketLaunchIcon } from '@heroicons/react/24/outline';
import { usePayment } from '../context/PaymentContext';

/**
 * CreditsUpgradeModal - Shown when user runs out of credits
 * Free tier: Only shows upgrade options (Monthly/Season Pass)
 * Subscribers: Can also buy credit packs
 */
const CreditsUpgradeModal = ({ isOpen, onClose, creditsRemaining = 0, feature = 'fit analysis' }) => {
    const navigate = useNavigate();
    const { isFreeTier } = usePayment();

    if (!isOpen) return null;

    const handleMonthlyUpgrade = () => {
        onClose();
        navigate('/pricing?plan=monthly');
    };

    const handleSeasonPass = () => {
        onClose();
        navigate('/pricing?plan=season');
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
                        className="absolute right-4 top-4 p-2 hover:bg-gray-100 rounded-lg transition-colors z-10"
                    >
                        <XMarkIcon className="w-5 h-5 text-white/80 hover:text-white" />
                    </button>

                    {/* Header - Stratia Green Theme */}
                    <div className="bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] px-6 py-8 text-center">
                        <div className="mx-auto w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-4">
                            <RocketLaunchIcon className="w-8 h-8 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-white">
                            {isFreeTier ? 'Upgrade Your Plan' : 'Need More Credits'}
                        </h2>
                        <p className="text-white/80 mt-2">
                            {isFreeTier
                                ? 'Unlock more schools and premium features'
                                : <>You have <span className="font-bold">{creditsRemaining}</span> credits remaining</>
                            }
                        </p>
                    </div>

                    {/* Content */}
                    <div className="px-6 py-6">
                        <p className="text-gray-600 text-center mb-6">
                            {isFreeTier
                                ? 'Choose a plan to continue adding schools and running fit analysis:'
                                : `Running ${feature} requires credits. Choose an option below:`
                            }
                        </p>

                        {/* Options */}
                        <div className="space-y-3">
                            {/* Monthly Subscription */}
                            <button
                                onClick={handleMonthlyUpgrade}
                                className="w-full flex items-center gap-4 p-4 bg-[#D6E8D5] border-2 border-[#1A4D2E]/30 rounded-xl hover:border-[#1A4D2E] transition-colors text-left"
                            >
                                <div className="p-3 bg-[#1A4D2E]/10 rounded-lg">
                                    <SparklesIcon className="w-6 h-6 text-[#1A4D2E]" />
                                </div>
                                <div className="flex-1">
                                    <div className="font-semibold text-gray-900">Monthly Pass</div>
                                    <div className="text-sm text-gray-500">50 credits/month + AI chat</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-bold text-[#1A4D2E]">$9.99</div>
                                    <div className="text-xs text-gray-400">/month</div>
                                </div>
                            </button>

                            {/* Season Pass */}
                            <button
                                onClick={handleSeasonPass}
                                className="w-full flex items-center gap-4 p-4 bg-gradient-to-r from-[#D6E8D5] to-[#C5DFC4] border-2 border-[#1A4D2E]/40 rounded-xl hover:border-[#1A4D2E] transition-colors text-left relative"
                            >
                                <span className="absolute -top-2 right-4 px-2 py-0.5 bg-[#C05838] text-white text-xs font-bold rounded-full">
                                    BEST VALUE
                                </span>
                                <div className="p-3 bg-[#1A4D2E]/20 rounded-lg">
                                    <RocketLaunchIcon className="w-6 h-6 text-[#1A4D2E]" />
                                </div>
                                <div className="flex-1">
                                    <div className="font-semibold text-gray-900">Season Pass</div>
                                    <div className="text-sm text-gray-500">150 credits/year + unlimited AI</div>
                                </div>
                                <div className="text-right">
                                    <div className="font-bold text-[#1A4D2E]">$99</div>
                                    <div className="text-xs text-gray-400">/year</div>
                                </div>
                            </button>

                            {/* Credit Pack - Only for subscribers */}
                            {!isFreeTier && (
                                <button
                                    onClick={handleBuyCredits}
                                    className="w-full flex items-center gap-4 p-4 bg-[#FCEEE8] border-2 border-[#C05838]/30 rounded-xl hover:border-[#C05838] transition-colors text-left"
                                >
                                    <div className="p-3 bg-[#C05838]/10 rounded-lg">
                                        <BoltIcon className="w-6 h-6 text-[#C05838]" />
                                    </div>
                                    <div className="flex-1">
                                        <div className="font-semibold text-gray-900">Buy Credit Pack</div>
                                        <div className="text-sm text-gray-500">10 credits (never expire)</div>
                                    </div>
                                    <div className="text-right">
                                        <div className="font-bold text-[#C05838]">$10</div>
                                        <div className="text-xs text-gray-400">one-time</div>
                                    </div>
                                </button>
                            )}
                        </div>

                        {/* Footer note */}
                        <p className="text-xs text-gray-400 text-center mt-6">
                            Each fit analysis uses 1 credit. Cache hits are free!
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CreditsUpgradeModal;
