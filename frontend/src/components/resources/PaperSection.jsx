import React from 'react';
import ReactMarkdown from 'react-markdown';
import { motion } from 'framer-motion';
import { getVisual } from './visuals';

// One section in a paper. Renders:
//   - a heading (with id for deep-link anchors)
//   - markdown body via react-markdown + tailwind prose styling
//   - optional inline visual after the body

const PaperSection = ({ section }) => {
    const Visual = section.visual?.component ? getVisual(section.visual.component) : null;

    return (
        <motion.section
            id={section.id}
            className="scroll-mt-24"
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-12% 0px' }}
            transition={{ duration: 0.5 }}
        >
            <h2 className="text-2xl sm:text-3xl font-bold text-[#1A2E1F] mb-5 mt-12 leading-tight">
                <a
                    href={`#${section.id}`}
                    className="group hover:text-[#1A4D2E] transition-colors no-underline"
                    aria-label={`Link to section: ${section.title}`}
                >
                    {section.title}
                    <span className="ml-2 text-[#C0BFB8] opacity-0 group-hover:opacity-100 transition-opacity text-base font-normal">
                        #
                    </span>
                </a>
            </h2>

            <div className="prose prose-emerald prose-lg max-w-none prose-p:text-[#4A4A4A] prose-p:leading-relaxed prose-strong:text-[#1A2E1F] prose-strong:font-semibold prose-li:text-[#4A4A4A] prose-li:leading-relaxed prose-a:text-[#1A4D2E] prose-code:text-[#1A4D2E] prose-code:bg-[#F2EFE6] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-medium prose-code:before:content-none prose-code:after:content-none">
                <ReactMarkdown>{section.body}</ReactMarkdown>
            </div>

            {Visual && (
                <div className="my-10">
                    <Visual {...(section.visual.props || {})} />
                </div>
            )}
        </motion.section>
    );
};

export default PaperSection;
