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
  HeartIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';

const LandingPage = () => {
  const navigate = useNavigate();

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

  const journeySteps = [
    {
      icon: AcademicCapIcon,
      title: 'Build Your Profile',
      desc: 'Share your story, achievements, and aspirations',
      color: 'from-amber-400 to-orange-500'
    },
    {
      icon: BuildingLibraryIcon,
      title: 'Explore Universities',
      desc: 'Discover schools that match your unique fit',
      color: 'from-blue-400 to-indigo-500'
    },
    {
      icon: ChartBarIcon,
      title: 'Get Personalized Insights',
      desc: 'AI-powered analysis of your admissions chances',
      color: 'from-emerald-400 to-teal-500'
    },
    {
      icon: RocketLaunchIcon,
      title: 'Launch Your Journey',
      desc: 'Apply strategically with confidence',
      color: 'from-purple-400 to-pink-500'
    },
  ];

  const features = [
    {
      icon: BuildingLibraryIcon,
      title: 'UniInsight',
      desc: 'Deep research on 150+ universities with AI-powered fit analysis tailored to you',
      color: 'bg-blue-500',
      lightBg: 'bg-blue-50',
    },
    {
      icon: ChartBarIcon,
      title: 'FitMatch',
      desc: 'Personalized fit scores showing how well each school aligns with your profile',
      color: 'bg-emerald-500',
      lightBg: 'bg-emerald-50',
    },
    {
      icon: ChatBubbleLeftRightIcon,
      title: 'AI Counselor',
      desc: '24/7 intelligent guidance for all your college admissions questions',
      color: 'bg-amber-500',
      lightBg: 'bg-amber-50',
    },
    {
      icon: RocketLaunchIcon,
      title: 'Launchpad',
      desc: 'Track applications, deadlines, and action items in one organized dashboard',
      color: 'bg-purple-500',
      lightBg: 'bg-purple-50',
    },
    {
      icon: BriefcaseIcon,
      title: 'CareerMap',
      desc: 'AI-driven career pathing aligned to your interests and strengths',
      color: 'bg-rose-500',
      lightBg: 'bg-rose-50',
      badge: 'Coming Soon',
    },
    {
      icon: PencilSquareIcon,
      title: 'EssayPro',
      desc: 'Connect with essay specialists who help your authentic story shine',
      color: 'bg-teal-500',
      lightBg: 'bg-teal-50',
      badge: 'Coming Soon',
    },
  ];

  const testimonialHighlights = [
    { icon: StarIcon, stat: '150+', label: 'Universities Analyzed' },
    { icon: LightBulbIcon, stat: 'AI', label: 'Powered Insights' },
    { icon: HeartIcon, stat: '24/7', label: 'Personalized Support' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 via-white to-orange-50">
      {/* Header */}
      <header className="px-6 py-5 bg-white/80 backdrop-blur-sm sticky top-0 z-50 border-b border-amber-100">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg shadow-amber-200">
              <SparklesIcon className="h-7 w-7 text-white" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
              Nova
            </span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleCounselorSignIn}
              className="hidden md:block text-gray-600 hover:text-amber-600 font-medium transition-colors"
            >
              For Counselors
            </button>
            <button
              onClick={handleStudentSignIn}
              className="px-5 py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-full hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-amber-200 hover:shadow-amber-300"
            >
              Get Started
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="px-6 pt-16 pb-24">
        <div className="max-w-5xl mx-auto text-center">
          {/* Tagline Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-100 text-amber-800 rounded-full text-sm font-medium mb-8 border border-amber-200">
            <SparklesIcon className="h-4 w-4" />
            Your Personal College Counselor
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
            <span className="text-gray-900">Find Your </span>
            <span className="bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 bg-clip-text text-transparent">
              Perfect Fit
            </span>
            <br />
            <span className="text-gray-900">College</span>
          </h1>

          <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto mb-10 leading-relaxed">
            AI-powered guidance from exploration to application.
            <br className="hidden md:block" />
            <span className="text-gray-700 font-medium">Discover schools. Build your story. Launch your future.</span>
          </p>

          {/* Dual CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <button
              onClick={handleStudentSignIn}
              className="group px-8 py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-lg font-bold rounded-2xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-xl shadow-amber-200 hover:shadow-amber-300 hover:-translate-y-0.5 flex items-center justify-center gap-3"
            >
              <AcademicCapIcon className="h-6 w-6" />
              I'm a Student
              <ArrowRightIcon className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <button
              onClick={handleCounselorSignIn}
              className="group px-8 py-4 bg-white border-2 border-gray-200 text-gray-700 text-lg font-semibold rounded-2xl hover:border-amber-300 hover:bg-amber-50 transition-all shadow-lg flex items-center justify-center gap-3"
            >
              <UserGroupIcon className="h-6 w-6" />
              I'm a Counselor
              <ArrowRightIcon className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="flex flex-wrap justify-center gap-8 md:gap-16">
            {testimonialHighlights.map((item, idx) => (
              <div key={idx} className="flex flex-col items-center">
                <div className="flex items-center gap-2 mb-1">
                  <item.icon className="h-5 w-5 text-amber-500" />
                  <span className="text-3xl font-bold text-gray-900">{item.stat}</span>
                </div>
                <span className="text-sm text-gray-500 font-medium">{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Journey Steps */}
      <section className="px-6 py-20 bg-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Your Journey to College Success
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              From building your profile to submitting applications — Nova guides every step
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {journeySteps.map((step, idx) => (
              <div key={idx} className="relative group">
                {/* Connector line */}
                {idx < journeySteps.length - 1 && (
                  <div className="hidden md:block absolute top-14 left-full w-full h-0.5">
                    <div className="h-full bg-gradient-to-r from-amber-300 to-transparent" />
                  </div>
                )}

                <div className="relative bg-white border-2 border-gray-100 rounded-3xl p-6 text-center hover:border-amber-200 hover:shadow-xl hover:shadow-amber-100 transition-all group-hover:-translate-y-1">
                  <div className={`w-16 h-16 mx-auto mb-4 bg-gradient-to-br ${step.color} rounded-2xl flex items-center justify-center shadow-lg`}>
                    <step.icon className="h-8 w-8 text-white" />
                  </div>
                  <div className="absolute -top-3 -left-3 w-8 h-8 bg-gradient-to-br from-amber-500 to-orange-500 text-white rounded-full flex items-center justify-center font-bold text-sm shadow-lg">
                    {idx + 1}
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">{step.title}</h3>
                  <p className="text-sm text-gray-500">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="px-6 py-20 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Everything You Need to Succeed
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Powerful AI-driven tools designed to maximize your college admissions success
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, idx) => (
              <div
                key={idx}
                className={`group ${feature.lightBg} border border-gray-100 rounded-3xl p-6 hover:shadow-xl transition-all hover:-translate-y-1`}
              >
                <div className={`w-14 h-14 ${feature.color} rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform shadow-lg`}>
                  <feature.icon className="h-7 w-7 text-white" />
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
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* For Counselors Section */}
      <section className="px-6 py-20 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-3xl p-8 md:p-12 border border-purple-100">
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div>
                <span className="inline-block px-4 py-1.5 bg-purple-100 text-purple-700 text-sm font-semibold rounded-full border border-purple-200 mb-4">
                  For Counselors & Essay Specialists
                </span>
                <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                  Empower Your Students
                </h2>
                <p className="text-gray-600 mb-6 text-lg">
                  Join Nova's network of professionals helping students achieve their college dreams.
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    'Dashboard to track student progress',
                    'AI-powered fit analysis at scale',
                    'Connect with students seeking essay help',
                    'Grow your practice with our platform',
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3 text-gray-700">
                      <div className="p-1 bg-purple-100 rounded-full">
                        <CheckCircleIcon className="h-4 w-4 text-purple-600" />
                      </div>
                      {item}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={handleCounselorSignIn}
                  className="px-6 py-3 bg-purple-600 text-white font-semibold rounded-xl hover:bg-purple-500 transition-all shadow-lg shadow-purple-200 hover:shadow-purple-300 flex items-center gap-2"
                >
                  Join as a Counselor
                  <ArrowRightIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="hidden md:block">
                <div className="bg-white rounded-2xl p-6 shadow-xl border border-purple-100">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
                      <UserGroupIcon className="h-6 w-6 text-purple-600" />
                    </div>
                    <div>
                      <p className="text-gray-900 font-semibold">Counselor Dashboard</p>
                      <p className="text-purple-600 text-sm font-medium">Coming Soon</p>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="h-3 bg-purple-100 rounded-full w-full" />
                    <div className="h-3 bg-purple-50 rounded-full w-4/5" />
                    <div className="h-3 bg-purple-50 rounded-full w-3/5" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-6 py-24 bg-gradient-to-b from-amber-50 to-orange-50">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex p-4 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl shadow-xl shadow-amber-200 mb-8">
            <SparklesIcon className="h-10 w-10 text-white" />
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Ready to Find Your Perfect Fit?
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Join students navigating their path to college success with Nova
          </p>
          <button
            onClick={handleStudentSignIn}
            className="px-10 py-4 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-lg font-bold rounded-2xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-xl shadow-amber-200 hover:shadow-amber-300 hover:-translate-y-0.5"
          >
            Get Started Free
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 py-12 bg-white border-t border-gray-100">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl">
                <SparklesIcon className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">
                Nova
              </span>
            </div>
            <p className="text-gray-500 text-sm">
              © {new Date().getFullYear()} Nova. Find Your Perfect Fit.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
