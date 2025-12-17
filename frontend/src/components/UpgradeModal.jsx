import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    XMarkIcon,
    SparklesIcon,
    RocketLaunchIcon,
    LockClosedIcon,
    ArrowRightIcon
} from '@heroicons/react/24/outline';
import { usePayment } from '../context/PaymentContext';

const UpgradeModal = () => {
    const navigate = useNavigate();
    const { showUpgradeModal, upgradeReason, upgradeFeature, closeUpgradeModal } = usePayment();

    if (!showUpgradeModal) return null;

    const getFeatureIcon = () => {
        switch (upgradeFeature) {
            case 'college_slots':
                return RocketLaunchIcon;
            case 'fit_analysis':
                return SparklesIcon;
            case 'explorer':
                return LockClosedIcon;
            default:
                return SparklesIcon;
        }
    };

    const getFeatureTitle = () => {
        switch (upgradeFeature) {
            case 'college_slots':
                return 'Add More Colleges';
            case 'fit_analysis':
                return 'Unlock Fit Analyses';
            case 'explorer':
                return 'Unlock University Explorer';
            case 'ai_messages':
                return 'Get More AI Messages';
            case 'essay_strategy':
                return 'Unlock Essay Strategy';
            default:
                return 'Upgrade Your Plan';
        }
    };

    const getSuggestedProduct = () => {
        switch (upgradeFeature) {
            case 'college_slots':
                return { name: '5 More Colleges', price: 39 };
            case 'fit_analysis':
                return { name: 'Deep Fit Analysis', price: 19 };
            case 'explorer':
                return { name: 'Explorer Pass', price: 29 };
            case 'ai_messages':
                return { name: '50 AI Messages', price: 9 };
            default:
                return { name: 'Starter Pack', price: 99 };
        }
    };

    const FeatureIcon = getFeatureIcon();
    const suggestedProduct = getSuggestedProduct();

    const handleViewPricing = () => {
        closeUpgradeModal();
        navigate('/pricing');
    };

    return (
        <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
                {/* Backdrop */}
                <div
                    className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity"
                    onClick={closeUpgradeModal}
                />

                {/* Modal */}
                <div className="inline-block align-bottom bg-white rounded-3xl text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-8 text-center">
                        <div className="mx-auto w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center mb-4">
                            <FeatureIcon className="h-8 w-8 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-2">
                            {getFeatureTitle()}
                        </h2>
                        <p className="text-white/80">
                            {upgradeReason}
                        </p>
                        <button
                            onClick={closeUpgradeModal}
                            className="absolute top-4 right-4 p-2 text-white/80 hover:text-white transition-colors"
                        >
                            <XMarkIcon className="h-6 w-6" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="px-6 py-6">
                        {/* Quick purchase option */}
                        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="font-semibold text-gray-900">{suggestedProduct.name}</p>
                                    <p className="text-sm text-gray-600">Instant access</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-2xl font-bold text-gray-900">${suggestedProduct.price}</p>
                                </div>
                            </div>
                        </div>

                        {/* Benefits */}
                        <div className="space-y-3 mb-6">
                            <p className="text-sm text-gray-600">With this upgrade you'll get:</p>
                            <ul className="space-y-2">
                                {upgradeFeature === 'college_slots' && (
                                    <>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Add 5 more colleges to your list
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Track deadlines for each
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Basic fit scores included
                                        </li>
                                    </>
                                )}
                                {upgradeFeature === 'fit_analysis' && (
                                    <>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Detailed admission probability
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Gap analysis & recommendations
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Comparison to admitted students
                                        </li>
                                    </>
                                )}
                                {upgradeFeature === 'explorer' && (
                                    <>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Access to 150+ universities
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Advanced search & filters
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Save favorites for later
                                        </li>
                                    </>
                                )}
                                {upgradeFeature === 'ai_messages' && (
                                    <>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> 50 more AI counselor messages
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Get personalized advice
                                        </li>
                                        <li className="flex items-center gap-2 text-sm text-gray-700">
                                            <span className="text-green-500">✓</span> Ask about any college topic
                                        </li>
                                    </>
                                )}
                            </ul>
                        </div>

                        {/* Buttons */}
                        <div className="space-y-3">
                            <button
                                onClick={handleViewPricing}
                                className="w-full py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-bold rounded-xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200 flex items-center justify-center gap-2"
                            >
                                View All Options
                                <ArrowRightIcon className="h-5 w-5" />
                            </button>
                            <button
                                onClick={closeUpgradeModal}
                                className="w-full py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 transition-all"
                            >
                                Maybe Later
                            </button>
                        </div>

                        {/* Bundle upsell */}
                        <div className="mt-6 text-center">
                            <p className="text-sm text-gray-500">
                                💡 <span className="font-medium">Pro tip:</span> Save up to 50% with our bundles
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UpgradeModal;
