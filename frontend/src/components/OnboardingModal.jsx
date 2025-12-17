import React, { useState, useEffect } from 'react';
import { XMarkIcon, ArrowRightIcon, ArrowLeftIcon, SparklesIcon, AcademicCapIcon, HeartIcon, MapPinIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon } from '@heroicons/react/24/solid';

// US States for dropdown
const US_STATES = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
    'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
    'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
    'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
    'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
    'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
    'Wisconsin', 'Wyoming'
];

// Common majors
const POPULAR_MAJORS = [
    'Computer Science', 'Business', 'Engineering', 'Biology', 'Psychology',
    'Economics', 'Communications', 'Pre-Med', 'Political Science', 'Mathematics',
    'Chemistry', 'English', 'History', 'Nursing', 'Architecture'
];

// Activity categories  
const ACTIVITY_TYPES = [
    'Sports', 'Music/Arts', 'Academic Club', 'Volunteer', 'Work Experience',
    'Student Government', 'STEM Club', 'Debate/Speech', 'Religious', 'Other'
];

const OnboardingModal = ({ isOpen, onComplete, onSkip, userEmail }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [isAnimating, setIsAnimating] = useState(false);

    // Form data across all steps
    const [formData, setFormData] = useState({
        // Step 1: Basics
        name: '',
        grade: '',
        state: '',
        highSchool: '',

        // Step 2: Academics
        gpa: '',
        satScore: '',
        actScore: '',
        apCourses: 0,

        // Step 3: Interests
        majors: [],
        topActivity: '',
        activityType: '',

        // Step 4: Preferences
        preferredLocations: [],
        schoolSize: '',
        campusType: ''
    });

    const totalSteps = 4;

    const updateFormData = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleNext = () => {
        if (currentStep < totalSteps - 1) {
            setIsAnimating(true);
            setTimeout(() => {
                setCurrentStep(prev => prev + 1);
                setIsAnimating(false);
            }, 200);
        } else {
            // Complete onboarding
            handleComplete();
        }
    };

    const handleBack = () => {
        if (currentStep > 0) {
            setIsAnimating(true);
            setTimeout(() => {
                setCurrentStep(prev => prev - 1);
                setIsAnimating(false);
            }, 200);
        }
    };

    const handleComplete = async () => {
        // Transform form data to profile structure
        const profileData = {
            student_info: {
                name: formData.name,
                email: userEmail,
                grade: formData.grade,
                high_school: formData.highSchool,
                state: formData.state
            },
            academic_profile: {
                gpa: {
                    weighted: parseFloat(formData.gpa) || null
                },
                test_scores: {
                    sat: formData.satScore ? { composite: parseInt(formData.satScore) } : null,
                    act: formData.actScore ? { composite: parseInt(formData.actScore) } : null
                },
                ap_courses: formData.apCourses
            },
            interests: {
                intended_majors: formData.majors,
                top_activity: formData.topActivity,
                activity_type: formData.activityType
            },
            preferences: {
                preferred_locations: formData.preferredLocations,
                school_size: formData.schoolSize,
                campus_type: formData.campusType
            },
            onboarding_status: 'completed',
            onboarding_completed_at: new Date().toISOString()
        };

        onComplete(profileData);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleNext();
        }
    };

    const toggleMajor = (major) => {
        setFormData(prev => {
            const current = prev.majors || [];
            if (current.includes(major)) {
                return { ...prev, majors: current.filter(m => m !== major) };
            } else if (current.length < 3) {
                return { ...prev, majors: [...current, major] };
            }
            return prev;
        });
    };

    const toggleLocation = (location) => {
        setFormData(prev => {
            const current = prev.preferredLocations || [];
            if (current.includes(location)) {
                return { ...prev, preferredLocations: current.filter(l => l !== location) };
            } else {
                return { ...prev, preferredLocations: [...current, location] };
            }
        });
    };

    // Get fit preview based on GPA
    const getFitPreview = () => {
        const gpa = parseFloat(formData.gpa);
        if (!gpa) return null;

        if (gpa >= 3.9) {
            return { level: 'Highly Competitive', targets: 'Top 20 universities', color: 'text-purple-600' };
        } else if (gpa >= 3.7) {
            return { level: 'Competitive', targets: 'Top 50 universities', color: 'text-blue-600' };
        } else if (gpa >= 3.4) {
            return { level: 'Solid', targets: 'Target schools', color: 'text-green-600' };
        } else {
            return { level: 'Building', targets: 'Many great options', color: 'text-amber-600' };
        }
    };

    if (!isOpen) return null;

    const stepIcons = [
        <SparklesIcon className="h-6 w-6" />,
        <AcademicCapIcon className="h-6 w-6" />,
        <HeartIcon className="h-6 w-6" />,
        <MapPinIcon className="h-6 w-6" />
    ];

    const stepTitles = [
        "Let's get started",
        "Your academics",
        "Your interests",
        "Your preferences"
    ];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-gradient-to-br from-amber-900/20 via-gray-900/60 to-orange-900/20 backdrop-blur-sm" />

            {/* Modal */}
            <div className={`relative w-full max-w-2xl mx-4 bg-white rounded-3xl shadow-2xl overflow-hidden transition-all duration-300 ${isAnimating ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}>
                {/* Progress dots */}
                <div className="absolute top-6 left-1/2 -translate-x-1/2 flex items-center gap-2">
                    {[...Array(totalSteps)].map((_, i) => (
                        <div
                            key={i}
                            className={`h-2 rounded-full transition-all duration-300 ${i === currentStep
                                    ? 'w-8 bg-gradient-to-r from-amber-500 to-orange-500'
                                    : i < currentStep
                                        ? 'w-2 bg-amber-400'
                                        : 'w-2 bg-gray-200'
                                }`}
                        />
                    ))}
                </div>

                {/* Content */}
                <div className="pt-16 pb-8 px-8" onKeyDown={handleKeyDown}>
                    {/* Step header */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 text-amber-600 mb-4">
                            {stepIcons[currentStep]}
                        </div>
                        <h2 className="text-2xl font-bold text-gray-900">{stepTitles[currentStep]}</h2>
                    </div>

                    {/* Step 1: Basics */}
                    {currentStep === 0 && (
                        <div className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Your name</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => updateFormData('name', e.target.value)}
                                    placeholder="Enter your full name"
                                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all"
                                    autoFocus
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Current grade</label>
                                <div className="grid grid-cols-4 gap-3">
                                    {['Freshman', 'Sophomore', 'Junior', 'Senior'].map(grade => (
                                        <button
                                            key={grade}
                                            onClick={() => updateFormData('grade', grade)}
                                            className={`py-3 px-4 rounded-xl border-2 text-sm font-medium transition-all ${formData.grade === grade
                                                    ? 'border-amber-500 bg-amber-50 text-amber-700'
                                                    : 'border-gray-200 text-gray-600 hover:border-amber-200'
                                                }`}
                                        >
                                            {grade}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">High school</label>
                                    <input
                                        type="text"
                                        value={formData.highSchool}
                                        onChange={(e) => updateFormData('highSchool', e.target.value)}
                                        placeholder="School name"
                                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">State</label>
                                    <select
                                        value={formData.state}
                                        onChange={(e) => updateFormData('state', e.target.value)}
                                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    >
                                        <option value="">Select state</option>
                                        {US_STATES.map(state => (
                                            <option key={state} value={state}>{state}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 2: Academics */}
                    {currentStep === 1 && (
                        <div className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Current GPA (Weighted)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    max="5"
                                    value={formData.gpa}
                                    onChange={(e) => updateFormData('gpa', e.target.value)}
                                    placeholder="e.g., 3.85"
                                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    autoFocus
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">SAT Score <span className="text-gray-400">(optional)</span></label>
                                    <input
                                        type="number"
                                        min="400"
                                        max="1600"
                                        value={formData.satScore}
                                        onChange={(e) => updateFormData('satScore', e.target.value)}
                                        placeholder="e.g., 1450"
                                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">ACT Score <span className="text-gray-400">(optional)</span></label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="36"
                                        value={formData.actScore}
                                        onChange={(e) => updateFormData('actScore', e.target.value)}
                                        placeholder="e.g., 32"
                                        className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">AP/IB Courses Taken</label>
                                <div className="flex items-center gap-4">
                                    <input
                                        type="range"
                                        min="0"
                                        max="15"
                                        value={formData.apCourses}
                                        onChange={(e) => updateFormData('apCourses', parseInt(e.target.value))}
                                        className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
                                    />
                                    <span className="w-12 text-center font-semibold text-amber-600">{formData.apCourses}</span>
                                </div>
                            </div>

                            {/* Instant gratification preview */}
                            {formData.gpa && getFitPreview() && (
                                <div className="mt-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl border border-amber-100">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-white rounded-xl shadow-sm">
                                            <SparklesIcon className="h-5 w-5 text-amber-500" />
                                        </div>
                                        <div>
                                            <p className="text-sm text-gray-600">With your profile, you're</p>
                                            <p className={`font-semibold ${getFitPreview().color}`}>
                                                {getFitPreview().level} for {getFitPreview().targets}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Step 3: Interests */}
                    {currentStep === 2 && (
                        <div className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Intended major(s) <span className="text-gray-400">(select up to 3)</span>
                                </label>
                                <div className="flex flex-wrap gap-2">
                                    {POPULAR_MAJORS.map(major => (
                                        <button
                                            key={major}
                                            onClick={() => toggleMajor(major)}
                                            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${formData.majors.includes(major)
                                                    ? 'bg-amber-500 text-white shadow-md'
                                                    : 'bg-gray-100 text-gray-600 hover:bg-amber-100'
                                                }`}
                                        >
                                            {formData.majors.includes(major) && <CheckCircleIcon className="inline h-4 w-4 mr-1" />}
                                            {major}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Top extracurricular activity</label>
                                <input
                                    type="text"
                                    value={formData.topActivity}
                                    onChange={(e) => updateFormData('topActivity', e.target.value)}
                                    placeholder="e.g., Debate Team Captain, Volunteer Coordinator"
                                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Activity type</label>
                                <div className="flex flex-wrap gap-2">
                                    {ACTIVITY_TYPES.map(type => (
                                        <button
                                            key={type}
                                            onClick={() => updateFormData('activityType', type)}
                                            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${formData.activityType === type
                                                    ? 'bg-amber-500 text-white shadow-md'
                                                    : 'bg-gray-100 text-gray-600 hover:bg-amber-100'
                                                }`}
                                        >
                                            {type}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 4: Preferences */}
                    {currentStep === 3 && (
                        <div className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Preferred regions</label>
                                <div className="flex flex-wrap gap-2">
                                    {['Northeast', 'Southeast', 'Midwest', 'Southwest', 'West Coast', 'No Preference'].map(region => (
                                        <button
                                            key={region}
                                            onClick={() => toggleLocation(region)}
                                            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${formData.preferredLocations.includes(region)
                                                    ? 'bg-amber-500 text-white shadow-md'
                                                    : 'bg-gray-100 text-gray-600 hover:bg-amber-100'
                                                }`}
                                        >
                                            {formData.preferredLocations.includes(region) && <CheckCircleIcon className="inline h-4 w-4 mr-1" />}
                                            {region}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">School size preference</label>
                                <div className="grid grid-cols-4 gap-3">
                                    {[
                                        { value: 'small', label: 'Small', desc: '<5,000' },
                                        { value: 'medium', label: 'Medium', desc: '5-15k' },
                                        { value: 'large', label: 'Large', desc: '15-30k' },
                                        { value: 'any', label: 'Any', desc: 'No pref' }
                                    ].map(size => (
                                        <button
                                            key={size.value}
                                            onClick={() => updateFormData('schoolSize', size.value)}
                                            className={`py-3 px-2 rounded-xl border-2 text-center transition-all ${formData.schoolSize === size.value
                                                    ? 'border-amber-500 bg-amber-50'
                                                    : 'border-gray-200 hover:border-amber-200'
                                                }`}
                                        >
                                            <div className="text-sm font-medium text-gray-700">{size.label}</div>
                                            <div className="text-xs text-gray-400">{size.desc}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Campus setting</label>
                                <div className="grid grid-cols-4 gap-3">
                                    {['Urban', 'Suburban', 'Rural', 'Any'].map(type => (
                                        <button
                                            key={type}
                                            onClick={() => updateFormData('campusType', type)}
                                            className={`py-3 px-4 rounded-xl border-2 text-sm font-medium transition-all ${formData.campusType === type
                                                    ? 'border-amber-500 bg-amber-50 text-amber-700'
                                                    : 'border-gray-200 text-gray-600 hover:border-amber-200'
                                                }`}
                                        >
                                            {type}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Navigation buttons */}
                    <div className="mt-8 flex items-center justify-between">
                        <div>
                            {currentStep > 0 && (
                                <button
                                    onClick={handleBack}
                                    className="flex items-center gap-2 px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors"
                                >
                                    <ArrowLeftIcon className="h-4 w-4" />
                                    Back
                                </button>
                            )}
                        </div>

                        <button
                            onClick={handleNext}
                            className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold rounded-xl shadow-lg shadow-amber-200 hover:shadow-xl hover:shadow-amber-300 transition-all"
                        >
                            {currentStep === totalSteps - 1 ? 'Complete Setup' : 'Continue'}
                            <ArrowRightIcon className="h-4 w-4" />
                        </button>
                    </div>

                    {/* Skip link */}
                    <div className="mt-6 text-center">
                        <button
                            onClick={onSkip}
                            className="text-sm text-gray-400 hover:text-gray-600 underline-offset-2 hover:underline transition-colors"
                        >
                            Skip for now — I'll explore first
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OnboardingModal;
