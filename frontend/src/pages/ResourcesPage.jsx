import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { BookOpenIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { papers } from '../data/resources';
import PaperCard from '../components/resources/PaperCard';
import ResourcesHeader from '../components/resources/ResourcesHeader';

// /resources hub. Public-readable. Lists every whitepaper as a card.
//
// One card per paper today, with the design built to scale to a richer
// taxonomy (categories, type filters) later if the catalog grows past
// what fits on one page.

const ResourcesPage = () => {
    useEffect(() => {
        document.title = 'Resources — Stratia Admissions';
    }, []);

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            <ResourcesHeader />

            {/* Hero */}
            <section className="relative overflow-hidden border-b border-[#E0DED8]">
                <div
                    aria-hidden="true"
                    className="absolute inset-0 opacity-60"
                    style={{
                        background:
                            'radial-gradient(circle at 15% 25%, rgba(26,77,46,0.08) 0%, transparent 50%), radial-gradient(circle at 85% 75%, rgba(45,107,69,0.07) 0%, transparent 50%)',
                    }}
                />
                <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-20 text-center">
                    <motion.div
                        className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#D6E8D5] text-[#1A4D2E] text-xs font-semibold uppercase tracking-wider mb-6"
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                    >
                        <BookOpenIcon className="h-3.5 w-3.5" />
                        Resources
                    </motion.div>

                    <motion.h1
                        className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#1A2E1F] mb-5 leading-tight"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.1 }}
                    >
                        Why and how Stratia works
                    </motion.h1>

                    <motion.p
                        className="text-lg sm:text-xl text-[#4A4A4A] max-w-2xl mx-auto leading-relaxed"
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.2 }}
                    >
                        Two whitepapers, written for students, parents, and counselors. The first
                        explains the problem worth solving. The second walks through the algorithm
                        underneath the product.
                    </motion.p>

                    <motion.div
                        className="mt-6 inline-flex items-center gap-2 text-sm text-[#6B6B6B]"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                    >
                        <SparklesIcon className="h-4 w-4 text-[#1A4D2E]" />
                        Free to read · no signup · public links
                    </motion.div>
                </div>
            </section>

            {/* Paper grid */}
            <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
                    {papers.map((paper, i) => (
                        <PaperCard key={paper.slug} paper={paper} index={i} />
                    ))}
                </div>

                {/* Footer note */}
                <motion.div
                    className="mt-16 text-center text-sm text-[#6B6B6B]"
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                >
                    More papers in development. Have a topic you want to see covered? Tell your
                    counselor — or{' '}
                    <a href="/contact" className="text-[#1A4D2E] underline font-semibold">
                        reach out
                    </a>
                    .
                </motion.div>
            </section>
        </div>
    );
};

export default ResourcesPage;
