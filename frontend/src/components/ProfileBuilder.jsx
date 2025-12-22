import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchStructuredProfile, updateProfileField, uploadStudentProfile, listStudentProfiles, deleteStudentProfile } from '../services/api';
import {
    CloudArrowUpIcon,
    CheckCircleIcon,
    ExclamationTriangleIcon,
    ChevronDownIcon,
    ChevronRightIcon,
    PencilIcon,
    XMarkIcon,
    PlusIcon,
    TrashIcon,
    DocumentTextIcon,
    ArrowPathIcon
} from '@heroicons/react/24/outline';

// Schema definition - maps to Elasticsearch fields
const PROFILE_SCHEMA = {
    basics: {
        label: 'Basics',
        icon: '👤',
        fields: [
            { key: 'name', label: 'Full Name', type: 'text', required: true },
            { key: 'grade', label: 'Current Grade', type: 'select', options: ['9', '10', '11', '12'], required: true },
            { key: 'school', label: 'High School', type: 'text', required: true },
            { key: 'location', label: 'City, State', type: 'text', required: false },
            { key: 'graduation_year', label: 'Graduation Year', type: 'number', required: true },
            { key: 'intended_major', label: 'Intended Major', type: 'text', required: false }
        ]
    },
    academics: {
        label: 'Academics',
        icon: '📊',
        fields: [
            { key: 'gpa_weighted', label: 'Weighted GPA', type: 'number', step: '0.01', required: true },
            { key: 'gpa_unweighted', label: 'Unweighted GPA', type: 'number', step: '0.01', required: false },
            { key: 'gpa_uc', label: 'UC GPA', type: 'number', step: '0.01', required: false },
            { key: 'class_rank', label: 'Class Rank', type: 'text', placeholder: 'e.g., 15/400', required: false }
        ]
    },
    testScores: {
        label: 'Test Scores',
        icon: '📝',
        fields: [
            { key: 'sat_total', label: 'SAT Total', type: 'number', min: 400, max: 1600, required: false },
            { key: 'sat_math', label: 'SAT Math', type: 'number', min: 200, max: 800, required: false },
            { key: 'sat_reading', label: 'SAT Reading/Writing', type: 'number', min: 200, max: 800, required: false },
            { key: 'act_composite', label: 'ACT Composite', type: 'number', min: 1, max: 36, required: false }
        ]
    },
    courses: {
        label: 'Courses',
        icon: '📚',
        isArray: true,
        arrayKey: 'courses',
        itemSchema: [
            { key: 'name', label: 'Course Name', type: 'text', required: true },
            { key: 'type', label: 'Type', type: 'select', options: ['Regular', 'Honors', 'AP', 'IB'], required: true },
            { key: 'grade_level', label: 'Grade Level', type: 'select', options: ['9', '10', '11', '12'], required: true },
            { key: 'semester1_grade', label: 'Sem 1 Grade', type: 'text', required: false },
            { key: 'semester2_grade', label: 'Sem 2 Grade', type: 'text', required: false }
        ]
    },
    apExams: {
        label: 'AP Exams',
        icon: '🎯',
        isArray: true,
        arrayKey: 'ap_exams',
        itemSchema: [
            { key: 'subject', label: 'Subject', type: 'text', required: true },
            { key: 'score', label: 'Score (1-5)', type: 'number', min: 1, max: 5, required: true }
        ]
    },
    activities: {
        label: 'Activities',
        icon: '🏆',
        isArray: true,
        arrayKey: 'extracurriculars',
        itemSchema: [
            { key: 'name', label: 'Activity Name', type: 'text', required: true },
            { key: 'role', label: 'Role/Position', type: 'text', required: false },
            { key: 'grades', label: 'Years (e.g., 9,10,11)', type: 'text', required: false },
            { key: 'hours_per_week', label: 'Hours/Week', type: 'number', required: false },
            { key: 'description', label: 'Description', type: 'textarea', required: false }
        ]
    },
    awards: {
        label: 'Awards & Honors',
        icon: '🏅',
        isArray: true,
        arrayKey: 'awards',
        itemSchema: [
            { key: 'name', label: 'Award Name', type: 'text', required: true },
            { key: 'grade', label: 'Grade Level', type: 'select', options: ['9', '10', '11', '12'], required: false },
            { key: 'level', label: 'Level', type: 'select', options: ['School', 'Regional', 'State', 'National', 'International'], required: false }
        ]
    }
};

// Completion Calculator
const calculateCompletion = (profile) => {
    if (!profile) return { percentage: 0, missing: [], filled: 0, total: 0 };

    let filled = 0;
    let total = 0;
    const missing = [];

    Object.entries(PROFILE_SCHEMA).forEach(([sectionKey, section]) => {
        if (section.isArray) {
            const items = profile[section.arrayKey] || [];
            if (items.length > 0) filled++;
            total++;
            if (items.length === 0) missing.push(section.label);
        } else {
            section.fields.forEach(field => {
                if (field.required) {
                    total++;
                    if (profile[field.key] !== undefined && profile[field.key] !== null && profile[field.key] !== '') {
                        filled++;
                    } else {
                        missing.push(field.label);
                    }
                }
            });
        }
    });

    return {
        percentage: total > 0 ? Math.round((filled / total) * 100) : 0,
        missing,
        filled,
        total
    };
};

// Progress Bar Component
const CompletionProgress = ({ profile }) => {
    const { percentage, missing } = calculateCompletion(profile);

    const getColor = () => {
        if (percentage >= 80) return 'bg-green-500';
        if (percentage >= 50) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    return (
        <div className="bg-white rounded-xl p-4 border border-gray-200 mb-6">
            <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Profile Completion</span>
                <span className={`text-sm font-bold ${percentage >= 80 ? 'text-green-600' : percentage >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {percentage}%
                </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div className={`h-2.5 rounded-full transition-all duration-500 ${getColor()}`} style={{ width: `${percentage}%` }}></div>
            </div>
            {missing.length > 0 && percentage < 100 && (
                <p className="mt-2 text-xs text-gray-500">
                    Missing: {missing.slice(0, 3).join(', ')}{missing.length > 3 && ` +${missing.length - 3} more`}
                </p>
            )}
        </div>
    );
};

// Section Accordion Component
const ProfileSection = ({ sectionKey, section, profile, onUpdate, expandedSections, toggleSection }) => {
    const isExpanded = expandedSections.includes(sectionKey);
    const [editingField, setEditingField] = useState(null);
    const [tempValue, setTempValue] = useState('');
    const [saving, setSaving] = useState(false);

    // Count filled vs total for section
    const getSectionStatus = () => {
        if (section.isArray) {
            const items = profile?.[section.arrayKey] || [];
            return { filled: items.length, total: items.length || 1, hasData: items.length > 0 };
        }

        let filled = 0;
        let required = 0;
        section.fields.forEach(f => {
            if (f.required) required++;
            if (profile?.[f.key] !== undefined && profile?.[f.key] !== null && profile?.[f.key] !== '') {
                filled++;
            }
        });
        return { filled, total: required, hasData: filled > 0 };
    };

    const status = getSectionStatus();

    const handleSave = async (fieldKey, value) => {
        setSaving(true);
        try {
            await onUpdate(fieldKey, value);
            setEditingField(null);
        } catch (e) {
            console.error('Failed to save:', e);
        } finally {
            setSaving(false);
        }
    };

    const handleAddArrayItem = async () => {
        const newItem = {};
        section.itemSchema.forEach(f => { newItem[f.key] = ''; });
        const currentArray = profile?.[section.arrayKey] || [];
        await onUpdate(section.arrayKey, [...currentArray, newItem], 'set');
    };

    const handleRemoveArrayItem = async (index) => {
        const currentArray = profile?.[section.arrayKey] || [];
        const itemToRemove = currentArray[index];
        // Use the 'remove' operation with identifying field
        await onUpdate(section.arrayKey, itemToRemove, 'remove');
    };

    const handleUpdateArrayItem = async (index, fieldKey, value) => {
        const currentArray = [...(profile?.[section.arrayKey] || [])];
        currentArray[index] = { ...currentArray[index], [fieldKey]: value };
        await onUpdate(section.arrayKey, currentArray, 'set');
    };

    return (
        <div className="border border-gray-200 rounded-lg overflow-hidden mb-3">
            {/* Section Header */}
            <button
                onClick={() => toggleSection(sectionKey)}
                className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <span className="text-xl">{section.icon}</span>
                    <span className="font-medium text-gray-900">{section.label}</span>
                </div>
                <div className="flex items-center gap-3">
                    {status.hasData ? (
                        <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                            <CheckCircleIcon className="h-4 w-4" />
                            {section.isArray ? `${status.filled} items` : 'Complete'}
                        </span>
                    ) : (
                        <span className="flex items-center gap-1 text-xs text-yellow-600 bg-yellow-50 px-2 py-1 rounded-full">
                            <ExclamationTriangleIcon className="h-4 w-4" />
                            Missing
                        </span>
                    )}
                    {isExpanded ? <ChevronDownIcon className="h-5 w-5 text-gray-500" /> : <ChevronRightIcon className="h-5 w-5 text-gray-500" />}
                </div>
            </button>

            {/* Section Content */}
            {isExpanded && (
                <div className="p-4 bg-white">
                    {section.isArray ? (
                        // Array section (courses, activities, etc.)
                        <div className="space-y-4">
                            {(profile?.[section.arrayKey] || []).map((item, idx) => (
                                <div key={idx} className="border border-gray-100 rounded-lg p-3 bg-gray-50 relative">
                                    <button
                                        onClick={() => handleRemoveArrayItem(idx)}
                                        className="absolute top-2 right-2 p-1 text-gray-400 hover:text-red-500 transition-colors"
                                    >
                                        <TrashIcon className="h-4 w-4" />
                                    </button>
                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3 pr-8">
                                        {section.itemSchema.map(field => (
                                            <div key={field.key} className={field.type === 'textarea' ? 'col-span-full' : ''}>
                                                <label className="block text-xs font-medium text-gray-600 mb-1">{field.label}</label>
                                                {field.type === 'select' ? (
                                                    <select
                                                        value={item[field.key] || ''}
                                                        onChange={(e) => handleUpdateArrayItem(idx, field.key, e.target.value)}
                                                        className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                                                    >
                                                        <option value="">Select...</option>
                                                        {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                                    </select>
                                                ) : field.type === 'textarea' ? (
                                                    <textarea
                                                        value={item[field.key] || ''}
                                                        onChange={(e) => handleUpdateArrayItem(idx, field.key, e.target.value)}
                                                        rows={2}
                                                        className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                                                    />
                                                ) : (
                                                    <input
                                                        type={field.type}
                                                        value={item[field.key] || ''}
                                                        onChange={(e) => handleUpdateArrayItem(idx, field.key, field.type === 'number' ? parseFloat(e.target.value) : e.target.value)}
                                                        className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-2 focus:ring-[#1A4D2E] focus:border-transparent"
                                                    />
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                            <button
                                onClick={handleAddArrayItem}
                                className="flex items-center gap-2 text-sm text-[#1A4D2E] hover:text-[#1A4D2E] font-medium"
                            >
                                <PlusIcon className="h-4 w-4" /> Add {section.label.replace(/s$/, '')}
                            </button>
                        </div>
                    ) : (
                        // Scalar fields section
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {section.fields.map(field => (
                                <div key={field.key}>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        {field.label}
                                        {field.required && <span className="text-red-500 ml-1">*</span>}
                                    </label>
                                    {editingField === field.key ? (
                                        <div className="flex gap-2">
                                            {field.type === 'select' ? (
                                                <select
                                                    value={tempValue}
                                                    onChange={(e) => setTempValue(e.target.value)}
                                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1A4D2E]"
                                                >
                                                    <option value="">Select...</option>
                                                    {field.options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                                                </select>
                                            ) : (
                                                <input
                                                    type={field.type}
                                                    value={tempValue}
                                                    onChange={(e) => setTempValue(e.target.value)}
                                                    step={field.step}
                                                    min={field.min}
                                                    max={field.max}
                                                    placeholder={field.placeholder}
                                                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#1A4D2E]"
                                                    autoFocus
                                                />
                                            )}
                                            <button
                                                onClick={() => handleSave(field.key, field.type === 'number' ? parseFloat(tempValue) : tempValue)}
                                                disabled={saving}
                                                className="px-3 py-2 bg-[#1A4D2E] text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                                            >
                                                {saving ? '...' : 'Save'}
                                            </button>
                                            <button
                                                onClick={() => setEditingField(null)}
                                                className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                                            >
                                                <XMarkIcon className="h-5 w-5" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div
                                            onClick={() => { setEditingField(field.key); setTempValue(profile?.[field.key] || ''); }}
                                            className={`px-3 py-2 rounded-lg border cursor-pointer transition-colors flex items-center justify-between ${profile?.[field.key] ? 'border-gray-200 bg-white hover:border-indigo-300' : 'border-dashed border-gray-300 bg-gray-50 hover:border-indigo-300'
                                                }`}
                                        >
                                            <span className={profile?.[field.key] ? 'text-gray-900' : 'text-gray-400'}>
                                                {profile?.[field.key] || `Click to add ${field.label.toLowerCase()}`}
                                            </span>
                                            {profile?.[field.key] ? (
                                                <PencilIcon className="h-4 w-4 text-gray-400" />
                                            ) : (
                                                <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500" />
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

// Document Upload Zone Component
const DocumentUploadZone = ({ onUpload, uploadedDocs, onDelete, uploading }) => {
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(e.type === 'dragenter' || e.type === 'dragover');
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            onUpload(Array.from(e.dataTransfer.files));
        }
    };

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files.length > 0) {
            onUpload(Array.from(e.target.files));
        }
    };

    return (
        <div className="space-y-4">
            {/* Drop Zone */}
            <div
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors ${dragActive ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-gray-400'
                    }`}
            >
                <CloudArrowUpIcon className={`h-10 w-10 mx-auto mb-3 ${dragActive ? 'text-indigo-500' : 'text-gray-400'}`} />
                <p className="text-sm text-gray-600 mb-2">
                    {uploading ? 'Uploading...' : 'Drop transcripts or resumes here'}
                </p>
                <label className="inline-block px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg cursor-pointer hover:bg-indigo-700">
                    Browse Files
                    <input
                        type="file"
                        multiple
                        accept=".pdf,.doc,.docx,.txt"
                        onChange={handleFileSelect}
                        className="hidden"
                        disabled={uploading}
                    />
                </label>
                <p className="text-xs text-gray-400 mt-2">PDF, DOCX, or TXT files</p>
            </div>

            {/* Uploaded Documents List */}
            {uploadedDocs.length > 0 && (
                <div className="space-y-2">
                    <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Uploaded Documents</p>
                    {uploadedDocs.map((doc, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                            <div className="flex items-center gap-2 text-sm">
                                <DocumentTextIcon className="h-4 w-4 text-gray-500" />
                                <span className="text-gray-700 truncate max-w-[150px]">{doc.display_name || doc.name}</span>
                                <CheckCircleIcon className="h-4 w-4 text-green-500" />
                            </div>
                            <button onClick={() => onDelete(doc)} className="text-gray-400 hover:text-red-500">
                                <TrashIcon className="h-4 w-4" />
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// Main ProfileBuilder Component
// Accepts profile and onProfileUpdate props from parent for state sync
const ProfileBuilder = ({ profile: parentProfile, onProfileUpdate }) => {
    const { currentUser } = useAuth();
    const [localProfile, setLocalProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expandedSections, setExpandedSections] = useState(['basics']);

    // Use parent profile if provided, otherwise use local
    const profile = parentProfile !== undefined ? parentProfile : localProfile;

    // Load profile on mount only if no parent profile provided
    useEffect(() => {
        if (currentUser?.email && parentProfile === undefined) {
            loadProfile();
        } else if (parentProfile !== undefined) {
            setLoading(false);
        }
    }, [currentUser, parentProfile]);

    const loadProfile = async () => {
        setLoading(true);
        try {
            const result = await fetchStructuredProfile(currentUser.email);
            if (result.success && result.profile) {
                setLocalProfile(result.profile);
            }
        } catch (e) {
            console.error('Failed to load profile:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (fieldPath, value, operation = 'set') => {
        try {
            await updateProfileField(currentUser.email, fieldPath, value, operation);
            // Call parent refresh if provided, otherwise refresh locally
            if (onProfileUpdate) {
                await onProfileUpdate();
            } else {
                await loadProfile();
            }
        } catch (e) {
            console.error('Failed to update profile:', e);
            throw e;
        }
    };

    const toggleSection = (sectionKey) => {
        setExpandedSections(prev =>
            prev.includes(sectionKey) ? prev.filter(k => k !== sectionKey) : [...prev, sectionKey]
        );
    };

    const handleUpload = async (files) => {
        setUploading(true);
        try {
            for (const file of files) {
                await uploadStudentProfile(currentUser.email, file);
            }
            await loadDocuments();
            await loadProfile(); // Refresh profile in case parsing added data
        } catch (e) {
            console.error('Upload failed:', e);
        } finally {
            setUploading(false);
        }
    };

    const handleDeleteDoc = async (doc) => {
        try {
            await deleteStudentProfile(currentUser.email, doc.display_name || doc.name);
            await loadDocuments();
        } catch (e) {
            console.error('Failed to delete document:', e);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <ArrowPathIcon className="h-8 w-8 text-gray-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Manual Entry</h1>
                <p className="text-gray-500 mt-1">Fill in your academic information to get personalized college recommendations.</p>
            </div>

            {/* Progress */}
            <CompletionProgress profile={profile} />

            {/* Schema Questionnaire - Full Width */}
            <div className="bg-white rounded-xl p-6 border border-gray-200">
                {Object.entries(PROFILE_SCHEMA).map(([key, section]) => (
                    <ProfileSection
                        key={key}
                        sectionKey={key}
                        section={section}
                        profile={profile}
                        onUpdate={handleUpdate}
                        expandedSections={expandedSections}
                        toggleSection={toggleSection}
                    />
                ))}
            </div>
        </div>
    );
};

export default ProfileBuilder;
