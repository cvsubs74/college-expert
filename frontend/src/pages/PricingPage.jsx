import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    SparklesIcon,
    CheckIcon,
    XMarkIcon,
    RocketLaunchIcon,
    ArrowRightIcon,
    AcademicCapIcon,
    StarIcon,
    LightBulbIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';

const PricingPage = () => {
    const navigate = useNavigate();
    const { currentUser } = useAuth();
    const { currentTier, TIERS } = usePayment();

    const handleGetStarted = async (tier) => {
        try {
            if (!currentUser) {
                await signInWithGoogle();
            }
            if (tier === 'free') {
                navigate('/profile');
            } else {
                // TODO: Implement Stripe checkout for Pro/Elite
                navigate('/profile');
            }
        } catch (error) {
            console.error('Failed to sign in', error);
        }
    };

    const tiers = [
        {
            id: 'free',
            name: 'Free',
            price: '$0',
            period: 'forever',
            description: 'Explore universities and plan your journey',
            icon: AcademicCapIcon,
            gradient: 'from-gray-500 to-gray-600',
            borderColor: 'border-gray-200',
            bgColor: 'bg-white',
            popular: false,
            features: [
                { text: 'Browse all 150+ universities', included: true },
                { text: '10 AI chat messages/month', included: true },
                { text: 'View soft fit badges', included: true },
                { text: 'Basic profile builder', included: true },
                { text: 'Launchpad (college list)', included: false },
                { text: 'Personalized fit analysis', included: false },
                { text: 'Recommendations & strategy', included: false },
                { text: 'Deep research', included: false },
            ],
            cta: 'Start Free',
            ctaStyle: 'bg-gray-900 text-white hover:bg-gray-800'
        },
        {
            id: 'pro',
            name: 'Pro',
            price: '$99',
            period: '/year',
            description: 'Full access to Launchpad and fit analysis',
            icon: RocketLaunchIcon,
            gradient: 'from-amber-500 to-orange-500',
            borderColor: 'border-amber-400',
            bgColor: 'bg-white',
            popular: true,
            features: [
                { text: 'Everything in Free', included: true, highlight: true },
                { text: '30 AI chat messages/month', included: true },
                { text: 'Full Launchpad access', included: true },
                { text: 'Basic fit analysis with scores', included: true },
                { text: 'Fit category breakdown', included: true },
                { text: 'Recommendations & essay tips', included: false },
                { text: 'Scholarship matching', included: false },
                { text: 'Deep research', included: false },
            ],
            cta: 'Get Pro',
            ctaStyle: 'bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-400 hover:to-orange-400 shadow-lg shadow-amber-200'
        },
        {
            id: 'elite',
            name: 'Elite',
            price: '$199',
            period: '/year',
            description: 'Complete guidance with deep insights',
            icon: StarIcon,
            gradient: 'from-purple-500 to-indigo-600',
            borderColor: 'border-purple-400',
            bgColor: 'bg-white',
            popular: false,
            features: [
                { text: 'Everything in Pro', included: true, highlight: true },
                { text: '50 AI chat messages/month', included: true },
                { text: 'Full fit analysis with recommendations', included: true },
                { text: 'Personalized essay angles', included: true },
                { text: 'Scholarship matching', included: true },
                { text: 'Application timeline strategies', included: true },
                { text: 'Deep university research', included: true },
                { text: 'Priority support', included: true },
            ],
            cta: 'Get Elite',
            ctaStyle: 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white hover:from-purple-400 hover:to-indigo-500 shadow-lg shadow-purple-200'
        }
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
                        <button
                            onClick={() => handleGetStarted('free')}
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
                        Simple, Transparent
                        <span className="bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent"> Pricing</span>
                    </h1>
                    <p className="text-xl text-gray-600 mb-6">
                        Choose the plan that fits your college admissions journey
                    </p>
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-800 rounded-full text-sm font-medium border border-amber-200">
                        <LightBulbIcon className="h-4 w-4" />
                        All plans are annual — one simple payment
                    </div>
                </div>

                {/* Pricing Cards */}
                <section className="max-w-6xl mx-auto mb-20">
                    <div className="grid md:grid-cols-3 gap-6">
                        {tiers.map((tier) => {
                            const Icon = tier.icon;
                            const isCurrentTier = currentTier === tier.id;

                            return (
                                <div
                                    key={tier.id}
                                    className={`relative ${tier.bgColor} rounded-3xl p-8 border-2 ${tier.borderColor} ${tier.popular ? 'shadow-xl shadow-amber-100' : 'shadow-sm'
                                        } transition-all hover:shadow-lg`}
                                >
                                    {/* Popular Badge */}
                                    {tier.popular && (
                                        <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm font-bold rounded-full shadow-lg">
                                            BEST VALUE
                                        </div>
                                    )}

                                    {/* Header */}
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className={`p-3 bg-gradient-to-br ${tier.gradient} rounded-xl shadow-lg`}>
                                            <Icon className="h-6 w-6 text-white" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-bold text-gray-900">{tier.name}</h3>
                                            <p className="text-gray-500 text-sm">{tier.description}</p>
                                        </div>
                                    </div>

                                    {/* Price */}
                                    <div className="flex items-baseline gap-1 mb-6">
                                        <span className="text-4xl font-bold text-gray-900">{tier.price}</span>
                                        <span className="text-gray-500">{tier.period}</span>
                                    </div>

                                    {/* Features */}
                                    <ul className="space-y-3 mb-8">
                                        {tier.features.map((feature, idx) => (
                                            <li
                                                key={idx}
                                                className={`flex items-start gap-3 ${feature.included ? 'text-gray-700' : 'text-gray-400'
                                                    } ${feature.highlight ? 'font-medium text-amber-600' : ''}`}
                                            >
                                                {feature.included ? (
                                                    <CheckIcon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${feature.highlight ? 'text-amber-500' : 'text-green-500'
                                                        }`} />
                                                ) : (
                                                    <XMarkIcon className="h-5 w-5 flex-shrink-0 mt-0.5 text-gray-300" />
                                                )}
                                                <span>{feature.text}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    {/* CTA Button */}
                                    <button
                                        onClick={() => handleGetStarted(tier.id)}
                                        disabled={isCurrentTier}
                                        className={`w-full py-3 rounded-xl font-semibold transition-all flex items-center justify-center gap-2 ${isCurrentTier
                                            ? 'bg-gray-100 text-gray-500 cursor-default'
                                            : tier.ctaStyle
                                            }`}
                                    >
                                        {isCurrentTier ? 'Current Plan' : tier.cta}
                                        {!isCurrentTier && <ArrowRightIcon className="h-4 w-4" />}
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* Comparison Table */}
                <section className="max-w-5xl mx-auto mb-20">
                    <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Compare Plans</h2>

                    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="bg-gray-50 border-b border-gray-200">
                                    <th className="p-4 text-left font-medium text-gray-700 w-1/3">Feature</th>
                                    <th className="p-4 text-center font-medium text-gray-700">Free</th>
                                    <th className="p-4 text-center font-medium text-amber-600 bg-amber-50">Pro $99</th>
                                    <th className="p-4 text-center font-medium text-purple-600 bg-purple-50">Elite $199</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[
                                    { feature: 'Browse Universities', free: '✓ All 150+', pro: '✓ All 150+', elite: '✓ All 150+' },
                                    { feature: 'AI Chat Messages', free: '10/month', pro: '30/month', elite: '50/month' },
                                    { feature: 'Launchpad Access', free: '—', pro: '✓ Full', elite: '✓ Full' },
                                    { feature: 'Fit Analysis', free: '—', pro: '✓ Basic', elite: '✓ Full + Recs' },
                                    { feature: 'Essay Angles & Tips', free: '—', pro: '—', elite: '✓' },
                                    { feature: 'Scholarship Matching', free: '—', pro: '—', elite: '✓' },
                                    { feature: 'Application Timeline', free: '—', pro: '—', elite: '✓' },
                                    { feature: 'Deep Research', free: '—', pro: '—', elite: '✓' },
                                ].map((row, idx) => (
                                    <tr key={idx} className="border-b border-gray-100 last:border-b-0">
                                        <td className="p-4 text-gray-700 font-medium">{row.feature}</td>
                                        <td className="p-4 text-center text-gray-600">{row.free}</td>
                                        <td className="p-4 text-center text-gray-900 bg-amber-50/50">{row.pro}</td>
                                        <td className="p-4 text-center text-gray-900 bg-purple-50/50 font-medium">{row.elite}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </section>

                {/* FAQ */}
                <section className="max-w-3xl mx-auto">
                    <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Common Questions</h2>
                    <div className="space-y-4">
                        {[
                            {
                                q: 'Why annual-only pricing?',
                                a: 'College admissions is a journey that takes months. Annual pricing lets us keep costs low while giving you time to explore, apply, and succeed without worrying about monthly fees.'
                            },
                            {
                                q: 'What\'s the difference between Basic and Full fit analysis?',
                                a: 'Basic (Pro) shows your fit category, match percentage, and key factors. Full (Elite) adds personalized recommendations, essay angles, scholarship matches, timeline strategies, and detailed gap analysis.'
                            },
                            {
                                q: 'Can I upgrade from Pro to Elite?',
                                a: 'Absolutely! You can upgrade anytime. Just pay the difference between plans, prorated for the remaining time in your subscription.'
                            },
                            {
                                q: 'What is Deep Research?',
                                a: 'Elite members get AI-powered deep research that analyzes university-specific insights, recent news, faculty opportunities, and strategic angles beyond standard admissions data.'
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
