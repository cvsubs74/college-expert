import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApproach, APPROACHES } from '../context/ApproachContext';
import {
  AcademicCapIcon,
  CheckCircleIcon,
  ServerIcon,
  CloudIcon,
  CircleStackIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';

const ApproachSelector = () => {
  const navigate = useNavigate();
  const { selectedApproach, selectApproach } = useApproach();
  const [tempSelection, setTempSelection] = useState(selectedApproach);

  const getApproachIcon = (approachId) => {
    switch (approachId) {
      case 'hybrid':
        return <ServerIcon className="h-12 w-12" />;
      case 'rag':
        return <CloudIcon className="h-12 w-12" />;
      case 'elasticsearch':
        return <ServerIcon className="h-12 w-12" />;
      case 'firestore':
        return <CircleStackIcon className="h-12 w-12" />;
      default:
        return <CloudIcon className="h-12 w-12" />;
    }
  };

  const handleContinue = () => {
    selectApproach(tempSelection);
    navigate('/profile');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-center">
            <AcademicCapIcon className="h-10 w-10 text-primary" />
            <h1 className="ml-3 text-3xl font-bold text-gray-900">College Counselor</h1>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="max-w-6xl w-full">
          {/* Title Section */}
          <div className="text-center mb-12">
            <h2 className="text-4xl font-extrabold text-gray-900 mb-4">
              Choose Your Knowledge Base Approach
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Select how you want the system to search and retrieve college information.
              Each approach has different strengths and capabilities.
            </p>
          </div>

          {/* Approach Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {Object.values(APPROACHES).map((approach) => (
              <button
                key={approach.id}
                onClick={() => setTempSelection(approach.id)}
                className={`
                  relative p-6 rounded-xl border-2 transition-all duration-200
                  ${tempSelection === approach.id
                    ? 'border-primary bg-blue-50 shadow-lg scale-105'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-md'
                  }
                `}
              >
                {/* Selection Indicator */}
                {tempSelection === approach.id && (
                  <div className="absolute top-4 right-4">
                    <CheckCircleIcon className="h-6 w-6 text-primary" />
                  </div>
                )}

                {/* Icon */}
                <div className={`
                  flex items-center justify-center w-16 h-16 rounded-full mb-4 mx-auto
                  ${tempSelection === approach.id ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600'}
                `}>
                  {getApproachIcon(approach.id)}
                </div>

                {/* Title */}
                <h3 className="text-xl font-bold text-gray-900 mb-2 text-center">
                  {approach.name}
                </h3>

                {/* Description */}
                <p className="text-sm text-gray-600 mb-4 text-center">
                  {approach.description}
                </p>

                {/* Features */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                    Features:
                  </p>
                  {approach.features.map((feature, index) => (
                    <div key={index} className="flex items-start">
                      <div className="flex-shrink-0 h-5 w-5 text-green-500 mr-2">
                        <CheckCircleIcon />
                      </div>
                      <span className="text-sm text-gray-700">{feature}</span>
                    </div>
                  ))}
                </div>

                {/* Best For */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">
                    Best For:
                  </p>
                  <p className="text-sm text-gray-600">{approach.bestFor}</p>
                </div>
              </button>
            ))}
          </div>

          {/* Continue Button */}
          <div className="flex justify-center">
            <button
              onClick={handleContinue}
              className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors shadow-lg hover:shadow-xl"
            >
              Continue with {APPROACHES[tempSelection].name}
              <ArrowRightIcon className="ml-2 h-5 w-5" />
            </button>
          </div>

          {/* Info Box */}
          <div className="mt-8 max-w-3xl mx-auto bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-blue-900">
                  You can test all approaches
                </h3>
                <div className="mt-2 text-sm text-blue-700">
                  <p>
                    Don't worry! You can change your approach at any time from the settings.
                    This choice helps us optimize your experience, but you're free to experiment
                    with different approaches to find what works best for you.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white border-t border-gray-200 py-6">
        <p className="text-center text-sm text-gray-500">
          AI-Powered College Admissions Analysis System
        </p>
      </div>
    </div>
  );
};

export default ApproachSelector;
