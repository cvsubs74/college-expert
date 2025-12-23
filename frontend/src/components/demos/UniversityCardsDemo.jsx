import React, { useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import { demoUniversities } from '../../data/demoData';

const UniversityCardsDemo = () => {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, amount: 0.3 });

    const [hoveredCard, setHoveredCard] = useState(null);
    const [savedCards, setSavedCards] = useState([]);

    useEffect(() => {
        if (!isInView) return;

        // Auto-save Princeton after 3 seconds
        const timeout = setTimeout(() => {
            setSavedCards(['princeton']);
        }, 3000);

        return () => clearTimeout(timeout);
    }, [isInView]);

    return (
        <div ref={ref} className="w-full max-w-4xl mx-auto">
            <div className="grid md:grid-cols-2 gap-4">
                {demoUniversities.slice(0, 4).map((university, index) => (
                    <motion.div
                        key={university.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={isInView ? { opacity: 1, y: 0 } : {}}
                        transition={{ delay: index * 0.1 }}
                        onMouseEnter={() => setHoveredCard(university.id)}
                        onMouseLeave={() => setHoveredCard(null)}
                        className="group relative"
                    >
                        <motion.div
                            whileHover={{ y: -4, scale: 1.02 }}
                            className="bg-white rounded-xl shadow-lg overflow-hidden border-2 border-[#E0DED8] hover:border-[#1A4D2E] transition-all cursor-pointer"
                        >
                            {/* Logo */}
                            <div className="h-40 overflow-hidden bg-white relative flex items-center justify-center p-6">
                                <img
                                    src={university.logoUrl}
                                    alt={university.name}
                                    className="max-h-32 max-w-full object-contain"
                                />
                                {/* Match score badge */}
                                <div className="absolute top-3 right-3 flex items-center gap-2">
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={isInView ? { scale: 1 } : {}}
                                        transition={{ delay: 0.3 + index * 0.1 }}
                                        className={`px-3 py-1.5 rounded-full font-bold text-sm shadow-lg ${university.fitCategory === 'Safety'
                                            ? 'bg-[#2E7D32] text-white'
                                            : university.fitCategory === 'Target'
                                                ? 'bg-[#FF8C42] text-white'
                                                : 'bg-[#C05838] text-white'
                                            }`}
                                    >
                                        {university.matchScore}%
                                    </motion.div>
                                </div>
                            </div>

                            {/* Content */}
                            <div className="p-5">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-[#1A4D2E] mb-1 line-clamp-1">
                                            {university.name}
                                        </h3>
                                        <p className="text-sm text-[#6B6B6B] flex items-center gap-1">
                                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                                            </svg>
                                            {university.location}
                                        </p>
                                    </div>
                                    <span className={`px-2 py-1 rounded text-xs font-semibold ${university.fitCategory === 'Safety'
                                        ? 'bg-[#E8F5E9] text-[#2E7D32]'
                                        : university.fitCategory === 'Target'
                                            ? 'bg-[#FFE6D5] text-[#FF8C42]'
                                            : 'bg-[#FCEEE8] text-[#C05838]'
                                        }`}>
                                        {university.fitCategory}
                                    </span>
                                </div>

                                {/* Stats */}
                                <div className="grid grid-cols-3 gap-3 mb-4">
                                    <div>
                                        <p className="text-xs text-[#6B6B6B]">Acceptance</p>
                                        <p className="text-sm font-bold text-[#1A4D2E]">{university.acceptanceRate}%</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-[#6B6B6B]">Ranking</p>
                                        <p className="text-sm font-bold text-[#1A4D2E]">#{university.ranking}</p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-[#6B6B6B]">Tuition</p>
                                        <p className="text-sm font-bold text-[#1A4D2E]">{university.tuition}</p>
                                    </div>
                                </div>

                                {/* Actions */}
                                <div className="flex gap-2">
                                    <motion.button
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        className="flex-1 px-4 py-2 bg-[#1A4D2E] text-white font-medium text-sm rounded-lg hover:bg-[#2D6B45] transition-colors"
                                    >
                                        Explore
                                    </motion.button>
                                    <motion.button
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        onClick={() => {
                                            if (savedCards.includes(university.id)) {
                                                setSavedCards(savedCards.filter(id => id !== university.id));
                                            } else {
                                                setSavedCards([...savedCards, university.id]);
                                            }
                                        }}
                                        className={`px-4 py-2 font-medium text-sm rounded-lg border-2 transition-all ${savedCards.includes(university.id)
                                            ? 'bg-[#FFE6D5] border-[#FF8C42] text-[#FF8C42]'
                                            : 'border-[#E0DED8] text-[#6B6B6B] hover:border-[#FF8C42] hover:text-[#FF8C42]'
                                            }`}
                                    >
                                        {savedCards.includes(university.id) ? (
                                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                                <path d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" />
                                            </svg>
                                        ) : (
                                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                                            </svg>
                                        )}
                                    </motion.button>
                                </div>
                            </div>

                            {/* Saved notification */}
                            {savedCards.includes(university.id) && (
                                <motion.div
                                    initial={{ opacity: 0, y: -10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    className="absolute -top-2 left-1/2 -translate-x-1/2 bg-[#2E7D32] text-white px-4 py-1.5 rounded-full text-xs font-medium shadow-lg whitespace-nowrap"
                                >
                                    ✓ Added to My Schools
                                </motion.div>
                            )}
                        </motion.div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

export default UniversityCardsDemo;
