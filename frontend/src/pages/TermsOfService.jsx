import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeftIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

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
                        Effective Date: January 17, 2026
                    </p>

                    {/* Important Disclaimer Banner */}
                    <div className="bg-amber-50 border-l-4 border-amber-500 p-6 rounded-r-xl mb-10">
                        <div className="flex items-start gap-3">
                            <ExclamationTriangleIcon className="h-6 w-6 text-amber-600 flex-shrink-0 mt-1" />
                            <div>
                                <h3 className="text-lg font-bold text-amber-800 mb-2">Important Disclaimer</h3>
                                <p className="text-amber-900">
                                    <strong>Stratia Admissions does not guarantee admission to any college or university.</strong> Our AI-powered tools provide informational guidance only and should not be relied upon as the sole basis for application decisions. College admissions are determined exclusively by the respective institutions.
                                </p>
                            </div>
                        </div>
                    </div>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">1. Acceptance of Terms</h2>
                        <p>
                            By accessing or using the Stratia Admissions website and services (collectively, the "Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to all of these Terms, you may not access or use the Service.
                        </p>
                        <p className="mt-4">
                            These Terms constitute a legally binding agreement between you and Stratia Admissions ("Company," "we," "us," or "our"). We may update these Terms from time to time, and the updated version will be effective upon posting. Your continued use of the Service after any changes constitutes acceptance of the new Terms.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">2. Description of Service</h2>
                        <p>
                            Stratia Admissions provides AI-powered college counseling tools, including but not limited to:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>University "fit analysis" comparing your academic profile to university admission data</li>
                            <li>AI-generated recommendations and essay assistance</li>
                            <li>University profile exploration and comparison tools</li>
                            <li>Student profile building and management</li>
                        </ul>
                        <p className="mt-4">
                            <strong>The Service is intended for informational purposes only.</strong> We do not provide professional college counseling, legal advice, or financial aid consultation. Users should consult qualified professionals for such services.
                        </p>
                    </section>

                    <section className="mb-10 bg-red-50 border border-red-200 rounded-xl p-6">
                        <h2 className="text-2xl font-bold text-red-800 mb-4">3. No Guarantee of College Admission</h2>
                        <p className="text-red-900">
                            <strong>STRATIA ADMISSIONS MAKES NO REPRESENTATIONS, WARRANTIES, OR GUARANTEES REGARDING COLLEGE ADMISSION OUTCOMES.</strong>
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4 text-red-900">
                            <li>Our "fit analysis" scores, match percentages, and recommendations are <strong>estimates based on publicly available data</strong> and proprietary algorithms. They do not predict or guarantee admission.</li>
                            <li>Admission decisions are made solely by the respective colleges and universities and are influenced by many factors beyond academic metrics.</li>
                            <li>AI-generated content, including essay suggestions and recommendations, may contain errors or inaccuracies. Users are responsible for verifying all information with official university sources.</li>
                            <li>Past results or fit scores do not guarantee future admission outcomes. Each application cycle and applicant is unique.</li>
                        </ul>
                        <p className="mt-4 text-red-900">
                            <strong>By using our Service, you acknowledge and accept that college admission is inherently uncertain and that we bear no responsibility for admission outcomes.</strong>
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">4. AI Disclaimer</h2>
                        <p>
                            Our Service utilizes artificial intelligence and machine learning technologies. You acknowledge and agree that:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>AI Limitations:</strong> AI-generated content may be inaccurate, incomplete, outdated, or inappropriate. You should not rely solely on AI-generated advice.</li>
                            <li><strong>Verification Required:</strong> You are responsible for independently verifying all information, including application deadlines, requirements, and university policies, with official sources.</li>
                            <li><strong>No Human Oversight:</strong> AI responses are generated automatically without real-time human review. We do not endorse or guarantee the accuracy of AI-generated content.</li>
                            <li><strong>Not Professional Advice:</strong> AI-generated content does not constitute professional college counseling, legal, financial, or other professional advice.</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">5. User Accounts and Eligibility</h2>
                        <p>
                            To access certain features, you must create an account using Google Authentication. By creating an account, you represent that:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>You are at least 13 years of age. Users under 18 should have parental or guardian consent.</li>
                            <li>All information you provide is accurate, current, and complete.</li>
                            <li>You will maintain the security of your account credentials.</li>
                            <li>You will not share your account with others or create multiple accounts.</li>
                            <li>You are responsible for all activity under your account.</li>
                        </ul>
                        <p className="mt-4">
                            We reserve the right to suspend or terminate accounts that violate these Terms or for any other reason at our sole discretion.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">6. Subscription Plans and Pricing</h2>
                        <p>We offer the following subscription plans:</p>

                        <div className="mt-4 space-y-4">
                            <div className="bg-gray-50 p-4 rounded-lg">
                                <h4 className="font-bold text-gray-900">Free Tier</h4>
                                <ul className="list-disc pl-6 mt-2 text-gray-700">
                                    <li>3 fit analysis credits (lifetime)</li>
                                    <li>Limited AI chat access</li>
                                    <li>Access to university profiles</li>
                                </ul>
                            </div>

                            <div className="bg-gray-50 p-4 rounded-lg">
                                <h4 className="font-bold text-gray-900">Monthly Subscription — $15/month</h4>
                                <ul className="list-disc pl-6 mt-2 text-gray-700">
                                    <li>20 fit analysis credits per month</li>
                                    <li>Unlimited AI chat access</li>
                                    <li>Billed monthly, auto-renews until canceled</li>
                                </ul>
                            </div>

                            <div className="bg-gray-50 p-4 rounded-lg">
                                <h4 className="font-bold text-gray-900">Season Pass (Annual) — $99/year</h4>
                                <ul className="list-disc pl-6 mt-2 text-gray-700">
                                    <li>150 fit analysis credits for the year</li>
                                    <li>Unlimited AI chat access</li>
                                    <li>Billed annually, auto-renews until canceled</li>
                                </ul>
                            </div>

                            <div className="bg-gray-50 p-4 rounded-lg">
                                <h4 className="font-bold text-gray-900">Credit Packs — $9 for 10 credits</h4>
                                <ul className="list-disc pl-6 mt-2 text-gray-700">
                                    <li>Available only to active Monthly or Season Pass subscribers</li>
                                    <li>One-time purchase, credits never expire</li>
                                </ul>
                            </div>
                        </div>

                        <p className="mt-4">
                            Prices are in US Dollars and are subject to change with notice. All payments are processed securely through Stripe.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">7. Billing, Renewal, and Cancellation</h2>

                        <h3 className="text-xl font-semibold text-gray-800 mt-6 mb-3">Automatic Renewal</h3>
                        <p>
                            <strong>Both Monthly and Season Pass (Annual) subscriptions automatically renew</strong> at the end of each billing period unless you cancel before the renewal date. The renewal charge will be the same as your current subscription rate unless we notify you of a price change in advance.
                        </p>

                        <h3 className="text-xl font-semibold text-gray-800 mt-6 mb-3">How to Cancel</h3>
                        <p>
                            You may cancel your subscription at any time through the Pricing page in your account. Upon cancellation:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>Your subscription will remain active until the end of your current billing period.</li>
                            <li>You will retain access to subscriber features (including unused credits) until the period ends.</li>
                            <li>Your subscription will not renew, and no further charges will be made.</li>
                            <li>After the period ends, your account will revert to the Free tier.</li>
                        </ul>

                        <h3 className="text-xl font-semibold text-gray-800 mt-6 mb-3">Refund Policy</h3>
                        <p>
                            <strong>All subscription fees and credit purchases are non-refundable</strong> except as required by applicable law. We do not provide prorated refunds for cancellations made before the end of a billing period. If you believe you were charged in error, please contact us within 7 days of the charge.
                        </p>

                        <h3 className="text-xl font-semibold text-gray-800 mt-6 mb-3">Failed Payments</h3>
                        <p>
                            If a payment fails, we may attempt to charge your payment method again. If the payment continues to fail, your subscription may be suspended or canceled. We are not responsible for any loss of access due to failed payments.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">8. User Content and Data</h2>
                        <p>
                            You retain ownership of all content you submit to the Service, including your student profile, essays, and academic information ("User Content"). By submitting User Content, you grant us a limited, non-exclusive license to use, store, and process your content solely to provide the Service.
                        </p>
                        <p className="mt-4">
                            You are solely responsible for the accuracy and legality of your User Content. You agree not to submit content that is false, misleading, defamatory, or that infringes on any third party's rights.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">9. Prohibited Uses</h2>
                        <p>You agree not to:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>Use the Service for any unlawful purpose or in violation of these Terms</li>
                            <li>Attempt to gain unauthorized access to the Service or its systems</li>
                            <li>Use automated scripts, bots, or scrapers to access the Service</li>
                            <li>Interfere with or disrupt the Service or servers</li>
                            <li>Impersonate any person or entity</li>
                            <li>Share, resell, or redistribute access to your account</li>
                            <li>Use the Service to submit false or fraudulent college applications</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">10. Intellectual Property</h2>
                        <p>
                            The Service, including its design, text, graphics, logos, and software, is the property of Stratia Admissions and is protected by copyright, trademark, and other intellectual property laws. You may not copy, modify, distribute, or create derivative works of any part of the Service without our prior written consent.
                        </p>
                    </section>

                    <section className="mb-10 bg-gray-100 rounded-xl p-6">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">11. Disclaimer of Warranties</h2>
                        <p className="uppercase text-sm font-semibold text-gray-700">
                            THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                        </p>
                        <p className="mt-4">
                            We do not warrant that the Service will be uninterrupted, error-free, secure, or free of viruses or other harmful components. We do not warrant the accuracy, completeness, or usefulness of any information provided through the Service.
                        </p>
                    </section>

                    <section className="mb-10 bg-gray-100 rounded-xl p-6">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">12. Limitation of Liability</h2>
                        <p className="uppercase text-sm font-semibold text-gray-700">
                            TO THE MAXIMUM EXTENT PERMITTED BY LAW, IN NO EVENT SHALL STRATIA ADMISSIONS, ITS OFFICERS, DIRECTORS, EMPLOYEES, AGENTS, OR AFFILIATES BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING WITHOUT LIMITATION:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4 text-gray-700">
                            <li>Loss of profits, revenue, or data</li>
                            <li>Loss of opportunity, including college admission opportunities</li>
                            <li>Damages arising from reliance on AI-generated content</li>
                            <li>Damages arising from service interruptions or errors</li>
                        </ul>
                        <p className="mt-4 text-gray-700">
                            OUR TOTAL LIABILITY TO YOU FOR ANY CLAIMS ARISING FROM YOUR USE OF THE SERVICE SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM, OR $100, WHICHEVER IS GREATER.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">13. Indemnification</h2>
                        <p>
                            You agree to indemnify, defend, and hold harmless Stratia Admissions and its officers, directors, employees, and agents from and against any claims, liabilities, damages, losses, and expenses (including reasonable attorneys' fees) arising out of or in any way connected with your use of the Service, your violation of these Terms, or your violation of any rights of another.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">14. Governing Law and Dispute Resolution</h2>
                        <p>
                            These Terms shall be governed by and construed in accordance with the laws of the State of California, United States, without regard to its conflict of law provisions. Any disputes arising from these Terms or your use of the Service shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association, except that either party may seek injunctive relief in any court of competent jurisdiction.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">15. Modifications to Terms</h2>
                        <p>
                            We reserve the right to modify these Terms at any time. If we make material changes, we will notify you by email or by posting a notice on our website at least 30 days before the changes take effect. Your continued use of the Service after the effective date of any changes constitutes your acceptance of the modified Terms.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">16. Severability</h2>
                        <p>
                            If any provision of these Terms is held to be invalid or unenforceable, that provision shall be limited or eliminated to the minimum extent necessary, and the remaining provisions shall remain in full force and effect.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">17. Contact Information</h2>
                        <p>
                            If you have any questions about these Terms, please contact us at:
                        </p>
                        <div className="mt-4 bg-gray-50 p-4 rounded-lg">
                            <p><strong>Stratia Admissions</strong></p>
                            <p>Email: <a href="mailto:support@stratiaadmissions.com" className="text-[#1A4D2E] font-medium underline">support@stratiaadmissions.com</a></p>
                            <p>Website: <a href="https://stratiaadmissions.com" className="text-[#1A4D2E] font-medium underline">https://stratiaadmissions.com</a></p>
                        </div>
                    </section>
                </div>
            </main>

            {/* Footer */}
            <footer className="px-6 py-12 bg-white border-t border-[#E0DED8]">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <span className="text-[#4A4A4A] text-sm">
                            © {new Date().getFullYear()} Stratia Admissions. All rights reserved.
                        </span>
                    </div>
                    <div className="flex gap-6 text-sm text-[#4A4A4A]">
                        <Link to="/privacy" className="hover:text-[#1A4D2E]">Privacy Policy</Link>
                        <Link to="/contact" className="hover:text-[#1A4D2E]">Contact</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default TermsOfService;
