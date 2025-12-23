import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

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
                        Last updated: {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                    </p>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">1. Introduction</h2>
                        <p>
                            Stratia Admissions ("we," "our," or "us") respects your privacy and is committed to protecting your personal data.
                            This privacy policy will inform you as to how we look after your personal data when you visit our website
                            and use our AI-powered college counseling services.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">2. Data We Collect</h2>
                        <p>We may collect, use, store, and transfer different kinds of personal data about you which we have grouped together follows:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>Identity Data:</strong> includes first name, last name, username or similar identifier.</li>
                            <li><strong>Contact Data:</strong> includes email address and telephone number.</li>
                            <li><strong>Academic Data:</strong> includes transcripts, test scores (SAT/ACT), GPA, extracurricular activities, and essays uploaded for analysis.</li>
                            <li><strong>Technical Data:</strong> includes internet protocol (IP) address, your login data, browser type and version, and operating system.</li>
                            <li><strong>Usage Data:</strong> includes information about how you use our website and AI services.</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">3. How We Use Your Data</h2>
                        <p>We use your data primarily to provide and improve our services:</p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li>To provide AI-powered college fit analysis and recommendations.</li>
                            <li>To manage your account and subscription.</li>
                            <li>To communicate with you about your account or changes to our services.</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">4. AI Governance & Data Privacy</h2>
                        <p>
                            AI Governance and Privacy by Design is baked into our platform's architecture. We adhere to the highest standards of data privacy regarding Artificial Intelligence:
                        </p>
                        <ul className="list-disc pl-6 space-y-2 mt-4">
                            <li><strong>No Training on User Data:</strong> We do not use any user data to train any AI models. Your data remains yours and is never used to improve foundation models.</li>
                            <li><strong>Data Protection:</strong> We do not send users' personal data (PII) to any Large Language Models (LLMs). All analysis is performed using privacy-preserving protocols.</li>
                        </ul>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">5. Data Security</h2>
                        <p>
                            We have put in place appropriate security measures to prevent your personal data from being accidentally lost, used, or accessed in an unauthorized way.
                            We limit access to your personal data to those employees, agents, contractors, and other third parties who have a business need to know.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">6. Your Rights</h2>
                        <p>
                            Under certain circumstances, you have rights under data protection laws in relation to your personal data, including the right to request access, correction, erasure, restriction, transfer, or to object to processing.
                            To exercise any of these rights, please contact us at <a href="mailto:cvsubs@gmail.com" className="text-[#1A4D2E] font-medium underline">cvsubs@gmail.com</a>.
                        </p>
                    </section>

                    <section className="mb-10">
                        <h2 className="text-2xl font-bold text-[#1A4D2E] mb-4">7. Contact Us</h2>
                        <p>
                            If you have specific questions about this Privacy Policy, please contact us at:
                            <br />
                            <strong>Email:</strong> <a href="mailto:cvsubs@gmail.com" className="text-[#1A4D2E] font-medium underline">cvsubs@gmail.com</a>
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

export default PrivacyPolicy;
