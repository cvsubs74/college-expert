import React, { useState, useRef, useEffect } from 'react';
import {
    ChatBubbleLeftRightIcon,
    PaperAirplaneIcon,
    XMarkIcon,
    SparklesIcon,
    AcademicCapIcon,
    ClockIcon,
    PlusIcon,
    TrashIcon,
    ChevronDownIcon,
    PencilIcon,
    CheckIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../context/AuthContext';

// API Configuration
const PROFILE_MANAGER_ES_URL = import.meta.env.VITE_PROFILE_MANAGER_ES_URL ||
    'https://profile-manager-es-pfnwjfp26a-ue.a.run.app';

/**
 * FitChatWidget - A floating chat widget for asking questions about fit analysis.
 * Uses context injection with Gemini to answer questions based on profile + fit data.
 * Now supports saving, loading, and continuing past conversations.
 * 
 * @param {string} universityId - The university ID to chat about
 * @param {string} universityName - Display name of the university
 * @param {string} fitCategory - The fit category (SAFETY, TARGET, REACH, SUPER_REACH)
 * @param {boolean} isOpen - Whether the chat is currently open
 * @param {function} onClose - Callback to close the chat
 */
const FitChatWidget = ({ universityId, universityName, fitCategory, isOpen, onClose }) => {
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
    const [savingConversation, setSavingConversation] = useState(false);

    // Rename state
    const [editingConversationId, setEditingConversationId] = useState(null);
    const [editTitle, setEditTitle] = useState('');

    // Fit category colors - Stratia theme consistency
    const fitColors = {
        'SAFETY': { bg: 'from-[#1A4D2E] to-[#2D6B45]', text: 'text-[#1A4D2E]', bgLight: 'bg-[#D6E8D5]' },
        'TARGET': { bg: 'from-[#1A4D2E] to-[#2D6B45]', text: 'text-[#1A4D2E]', bgLight: 'bg-[#D6E8D5]' },
        'REACH': { bg: 'from-[#C05838] to-[#D97858]', text: 'text-[#C05838]', bgLight: 'bg-[#FCEEE8]' },
        'SUPER_REACH': { bg: 'from-[#C05838] to-[#D97858]', text: 'text-[#C05838]', bgLight: 'bg-[#FCEEE8]' },
    };
    const colors = fitColors[fitCategory] || fitColors['TARGET'];

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
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-list`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    limit: 20
                })
            });
            const data = await response.json();
            if (data.success) {
                setSavedConversations(data.conversations || []);
            }
        } catch (error) {
            console.error('[FitChat] Failed to load conversation list:', error);
        }
        setLoadingHistory(false);
    };

    // Save current conversation
    const saveConversation = async () => {
        if (!currentUser?.email || messages.length === 0) return;
        setSavingConversation(true);
        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    university_name: universityName,
                    messages: messages,
                    conversation_id: currentConversationId
                })
            });
            const data = await response.json();
            if (data.success) {
                setCurrentConversationId(data.conversation_id);
                // Refresh conversation list
                loadConversationList();
            }
        } catch (error) {
            console.error('[FitChat] Failed to save conversation:', error);
        }
        setSavingConversation(false);
    };

    // Load a specific conversation
    const loadConversation = async (conversationId) => {
        if (!currentUser?.email) return;
        setLoadingHistory(true);
        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-load`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    conversation_id: conversationId
                })
            });
            const data = await response.json();
            if (data.success && data.conversation) {
                setMessages(data.conversation.messages || []);
                setCurrentConversationId(data.conversation.conversation_id);
                // Rebuild conversation history for API
                setConversationHistory(data.conversation.messages || []);
                // Keep history dropdown open so user can switch between conversations
            }
        } catch (error) {
            console.error('[FitChat] Failed to load conversation:', error);
        }
        setLoadingHistory(false);
    };

    // Delete a conversation
    const deleteConversation = async (conversationId, e) => {
        e.stopPropagation();
        if (!currentUser?.email) return;
        if (!confirm('Delete this conversation?')) return;

        try {
            await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    conversation_id: conversationId
                })
            });
            // If deleting current conversation, start fresh
            if (conversationId === currentConversationId) {
                startNewConversation();
            }
            loadConversationList();
        } catch (error) {
            console.error('[FitChat] Failed to delete conversation:', error);
        }
    };

    // Start editing a conversation title
    const startRename = (conv, e) => {
        e.stopPropagation();
        setEditingConversationId(conv.conversation_id);
        setEditTitle(conv.title || '');
    };

    // Save renamed title
    const saveRename = async (conversationId, e) => {
        e.stopPropagation();
        if (!currentUser?.email || !editTitle.trim()) {
            setEditingConversationId(null);
            return;
        }

        try {
            // Load the conversation first to get messages
            const loadResponse = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-load`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    conversation_id: conversationId
                })
            });
            const loadData = await loadResponse.json();

            if (loadData.success && loadData.conversation) {
                // Save with new title
                await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-save`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_email: currentUser.email,
                        university_id: loadData.conversation.university_id,
                        university_name: loadData.conversation.university_name,
                        messages: loadData.conversation.messages,
                        conversation_id: conversationId,
                        title: editTitle.trim()
                    })
                });
                loadConversationList();
            }
        } catch (error) {
            console.error('[FitChat] Failed to rename conversation:', error);
        }
        setEditingConversationId(null);
    };

    // Cancel rename
    const cancelRename = (e) => {
        e.stopPropagation();
        setEditingConversationId(null);
        setEditTitle('');
    };

    // Start a new conversation
    const startNewConversation = () => {
        setMessages([]);
        setConversationHistory([]);
        setCurrentConversationId(null);
        setShowHistory(false);
    };

    const sendMessage = async () => {
        if (!input.trim() || loading || !currentUser?.email) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setLoading(true);

        console.log('[FitChat] Sending message:', {
            user_email: currentUser.email,
            university_id: universityId,
            question: userMessage
        });

        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    question: userMessage,
                    conversation_history: conversationHistory
                })
            });

            const data = await response.json();
            console.log('[FitChat] Response:', response.status, data);

            if (data.success) {
                const newMessages = [...messages,
                { role: 'user', content: userMessage },
                { role: 'assistant', content: data.answer }
                ];
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
                setConversationHistory(data.conversation_history || []);

                // Auto-save after each exchange
                setTimeout(() => {
                    saveConversationSilent(newMessages);
                }, 100);
            } else {
                const errorMsg = data.error || 'Unknown error';
                console.error('[FitChat] Backend error:', errorMsg);
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `Sorry, I couldn't process your question. ${errorMsg}`
                }]);
            }
        } catch (error) {
            console.error('[FitChat] Network error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered a network error. Please try again.'
            }]);
        }
        setLoading(false);
    };

    // Silent auto-save (no loading indicator)
    const saveConversationSilent = async (msgs) => {
        if (!currentUser?.email || !msgs || msgs.length === 0) return;
        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat-save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    university_name: universityName,
                    messages: msgs,
                    conversation_id: currentConversationId
                })
            });
            const data = await response.json();
            if (data.success && !currentConversationId) {
                setCurrentConversationId(data.conversation_id);
            }
        } catch (error) {
            console.error('[FitChat] Silent save failed:', error);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Dynamic suggested questions based on fit category
    const getSuggestedQuestions = () => {
        const baseQuestions = [
            "Why am I this fit category?",
            "What can I improve?",
        ];

        if (fitCategory === 'SUPER_REACH' || fitCategory === 'REACH') {
            return [
                ...baseQuestions,
                "What are my chances of admission?",
                "How can I strengthen my application?",
            ];
        } else if (fitCategory === 'SAFETY') {
            return [
                ...baseQuestions,
                "Should I apply Early Decision?",
                "Will I get merit scholarships?",
            ];
        } else {
            return [
                ...baseQuestions,
                "What makes me a good fit?",
                "What specific programs stand out here?",
            ];
        }
    };

    // Follow-up questions after AI response (contextual based on conversation)
    const getFollowUpQuestions = () => {
        const messageCount = messages.length;

        // First round of follow-ups
        if (messageCount <= 2) {
            if (fitCategory === 'SUPER_REACH' || fitCategory === 'REACH') {
                return [
                    "What's the acceptance rate?",
                    "How can I improve my chances?",
                    "What makes a strong applicant?",
                ];
            } else if (fitCategory === 'SAFETY') {
                return [
                    "What scholarships are available?",
                    "What are the strongest programs?",
                    "Is Early Decision worth it?",
                ];
            } else {
                return [
                    "What makes me competitive?",
                    "Popular majors here?",
                    "Campus culture?",
                ];
            }
        }

        // Deeper follow-ups after more conversation
        return [
            "Tell me more about this",
            "What else should I know?",
            "How can I best demonstrate interest?",
        ];
    };

    // Auto-submit a suggested question
    const handleSuggestedQuestion = async (question) => {
        if (loading || !currentUser?.email) return;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: question }]);
        setLoading(true);

        console.log('[FitChat] Suggested question:', {
            user_email: currentUser.email,
            university_id: universityId,
            question: question
        });

        try {
            const response = await fetch(`${PROFILE_MANAGER_ES_URL}/fit-chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_email: currentUser.email,
                    university_id: universityId,
                    question: question,
                    conversation_history: conversationHistory
                })
            });

            const data = await response.json();
            console.log('[FitChat] Suggested question response:', response.status, data);

            if (data.success) {
                const newMessages = [...messages,
                { role: 'user', content: question },
                { role: 'assistant', content: data.answer }
                ];
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
                setConversationHistory(data.conversation_history || []);

                // Auto-save
                setTimeout(() => {
                    saveConversationSilent(newMessages);
                }, 100);
            } else {
                const errorMsg = data.error || 'Unknown error';
                console.error('[FitChat] Backend error:', errorMsg);
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `Sorry, I couldn't process your question. ${errorMsg}`
                }]);
            }
        } catch (error) {
            console.error('[FitChat] Network error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered a network error. Please try again.'
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
                <div className={`px-4 py-3 border-b ${colors.bgLight} flex items-center justify-between`}>
                    <div className="flex items-center gap-2">
                        <div className={`p-1.5 bg-gradient-to-br ${colors.bg} rounded-lg`}>
                            <AcademicCapIcon className="h-4 w-4 text-white" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900 text-sm">{universityName}</h3>
                            <div className="flex items-center gap-1.5">
                                <span className={`text-xs font-medium ${colors.text}`}>
                                    {fitCategory?.replace('_', ' ')} fit
                                </span>
                                <span className="text-xs text-gray-400">•</span>
                                <span className="text-xs text-gray-500">AI advisor</span>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        {/* History toggle */}
                        <button
                            onClick={() => setShowHistory(!showHistory)}
                            className={`p-1.5 rounded-lg transition-colors ${showHistory ? 'bg-white shadow-sm' : 'hover:bg-white/50'}`}
                            title="Conversation history"
                        >
                            <ClockIcon className={`h-5 w-5 ${showHistory ? colors.text : 'text-gray-500'}`} />
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
                            <span className="text-xs font-medium text-gray-600">Past Conversations ({savedConversations.length})</span>
                            <ChevronDownIcon className="h-4 w-4 text-gray-400 transform rotate-180" />
                        </div>
                        <div className="p-2 max-h-48 overflow-y-auto">
                            {loadingHistory ? (
                                <div className="text-center py-4 text-gray-400 text-sm">Loading...</div>
                            ) : savedConversations.length === 0 ? (
                                <div className="text-center py-4 text-gray-400 text-sm">No saved conversations yet</div>
                            ) : (
                                <div className="space-y-1">
                                    {savedConversations.map((conv) => (
                                        <div
                                            key={conv.conversation_id}
                                            onClick={() => editingConversationId !== conv.conversation_id && loadConversation(conv.conversation_id)}
                                            className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${conv.conversation_id === currentConversationId
                                                ? colors.bgLight + ' border border-current'
                                                : 'hover:bg-white'
                                                }`}
                                        >
                                            <div className="flex-1 min-w-0 mr-2">
                                                {editingConversationId === conv.conversation_id ? (
                                                    <input
                                                        type="text"
                                                        value={editTitle}
                                                        onChange={(e) => setEditTitle(e.target.value)}
                                                        onClick={(e) => e.stopPropagation()}
                                                        onKeyDown={(e) => {
                                                            if (e.key === 'Enter') saveRename(conv.conversation_id, e);
                                                            if (e.key === 'Escape') cancelRename(e);
                                                        }}
                                                        autoFocus
                                                        className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                                                        placeholder="Enter title..."
                                                    />
                                                ) : (
                                                    <p className="text-sm font-medium text-gray-800 truncate">
                                                        {conv.title || 'Untitled'}
                                                    </p>
                                                )}
                                                <p className="text-xs text-gray-400">
                                                    {formatDate(conv.updated_at)} • {conv.message_count || 0} messages
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-1">
                                                {editingConversationId === conv.conversation_id ? (
                                                    <>
                                                        <button
                                                            onClick={(e) => saveRename(conv.conversation_id, e)}
                                                            className="p-1 hover:bg-green-100 rounded text-gray-400 hover:text-green-600 transition-colors"
                                                            title="Save"
                                                        >
                                                            <CheckIcon className="h-4 w-4" />
                                                        </button>
                                                        <button
                                                            onClick={cancelRename}
                                                            className="p-1 hover:bg-gray-200 rounded text-gray-400 hover:text-gray-600 transition-colors"
                                                            title="Cancel"
                                                        >
                                                            <XMarkIcon className="h-4 w-4" />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <button
                                                            onClick={(e) => startRename(conv, e)}
                                                            className="p-1 hover:bg-blue-100 rounded text-gray-400 hover:text-blue-600 transition-colors"
                                                            title="Rename"
                                                        >
                                                            <PencilIcon className="h-4 w-4" />
                                                        </button>
                                                        <button
                                                            onClick={(e) => deleteConversation(conv.conversation_id, e)}
                                                            className="p-1 hover:bg-red-100 rounded text-gray-400 hover:text-red-500 transition-colors"
                                                            title="Delete"
                                                        >
                                                            <TrashIcon className="h-4 w-4" />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
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
                            <ChatBubbleLeftRightIcon className={`h-10 w-10 mx-auto mb-3 ${colors.text} opacity-50`} />
                            <p className="text-gray-600 text-sm mb-4">
                                Ask about your fit with {universityName}
                            </p>
                            <div className="space-y-2">
                                {getSuggestedQuestions().map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestedQuestion(q)}
                                        disabled={loading}
                                        className={`block w-full text-left px-3 py-2 text-sm text-gray-600 bg-white rounded-lg border border-gray-200 hover:border-current ${colors.text} hover:${colors.bgLight} transition-colors disabled:opacity-50`}
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
                                        ? `bg-gradient-to-r ${colors.bg} text-white`
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

                            {/* Follow-up question suggestions - show after last assistant message */}
                            {!loading && messages.length > 0 && messages[messages.length - 1].role === 'assistant' && (
                                <div className="pt-2 space-y-1.5">
                                    <p className="text-xs text-gray-400 px-1">Follow-up questions:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {getFollowUpQuestions().map((q, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSuggestedQuestion(q)}
                                                className={`px-3 py-1.5 text-xs font-medium rounded-full border border-gray-200 bg-white hover:bg-gray-50 ${colors.text} hover:border-current transition-colors`}
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
                                    <span className={`w-2 h-2 rounded-full animate-bounce bg-gradient-to-r ${colors.bg}`} style={{ animationDelay: '0ms' }} />
                                    <span className={`w-2 h-2 rounded-full animate-bounce bg-gradient-to-r ${colors.bg}`} style={{ animationDelay: '150ms' }} />
                                    <span className={`w-2 h-2 rounded-full animate-bounce bg-gradient-to-r ${colors.bg}`} style={{ animationDelay: '300ms' }} />
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
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Ask about your fit..."
                            className={`flex-1 px-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-opacity-20 focus:border-current transition-all`}
                            disabled={loading}
                        />
                        <button
                            onClick={sendMessage}
                            disabled={loading || !input.trim()}
                            className={`p-2.5 bg-gradient-to-r ${colors.bg} text-white rounded-xl hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg`}
                        >
                            <PaperAirplaneIcon className="h-5 w-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FitChatWidget;
