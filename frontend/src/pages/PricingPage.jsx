import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    SparklesIcon,
    CheckIcon,
    ChatBubbleLeftRightIcon,
    RocketLaunchIcon,
    ShieldCheckIcon,
    ArrowRightIcon,
    AcademicCapIcon,
    ChartBarIcon,
    PlusIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';

const PricingPage = () => {
    const navigate = useNavigate();
    const { currentUser } = useAuth();
    const { hasActiveSubscription } = usePayment();
    const [billingPeriod, setBillingPeriod] = useState('annual');

    const handleGetStarted = async () => {
        try {
            if (!currentUser) {
                await signInWithGoogle();
            }
            navigate('/profile');
        } catch (error) {
            console.error('Failed to sign in', error);
        }
    };

    const handleStartTrial = async () => {
        try {
            if (!currentUser) {
                await signInWithGoogle();
            }
            // TODO: Implement trial checkout with Stripe
            navigate('/profile');
        } catch (error) {
            console.error('Failed to start trial', error);
        }
    };

    // Add-on college slot packs
    const addonPacks = [
        { count: 1, price: 9, perCollege: 9.00 },
        { count: 3, price: 20, perCollege: 6.67, savings: 7 },
        { count: 5, price: 29, perCollege: 5.80, savings: 16 },
        { count: 10, price: 49, perCollege: 4.90, savings: 41 },
    ];

    return (
        <div className="min-h-screen bg-gradient-to-b from-amber-50 via-white to-orange-50">
            {/* Header */}
            <header className="px-6 py-5 bg-white/80 backdrop-blur-sm sticky top-0 z-50 border-b border-amber-100">
                <nav className="max-w-7xl mx-auto flex items-center justify-between">
                    <a href="/" className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg shadow-amber-200">
                            <SparklesIcon className="h-7 w-7 text-white" />
                        </div>
                        <span className="text-2xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
                            CollegeAI Pro
                        </span>
                    </a>
                    <div className="flex items-center gap-4">
                        <a href="/contact" className="text-gray-600 hover:text-amber-600 font-medium transition-colors">
                            Contact
                        </a>
                        <button
                            onClick={handleGetStarted}
                            className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-full hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200"
                        >
                            {currentUser ? 'Go to Dashboard' : 'Get Started Free'}
                        </button>
                    </div>
                </nav>
            </header>

            <main className="px-6 py-16">
                {/* Hero */}
                <div className="max-w-4xl mx-auto text-center mb-16">
                    <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                        Your Dream College
                        <span className="bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent"> Is Within Reach</span>
                    </h1>
                    <p className="text-xl text-gray-600 mb-6">
                        AI-powered guidance that helps you navigate college admissions with confidence
                    </p>
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-100 text-green-800 rounded-full text-sm font-medium border border-green-200">
                        <ShieldCheckIcon className="h-4 w-4" />
                        30-day free trial • Cancel anytime
                    </div>
                </div>

                {/* Billing Toggle */}
                <div className="flex justify-center mb-12">
                    <div className="inline-flex items-center p-1.5 bg-gray-100 rounded-full">
                        <button
                            onClick={() => setBillingPeriod('monthly')}
                            className={`px-6 py-2.5 rounded-full font-medium transition-all ${billingPeriod === 'monthly'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-600 hover:text-gray-900'
                                }`}
                        >
                            Monthly
                        </button>
                        <button
                            onClick={() => setBillingPeriod('annual')}
                            className={`px-6 py-2.5 rounded-full font-medium transition-all flex items-center gap-2 ${billingPeriod === 'annual'
                                ? 'bg-white text-gray-900 shadow-sm'
                                : 'text-gray-600 hover:text-gray-900'
                                }`}
                        >
                            Annual
                            <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full">
                                Save 45%
                            </span>
                        </button>
                    </div>
                </div>

                {/* Pricing Cards */}
                <section className="max-w-5xl mx-auto mb-20">
                    <div className="grid md:grid-cols-2 gap-8">
                        {/* Free Tier */}
                        <div className="bg-white rounded-3xl p-8 border border-gray-200 shadow-sm">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-3 bg-gray-100 rounded-xl">
                                    <AcademicCapIcon className="h-6 w-6 text-gray-600" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-gray-900">Free</h3>
                                    <p className="text-gray-500 text-sm">Get started exploring</p>
                                </div>
                            </div>

                            <div className="flex items-baseline gap-2 mb-6">
                                <span className="text-4xl font-bold text-gray-900">$0</span>
                                <span className="text-gray-500">/month</span>
                            </div>

                            <ul className="space-y-3 mb-8">
                                {[
                                    'Browse all 150+ universities',
                                    '30 AI messages per month',
                                    '3 fit analysis credits',
                                    'Basic profile builder',
                                    'Save to Launchpad'
                                ].map((feature, idx) => (
                                    <li key={idx} className="flex items-start gap-3 text-gray-600">
                                        <CheckIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                                        <span>{feature}</span>
                                    </li>
                                ))}
                            </ul>

                            <button
                                onClick={handleGetStarted}
                                className="w-full py-3 bg-gray-900 text-white rounded-xl font-semibold hover:bg-gray-800 transition-all"
                            >
                                {currentUser ? 'You\'re on Free' : 'Start Free'}
                            </button>
                        </div>

                        {/* Pro Tier */}
                        <div className="relative bg-white rounded-3xl p-8 border-2 border-amber-400 shadow-xl shadow-amber-100">
                            <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm font-bold rounded-full shadow-lg">
                                RECOMMENDED
                            </div>

                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-3 bg-gradient-to-br from-amber-100 to-orange-100 rounded-xl">
                                    <RocketLaunchIcon className="h-6 w-6 text-amber-600" />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-gray-900">Pro</h3>
                                    <p className="text-gray-500 text-sm">Full counseling experience</p>
                                </div>
                            </div>

                            <div className="flex items-baseline gap-2 mb-2">
                                {billingPeriod === 'annual' ? (
                                    <>
                                        <span className="text-4xl font-bold text-gray-900">$99</span>
                                        <span className="text-gray-500">/year</span>
                                        <span className="text-gray-400 line-through text-lg">$180</span>
                                    </>
                                ) : (
                                    <>
                                        <span className="text-4xl font-bold text-gray-900">$15</span>
                                        <span className="text-gray-500">/month</span>
                                    </>
                                )}
                            </div>
                            {billingPeriod === 'annual' && (
                                <p className="text-green-600 text-sm font-medium mb-4">
                                    Just $8.25/month, billed annually
                                </p>
                            )}

                            <ul className="space-y-3 mb-8">
                                {[
                                    'Everything in Free, plus:',
                                    '100 AI messages per month',
                                    '3 fit analysis credits included',
                                    'Personalized strategy recommendations',
                                    'Deadline tracking & reminders',
                                    'In-depth university insights'
                                ].map((feature, idx) => (
                                    <li key={idx} className={`flex items-start gap-3 ${idx === 0 ? 'text-amber-600 font-medium' : 'text-gray-600'}`}>
                                        <CheckIcon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${idx === 0 ? 'text-amber-500' : 'text-green-500'}`} />
                                        <span>{feature}</span>
                                    </li>
                                ))}
                            </ul>

                            <button
                                onClick={handleStartTrial}
                                className="w-full py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-semibold hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200 flex items-center justify-center gap-2"
                            >
                                Start 30-Day Free Trial
                                <ArrowRightIcon className="h-4 w-4" />
                            </button>
                            <p className="text-center text-gray-500 text-sm mt-3">
                                No charge for 30 days • Cancel anytime
                            </p>
                        </div>
                    </div>
                </section>

                {/* Add-on Packs */}
                <section className="max-w-4xl mx-auto mb-20">
                    <div className="text-center mb-10">
                        <h2 className="text-3xl font-bold text-gray-900 mb-4">Need More Fit Analyses?</h2>
                        <p className="text-lg text-gray-600">
                            Get detailed AI-powered fit analysis for additional colleges
                        </p>
                    </div>

                    <div className="bg-white rounded-3xl p-8 border border-gray-200 shadow-sm">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-3 bg-purple-100 rounded-xl">
                                <ChartBarIcon className="h-6 w-6 text-purple-600" />
                            </div>
                            <div>
                                <h3 className="text-xl font-bold text-gray-900">College Slot Packs</h3>
                                <p className="text-gray-500 text-sm">One-time purchase, never expires</p>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                            {addonPacks.map((pack, idx) => (
                                <div
                                    key={idx}
                                    className={`relative p-4 rounded-2xl border-2 text-center cursor-pointer transition-all hover:shadow-md ${pack.count === 5
                                        ? 'border-purple-400 bg-purple-50'
                                        : 'border-gray-200 hover:border-purple-200'
                                        }`}
                                >
                                    {pack.count === 5 && (
                                        <div className="absolute -top-2 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-purple-500 text-white text-xs font-bold rounded-full">
                                            BEST VALUE
                                        </div>
                                    )}
                                    <div className="flex items-center justify-center gap-1 mb-2">
                                        <PlusIcon className="h-4 w-4 text-purple-600" />
                                        <span className="text-2xl font-bold text-gray-900">{pack.count}</span>
                                    </div>
                                    <p className="text-gray-500 text-sm mb-2">
                                        {pack.count === 1 ? 'college' : 'colleges'}
                                    </p>
                                    <p className="text-xl font-bold text-gray-900">${pack.price}</p>
                                    <p className="text-gray-500 text-xs">
                                        ${pack.perCollege.toFixed(2)}/each
                                    </p>
                                    {pack.savings && (
                                        <p className="text-green-600 text-xs font-medium mt-1">
                                            Save ${pack.savings}
                                        </p>
                                    )}
                                </div>
                            ))}
                        </div>

                        <div className="bg-gray-50 rounded-xl p-4 text-center">
                            <p className="text-gray-600 text-sm">
                                <span className="font-medium">Each fit analysis includes:</span> Admission probability, gap analysis,
                                comparison to admitted students, and personalized action items
                            </p>
                        </div>
                    </div>
                </section>

                {/* Comparison Table */}
                <section className="max-w-4xl mx-auto mb-20">
                    <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Compare Plans</h2>

                    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                        <div className="grid grid-cols-3 bg-gray-50 border-b border-gray-200">
                            <div className="p-4 font-medium text-gray-700">Feature</div>
                            <div className="p-4 font-medium text-gray-700 text-center">Free</div>
                            <div className="p-4 font-medium text-amber-600 text-center bg-amber-50">Pro</div>
                        </div>
                        {[
                            { feature: 'Browse Universities', free: 'All 150+', pro: 'All 150+' },
                            { feature: 'AI Messages', free: '30/month', pro: '100/month' },
                            { feature: 'Fit Analysis Credits', free: '3 total', pro: '3 + add-ons' },
                            { feature: 'Strategy Recommendations', free: 'Basic', pro: 'Personalized' },
                            { feature: 'Deadline Tracking', free: '—', pro: '✓' },
                            { feature: 'University Insights', free: 'Basic', pro: 'In-depth' },
                        ].map((row, idx) => (
                            <div key={idx} className="grid grid-cols-3 border-b border-gray-100 last:border-b-0">
                                <div className="p-4 text-gray-600">{row.feature}</div>
                                <div className="p-4 text-center text-gray-600">{row.free}</div>
                                <div className="p-4 text-center text-gray-900 bg-amber-50/50 font-medium">{row.pro}</div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* FAQ */}
                <section className="max-w-3xl mx-auto">
                    <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Common Questions</h2>
                    <div className="space-y-4">
                        {[
                            {
                                q: 'How does the 30-day free trial work?',
                                a: 'You get full Pro access for 30 days. We\'ll ask for a credit card upfront, but you won\'t be charged until day 31. Cancel anytime before that — no questions asked.'
                            },
                            {
                                q: 'What happens when I run out of fit analyses?',
                                a: 'You can purchase additional college slot packs at any time. These never expire and give you deep AI analysis for more schools.'
                            },
                            {
                                q: 'Can I switch from monthly to annual?',
                                a: 'Absolutely! Upgrade to annual anytime and save 45%. Your remaining monthly balance is applied to the annual plan.'
                            },
                            {
                                q: 'Do AI messages roll over?',
                                a: 'AI message limits reset at the start of each billing period. We designed generous limits so you shouldn\'t run out, but you can always upgrade if needed.'
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
            <footer className="px-6 py-12 bg-white border-t border-gray-100 mt-20">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl">
                            <SparklesIcon className="h-6 w-6 text-white" />
                        </div>
                        <span className="text-xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
                            CollegeAI Pro
                        </span>
                    </div>
                    <div className="flex gap-6 text-sm text-gray-500">
                        <a href="/pricing" className="hover:text-amber-600">Pricing</a>
                        <a href="/contact" className="hover:text-amber-600">Contact</a>
                        <a href="mailto:cvsubs@gmail.com" className="hover:text-amber-600">Support</a>
                    </div>
                    <p className="text-gray-500 text-sm">
                        © {new Date().getFullYear()} CollegeAI Pro
                    </p>
                </div>
            </footer>
        </div>
    );
};

export default PricingPage;
