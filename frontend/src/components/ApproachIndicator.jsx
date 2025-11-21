import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApproach } from '../context/ApproachContext';
import { 
  CogIcon, 
  ChevronDownIcon,
  CheckIcon,
  ServerIcon,
  CloudIcon,
  CircleStackIcon
} from '@heroicons/react/24/outline';

const ApproachIndicator = () => {
  const navigate = useNavigate();
  const { selectedApproach, selectApproach, getApproachInfo, allApproaches } = useApproach();
  const [isOpen, setIsOpen] = useState(false);
  const currentApproach = getApproachInfo();

  const getApproachIcon = (approachId) => {
    switch (approachId) {
      case 'rag':
        return <CloudIcon className="h-4 w-4" />;
      case 'elasticsearch':
        return <ServerIcon className="h-4 w-4" />;
      case 'firestore':
        return <CircleStackIcon className="h-4 w-4" />;
      default:
        return <CloudIcon className="h-4 w-4" />;
    }
  };

  const handleApproachChange = (approachId) => {
    selectApproach(approachId);
    setIsOpen(false);
    // Optional: Show a toast notification
    console.log(`[APPROACH] Switched to: ${approachId}`);
  };

  const handleChangeClick = () => {
    navigate('/select-approach');
  };

  return (
    <div className="relative">
      {/* Current Approach Display */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-100 hover:bg-gray-200 transition-colors text-sm"
      >
        <div className="flex items-center space-x-2">
          {getApproachIcon(selectedApproach)}
          <span className="font-medium text-gray-700">
            {currentApproach.name}
          </span>
        </div>
        <ChevronDownIcon className={`h-4 w-4 text-gray-500 transition-transform ${isOpen ? 'transform rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 rounded-lg shadow-lg bg-white ring-1 ring-black ring-opacity-5 z-50">
          <div className="py-1">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-200">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                Knowledge Base Approach
              </p>
            </div>

            {/* Approach Options */}
            <div className="py-2">
              {Object.values(allApproaches).map((approach) => (
                <button
                  key={approach.id}
                  onClick={() => handleApproachChange(approach.id)}
                  className={`
                    w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors
                    ${selectedApproach === approach.id ? 'bg-blue-50' : ''}
                  `}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      <div className={`
                        flex items-center justify-center w-8 h-8 rounded-full flex-shrink-0
                        ${selectedApproach === approach.id ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600'}
                      `}>
                        {getApproachIcon(approach.id)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          {approach.name}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {approach.description}
                        </p>
                      </div>
                    </div>
                    {selectedApproach === approach.id && (
                      <CheckIcon className="h-5 w-5 text-primary flex-shrink-0 ml-2" />
                    )}
                  </div>
                </button>
              ))}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
              <button
                onClick={handleChangeClick}
                className="w-full flex items-center justify-center space-x-2 text-sm text-primary hover:text-primary-dark font-medium"
              >
                <CogIcon className="h-4 w-4" />
                <span>View Full Comparison</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Overlay to close dropdown */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
};

export default ApproachIndicator;
