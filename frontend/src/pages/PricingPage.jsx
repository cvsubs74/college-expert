import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
    SparklesIcon,
    CheckIcon,
    BoltIcon,
    RocketLaunchIcon,
    ArrowRightIcon,
    AcademicCapIcon,
    LightBulbIcon,
    CheckCircleIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';
import { createCheckoutSession, reactivateSubscription } from '../services/paymentService';
import CancelSubscriptionModal from '../components/CancelSubscriptionModal';

const PricingPage = () => {
    const navigate = useNavigate();
    const { currentUser } = useAuth();
    const { creditsRemaining, creditsTier, isMonthly, isSeasonal, purchases } = usePayment();
    const [loading, setLoading] = useState(null);
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [cancelEndDate, setCancelEndDate] = useState(null);

    const isCanceling = purchases?.subscription_cancel_at_period_end;

    const handleGetStarted = async (planId) => {
        try {
            if (!currentUser) {
                await signInWithGoogle();
            }

            if (planId === 'free') {
                navigate('/profile');
                return;
            }

            // Start Stripe checkout for paid plans
            setLoading(planId);
            const result = await createCheckoutSession(currentUser.email, planId);
            if (result.setup_required) {
                alert('Payment system is being configured. Please try again later.');
            }
            setLoading(null);
        } catch (error) {
            console.error('Failed to process:', error);
            setLoading(null);
        }
    };

    const handleCancelClick = async () => {
        // Get subscription end date for modal display
        try {
            const { getSubscriptionStatus } = await import('../services/paymentService');
            const status = await getSubscriptionStatus(currentUser.email);
            if (status.success && status.subscription_current_period_end) {
                const endDate = new Date(status.subscription_current_period_end).toLocaleDateString();
                setCancelEndDate(endDate);
            }
        } catch (error) {
            console.error('Failed to get subscription status:', error);
            setCancelEndDate('the end of your billing period');
        }
        setShowCancelModal(true);
    };

    const handleCancelConfirm = async () => {
        try {
            setLoading('canceling');
            const { cancelSubscription } = await import('../services/paymentService');
            const result = await cancelSubscription(currentUser.email);

            if (result.success) {
                // Refresh page to update UI
                window.location.reload();
            } else {
                alert(`Failed to cancel: ${result.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Failed to cancel subscription:', error);
            alert('Failed to cancel subscription. Please try again.');
        } finally {
            setLoading(null);
        }
    };

    const handleReactivate = async () => {
        if (!currentUser?.email) return;

        setLoading('reactivate');
        try {
            const result = await reactivateSubscription(currentUser.email);
            if (result.success) {
                // Refresh page to show active status
                window.location.reload();
            }
        } catch (error) {
            console.error('Error reactivating:', error);
        } finally {
            setLoading(null);
        }
    };

    const cancellationDate = purchases?.subscription_end_date ? new Date(purchases.subscription_end_date).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '';
    const renewalDate = purchases?.subscription_current_period_end ? new Date(purchases.subscription_current_period_end).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '';

    const allPlans = [
        {
            id: 'free',
            name: 'Free',
            price: '$0',
            period: 'forever',
            description: 'Perfect for exploring. Try fit analysis on your top 3 schools.',
            icon: AcademicCapIcon,
            gradient: 'from-gray-500 to-gray-600',
            borderColor: 'border-gray-200',
            credits: 3,
            bestFor: 'Sophomores & Juniors exploring options',
            features: [
                { text: '3 fit analysis credits', included: true, highlight: true },
                { text: 'Chat with AI on university pages', included: true },
                { text: 'Browse 200+ university profiles', included: true },
                { text: 'Build your student profile', included: true },
            ],
            cta: currentUser ? 'Go to Dashboard' : 'Start Free',
            ctaStyle: 'bg-gray-900 text-white hover:bg-gray-800'
        },
        {
            id: 'subscription_monthly',
            name: 'Monthly',
            price: '$15',
            period: '/month',
            description: 'Great for active research. Analyze multiple schools each month.',
            icon: SparklesIcon,
            gradient: 'from-[#1A4D2E] to-[#2D6B45]',
            borderColor: 'border-[#A8C5A6]',
            credits: 20,
            bestFor: 'Students building their college list',
            features: [
                { text: '20 fit analyses/month', included: true, highlight: true },
                { text: 'Unlimited AI chat on all universities', included: true },
                { text: 'Compare schools side-by-side', included: true },
                { text: 'Cancel anytime, no commitment', included: true },
            ],
            cta: isMonthly ? 'Already Subscribed' : (isSeasonal ? 'Included in Season Pass' : 'Start Monthly'),
            ctaStyle: 'bg-[#1A4D2E] text-white hover:bg-[#2D6B45] shadow-md',
            disabled: isMonthly || isSeasonal
        },
        {
            id: 'subscription_annual',
            name: 'Season Pass',
            price: '$99',
            period: '/year',
            description: 'Best value for your entire application journey — from research to acceptance.',
            icon: RocketLaunchIcon,
            gradient: 'from-[#1A4D2E] to-[#2D6B45]',
            borderColor: 'border-[#1A4D2E]',
            credits: 150,
            popular: true,
            badge: 'Best Value',
            bestFor: 'Seniors applying this year',
            features: [
                { text: '150 fit analyses for the year', included: true, highlight: true },
                { text: 'Unlimited AI chat on all universities', included: true },
                { text: 'Covers entire application season', included: true },
                { text: 'Priority support when you need it', included: true },
            ],
            cta: isSeasonal ? 'Already Subscribed' : (isMonthly ? 'Upgrade to Season Pass' : 'Get Season Pass'),
            ctaStyle: 'bg-[#1A4D2E] text-white hover:bg-[#2D6B45] shadow-md',
            disabled: isSeasonal
        },
        {
            id: 'credit_pack_10',
            name: 'Credit Pack',
            price: '$9',
            period: 'one-time',
            description: 'Need a few more analyses? Add credits anytime.',
            icon: BoltIcon,
            gradient: 'from-[#1A4D2E] to-[#2D6B45]',
            borderColor: 'border-[#A8C5A6]',
            credits: 10,
            bestFor: 'When you need extra analyses',
            features: [
                { text: '+10 fit analysis credits', included: true, highlight: true },
                { text: 'Credits never expire', included: true },
                { text: 'Use with any plan', included: true },
                { text: 'Instant activation', included: true },
            ],
            cta: (isMonthly || isSeasonal) ? 'Buy Credits' : 'Requires Subscription',
            ctaStyle: (isMonthly || isSeasonal) ? 'bg-[#1A4D2E] text-white hover:bg-[#2D6B45] shadow-md' : 'bg-gray-300 text-gray-500 cursor-not-allowed',
            disabled: !(isMonthly || isSeasonal),
            subscriberOnly: true,
        }
    ];

    // Show all plans (no filtering)
    const plans = allPlans;

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            {/* Header */}
            <header className="px-6 py-5 bg-[#FDFCF7]/95 backdrop-blur-sm sticky top-0 z-50 border-b border-[#E0DED8]">
                <nav className="max-w-7xl mx-auto flex items-center justify-between">
                    <Link to="/launchpad" className="flex items-center">
                        <img
                            src="/logo.png"
                            alt="Stratia Admissions"
                            className="h-24 w-auto object-contain mix-blend-multiply"
                        />
                    </Link>
                    <div className="flex items-center gap-4">
                        {currentUser && (
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-[#D6E8D5] rounded-full text-sm font-medium text-[#1A4D2E]">
                                <BoltIcon className="h-4 w-4" />
                                {creditsRemaining} credits
                            </div>
                        )}
                        <Link
                            to="/launchpad"
                            className="px-5 py-2.5 bg-[#1A4D2E] text-white font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                        >
                            Go to App
                        </Link>
                    </div>
                </nav>
            </header>

            <main className="px-6 py-16">
                {/* Hero */}
                <div className="max-w-4xl mx-auto text-center mb-16">
                    <h1 className="font-serif text-4xl md:text-5xl font-bold text-[#2C2C2C] mb-4">
                        Find Your
                        <span className="text-[#1A4D2E]"> Perfect Fit</span>
                    </h1>
                    <p className="text-xl text-[#4A4A4A] mb-6">
                        Get AI-powered insights on how well you match with each university — academics, culture, and admission chances.
                    </p>
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#D6E8D5] text-[#1A4D2E] rounded-full text-sm font-medium border border-[#A8C5A6]">
                        <LightBulbIcon className="h-4 w-4" />
                        1 credit = 1 comprehensive fit analysis for any university
                    </div>
                </div>

                {/* Pricing Cards */}
                <section className="max-w-5xl mx-auto mb-20">
                    <div className="grid md:grid-cols-3 gap-6">
                        {plans.map((plan) => {
                            const Icon = plan.icon;
                            // Free plan is current only if user has NO active subscription
                            // Monthly/Annual are current if user has that subscription
                            const isSubscriptionPlan = plan.id === 'subscription_monthly' || plan.id === 'subscription_annual';
                            const isCurrentPlan =
                                (plan.id === 'free' && !isMonthly && !isSeasonal) ||
                                (plan.id === 'subscription_monthly' && isMonthly) ||
                                (plan.id === 'subscription_annual' && isSeasonal);

                            return (
                                <div
                                    key={plan.id}
                                    className={`relative bg-white rounded-3xl p-8 border-2 ${plan.borderColor} ${plan.popular ? 'shadow-xl shadow-[#D6E8D5]' : 'shadow-sm'
                                        } transition-all hover:shadow-lg`}
                                >
                                    {/* Popular Badge */}
                                    {plan.popular && (
                                        <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-[#1A4D2E] text-white text-sm font-bold rounded-full shadow-md">
                                            BEST VALUE
                                        </div>
                                    )}

                                    {/* Header */}
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className={`p-3 bg-gradient-to-br ${plan.gradient} rounded-xl shadow-lg`}>
                                            <Icon className="h-6 w-6 text-white" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-gray-900">{plan.name}</h3>
                                            <p className="text-gray-500 text-sm">{plan.description}</p>
                                        </div>
                                    </div>

                                    {/* Price */}
                                    <div className="flex items-baseline gap-1 mb-2">
                                        <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                                        <span className="text-gray-500">{plan.period}</span>
                                    </div>

                                    {/* Credits Badge */}
                                    <div className="mb-4">
                                        <span className="inline-flex items-center gap-1 px-3 py-1 bg-[#D6E8D5] text-[#1A4D2E] rounded-full text-sm font-semibold">
                                            <BoltIcon className="h-4 w-4" />
                                            {plan.credits} credits
                                        </span>
                                    </div>

                                    {/* Best For Badge */}
                                    {plan.bestFor && (
                                        <div className="mb-6 px-3 py-2 bg-gray-50 rounded-lg border border-gray-100">
                                            <p className="text-xs text-gray-500 uppercase tracking-wide font-medium mb-1">Best for</p>
                                            <p className="text-sm text-gray-700 font-medium">{plan.bestFor}</p>
                                        </div>
                                    )}

                                    {/* Features */}
                                    <ul className="space-y-3 mb-8">
                                        {plan.features.map((feature, idx) => (
                                            <li
                                                key={idx}
                                                className={`flex items-start gap-3 ${feature.included ? 'text-gray-700' : 'text-gray-400'
                                                    } ${feature.highlight ? 'font-medium text-[#1A4D2E]' : ''}`}
                                            >
                                                <CheckIcon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${feature.highlight ? 'text-[#1A4D2E]' : 'text-[#1A4D2E]'
                                                    }`} />
                                                <span>{feature.text}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {/* CTA Button Area */}
                                    <div className="space-y-4">
                                        {/* Renewal/Cancellation Message - only for SUBSCRIPTION plans */}
                                        {isCurrentPlan && isSubscriptionPlan && (isMonthly || isSeasonal) && (
                                            <div className="text-center">
                                                {isCanceling ? (
                                                    <p className="text-sm text-red-600 font-medium">Cancels on {cancellationDate}</p>
                                                ) : (
                                                    <p className="text-sm text-[#1A4D2E] font-medium flex items-center justify-center gap-1">
                                                        <SparklesIcon className="h-4 w-4" />
                                                        Renews automatically on {renewalDate}
                                                    </p>
                                                )}
                                            </div>
                                        )}

                                        {/* Main CTA Button */}
                                        <button
                                            onClick={() => {
                                                // Only allow reactivation for subscription plans
                                                if (isCurrentPlan && isSubscriptionPlan && isCanceling) {
                                                    handleReactivate();
                                                } else if (!isCurrentPlan) {
                                                    !plan.disabled && handleGetStarted(plan.id);
                                                }
                                            }}
                                            disabled={loading === plan.id || loading === 'reactivate' || (plan.disabled && !isCurrentPlan) || (isCurrentPlan && !(isSubscriptionPlan && isCanceling))}
                                            className={`w-full py-3 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${loading === plan.id || loading === 'reactivate' ? 'opacity-50 cursor-wait' :
                                                (isCurrentPlan && isSubscriptionPlan && isCanceling) ? 'bg-green-600 text-white hover:bg-green-700' :
                                                    (isCurrentPlan && !isCanceling) ? 'bg-[#D6E8D5] text-[#1A4D2E] border border-[#A8C5A6] cursor-default' :
                                                        plan.ctaStyle
                                                }`}
                                        >
                                            {loading === plan.id ? 'Processing...' :
                                                loading === 'reactivate' ? 'Reactivating...' :
                                                    (isCurrentPlan && isSubscriptionPlan && isCanceling) ? 'Reactivate Subscription' :
                                                        (isCurrentPlan && !isCanceling) ? (
                                                            <>
                                                                <CheckCircleIcon className="h-5 w-5" />
                                                                Active Plan
                                                            </>
                                                        ) :
                                                            plan.cta}
                                            {loading !== plan.id && loading !== 'reactivate' && !isCurrentPlan && !plan.disabled && <ArrowRightIcon className="h-4 w-4" />}
                                        </button>

                                        {/* De-emphasized Cancel Link - only for subscription plans */}
                                        {isCurrentPlan && isSubscriptionPlan && (isMonthly || isSeasonal) && !isCanceling && (
                                            <button
                                                onClick={handleCancelClick}
                                                className="w-full text-sm text-gray-400 hover:text-red-600 hover:underline transition-colors block text-center"
                                            >
                                                Cancel Subscription
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* How Credits Work */}
                <section className="max-w-4xl mx-auto mb-20">
                    <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">How Credits Work</h2>
                    <div className="grid md:grid-cols-3 gap-6">
                        <div className="bg-white rounded-2xl p-6 border border-gray-200 text-center">
                            <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <span className="text-2xl">1️⃣</span>
                            </div>
                            <h3 className="font-bold text-gray-900 mb-2">Add College to List</h3>
                            <p className="text-gray-600 text-sm">Save universities you're interested in to your Launchpad</p>
                        </div>
                        <div className="bg-white rounded-2xl p-6 border border-gray-200 text-center">
                            <div className="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <span className="text-2xl">2️⃣</span>
                            </div>
                            <h3 className="font-bold text-gray-900 mb-2">Run Fit Analysis</h3>
                            <p className="text-gray-600 text-sm">Uses 1 credit to compute personalized fit + generate infographic</p>
                        </div>
                        <div className="bg-white rounded-2xl p-6 border border-gray-200 text-center">
                            <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <span className="text-2xl">♻️</span>
                            </div>
                            <h3 className="font-bold text-gray-900 mb-2">Re-view for FREE</h3>
                            <p className="text-gray-600 text-sm">Cached results don't use credits — view your analysis anytime!</p>
                        </div>
                    </div>
                </section>

                {/* FAQ */}
                <section className="max-w-3xl mx-auto">
                    <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Common Questions</h2>
                    <div className="space-y-4">
                        {[
                            {
                                q: 'What is a credit?',
                                a: '1 credit = 1 personalized fit analysis for a university. This includes the fit category, match percentage, score breakdown, recommendations, and a custom infographic.'
                            },
                            {
                                q: 'Do credits expire?',
                                a: 'Credit packs never expire. Pro subscription credits are valid for the subscription year and refresh when you renew.'
                            },
                            {
                                q: 'When do I use a credit?',
                                a: 'Only when computing a NEW fit analysis. Re-viewing existing analyses, browsing universities, and using AI chat do NOT consume credits.'
                            },
                            {
                                q: 'What if I update my profile?',
                                a: 'Your existing fit analyses become "stale" but are still viewable. You can refresh them using credits if your academic info changed significantly.'
                            },
                        ].map((faq, idx) => (
                            <div key={idx} className="bg-white rounded-2xl p-6 border border-gray-200">
                                <h3 className="font-bold text-gray-900 mb-2">{faq.q}</h3>
                                <p className="text-gray-600">{faq.a}</p>
                            </div>
                        ))}
                    </div>
                </section>
            </main>

            {/* Footer */}
            <footer className="px-6 py-12 bg-white border-t border-[#E0DED8] mt-20">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <Link to="/launchpad" className="flex items-center">
                        <img
                            src="/logo.png"
                            alt="Stratia Admissions"
                            className="h-10 w-auto object-contain mix-blend-multiply"
                        />
                    </Link>
                    <div className="flex gap-6 text-sm text-[#4A4A4A]">
                        <Link to="/privacy" className="hover:text-[#1A4D2E]">Privacy Policy</Link>
                        <Link to="/terms" className="hover:text-[#1A4D2E]">Terms of Service</Link>
                        <Link to="/contact" className="hover:text-[#1A4D2E]">Contact</Link>
                    </div>
                    <p className="text-[#4A4A4A] text-sm">
                        © {new Date().getFullYear()} Stratia Admissions
                    </p>
                </div>
            </footer>

            {/* Cancel Subscription Modal */}
            <CancelSubscriptionModal
                isOpen={showCancelModal}
                onClose={() => setShowCancelModal(false)}
                onConfirm={handleCancelConfirm}
                subscriptionType={isMonthly ? 'subscription_monthly' : 'subscription_annual'}
                endDate={cancelEndDate || 'the end of your billing period'}
            />
        </div>
    );
};

export default PricingPage;
