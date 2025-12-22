import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  SparklesIcon,
  RocketLaunchIcon,
  AcademicCapIcon,
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  ArrowRightIcon,
  BuildingLibraryIcon,
  ShieldCheckIcon,
  ClockIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  BookOpenIcon,
  KeyIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';

/**
 * LandingPage - Stratia Admissions themed landing
 * 
 * Uses Digital Ivy design system:
 * - Cream background (#FDFCF7)
 * - Forest green primary (#1A4D2E)
 * - Sage secondary (#D6E8D5)
 * - Playfair Display for headlines
 */
const LandingPage = () => {
  const navigate = useNavigate();
  const [openFaq, setOpenFaq] = useState(null);

  const handleSignIn = async () => {
    try {
      await signInWithGoogle();
      navigate('/launchpad');
    } catch (error) {
      console.error('Failed to sign in', error);
    }
  };

  // Journey steps with Stratia colors
  const journeySteps = [
    {
      icon: AcademicCapIcon,
      title: 'Build Your Profile',
      desc: 'Upload transcripts, test scores, and activities — our AI extracts everything',
      color: 'from-[#1A4D2E] to-[#2D6B45]'
    },
    {
      icon: BuildingLibraryIcon,
      title: 'Discover Colleges',
      desc: 'Explore 150+ universities with AI-powered match scores',
      color: 'from-[#2D6B45] to-[#A8C5A6]'
    },
    {
      icon: ChartBarIcon,
      title: 'Get Fit Analysis',
      desc: 'Understand your real admission chances at each school',
      color: 'from-[#C05838] to-[#E8A090]'
    },
    {
      icon: RocketLaunchIcon,
      title: 'Apply with Confidence',
      desc: 'Strategic advice from our AI counselor every step',
      color: 'from-[#1A4D2E] to-[#C05838]'
    },
  ];

  // Features with Stratia palette
  const features = [
    {
      icon: BuildingLibraryIcon,
      title: 'University Explorer',
      desc: 'Research 150+ top colleges with comprehensive profiles and admission stats',
      bg: 'bg-[#D6E8D5]',
      iconBg: 'bg-[#1A4D2E]'
    },
    {
      icon: ChartBarIcon,
      title: 'Personalized Fit Score',
      desc: 'AI calculates your admission probability based on your unique profile',
      bg: 'bg-[#FCEEE8]',
      iconBg: 'bg-[#C05838]'
    },
    {
      icon: ChatBubbleLeftRightIcon,
      title: 'AI Admissions Counselor',
      desc: 'Get 24/7 expert guidance on applications and strategy',
      bg: 'bg-[#D6E8D5]',
      iconBg: 'bg-[#2D6B45]'
    },
    {
      icon: RocketLaunchIcon,
      title: 'Application Launchpad',
      desc: 'Track all your applications, deadlines, and requirements',
      bg: 'bg-[#F8F6F0]',
      iconBg: 'bg-[#1A4D2E]'
    },
    {
      icon: DocumentTextIcon,
      title: 'Smart Profile Builder',
      desc: 'Upload documents and our AI extracts your academic info',
      bg: 'bg-[#FCEEE8]',
      iconBg: 'bg-[#C05838]'
    },
  ];

  // Trust indicators
  const trustIndicators = [
    { icon: BuildingLibraryIcon, stat: '150+', label: 'Universities', sublabel: 'Detailed Profiles' },
    { icon: SparklesIcon, stat: 'AI', label: 'Powered', sublabel: 'Smart Analysis' },
    { icon: ClockIcon, stat: '24/7', label: 'Available', sublabel: 'AI Counselor' },
    { icon: ShieldCheckIcon, stat: 'Free', label: 'To Start', sublabel: 'No Credit Card' },
  ];

  // FAQs
  const faqs = [
    {
      question: 'How does AI help with college admissions?',
      answer: 'Our AI analyzes your complete academic profile — GPA, test scores, extracurricular activities, and interests — to provide personalized college recommendations and fit scores.'
    },
    {
      question: 'What makes Stratia different from other tools?',
      answer: 'Unlike basic college search tools, Stratia uses advanced AI to provide truly personalized recommendations based on real admission data from 150+ universities.'
    },
    {
      question: 'Is Stratia Admissions free to use?',
      answer: 'Yes! Stratia offers a comprehensive free tier including AI college matching, fit analysis, and access to our 24/7 AI counselor. No credit card required.'
    },
    {
      question: 'How accurate are the college fit scores?',
      answer: 'Our AI-powered fit scores are based on real admission data and acceptance rates. While no tool guarantees admission, our analysis provides highly accurate predictions.'
    },
  ];

  return (
    <div className="min-h-screen bg-[#FDFCF7]">
      {/* Header with Stratia styling */}
      <header className="px-6 py-5 sticky top-0 z-50 transition-all bg-[#FDFCF7]/90 backdrop-blur-sm border-b border-[#E0DED8]" role="banner">
        <nav className="max-w-7xl mx-auto flex items-center justify-between" aria-label="Main navigation">
          {/* Logo */}
          <Link to="/" className="flex items-center group">
            <img
              src="/logo.png"
              alt="Stratia Admissions"
              className="h-24 w-auto object-contain mix-blend-multiply"
            />
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-4">
            <Link to="/pricing" className="hidden md:block text-[#4A4A4A] hover:text-[#1A4D2E] font-medium transition-colors">
              Pricing
            </Link>
            <Link to="/contact" className="hidden md:block text-[#4A4A4A] hover:text-[#1A4D2E] font-medium transition-colors">
              Contact
            </Link>
            <button
              onClick={handleSignIn}
              className="px-5 py-2.5 bg-[#1A4D2E] text-white font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md hover:shadow-lg"
            >
              Get Started Free
            </button>
          </div>
        </nav>
      </header>

      <main>
        {/* Hero Section */}
        <section className="px-6 pt-16 pb-24" aria-labelledby="hero-heading">
          <div className="max-w-5xl mx-auto text-center">
            {/* Tagline Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#D6E8D5] text-[#1A4D2E] rounded-full text-sm font-medium mb-8 border border-[#A8C5A6]">
              <SparklesIcon className="h-4 w-4" />
              <span>AI-Powered College Strategy Platform</span>
            </div>

            {/* Headline - Serif */}
            <h1 id="hero-heading" className="font-serif text-5xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
              <span className="text-[#2C2C2C]">Your </span>
              <span className="text-[#1A4D2E]">Dream College</span>
              <br />
              <span className="text-[#2C2C2C]">Is Within Reach</span>
            </h1>

            <p className="text-xl md:text-2xl text-[#4A4A4A] max-w-3xl mx-auto mb-10 leading-relaxed">
              <strong className="text-[#2C2C2C]">AI-powered college guidance built for you.</strong>{' '}
              Get personalized university matches, admission insights, and 24/7 support — like having a $5,000 counselor in your pocket.
            </p>

            {/* CTA Button */}
            <div className="flex justify-center mb-16">
              <button
                onClick={handleSignIn}
                className="group px-10 py-5 bg-[#1A4D2E] text-white text-xl font-bold rounded-2xl hover:bg-[#2D6B45] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5 flex items-center justify-center gap-3"
              >
                <RocketLaunchIcon className="h-7 w-7" />
                Start My College Journey
                <ArrowRightIcon className="h-6 w-6 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>

            {/* Trust Indicators */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 max-w-3xl mx-auto">
              {trustIndicators.map((item, idx) => (
                <div key={idx} className="flex flex-col items-center p-4 bg-white rounded-2xl shadow-sm border border-[#E0DED8]">
                  <item.icon className="h-6 w-6 text-[#1A4D2E] mb-2" />
                  <span className="text-2xl font-bold text-[#2C2C2C]">{item.stat}</span>
                  <span className="text-sm font-medium text-[#4A4A4A]">{item.label}</span>
                  <span className="text-xs text-[#6B6B6B]">{item.sublabel}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="px-6 py-20 bg-white" aria-labelledby="journey-heading">
          <div className="max-w-6xl mx-auto">
            <header className="text-center mb-16">
              <h2 id="journey-heading" className="font-serif text-3xl md:text-4xl font-bold text-[#2C2C2C] mb-4">
                Your Path to College Success
              </h2>
              <p className="text-lg text-[#4A4A4A] max-w-2xl mx-auto">
                From building your profile to submitting applications — our AI guides every step
              </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {journeySteps.map((step, idx) => (
                <article key={idx} className="relative group">
                  {idx < journeySteps.length - 1 && (
                    <div className="hidden md:block absolute top-14 left-full w-full h-0.5">
                      <div className="h-full bg-gradient-to-r from-[#D6E8D5] to-transparent" />
                    </div>
                  )}

                  <div className="relative bg-white border-2 border-[#E0DED8] rounded-3xl p-6 text-center hover:border-[#1A4D2E] hover:shadow-xl transition-all group-hover:-translate-y-1">
                    <div className={`w-16 h-16 mx-auto mb-4 bg-gradient-to-br ${step.color} rounded-2xl flex items-center justify-center shadow-lg`}>
                      <step.icon className="h-8 w-8 text-white" />
                    </div>
                    <div className="absolute -top-3 -left-3 w-8 h-8 bg-[#1A4D2E] text-white rounded-full flex items-center justify-center font-bold text-sm shadow-lg">
                      {idx + 1}
                    </div>
                    <h3 className="font-serif text-lg font-bold text-[#2C2C2C] mb-2">{step.title}</h3>
                    <p className="text-sm text-[#4A4A4A]">{step.desc}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="px-6 py-20 bg-[#F8F6F0]" aria-labelledby="features-heading">
          <div className="max-w-6xl mx-auto">
            <header className="text-center mb-16">
              <h2 id="features-heading" className="font-serif text-3xl md:text-4xl font-bold text-[#2C2C2C] mb-4">
                Complete College Admissions Platform
              </h2>
              <p className="text-lg text-[#4A4A4A] max-w-2xl mx-auto">
                AI-powered tools to maximize your admission chances
              </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {features.map((feature, idx) => (
                <article
                  key={idx}
                  className={`group ${feature.bg} border border-[#E0DED8] rounded-3xl p-6 hover:shadow-xl transition-all hover:-translate-y-1`}
                >
                  <div className={`w-14 h-14 ${feature.iconBg} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg`}>
                    <feature.icon className="h-7 w-7 text-white" />
                  </div>
                  <h3 className="font-serif text-xl font-bold text-[#2C2C2C] mb-2">{feature.title}</h3>
                  <p className="text-[#4A4A4A] leading-relaxed">{feature.desc}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Social Proof */}
        <section className="px-6 py-16 bg-white" aria-labelledby="proof-heading">
          <div className="max-w-4xl mx-auto text-center">
            <h2 id="proof-heading" className="font-serif text-2xl md:text-3xl font-bold text-[#2C2C2C] mb-12">
              Students Apply to Top Universities
            </h2>
            <div className="flex flex-wrap justify-center gap-8 opacity-60">
              {['Harvard', 'Stanford', 'MIT', 'Yale', 'Princeton', 'Columbia', 'UPenn', 'Brown'].map((school) => (
                <span key={school} className="text-lg font-semibold text-[#4A4A4A]">
                  {school}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section className="px-6 py-20 bg-[#FDFCF7]" aria-labelledby="faq-heading">
          <div className="max-w-3xl mx-auto">
            <header className="text-center mb-12">
              <h2 id="faq-heading" className="font-serif text-3xl md:text-4xl font-bold text-[#2C2C2C] mb-4">
                Frequently Asked Questions
              </h2>
              <p className="text-lg text-[#4A4A4A]">
                Everything you need to know about using AI for college admissions
              </p>
            </header>

            <div className="space-y-4">
              {faqs.map((faq, idx) => (
                <article key={idx} className="border border-[#E0DED8] rounded-2xl overflow-hidden bg-white">
                  <button
                    onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    className="w-full flex items-center justify-between p-5 text-left hover:bg-[#F8F6F0] transition-colors"
                    aria-expanded={openFaq === idx}
                  >
                    <h3 className="font-semibold text-[#2C2C2C] pr-4">{faq.question}</h3>
                    {openFaq === idx ? (
                      <ChevronUpIcon className="h-5 w-5 text-[#1A4D2E] flex-shrink-0" />
                    ) : (
                      <ChevronDownIcon className="h-5 w-5 text-[#4A4A4A] flex-shrink-0" />
                    )}
                  </button>
                  {openFaq === idx && (
                    <div className="px-5 pb-5 text-[#4A4A4A] leading-relaxed">
                      {faq.answer}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="px-6 py-24 bg-[#D6E8D5]" aria-labelledby="cta-heading">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex p-4 bg-[#1A4D2E] rounded-2xl shadow-xl mb-8">
              <SparklesIcon className="h-10 w-10 text-white" />
            </div>
            <h2 id="cta-heading" className="font-serif text-3xl md:text-4xl font-bold text-[#2C2C2C] mb-4">
              Ready to Find Your Perfect Fit College?
            </h2>
            <p className="text-lg text-[#4A4A4A] mb-8">
              Join students using AI to navigate their college admissions journey — completely free
            </p>
            <button
              onClick={handleSignIn}
              className="px-10 py-4 bg-[#1A4D2E] text-white text-lg font-bold rounded-2xl hover:bg-[#2D6B45] transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started Free — No Credit Card Required
            </button>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="px-6 py-12 bg-white border-t border-[#E0DED8]" role="contentinfo">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 mb-8">
            <div>
              <Link to="/" className="flex items-center mb-4">
                <img
                  src="/logo.png"
                  alt="Stratia Admissions"
                  className="h-14 w-auto object-contain mix-blend-multiply"
                />
              </Link>
              <p className="text-[#4A4A4A] text-sm">
                AI-powered college admissions strategy platform. Find your perfect fit college.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-[#2C2C2C] mb-3">Features</h3>
              <ul className="space-y-2 text-sm text-[#4A4A4A]">
                <li>AI College Matching</li>
                <li>Personalized Fit Analysis</li>
                <li>24/7 AI Counselor</li>
                <li>Application Tracker</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-[#2C2C2C] mb-3">Resources</h3>
              <ul className="space-y-2 text-sm text-[#4A4A4A]">
                <li>College Search</li>
                <li>Admissions Guide</li>
                <li>Deadline Tracking</li>
                <li>Financial Aid</li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-[#E0DED8]">
            <p className="text-[#4A4A4A] text-sm">
              © {new Date().getFullYear()} Stratia Admissions. AI-Powered College Strategy.
            </p>
            <div className="flex gap-6 text-sm text-[#4A4A4A]">
              <a href="#" className="hover:text-[#1A4D2E]">Privacy Policy</a>
              <a href="#" className="hover:text-[#1A4D2E]">Terms of Service</a>
              <a href="#" className="hover:text-[#1A4D2E]">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
