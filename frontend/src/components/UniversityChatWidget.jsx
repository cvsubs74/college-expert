import React, { useState, useRef, useEffect } from 'react';
import {
    ChatBubbleLeftRightIcon,
    PaperAirplaneIcon,
    XMarkIcon,
    SparklesIcon,
    ClockIcon,
    PlusIcon,
    TrashIcon,
    ChevronDownIcon,
    PencilIcon,
    CheckIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../context/AuthContext';
import ConfirmationModal from './ConfirmationModal';

// API Configuration
const KNOWLEDGE_BASE_UNIVERSITIES_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL ||
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

const PROFILE_MANAGER_V2_URL = import.meta.env.VITE_PROFILE_MANAGER_V2_URL ||
    'https://profile-manager-v2-pfnwjfp26a-ue.a.run.app';

/**
 * UniversityChatWidget - A floating chat widget for asking questions about a university.
 * Uses context injection with Gemini to answer questions based on university data.
 * Now supports saving, loading, and continuing past conversations.
 * 
 * @param {string} universityId - The university ID to chat about
 * @param {string} universityName - Display name of the university
 * @param {boolean} isOpen - Whether the chat is currently open
 * @param {function} onClose - Callback to close the chat
 */
const UniversityChatWidget = ({ universityId, universityName, isOpen, onClose }) => {
    const { currentUser } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [conversationHistory, setConversationHistory] = useState([]);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    // Conversation history state
    const [savedConversations, setSavedConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [showHistory, setShowHistory] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false);

    // Rename state
    const [editingConversationId, setEditingConversationId] = useState(null);
    const [editTitle, setEditTitle] = useState('');

    // Delete confirmation state
    const [deleteConfirmation, setDeleteConfirmation] = useState({ isOpen: false, conversationId: null });

    // Dynamic suggested questions from AI response
    const [suggestedQuestions, setSuggestedQuestions] = useState([
        "What's the acceptance rate?",
        "What majors are popular?",
        "Tell me about campus life"
    ]);

    // Scroll to bottom when messages change
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen) {
            setTimeout(() => inputRef.current?.focus(), 100);
        }
    }, [isOpen]);

    // Reset chat and load history when university changes
    useEffect(() => {
        setMessages([]);
        setConversationHistory([]);
        setInput('');
        setCurrentConversationId(null);
        setShowHistory(false);
        if (isOpen && currentUser?.email && universityId) {
            loadConversationList();
        }
    }, [universityId]);

    // Load conversation list when widget opens
    useEffect(() => {
        if (isOpen && currentUser?.email && universityId) {
            loadConversationList();
        }
    }, [isOpen]);

    // Load saved conversations for this university
    const loadConversationList = async () => {
        if (!currentUser?.email) return;
        setLoadingHistory(true);
        try {
            const response = await fetch(`${PROFILE_MANAGER_V2_URL}/university-chat-load`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId
                })
            });
            const data = await response.json();
            if (data.success && data.messages?.length > 0) {
                // For university chat, we have one conversation per university
                setSavedConversations([{
                    conversation_id: universityId,
                    university_name: data.university_name || universityName,
                    title: data.university_name || universityName,
                    message_count: data.message_count || data.messages.length,
                    updated_at: new Date().toISOString()
                }]);
            } else {
                setSavedConversations([]);
            }
        } catch (error) {
            console.error('[UniversityChat] Failed to check for saved conversation:', error);
        }
        setLoadingHistory(false);
    };

    // Save current conversation (silent auto-save)
    const saveConversationSilent = async (msgs) => {
        if (!currentUser?.email || !msgs || msgs.length === 0) return;
        try {
            await fetch(`${PROFILE_MANAGER_V2_URL}/university-chat-save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    university_name: universityName,
                    messages: msgs
                })
            });
            setCurrentConversationId(universityId);
        } catch (error) {
            console.error('[UniversityChat] Silent save failed:', error);
        }
    };

    // Load saved conversation
    const loadConversation = async () => {
        if (!currentUser?.email) return;
        setLoadingHistory(true);
        try {
            const response = await fetch(`${PROFILE_MANAGER_V2_URL}/university-chat-load`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId
                })
            });
            const data = await response.json();
            if (data.success && data.messages?.length > 0) {
                setMessages(data.messages);
                setConversationHistory(data.messages);
                setCurrentConversationId(universityId);
                setShowHistory(false);
            }
        } catch (error) {
            console.error('[UniversityChat] Failed to load conversation:', error);
        }
        setLoadingHistory(false);
    };

    // Show delete confirmation modal
    const showDeleteConfirmation = (e) => {
        e.stopPropagation();
        setDeleteConfirmation({ isOpen: true, conversationId: universityId });
    };

    // Clear/delete conversation
    const clearConversation = async () => {
        if (!currentUser?.email) return;

        try {
            // Clear both locally and start fresh
            setMessages([]);
            setConversationHistory([]);
            setCurrentConversationId(null);
            setSavedConversations([]);
            setShowHistory(false);

            // Note: Backend doesn't have a delete endpoint for university chat yet,
            // so we just clear locally. Saving a new conversation will overwrite.
        } catch (error) {
            console.error('[UniversityChat] Failed to clear conversation:', error);
        }
    };

    // Start a new conversation
    const startNewConversation = () => {
        setMessages([]);
        setConversationHistory([]);
        setCurrentConversationId(null);
        setShowHistory(false);
    };

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setLoading(true);

        try {
            console.log('[UniversityChat] Sending chat request:', {
                university_id: universityId,
                question: userMessage,
                url: KNOWLEDGE_BASE_UNIVERSITIES_URL
            });

            const response = await fetch(KNOWLEDGE_BASE_UNIVERSITIES_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'chat',
                    university_id: universityId,
                    question: userMessage,
                    conversation_history: conversationHistory
                })
            });

            const data = await response.json();
            console.log('[UniversityChat] API response:', data);

            if (data.success) {
                const newMessages = [...messages,
                { role: 'user', content: userMessage },
                { role: 'assistant', content: data.answer }
                ];
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
                setConversationHistory(data.conversation_history || []);

                // Update suggested questions from AI response
                console.log('[UniversityChat] Suggested questions from API:', data.suggested_questions);
                if (data.suggested_questions && data.suggested_questions.length > 0) {
                    console.log('[UniversityChat] Setting suggested questions:', data.suggested_questions);
                    setSuggestedQuestions(data.suggested_questions);
                }

                // Auto-save after each exchange
                setTimeout(() => {
                    saveConversationSilent(newMessages);
                }, 100);
            } else {
                console.error('[UniversityChat] API error:', data.error);
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `Sorry, I couldn't get information about ${universityName}. ${data.error || ''}`
                }]);
            }
        } catch (error) {
            console.error('University chat error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.'
            }]);
        }
        setLoading(false);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Auto-submit a suggested question
    const handleSuggestedQuestion = async (question) => {
        if (loading) return;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: question }]);
        setLoading(true);

        try {
            console.log('[UniversityChat] Sending suggested question:', question);
            const response = await fetch(KNOWLEDGE_BASE_UNIVERSITIES_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'chat',
                    university_id: universityId,
                    question: question,
                    conversation_history: conversationHistory
                })
            });

            const data = await response.json();
            console.log('[UniversityChat] Suggested question response:', data);

            if (data.success) {
                const newMessages = [...messages,
                { role: 'user', content: question },
                { role: 'assistant', content: data.answer }
                ];
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
                setConversationHistory(data.conversation_history || []);

                // Update suggested questions from AI response
                console.log('[UniversityChat] New suggestions from API:', data.suggested_questions);
                if (data.suggested_questions && data.suggested_questions.length > 0) {
                    setSuggestedQuestions(data.suggested_questions);
                }

                // Auto-save
                setTimeout(() => {
                    saveConversationSilent(newMessages);
                }, 100);
            } else {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `Sorry, I couldn't get information about ${universityName}. ${data.error || ''}`
                }]);
            }
        } catch (error) {
            console.error('University chat error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.'
            }]);
        }
        setLoading(false);
    };

    // Format date for display
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const now = new Date();
        const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        return date.toLocaleDateString();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
            <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl flex flex-col max-h-[80vh] overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">
                {/* Header */}
                <div className="px-4 py-3 border-b bg-[#D6E8D5] flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] rounded-lg">
                            <SparklesIcon className="h-4 w-4 text-white" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900 text-sm">{universityName}</h3>
                            <p className="text-xs text-gray-500">AI-powered insights</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {/* History toggle */}
                        <button
                            onClick={() => setShowHistory(!showHistory)}
                            className={`p-1.5 rounded-lg transition-colors ${showHistory ? 'bg-white shadow-sm' : 'hover:bg-white/50'}`}
                            title="Conversation history"
                        >
                            <ClockIcon className={`h-5 w-5 ${showHistory ? 'text-[#1A4D2E]' : 'text-gray-500'}`} />
                        </button>
                        {/* New conversation */}
                        <button
                            onClick={startNewConversation}
                            className="p-1.5 hover:bg-white/50 rounded-lg transition-colors"
                            title="New conversation"
                        >
                            <PlusIcon className="h-5 w-5 text-gray-500" />
                        </button>
                        <button
                            onClick={onClose}
                            className="p-1.5 hover:bg-white/50 rounded-lg transition-colors"
                        >
                            <XMarkIcon className="h-5 w-5 text-gray-500" />
                        </button>
                    </div>
                </div>

                {/* Conversation History Dropdown */}
                {showHistory && (
                    <div className="border-b-2 border-gray-200 bg-white shadow-sm">
                        {/* Clickable header to collapse */}
                        <div
                            onClick={() => setShowHistory(false)}
                            className="flex items-center justify-between px-4 py-2 bg-gray-100 cursor-pointer hover:bg-gray-150 border-b border-gray-200"
                        >
                            <span className="text-xs font-medium text-gray-600">
                                {savedConversations.length > 0 ? 'Previous Conversation' : 'No saved conversation'}
                            </span>
                            <ChevronDownIcon className="h-4 w-4 text-gray-400 transform rotate-180" />
                        </div>
                        <div className="p-2 max-h-48 overflow-y-auto">
                            {loadingHistory ? (
                                <div className="text-center py-4 text-gray-400 text-sm">Loading...</div>
                            ) : savedConversations.length === 0 ? (
                                <div className="text-center py-4 text-gray-400 text-sm">No saved conversation yet. Start chatting!</div>
                            ) : (
                                <div className="space-y-1">
                                    {savedConversations.map((conv) => (
                                        <div
                                            key={conv.conversation_id}
                                            onClick={() => loadConversation()}
                                            className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${conv.conversation_id === currentConversationId
                                                ? 'bg-[#D6E8D5] border border-[#1A4D2E]'
                                                : 'hover:bg-gray-50'
                                                }`}
                                        >
                                            <div className="flex-1 min-w-0 mr-2">
                                                <p className="text-sm font-medium text-gray-800 truncate">
                                                    {conv.title || universityName}
                                                </p>
                                                <p className="text-xs text-gray-400">
                                                    {conv.message_count || 0} messages
                                                </p>
                                            </div>
                                            <button
                                                onClick={showDeleteConfirmation}
                                                className="p-1 hover:bg-red-100 rounded text-gray-400 hover:text-red-500 transition-colors"
                                                title="Clear conversation"
                                            >
                                                <TrashIcon className="h-4 w-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] bg-gray-50/50">
                    {messages.length === 0 ? (
                        <div className="text-center py-8">
                            <ChatBubbleLeftRightIcon className="h-10 w-10 mx-auto mb-3 text-[#1A4D2E] opacity-50" />
                            <p className="text-gray-600 text-sm mb-4">
                                Ask anything about {universityName}!
                            </p>
                            <div className="space-y-2">
                                {suggestedQuestions.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestedQuestion(q)}
                                        disabled={loading}
                                        className="block w-full text-left px-3 py-2 text-sm rounded-lg border border-gray-200 bg-white text-gray-700 hover:border-[#1A4D2E] hover:bg-[#D6E8D5] transition-colors disabled:opacity-50"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <>
                            {messages.map((msg, i) => (
                                <div
                                    key={i}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${msg.role === 'user'
                                        ? 'bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] text-white'
                                        : 'bg-white border border-gray-100 shadow-sm'
                                        }`}>
                                        {msg.role === 'assistant' ? (
                                            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0">
                                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                            </div>
                                        ) : (
                                            msg.content
                                        )}
                                    </div>
                                </div>
                            ))}

                            {/* Follow-up question suggestions */}
                            {!loading && messages.length > 0 && messages[messages.length - 1].role === 'assistant' && suggestedQuestions.length > 0 && (
                                <div className="pt-2 space-y-1.5">
                                    <p className="text-xs text-gray-400 px-1">Suggested follow-ups:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {suggestedQuestions.map((q, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSuggestedQuestion(q)}
                                                className="px-3 py-1.5 text-xs font-medium rounded-full border border-transparent bg-[#D6E8D5] text-[#1A4D2E] hover:opacity-80 transition-opacity text-left"
                                            >
                                                {q}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-white border border-gray-100 shadow-sm px-4 py-3 rounded-xl">
                                <div className="flex gap-1">
                                    <span className="w-2 h-2 rounded-full animate-bounce bg-[#1A4D2E]" style={{ animationDelay: '0ms' }} />
                                    <span className="w-2 h-2 rounded-full animate-bounce bg-[#1A4D2E]" style={{ animationDelay: '150ms' }} />
                                    <span className="w-2 h-2 rounded-full animate-bounce bg-[#1A4D2E]" style={{ animationDelay: '300ms' }} />
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-3 border-t bg-white">
                    <div className="flex gap-2">
                        <input
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value.slice(0, 500))}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask a question..."
                            maxLength={500}
                            className="flex-1 px-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1A4D2E] focus:ring-opacity-20 focus:border-[#1A4D2E] transition-all"
                            disabled={loading}
                        />
                        <button
                            onClick={sendMessage}
                            disabled={loading || !input.trim()}
                            className="p-2.5 bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] text-white rounded-xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
                        >
                            <PaperAirplaneIcon className="h-5 w-5" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            <ConfirmationModal
                isOpen={deleteConfirmation.isOpen}
                onClose={() => setDeleteConfirmation({ isOpen: false, conversationId: null })}
                onConfirm={clearConversation}
                title="Clear Conversation"
                message="Are you sure you want to clear this conversation? This action cannot be undone."
                confirmText="Clear"
                cancelText="Cancel"
                variant="danger"
            />
        </div>
    );
};

export default UniversityChatWidget;
