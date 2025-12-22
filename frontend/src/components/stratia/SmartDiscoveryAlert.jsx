import React from 'react';
import { LightBulbIcon, ArrowRightIcon } from '@heroicons/react/24/outline';

/**
 * SmartDiscoveryAlert - Friendly alert card for college list suggestions
 * 
 * Replaces generic warning boxes with warm, academic-styled cards
 * Features:
 * - Pastel gold/terracotta background blend
 * - Serif headline for friendly tone
 * - Filled Tonal button for action
 */
const SmartDiscoveryAlert = ({
    hasNoSafety = false,
    isTooAmbitious = false,
    onFindSchools
}) => {
    if (!hasNoSafety && !isTooAmbitious) return null;

    const alertContent = hasNoSafety ? {
        headline: "Your list could use some balance!",
        body: "Adding a few safety schools can give you peace of mind and more options come decision day.",
        action: "Find Safety Schools",
        icon: LightBulbIcon
    } : {
        headline: "Your list is looking ambitious!",
        body: "Consider adding some target and safety schools to ensure you have great options.",
        action: "Build Balanced List",
        icon: LightBulbIcon
    };

    return (
        <section className="py-4">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div
                    className="stratia-card p-6 animate-fade-up"
                    style={{
                        background: 'linear-gradient(135deg, #FEF7F0 0%, #FCEEE8 50%, #FFF9F5 100%)',
                        border: '1px solid #E8A090'
                    }}
                >
                    <div className="flex items-start gap-4">
                        {/* Icon */}
                        <div className="flex-shrink-0 w-12 h-12 rounded-2xl bg-[#C05838]/10 flex items-center justify-center">
                            <alertContent.icon className="w-6 h-6 text-[#C05838]" />
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                            <h3 className="font-serif text-lg font-semibold text-[#2C2C2C] mb-1">
                                {alertContent.headline}
                            </h3>
                            <p className="text-sm text-[#4A4A4A] font-sans leading-relaxed">
                                {alertContent.body}
                            </p>
                        </div>

                        {/* Action Button */}
                        <div className="flex-shrink-0">
                            <button
                                onClick={onFindSchools}
                                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full font-sans font-semibold text-sm transition-all
                                    bg-[#C05838]/15 text-[#C05838] hover:bg-[#C05838]/25 hover:shadow-md"
                            >
                                {alertContent.action}
                                <ArrowRightIcon className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default SmartDiscoveryAlert;
