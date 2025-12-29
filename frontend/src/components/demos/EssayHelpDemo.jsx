import React, { useState, useEffect, useRef } from 'react';
import { motion, useInView, AnimatePresence } from 'framer-motion';
import {
    SparklesIcon,
    LightBulbIcon,
    DocumentTextIcon,
    ChevronDownIcon,
    ChevronUpIcon,
    ChatBubbleLeftRightIcon,
    CheckCircleIcon
} from '@heroicons/react/24/outline';

// Demo data - matching the real product experience
const demoPrompt = {
    type: "PIQ",
    word_limit: "350 words max",
    prompt: "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced."
};

const demoGuidingQuestions = [
    "What specific educational opportunity or barrier comes to mind?",
    "How did this experience change your perspective or approach to learning?",
    "What skills or insights did you gain that you still use today?"
];

const demoStarters = [
    "When I discovered MIT's OpenCourseWare during my freshman year, I realized that educational barriers could become launching pads...",
    "Growing up in a small town with no AP courses, I learned to create my own advanced curriculum...",
    "The moment my school library closed due to budget cuts, I became determined to build my own learning ecosystem..."
];

const demoEssayText = `Growing up in a small town with limited resources, I never had access to advanced computing courses. When I discovered MIT's OpenCourseWare during my freshman year, it transformed my educational journey.

I spent countless nights teaching myself data structures and algorithms through MIT's curriculum. When concepts felt overwhelming, I created study groups with classmates, becoming a peer tutor for others interested in computer science.

This self-directed learning taught me that barriers are often just opportunities in disguise. Today, I mentor middle schoolers through a coding club I founded, ensuring others won't face the same obstacles I did.`;

const demoFeedback = {
    overall_score: 8,
    prompt_alignment: 9,
    authenticity: 8,
    strengths: [
        "Strong narrative arc showing clear growth",
        "Specific details (MIT OCW, peer tutoring) add credibility",
        "Clear connection to current impact (coding club)"
    ],
    improvements: [
        "Add specific numbers (e.g., 'mentoring 12 middle schoolers')",
        "Briefly mention how this prepared you for Berkeley specifically"
    ],
    next_step: "Consider adding one sentence about how Berkeley's resources will help you expand this mission."
};

const EssayHelpDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.2 });

    const [step, setStep] = useState(0);
    // Steps: 0=idle, 1=prompt expanded, 2=show starters, 3=writing, 4=show feedback
    const [typedText, setTypedText] = useState('');
    const [wordCount, setWordCount] = useState(0);
    const [showStarters, setShowStarters] = useState(false);
    const [showFeedback, setShowFeedback] = useState(false);
    const [expandedPrompt, setExpandedPrompt] = useState(false);

    useEffect(() => {
        if (!isInView) return;

        const timeline = [
            // Step 1: Expand prompt (after 500ms)
            { delay: 500, action: () => setExpandedPrompt(true) },
            // Step 2: Show starters (after 1.5s)
            { delay: 1500, action: () => setShowStarters(true) },
            // Step 3: Start typing essay (after 2.5s)
            {
                delay: 2500, action: () => {
                    setStep(3);
                    let charIndex = 0;
                    const typingInterval = setInterval(() => {
                        if (charIndex < demoEssayText.length) {
                            const newText = demoEssayText.substring(0, charIndex + 1);
                            setTypedText(newText);
                            setWordCount(newText.split(/\s+/).filter(w => w).length);
                            charIndex += 4; // Type 4 chars at a time
                        } else {
                            clearInterval(typingInterval);
                            setTypedText(demoEssayText);
                            setWordCount(demoEssayText.split(/\s+/).filter(w => w).length);
                            // Step 4: Show feedback after typing completes
                            setTimeout(() => setShowFeedback(true), 1000);
                        }
                    }, 30);
                }
            }
        ];

        const timers = timeline.map(item =>
            setTimeout(item.action, item.delay)
        );

        return () => timers.forEach(t => clearTimeout(t));
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-2xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                className="bg-[#FDFCF7] rounded-2xl shadow-2xl overflow-hidden border border-[#E0DED8]"
            >
                {/* Header - matches real product */}
                <div className="bg-[#FDFCF7] border-b border-[#E0DED8] px-6 py-4">
                    <h3 className="font-serif text-xl font-semibold text-[#2C2C2C]">Essay Workshop</h3>
                    <p className="text-[#6B6B6B] text-sm">University of California, Berkeley</p>
                </div>

                {/* Philosophy Card - matches real product */}
                <div className="mx-4 mt-4 p-4 bg-gradient-to-r from-[#F8F6F0] to-[#FDFCF7] rounded-xl border border-[#E0DED8]">
                    <div className="flex items-start gap-3">
                        <div className="w-10 h-10 bg-[#D6E8D5] rounded-full flex items-center justify-center flex-shrink-0">
                            <SparklesIcon className="w-5 h-5 text-[#1A4D2E]" />
                        </div>
                        <div>
                            <h4 className="font-serif text-sm font-semibold text-[#2C2C2C] mb-1">Your AI Writing Partner</h4>
                            <p className="text-[#4A4A4A] text-xs leading-relaxed">
                                I help you discover your unique story and guide your writing.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Essay Prompt Card - matches real product */}
                <div className="m-4">
                    <div className="bg-white rounded-xl shadow-sm border border-[#E0DED8] overflow-hidden">
                        {/* Colored accent bar */}
                        <div className="h-1.5 bg-gradient-to-r from-[#1A4D2E] to-[#2D6B45]"></div>

                        {/* Prompt Header */}
                        <motion.button
                            onClick={() => setExpandedPrompt(!expandedPrompt)}
                            className="w-full p-4 flex items-start justify-between text-left hover:bg-[#FAFAF8] transition-colors"
                            animate={expandedPrompt ? {} : { backgroundColor: ['#FAFAF8', '#FFFFFF', '#FAFAF8'] }}
                            transition={{ duration: 2, repeat: expandedPrompt ? 0 : Infinity }}
                        >
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] text-xs font-medium rounded">
                                        {demoPrompt.type}
                                    </span>
                                    <span className="text-xs text-[#6B6B6B]">{demoPrompt.word_limit}</span>
                                </div>
                                <p className="text-[#2C2C2C] font-medium leading-relaxed text-sm">{demoPrompt.prompt}</p>
                            </div>
                            <div className="ml-3 flex-shrink-0">
                                {expandedPrompt ? (
                                    <ChevronUpIcon className="w-5 h-5 text-[#6B6B6B]" />
                                ) : (
                                    <ChevronDownIcon className="w-5 h-5 text-[#6B6B6B]" />
                                )}
                            </div>
                        </motion.button>

                        {/* Expanded Section */}
                        <AnimatePresence>
                            {expandedPrompt && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    transition={{ duration: 0.3 }}
                                    className="overflow-hidden"
                                >
                                    <div className="p-4 space-y-4 bg-[#FAFAF8] border-t border-[#E0DED8]">
                                        {/* Guiding Questions */}
                                        <div className="bg-white rounded-lg border border-[#E0DED8] p-4">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-6 h-6 bg-[#FFF3E0] rounded-lg flex items-center justify-center">
                                                    <LightBulbIcon className="w-4 h-4 text-[#C05838]" />
                                                </div>
                                                <h5 className="font-semibold text-[#2C2C2C] text-sm">Questions to Guide Your Thinking</h5>
                                            </div>
                                            <ul className="space-y-2">
                                                {demoGuidingQuestions.map((q, i) => (
                                                    <motion.li
                                                        key={i}
                                                        initial={{ opacity: 0, x: -10 }}
                                                        animate={{ opacity: 1, x: 0 }}
                                                        transition={{ delay: 0.2 + i * 0.15 }}
                                                        className="flex items-start gap-2 text-xs text-[#4A4A4A]"
                                                    >
                                                        <span className="w-5 h-5 bg-gradient-to-br from-[#C05838] to-[#E07050] text-white rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">
                                                            {i + 1}
                                                        </span>
                                                        <span className="leading-relaxed">{q}</span>
                                                    </motion.li>
                                                ))}
                                            </ul>
                                        </div>

                                        {/* Essay Starters */}
                                        <AnimatePresence>
                                            {showStarters && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    className="bg-white rounded-lg border border-[#E0DED8] p-4"
                                                >
                                                    <div className="flex items-center justify-between mb-3">
                                                        <div className="flex items-center gap-2">
                                                            <div className="w-6 h-6 bg-[#E8F5E9] rounded-lg flex items-center justify-center">
                                                                <SparklesIcon className="w-4 h-4 text-[#1A4D2E]" />
                                                            </div>
                                                            <h5 className="font-semibold text-[#2C2C2C] text-sm">Personalized Starters</h5>
                                                        </div>
                                                    </div>
                                                    <div className="space-y-2">
                                                        {demoStarters.map((starter, i) => (
                                                            <motion.div
                                                                key={i}
                                                                initial={{ opacity: 0, x: -10 }}
                                                                animate={{ opacity: 1, x: 0 }}
                                                                transition={{ delay: i * 0.2 }}
                                                                className="p-3 bg-gradient-to-r from-[#F0F9F0] to-[#FAFAF8] border border-[#D6E8D5] rounded-lg cursor-pointer hover:shadow-sm transition-shadow"
                                                            >
                                                                <p className="text-xs text-[#2C2C2C] leading-relaxed italic">{starter}</p>
                                                            </motion.div>
                                                        ))}
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>

                                        {/* Writing Area */}
                                        <div className="bg-white rounded-lg border border-[#E0DED8] p-4">
                                            <div className="flex items-center justify-between mb-3">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-6 h-6 bg-[#E8F5E9] rounded-lg flex items-center justify-center">
                                                        <DocumentTextIcon className="w-4 h-4 text-[#1A4D2E]" />
                                                    </div>
                                                    <h5 className="font-semibold text-[#2C2C2C] text-sm">Write Your Essay</h5>
                                                </div>
                                                <span className="text-xs text-[#6B6B6B] bg-[#F5F5F5] px-2 py-1 rounded">
                                                    {wordCount}/350 words
                                                </span>
                                            </div>

                                            {/* Essay text area with typing */}
                                            <div className="min-h-[120px] px-3 py-3 bg-[#FAFAF8] border border-[#E0DED8] rounded-lg">
                                                <p className="text-xs text-[#2C2C2C] leading-relaxed whitespace-pre-line">
                                                    {typedText}
                                                    {step === 3 && typedText.length < demoEssayText.length && (
                                                        <motion.span
                                                            className="inline-block w-0.5 h-3 bg-[#1A4D2E] ml-0.5"
                                                            animate={{ opacity: [1, 0] }}
                                                            transition={{ duration: 0.5, repeat: Infinity }}
                                                        />
                                                    )}
                                                </p>
                                            </div>

                                            {/* Action buttons */}
                                            <div className="flex flex-wrap gap-2 mt-3">
                                                <button className="px-3 py-1.5 bg-[#F8F6F0] border border-[#E0DED8] text-[#2C2C2C] text-xs rounded-lg flex items-center gap-1">
                                                    <ChatBubbleLeftRightIcon className="w-3 h-3" />
                                                    💡 Need a pointer?
                                                </button>
                                                <button className="px-3 py-1.5 bg-[#1A4D2E] text-white text-xs rounded-lg flex items-center gap-1">
                                                    <CheckCircleIcon className="w-3 h-3" />
                                                    Get Feedback
                                                </button>
                                                <button className="px-3 py-1.5 bg-[#2D6B45] text-white text-xs rounded-lg ml-auto">
                                                    💾 Save
                                                </button>
                                            </div>
                                        </div>

                                        {/* Feedback Panel */}
                                        <AnimatePresence>
                                            {showFeedback && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    className="bg-white border border-[#E0DED8] rounded-lg p-4"
                                                >
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h5 className="font-medium text-[#2C2C2C] text-sm">📊 Essay Feedback</h5>
                                                        <span className="px-2 py-0.5 bg-[#D6E8D5] text-[#1A4D2E] text-xs rounded font-medium">
                                                            Score: {demoFeedback.overall_score}/10
                                                        </span>
                                                    </div>

                                                    <div className="grid grid-cols-2 gap-3 mb-3 text-xs">
                                                        <div>
                                                            <span className="text-[#6B6B6B]">Prompt Alignment:</span>
                                                            <span className="ml-2 font-medium">{demoFeedback.prompt_alignment}/10</span>
                                                        </div>
                                                        <div>
                                                            <span className="text-[#6B6B6B]">Authenticity:</span>
                                                            <span className="ml-2 font-medium">{demoFeedback.authenticity}/10</span>
                                                        </div>
                                                    </div>

                                                    <div className="mb-3">
                                                        <p className="text-xs font-medium text-[#1A4D2E] mb-1">Strengths:</p>
                                                        <ul className="text-xs text-[#4A4A4A] space-y-1">
                                                            {demoFeedback.strengths.slice(0, 2).map((s, i) => (
                                                                <motion.li
                                                                    key={i}
                                                                    initial={{ opacity: 0 }}
                                                                    animate={{ opacity: 1 }}
                                                                    transition={{ delay: i * 0.2 }}
                                                                >
                                                                    ✓ {s}
                                                                </motion.li>
                                                            ))}
                                                        </ul>
                                                    </div>

                                                    <div className="mb-3">
                                                        <p className="text-xs font-medium text-[#C05838] mb-1">To Improve:</p>
                                                        <ul className="text-xs text-[#4A4A4A] space-y-1">
                                                            {demoFeedback.improvements.map((s, i) => (
                                                                <motion.li
                                                                    key={i}
                                                                    initial={{ opacity: 0 }}
                                                                    animate={{ opacity: 1 }}
                                                                    transition={{ delay: 0.4 + i * 0.2 }}
                                                                >
                                                                    → {s}
                                                                </motion.li>
                                                            ))}
                                                        </ul>
                                                    </div>

                                                    <div className="p-2 bg-[#F8F6F0] rounded text-xs text-[#2C2C2C]">
                                                        <strong>Next step:</strong> {demoFeedback.next_step}
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default EssayHelpDemo;
