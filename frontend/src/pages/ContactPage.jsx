import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
    SparklesIcon,
    EnvelopeIcon,
    ChatBubbleLeftRightIcon,
    QuestionMarkCircleIcon,
    ArrowRightIcon
} from '@heroicons/react/24/outline';

const ContactPage = () => {
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        subject: 'General Inquiry',
        message: ''
    });
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitStatus, setSubmitStatus] = useState(null); // 'success' | 'error' | null

    const CONTACT_API_URL = import.meta.env.VITE_CONTACT_API_URL || 'https://contact-form-pfnwjfp26a-ue.a.run.app';

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        setSubmitStatus(null);

        try {
            const response = await fetch(CONTACT_API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            });

            const result = await response.json();

            if (response.ok && result.success) {
                setSubmitStatus('success');
                setFormData({ name: '', email: '', subject: 'General Inquiry', message: '' });
            } else {
                setSubmitStatus('error');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            setSubmitStatus('error');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleChange = (e) => {
        setFormData(prev => ({
            ...prev,
            [e.target.name]: e.target.value
        }));
        // Clear status when user starts typing again
        if (submitStatus) setSubmitStatus(null);
    };

    const quickLinks = [
        {
            icon: QuestionMarkCircleIcon,
            title: 'FAQs',
            desc: 'Find answers to common questions',
            link: '/pricing#faq'
        },
        {
            icon: ChatBubbleLeftRightIcon,
            title: 'AI Counselor',
            desc: 'Get instant help from our AI',
            link: '/chat'
        },
    ];

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            {/* Header */}
            <header className="px-6 py-5 bg-white/80 backdrop-blur-sm sticky top-0 z-50 border-b border-[#E0DED8]">
                <nav className="max-w-7xl mx-auto flex items-center justify-between">
                    <Link to="/" className="flex items-center">
                        <img
                            src="/logo.png"
                            alt="Stratia Admissions"
                            className="h-24 w-auto object-contain mix-blend-multiply"
                        />
                    </Link>
                    <div className="flex items-center gap-4">
                        <Link to="/pricing" className="text-gray-600 hover:text-[#1A4D2E] font-medium transition-colors">
                            Pricing
                        </Link>
                        <Link
                            to="/"
                            className="px-5 py-2.5 bg-[#1A4D2E] text-white font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                        >
                            Get Started
                        </Link>
                    </div>
                </nav>
            </header>

            <main className="px-6 py-16">
                <div className="max-w-5xl mx-auto">
                    {/* Hero */}
                    <div className="text-center mb-16">
                        <h1 className="font-serif text-4xl md:text-5xl font-bold text-[#2C2C2C] mb-4">
                            We'd Love to Hear From You
                        </h1>
                        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                            Your feedback shapes our product. Share feature requests, report issues,
                            or just tell us what you think—every message helps us build a better Stratia.
                        </p>
                    </div>

                    <div className="max-w-2xl mx-auto mb-20">
                        {/* Contact Form */}
                        <div>
                            <div className="bg-white rounded-3xl p-8 shadow-xl border border-gray-200">
                                <h2 className="text-2xl font-bold text-gray-900 mb-2">Send Us a Message</h2>
                                <p className="text-gray-600 mb-6">Feature requests • Feedback • Bug reports • Questions</p>

                                <form onSubmit={handleSubmit} className="space-y-6">
                                    <div className="grid md:grid-cols-2 gap-6">
                                        <div>
                                            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                                                Your Name
                                            </label>
                                            <input
                                                type="text"
                                                id="name"
                                                name="name"
                                                value={formData.name}
                                                onChange={handleChange}
                                                required
                                                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1A4D2E] focus:border-[#1A4D2E] transition-all"
                                                placeholder="John Doe"
                                            />
                                        </div>
                                        <div>
                                            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                                                Email Address
                                            </label>
                                            <input
                                                type="email"
                                                id="email"
                                                name="email"
                                                value={formData.email}
                                                onChange={handleChange}
                                                required
                                                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1A4D2E] focus:border-[#1A4D2E] transition-all"
                                                placeholder="john@example.com"
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-2">
                                            Subject
                                        </label>
                                        <select
                                            id="subject"
                                            name="subject"
                                            value={formData.subject}
                                            onChange={handleChange}
                                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1A4D2E] focus:border-[#1A4D2E] transition-all"
                                        >
                                            <option>General Inquiry</option>
                                            <option>Pricing Question</option>
                                            <option>Technical Support</option>
                                            <option>Partnership Opportunity</option>
                                            <option>Other</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-2">
                                            Message
                                        </label>
                                        <textarea
                                            id="message"
                                            name="message"
                                            value={formData.message}
                                            onChange={handleChange}
                                            required
                                            rows={5}
                                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#1A4D2E] focus:border-[#1A4D2E] transition-all resize-none"
                                            placeholder="How can we help you?"
                                        />
                                    </div>

                                    <button
                                        type="submit"
                                        disabled={isSubmitting}
                                        className={`w-full py-4 text-white text-lg font-bold rounded-xl transition-all shadow-lg flex items-center justify-center gap-2 ${isSubmitting
                                            ? 'bg-gray-400 cursor-not-allowed'
                                            : 'bg-[#1A4D2E] hover:bg-[#2D6B45]'
                                            }`}
                                    >
                                        {isSubmitting ? (
                                            <>
                                                <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                                </svg>
                                                Sending...
                                            </>
                                        ) : (
                                            <>
                                                <EnvelopeIcon className="h-5 w-5" />
                                                Send Message
                                                <ArrowRightIcon className="h-5 w-5" />
                                            </>
                                        )}
                                    </button>
                                </form>

                                {/* Status Messages */}
                                {submitStatus === 'success' && (
                                    <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-xl text-green-700 text-center">
                                        ✓ Message sent successfully! We'll get back to you soon.
                                    </div>
                                )}
                                {submitStatus === 'error' && (
                                    <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-center">
                                        Failed to send message. Please try again or email us directly.
                                    </div>
                                )}
                            </div>

                            <p className="text-center text-gray-500 text-sm mt-6">
                                We typically respond within 24 hours.
                            </p>
                        </div>
                    </div>

                    {/* Extended FAQs */}
                    <div className="max-w-3xl mx-auto">
                        <div className="text-center mb-10">
                            <h2 className="font-serif text-3xl font-bold text-[#2C2C2C] mb-4">
                                Frequently Asked Questions
                            </h2>
                            <p className="text-gray-600">Common questions about Stratia Admissions</p>
                        </div>

                        <div className="space-y-4">
                            {[
                                {
                                    q: 'Is Stratia Admissions free?',
                                    a: 'Yes! We offer a Free Tier that enables you to build your profile, search universities, and chat with our AI counselor. For deeper insights and unlimited fit analysis credits, we offer Monthly and Season Pass upgrade options.'
                                },
                                {
                                    q: 'How does the AI Fit Analysis work?',
                                    a: 'Our AI analyzes over 50 data points from your academic profile (GPA, test scores, activities) and compares them against real admission trends and institutional priorities. It then generates a "Fit Score" across Academic, Culture, and Financial dimensions.'
                                },
                                {
                                    q: 'Is my data secure?',
                                    a: 'Absolutely. We use enterprise-grade encryption for all data. Furthermore, we NEVER use your personal data to train public AI models, and we do not share your PII with third-party LLMs.'
                                },
                                {
                                    q: 'Can I cancel my subscription?',
                                    a: 'Yes, you can cancel your Monthly subscription at any time from your dashboard. Your credits will remain valid until the end of the billing period.'
                                },
                                {
                                    q: 'Do you offer human counseling?',
                                    a: 'Stratia is an AI-first platform designed to provide 24/7 accessible guidance at a fraction of the cost of private counselors. While we do not offer human counseling, our AI is trained on expert admission strategies.'
                                },
                                {
                                    q: 'What if I need technical support?',
                                    a: 'If you encounter any issues, please email us directly at support@stratiaadmissions.com or use the form above. We prioritize technical support requests.'
                                }
                            ].map((faq, idx) => (
                                <div key={idx} className="bg-white rounded-2xl p-6 border border-gray-200 hover:border-[#A8C5A6] transition-colors">
                                    <h3 className="font-bold text-gray-900 mb-2">{faq.q}</h3>
                                    <p className="text-gray-600 leading-relaxed">{faq.a}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="px-6 py-12 bg-white border-t border-gray-100 mt-20">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <Link to="/" className="flex items-center">
                            <img
                                src="/logo.png"
                                alt="Stratia Admissions"
                                className="h-10 w-auto object-contain mix-blend-multiply"
                            />
                        </Link>
                        <span className="text-[#4A4A4A] text-sm">
                            © {new Date().getFullYear()} Stratia Admissions
                        </span>
                    </div>
                    <div className="flex gap-6 text-sm text-gray-500">
                        <Link to="/privacy" className="hover:text-[#1A4D2E]">Privacy Policy</Link>
                        <Link to="/terms" className="hover:text-[#1A4D2E]">Terms of Service</Link>
                        <Link to="/contact" className="hover:text-[#1A4D2E]">Contact</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
};

export default ContactPage;
