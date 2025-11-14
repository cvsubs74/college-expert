import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AcademicCapIcon,
  SparklesIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  ChartBarIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';

const LandingPage = () => {
  const navigate = useNavigate();

  const handleSignIn = async () => {
    try {
      await signInWithGoogle();
      navigate('/chat');
    } catch (error) {
      console.error('Failed to sign in with Google', error);
    }
  };

  const features = [
    {
      icon: <ChatBubbleLeftRightIcon className="h-10 w-10 text-primary" />,
      title: 'Expert College Guidance',
      description: 'Get instant answers about colleges, admissions requirements, and application strategies from our AI-powered knowledge base.',
    },
    {
      icon: <DocumentTextIcon className="h-10 w-10 text-primary" />,
      title: 'Profile Management',
      description: 'Upload and manage your academic profile, including transcripts, test scores, activities, and awards in one secure place.',
    },
    {
      icon: <ChartBarIcon className="h-10 w-10 text-primary" />,
      title: 'Admissions Analysis',
      description: 'Receive comprehensive, data-driven analysis of your chances at specific universities with personalized recommendations.',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AcademicCapIcon className="h-8 w-8 text-primary" />
              <span className="text-2xl font-bold text-gray-900">College Counselor</span>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          Your AI-Powered College Admissions Partner
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
          Navigate the college admissions process with confidence. Get expert guidance, 
          manage your profile, and receive personalized analysis powered by AI.
        </p>
        <button
          onClick={handleSignIn}
          className="inline-flex items-center px-8 py-4 bg-primary text-white text-lg font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-lg"
        >
          <svg className="w-6 h-6 mr-3" viewBox="0 0 24 24">
            <path
              fill="currentColor"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="currentColor"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="currentColor"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="currentColor"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Sign in with Google
        </button>
      </section>

      {/* Features Section */}
      <section className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {features.map((feature, index) => (
              <div key={index} className="text-center">
                <div className="flex justify-center mb-4">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {feature.title}
                </h3>
                <p className="text-gray-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          Everything you need for college admissions success
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
            <SparklesIcon className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              AI-Powered Insights
            </h3>
            <p className="text-gray-600">
              Leverage advanced AI to get accurate, data-driven insights about your college admissions chances.
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
            <ChatBubbleLeftRightIcon className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              24/7 Expert Guidance
            </h3>
            <p className="text-gray-600">
              Ask questions anytime and get instant answers based on our curated knowledge base of college admissions expertise.
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
            <ShieldCheckIcon className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Secure & Private
            </h3>
            <p className="text-gray-600">
              Your academic information is protected with enterprise-grade security. We never share your data.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-gray-600">
            © {new Date().getFullYear()} College Counselor. Powered by AI.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
