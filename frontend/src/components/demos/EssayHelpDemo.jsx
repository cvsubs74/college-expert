import React, { useState, useEffect, useRef } from 'react';
import { motion, useInView, AnimatePresence } from 'framer-motion';
import {
    DocumentTextIcon,
    SparklesIcon,
    CheckCircleIcon,
    PencilIcon,
    LightBulbIcon
} from '@heroicons/react/24/outline';

// Demo data - simulating the essay help experience
const demoEssayPrompt = {
    school: "UC Berkeley",
    prompt: "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
    wordLimit: 350
};

const demoEssayDraft = `Growing up in a small town with limited resources, I never had access to advanced computing courses. When I discovered MIT's OpenCourseWare during my freshman year, it transformed my educational journey.

I spent countless nights teaching myself data structures and algorithms through MIT's curriculum. When concepts felt overwhelming, I created study groups with classmates, becoming a peer tutor for others interested in computer science.

This self-directed learning taught me that barriers are often just opportunities in disguise. Today, I mentor middle schoolers through a coding club I founded, ensuring others won't face the same obstacles I did.`;

const demoFeedback = [
    {
        type: 'strength',
        icon: CheckCircleIcon,
        title: 'Strong personal narrative',
        text: 'You effectively show resilience and growth through a specific challenge.'
    },
    {
        type: 'suggestion',
        icon: LightBulbIcon,
        title: 'Add specific details',
        text: 'Include the name of your coding club and how many students you\'ve mentored to strengthen impact.'
    },
    {
        type: 'suggestion',
        icon: PencilIcon,
        title: 'Connect to UC Berkeley',
        text: 'Briefly mention how Berkeley\'s resources would help you continue this mission.'
    }
];

const EssayHelpDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.3 });

    const [step, setStep] = useState(0); // 0: prompt, 1: writing, 2: analyzing, 3: feedback
    const [typedText, setTypedText] = useState('');
    const [showFeedback, setShowFeedback] = useState([]);
    const [wordCount, setWordCount] = useState(0);

    useEffect(() => {
        if (!isInView) return;

        // Step 1: Show prompt selection (already visible)
        const timer1 = setTimeout(() => {
            setStep(1);
            // Start typing the essay
            let charIndex = 0;
            const typingInterval = setInterval(() => {
                if (charIndex < demoEssayDraft.length) {
                    const newText = demoEssayDraft.substring(0, charIndex + 1);
                    setTypedText(newText);
                    setWordCount(newText.split(/\s+/).filter(w => w).length);
                    charIndex += 3; // Type 3 chars at a time for speed
                } else {
                    clearInterval(typingInterval);
                    setTypedText(demoEssayDraft);
                    setWordCount(demoEssayDraft.split(/\s+/).filter(w => w).length);

                    // Step 2: Show analyzing state
                    setTimeout(() => {
                        setStep(2);

                        // Step 3: Show feedback one by one
                        setTimeout(() => {
                            setStep(3);
                            demoFeedback.forEach((_, idx) => {
                                setTimeout(() => {
                                    setShowFeedback(prev => [...prev, idx]);
                                }, idx * 400);
                            });
                        }, 1500);
                    }, 1000);
                }
            }, 25);
        }, 800);

        return () => clearTimeout(timer1);
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-2xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-[#8B5CF6] to-[#A78BFA] px-6 py-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                        <DocumentTextIcon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h3 className="text-white font-semibold">Essay Copilot</h3>
                        <p className="text-white/80 text-sm">AI-powered essay feedback</p>
                    </div>
                    <div className="ml-auto">
                        <span className="px-3 py-1 bg-white/20 rounded-full text-white text-xs font-medium">
                            {demoEssayPrompt.school}
                        </span>
                    </div>
                </div>

                {/* Essay Prompt */}
                <div className="px-6 py-4 bg-gradient-to-r from-[#FAF5FF] to-white border-b border-[#E9D5FF]">
                    <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-[#8B5CF6]/10 flex items-center justify-center flex-shrink-0">
                            <SparklesIcon className="w-4 h-4 text-[#8B5CF6]" />
                        </div>
                        <div>
                            <p className="text-sm font-medium text-[#7C3AED] mb-1">Personal Insight Question #4</p>
                            <p className="text-sm text-[#4A4A4A] leading-relaxed">{demoEssayPrompt.prompt}</p>
                            <p className="text-xs text-[#9CA3AF] mt-2">{demoEssayPrompt.wordLimit} words max</p>
                        </div>
                    </div>
                </div>

                {/* Essay Writing Area */}
                <div className="p-6 bg-[#FDFCF7] min-h-[280px]">
                    {/* Essay text with typing animation */}
                    <div className="bg-white rounded-xl border-2 border-[#E0DED8] p-4 min-h-[200px] relative">
                        <p className="text-sm text-[#1A4D2E] leading-relaxed whitespace-pre-line">
                            {typedText}
                            {step === 1 && (
                                <motion.span
                                    className="inline-block w-0.5 h-4 bg-[#8B5CF6] ml-1"
                                    animate={{ opacity: [1, 0] }}
                                    transition={{ duration: 0.5, repeat: Infinity }}
                                />
                            )}
                        </p>

                        {/* Word count badge */}
                        <div className="absolute bottom-3 right-3">
                            <span className={`text-xs font-medium px-2 py-1 rounded-full ${wordCount > demoEssayPrompt.wordLimit
                                    ? 'bg-red-100 text-red-600'
                                    : 'bg-[#E0DED8] text-[#4A4A4A]'
                                }`}>
                                {wordCount}/{demoEssayPrompt.wordLimit} words
                            </span>
                        </div>
                    </div>

                    {/* Analyzing indicator */}
                    <AnimatePresence>
                        {step === 2 && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mt-4 flex items-center justify-center gap-3 py-3"
                            >
                                <div className="flex gap-1">
                                    {[0, 1, 2].map((i) => (
                                        <motion.div
                                            key={i}
                                            className="w-2 h-2 bg-[#8B5CF6] rounded-full"
                                            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                                            transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                                        />
                                    ))}
                                </div>
                                <span className="text-sm text-[#8B5CF6] font-medium">Analyzing your essay...</span>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* AI Feedback Cards */}
                    <AnimatePresence>
                        {step === 3 && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="mt-4 space-y-3"
                            >
                                {demoFeedback.map((feedback, idx) => (
                                    <AnimatePresence key={idx}>
                                        {showFeedback.includes(idx) && (
                                            <motion.div
                                                initial={{ opacity: 0, x: -20 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                                                className={`flex items-start gap-3 p-3 rounded-xl ${feedback.type === 'strength'
                                                        ? 'bg-green-50 border border-green-200'
                                                        : 'bg-amber-50 border border-amber-200'
                                                    }`}
                                            >
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${feedback.type === 'strength'
                                                        ? 'bg-green-100'
                                                        : 'bg-amber-100'
                                                    }`}>
                                                    <feedback.icon className={`w-4 h-4 ${feedback.type === 'strength'
                                                            ? 'text-green-600'
                                                            : 'text-amber-600'
                                                        }`} />
                                                </div>
                                                <div>
                                                    <p className={`text-sm font-semibold ${feedback.type === 'strength'
                                                            ? 'text-green-800'
                                                            : 'text-amber-800'
                                                        }`}>
                                                        {feedback.title}
                                                    </p>
                                                    <p className={`text-xs mt-0.5 ${feedback.type === 'strength'
                                                            ? 'text-green-700'
                                                            : 'text-amber-700'
                                                        }`}>
                                                        {feedback.text}
                                                    </p>
                                                </div>
                                            </motion.div>
                                        )}
                                    </AnimatePresence>
                                ))}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-[#E0DED8] bg-white flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <SparklesIcon className="w-5 h-5 text-[#8B5CF6]" />
                        <span className="text-sm text-[#4A4A4A]">Powered by AI</span>
                    </div>
                    <button className="px-4 py-2 bg-[#8B5CF6] text-white text-sm font-medium rounded-lg hover:bg-[#7C3AED] transition-colors">
                        Get Feedback
                    </button>
                </div>
            </motion.div>
        </div>
    );
};

export default EssayHelpDemo;
