import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

const TermsOfService = () => {
    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            {/* Header */}
            <header className="px-6 py-5 bg-[#FDFCF7]/95 backdrop-blur-sm sticky top-0 z-50 border-b border-[#E0DED8]">
                <nav className="max-w-7xl mx-auto flex items-center justify-between">
                    <Link to="/" className="flex items-center">
                        <img
                            src="/logo.png"
                            alt="Stratia Admissions"
                            className="h-24 w-auto object-contain mix-blend-multiply"
                        />
                    </Link>
                    <Link
                        to="/"
                        className="flex items-center gap-2 text-[#4A4A4A] hover:text-[#1A4D2E] font-medium transition-colors"
                    >
                        <ArrowLeftIcon className="h-4 w-4" />
                        Back to Home
                    </Link>
                </nav>
            </header>

            <main className="max-w-4xl mx-auto px-6 py-16">
                <h1 className="font-serif text-4xl md:text-5xl font-bold text-[#2C2C2C] mb-8">
                    Terms of Service
                </h1>

                <div className="prose prose-lg prose-stone max-w-none">
                    <p className="text-gray-600 mb-8">
                        Last updated: {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                    </p>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">1. Acceptance of Terms</h2>
                        <p>
                            By accessing and using Stratia Admissions ("the Service"), you agree to comply with and be bound by these Terms of Service.
                            If you do not agree to these terms, you should not access or use the Service.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">2. Description of Service</h2>
                        <p>
                            Stratia Admissions provides AI-powered college counseling tools, including university matching, fit analysis, and profile building.
                            The Service is intended to assist students in their college application process but does not guarantee admission to any specific university.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">3. AI Disclaimer</h2>
                        <p>
                            <strong>Important:</strong> Our services generate content using Artificial Intelligence. While we strive for accuracy, AI-generated advice may occasionally be incorrect or incomplete.
                            You should always verify critical information (such as application deadlines and specific requirements) directly with the respective university's official sources.
                            We are not responsible for any decisions made based on AI-generated advice.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">4. User Accounts</h2>
                        <p>
                            To access certain features, you must register for an account. You agree to provide accurate, current, and complete information during the registration process
                            and to update such information to keep it accurate, current, and complete. You are responsible for safeguarding your password and for all activities that occur under your account.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">5. Subscriptions and Payments</h2>
                        <p>
                            Certain features of the Service are billed on a subscription or per-usage basis ("Paid Services").
                            You agree to pay all fees associated with your use of Paid Services. All payments are non-refundable except as expressly provided in our Refund Policy or required by law.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">6. Intellectual Property</h2>
                        <p>
                            The Service and its original content, features, and functionality are and will remain the exclusive property of Stratia Admissions and its licensors.
                            The Service is protected by copyright, trademark, and other laws.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">7. Limitation of Liability</h2>
                        <p>
                            In no event shall Stratia Admissions, nor its directors, employees, partners, agents, suppliers, or affiliates, be liable for any indirect, incidental, special, consequential, or punitive damages,
                            including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your access to or use of or inability to access or use the Service.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">8. Changes to Terms</h2>
                        <p>
                            We reserve the right, at our sole discretion, to modify or replace these Terms at any time. If a revision is material, we will try to provide at least 30 days' notice prior to any new terms taking effect.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">9. Contact Us</h2>
                        <p>
                            If you have any questions about these Terms, please contact us at <a href="mailto:cvsubs@gmail.com" className="text-[#1A4D2E] font-medium underline">cvsubs@gmail.com</a>.
                        </p>
                    </section>
                </div>
            </main>

            {/* Footer */}
            <footer className="px-6 py-12 bg-white border-t border-[#E0DED8]">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <span className="text-[#4A4A4A] text-sm">
                            © {new Date().getFullYear()} Stratia Admissions.
                        </span>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default TermsOfService;
