import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
    SparklesIcon,
    CheckCircleIcon,
    ArrowRightIcon
} from '@heroicons/react/24/outline';
import { usePayment } from '../context/PaymentContext';
import { useAuth } from '../context/AuthContext';
import { addUserCredits, upgradeSubscription } from '../services/api';

const PaymentSuccess = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { fetchPurchases, fetchCredits } = usePayment();
    const { currentUser } = useAuth();
    const [loading, setLoading] = useState(true);
    const [creditsAdded, setCreditsAdded] = useState(0);

    const sessionId = searchParams.get('session_id');

    useEffect(() => {
        // Refresh purchases and add credits after successful payment
        const refreshData = async () => {
            try {
                // First, fetch the purchase info
                await fetchPurchases();

                // Add credits to user's profile-manager-es account
                // Add credits based on product_id
                const productId = searchParams.get('product_id');

                if (currentUser?.email) {
                    console.log('[PaymentSuccess] Processing purchase for user:', currentUser.email, 'Product:', productId);
                    let result = { success: false };

                    if (productId === 'subscription_monthly') {
                        result = await upgradeSubscription(currentUser.email, null, 'monthly');
                    } else if (productId === 'subscription_annual') {
                        result = await upgradeSubscription(currentUser.email, null, 'season_pass');
                    } else if (productId === 'credit_pack_10') {
                        result = await addUserCredits(currentUser.email, 10, 'credit_pack');
                    } else {
                        // Fallback logic could go here, but safer to rely on explicit product IDs
                        console.warn('[PaymentSuccess] Unknown or missing product_id:', productId);
                    }

                    if (result.success) {
                        console.log('[PaymentSuccess] Credits/Tier updated:', result);
                        setCreditsAdded(result.credits_remaining || result.credits_added || 0);
                    } else {
                        console.warn('[PaymentSuccess] Failed to update credits/tier:', result.error);
                    }

                    // Refresh credits in context
                    if (fetchCredits) {
                        await fetchCredits();
                    }
                }
            } catch (error) {
                console.error('Error refreshing purchases:', error);
            } finally {
                setLoading(false);
            }
        };

        if (sessionId) {
            refreshData();
        } else {
            setLoading(false);
        }
    }, [sessionId, fetchPurchases, currentUser?.email, fetchCredits]);

    return (
        <div className="min-h-screen bg-[#FDFCF7] flex items-center justify-center px-6">
            <div className="max-w-md w-full text-center">
                {/* Success Icon */}
                <div className="mx-auto w-20 h-20 bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] rounded-full flex items-center justify-center mb-8 shadow-xl shadow-[#A8C5A6]">
                    {loading ? (
                        <SparklesIcon className="h-10 w-10 text-white animate-pulse" />
                    ) : (
                        <CheckCircleIcon className="h-10 w-10 text-white" />
                    )}
                </div>

                {/* Content */}
                <h1 className="text-3xl font-bold text-gray-900 mb-4">
                    {loading ? 'Processing...' : 'Payment Successful!'}
                </h1>

                <p className="text-lg text-gray-600 mb-8">
                    {loading
                        ? 'Please wait while we confirm your purchase...'
                        : 'Thank you for your purchase! Your account has been upgraded and you now have access to your new features.'
                    }
                </p>

                {/* What's next */}
                {!loading && (
                    <div className="bg-white rounded-2xl p-6 mb-8 border border-gray-200 text-left">
                        <h2 className="font-bold text-gray-900 mb-4">What's next?</h2>
                        <ul className="space-y-3">
                            <li className="flex items-start gap-3">
                                <span className="text-green-500 mt-1">✓</span>
                                <span className="text-gray-600">Your credits are ready to use immediately</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-green-500 mt-1">✓</span>
                                <span className="text-gray-600">Explore universities and add to your list</span>
                            </li>
                            <li className="flex items-start gap-3">
                                <span className="text-green-500 mt-1">✓</span>
                                <span className="text-gray-600">Get detailed fit analyses for your top choices</span>
                            </li>
                        </ul>
                    </div>
                )}

                {/* Actions */}
                <div className="space-y-3">
                    <button
                        onClick={() => navigate('/universities')}
                        className="w-full py-4 bg-[#1A4D2E] text-white text-lg font-bold rounded-xl hover:bg-[#2D6B45] transition-all shadow-lg flex items-center justify-center gap-2"
                    >
                        Start Exploring
                        <ArrowRightIcon className="h-5 w-5" />
                    </button>
                    <button
                        onClick={() => navigate('/profile')}
                        className="w-full py-3 bg-gray-100 text-gray-700 font-medium rounded-xl hover:bg-gray-200 transition-all"
                    >
                        Go to My Profile
                    </button>
                </div>

                {/* Receipt note */}
                <p className="text-sm text-gray-500 mt-8">
                    A receipt has been sent to your email address.
                </p>
            </div>
        </div>
    );
};

export default PaymentSuccess;
