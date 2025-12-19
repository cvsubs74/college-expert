import React, { useState, useRef, useEffect } from 'react';
import {
    ChatBubbleLeftRightIcon,
    PaperAirplaneIcon,
    XMarkIcon,
    SparklesIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';

// API Configuration
const KNOWLEDGE_BASE_UNIVERSITIES_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL ||
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

/**
 * UniversityChatWidget - A floating chat widget for asking questions about a university.
 * Uses context injection with Gemini to answer questions based on university data.
 * 
 * @param {string} universityId - The university ID to chat about
 * @param {string} universityName - Display name of the university
 * @param {boolean} isOpen - Whether the chat is currently open
 * @param {function} onClose - Callback to close the chat
 */
const UniversityChatWidget = ({ universityId, universityName, isOpen, onClose }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [conversationHistory, setConversationHistory] = useState([]);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

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

    // Reset chat when university changes
    useEffect(() => {
        setMessages([]);
        setConversationHistory([]);
        setInput('');
    }, [universityId]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setLoading(true);

        try {
            console.log('[UniversityChatWidget] Sending chat request:', {
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
            console.log('[UniversityChatWidget] API response:', data);

            if (data.success) {
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
                setConversationHistory(data.conversation_history || []);
            } else {
                console.error('[UniversityChatWidget] API error:', data.error);
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

    // Suggested questions for initial state
    const suggestedQuestions = [
        "What's the acceptance rate?",
        "What majors are popular?",
        "Tell me about campus life",
        "What are the SAT/ACT requirements?"
    ];

    // Follow-up questions based on conversation
    const getFollowUpQuestions = () => {
        const messageCount = messages.length;

        // First round of follow-ups
        if (messageCount <= 2) {
            return [
                "Tuition & financial aid?",
                "Housing options?",
                "Career outcomes?",
            ];
        }

        // Second round
        if (messageCount <= 4) {
            return [
                "Application deadlines?",
                "Student life & clubs?",
                "Research opportunities?",
            ];
        }

        // Later rounds
        return [
            "Tell me more",
            "Compare to similar schools",
            "Why should I apply?",
        ];
    };

    // Auto-submit a suggested question
    const handleSuggestedQuestion = async (question) => {
        if (loading) return;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: question }]);
        setLoading(true);

        try {
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

            if (data.success) {
                setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
                setConversationHistory(data.conversation_history || []);
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

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
            <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl flex flex-col max-h-[80vh] overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-200">
                {/* Header */}
                <div className="px-4 py-3 border-b bg-gradient-to-r from-amber-50 to-orange-50 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-gradient-to-br from-amber-400 to-orange-500 rounded-lg">
                            <SparklesIcon className="h-4 w-4 text-white" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900 text-sm">{universityName}</h3>
                            <p className="text-xs text-gray-500">AI-powered insights</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-white/50 rounded-lg transition-colors"
                    >
                        <XMarkIcon className="h-5 w-5 text-gray-500" />
                    </button>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-[300px] bg-gray-50/50">
                    {messages.length === 0 ? (
                        <div className="text-center py-8">
                            <ChatBubbleLeftRightIcon className="h-10 w-10 text-amber-300 mx-auto mb-3" />
                            <p className="text-gray-600 text-sm mb-4">
                                Ask anything about {universityName}!
                            </p>
                            <div className="space-y-2">
                                {suggestedQuestions.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSuggestedQuestion(q)}
                                        disabled={loading}
                                        className="block w-full text-left px-3 py-2 text-sm text-gray-600 bg-white rounded-lg border border-gray-200 hover:border-amber-300 hover:bg-amber-50 transition-colors disabled:opacity-50"
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
                                        ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white'
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
                            {!loading && messages.length > 0 && messages[messages.length - 1].role === 'assistant' && (
                                <div className="pt-2 space-y-1.5">
                                    <p className="text-xs text-gray-400 px-1">Ask more:</p>
                                    <div className="flex flex-wrap gap-2">
                                        {getFollowUpQuestions().map((q, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSuggestedQuestion(q)}
                                                className="px-3 py-1.5 text-xs font-medium rounded-full border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 hover:border-amber-300 transition-colors"
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
                                    <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                    <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                    <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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
                            placeholder="Ask a question..."
                            className="flex-1 px-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-amber-500/20 focus:border-amber-400 transition-all"
                            disabled={loading}
                        />
                        <button
                            onClick={sendMessage}
                            disabled={loading || !input.trim()}
                            className="p-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl hover:from-amber-400 hover:to-orange-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
                        >
                            <PaperAirplaneIcon className="h-5 w-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UniversityChatWidget;
