import React from 'react';
import { XMarkIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

/**
 * CancelSubscriptionModal - Themed confirmation modal for subscription cancellation
 * Matches Stratia app design with proper modal backdrop
 */
const CancelSubscriptionModal = ({ isOpen, onClose, onConfirm, subscriptionType, endDate }) => {
    if (!isOpen) return null;

    const isPremium = subscriptionType === 'subscription_monthly' || subscriptionType === 'subscription_annual';
    const planName = subscriptionType === 'subscription_monthly' ? 'Monthly' : 'Season Pass';

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
                        <XMarkIcon className="w-5 h-5 text-gray-500" />
                    </button>

                    {/* Header */}
                    <div className="text-center pt-8 pb-4 px-6">
                        <div className="mx-auto w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mb-4">
                            <ExclamationTriangleIcon className="w-7 h-7 text-red-600" />
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900">Cancel Subscription?</h2>
                    </div>

                    {/* Content */}
                    <div className="px-6 pb-6">
                        <div className="bg-[#F8F6F0] rounded-xl p-4 mb-6 border border-[#E0DED8]">
                            <p className="text-sm text-gray-700 mb-2">
                                Your <span className="font-semibold">{planName}</span> subscription will be cancelled.
                            </p>
                            <p className="text-sm text-gray-700">
                                You'll keep your <span className="font-semibold">credits and access</span> until{' '}
                                <span className="font-semibold text-[#1A4D2E]">{endDate}</span>, then default to the Free plan.
                            </p>
                        </div>

                        {/* What happens next */}
                        <div className="space-y-2 mb-6">
                            <h3 className="text-sm font-semibold text-gray-900">What happens next:</h3>
                            <ul className="space-y-1.5 text-sm text-gray-600">
                                <li className="flex items-start gap-2">
                                    <span className="text-[#1A4D2E] mt-0.5">✓</span>
                                    <span>All credits valid until {endDate}</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-[#1A4D2E] mt-0.5">✓</span>
                                    <span>Full access to all features until then</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-red-600 mt-0.5">✗</span>
                                    <span>No refunds for unused time</span>
                                </li>
                                <li className="flex items-start gap-2">
                                    <span className="text-red-600 mt-0.5">✗</span>
                                    <span>After {endDate}: 3 credits/analyses only</span>
                                </li>
                            </ul>
                        </div>

                        {/* Action Buttons */}
                        <div className="flex gap-3">
                            <button
                                onClick={onClose}
                                className="flex-1 px-4 py-3 bg-[#F8F6F0] text-gray-700 font-semibold rounded-full hover:bg-[#E0DED8] transition-colors border border-[#E0DED8]"
                            >
                                Keep Subscription
                            </button>
                            <button
                                onClick={() => {
                                    onConfirm();
                                    onClose();
                                }}
                                className="flex-1 px-4 py-3 bg-red-600 text-white font-semibold rounded-full hover:bg-red-700 transition-colors"
                            >
                                Confirm Cancel
                            </button>
                        </div>

                        {/* Footer note */}
                        <p className="text-xs text-gray-400 text-center mt-4">
                            You can reactivate anytime before {endDate}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CancelSubscriptionModal;
