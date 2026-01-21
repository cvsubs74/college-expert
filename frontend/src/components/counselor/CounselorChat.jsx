
import React, { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../../context/AuthContext';
import { fetchCounselorChat, fetchStudentRoadmap } from '../../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const CounselorChat = () => {
    const { currentUser: user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [roadmapTitle, setRoadmapTitle] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    // Fetch roadmap on mount to get dynamic timeline title
    useEffect(() => {
        const loadRoadmap = async () => {
            if (!user?.email) return;

            try {
                const roadmap = await fetchStudentRoadmap(user.email);
                if (roadmap?.roadmap?.title) {
                    const title = roadmap.roadmap.title;
                    setRoadmapTitle(title);

                    // Set welcome message with dynamic title
                    setMessages([{
                        id: 1,
                        sender: 'agent',
                        text: `Hi there! I'm your AI Counselor. I've analyzed your profile and generated a roadmap for your **${title}**. Ready to look at your college list?`,
                        quickActions: [
                            { label: 'Show my Reach schools', action: 'Show my Reach schools' },
                            { label: 'Check deadlines', action: 'What are my upcoming deadlines?' }
                        ]
                    }]);
                } else {
                    // Fallback welcome message
                    setMessages([{
                        id: 1,
                        sender: 'agent',
                        text: "Hi there! I'm your AI Counselor. I've analyzed your profile and generated your personalized roadmap. Ready to look at your college list?",
                        quickActions: [
                            { label: 'Show my Reach schools', action: 'Show my Reach schools' },
                            { label: 'Check deadlines', action: 'What are my upcoming deadlines?' }
                        ]
                    }]);
                }
            } catch (error) {
                console.error('Failed to load roadmap for chat:', error);
                // Fallback welcome message
                setMessages([{
                    id: 1,
                    sender: 'agent',
                    text: "Hi there! I'm your AI Counselor. Ready to help you with your college admissions journey!",
                    quickActions: [
                        { label: 'Show my Reach schools', action: 'Show my Reach schools' },
                        { label: 'Check deadlines', action: 'What are my upcoming deadlines?' }
                    ]
                }]);
            }
        };

        loadRoadmap();
    }, [user]);

    const handleSend = async (manualMessage = null) => {
        const textToSend = manualMessage || inputValue;
        if (!textToSend.trim()) return;

        // Safety check for user
        if (!user || !user.email) {
            console.error("User not authenticated or email missing");
            const errorMsg = {
                id: Date.now(),
                sender: 'agent',
                text: "Please sign in to chat with the counselor.",
                quickActions: []
            };
            setMessages(prev => [...prev, errorMsg]);
            return;
        }

        // Add user message
        const userMsg = { id: Date.now(), sender: 'user', text: textToSend };
        setMessages(prev => [...prev, userMsg]);
        setInputValue('');
        setIsLoading(true);

        try {
            // Prepare history for context
            const history = messages
                .filter(m => m.id !== 1) // Skip welcome message
                .map(m => ({
                    role: m.sender === 'user' ? 'user' : 'model',
                    parts: [{ text: m.text }]
                }));

            const response = await fetchCounselorChat(user.email, textToSend, history);

            if (response && response.success) {
                const agentMsg = {
                    id: Date.now() + 1,
                    sender: 'agent',
                    text: response.reply,
                    quickActions: response.suggested_actions || []
                };
                setMessages(prev => [...prev, agentMsg]);
            } else {
                const errorMsg = {
                    id: Date.now() + 1,
                    sender: 'agent',
                    text: "I'm having a little trouble connecting to my brain right now. Please try again in a moment.",
                    quickActions: []
                };
                setMessages(prev => [...prev, errorMsg]);
            }
        } catch (error) {
            console.error("Chat error", error);
            const errorMsg = {
                id: Date.now() + 1,
                sender: 'agent',
                text: "I encountered an error. Please check your connection.",
                quickActions: []
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleQuickAction = (actionText) => {
        handleSend(actionText);
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') handleSend();
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-stone-100 bg-[#FDFCF7] flex items-center gap-2">
                <SparklesIcon className="h-5 w-5 text-[#1A4D2E]" />
                <h3 className="font-medium text-[#1A4D2E]">Counselor Assistant</h3>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-stone-50/30">
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                        <div
                            className={`
                max-w-[85%] p-3.5 rounded-2xl text-sm leading-relaxed
                ${msg.sender === 'user'
                                    ? 'bg-[#1A4D2E] text-white rounded-br-none'
                                    : 'bg-white border border-stone-200 text-stone-700 rounded-bl-none shadow-sm'}
              `}
                        >
                            {msg.sender === 'agent' ? (
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    className="prose prose-sm prose-stone max-w-none
                                        prose-headings:text-stone-800 prose-headings:font-medium
                                        prose-p:text-stone-700 prose-p:my-2
                                        prose-ul:my-2 prose-li:my-1
                                        prose-strong:text-stone-800 prose-strong:font-semibold"
                                >
                                    {msg.text}
                                </ReactMarkdown>
                            ) : (
                                <div className="whitespace-pre-wrap">{msg.text}</div>
                            )}
                        </div>

                        {/* Quick Actions (Nudge UI) */}
                        {msg.sender === 'agent' && msg.quickActions && msg.quickActions.length > 0 && (
                            <div className="mt-2 flex gap-2 flex-wrap max-w-[85%]">
                                {msg.quickActions.map((action, idx) => {
                                    // Determine button style based on action type
                                    const actionStr = (action.action || action.label || action).toLowerCase();
                                    let buttonClass = "text-xs px-3 py-1.5 rounded-full transition-colors border ";

                                    if (actionStr.includes('analyze') || actionStr.includes('show')) {
                                        buttonClass += "bg-blue-50 border-blue-300 text-blue-700 hover:bg-blue-100";
                                    } else if (actionStr.includes('deadline') || actionStr.includes('timeline')) {
                                        buttonClass += "bg-amber-50 border-amber-300 text-amber-700 hover:bg-amber-100";
                                    } else if (actionStr.includes('essay') || actionStr.includes('strengthen')) {
                                        buttonClass += "bg-purple-50 border-purple-300 text-purple-700 hover:bg-purple-100";
                                    } else {
                                        buttonClass += "bg-white border-[#1A4D2E]/20 text-[#1A4D2E] hover:bg-[#1A4D2E]/5";
                                    }

                                    return (
                                        <button
                                            key={idx}
                                            className={buttonClass}
                                            onClick={() => handleQuickAction(action.label || action.action || action)}
                                        >
                                            {action.label || action.action || action}
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                ))}

                {isLoading && (
                    <div className="flex flex-col items-start">
                        <div className="bg-white border border-stone-200 p-3.5 rounded-2xl rounded-bl-none shadow-sm flex items-center gap-2">
                            <div className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white border-t border-stone-100">
                <div className="relative">
                    <input
                        type="text"
                        className="w-full pl-4 pr-12 py-3 bg-stone-50 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#1A4D2E]/20 focus:border-[#1A4D2E] transition-all"
                        placeholder="Ask your counselor anything..."
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={isLoading}
                    />
                    <button
                        className="absolute right-2 top-2 p-1.5 text-[#1A4D2E] hover:bg-stone-100 rounded-lg transition-colors disabled:opacity-50"
                        onClick={() => handleSend()}
                        disabled={isLoading || !inputValue.trim()}
                    >
                        <PaperAirplaneIcon className="h-5 w-5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default CounselorChat;
