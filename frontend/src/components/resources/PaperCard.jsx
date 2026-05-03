import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import * as HeroIcons from '@heroicons/react/24/outline';
import { ArrowRightIcon } from '@heroicons/react/24/outline';

// Card on the /resources hub. Each paper renders one of these.
//
// Pulls the icon from heroicons by name (so paper data files can reference
// 'ClockIcon' as a string instead of importing components into the data
// layer — keeps content authoring purely declarative).

const PaperCard = ({ paper, index = 0 }) => {
    const Icon = HeroIcons[paper.card.icon] || HeroIcons.DocumentTextIcon;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-10% 0px' }}
            transition={{ duration: 0.5, delay: 0.1 + index * 0.15 }}
        >
            <Link
                to={`/resources/${paper.slug}`}
                className="group block relative rounded-3xl bg-white border border-[#E0DED8] hover:border-[#1A4D2E]/40 transition-all overflow-hidden shadow-sm hover:shadow-xl"
                style={{ background: paper.card.bgPattern }}
            >
                {/* Top gradient strip */}
                <div className={`h-2 bg-gradient-to-r ${paper.card.gradient}`} />

                <div className="p-7 sm:p-8">
                    {/* Top row: icon + meta */}
                    <div className="flex items-start justify-between mb-5">
                        <div
                            className={`bg-gradient-to-br ${paper.card.gradient} p-3 rounded-2xl shadow-md`}
                        >
                            <Icon className="h-6 w-6 text-white" />
                        </div>
                        <div className="text-right">
                            <div className="text-[10px] uppercase tracking-wider text-[#8A8A8A] font-semibold">
                                {paper.type === 'whitepaper' ? 'White Paper' : paper.type}
                            </div>
                            <div className="text-xs text-[#6B6B6B] mt-0.5">{paper.readTime}</div>
                        </div>
                    </div>

                    {/* Title */}
                    <h3 className="text-xl sm:text-2xl font-bold text-[#1A2E1F] leading-tight mb-2 group-hover:text-[#1A4D2E] transition-colors">
                        {paper.title}
                    </h3>

                    {/* Subtitle */}
                    <p className="text-sm text-[#4A4A4A] mb-4 leading-relaxed font-medium">
                        {paper.subtitle}
                    </p>

                    {/* Description */}
                    <p className="text-sm text-[#6B6B6B] mb-6 leading-relaxed line-clamp-3">
                        {paper.description}
                    </p>

                    {/* Footer */}
                    <div className="flex items-center justify-between pt-4 border-t border-[#E0DED8]">
                        <div className="text-xs text-[#8A8A8A]">{paper.category}</div>
                        <div
                            className="inline-flex items-center gap-1 text-sm font-semibold transition-transform group-hover:translate-x-1"
                            style={{ color: paper.card.accentColor }}
                        >
                            Read paper
                            <ArrowRightIcon className="h-4 w-4" />
                        </div>
                    </div>
                </div>
            </Link>
        </motion.div>
    );
};

export default PaperCard;
