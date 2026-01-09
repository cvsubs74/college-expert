import React from 'react';
import { useNavigate } from 'react-router-dom';
import { XMarkIcon, BoltIcon, SparklesIcon, RocketLaunchIcon, CheckIcon } from '@heroicons/react/24/outline';
import { usePayment } from '../context/PaymentContext';

/**
 * CreditsUpgradeModal - Shown when user needs to upgrade
 * Matches the pricing page format with full feature details
 * Free tier: Only shows Monthly/Season Pass (no credit pack)
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

    // Feature list component
    const FeatureItem = ({ children }) => (
        <li className="flex items-start gap-2 text-sm text-gray-600">
            <CheckIcon className="w-4 h-4 text-[#1A4D2E] mt-0.5 flex-shrink-0" />
            <span>{children}</span>
        </li>
    );

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="flex min-h-full items-center justify-center p-4">
                <div className="relative w-full max-w-3xl transform overflow-hidden rounded-2xl bg-[#F5F5F0] shadow-2xl transition-all">
                    {/* Close button */}
                    <button
                        onClick={onClose}
                        className="absolute right-4 top-4 p-2 hover:bg-white/50 rounded-lg transition-colors z-10"
                    >
                        <XMarkIcon className="w-6 h-6 text-gray-500" />
                    </button>

                    {/* Header */}
                    <div className="text-center pt-8 pb-4 px-6">
                        <div className="mx-auto w-14 h-14 bg-[#1A4D2E] rounded-full flex items-center justify-center mb-4">
                            <RocketLaunchIcon className="w-7 h-7 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900">Upgrade Your Plan</h2>
                        <p className="text-gray-600 mt-2">
                            Choose a plan to continue adding schools and running fit analysis
                        </p>
                    </div>

                    {/* Plans Grid */}
                    <div className="px-6 pb-8">
                        <div className="grid md:grid-cols-3 gap-4">
                            {/* Free Tier */}
                            <div className="bg-white rounded-xl p-6 border-2 border-gray-200 hover:border-gray-300 transition-all cursor-pointer group"
                                onClick={() => {
                                    onClose();
                                    navigate('/launchpad');
                                }}>
                                <div className="flex items-start gap-3 mb-4">
                                    <div className="p-2 bg-gray-100 rounded-lg">
                                        <SparklesIcon className="w-5 h-5 text-gray-600" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-gray-900">Free</h3>
                                        <p className="text-xs text-gray-500">Perfect for exploring. Try fit analysis on your top 3 schools.</p>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <span className="text-3xl font-bold text-gray-900">$0</span>
                                    <span className="text-gray-500">/forever</span>
                                </div>

                                <div className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full mb-4">
                                    <BoltIcon className="w-3 h-3" />
                                    3 credits
                                </div>

                                <div className="border-t border-gray-100 pt-4 mb-4">
                                    <p className="text-xs font-semibold text-gray-400 mb-2">BEST FOR</p>
                                    <p className="text-sm text-gray-700">Sophomores & Juniors exploring</p>
                                </div>

                                <ul className="space-y-2 mb-6">
                                    <FeatureItem>3 fit analysis credits</FeatureItem>
                                    <FeatureItem>Chat with AI on universities</FeatureItem>
                                    <FeatureItem>Browse 200+ profiles</FeatureItem>
                                    <FeatureItem>Build your profile</FeatureItem>
                                </ul>

                                <button
                                    onClick={() => {
                                        onClose();
                                        navigate('/launchpad');
                                    }}
                                    className="w-full py-3 bg-gray-900 text-white font-semibold rounded-full hover:bg-gray-800 transition-colors"
                                >
                                    Use Free Plan →
                                </button>
                            </div>

                            {/* Monthly Plan */}
                            <div className="bg-white rounded-xl p-6 border-2 border-gray-200 hover:border-[#1A4D2E] transition-all cursor-pointer group"
                                onClick={handleMonthlyUpgrade}>
                                <div className="flex items-start gap-3 mb-4">
                                    <div className="p-2 bg-[#D6E8D5] rounded-lg">
                                        <SparklesIcon className="w-5 h-5 text-[#1A4D2E]" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-gray-900">Monthly</h3>
                                        <p className="text-xs text-gray-500">Great for active research. Analyze multiple schools each month.</p>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <span className="text-3xl font-bold text-gray-900">$15</span>
                                    <span className="text-gray-500">/month</span>
                                </div>

                                <div className="inline-flex items-center gap-1 px-3 py-1 bg-[#D6E8D5] text-[#1A4D2E] text-xs font-semibold rounded-full mb-4">
                                    <BoltIcon className="w-3 h-3" />
                                    20 credits
                                </div>

                                <div className="border-t border-gray-100 pt-4 mb-4">
                                    <p className="text-xs font-semibold text-gray-400 mb-2">BEST FOR</p>
                                    <p className="text-sm text-gray-700">Students building their college list</p>
                                </div>

                                <ul className="space-y-2 mb-6">
                                    <FeatureItem>20 fit analyses/month</FeatureItem>
                                    <FeatureItem>Unlimited AI chat on all universities</FeatureItem>
                                    <FeatureItem>Compare schools side-by-side</FeatureItem>
                                    <FeatureItem>Cancel anytime, no commitment</FeatureItem>
                                </ul>

                                <button
                                    onClick={handleMonthlyUpgrade}
                                    className="w-full py-3 bg-[#1A4D2E] text-white font-semibold rounded-full hover:bg-[#143D24] transition-colors group-hover:shadow-lg"
                                >
                                    Start Monthly →
                                </button>
                            </div>

                            {/* Season Pass */}
                            <div className="bg-white rounded-xl p-6 border-2 border-[#1A4D2E] relative cursor-pointer group"
                                onClick={handleSeasonPass}>
                                {/* Best Value Badge */}
                                <div className="absolute -top-3 right-6 px-3 py-1 bg-[#C05838] text-white text-xs font-bold rounded-full">
                                    BEST VALUE
                                </div>

                                <div className="flex items-start gap-3 mb-4">
                                    <div className="p-2 bg-[#D6E8D5] rounded-lg">
                                        <RocketLaunchIcon className="w-5 h-5 text-[#1A4D2E]" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-gray-900">Season Pass</h3>
                                        <p className="text-xs text-gray-500">Best value for your entire application journey — from research to acceptance.</p>
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <span className="text-3xl font-bold text-gray-900">$99</span>
                                    <span className="text-gray-500">/year</span>
                                </div>

                                <div className="inline-flex items-center gap-1 px-3 py-1 bg-[#D6E8D5] text-[#1A4D2E] text-xs font-semibold rounded-full mb-4">
                                    <BoltIcon className="w-3 h-3" />
                                    150 credits
                                </div>

                                <div className="border-t border-gray-100 pt-4 mb-4">
                                    <p className="text-xs font-semibold text-gray-400 mb-2">BEST FOR</p>
                                    <p className="text-sm text-gray-700">Seniors applying this year</p>
                                </div>

                                <ul className="space-y-2 mb-6">
                                    <FeatureItem>150 fit analyses for the year</FeatureItem>
                                    <FeatureItem>Unlimited AI chat on all universities</FeatureItem>
                                    <FeatureItem>Covers entire application season</FeatureItem>
                                    <FeatureItem>Priority support when you need it</FeatureItem>
                                </ul>

                                <button
                                    onClick={handleSeasonPass}
                                    className="w-full py-3 bg-[#1A4D2E] text-white font-semibold rounded-full hover:bg-[#143D24] transition-colors group-hover:shadow-lg"
                                >
                                    Get Season Pass →
                                </button>
                            </div>
                        </div>

                        {/* Credit Pack - Only for subscribers */}
                        {!isFreeTier && (
                            <div className="mt-4 p-4 bg-white rounded-xl border border-gray-200 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-[#FCEEE8] rounded-lg">
                                        <BoltIcon className="w-5 h-5 text-[#C05838]" />
                                    </div>
                                    <div>
                                        <h4 className="font-semibold text-gray-900">Credit Pack</h4>
                                        <p className="text-xs text-gray-500">Need a few more analyses? Add credits anytime.</p>
                                    </div>
                                </div>
                                <button
                                    onClick={handleBuyCredits}
                                    className="px-4 py-2 text-[#C05838] font-medium hover:bg-[#FCEEE8] rounded-full transition-colors"
                                >
                                    $10 for 10 credits →
                                </button>
                            </div>
                        )}

                        {/* Footer note */}
                        <p className="text-xs text-gray-400 text-center mt-6">
                            1 credit = 1 comprehensive fit analysis for any university. Cache hits are free!
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CreditsUpgradeModal;
