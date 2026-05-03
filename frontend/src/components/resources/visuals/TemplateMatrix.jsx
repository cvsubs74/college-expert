import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

// 4×3 grid: rows = grade (freshman → senior), columns = semester (fall, spring, summer)
// Cells with templates show the name. Summer cells (except junior_summer) show
// the fallback arrow. The "junior_spring" cell glows to anchor the worked example.

const GRADES = ['freshman', 'sophomore', 'junior', 'senior'];
const SEMESTERS = ['fall', 'spring', 'summer'];

// Maps to: { template_used, falls_back_to_spring? }
const cellFor = (grade, semester) => {
    if (semester === 'summer') {
        if (grade === 'junior') return { template: 'junior_summer', special: true };
        return { template: null, fallback: `${grade}_spring` };
    }
    return { template: `${grade}_${semester}` };
};

const isWorkedExample = (grade, semester) => grade === 'junior' && semester === 'spring';

const TemplateMatrix = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    return (
        <div ref={ref} className="w-full max-w-3xl mx-auto py-4">
            <div className="text-xs uppercase tracking-wider text-[#8A8A8A] font-semibold mb-3">
                The template grid · 9 hand-curated semesters
            </div>

            {/* Header */}
            <div className="grid grid-cols-[100px_repeat(3,1fr)] gap-2 mb-2">
                <div />
                {SEMESTERS.map((sem) => (
                    <div
                        key={sem}
                        className="text-xs font-semibold uppercase tracking-wide text-[#4A4A4A] text-center pb-1 border-b border-[#E0DED8]"
                    >
                        {sem}
                    </div>
                ))}
            </div>

            {/* Rows */}
            {GRADES.map((grade, rowIdx) => (
                <div key={grade} className="grid grid-cols-[100px_repeat(3,1fr)] gap-2 mb-2">
                    <div className="text-sm font-semibold text-[#1A4D2E] capitalize flex items-center">
                        {grade}
                    </div>
                    {SEMESTERS.map((sem, colIdx) => {
                        const cell = cellFor(grade, sem);
                        const worked = isWorkedExample(grade, sem);
                        const delay = 0.2 + rowIdx * 0.12 + colIdx * 0.08;

                        return (
                            <motion.div
                                key={`${grade}-${sem}`}
                                initial={{ opacity: 0, scale: 0.85 }}
                                animate={inView ? { opacity: 1, scale: 1 } : {}}
                                transition={{ duration: 0.4, delay }}
                                className={`relative rounded-lg p-3 min-h-[64px] flex items-center justify-center text-center text-xs font-medium border ${
                                    cell.template && worked
                                        ? 'bg-gradient-to-br from-emerald-500 to-teal-600 text-white border-transparent shadow-lg ring-2 ring-emerald-300'
                                        : cell.template
                                          ? cell.special
                                              ? 'bg-indigo-100 text-indigo-900 border-indigo-200'
                                              : 'bg-[#F8F6F0] text-[#1A4D2E] border-[#E0DED8]'
                                          : 'bg-white text-[#8A8A8A] border-dashed border-[#D0CFC8]'
                                }`}
                            >
                                {cell.template ? (
                                    <div>
                                        <div className="font-mono text-[11px]">{cell.template}</div>
                                        {worked && (
                                            <div className="text-[10px] mt-1 text-emerald-100">
                                                ← your example
                                            </div>
                                        )}
                                        {cell.special && (
                                            <div className="text-[10px] mt-1 text-indigo-700">
                                                summer-only template
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="text-[#8A8A8A]">
                                        <div className="text-[10px] italic">no template</div>
                                        <div className="text-[10px] font-mono mt-1">
                                            → {cell.fallback}
                                        </div>
                                    </div>
                                )}
                            </motion.div>
                        );
                    })}
                </div>
            ))}

            <motion.div
                className="mt-4 text-xs text-[#6B6B6B] text-center italic"
                initial={{ opacity: 0 }}
                animate={inView ? { opacity: 1 } : {}}
                transition={{ delay: 1.4 }}
            >
                Eight per-semester templates + one for the rising-senior summer.
                Other summers fall back to that grade's spring template.
            </motion.div>
        </div>
    );
};

export default TemplateMatrix;
