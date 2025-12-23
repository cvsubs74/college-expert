import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchStructuredProfile, updateProfileField } from '../services/api';
import {
    SparklesIcon,
    CheckCircleIcon,
    ArrowRightIcon,
    ArrowLeftIcon,
    ArrowPathIcon,
    PlusIcon,
    TrashIcon
} from '@heroicons/react/24/outline';

// ============================================================================
// COMPREHENSIVE ASSESSMENT SCHEMA - Matches PROFILE_SCHEMA from Manual Entry
// ============================================================================
const ASSESSMENT_SECTIONS = [
    {
        id: 'basics',
        label: 'Basic Info',
        icon: '👤',
        questions: [
            { key: 'name', label: 'Full Name', question: "What's your full name?", placeholder: 'Enter your full name', type: 'text', required: true },
            { key: 'grade', label: 'Current Grade', question: "What grade are you currently in?", type: 'select', options: ['9', '10', '11', '12'], required: true },
            { key: 'school', label: 'High School', question: "What high school do you attend?", placeholder: 'Enter your school name', type: 'text', required: true },
            { key: 'location', label: 'Location', question: "Where is your school located?", placeholder: 'City, State', type: 'text', required: false },
            { key: 'graduation_year', label: 'Graduation Year', question: "What year will you graduate?", placeholder: '2025', type: 'number', required: true },
            { key: 'intended_major', label: 'Intended Major', question: "What do you want to study in college?", placeholder: 'e.g., Computer Science, Psychology', type: 'text', required: false }
        ]
    },
    {
        id: 'academics',
        label: 'Academics',
        icon: '📊',
        questions: [
            { key: 'gpa_weighted', label: 'Weighted GPA', question: "What's your weighted GPA?", placeholder: 'e.g., 4.2', type: 'number', step: '0.01', required: true },
            { key: 'gpa_unweighted', label: 'Unweighted GPA', question: "What's your unweighted GPA?", placeholder: 'e.g., 3.85', type: 'number', step: '0.01', required: false },
            { key: 'gpa_uc', label: 'UC GPA', question: "What's your UC GPA (if applicable)?", placeholder: 'e.g., 4.5', type: 'number', step: '0.01', required: false },
            { key: 'class_rank', label: 'Class Rank', question: "What's your class rank?", placeholder: 'e.g., 15/400 or Top 10%', type: 'text', required: false }
        ]
    },
    {
        id: 'test_scores',
        label: 'Test Scores',
        icon: '📝',
        questions: [
            { key: 'sat_total', label: 'SAT Total', question: "What was your SAT total score?", placeholder: '400-1600', type: 'number', required: false },
            { key: 'sat_math', label: 'SAT Math', question: "What was your SAT Math score?", placeholder: '200-800', type: 'number', required: false },
            { key: 'sat_reading', label: 'SAT Reading/Writing', question: "What was your SAT Reading/Writing score?", placeholder: '200-800', type: 'number', required: false },
            { key: 'act_composite', label: 'ACT Composite', question: "What was your ACT composite score?", placeholder: '1-36', type: 'number', required: false }
        ]
    },
    {
        id: 'courses',
        label: 'Courses',
        icon: '📚',
        isArray: true,
        arrayKey: 'courses',
        intro: "Let's add your courses. You can add multiple.",
        itemFields: [
            { key: 'name', label: 'Course Name', placeholder: 'e.g., AP Calculus BC', type: 'text', required: true },
            { key: 'type', label: 'Course Type', type: 'select', options: ['Regular', 'Honors', 'AP', 'IB'], required: true },
            { key: 'grade_level', label: 'Grade Level', type: 'select', options: ['9', '10', '11', '12'], required: true }
        ]
    },
    {
        id: 'ap_exams',
        label: 'AP Exams',
        icon: '🎯',
        isArray: true,
        arrayKey: 'ap_exams',
        intro: "Add your AP exam scores.",
        itemFields: [
            { key: 'subject', label: 'Subject', placeholder: 'e.g., AP Chemistry', type: 'text', required: true },
            { key: 'score', label: 'Score (1-5)', type: 'number', min: 1, max: 5, required: true }
        ]
    },
    {
        id: 'activities',
        label: 'Activities',
        icon: '🏆',
        isArray: true,
        arrayKey: 'extracurriculars',
        intro: "Add your extracurricular activities with details.",
        itemFields: [
            { key: 'name', label: 'Activity Name', placeholder: 'e.g., Varsity Soccer', type: 'text', required: true },
            { key: 'role', label: 'Your Role', placeholder: 'e.g., Team Captain', type: 'text', required: false },
            { key: 'grades', label: 'Years Active', placeholder: 'e.g., 9,10,11,12', type: 'text', required: false },
            { key: 'hours_per_week', label: 'Hours/Week', placeholder: 'e.g., 10', type: 'number', required: false },
            { key: 'description', label: 'Description', placeholder: 'Briefly describe your involvement...', type: 'textarea', required: false }
        ]
    },
    {
        id: 'awards',
        label: 'Awards',
        icon: '🏅',
        isArray: true,
        arrayKey: 'awards',
        intro: "Add your awards and honors.",
        itemFields: [
            { key: 'name', label: 'Award Name', placeholder: 'e.g., National Merit Semifinalist', type: 'text', required: true },
            { key: 'grade', label: 'Grade Level', type: 'select', options: ['9', '10', '11', '12'], required: false },
            { key: 'level', label: 'Recognition Level', type: 'select', options: ['School', 'Regional', 'State', 'National', 'International'], required: false }
        ]
    }
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================
const GuidedInterview = ({ profile: parentProfile, onProfileUpdate }) => {
    const { currentUser } = useAuth();
    const [loading, setLoading] = useState(true);
    const [sectionIndex, setSectionIndex] = useState(0);
    const [questionIndex, setQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState({});
    const [arrayItems, setArrayItems] = useState({});
    const [currentArrayItem, setCurrentArrayItem] = useState({});
    const [saving, setSaving] = useState(false);
    const initialized = useRef(false);

    const currentSection = ASSESSMENT_SECTIONS[sectionIndex];
    const isArraySection = currentSection?.isArray;

    // Track original values to detect changes
    const originalProfile = useRef({});

    // Initialize only once
    useEffect(() => {
        if (currentUser?.email && !initialized.current) {
            initialized.current = true;
            initializeFromProfile(parentProfile || {});
            setLoading(false);
        }
    }, [currentUser, parentProfile]);

    const initializeFromProfile = (profileData) => {
        const existingAnswers = {};
        const existingArrayItems = {};
        const originals = {};

        ASSESSMENT_SECTIONS.forEach(section => {
            if (section.isArray) {
                existingArrayItems[section.arrayKey] = profileData[section.arrayKey] || [];
                // Store original array length for comparison
                originals[section.arrayKey] = JSON.stringify(profileData[section.arrayKey] || []);
            } else {
                section.questions.forEach(q => {
                    const value = profileData[q.key];
                    if (value !== undefined && value !== null && value !== '') {
                        existingAnswers[q.key] = value;
                    }
                    // Store original value (even if empty)
                    originals[q.key] = value;
                });
            }
        });

        setAnswers(existingAnswers);
        setArrayItems(existingArrayItems);
        originalProfile.current = originals;
        console.log('[GuidedInterview] Initialized from profile, tracking originals for change detection');
    };

    const handleAnswerChange = (key, value) => {
        setAnswers(prev => ({ ...prev, [key]: value }));
    };

    const handleArrayFieldChange = (key, value) => {
        setCurrentArrayItem(prev => ({ ...prev, [key]: value }));
    };

    const saveCurrentAnswer = async () => {
        if (!currentSection || isArraySection) return true;

        const question = currentSection.questions[questionIndex];
        const answer = answers[question.key];

        if (!answer && question.required) return false;
        if (!answer) return true;

        // OPTIMIZATION: Check if value actually changed from original
        const originalValue = originalProfile.current[question.key];
        let newValue = answer;
        if (question.type === 'number' && newValue) {
            newValue = parseFloat(newValue);
        }

        // Compare values - skip API call if unchanged
        const originalNum = question.type === 'number' && originalValue ? parseFloat(originalValue) : originalValue;
        if (newValue === originalNum || String(newValue) === String(originalValue)) {
            console.log(`[GuidedInterview] Skipping save for ${question.key} - value unchanged`);
            return true; // No change, skip API call
        }

        console.log(`[GuidedInterview] Saving ${question.key}: ${originalValue} → ${newValue}`);
        setSaving(true);
        try {
            await updateProfileField(currentUser.email, question.key, newValue, 'set');
            // Update original value after successful save
            originalProfile.current[question.key] = newValue;
            if (onProfileUpdate) await onProfileUpdate();
            return true;
        } catch (e) {
            console.error('Failed to save:', e);
            return false;
        } finally {
            setSaving(false);
        }
    };

    const addArrayItem = async () => {
        if (!currentSection?.isArray) return;

        const requiredFields = currentSection.itemFields.filter(f => f.required);
        const hasRequired = requiredFields.every(f => currentArrayItem[f.key]);

        if (!hasRequired) return;

        setSaving(true);
        try {
            await updateProfileField(currentUser.email, currentSection.arrayKey, currentArrayItem, 'append');
            setArrayItems(prev => ({
                ...prev,
                [currentSection.arrayKey]: [...(prev[currentSection.arrayKey] || []), currentArrayItem]
            }));
            setCurrentArrayItem({});
            if (onProfileUpdate) await onProfileUpdate();
        } catch (e) {
            console.error('Failed to add item:', e);
        } finally {
            setSaving(false);
        }
    };

    const removeArrayItem = async (index) => {
        if (!currentSection?.isArray) return;

        const itemToRemove = arrayItems[currentSection.arrayKey]?.[index];
        if (!itemToRemove) return;

        setSaving(true);
        try {
            // Remove from backend using 'remove' operation (matches by name/subject field)
            // This is safer than index-based removal in case of stale data
            await updateProfileField(currentUser.email, currentSection.arrayKey, itemToRemove, 'remove');

            // Update local state
            setArrayItems(prev => ({
                ...prev,
                [currentSection.arrayKey]: (prev[currentSection.arrayKey] || []).filter((_, i) => i !== index)
            }));

            console.log(`[GuidedInterview] Removed item from ${currentSection.arrayKey}:`, itemToRemove.name || itemToRemove.subject);
            if (onProfileUpdate) await onProfileUpdate();
        } catch (e) {
            console.error('Failed to remove item:', e);
        } finally {
            setSaving(false);
        }
    };

    const handleNext = async () => {
        if (isArraySection) {
            // Move to next section
            if (sectionIndex < ASSESSMENT_SECTIONS.length - 1) {
                setSectionIndex(sectionIndex + 1);
                setQuestionIndex(0);
                setCurrentArrayItem({});
            }
        } else {
            const saved = await saveCurrentAnswer();
            if (!saved) return;

            if (questionIndex < currentSection.questions.length - 1) {
                setQuestionIndex(questionIndex + 1);
            } else if (sectionIndex < ASSESSMENT_SECTIONS.length - 1) {
                setSectionIndex(sectionIndex + 1);
                setQuestionIndex(0);
            }
        }
    };

    const handlePrevious = () => {
        if (isArraySection) {
            if (sectionIndex > 0) {
                setSectionIndex(sectionIndex - 1);
                const prevSection = ASSESSMENT_SECTIONS[sectionIndex - 1];
                if (prevSection.isArray) {
                    setQuestionIndex(0);
                } else {
                    setQuestionIndex(prevSection.questions.length - 1);
                }
            }
        } else {
            if (questionIndex > 0) {
                setQuestionIndex(questionIndex - 1);
            } else if (sectionIndex > 0) {
                setSectionIndex(sectionIndex - 1);
                const prevSection = ASSESSMENT_SECTIONS[sectionIndex - 1];
                if (prevSection.isArray) {
                    setQuestionIndex(0);
                } else {
                    setQuestionIndex(prevSection.questions.length - 1);
                }
            }
        }
    };

    const jumpToSection = (idx) => {
        setSectionIndex(idx);
        setQuestionIndex(0);
        setCurrentArrayItem({});
    };

    // Calculate progress
    const totalQuestions = ASSESSMENT_SECTIONS.reduce((sum, s) => sum + (s.isArray ? 1 : s.questions.length), 0);
    const currentQuestionNum = ASSESSMENT_SECTIONS.slice(0, sectionIndex).reduce((sum, s) => sum + (s.isArray ? 1 : s.questions.length), 0) + (isArraySection ? 1 : questionIndex + 1);
    const answeredCount = Object.keys(answers).filter(k => answers[k]).length;

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[500px]">
                <ArrowPathIcon className="h-8 w-8 text-[#1A4D2E] animate-spin" />
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[600px]">
            {/* Section Navigation */}
            <div className="p-4 border-b border-[#E0DED8] bg-[#FDFCF7]">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-[#1A4D2E]" />
                        <h2 className="text-sm font-semibold text-gray-900">Profile Assessment</h2>
                    </div>
                    <span className="text-xs font-medium text-[#1A4D2E] bg-[#D6E8D5] px-2 py-1 rounded-full">
                        {currentQuestionNum} / {totalQuestions}
                    </span>
                </div>

                {/* Section Tabs */}
                <div className="flex gap-1 overflow-x-auto pb-1">
                    {ASSESSMENT_SECTIONS.map((section, idx) => (
                        <button
                            key={section.id}
                            onClick={() => jumpToSection(idx)}
                            className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${idx === sectionIndex
                                ? 'bg-[#1A4D2E] text-white'
                                : idx < sectionIndex
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            <span>{section.icon}</span>
                            <span className="hidden sm:inline">{section.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Question Content */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-lg mx-auto">
                    {isArraySection ? (
                        // Array Section (Courses, Activities, Awards, AP Exams)
                        <div>
                            <div className="text-center mb-4">
                                <span className="text-3xl mb-2 block">{currentSection.icon}</span>
                                <h3 className="text-lg font-bold text-gray-900">{currentSection.label}</h3>
                                <p className="text-sm text-gray-500 mt-1">{currentSection.intro}</p>
                            </div>

                            {/* Existing Items */}
                            {(arrayItems[currentSection.arrayKey] || []).length > 0 && (
                                <div className="mb-4 space-y-2">
                                    <p className="text-xs font-medium text-gray-500">Added items:</p>
                                    {(arrayItems[currentSection.arrayKey] || []).map((item, idx) => (
                                        <div key={idx} className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-3 py-2 group">
                                            <span className="text-sm text-green-800 font-medium">
                                                {item.name || item.subject || 'Item ' + (idx + 1)}
                                            </span>
                                            <button
                                                onClick={() => removeArrayItem(idx)}
                                                disabled={saving}
                                                className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                                                title="Remove"
                                            >
                                                <TrashIcon className="h-4 w-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Add New Item Form */}
                            <div className="border border-gray-200 rounded-xl p-4 bg-white">
                                <p className="text-xs font-medium text-gray-500 mb-3">Add {currentSection.label.toLowerCase().replace(/s$/, '')}:</p>
                                <div className="space-y-3">
                                    {currentSection.itemFields.map(field => (
                                        <div key={field.key}>
                                            <label className="block text-xs font-medium text-gray-600 mb-1">
                                                {field.label} {field.required && <span className="text-red-500">*</span>}
                                            </label>
                                            {field.type === 'select' ? (
                                                <select
                                                    value={currentArrayItem[field.key] || ''}
                                                    onChange={(e) => handleArrayFieldChange(field.key, e.target.value)}
                                                    className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 ${currentArrayItem[field.key] ? 'border-purple-300 bg-purple-50' : 'border-gray-200'
                                                        }`}
                                                >
                                                    <option value="">Select...</option>
                                                    {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                                </select>
                                            ) : field.type === 'textarea' ? (
                                                <textarea
                                                    value={currentArrayItem[field.key] || ''}
                                                    onChange={(e) => handleArrayFieldChange(field.key, e.target.value)}
                                                    placeholder={field.placeholder}
                                                    rows={2}
                                                    className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 ${currentArrayItem[field.key] ? 'border-purple-300 bg-purple-50' : 'border-gray-200'
                                                        }`}
                                                />
                                            ) : (
                                                <input
                                                    type={field.type}
                                                    value={currentArrayItem[field.key] || ''}
                                                    onChange={(e) => handleArrayFieldChange(field.key, e.target.value)}
                                                    placeholder={field.placeholder}
                                                    className={`w-full px-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 ${currentArrayItem[field.key] ? 'border-purple-300 bg-purple-50' : 'border-gray-200'
                                                        }`}
                                                />
                                            )}
                                        </div>
                                    ))}
                                </div>
                                <button
                                    onClick={addArrayItem}
                                    disabled={saving || !currentSection.itemFields.filter(f => f.required).every(f => currentArrayItem[f.key])}
                                    className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg hover:bg-[#2D6B45] disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {saving ? <ArrowPathIcon className="h-4 w-4 animate-spin" /> : <PlusIcon className="h-4 w-4" />}
                                    Add {currentSection.label.replace(/s$/, '')}
                                </button>
                            </div>
                        </div>
                    ) : (
                        // Scalar Question
                        <div className="text-center">
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-[#D6E8D5] text-[#1A4D2E] mb-3">
                                {currentSection.questions[questionIndex].label}
                                {!currentSection.questions[questionIndex].required && <span className="ml-1 opacity-70">(Optional)</span>}
                            </span>
                            <h3 className="text-xl font-bold text-gray-900 mb-6">
                                {currentSection.questions[questionIndex].question}
                            </h3>

                            {currentSection.questions[questionIndex].type === 'select' ? (
                                <div className="grid grid-cols-2 gap-2">
                                    {currentSection.questions[questionIndex].options.map(opt => {
                                        const isSelected = String(answers[currentSection.questions[questionIndex].key]) === String(opt);
                                        return (
                                            <button
                                                key={opt}
                                                onClick={() => handleAnswerChange(currentSection.questions[questionIndex].key, opt)}
                                                className={`p-3 rounded-xl border-2 text-sm font-medium transition-all ${isSelected
                                                    ? 'border-purple-500 bg-[#D6E8D5] text-[#1A4D2E]'
                                                    : 'border-gray-200 hover:border-purple-300 text-gray-700'
                                                    }`}
                                            >
                                                {opt === '9' ? '9th Grade' : opt === '10' ? '10th Grade' : opt === '11' ? '11th Grade' : opt === '12' ? '12th Grade' : opt}
                                            </button>
                                        );
                                    })}
                                </div>
                            ) : (
                                <input
                                    type={currentSection.questions[questionIndex].type}
                                    value={answers[currentSection.questions[questionIndex].key] || ''}
                                    onChange={(e) => handleAnswerChange(currentSection.questions[questionIndex].key, e.target.value)}
                                    placeholder={currentSection.questions[questionIndex].placeholder}
                                    step={currentSection.questions[questionIndex].step}
                                    className="w-full px-4 py-3 text-sm border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-purple-500 text-center"
                                    onKeyDown={(e) => e.key === 'Enter' && handleNext()}
                                />
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Navigation */}
            <div className="p-4 border-t border-gray-100 bg-gray-50">
                <div className="flex items-center justify-between max-w-lg mx-auto">
                    <button
                        onClick={handlePrevious}
                        disabled={sectionIndex === 0 && questionIndex === 0}
                        className={`flex items-center gap-1 px-4 py-2 rounded-xl text-sm font-medium transition-all ${sectionIndex === 0 && questionIndex === 0
                            ? 'text-gray-300 cursor-not-allowed'
                            : 'text-gray-600 hover:bg-gray-200'
                            }`}
                    >
                        <ArrowLeftIcon className="h-4 w-4" />
                        Back
                    </button>

                    <span className="text-xs text-gray-500">{answeredCount} answered</span>

                    <button
                        onClick={handleNext}
                        disabled={saving}
                        className="flex items-center gap-1 px-4 py-2 bg-[#1A4D2E] text-white rounded-xl text-sm font-medium hover:bg-[#2D6B45] disabled:opacity-50"
                    >
                        {saving ? (
                            <ArrowPathIcon className="h-4 w-4 animate-spin" />
                        ) : sectionIndex === ASSESSMENT_SECTIONS.length - 1 && (isArraySection || questionIndex === currentSection.questions.length - 1) ? (
                            <>
                                Complete
                                <CheckCircleIcon className="h-4 w-4" />
                            </>
                        ) : (
                            <>
                                Next
                                <ArrowRightIcon className="h-4 w-4" />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default GuidedInterview;
