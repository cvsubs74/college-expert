import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ArrowLeftIcon, LightBulbIcon, PencilSquareIcon, SparklesIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';

const KB_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL || 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

// Fallback brainstorming questions if none are persisted
const getDefaultBrainstormingQuestions = (promptText) => {
    // Generate relevant questions based on keywords in the prompt
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

    // Default personal reflection questions
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

    const handleSaveNote = (promptIndex) => {
        if (brainstormNote.trim()) {
            setSavedNotes(prev => ({
                ...prev,
                [promptIndex]: [...(prev[promptIndex] || []), brainstormNote]
            }));
            setBrainstormNote('');
        }
    };

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

    // Get essay prompts from the new field, fallback to empty array
    const essayPrompts = profile?.application_process?.essay_prompts || [];

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

                        {/* Deadline Badge */}
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
                            <h3 className="font-serif text-lg font-semibold text-[#2C2C2C] mb-2">Your Brainstorming Partner</h3>
                            <p className="text-[#4A4A4A] text-sm leading-relaxed">
                                Great essays come from authentic self-reflection. I'm here to ask the right questions,
                                not give you answers. Click on each prompt below to explore guiding questions that will
                                help you discover your unique story.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Essay Prompts */}
                <div className="space-y-4">
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
                            <div key={index} className="stratia-card overflow-hidden">
                                {/* Prompt Header */}
                                <button
                                    onClick={() => setExpandedPrompt(expandedPrompt === index ? null : index)}
                                    className="w-full p-5 flex items-start justify-between text-left hover:bg-[#F8F6F0] transition-colors"
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
                                        </div>
                                        <p className="text-[#2C2C2C] font-medium leading-relaxed">{prompt.prompt}</p>
                                    </div>
                                    <div className="ml-4 flex-shrink-0">
                                        {expandedPrompt === index ? (
                                            <ChevronUpIcon className="w-5 h-5 text-[#6B6B6B]" />
                                        ) : (
                                            <ChevronDownIcon className="w-5 h-5 text-[#6B6B6B]" />
                                        )}
                                    </div>
                                </button>

                                {/* Expanded Brainstorming Section */}
                                {expandedPrompt === index && (
                                    <div className="border-t border-[#E0DED8] bg-[#FAF8F5]">
                                        {/* Guiding Questions */}
                                        <div className="p-5">
                                            <div className="flex items-center gap-2 mb-3">
                                                <LightBulbIcon className="w-5 h-5 text-[#C05838]" />
                                                <h4 className="font-medium text-[#2C2C2C]">Questions to Guide Your Thinking</h4>
                                            </div>
                                            <ul className="space-y-3">
                                                {(prompt.brainstorming_questions || getDefaultBrainstormingQuestions(prompt.prompt)).map((q, i) => (
                                                    <li key={i} className="flex items-start gap-3 text-sm text-[#4A4A4A]">
                                                        <span className="w-5 h-5 bg-[#E0DED8] rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0 mt-0.5">
                                                            {i + 1}
                                                        </span>
                                                        <span>{q}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Brainstorm Notes */}
                                        <div className="p-5 border-t border-[#E0DED8]">
                                            <h4 className="font-medium text-[#2C2C2C] mb-3">✍️ Jot Down Your Thoughts</h4>
                                            <textarea
                                                value={brainstormNote}
                                                onChange={(e) => setBrainstormNote(e.target.value)}
                                                placeholder="Capture your ideas, memories, and reflections here..."
                                                rows={4}
                                                className="w-full px-4 py-3 border border-[#E0DED8] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20 focus:border-[#1A4D2E] resize-none text-sm"
                                            />
                                            <div className="flex justify-between items-center mt-3">
                                                <span className="text-xs text-[#6B6B6B]">
                                                    {savedNotes[index]?.length || 0} notes saved
                                                </span>
                                                <button
                                                    onClick={() => handleSaveNote(index)}
                                                    disabled={!brainstormNote.trim()}
                                                    className="px-4 py-2 bg-[#1A4D2E] text-white text-sm rounded-lg font-medium hover:bg-[#2D6B45] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                                >
                                                    Save Note
                                                </button>
                                            </div>

                                            {/* Saved Notes */}
                                            {savedNotes[index]?.length > 0 && (
                                                <div className="mt-4 space-y-2">
                                                    {savedNotes[index].map((note, i) => (
                                                        <div key={i} className="p-3 bg-white border border-[#E0DED8] rounded-lg text-sm text-[#4A4A4A]">
                                                            {note}
                                                        </div>
                                                    ))}
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
        </div>
    );
}
