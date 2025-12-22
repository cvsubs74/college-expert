import React from 'react';
import {
    AcademicCapIcon,
    SparklesIcon,
    ShieldCheckIcon
} from '@heroicons/react/24/outline';

/**
 * HeroSection - Welcoming greeting area with stats cards
 * 
 * Layout: 2-column grid (text left, illustration right on desktop)
 * Features:
 * - Large Serif headline greeting
 * - 3 elevated stat cards for school categories
 * - Illustration placeholder area
 */
const HeroSection = ({ userName = 'Student', stats = {} }) => {
    // Get time-appropriate greeting
    const getGreeting = () => {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 17) return 'Good afternoon';
        return 'Good evening';
    };

    const statCards = [
        {
            label: 'Super Reach',
            count: stats.superReach || 0,
            icon: SparklesIcon,
            color: 'tertiary', // Terracotta
            description: 'Dream schools'
        },
        {
            label: 'Target',
            count: stats.target || 0,
            icon: AcademicCapIcon,
            color: 'primary', // Forest Green
            description: 'Great matches'
        },
        {
            label: 'Safety',
            count: stats.safety || 0,
            icon: ShieldCheckIcon,
            color: 'secondary', // Sage
            description: 'Solid options'
        }
    ];

    const colorStyles = {
        tertiary: {
            bg: 'bg-[#FCEEE8]',
            text: 'text-[#C05838]',
            border: 'border-[#E8A090]'
        },
        primary: {
            bg: 'bg-[#D6E8D5]',
            text: 'text-[#1A4D2E]',
            border: 'border-[#A8C5A6]'
        },
        secondary: {
            bg: 'bg-[#E8F5E9]',
            text: 'text-[#2E7D32]',
            border: 'border-[#A5D6A7]'
        }
    };

    return (
        <section className="py-8 md:py-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
                    {/* Left: Greeting & Stats */}
                    <div className="space-y-8">
                        {/* Headline - Serif */}
                        <div className="space-y-3">
                            <h1 className="headline-large">
                                {getGreeting()}, {userName}.
                            </h1>
                            <p className="headline-medium text-[#4A4A4A]" style={{ fontWeight: 400 }}>
                                Your future is waiting.
                            </p>
                        </div>

                        {/* Stats Cards */}
                        <div className="grid grid-cols-3 gap-4">
                            {statCards.map((stat, index) => {
                                const colors = colorStyles[stat.color];
                                const Icon = stat.icon;

                                return (
                                    <div
                                        key={stat.label}
                                        className={`stratia-card p-4 text-center ${colors.bg} border ${colors.border} animate-fade-up`}
                                        style={{ animationDelay: `${index * 100}ms` }}
                                    >
                                        <Icon className={`w-6 h-6 mx-auto mb-2 ${colors.text}`} />
                                        <div className={`text-3xl font-bold ${colors.text} font-sans`}>
                                            {stat.count}
                                        </div>
                                        <div className="text-xs font-medium text-[#4A4A4A] mt-1">
                                            {stat.label}
                                        </div>
                                        <div className="text-xs text-[#6B6B6B] mt-0.5">
                                            {stat.description}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Right: Illustration Placeholder */}
                    <div className="hidden lg:flex items-center justify-center">
                        <div className="relative w-full max-w-md aspect-square">
                            {/* Decorative background circle */}
                            <div className="absolute inset-0 bg-gradient-to-br from-[#D6E8D5] to-[#FCEEE8] rounded-full opacity-50 animate-float" />

                            {/* Placeholder for illustration */}
                            <div className="absolute inset-8 flex items-center justify-center">
                                <div className="text-center space-y-4">
                                    {/* Telescope made of books - placeholder illustration */}
                                    <div className="relative mx-auto">
                                        <div className="w-24 h-8 bg-[#1A4D2E] rounded-lg transform -rotate-45 mb-2" />
                                        <div className="w-16 h-6 bg-[#2D6B45] rounded-md transform -rotate-45 -mt-4 ml-6" />
                                        <div className="w-12 h-4 bg-[#C05838] rounded-sm transform -rotate-45 -mt-3 ml-10" />
                                    </div>
                                    <div className="flex justify-center gap-2">
                                        <div className="w-8 h-12 bg-[#1A4D2E] rounded-sm" />
                                        <div className="w-8 h-14 bg-[#C05838] rounded-sm" />
                                        <div className="w-8 h-10 bg-[#2D6B45] rounded-sm" />
                                    </div>
                                    <p className="text-sm text-[#4A4A4A] font-sans">
                                        Your college journey starts here
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default HeroSection;
