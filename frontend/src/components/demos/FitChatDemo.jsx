import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';

const FitChatDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.5 });

    const [messages, setMessages] = useState([]);
    const [isTyping, setIsTyping] = useState(false);
    const [currentMessageText, setCurrentMessageText] = useState('');

    const conversation = [
        {
            role: "user",
            message: "What are my chances at Stanford?"
        },
        {
            role: "assistant",
            message: "Based on your profile:\n\n• GPA: 3.85 (Stanford avg: 3.95)\n• SAT: 1450 (Stanford 25th-75th: 1470-1570)\n• Leadership: Debate Captain, Coding Club President\n\nYour match score is 82% - Stanford is a Reach school.\n\nStrengths:\n✓ Strong leadership roles\n✓ Competitive test scores\n✓ Well-rounded activities\n\nTo improve your chances:\n• Consider retaking SAT to reach 1500+\n• Highlight your unique debate achievements\n• Emphasize coding projects in essays"
        },
        {
            role: "user",
            message: "Should I apply early decision?"
        },
        {
            role: "assistant",
            message: "Stanford offers Restrictive Early Action (REA), not Early Decision.\n\nREA Advantages:\n• ~9% acceptance rate vs. ~4% regular\n• Non-binding - you can compare offers\n• Shows demonstrated interest\n\nConsider REA if:\n✓ Stanford is your top choice\n✓ Your application is ready by Nov 1\n✓ You don't need to compare financial aid\n\nYour profile is competitive for REA!"
        }
    ];

    useEffect(() => {
        if (!isInView) return;

        let messageIndex = 0;

        const showNextMessage = () => {
            if (messageIndex >= conversation.length) return;

            const currentMsg = conversation[messageIndex];

            if (currentMsg.role === 'user') {
                // Show user message immediately
                setMessages(prev => [...prev, currentMsg]);
                messageIndex++;
                setTimeout(showNextMessage, 800);
            } else {
                // Show typing indicator
                setIsTyping(true);

                setTimeout(() => {
                    setIsTyping(false);

                    // Type out AI response
                    const aiMessage = currentMsg.message;
                    let charIndex = 0;

                    const typingInterval = setInterval(() => {
                        if (charIndex < aiMessage.length) {
                            setCurrentMessageText(aiMessage.substring(0, charIndex + 1));
                            charIndex++;
                        } else {
                            clearInterval(typingInterval);
                            setMessages(prev => [...prev, currentMsg]);
                            setCurrentMessageText('');
                            messageIndex++;
                            setTimeout(showNextMessage, 1200);
                        }
                    }, 15);
                }, 1000);
            }
        };

        // Start conversation after 500ms
        setTimeout(showNextMessage, 500);
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-2xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-[#FF8C42] to-[#E67A2E] px-6 py-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="text-white font-semibold">Fit Chat</h3>
                        <p className="text-white/80 text-sm">Ask about your college chances</p>
                    </div>
                </div>

                {/* Chat messages */}
                <div className="p-6 space-y-4 min-h-[450px] max-h-[500px] overflow-y-auto bg-[#FDFCF7]">
                    {messages.map((msg, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 }}
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
                    {currentMessageText && (
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
                                            className="w-2 h-2 bg-[#FF8C42] rounded-full"
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
                            placeholder="Ask about your fit with any school..."
                            className="flex-1 px-4 py-3 border-2 border-[#E0DED8] rounded-xl focus:border-[#FF8C42] focus:outline-none transition-colors text-sm"
                            disabled
                        />
                        <button className="p-3 bg-[#FF8C42] text-white rounded-xl hover:bg-[#E67A2E] transition-colors">
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

export default FitChatDemo;
