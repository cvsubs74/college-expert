import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoStudent } from '../../data/demoData';

const OnboardingDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.5 });

    const [name, setName] = useState('');
    const [selectedGrade, setSelectedGrade] = useState('');
    const [school, setSchool] = useState('');
    const [selectedState, setSelectedState] = useState('');

    useEffect(() => {
        if (!isInView) return;

        // Typing animation for name
        const nameText = demoStudent.name;
        let nameIndex = 0;
        const nameInterval = setInterval(() => {
            if (nameIndex < nameText.length) {
                setName(nameText.substring(0, nameIndex + 1));
                nameIndex++;
            } else {
                clearInterval(nameInterval);
                // Select grade after name is done
                setTimeout(() => setSelectedGrade(demoStudent.grade), 300);
            }
        }, 100);

        // Typing animation for school (starts after 2s)
        setTimeout(() => {
            const schoolText = demoStudent.school;
            let schoolIndex = 0;
            const schoolInterval = setInterval(() => {
                if (schoolIndex < schoolText.length) {
                    setSchool(schoolText.substring(0, schoolIndex + 1));
                    schoolIndex++;
                } else {
                    clearInterval(schoolInterval);
                    // Select state after school is done
                    setTimeout(() => setSelectedState(demoStudent.state), 300);
                }
            }, 80);
        }, 2000);

        return () => {
            clearInterval(nameInterval);
        };
    }, [isInView]);

    const grades = ['Freshman', 'Sophomore', 'Junior', 'Senior'];

    return (
        <div ref={ref} className="w-full max-w-md mx-auto">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={isInView ? { opacity: 1, scale: 1 } : {}}
                transition={{ duration: 0.5 }}
                className="bg-white rounded-2xl shadow-2xl p-8 border border-[#E0DED8]"
            >
                {/* Progress dots */}
                <div className="flex justify-center gap-2 mb-8">
                    {[0, 1, 2, 3].map((i) => (
                        <motion.div
                            key={i}
                            className={`h-2 rounded-full ${i === 0 ? 'w-8 bg-[#FF8C42]' : 'w-2 bg-[#E0DED8]'}`}
                            animate={{
                                width: i === 0 ? '2rem' : '0.5rem',
                                backgroundColor: i === 0 ? '#FF8C42' : '#E0DED8'
                            }}
                        />
                    ))}
                </div>

                {/* Icon */}
                <div className="w-14 h-14 rounded-full bg-[#FFF3E6] flex items-center justify-center mx-auto mb-6">
                    <svg className="w-7 h-7 text-[#FF8C42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>

                <h2 className="text-2xl font-bold text-[#1A4D2E] text-center mb-2">
                    Let's get started
                </h2>
                <p className="text-[#6B6B6B] text-center mb-8 text-sm">
                    Tell us a bit about yourself
                </p>

                {/* Name input */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-[#4A4A4A] mb-2">
                        Your name
                    </label>
                    <div className="relative">
                        <input
                            type="text"
                            value={name}
                            readOnly
                            className="w-full px-4 py-3 border-2 border-[#E0DED8] rounded-xl focus:border-[#FF8C42] focus:outline-none transition-colors"
                            placeholder="John Doe"
                        />
                        {isInView && name.length < demoStudent.name.length && (
                            <motion.div
                                className="absolute right-4 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[#1A4D2E]"
                                animate={{ opacity: [1, 0] }}
                                transition={{ duration: 0.8, repeat: Infinity }}
                            />
                        )}
                    </div>
                </div>

                {/* Grade selection */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-[#4A4A4A] mb-2">
                        Current grade
                    </label>
                    <div className="grid grid-cols-2 gap-3">
                        {grades.map((grade) => (
                            <motion.button
                                key={grade}
                                className={`px-4 py-3 rounded-xl border-2 font-medium text-sm transition-all ${selectedGrade === grade
                                        ? 'bg-[#FF8C42] border-[#FF8C42] text-white'
                                        : 'border-[#E0DED8] text-[#6B6B6B] hover:border-[#C4C4C4]'
                                    }`}
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                            >
                                {grade}
                            </motion.button>
                        ))}
                    </div>
                </div>

                {/* School input */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-[#4A4A4A] mb-2">
                        High school
                    </label>
                    <div className="relative">
                        <input
                            type="text"
                            value={school}
                            readOnly
                            className="w-full px-4 py-3 border-2 border-[#E0DED8] rounded-xl focus:border-[#FF8C42] focus:outline-none transition-colors"
                            placeholder="Monte Vista High School"
                        />
                        {isInView && school.length > 0 && school.length < demoStudent.school.length && (
                            <motion.div
                                className="absolute right-4 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[#1A4D2E]"
                                animate={{ opacity: [1, 0] }}
                                transition={{ duration: 0.8, repeat: Infinity }}
                            />
                        )}
                    </div>
                </div>

                {/* State dropdown */}
                <div className="mb-8">
                    <label className="block text-sm font-medium text-[#4A4A4A] mb-2">
                        State
                    </label>
                    <div className="relative">
                        <select
                            value={selectedState}
                            readOnly
                            className="w-full px-4 py-3 border-2 border-[#E0DED8] rounded-xl focus:border-[#FF8C42] focus:outline-none transition-colors appearance-none bg-white"
                        >
                            <option value="">Select state</option>
                            <option value="California">California</option>
                        </select>
                        <svg
                            className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#6B6B6B] pointer-events-none"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
                </div>

                {/* Continue button */}
                <motion.button
                    className="w-full py-4 bg-[#FF8C42] text-white font-semibold rounded-xl hover:bg-[#E67A2E] transition-colors flex items-center justify-center gap-2"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    animate={selectedState ? {
                        boxShadow: ['0 0 0 0 rgba(255, 140, 66, 0.4)', '0 0 0 10px rgba(255, 140, 66, 0)']
                    } : {}}
                    transition={{ duration: 1.5, repeat: Infinity }}
                >
                    Continue
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                </motion.button>

                <p className="text-center text-xs text-[#6B6B6B] mt-4">
                    Skip for now — I'll explore first
                </p>
            </motion.div>
        </div>
    );
};

export default OnboardingDemo;
