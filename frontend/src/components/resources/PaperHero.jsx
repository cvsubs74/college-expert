import React from 'react';
import { motion } from 'framer-motion';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import { getVisual } from './visuals';

// Hero block at the top of each paper page. Renders:
//  - back link
//  - paper title + subtitle
//  - read time + publish date
//  - the paper-specific hero visual underneath

const PaperHero = ({ paper }) => {
    const HeroVisual = paper.hero?.component ? getVisual(paper.hero.component) : null;

    return (
        <header className="relative">
            {/* Subtle background gradient pulled from the paper's accent */}
            <div
                aria-hidden="true"
                className="absolute inset-0"
                style={{ background: paper.card.bgPattern }}
            />

            <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-10">
                {/* Back link */}
                <Link
                    to="/resources"
                    className="inline-flex items-center gap-1 text-xs font-medium text-[#6B6B6B] hover:text-[#1A4D2E] transition-colors mb-8"
                >
                    <ArrowLeftIcon className="h-3.5 w-3.5" />
                    All resources
                </Link>

                {/* Meta row */}
                <motion.div
                    className="flex flex-wrap items-center gap-3 text-xs mb-4"
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                >
                    <span
                        className={`inline-flex items-center px-3 py-1 rounded-full text-white font-semibold uppercase tracking-wide bg-gradient-to-r ${paper.card.gradient}`}
                    >
                        {paper.type === 'whitepaper' ? 'White Paper' : paper.type}
                    </span>
                    <span className="text-[#6B6B6B]">{paper.readTime}</span>
                    <span className="text-[#8A8A8A]">·</span>
                    <span className="text-[#8A8A8A]">{paper.category}</span>
                </motion.div>

                {/* Title */}
                <motion.h1
                    className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[#1A2E1F] leading-tight mb-4"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                >
                    {paper.title}
                </motion.h1>

                {/* Subtitle */}
                <motion.p
                    className="text-lg sm:text-xl text-[#4A4A4A] leading-relaxed max-w-3xl"
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                >
                    {paper.subtitle}
                </motion.p>

                {/* Hero visual */}
                {HeroVisual && (
                    <motion.div
                        className="mt-10"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.6, delay: 0.4 }}
                    >
                        <HeroVisual />
                    </motion.div>
                )}
            </div>
        </header>
    );
};

export default PaperHero;
