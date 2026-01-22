import React, { useState } from 'react';
import { PencilSquareIcon, AcademicCapIcon } from '@heroicons/react/24/outline';
import EssayDashboard from './EssayDashboard';
import ScholarshipTracker from './ScholarshipTracker';

/**
 * ProgressPage - Combined view for Essays and Scholarships tracking
 * 
 * - Essays: Auto-populated prompts from college list, grouped by type
 * - Scholarships: Available scholarships from college list with eligibility
 */
const ProgressPage = () => {
    const [activeTab, setActiveTab] = useState('essays');

    const tabs = [
        { id: 'essays', label: 'Essays', icon: PencilSquareIcon },
        { id: 'scholarships', label: 'Scholarships', icon: AcademicCapIcon },
    ];

    return (
        <div className="min-h-screen">
            {/* Page Header */}
            <div className="mb-6">
                <h1 className="font-serif text-3xl font-bold text-[#2C2C2C]">
                    My Progress
                </h1>
                <p className="text-[#6B6B6B] mt-1">
                    Track essays and scholarships across your colleges
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="border-b border-[#E0DED8] mb-6">
                <nav className="flex gap-1">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all relative
                                ${activeTab === tab.id
                                    ? 'text-[#1A4D2E]'
                                    : 'text-[#6B6B6B] hover:text-[#4A4A4A]'
                                }`}
                        >
                            <tab.icon className="w-5 h-5" />
                            {tab.label}
                            {/* Active indicator */}
                            {activeTab === tab.id && (
                                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#1A4D2E] rounded-full" />
                            )}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Tab Content */}
            <div className="animate-fade-up">
                {activeTab === 'essays' && <EssayDashboard embedded />}
                {activeTab === 'scholarships' && <ScholarshipTracker embedded />}
            </div>
        </div>
    );
};

export default ProgressPage;

