import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeftIcon, ShieldCheckIcon } from '@heroicons/react/24/outline';

const PrivacyPolicy = () => {
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
                    Privacy Policy
                </h1>

                <div className="prose prose-lg prose-stone max-w-none">
                    <p className="text-gray-600 mb-8">
                        Effective Date: January 17, 2026
                    </p>

                    {/* Privacy Commitment Banner */}
                    <div className="bg-green-50 border-l-4 border-green-500 p-6 rounded-r-xl mb-10">
                        <div className="flex items-start gap-3">
                            <ShieldCheckIcon className="h-6 w-6 text-green-600 flex-shrink-0 mt-1" />
                            <div>
                                <h3 className="text-lg font-bold text-green-800 mb-2">Our Privacy Commitment</h3>
                                <p className="text-green-900">
                                    We do not sell your personal data. We do not use your data to train AI models. Your academic information is used solely to provide our services to you.
                                </p>
                            </div>
                        </div>
                    </div>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">1. Introduction</h2>
                        <p>
                            Stratia Admissions ("Company," "we," "our," or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our website and services (collectively, the "Service").
                        </p>
                        <p className="mt-4">
                            By using the Service, you consent to the data practices described in this Privacy Policy. If you do not agree with any part of this Privacy Policy, please do not use the Service.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">2. Information We Collect</h2>

                        <h3 className="text-xl font-semibold text-gray-800 mt-6 mb-3">2.1 Information You Provide</h3>
                        <p>We collect information you voluntarily provide when using our Service:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Account Information:</strong> Name, email address, and profile photo from your Google account when you sign in.</li>
                            <li><strong>Student Profile Data:</strong> Academic information you provide, including:
                                <ul className="list-circle pl-6 mt-2">
                                    <li>GPA (weighted and unweighted)</li>
                                    <li>Standardized test scores (SAT, ACT)</li>
                                    <li>High school name, grade level, and location</li>
                                    <li>Extracurricular activities and awards</li>
                                    <li>Intended majors and career interests</li>
                                    <li>College preferences (size, location, setting)</li>
                                </ul>
                            </li>
                            <li><strong>Essay Content:</strong> Any essays or writing samples you upload for analysis or assistance.</li>
                            <li><strong>Communications:</strong> Messages you send through our AI chat features or customer support.</li>
                            <li><strong>Payment Information:</strong> Payment is processed by Stripe; we do not store your credit card numbers. We receive transaction confirmation and subscription status from Stripe.</li>
                        </ul>

                        <h3 className="text-xl font-semibold text-gray-800 mt-6 mb-3">2.2 Information Collected Automatically</h3>
                        <p>When you use the Service, we automatically collect:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Device Information:</strong> Browser type, operating system, device type</li>
                            <li><strong>Log Data:</strong> IP address, access times, pages viewed, referring URL</li>
                            <li><strong>Usage Data:</strong> Features used, actions taken, time spent on pages</li>
                            <li><strong>Cookies:</strong> We use cookies and similar technologies for authentication and analytics (see Section 8)</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">3. How We Use Your Information</h2>
                        <p>We use the information we collect to:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Provide Our Services:</strong> Generate fit analyses, provide AI-powered recommendations, and deliver personalized content</li>
                            <li><strong>Manage Your Account:</strong> Authenticate your identity, maintain your profile, and process payments</li>
                            <li><strong>Improve Our Services:</strong> Analyze usage patterns to enhance features and user experience (in aggregate, not individual data)</li>
                            <li><strong>Communicate With You:</strong> Send service-related notifications, respond to inquiries, and provide customer support</li>
                            <li><strong>Ensure Security:</strong> Detect and prevent fraud, abuse, and unauthorized access</li>
                            <li><strong>Legal Compliance:</strong> Comply with applicable laws and legal obligations</li>
                        </ul>
                    </section>

                    <section className="mb-10 bg-blue-50 border border-blue-200 rounded-xl p-6">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">4. AI and Data Privacy</h2>
                        <p className="mb-4">
                            <strong>We prioritize your privacy when using AI technologies:</strong>
                        </p>
                        <ul className="list-disc pl-6 space-y-3">
                            <li>
                                <strong>No Training on Your Data:</strong> We do not use your personal data or content to train any AI or machine learning models. Your data is used only to provide services to you.
                            </li>
                            <li>
                                <strong>Privacy-Preserving AI:</strong> When sending data to AI providers (such as Google's Gemini API), we minimize the personal information transmitted and do not include unnecessary identifying information.
                            </li>
                            <li>
                                <strong>Third-Party AI Providers:</strong> We use Google Cloud AI services, which are governed by Google's enterprise data processing agreements. These services do not use customer data to train their models.
                            </li>
                            <li>
                                <strong>Data Retention by AI Providers:</strong> AI providers may temporarily process your queries but do not retain your data beyond the immediate processing needs, per our agreements.
                            </li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">5. Information Sharing and Disclosure</h2>
                        <p className="mb-4">
                            <strong>We do not sell your personal information.</strong> We may share your information only in the following circumstances:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Service Providers:</strong> With trusted third-party vendors who assist us in operating the Service:
                                <ul className="list-circle pl-6 mt-2">
                                    <li><strong>Google Cloud Platform:</strong> Cloud hosting and AI services</li>
                                    <li><strong>Firebase:</strong> Authentication and database services</li>
                                    <li><strong>Stripe:</strong> Payment processing</li>
                                </ul>
                            </li>
                            <li><strong>Legal Requirements:</strong> When required by law, court order, or governmental authority</li>
                            <li><strong>Safety and Rights:</strong> To protect our rights, safety, or property, or that of our users or others</li>
                            <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets (you will be notified)</li>
                            <li><strong>With Your Consent:</strong> When you explicitly authorize us to share specific information</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">6. Data Retention</h2>
                        <p>We retain your personal information for as long as necessary to:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>Provide you with the Service</li>
                            <li>Comply with legal obligations</li>
                            <li>Resolve disputes and enforce our agreements</li>
                        </ul>
                        <p className="mt-4">
                            <strong>Account Data:</strong> Retained while your account is active. You may request deletion at any time (see Section 9).
                        </p>
                        <p className="mt-2">
                            <strong>Payment Records:</strong> Retained for 7 years as required for accounting and tax purposes.
                        </p>
                        <p className="mt-2">
                            <strong>Chat History:</strong> Retained while your account is active; deleted upon account deletion.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">7. Data Security</h2>
                        <p>
                            We implement appropriate technical and organizational security measures to protect your personal information, including:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>Encryption of data in transit (TLS/HTTPS) and at rest</li>
                            <li>Secure authentication via Google OAuth 2.0</li>
                            <li>Access controls limiting employee access to personal data</li>
                            <li>Regular security assessments and monitoring</li>
                            <li>Use of enterprise-grade cloud infrastructure (Google Cloud)</li>
                        </ul>
                        <p className="mt-4">
                            However, no method of transmission over the Internet or electronic storage is 100% secure. We cannot guarantee absolute security.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">8. Cookies and Tracking Technologies</h2>
                        <p>We use cookies and similar technologies for:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Essential Cookies:</strong> Required for authentication and session management</li>
                            <li><strong>Analytics Cookies:</strong> To understand how users interact with our Service (Google Analytics)</li>
                            <li><strong>Preference Cookies:</strong> To remember your settings and preferences</li>
                        </ul>
                        <p className="mt-4">
                            You can control cookies through your browser settings. Disabling certain cookies may affect the functionality of the Service.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">9. Your Rights and Choices</h2>
                        <p>Depending on your location, you may have the following rights:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Access:</strong> Request a copy of the personal data we hold about you</li>
                            <li><strong>Correction:</strong> Request correction of inaccurate personal data</li>
                            <li><strong>Deletion:</strong> Request deletion of your personal data and account</li>
                            <li><strong>Portability:</strong> Request a copy of your data in a structured, machine-readable format</li>
                            <li><strong>Restriction:</strong> Request restriction of processing in certain circumstances</li>
                            <li><strong>Objection:</strong> Object to processing based on legitimate interests</li>
                            <li><strong>Withdraw Consent:</strong> Where processing is based on consent, you may withdraw it at any time</li>
                        </ul>
                        <p className="mt-4">
                            To exercise these rights, please contact us at <a href="mailto:support@stratiaadmissions.com" className="text-[#1A4D2E] font-medium underline">support@stratiaadmissions.com</a>. We will respond within 30 days.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">10. Children's Privacy</h2>
                        <p>
                            The Service is intended for users who are at least 13 years of age. We do not knowingly collect personal information from children under 13. If we learn that we have collected personal information from a child under 13, we will promptly delete it.
                        </p>
                        <p className="mt-4">
                            Users between 13 and 18 years of age should use the Service only with the involvement of a parent or guardian.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">11. California Privacy Rights (CCPA)</h2>
                        <p>
                            If you are a California resident, you have additional rights under the California Consumer Privacy Act (CCPA):
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Right to Know:</strong> You may request information about the categories and specific pieces of personal information we have collected</li>
                            <li><strong>Right to Delete:</strong> You may request deletion of your personal information</li>
                            <li><strong>Right to Opt-Out of Sale:</strong> We do not sell personal information</li>
                            <li><strong>Right to Non-Discrimination:</strong> We will not discriminate against you for exercising your rights</li>
                        </ul>
                        <p className="mt-4">
                            To exercise your CCPA rights, contact us at <a href="mailto:support@stratiaadmissions.com" className="text-[#1A4D2E] font-medium underline">support@stratiaadmissions.com</a>.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">12. International Data Transfers</h2>
                        <p>
                            Your information may be transferred to and processed in the United States, where our servers are located. If you are accessing the Service from outside the United States, please be aware that your information may be transferred to, stored, and processed in a jurisdiction with different data protection laws.
                        </p>
                        <p className="mt-4">
                            By using the Service, you consent to such transfers. We take appropriate safeguards to ensure your data is protected in accordance with this Privacy Policy.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">13. Changes to This Privacy Policy</h2>
                        <p>
                            We may update this Privacy Policy from time to time. If we make material changes, we will notify you by email or by posting a prominent notice on our website at least 30 days before the changes take effect. The "Effective Date" at the top of this policy indicates when it was last revised.
                        </p>
                        <p className="mt-4">
                            Your continued use of the Service after any changes constitutes your acceptance of the updated Privacy Policy.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">14. Contact Us</h2>
                        <p>
                            If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact us:
                        </p>
                        <div className="mt-4 bg-gray-50 p-4 rounded-lg">
                            <p><strong>Stratia Admissions</strong></p>
                            <p>Email: <a href="mailto:support@stratiaadmissions.com" className="text-[#1A4D2E] font-medium underline">support@stratiaadmissions.com</a></p>
                            <p>Website: <a href="https://stratiaadmissions.com" className="text-[#1A4D2E] font-medium underline">https://stratiaadmissions.com</a></p>
                        </div>
                        <p className="mt-4">
                            For EU residents, you also have the right to lodge a complaint with your local data protection authority.
                        </p>
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
                        <Link to="/terms" className="hover:text-[#1A4D2E]">Terms of Service</Link>
                        <Link to="/contact" className="hover:text-[#1A4D2E]">Contact</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default PrivacyPolicy;
