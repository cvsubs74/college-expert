import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  SparklesIcon,
  RocketLaunchIcon,
  AcademicCapIcon,
  BriefcaseIcon,
  PencilSquareIcon,
  ChartBarIcon,
  UserGroupIcon,
  ChatBubbleLeftRightIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  BuildingLibraryIcon,
  StarIcon,
  LightBulbIcon,
  HeartIcon,
  ShieldCheckIcon,
  ClockIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';

const LandingPage = () => {
  const navigate = useNavigate();
  const [openFaq, setOpenFaq] = useState(null);

  const handleStudentSignIn = async () => {
    try {
      await signInWithGoogle();
      navigate('/profile');
    } catch (error) {
      console.error('Failed to sign in', error);
    }
  };

  const handleCounselorSignIn = async () => {
    try {
      await signInWithGoogle();
      navigate('/profile');
    } catch (error) {
      console.error('Failed to sign in', error);
    }
  };

  // SEO-optimized journey steps with keyword-rich descriptions
  const journeySteps = [
    {
      icon: AcademicCapIcon,
      title: 'Build Your Student Profile',
      desc: 'Upload transcripts, test scores, and activities — our AI extracts and organizes everything',
      color: 'from-amber-400 to-orange-500'
    },
    {
      icon: BuildingLibraryIcon,
      title: 'Discover Best-Fit Colleges',
      desc: 'Explore 150+ universities with AI-powered match scores based on your unique profile',
      color: 'from-blue-400 to-indigo-500'
    },
    {
      icon: ChartBarIcon,
      title: 'Get Admissions Insights',
      desc: 'Understand your admission chances with personalized fit analysis for each school',
      color: 'from-emerald-400 to-teal-500'
    },
    {
      icon: RocketLaunchIcon,
      title: 'Apply with Confidence',
      desc: 'Track deadlines, manage applications, and get strategic advice from our AI counselor',
      color: 'from-purple-400 to-pink-500'
    },
  ];

  // SEO-optimized features with keyword-rich descriptions
  const features = [
    {
      icon: BuildingLibraryIcon,
      title: 'University Explorer',
      desc: 'Research 150+ top colleges and universities with comprehensive profiles, admission stats, and financial aid data',
      color: 'bg-blue-500',
      lightBg: 'bg-blue-50',
      keywords: ['college research', 'university database', 'admission statistics']
    },
    {
      icon: ChartBarIcon,
      title: 'Personalized Fit Score',
      desc: 'AI calculates your admission probability and fit score for each college based on your GPA, test scores, and activities',
      color: 'bg-emerald-500',
      lightBg: 'bg-emerald-50',
      keywords: ['admission chances', 'college match', 'fit analysis']
    },
    {
      icon: ChatBubbleLeftRightIcon,
      title: 'AI Admissions Counselor',
      desc: 'Get 24/7 expert guidance on college applications and strategy — powered by advanced AI',
      color: 'bg-amber-500',
      lightBg: 'bg-amber-50',
      keywords: ['college counselor', 'admissions advice', 'application help']
    },
    {
      icon: RocketLaunchIcon,
      title: 'Application Launchpad',
      desc: 'Track all your college applications, deadlines, and requirements in one organized dashboard',
      color: 'bg-purple-500',
      lightBg: 'bg-purple-50',
      keywords: ['application tracker', 'deadline management', 'college list']
    },
    {
      icon: DocumentTextIcon,
      title: 'Smart Profile Builder',
      desc: 'Upload documents and our AI automatically extracts your GPA, SAT/ACT scores, activities, and achievements',
      color: 'bg-rose-500',
      lightBg: 'bg-rose-50',
      keywords: ['profile builder', 'document parsing', 'transcript analysis']
    },
  ];

  // Trust indicators with real metrics
  const trustIndicators = [
    { icon: BuildingLibraryIcon, stat: '150+', label: 'Universities', sublabel: 'Detailed Profiles' },
    { icon: SparklesIcon, stat: 'AI', label: 'Powered', sublabel: 'Smart Analysis' },
    { icon: ClockIcon, stat: '24/7', label: 'Available', sublabel: 'AI Counselor' },
    { icon: ShieldCheckIcon, stat: 'Free', label: 'To Start', sublabel: 'No Credit Card' },
  ];

  // SEO-optimized FAQs
  const faqs = [
    {
      question: 'How does AI help with college admissions?',
      answer: 'Our AI analyzes your complete academic profile — GPA, test scores, extracurricular activities, and interests — to provide personalized college recommendations. It calculates fit scores for each university, identifying schools where you have the best admission chances and will thrive academically and socially.'
    },
    {
      question: 'What makes CollegeAI Pro different from other college planning tools?',
      answer: 'Unlike basic college search tools, CollegeAI Pro uses advanced AI to provide truly personalized recommendations. We analyze your unique profile against real admission data from 150+ universities, giving you accurate fit scores and strategic insights that traditional tools cannot provide.'
    },
    {
      question: 'Is CollegeAI Pro free to use?',
      answer: 'Yes! CollegeAI Pro offers a comprehensive free tier that includes AI-powered college matching, personalized fit analysis, access to our 24/7 AI counselor, and full use of the application tracking dashboard. No credit card required.'
    },
    {
      question: 'How accurate are the college fit scores?',
      answer: 'Our AI-powered fit scores are based on real admission data, acceptance rates, and student profiles from each university. While no tool can guarantee admission, our analysis provides highly accurate predictions by considering multiple factors including academic fit, campus culture, and program strength.'
    },
    {
      question: 'Can I upload my transcript and test scores?',
      answer: 'Absolutely! You can upload PDFs, Word documents, or images of your transcripts, SAT/ACT score reports, and activity lists. Our AI automatically extracts and organizes all the relevant information to build your comprehensive student profile.'
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 via-white to-orange-50">
      {/* SEO-Optimized Header with Semantic HTML */}
      <header className="px-6 py-5 bg-white/80 backdrop-blur-sm sticky top-0 z-50 border-b border-amber-100" role="banner">
        <nav className="max-w-7xl mx-auto flex items-center justify-between" aria-label="Main navigation">
          <a href="/" className="flex items-center gap-3" aria-label="CollegeAI Pro Home">
            <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg shadow-amber-200">
              <SparklesIcon className="h-7 w-7 text-white" aria-hidden="true" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
              CollegeAI Pro
            </span>
          </a>
          <div className="flex items-center gap-4">
            <a
              href="/pricing"
              className="hidden md:block text-gray-600 hover:text-amber-600 font-medium transition-colors"
            >
              Pricing
            </a>
            <a
              href="/contact"
              className="hidden md:block text-gray-600 hover:text-amber-600 font-medium transition-colors"
            >
              Contact
            </a>
            <button
              onClick={handleStudentSignIn}
              className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-full hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200 hover:shadow-amber-300"
              aria-label="Get started with CollegeAI Pro"
            >
              Get Started Free
            </button>
          </div>
        </nav>
      </header>

      {/* Hero Section with SEO-Optimized H1 */}
      <main>
        <section className="px-6 pt-16 pb-24" aria-labelledby="hero-heading">
          <div className="max-w-5xl mx-auto text-center">
            {/* Tagline Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-800 rounded-full text-sm font-medium mb-8 border border-amber-200">
              <SparklesIcon className="h-4 w-4" aria-hidden="true" />
              <span>AI-Powered College Admissions Counselor</span>
            </div>

            <h1 id="hero-heading" className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
              <span className="text-gray-900">Your </span>
              <span className="bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 bg-clip-text text-transparent">
                Dream College
              </span>
              <br />
              <span className="text-gray-900">Is Within Reach</span>
            </h1>

            <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-10 leading-relaxed">
              <strong className="text-gray-700">AI-powered college guidance built for you.</strong>{' '}
              Get personalized university matches, admission insights, and 24/7 support — like having a $5,000 counselor in your pocket.
            </p>

            {/* Single CTA */}
            <div className="flex justify-center mb-16">
              <button
                onClick={handleStudentSignIn}
                className="group px-10 py-5 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xl font-bold rounded-2xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-xl shadow-amber-200 hover:shadow-amber-300 hover:-translate-y-0.5 flex items-center justify-center gap-3"
                aria-label="Start your college admissions journey"
              >
                <RocketLaunchIcon className="h-7 w-7" aria-hidden="true" />
                Start My College Journey
                <ArrowRightIcon className="h-6 w-6 group-hover:translate-x-1 transition-transform" aria-hidden="true" />
              </button>
            </div>

            {/* Trust Indicators */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8 max-w-3xl mx-auto">
              {trustIndicators.map((item, idx) => (
                <div key={idx} className="flex flex-col items-center p-4 bg-white rounded-2xl shadow-sm border border-gray-100">
                  <item.icon className="h-6 w-6 text-amber-500 mb-2" aria-hidden="true" />
                  <span className="text-2xl font-bold text-gray-900">{item.stat}</span>
                  <span className="text-sm font-medium text-gray-700">{item.label}</span>
                  <span className="text-xs text-gray-500">{item.sublabel}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section className="px-6 py-20 bg-white" aria-labelledby="journey-heading">
          <div className="max-w-6xl mx-auto">
            <header className="text-center mb-16">
              <h2 id="journey-heading" className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                Your Path to College Admissions Success
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                From building your student profile to submitting applications — our AI guides every step of your college journey
              </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {journeySteps.map((step, idx) => (
                <article key={idx} className="relative group">
                  {/* Connector line */}
                  {idx < journeySteps.length - 1 && (
                    <div className="hidden md:block absolute top-14 left-full w-full h-0.5" aria-hidden="true">
                      <div className="h-full bg-gradient-to-r from-amber-300 to-transparent" />
                    </div>
                  )}

                  <div className="relative bg-white border-2 border-gray-100 rounded-3xl p-6 text-center hover:border-amber-200 hover:shadow-xl hover:shadow-amber-100 transition-all group-hover:-translate-y-1">
                    <div className={`w-16 h-16 mx-auto mb-4 bg-gradient-to-br ${step.color} rounded-2xl flex items-center justify-center shadow-lg`}>
                      <step.icon className="h-8 w-8 text-white" aria-hidden="true" />
                    </div>
                    <div className="absolute -top-3 -left-3 w-8 h-8 bg-gradient-to-br from-amber-500 to-orange-500 text-white rounded-full flex items-center justify-center font-bold text-sm shadow-lg" aria-label={`Step ${idx + 1}`}>
                      {idx + 1}
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 mb-2">{step.title}</h3>
                    <p className="text-sm text-gray-500">{step.desc}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Features Grid with SEO Keywords */}
        <section className="px-6 py-20 bg-gradient-to-b from-gray-50 to-white" aria-labelledby="features-heading">
          <div className="max-w-6xl mx-auto">
            <header className="text-center mb-16">
              <h2 id="features-heading" className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                Complete College Admissions Platform
              </h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                AI-powered tools designed to maximize your college admission chances and simplify the application process
              </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {features.map((feature, idx) => (
                <article
                  key={idx}
                  className={`group ${feature.lightBg} border border-gray-100 rounded-3xl p-6 hover:shadow-xl transition-all hover:-translate-y-1`}
                >
                  <div className={`w-14 h-14 ${feature.color} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg`}>
                    <feature.icon className="h-7 w-7 text-white" aria-hidden="true" />
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="text-xl font-bold text-gray-900">{feature.title}</h3>
                    {feature.badge && (
                      <span className="px-2 py-0.5 bg-white text-amber-600 text-xs font-medium rounded-full border border-amber-200">
                        {feature.badge}
                      </span>
                    )}
                  </div>
                  <p className="text-gray-600 leading-relaxed">{feature.desc}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Social Proof Section */}
        <section className="px-6 py-16 bg-white" aria-labelledby="proof-heading">
          <div className="max-w-4xl mx-auto text-center">
            <h2 id="proof-heading" className="text-2xl md:text-3xl font-bold text-gray-900 mb-12">
              Trusted by Students Applying to Top Universities
            </h2>
            <div className="flex flex-wrap justify-center gap-8 opacity-60">
              {['Harvard', 'Stanford', 'MIT', 'Yale', 'Princeton', 'Columbia', 'UPenn', 'Brown'].map((school) => (
                <span key={school} className="text-lg font-semibold text-gray-500">
                  {school}
                </span>
              ))}
            </div>
          </div>
        </section>


        {/* FAQ Section for SEO */}
        <section className="px-6 py-20 bg-white" aria-labelledby="faq-heading">
          <div className="max-w-3xl mx-auto">
            <header className="text-center mb-12">
              <h2 id="faq-heading" className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                Frequently Asked Questions
              </h2>
              <p className="text-lg text-gray-600">
                Everything you need to know about using AI for college admissions
              </p>
            </header>

            <div className="space-y-4">
              {faqs.map((faq, idx) => (
                <article key={idx} className="border border-gray-200 rounded-2xl overflow-hidden">
                  <button
                    onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                    className="w-full flex items-center justify-between p-5 text-left bg-white hover:bg-gray-50 transition-colors"
                    aria-expanded={openFaq === idx}
                    aria-controls={`faq-answer-${idx}`}
                  >
                    <h3 className="text-lg font-semibold text-gray-900 pr-4">{faq.question}</h3>
                    {openFaq === idx ? (
                      <ChevronUpIcon className="h-5 w-5 text-amber-500 flex-shrink-0" aria-hidden="true" />
                    ) : (
                      <ChevronDownIcon className="h-5 w-5 text-gray-400 flex-shrink-0" aria-hidden="true" />
                    )}
                  </button>
                  {openFaq === idx && (
                    <div id={`faq-answer-${idx}`} className="px-5 pb-5 text-gray-600 leading-relaxed">
                      {faq.answer}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="px-6 py-24 bg-gradient-to-b from-amber-50 to-orange-50" aria-labelledby="cta-heading">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex p-4 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl shadow-xl shadow-amber-200 mb-8">
              <SparklesIcon className="h-10 w-10 text-white" aria-hidden="true" />
            </div>
            <h2 id="cta-heading" className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Ready to Find Your Perfect Fit College?
            </h2>
            <p className="text-lg text-gray-600 mb-8">
              Join thousands of students using AI to navigate their college admissions journey — completely free
            </p>
            <button
              onClick={handleStudentSignIn}
              className="px-10 py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-lg font-bold rounded-2xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-xl shadow-amber-200 hover:shadow-amber-300 hover:-translate-y-0.5"
              aria-label="Start using CollegeAI Pro for free"
            >
              Get Started Free — No Credit Card Required
            </button>
          </div>
        </section>
      </main>

      {/* SEO-Optimized Footer */}
      <footer className="px-6 py-12 bg-white border-t border-gray-100" role="contentinfo">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 mb-8">
            <div>
              <a href="/" className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl">
                  <SparklesIcon className="h-6 w-6 text-white" aria-hidden="true" />
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
                  CollegeAI Pro
                </span>
              </a>
              <p className="text-gray-500 text-sm">
                AI-powered college admissions counseling platform. Find your perfect fit college with personalized recommendations.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Features</h3>
              <ul className="space-y-2 text-sm text-gray-500">
                <li>AI College Matching</li>
                <li>Personalized Fit Analysis</li>
                <li>24/7 AI Counselor</li>
                <li>Application Tracker</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-3">Resources</h3>
              <ul className="space-y-2 text-sm text-gray-500">
                <li>College Search</li>
                <li>Admissions Guide</li>
                <li>Deadline Tracking</li>
                <li>Financial Aid</li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-gray-100">
            <p className="text-gray-500 text-sm">
              © {new Date().getFullYear()} CollegeAI Pro. AI-Powered College Admissions Counselor.
            </p>
            <div className="flex gap-6 text-sm text-gray-500">
              <a href="#" className="hover:text-amber-600">Privacy Policy</a>
              <a href="#" className="hover:text-amber-600">Terms of Service</a>
              <a href="#" className="hover:text-amber-600">Contact</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
