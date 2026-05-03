import React, { useEffect } from 'react';
import { useParams, Link, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRightIcon } from '@heroicons/react/24/outline';
import { getPaperBySlug, papers } from '../data/resources';
import PaperHero from '../components/resources/PaperHero';
import PaperSection from '../components/resources/PaperSection';
import ResourcesHeader from '../components/resources/ResourcesHeader';

// /resources/<slug> — long-form reading view for a single whitepaper.
//
// Bookend layout:
//   - Hero (title, subtitle, hero visual)
//   - Sections (each with optional inline visual)
//   - Cross-promo footer (link to the other paper)

const ResourcePaperPage = () => {
    const { slug } = useParams();
    const paper = getPaperBySlug(slug);

    useEffect(() => {
        if (paper) {
            document.title = `${paper.title} — Stratia Resources`;
            // Update meta description for SEO + sharing
            let metaDesc = document.querySelector('meta[name="description"]');
            if (!metaDesc) {
                metaDesc = document.createElement('meta');
                metaDesc.setAttribute('name', 'description');
                document.head.appendChild(metaDesc);
            }
            metaDesc.setAttribute('content', paper.subtitle);
        }
    }, [paper]);

    // Scroll to anchor on mount if URL contains a hash
    useEffect(() => {
        if (typeof window !== 'undefined' && window.location.hash) {
            const id = window.location.hash.slice(1);
            const el = document.getElementById(id);
            if (el) {
                setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 250);
            }
        }
    }, [paper]);

    if (!paper) {
        return <Navigate to="/resources" replace />;
    }

    // Cross-promo: pick the next paper in the list (or wrap to first)
    const otherPaper =
        papers.find((p) => p.slug !== paper.slug) || null;

    return (
        <div className="min-h-screen bg-[#FDFCF7]">
            <ResourcesHeader />
            <PaperHero paper={paper} />

            <article className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-16">
                {paper.sections.map((section) => (
                    <PaperSection key={section.id} section={section} />
                ))}
            </article>

            {/* Cross-promo footer */}
            {otherPaper && (
                <section className="border-t border-[#E0DED8] bg-[#F8F6F0]">
                    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                        <motion.div
                            className="text-center"
                            initial={{ opacity: 0, y: 8 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5 }}
                        >
                            <div className="text-xs uppercase tracking-wider text-[#8A8A8A] font-semibold mb-3">
                                Read next
                            </div>
                            <h3 className="text-2xl sm:text-3xl font-bold text-[#1A2E1F] mb-3 leading-tight">
                                {otherPaper.title}
                            </h3>
                            <p className="text-[#4A4A4A] mb-6 max-w-xl mx-auto">
                                {otherPaper.subtitle}
                            </p>
                            <Link
                                to={`/resources/${otherPaper.slug}`}
                                className={`inline-flex items-center gap-2 px-6 py-3 rounded-full text-white font-semibold shadow-md hover:shadow-lg transition-all bg-gradient-to-r ${otherPaper.card.gradient}`}
                            >
                                Read paper
                                <ArrowRightIcon className="h-4 w-4" />
                            </Link>
                        </motion.div>
                    </div>
                </section>
            )}
        </div>
    );
};

export default ResourcePaperPage;
