import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoChatConversation } from '../../data/demoData';

const AIChatDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.5 });

    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [currentMessageText, setCurrentMessageText] = useState('');

    useEffect(() => {
        if (!isInView) return;

        // Show user message after 0.5s
        setTimeout(() => {
            setMessages([demoChatConversation[0]]);

            // Show typing indicator after 1s
            setTimeout(() => {
                setIsTyping(true);

                // Start typing AI response after 1.5s
                setTimeout(() => {
                    setIsTyping(false);
                    const aiMessage = demoChatConversation[1].message;
                    let charIndex = 0;

                    const typingInterval = setInterval(() => {
                        if (charIndex < aiMessage.length) {
                            setCurrentMessageText(aiMessage.substring(0, charIndex + 1));
                            charIndex++;
                        } else {
                            clearInterval(typingInterval);
                            setMessages([...demoChatConversation]);
                        }
                    }, 20);
                }, 1500);
            }, 1000);
        }, 500);
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-2xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45] px-6 py-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="text-white font-semibold">AI College Advisor</h3>
                        <p className="text-white/80 text-sm">Ask anything about any school</p>
                    </div>
                </div>

                {/* Chat messages */}
                <div className="p-6 space-y-4 min-h-[400px] bg-[#FDFCF7]">
                    {messages.map((msg, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.3 }}
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] ${msg.role === 'user'
                                        ? 'bg-[#1A4D2E] text-white'
                                        : 'bg-white border border-[#E0DED8]'
                                    } rounded-2xl px-5 py-3 shadow-sm`}
                            >
                                <p className={`text-sm leading-relaxed whitespace-pre-line ${msg.role === 'user' ? 'text-white' : 'text-[#1A4D2E]'
                                    }`}>
                                    {msg.message}
                                </p>
                            </div>
                        </motion.div>
                    ))}

                    {/* Typing animation for AI response */}
                    {currentMessageText && currentMessageText !== demoChatConversation[1].message && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex justify-start"
                        >
                            <div className="max-w-[85%] bg-white border border-[#E0DED8] rounded-2xl px-5 py-3 shadow-sm">
                                <p className="text-sm leading-relaxed whitespace-pre-line text-[#1A4D2E]">
                                    {currentMessageText}
                                    <motion.span
                                        className="inline-block w-0.5 h-4 bg-[#1A4D2E] ml-1"
                                        animate={{ opacity: [1, 0] }}
                                        transition={{ duration: 0.8, repeat: Infinity }}
                                    />
                                </p>
                            </div>
                        </motion.div>
                    )}

                    {/* Typing indicator */}
                    {isTyping && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex justify-start"
                        >
                            <div className="bg-white border border-[#E0DED8] rounded-2xl px-5 py-4 shadow-sm">
                                <div className="flex gap-1.5">
                                    {[0, 1, 2].map((i) => (
                                        <motion.div
                                            key={i}
                                            className="w-2 h-2 bg-[#1A4D2E] rounded-full"
                                            animate={{ y: [0, -8, 0] }}
                                            transition={{
                                                duration: 0.6,
                                                repeat: Infinity,
                                                delay: i * 0.1
                                            }}
                                        />
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </div>

                {/* Input box */}
                <div className="px-6 py-4 border-t border-[#E0DED8] bg-white">
                    <div className="flex items-center gap-3">
                        <input
                            type="text"
                            placeholder="Ask about majors, costs, campus life..."
                            className="flex-1 px-4 py-3 border-2 border-[#E0DED8] rounded-xl focus:border-[#1A4D2E] focus:outline-none transition-colors text-sm"
                            disabled
                        />
                        <button className="p-3 bg-[#1A4D2E] text-white rounded-xl hover:bg-[#2D6B45] transition-colors">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default AIChatDemo;
