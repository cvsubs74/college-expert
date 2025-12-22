import React, { useState } from 'react';
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

    const handleSubmit = (e) => {
        e.preventDefault();

        // Create mailto link with form data
        const mailtoLink = `mailto:cvsubs@gmail.com?subject=${encodeURIComponent(
            `CollegeAI Pro: ${formData.subject}`
        )}&body=${encodeURIComponent(
            `Name: ${formData.name}\nEmail: ${formData.email}\n\n${formData.message}`
        )}`;

        window.location.href = mailtoLink;
    };

    const handleChange = (e) => {
        setFormData(prev => ({
            ...prev,
            [e.target.name]: e.target.value
        }));
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
                    <a href="/" className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] rounded-xl shadow-lg shadow-md">
                            <SparklesIcon className="h-7 w-7 text-white" />
                        </div>
                        <span className="text-2xl font-bold bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] bg-clip-text text-transparent">
                            CollegeAI Pro
                        </span>
                    </a>
                    <div className="flex items-center gap-4">
                        <a href="/pricing" className="text-gray-600 hover:text-[#1A4D2E] font-medium transition-colors">
                            Pricing
                        </a>
                        <a
                            href="/"
                            className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-full hover:from-[#2D6B45] hover:to-[#3A7D5A] transition-all shadow-lg shadow-md"
                        >
                            Get Started
                        </a>
                    </div>
                </nav>
            </header>

            <main className="px-6 py-16">
                <div className="max-w-5xl mx-auto">
                    {/* Hero */}
                    <div className="text-center mb-16">
                        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
                            Get in Touch
                        </h1>
                        <p className="text-xl text-gray-600">
                            Have questions about CollegeAI Pro? We're here to help.
                        </p>
                    </div>

                    <div className="grid lg:grid-cols-5 gap-12">
                        {/* Contact Form */}
                        <div className="lg:col-span-3">
                            <div className="bg-white rounded-3xl p-8 shadow-xl border border-gray-200">
                                <h2 className="text-2xl font-bold text-gray-900 mb-6">Send Us a Message</h2>

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
                                            <option>Feature Request</option>
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
                                        className="w-full py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-lg font-bold rounded-xl hover:from-[#2D6B45] hover:to-[#3A7D5A] transition-all shadow-lg shadow-md flex items-center justify-center gap-2"
                                    >
                                        <EnvelopeIcon className="h-5 w-5" />
                                        Send Message
                                        <ArrowRightIcon className="h-5 w-5" />
                                    </button>
                                </form>

                                <p className="text-gray-500 text-sm text-center mt-4">
                                    This will open your email client with a pre-filled message.
                                </p>
                            </div>
                        </div>

                        {/* Sidebar */}
                        <div className="lg:col-span-2 space-y-6">
                            {/* Direct Email */}
                            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-3xl p-6 border border-[#A8C5A6]">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="p-3 bg-white rounded-xl shadow-sm">
                                        <EnvelopeIcon className="h-6 w-6 text-[#1A4D2E]" />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-gray-900">Email Us Directly</h3>
                                        <p className="text-gray-600 text-sm">We'll respond within 24 hours</p>
                                    </div>
                                </div>
                                <a
                                    href="mailto:cvsubs@gmail.com?subject=CollegeAI%20Pro%20Inquiry"
                                    className="block text-center py-3 bg-white text-[#1A4D2E] font-semibold rounded-xl border border-[#A8C5A6] hover:bg-[#D6E8D5] transition-all"
                                >
                                    cvsubs@gmail.com
                                </a>
                            </div>

                            {/* Quick Links */}
                            <div className="space-y-4">
                                <h3 className="font-bold text-gray-900">Quick Help</h3>
                                {quickLinks.map((link, idx) => (
                                    <a
                                        key={idx}
                                        href={link.link}
                                        className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-gray-200 hover:border-[#A8C5A6] hover:shadow-md transition-all group"
                                    >
                                        <div className="p-2 bg-gray-100 rounded-xl group-hover:bg-[#D6E8D5] transition-colors">
                                            <link.icon className="h-5 w-5 text-gray-600 group-hover:text-[#1A4D2E]" />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-gray-900">{link.title}</p>
                                            <p className="text-gray-500 text-sm">{link.desc}</p>
                                        </div>
                                        <ArrowRightIcon className="h-4 w-4 text-gray-400 ml-auto group-hover:translate-x-1 transition-transform" />
                                    </a>
                                ))}
                            </div>

                            {/* Response Time */}
                            <div className="bg-white rounded-2xl p-6 border border-gray-200">
                                <h3 className="font-bold text-gray-900 mb-3">Response Times</h3>
                                <ul className="space-y-2 text-sm text-gray-600">
                                    <li className="flex justify-between">
                                        <span>General inquiries</span>
                                        <span className="text-[#1A4D2E] font-medium">&lt; 24 hours</span>
                                    </li>
                                    <li className="flex justify-between">
                                        <span>Technical support</span>
                                        <span className="text-[#1A4D2E] font-medium">&lt; 12 hours</span>
                                    </li>
                                    <li className="flex justify-between">
                                        <span>Partnerships</span>
                                        <span className="text-[#1A4D2E] font-medium">&lt; 48 hours</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="px-6 py-12 bg-white border-t border-gray-100 mt-20">
                <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] rounded-xl">
                            <SparklesIcon className="h-6 w-6 text-white" />
                        </div>
                        <span className="text-xl font-bold bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] bg-clip-text text-transparent">
                            CollegeAI Pro
                        </span>
                    </div>
                    <div className="flex gap-6 text-sm text-gray-500">
                        <a href="/pricing" className="hover:text-[#1A4D2E]">Pricing</a>
                        <a href="/contact" className="hover:text-[#1A4D2E]">Contact</a>
                    </div>
                    <p className="text-gray-500 text-sm">
                        © {new Date().getFullYear()} CollegeAI Pro
                    </p>
                </div>
            </footer>
        </div>
    );
};

export default ContactPage;
