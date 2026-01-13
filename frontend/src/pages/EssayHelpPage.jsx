import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
    ArrowLeftIcon,
    LightBulbIcon,
    PencilSquareIcon,
    SparklesIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    DocumentTextIcon,
    ArrowPathIcon,
    ChatBubbleLeftRightIcon,
    CheckCircleIcon
} from '@heroicons/react/24/outline';

const KB_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL || 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';
const PROFILE_V2_URL = import.meta.env.VITE_PROFILE_MANAGER_V2_URL || 'https://profile-manager-v2-pfnwjfp26a-ue.a.run.app';

// Fallback brainstorming questions if none are persisted
const getDefaultBrainstormingQuestions = (promptText) => {
    const lowerPrompt = promptText.toLowerCase();

    if (lowerPrompt.includes('why') && (lowerPrompt.includes('major') || lowerPrompt.includes('study') || lowerPrompt.includes('academic'))) {
        return [
            "When did you first become interested in this field? Was there a specific moment?",
            "What problems or questions in this field excite you most?",
            "How have you explored this interest outside of required coursework?",
            "What do you hope to discover or create in this field?",
            "Who has influenced your thinking about this subject?"
        ];
    }

    if (lowerPrompt.includes('leader') || lowerPrompt.includes('contribute') || lowerPrompt.includes('impact')) {
        return [
            "Think of a time you took initiative without being asked. What motivated you?",
            "What leadership experiences have shaped how you approach working with others?",
            "How do you inspire or support people around you?",
            "What kind of change do you want to create, and why does it matter to you?",
            "Describe a moment when you helped a group achieve something together."
        ];
    }

    if (lowerPrompt.includes('community') || lowerPrompt.includes('belong')) {
        return [
            "What communities have shaped who you are?",
            "How have you contributed to a community you care about?",
            "What challenges has your community faced, and what role did you play?",
            "How has being part of this community influenced your values?",
            "What have you learned from people different from you?"
        ];
    }

    if (lowerPrompt.includes('challenge') || lowerPrompt.includes('overcome') || lowerPrompt.includes('difficult')) {
        return [
            "What was the specific challenge, and why was it significant to you?",
            "How did you initially react when facing this challenge?",
            "What resources, people, or inner strengths helped you navigate it?",
            "What did you learn about yourself through this experience?",
            "How has this experience influenced your approach to future obstacles?"
        ];
    }

    if (lowerPrompt.includes('why') && lowerPrompt.includes('university') || lowerPrompt.includes('school') || lowerPrompt.includes('college')) {
        return [
            "What first sparked your interest in this school?",
            "Which specific programs, professors, or opportunities align with your goals?",
            "How does this school's approach differ from others you're considering?",
            "What would you contribute to their community?",
            "What do you hope to accomplish or become during your time there?"
        ];
    }

    return [
        "What specific moment or experience comes to mind when you read this prompt?",
        "Why does this resonate with you personally?",
        "What would someone close to you say about this aspect of your life?",
        "How has this shaped who you are today?",
        "What do you want the admissions committee to understand about you through this?"
    ];
};

export default function EssayHelpPage() {
    const { universityId } = useParams();
    const navigate = useNavigate();
    const { currentUser } = useAuth();

    const [university, setUniversity] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedPrompt, setExpandedPrompt] = useState(null);
    const [brainstormNote, setBrainstormNote] = useState('');
    const [savedNotes, setSavedNotes] = useState({});

    // Essay Copilot State
    const [essayDrafts, setEssayDrafts] = useState({});
    const [starters, setStarters] = useState({});
    const [loadingStarters, setLoadingStarters] = useState({});
    const [copilotSuggestion, setCopilotSuggestion] = useState({}); // Now stores array of suggestions
    const [loadingCopilot, setLoadingCopilot] = useState({});
    const [feedback, setFeedback] = useState({});
    const [loadingFeedback, setLoadingFeedback] = useState({});
    const [writingMode, setWritingMode] = useState({});
    const [savingDraft, setSavingDraft] = useState({});
    const [lastSaved, setLastSaved] = useState({});
    // Context Panel state - shows relevant facts when hook is selected
    const [selectedHook, setSelectedHook] = useState({});
    const [contextPanel, setContextPanel] = useState({});
    const [loadingContext, setLoadingContext] = useState({});
    // Chat state
    const [chatQuestion, setChatQuestion] = useState({});
    const [chatResponse, setChatResponse] = useState({});
    const [loadingChat, setLoadingChat] = useState({});
    // Version state - stores all versions per prompt
    const [draftVersions, setDraftVersions] = useState({}); // { promptIndex: [{ version: 0, version_name: "Main", draft_text: "..." }, ...] }
    const [currentVersion, setCurrentVersion] = useState({}); // { promptIndex: 0 } - currently selected version
    // Outline state
    const [outline, setOutline] = useState({});
    const [loadingOutline, setLoadingOutline] = useState({});
    const [outlineExpanded, setOutlineExpanded] = useState({});

    const fetchUniversityData = useCallback(async () => {
        try {
            setLoading(true);
            const response = await fetch(`${KB_URL}?university_id=${universityId}`);
            const data = await response.json();

            if (data.success && data.university) {
                setUniversity(data.university);
            } else {
                setError('University not found');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [universityId]);

    useEffect(() => {
        fetchUniversityData();
    }, [fetchUniversityData]);

    const handleSaveNote = async (promptIndex, promptText) => {
        if (brainstormNote.trim()) {
            const newNotes = [...(savedNotes[promptIndex] || []), brainstormNote];
            setSavedNotes(prev => ({
                ...prev,
                [promptIndex]: newNotes
            }));
            setBrainstormNote('');

            // Auto-save draft with the new note
            try {
                await fetch(`${PROFILE_V2_URL}/save-essay-draft`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_email: currentUser?.email,
                        university_id: universityId,
                        prompt_index: promptIndex,
                        prompt_text: promptText,
                        draft_text: essayDrafts[promptIndex] || '',
                        notes: newNotes
                    })
                });
            } catch (err) {
                console.error('Failed to auto-save note:', err);
            }
        }
    };

    // Generate essay starters
    const handleGetStarters = async (promptIndex, promptText) => {
        setLoadingStarters(prev => ({ ...prev, [promptIndex]: true }));
        try {
            const notes = savedNotes[promptIndex]?.join('\n') || '';
            const response = await fetch(`${PROFILE_V2_URL}/essay-starters`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser?.email,
                    university_id: universityId,
                    prompt_text: promptText,
                    notes: notes
                })
            });
            const data = await response.json();
            if (data.success && data.starters) {
                setStarters(prev => ({ ...prev, [promptIndex]: data.starters }));
            }
        } catch (err) {
            console.error('Failed to get starters:', err);
        } finally {
            setLoadingStarters(prev => ({ ...prev, [promptIndex]: false }));
        }
    };

    // Handle selecting a coaching hook - fetches context panel data
    const handleSelectHook = async (promptIndex, selectedStarter, promptText) => {
        setSelectedHook(prev => ({ ...prev, [promptIndex]: selectedStarter }));
        setLoadingContext(prev => ({ ...prev, [promptIndex]: true }));
        setStarters(prev => ({ ...prev, [promptIndex]: null })); // Hide other starters

        try {
            const response = await fetch(`${PROFILE_V2_URL}/starter-context`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser?.email,
                    university_id: universityId,
                    selected_hook: selectedStarter,
                    prompt_text: promptText
                })
            });
            const data = await response.json();
            if (data.success) {
                setContextPanel(prev => ({ ...prev, [promptIndex]: data }));
            }
        } catch (err) {
            console.error('Failed to get context:', err);
        } finally {
            setLoadingContext(prev => ({ ...prev, [promptIndex]: false }));
        }
    };

    // Generate essay outline
    const handleGenerateOutline = async (promptIndex, prompt) => {
        setLoadingOutline(prev => ({ ...prev, [promptIndex]: true }));
        try {
            // Extract numeric word limit from prompt.word_limit (e.g., "250 words" -> 250)
            let wordLimit = null;
            if (prompt.word_limit) {
                const match = prompt.word_limit.match(/(\d+)/);
                if (match) {
                    wordLimit = parseInt(match[1]);
                }
            }

            const response = await fetch(`${PROFILE_V2_URL}/generate-outline`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser?.email,
                    university_id: universityId,
                    prompt_text: prompt.prompt,
                    selected_hook: selectedHook[promptIndex] || null,
                    word_limit: wordLimit
                })
            });
            const data = await response.json();
            if (data.success && data.outline) {
                setOutline(prev => ({ ...prev, [promptIndex]: data }));
                setOutlineExpanded(prev => ({ ...prev, [promptIndex]: true }));
            }
        } catch (err) {
            console.error('Failed to generate outline:', err);
        } finally {
            setLoadingOutline(prev => ({ ...prev, [promptIndex]: false }));
        }
    };


    // Get copilot suggestions (now returns array for 'suggest' action)
    const handleGetSuggestion = async (promptIndex, promptText, action = 'suggest') => {
        setLoadingCopilot(prev => ({ ...prev, [promptIndex]: true }));
        try {
            const currentText = essayDrafts[promptIndex] || '';
            const response = await fetch(`${PROFILE_V2_URL}/essay-copilot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt_text: promptText,
                    current_text: currentText,
                    action: action
                })
            });
            const data = await response.json();
            if (data.success && data.suggestions) {
                setCopilotSuggestion(prev => ({ ...prev, [promptIndex]: data.suggestions }));
            }
        } catch (err) {
            console.error('Failed to get suggestion:', err);
        } finally {
            setLoadingCopilot(prev => ({ ...prev, [promptIndex]: false }));
        }
    };

    // Chat with AI about essay context
    const handleChat = async (promptIndex, promptText) => {
        const question = chatQuestion[promptIndex];
        if (!question?.trim()) return;

        setLoadingChat(prev => ({ ...prev, [promptIndex]: true }));
        try {
            const response = await fetch(`${PROFILE_V2_URL}/essay-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser?.email,
                    university_id: universityId,
                    prompt_text: promptText,
                    current_text: essayDrafts[promptIndex] || '',
                    question: question
                })
            });
            const data = await response.json();
            if (data.success && data.response) {
                setChatResponse(prev => ({ ...prev, [promptIndex]: data.response }));
                setChatQuestion(prev => ({ ...prev, [promptIndex]: '' }));
            }
        } catch (err) {
            console.error('Failed to chat:', err);
        } finally {
            setLoadingChat(prev => ({ ...prev, [promptIndex]: false }));
        }
    };

    // Get draft feedback
    const handleGetFeedback = async (promptIndex, promptText) => {
        setLoadingFeedback(prev => ({ ...prev, [promptIndex]: true }));
        try {
            const draftText = essayDrafts[promptIndex] || '';
            const response = await fetch(`${PROFILE_V2_URL}/essay-feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt_text: promptText,
                    draft_text: draftText,
                    university_name: university?.profile?.metadata?.official_name || ''
                })
            });
            const data = await response.json();
            if (data.success && data.feedback) {
                setFeedback(prev => ({ ...prev, [promptIndex]: data.feedback }));
            }
        } catch (err) {
            console.error('Failed to get feedback:', err);
        } finally {
            setLoadingFeedback(prev => ({ ...prev, [promptIndex]: false }));
        }
    };

    // Apply a starter to the draft
    const handleUseStarter = (promptIndex, starterText) => {
        setEssayDrafts(prev => ({ ...prev, [promptIndex]: starterText }));
        setWritingMode(prev => ({ ...prev, [promptIndex]: true }));
        setStarters(prev => ({ ...prev, [promptIndex]: null }));
    };

    // Apply copilot suggestion to draft
    const handleApplySuggestion = (promptIndex) => {
        const suggestion = copilotSuggestion[promptIndex];
        if (suggestion) {
            setEssayDrafts(prev => ({
                ...prev,
                [promptIndex]: (prev[promptIndex] || '') + ' ' + suggestion
            }));
            setCopilotSuggestion(prev => ({ ...prev, [promptIndex]: null }));
        }
    };

    // Save essay draft to backend
    const handleSaveDraft = async (promptIndex, promptText, saveAsNew = false) => {
        setSavingDraft(prev => ({ ...prev, [promptIndex]: true }));
        try {
            const version = saveAsNew
                ? (draftVersions[promptIndex]?.length || 1)  // Next version number
                : (currentVersion[promptIndex] || 0);

            const response = await fetch(`${PROFILE_V2_URL}/save-essay-draft`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser?.email,
                    university_id: universityId,
                    prompt_index: promptIndex,
                    prompt_text: promptText,
                    draft_text: essayDrafts[promptIndex] || '',
                    notes: savedNotes[promptIndex] || [],
                    version: version,
                    version_name: saveAsNew ? `Version ${version + 1}` : ''
                })
            });
            const data = await response.json();
            if (data.success) {
                setLastSaved(prev => ({ ...prev, [promptIndex]: new Date().toLocaleTimeString() }));
                if (saveAsNew) {
                    // Reload drafts to get all versions
                    loadDrafts();
                    setCurrentVersion(prev => ({ ...prev, [promptIndex]: version }));
                }
            }
        } catch (err) {
            console.error('Failed to save draft:', err);
        } finally {
            setSavingDraft(prev => ({ ...prev, [promptIndex]: false }));
        }
    };

    // Load saved drafts on mount - group by prompt and track versions
    const loadDrafts = useCallback(async () => {
        if (!currentUser?.email) return;
        try {
            const response = await fetch(`${PROFILE_V2_URL}/get-essay-drafts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId
                })
            });
            const data = await response.json();
            if (data.success && data.drafts) {
                const draftsMap = {};
                const notesMap = {};
                const versionsMap = {};

                // Group drafts by prompt_index
                data.drafts.forEach(draft => {
                    const idx = draft.prompt_index;
                    const version = draft.version || 0;

                    // Store versions
                    if (!versionsMap[idx]) versionsMap[idx] = [];
                    versionsMap[idx].push({
                        version: version,
                        version_name: draft.version_name || `Version ${version + 1}`,
                        draft_text: draft.draft_text,
                        notes: draft.notes,
                        updated_at: draft.updated_at
                    });

                    // Set main draft (version 0) as default display
                    if (version === (currentVersion[idx] || 0)) {
                        draftsMap[idx] = draft.draft_text;
                        if (draft.notes?.length > 0) {
                            notesMap[idx] = draft.notes;
                        }
                    }
                });

                // Sort versions by version number
                Object.keys(versionsMap).forEach(idx => {
                    versionsMap[idx].sort((a, b) => a.version - b.version);
                });

                setDraftVersions(versionsMap);
                setEssayDrafts(draftsMap);
                setSavedNotes(prev => ({ ...prev, ...notesMap }));
            }
        } catch (err) {
            console.error('Failed to load drafts:', err);
        }
    }, [currentUser?.email, universityId, currentVersion]);

    useEffect(() => {
        loadDrafts();
    }, [loadDrafts]);

    if (loading) {
        return (
            <div className="min-h-screen bg-[#FDFCF7] flex items-center justify-center">
                <div className="text-center">
                    <div className="w-10 h-10 border-3 border-[#E0DED8] border-t-[#1A4D2E] rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-[#4A4A4A]">Loading essay prompts...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-[#FDFCF7] p-8">
                <button onClick={() => navigate('/launchpad')} className="flex items-center gap-2 text-[#1A4D2E] mb-4">
                    <ArrowLeftIcon className="w-5 h-5" /> Back to My Schools
                </button>
                <div className="text-center py-12">
                    <p className="text-red-500">{error}</p>
                </div>
            </div>
        );
    }

    const profile = university?.profile;
    const universityName = profile?.metadata?.official_name || universityId.replace(/_/g, ' ');
    const essayTips = profile?.student_insights?.essay_tips || [];
    const deadlines = profile?.application_process?.application_deadlines || [];
    const essayPrompts = profile?.application_process?.supplemental_requirements?.essay_prompts || profile?.application_process?.essay_prompts || [];

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            {/* Hero Header */}
            <div className="bg-[#FDFCF7] border-b border-[#E0DED8]">
                <div className="max-w-6xl mx-auto px-6 py-6">
                    <button
                        onClick={() => navigate('/launchpad')}
                        className="flex items-center gap-2 text-[#1A4D2E] hover:text-[#2D6B45] mb-4 transition-colors text-sm"
                    >
                        <ArrowLeftIcon className="w-4 h-4" /> Back to My Schools
                    </button>

                    <div className="flex items-start justify-between">
                        <div>
                            <h1 className="font-serif text-2xl md:text-3xl font-semibold text-[#2C2C2C]">
                                Essay Workshop
                            </h1>
                            <p className="text-[#6B6B6B] mt-1">{universityName}</p>
                        </div>

                        {deadlines.length > 0 && (
                            <div className="text-right">
                                <span className="text-xs text-[#6B6B6B] uppercase tracking-wide">Next Deadline</span>
                                <div className="font-medium text-[#1A4D2E]">
                                    {deadlines[0].plan_type}: {new Date(deadlines[0].date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="max-w-6xl mx-auto px-6 py-8">

                {/* Philosophy Card */}
                <div className="stratia-card p-6 mb-8 bg-gradient-to-r from-[#F8F6F0] to-[#FDFCF7]">
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-[#D6E8D5] rounded-full flex items-center justify-center flex-shrink-0">
                            <SparklesIcon className="w-6 h-6 text-[#1A4D2E]" />
                        </div>
                        <div>
                            <h3 className="font-serif text-lg font-semibold text-[#2C2C2C] mb-2">Your AI Writing Partner</h3>
                            <p className="text-[#4A4A4A] text-sm leading-relaxed">
                                I help you discover your unique story and guide your writing. Click on a prompt to brainstorm,
                                get personalized essay starters, and receive real-time suggestions as you write.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Essay Prompts */}
                <div className="space-y-6">
                    <h2 className="font-serif text-xl font-semibold text-[#2C2C2C] flex items-center gap-2">
                        <PencilSquareIcon className="w-5 h-5 text-[#1A4D2E]" />
                        Essay Prompts ({essayPrompts.length})
                    </h2>

                    {essayPrompts.length === 0 ? (
                        <div className="stratia-card p-8 text-center">
                            <p className="text-[#6B6B6B]">Essay prompts for this university are being collected. Check back soon!</p>
                        </div>
                    ) : (
                        essayPrompts.map((prompt, index) => (
                            <div key={index} className="bg-white rounded-2xl shadow-md border border-[#E0DED8] overflow-hidden hover:shadow-lg transition-shadow">
                                {/* Colored accent bar */}
                                <div className={`h-1.5 ${index % 3 === 0 ? 'bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45]' : index % 3 === 1 ? 'bg-gradient-to-r from-[#C05838] to-[#E07050]' : 'bg-gradient-to-r from-[#4A7C59] to-[#6B9969]'}`}></div>
                                {/* Prompt Header */}
                                <button
                                    onClick={() => setExpandedPrompt(expandedPrompt === index ? null : index)}
                                    className="w-full p-6 flex items-start justify-between text-left hover:bg-[#FAFAF8] transition-colors"
                                >
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] text-xs font-medium rounded">
                                                {prompt.type || 'Essay'}
                                            </span>
                                            <span className="text-xs text-[#6B6B6B]">{prompt.word_limit}</span>
                                            {prompt.required && (
                                                <span className="text-xs text-[#C05838]">Required</span>
                                            )}
                                            {essayDrafts[index] && (
                                                <span className="text-xs text-[#1A4D2E] flex items-center gap-1">
                                                    <DocumentTextIcon className="w-3 h-3" /> Draft saved
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-[#2C2C2C] font-medium leading-relaxed text-base">{prompt.prompt}</p>
                                    </div>
                                    <div className="ml-4 flex-shrink-0">
                                        {expandedPrompt === index ? (
                                            <ChevronUpIcon className="w-5 h-5 text-[#6B6B6B]" />
                                        ) : (
                                            <ChevronDownIcon className="w-5 h-5 text-[#6B6B6B]" />
                                        )}
                                    </div>
                                </button>

                                {/* Expanded Section */}
                                {expandedPrompt === index && (
                                    <div className="p-5 space-y-4 bg-[#FAFAF8]">
                                        {/* Guiding Questions Card */}
                                        <div className="bg-white rounded-xl border border-[#E0DED8] shadow-sm p-5">
                                            <div className="flex items-center gap-2 mb-4">
                                                <div className="w-8 h-8 bg-[#FFF3E0] rounded-lg flex items-center justify-center">
                                                    <LightBulbIcon className="w-5 h-5 text-[#C05838]" />
                                                </div>
                                                <h4 className="font-semibold text-[#2C2C2C]">Questions to Guide Your Thinking</h4>
                                            </div>
                                            <ul className="space-y-3">
                                                {(prompt.brainstorming_questions || getDefaultBrainstormingQuestions(prompt.prompt)).map((q, i) => (
                                                    <li key={i} className="flex items-start gap-3 text-sm text-[#4A4A4A]">
                                                        <span className="w-6 h-6 bg-gradient-to-br from-[#C05838] to-[#E07050] text-white rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                                                            {i + 1}
                                                        </span>
                                                        <span className="leading-relaxed">{q}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Brainstorm Notes Card - Collapsible */}
                                        <div className="bg-white rounded-xl border border-[#E0DED8] shadow-sm overflow-hidden">
                                            <button
                                                onClick={() => setWritingMode(prev => ({ ...prev, [`notes_${index}`]: !prev[`notes_${index}`] }))}
                                                className="w-full p-4 flex items-center justify-between text-left hover:bg-[#FAFAF8] transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-[#E8F5E9] rounded-lg flex items-center justify-center">
                                                        <span className="text-lg">✍️</span>
                                                    </div>
                                                    <div>
                                                        <h4 className="font-semibold text-[#2C2C2C]">Jot Down Your Thoughts</h4>
                                                        <span className="text-xs text-[#6B6B6B]">
                                                            {savedNotes[index]?.length || 0} notes saved
                                                        </span>
                                                    </div>
                                                </div>
                                                {writingMode[`notes_${index}`] ? (
                                                    <ChevronUpIcon className="w-5 h-5 text-[#6B6B6B]" />
                                                ) : (
                                                    <ChevronDownIcon className="w-5 h-5 text-[#6B6B6B]" />
                                                )}
                                            </button>

                                            {writingMode[`notes_${index}`] && (
                                                <div className="px-4 pb-4 border-t border-[#E0DED8]">
                                                    <textarea
                                                        value={brainstormNote}
                                                        onChange={(e) => setBrainstormNote(e.target.value)}
                                                        placeholder="Capture your ideas, memories, and reflections here..."
                                                        rows={2}
                                                        className="w-full mt-4 px-4 py-3 bg-[#FAFAF8] border border-[#E0DED8] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20 focus:border-[#1A4D2E] resize-none text-sm"
                                                    />
                                                    <div className="flex justify-end mt-2">
                                                        <button
                                                            onClick={() => handleSaveNote(index, prompt.prompt)}
                                                            disabled={!brainstormNote.trim()}
                                                            className="px-3 py-1.5 bg-[#1A4D2E] text-white text-xs rounded-lg font-medium hover:bg-[#2D6B45] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                                        >
                                                            Add Note
                                                        </button>
                                                    </div>

                                                    {savedNotes[index]?.length > 0 && (
                                                        <div className="mt-3 space-y-2 max-h-32 overflow-y-auto">
                                                            {savedNotes[index].map((note, i) => (
                                                                <div key={i} className="p-3 bg-[#FAFAF8] border border-[#E0DED8] rounded-lg text-xs text-[#4A4A4A]">
                                                                    {note}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>

                                        {/* Essay Starters Card */}
                                        <div className="bg-white rounded-xl border border-[#E0DED8] shadow-sm p-5">
                                            <div className="flex items-center justify-between mb-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-[#E8F5E9] rounded-lg flex items-center justify-center">
                                                        <SparklesIcon className="w-5 h-5 text-[#1A4D2E]" />
                                                    </div>
                                                    <h4 className="font-semibold text-[#2C2C2C]">Get Personalized Starters</h4>
                                                </div>
                                                <button
                                                    onClick={() => handleGetStarters(index, prompt.prompt)}
                                                    disabled={loadingStarters[index]}
                                                    className="px-4 py-2 bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] text-white text-sm rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-2 shadow-sm"
                                                >
                                                    {loadingStarters[index] ? (
                                                        <>
                                                            <ArrowPathIcon className="w-4 h-4 animate-spin" />
                                                            Generating...
                                                        </>
                                                    ) : (
                                                        '✨ Generate Starters'
                                                    )}
                                                </button>
                                            </div>

                                            {starters[index] && (
                                                <div className="space-y-3">
                                                    <p className="text-xs text-[#6B6B6B]">Select a prompt to see relevant context:</p>
                                                    {starters[index].map((starter, i) => (
                                                        <div key={i} className="p-4 bg-gradient-to-r from-[#F0F9F0] to-[#FAFAF8] border border-[#D6E8D5] rounded-xl hover:shadow-sm transition-shadow cursor-pointer"
                                                            onClick={() => handleSelectHook(index, starter, prompt.prompt)}
                                                        >
                                                            <p className="text-sm text-[#2C2C2C] leading-relaxed italic">{starter}</p>
                                                            <span className="text-xs text-[#1A4D2E] font-semibold mt-2 inline-block">
                                                                → Select this prompt
                                                            </span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Context Panel - shows when hook is selected */}
                                            {(selectedHook[index] || loadingContext[index]) && (
                                                <div className="mt-4 p-5 bg-gradient-to-br from-[#F0F9F0] to-[#E8F5E9] border-2 border-[#4A7C59] rounded-xl">
                                                    <div className="flex items-center justify-between mb-4">
                                                        <h5 className="text-sm font-bold text-[#1A4D2E]">📝 Your Writing Prompt</h5>
                                                        <button
                                                            onClick={() => {
                                                                setSelectedHook(prev => ({ ...prev, [index]: null }));
                                                                setContextPanel(prev => ({ ...prev, [index]: null }));
                                                            }}
                                                            className="text-xs text-[#6B6B6B] hover:underline"
                                                        >
                                                            ✕ Clear
                                                        </button>
                                                    </div>

                                                    {/* Selected Hook Display */}
                                                    <div className="p-3 bg-white/70 rounded-lg mb-4 border border-[#D6E8D5]">
                                                        <p className="text-sm text-[#2C2C2C] italic font-medium">{selectedHook[index]}</p>
                                                    </div>

                                                    {loadingContext[index] ? (
                                                        <div className="text-center py-4">
                                                            <div className="animate-spin w-5 h-5 border-2 border-[#1A4D2E] border-t-transparent rounded-full mx-auto"></div>
                                                            <p className="text-xs text-[#6B6B6B] mt-2">Generating personalized pointers...</p>
                                                        </div>
                                                    ) : contextPanel[index] && (
                                                        <div>
                                                            <h6 className="text-xs font-bold text-[#1A4D2E] mb-3">💡 Writing Pointers Based on Your Background</h6>
                                                            {contextPanel[index].pointers?.length > 0 ? (
                                                                <ul className="space-y-3">
                                                                    {contextPanel[index].pointers.map((pointer, i) => (
                                                                        <li key={i} className="flex items-start gap-2 p-3 bg-white/70 rounded-lg">
                                                                            <span className="text-[#1A4D2E] mt-0.5">→</span>
                                                                            <p className="text-sm text-[#2C2C2C] leading-relaxed">{pointer}</p>
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            ) : (
                                                                <p className="text-xs text-[#6B6B6B] italic">Complete your profile for personalized pointers</p>
                                                            )}
                                                        </div>
                                                    )}

                                                    <p className="text-xs text-[#6B6B6B] mt-4 text-center italic">
                                                        Use these pointers as inspiration — write your answer in the essay area below ↓
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                        {/* Generate Outline Button - Add after contextPanel */}
                                        {
                                            contextPanel[index] && (
                                                <div className="flex justify-end mt-4">
                                                    <button
                                                        onClick={() => handleGenerateOutline(index, prompt)}
                                                        disabled={loadingOutline[index]}
                                                        className="px-4 py-2 bg-[#1A4D2E] text-white text-sm rounded-lg font-medium hover:bg-[#2A6D4E] disabled:opacity-50 transition-all flex items-center gap-2 shadow-sm "
                                                    >
                                                        {loadingOutline[index] ? (
                                                            <>
                                                                <ArrowPathIcon className="w-4 h-4 animate-spin" />
                                                                Generating Outline...
                                                            </>
                                                        ) : (
                                                            '📝 Generate Essay Outline'
                                                        )}
                                                    </button>
                                                </div>
                                            )
                                        }

                                        {/* Essay Outline Display - Collapsible */}
                                        {
                                            outline[index] && (
                                                <div className="bg-white rounded-xl border-2 border-purple-200 shadow-sm overflow-hidden mb-4">
                                                    <button
                                                        onClick={() => setOutlineExpanded(prev => ({ ...prev, [index]: !prev[index] }))}
                                                        className="w-full p-4 flex items-center justify-between text-left hover:bg-purple-50 transition-colors"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                                                                <span className="text-lg">📝</span>
                                                            </div>
                                                            <h4 className="font-semibold text-purple-900">Essay Outline</h4>
                                                        </div>
                                                        {outlineExpanded[index] ? (
                                                            <ChevronUpIcon className="w-5 h-5 text-purple-600" />
                                                        ) : (
                                                            <ChevronDownIcon className="w-5 h-5 text-purple-600" />
                                                        )}
                                                    </button>

                                                    {outlineExpanded[index] && (
                                                        <div className="p-5 bg-purple-50 border-t border-purple-200">
                                                            <div className="space-y-4">
                                                                {outline[index].outline?.map((section, i) => (
                                                                    <div key={i} className="bg-white rounded-lg border-l-4 border-purple-400 p-4 shadow-sm">
                                                                        <h5 className="font-bold text-purple-800 mb-2">
                                                                            {section.section}
                                                                            <span className="text-sm font-normal text-purple-600 ml-2">
                                                                                ({section.word_count})
                                                                            </span>
                                                                        </h5>
                                                                        <ul className="mt-2 space-y-2">
                                                                            {section.points?.map((point, j) => (
                                                                                <li key={j} className="text-sm text-gray-700 flex items-start gap-2">
                                                                                    <span className="text-purple-500 mt-0.5">•</span>
                                                                                    <span>{point}</span>
                                                                                </li>
                                                                            ))}
                                                                        </ul>
                                                                    </div>
                                                                ))}

                                                                {/* Total Word Count */}
                                                                <div className="bg-purple-100 rounded-lg p-3">
                                                                    <p className="text-sm font-semibold text-purple-900">
                                                                        📏 Total: {outline[index].total_word_count}
                                                                    </p>
                                                                </div>

                                                                {/* Writing Tips */}
                                                                {outline[index].writing_tips && outline[index].writing_tips.length > 0 && (
                                                                    <div className="bg-white rounded-lg border border-purple-200 p-4">
                                                                        <h6 className="text-sm font-bold text-purple-800 mb-2 flex items-center gap-2">
                                                                            <span>💡</span> Writing Tips
                                                                        </h6>
                                                                        <ul className="space-y-1.5">
                                                                            {outline[index].writing_tips.map((tip, i) => (
                                                                                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                                                                                    <span className="text-purple-500 font-bold">{i + 1}.</span>
                                                                                    <span>{tip}</span>
                                                                                </li>
                                                                            ))}
                                                                        </ul>
                                                                    </div>
                                                                )}
                                                            </div>

                                                            <p className="text-xs text-purple-600 mt-4 text-center italic">
                                                                ↓ Use this outline as a guide while writing your essay below
                                                            </p>
                                                        </div>
                                                    )}
                                                </div>
                                            )
                                        }

                                        {/* Writing Mode Card */}
                                        <div className="bg-white rounded-xl border border-[#E0DED8] shadow-sm p-5">
                                            <div className="flex items-center justify-between mb-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-[#E8F5E9] rounded-lg flex items-center justify-center">
                                                        <DocumentTextIcon className="w-5 h-5 text-[#1A4D2E]" />
                                                    </div>
                                                    <h4 className="font-semibold text-[#2C2C2C]">Write Your Essay</h4>

                                                    {/* Version Selector */}
                                                    {draftVersions[index]?.length > 0 && (
                                                        <select
                                                            value={currentVersion[index] || 0}
                                                            onChange={(e) => {
                                                                const newVersion = parseInt(e.target.value);
                                                                setCurrentVersion(prev => ({ ...prev, [index]: newVersion }));
                                                                // Load the selected version's content
                                                                const versionData = draftVersions[index].find(v => v.version === newVersion);
                                                                if (versionData) {
                                                                    setEssayDrafts(prev => ({ ...prev, [index]: versionData.draft_text }));
                                                                    if (versionData.notes?.length > 0) {
                                                                        setSavedNotes(prev => ({ ...prev, [index]: versionData.notes }));
                                                                    }
                                                                }
                                                            }}
                                                            className="text-xs px-2 py-1 bg-[#F5F5F5] border border-[#E0DED8] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1A4D2E]"
                                                        >
                                                            {draftVersions[index].map((v) => (
                                                                <option key={v.version} value={v.version}>
                                                                    {v.version_name || `Version ${v.version + 1}`}
                                                                </option>
                                                            ))}
                                                        </select>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs text-[#6B6B6B] bg-[#F5F5F5] px-2 py-1 rounded">
                                                        {(essayDrafts[index]?.split(/\s+/).filter(Boolean).length || 0)} words
                                                    </span>
                                                </div>
                                            </div>

                                            <textarea
                                                value={essayDrafts[index] || ''}
                                                onChange={(e) => setEssayDrafts(prev => ({ ...prev, [index]: e.target.value }))}
                                                placeholder="Start writing your essay here... Use the starters above or begin fresh."
                                                rows={10}
                                                className="w-full px-4 py-4 bg-[#FAFAF8] border border-[#E0DED8] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20 focus:border-[#1A4D2E] resize-none text-sm leading-relaxed"
                                            />

                                            {/* Copilot Actions */}
                                            <div className="flex flex-wrap gap-2 mt-3">
                                                <button
                                                    onClick={() => handleGetSuggestion(index, prompt.prompt, 'suggest')}
                                                    disabled={loadingCopilot[index] || !essayDrafts[index]}
                                                    className="px-3 py-1.5 bg-[#F8F6F0] border border-[#E0DED8] text-[#2C2C2C] text-xs rounded-lg hover:bg-[#E0DED8] disabled:opacity-50 transition-colors flex items-center gap-1"
                                                >
                                                    <ChatBubbleLeftRightIcon className="w-3.5 h-3.5" />
                                                    {loadingCopilot[index] ? 'Thinking...' : '💡 Need a pointer?'}
                                                </button>
                                                <button
                                                    onClick={() => handleGetFeedback(index, prompt.prompt)}
                                                    disabled={loadingFeedback[index] || !essayDrafts[index] || (essayDrafts[index]?.split(/\s+/).length < 20)}
                                                    className="px-3 py-1.5 bg-[#1A4D2E] text-white text-xs rounded-lg hover:bg-[#2D6B45] disabled:opacity-50 transition-colors flex items-center gap-1"
                                                >
                                                    <CheckCircleIcon className="w-3.5 h-3.5" />
                                                    {loadingFeedback[index] ? 'Analyzing...' : 'Get Feedback'}
                                                </button>
                                                <div className="flex items-center gap-2 ml-auto">
                                                    <button
                                                        onClick={() => handleSaveDraft(index, prompt.prompt, false)}
                                                        disabled={savingDraft[index] || !essayDrafts[index]}
                                                        className="px-3 py-1.5 bg-[#2D6B45] text-white text-xs rounded-lg hover:bg-[#1A4D2E] disabled:opacity-50 transition-colors flex items-center gap-1"
                                                    >
                                                        {savingDraft[index] ? 'Saving...' : '💾 Save'}
                                                    </button>
                                                    <button
                                                        onClick={() => handleSaveDraft(index, prompt.prompt, true)}
                                                        disabled={savingDraft[index] || !essayDrafts[index]}
                                                        className="px-3 py-1.5 bg-[#F8F6F0] border border-[#2D6B45] text-[#2D6B45] text-xs rounded-lg hover:bg-[#E8F5E9] disabled:opacity-50 transition-colors flex items-center gap-1"
                                                    >
                                                        + New Version
                                                    </button>
                                                </div>
                                            </div>
                                            {lastSaved[index] && (
                                                <p className="text-xs text-[#6B6B6B] mt-1">Last saved: {lastSaved[index]}</p>
                                            )}

                                            {/* Copilot Suggestions - Now shows multiple options */}
                                            {copilotSuggestion[index]?.length > 0 && (
                                                <div className="mt-4 p-4 bg-gradient-to-r from-[#D6E8D5]/30 to-[#E8F5E9]/30 border border-[#D6E8D5] rounded-xl">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h5 className="text-sm font-semibold text-[#1A4D2E]">💡 Coaching prompts to guide your next thought:</h5>
                                                        <button
                                                            onClick={() => setCopilotSuggestion(prev => ({ ...prev, [index]: null }))}
                                                            className="text-xs text-[#6B6B6B] hover:underline"
                                                        >
                                                            Dismiss
                                                        </button>
                                                    </div>
                                                    <div className="space-y-2">
                                                        {copilotSuggestion[index].map((suggestion, i) => (
                                                            <div key={i} className="p-3 bg-white/80 border border-[#D6E8D5]/50 rounded-lg">
                                                                <p className="text-sm text-[#2C2C2C] leading-relaxed italic">{suggestion}</p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Chat Card - Ask AI for Context */}
                                            <div className="mt-4 p-4 bg-gradient-to-r from-[#D6E8D5]/30 to-[#E8F5E9]/30 border border-[#4A7C59] rounded-xl">
                                                <div className="flex items-center gap-2 mb-3">
                                                    <div className="w-6 h-6 bg-[#D6E8D5] rounded-full flex items-center justify-center">
                                                        <ChatBubbleLeftRightIcon className="w-3.5 h-3.5 text-[#1A4D2E]" />
                                                    </div>
                                                    <h5 className="text-sm font-semibold text-[#1A4D2E]">Ask AI for Context</h5>
                                                </div>
                                                <div className="flex gap-2">
                                                    <input
                                                        type="text"
                                                        value={chatQuestion[index] || ''}
                                                        onChange={(e) => setChatQuestion(prev => ({ ...prev, [index]: e.target.value }))}
                                                        onKeyPress={(e) => e.key === 'Enter' && handleChat(index, prompt.prompt)}
                                                        placeholder="e.g., 'Find professors who work on marketing psychology'"
                                                        className="flex-1 px-3 py-2 text-sm border border-[#4A7C59]/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20 bg-white/80"
                                                    />
                                                    <button
                                                        onClick={() => handleChat(index, prompt.prompt)}
                                                        disabled={loadingChat[index] || !chatQuestion[index]?.trim()}
                                                        className="px-4 py-2 bg-[#1A4D2E] text-white text-sm rounded-lg hover:bg-[#2D6B45] disabled:opacity-50 transition-colors"
                                                    >
                                                        {loadingChat[index] ? '...' : 'Ask'}
                                                    </button>
                                                </div>
                                                {chatResponse[index] && (
                                                    <div className="mt-3 p-3 bg-white/90 border border-[#D6E8D5] rounded-lg">
                                                        <p className="text-sm text-[#2C2C2C] leading-relaxed">{chatResponse[index]}</p>
                                                        <button
                                                            onClick={() => setChatResponse(prev => ({ ...prev, [index]: null }))}
                                                            className="text-xs text-[#6B6B6B] hover:underline mt-2"
                                                        >
                                                            Dismiss
                                                        </button>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Feedback Panel */}
                                            {feedback[index] && (
                                                <div className="mt-4 p-4 bg-white border border-[#E0DED8] rounded-xl">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h5 className="font-medium text-[#2C2C2C]">📊 Essay Feedback</h5>
                                                        <div className="flex gap-2">
                                                            <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] text-xs rounded">
                                                                Score: {feedback[index].overall_score}/10
                                                            </span>
                                                        </div>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-4 mb-4 text-xs">
                                                        <div>
                                                            <span className="text-[#6B6B6B]">Prompt Alignment:</span>
                                                            <span className="ml-2 font-medium">{feedback[index].prompt_alignment}/10</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-[#6B6B6B]">Authenticity:</span>
                                                            <span className="ml-2 font-medium">{feedback[index].authenticity}/10</span>
                                                        </div>
                                                    </div>

                                                    {feedback[index].strengths?.length > 0 && (
                                                        <div className="mb-3">
                                                            <p className="text-xs font-medium text-[#1A4D2E] mb-1">Strengths:</p>
                                                            <ul className="text-xs text-[#4A4A4A] space-y-1">
                                                                {feedback[index].strengths.map((s, i) => (
                                                                    <li key={i}>✓ {s}</li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    )}

                                                    {feedback[index].improvements?.length > 0 && (
                                                        <div className="mb-3">
                                                            <p className="text-xs font-medium text-[#C05838] mb-1">To Improve:</p>
                                                            <ul className="text-xs text-[#4A4A4A] space-y-1">
                                                                {feedback[index].improvements.map((s, i) => (
                                                                    <li key={i}>→ {s}</li>
                                                                ))}
                                                            </ul>
                                                        </div>
                                                    )}

                                                    {feedback[index].next_step && (
                                                        <div className="p-2 bg-[#F8F6F0] rounded text-xs text-[#2C2C2C]">
                                                            <strong>Next step:</strong> {feedback[index].next_step}
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>

                {/* Essay Tips Sidebar */}
                {essayTips.length > 0 && (
                    <div className="mt-8 stratia-card p-5">
                        <h3 className="font-serif text-lg font-semibold text-[#2C2C2C] mb-4">
                            💡 Tips from Admissions Officers
                        </h3>
                        <ul className="space-y-3">
                            {essayTips.slice(0, 5).map((tip, i) => (
                                <li key={i} className="text-sm text-[#4A4A4A] leading-relaxed pl-4 border-l-2 border-[#D6E8D5]">
                                    {tip}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div >
    );
}
