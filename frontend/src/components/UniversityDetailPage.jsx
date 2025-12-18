import React, { useState, useEffect, useRef } from 'react';
import {
    ArrowLeftIcon,
    MapPinIcon,
    AcademicCapIcon,
    CurrencyDollarIcon,
    ChartBarIcon,
    SparklesIcon,
    PlayCircleIcon,
    ChevronDownIcon,
    CheckCircleIcon,
    CalendarIcon,
    BriefcaseIcon,
    BuildingLibraryIcon,
    GlobeAltIcon,
    PhotoIcon,
    StarIcon,
    TrophyIcon
} from '@heroicons/react/24/outline';
import { StarIcon as StarSolid } from '@heroicons/react/24/solid';

// Format numbers with commas
const formatNumber = (num) => {
    if (num === 'N/A' || num === null || num === undefined) return 'N/A';
    return typeof num === 'number' ? num.toLocaleString() : num;
};

// Section Navigation Dot Component
const NavDot = ({ section, isActive, onClick }) => (
    <button
        onClick={onClick}
        className={`group flex items-center gap-2 transition-all duration-300 ${isActive ? 'scale-110' : ''}`}
        title={section.label}
    >
        <span className={`w-3 h-3 rounded-full transition-all duration-300 ${isActive
                ? 'bg-blue-600 shadow-lg shadow-blue-500/50'
                : 'bg-gray-300 hover:bg-gray-400'
            }`} />
        <span className={`text-xs font-medium transition-all duration-300 hidden lg:block ${isActive ? 'text-blue-600 opacity-100' : 'text-gray-400 opacity-0 group-hover:opacity-100'
            }`}>
            {section.label}
        </span>
    </button>
);

// Floating Glass Card Component
const GlassCard = ({ children, className = '' }) => (
    <div className={`bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-white/20 ${className}`}>
        {children}
    </div>
);

// Stat Card Component
const StatCard = ({ label, value, subtext, icon: Icon, color = 'blue' }) => {
    const colors = {
        blue: 'from-blue-500 to-blue-600',
        green: 'from-green-500 to-green-600',
        purple: 'from-purple-500 to-purple-600',
        amber: 'from-amber-500 to-amber-600',
    };

    return (
        <div className="bg-white rounded-2xl p-5 shadow-lg border border-gray-100 hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
            <div className="flex items-start justify-between mb-2">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</span>
                {Icon && (
                    <div className={`p-2 rounded-xl bg-gradient-to-br ${colors[color]} shadow-lg`}>
                        <Icon className="h-4 w-4 text-white" />
                    </div>
                )}
            </div>
            <div className="text-3xl font-bold text-gray-900 mb-1">{value}</div>
            {subtext && <p className="text-xs text-gray-500">{subtext}</p>}
        </div>
    );
};

// Section Header Component
const SectionHeader = ({ icon: Icon, title, subtitle, id }) => (
    <div id={id} className="scroll-mt-24 mb-8">
        <div className="flex items-center gap-3 mb-2">
            {Icon && (
                <div className="p-3 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg">
                    <Icon className="h-6 w-6 text-white" />
                </div>
            )}
            <div>
                <h2 className="text-2xl md:text-3xl font-bold text-gray-900">{title}</h2>
                {subtitle && <p className="text-gray-500 text-sm mt-1">{subtitle}</p>}
            </div>
        </div>
    </div>
);

// Media Carousel Component
const MediaShowcase = ({ media }) => {
    const [activeIndex, setActiveIndex] = useState(0);

    if (!media) return null;

    const infographics = media.infographics || [];
    const videos = media.videos || [];
    const allMedia = [...infographics.map(i => ({ ...i, type: 'image' })), ...videos.map(v => ({ ...v, type: 'video' }))];

    if (allMedia.length === 0) return null;

    return (
        <div className="relative">
            {/* Main Display */}
            <div className="aspect-video bg-gray-900 rounded-2xl overflow-hidden shadow-2xl">
                {allMedia[activeIndex]?.type === 'video' ? (
                    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-800 to-gray-900">
                        <a
                            href={allMedia[activeIndex].url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex flex-col items-center gap-4 text-white hover:scale-105 transition-transform"
                        >
                            <PlayCircleIcon className="h-20 w-20 text-white/80" />
                            <span className="text-lg font-medium">{allMedia[activeIndex].title}</span>
                        </a>
                    </div>
                ) : (
                    <img
                        src={allMedia[activeIndex]?.url}
                        alt={allMedia[activeIndex]?.title}
                        className="w-full h-full object-contain bg-gray-100"
                    />
                )}
            </div>

            {/* Thumbnails */}
            {allMedia.length > 1 && (
                <div className="flex gap-3 mt-4 overflow-x-auto pb-2">
                    {allMedia.map((item, idx) => (
                        <button
                            key={idx}
                            onClick={() => setActiveIndex(idx)}
                            className={`flex-shrink-0 w-24 h-16 rounded-lg overflow-hidden border-2 transition-all ${idx === activeIndex
                                    ? 'border-blue-500 shadow-lg scale-105'
                                    : 'border-transparent opacity-60 hover:opacity-100'
                                }`}
                        >
                            {item.type === 'video' ? (
                                <div className="w-full h-full bg-gray-800 flex items-center justify-center">
                                    <PlayCircleIcon className="h-8 w-8 text-white" />
                                </div>
                            ) : (
                                <img src={item.url} alt="" className="w-full h-full object-cover" />
                            )}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

// Main University Detail Page Component
const UniversityDetailPage = ({ uni, onBack, sentiment, fitAnalysis }) => {
    const [activeSection, setActiveSection] = useState('hero');
    const containerRef = useRef(null);

    if (!uni) return null;

    const profile = uni.fullProfile || {};
    const strategic = profile.strategic_profile || {};
    const admissions = profile.admissions_data || {};
    const academic = profile.academic_structure || {};
    const financials = profile.financials || {};
    const outcomes = profile.outcomes || {};
    const studentInsights = profile.student_insights || {};
    const appProcess = profile.application_process || {};

    const sections = [
        { id: 'hero', label: 'Overview' },
        { id: 'media', label: 'Visual Guide' },
        { id: 'academics', label: 'Academics' },
        { id: 'admissions', label: 'Admissions' },
        { id: 'financials', label: 'Financials' },
        { id: 'outcomes', label: 'Outcomes' },
        { id: 'campus', label: 'Campus' },
    ];

    const scrollToSection = (sectionId) => {
        const element = document.getElementById(sectionId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    // Intersection Observer for active section tracking
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        setActiveSection(entry.target.id);
                    }
                });
            },
            { threshold: 0.3, rootMargin: '-100px 0px -50% 0px' }
        );

        sections.forEach(({ id }) => {
            const element = document.getElementById(id);
            if (element) observer.observe(element);
        });

        return () => observer.disconnect();
    }, []);

    return (
        <div ref={containerRef} className="relative bg-gray-50 min-h-screen">
            {/* Floating Navigation Dots */}
            <div className="fixed right-6 top-1/2 -translate-y-1/2 z-50 hidden md:flex flex-col gap-4 p-3 bg-white/80 backdrop-blur-md rounded-2xl shadow-lg border border-gray-200">
                {sections.map((section) => (
                    <NavDot
                        key={section.id}
                        section={section}
                        isActive={activeSection === section.id}
                        onClick={() => scrollToSection(section.id)}
                    />
                ))}
            </div>

            {/* Back Button */}
            <button
                onClick={onBack}
                className="fixed top-6 left-6 z-50 p-3 bg-white/90 backdrop-blur-md hover:bg-white rounded-full shadow-lg border border-gray-200 transition-all hover:scale-105"
            >
                <ArrowLeftIcon className="h-5 w-5 text-gray-700" />
            </button>

            {/* ========== HERO SECTION ========== */}
            <section id="hero" className="relative min-h-[80vh] flex items-end">
                {/* Background */}
                <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-indigo-700 to-purple-800">
                    {/* Decorative pattern */}
                    <div className="absolute inset-0 opacity-10" style={{
                        backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
                    }} />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                </div>

                {/* Hero Content */}
                <div className="relative z-10 w-full px-6 md:px-12 lg:px-20 pb-12">
                    <div className="max-w-7xl mx-auto">
                        {/* Badges */}
                        <div className="flex flex-wrap gap-2 mb-4">
                            <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-white/20 text-white backdrop-blur-sm border border-white/20">
                                {uni.location.type}
                            </span>
                            <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-white/20 text-white backdrop-blur-sm border border-white/20 flex items-center gap-1">
                                <MapPinIcon className="h-3 w-3" /> {uni.location.city}, {uni.location.state}
                            </span>
                            {uni.rankings.usNews !== 'N/A' && (
                                <span className="px-3 py-1.5 rounded-full text-xs font-bold bg-amber-400 text-amber-900 flex items-center gap-1">
                                    <TrophyIcon className="h-3 w-3" /> #{uni.rankings.usNews} US News
                                </span>
                            )}
                        </div>

                        {/* Title */}
                        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold text-white mb-3 leading-tight">
                            {uni.name}
                        </h1>
                        <p className="text-xl md:text-2xl text-blue-100 font-medium mb-8 max-w-3xl">
                            {uni.market_position}
                        </p>

                        {/* Floating Stats Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 -mb-24">
                            <GlassCard className="p-5 text-center hover:scale-105 transition-transform">
                                <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Acceptance</div>
                                <div className="text-3xl font-bold text-gray-900">
                                    {uni.admissions.acceptanceRate !== 'N/A' ? `${uni.admissions.acceptanceRate}%` : 'N/A'}
                                </div>
                                <div className="w-full bg-gray-200 h-1.5 mt-2 rounded-full overflow-hidden">
                                    <div
                                        className="bg-gradient-to-r from-green-400 to-green-600 h-full rounded-full"
                                        style={{ width: `${uni.admissions.acceptanceRate || 0}%` }}
                                    />
                                </div>
                            </GlassCard>

                            <GlassCard className="p-5 text-center hover:scale-105 transition-transform">
                                <div className="text-xs font-semibold text-gray-500 uppercase mb-1">US News Rank</div>
                                <div className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                                    {uni.rankings.usNews !== 'N/A' ? `#${uni.rankings.usNews}` : 'N/A'}
                                </div>
                            </GlassCard>

                            <GlassCard className="p-5 text-center hover:scale-105 transition-transform">
                                <div className="text-xs font-semibold text-gray-500 uppercase mb-1">Total Cost</div>
                                <div className="text-3xl font-bold text-gray-900">
                                    ${formatNumber(uni.financials.outStateCOA)}
                                </div>
                                <div className="text-xs text-gray-500 mt-1">Out-of-state</div>
                            </GlassCard>

                            <GlassCard className="p-5 text-center hover:scale-105 transition-transform">
                                <div className="text-xs font-semibold text-gray-500 uppercase mb-1">10yr Earnings</div>
                                <div className="text-3xl font-bold text-green-600">
                                    ${formatNumber(uni.outcomes.medianEarnings)}
                                </div>
                                <div className="text-xs text-gray-500 mt-1">Median salary</div>
                            </GlassCard>
                        </div>
                    </div>
                </div>

                {/* Scroll Indicator */}
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 animate-bounce">
                    <ChevronDownIcon className="h-8 w-8 text-white/60" />
                </div>
            </section>

            {/* Content Wrapper */}
            <div className="relative z-10 pt-32 pb-20 px-6 md:px-12 lg:px-20">
                <div className="max-w-6xl mx-auto space-y-24">

                    {/* ========== EXECUTIVE SUMMARY ========== */}
                    <section className="bg-white rounded-3xl p-8 md:p-10 shadow-xl border border-gray-100">
                        <div className="flex items-start gap-4 mb-6">
                            <div className="p-3 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg">
                                <SparklesIcon className="h-6 w-6 text-white" />
                            </div>
                            <div className="flex-1">
                                <h2 className="text-2xl font-bold text-gray-900 mb-2">Executive Summary</h2>
                                <p className="text-gray-600 leading-relaxed text-lg">
                                    {uni.summary || strategic.executive_summary}
                                </p>
                            </div>
                        </div>

                        {/* Strategic Takeaways */}
                        {strategic.analyst_takeaways && strategic.analyst_takeaways.length > 0 && (
                            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                                {strategic.analyst_takeaways.map((takeaway, idx) => (
                                    <div key={idx} className="bg-gradient-to-br from-gray-50 to-gray-100 p-5 rounded-2xl border border-gray-200">
                                        <span className="text-xs font-bold text-blue-600 uppercase tracking-wide">{takeaway.category}</span>
                                        <p className="text-gray-800 font-medium mt-2 mb-2">{takeaway.insight}</p>
                                        <p className="text-sm text-gray-500 italic">→ {takeaway.implication}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    {/* ========== MEDIA SHOWCASE ========== */}
                    {uni.media && (uni.media.infographics?.length > 0 || uni.media.videos?.length > 0) && (
                        <section id="media" className="scroll-mt-24">
                            <SectionHeader
                                icon={PhotoIcon}
                                title="Visual Guide"
                                subtitle="Infographics, videos, and visual insights"
                            />
                            <MediaShowcase media={uni.media} />
                        </section>
                    )}

                    {/* ========== ACADEMICS ========== */}
                    <section id="academics" className="scroll-mt-24">
                        <SectionHeader
                            icon={AcademicCapIcon}
                            title="Academics"
                            subtitle={`${academic.colleges?.length || 0} colleges & schools`}
                        />

                        <div className="space-y-4">
                            {academic.colleges?.map((college, idx) => (
                                <details key={idx} className="group bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                                    <summary className="flex items-center justify-between p-6 cursor-pointer hover:bg-gray-50 transition-colors">
                                        <div className="flex items-center gap-4">
                                            <div className="p-2 rounded-xl bg-blue-100">
                                                <BuildingLibraryIcon className="h-5 w-5 text-blue-600" />
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-gray-900">{college.name}</h3>
                                                <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${college.admissions_model === 'Direct Admit'
                                                        ? 'bg-green-100 text-green-700'
                                                        : 'bg-orange-100 text-orange-700'
                                                    }`}>
                                                    {college.admissions_model}
                                                </span>
                                            </div>
                                        </div>
                                        <ChevronDownIcon className="h-5 w-5 text-gray-400 transition-transform group-open:rotate-180" />
                                    </summary>
                                    <div className="px-6 pb-6 pt-2 border-t border-gray-100">
                                        {college.strategic_fit_advice && (
                                            <p className="text-gray-600 text-sm mb-4 italic">{college.strategic_fit_advice}</p>
                                        )}
                                        {college.majors && college.majors.length > 0 && (
                                            <div className="flex flex-wrap gap-2">
                                                {college.majors.slice(0, 10).map((major, i) => (
                                                    <span key={i} className="text-sm bg-blue-50 text-blue-700 px-3 py-1.5 rounded-full border border-blue-100 font-medium">
                                                        {major.name}
                                                    </span>
                                                ))}
                                                {college.majors.length > 10 && (
                                                    <span className="text-sm text-gray-400 px-3 py-1.5">+{college.majors.length - 10} more</span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </details>
                            ))}
                        </div>
                    </section>

                    {/* ========== ADMISSIONS ========== */}
                    <section id="admissions" className="scroll-mt-24">
                        <SectionHeader
                            icon={CheckCircleIcon}
                            title="Admissions"
                            subtitle="Requirements, deadlines, and class profile"
                        />

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Deadlines Card */}
                            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                                <div className="p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-100">
                                    <div className="flex items-center gap-3">
                                        <CalendarIcon className="h-5 w-5 text-blue-600" />
                                        <h3 className="font-bold text-gray-900">Application Deadlines</h3>
                                    </div>
                                </div>
                                <div className="p-6">
                                    {appProcess.application_deadlines?.map((deadline, i) => (
                                        <div key={i} className="flex justify-between items-center py-3 border-b border-gray-100 last:border-0">
                                            <div>
                                                <span className="font-semibold text-gray-900">{deadline.plan_type}</span>
                                                {deadline.is_binding && (
                                                    <span className="ml-2 text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-bold">BINDING</span>
                                                )}
                                            </div>
                                            <span className="text-gray-600 font-medium">{deadline.date}</span>
                                        </div>
                                    )) || <p className="text-gray-500 italic">No deadline information available</p>}
                                </div>
                            </div>

                            {/* Class Profile Card */}
                            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                                <div className="p-6 bg-gradient-to-r from-purple-50 to-pink-50 border-b border-gray-100">
                                    <h3 className="font-bold text-gray-900">Admitted Class Profile</h3>
                                </div>
                                <div className="p-6 grid grid-cols-3 gap-4 text-center">
                                    <div>
                                        <div className="text-sm text-gray-500 mb-1">SAT (50%)</div>
                                        <div className="text-xl font-bold text-indigo-600">
                                            {admissions.admitted_student_profile?.testing?.sat_composite_middle_50 || 'N/A'}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-sm text-gray-500 mb-1">ACT (50%)</div>
                                        <div className="text-xl font-bold text-indigo-600">
                                            {admissions.admitted_student_profile?.testing?.act_composite_middle_50 || 'N/A'}
                                        </div>
                                    </div>
                                    <div>
                                        <div className="text-sm text-gray-500 mb-1">Avg GPA</div>
                                        <div className="text-xl font-bold text-indigo-600">
                                            {admissions.admitted_student_profile?.gpa?.average_weighted || 'N/A'}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* ========== FINANCIALS ========== */}
                    <section id="financials" className="scroll-mt-24">
                        <SectionHeader
                            icon={CurrencyDollarIcon}
                            title="Cost & Financial Aid"
                            subtitle="Tuition, fees, and scholarship opportunities"
                        />

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {/* Cost Breakdown */}
                            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
                                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <CurrencyDollarIcon className="h-5 w-5 text-green-600" />
                                    Annual Cost Breakdown
                                </h3>
                                <div className="space-y-3">
                                    <div className="flex justify-between py-2 border-b border-gray-100">
                                        <span className="text-gray-600">Tuition (In-State)</span>
                                        <span className="font-bold text-gray-900">
                                            ${formatNumber(financials.cost_of_attendance_breakdown?.in_state?.tuition || uni.financials.inStateTuition)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between py-2 border-b border-gray-100">
                                        <span className="text-gray-600">Tuition (Out-of-State)</span>
                                        <span className="font-bold text-gray-900">
                                            ${formatNumber(financials.cost_of_attendance_breakdown?.out_of_state?.tuition || uni.financials.outStateTuition)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between py-3 bg-gradient-to-r from-green-50 to-emerald-50 -mx-6 px-6 mt-4 rounded-xl">
                                        <span className="font-bold text-gray-900">Total COA (Out)</span>
                                        <span className="font-bold text-green-700 text-xl">
                                            ${formatNumber(financials.cost_of_attendance_breakdown?.out_of_state?.total_coa || uni.financials.outStateCOA)}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Scholarships */}
                            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
                                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <StarIcon className="h-5 w-5 text-amber-500" />
                                    Top Scholarships
                                </h3>
                                <div className="space-y-3 max-h-64 overflow-y-auto">
                                    {financials.scholarships?.slice(0, 5).map((sch, i) => (
                                        <div key={i} className="p-4 bg-gradient-to-br from-amber-50 to-yellow-50 rounded-xl border border-amber-100">
                                            <h4 className="font-bold text-amber-900">{sch.name}</h4>
                                            <div className="flex justify-between text-sm text-amber-700 mt-1">
                                                <span>{sch.amount}</span>
                                                <span>{sch.type}</span>
                                            </div>
                                        </div>
                                    )) || <p className="text-gray-500 italic">No scholarship data available</p>}
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* ========== OUTCOMES ========== */}
                    <section id="outcomes" className="scroll-mt-24">
                        <SectionHeader
                            icon={ChartBarIcon}
                            title="Career Outcomes"
                            subtitle="Earnings, employment, and top employers"
                        />

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                            <StatCard
                                label="10-Year Median Earnings"
                                value={`$${formatNumber(outcomes.median_earnings_10yr)}`}
                                subtext="vs $50k national median"
                                icon={CurrencyDollarIcon}
                                color="green"
                            />
                            <StatCard
                                label="Employment Rate"
                                value={`${outcomes.employment_rate_2yr || 'N/A'}%`}
                                subtext="Within 2 years"
                                icon={BriefcaseIcon}
                                color="blue"
                            />
                            <StatCard
                                label="Grad School Rate"
                                value={`${outcomes.grad_school_rate || 'N/A'}%`}
                                subtext="Continue to graduate studies"
                                icon={AcademicCapIcon}
                                color="purple"
                            />
                        </div>

                        {/* Top Employers */}
                        {outcomes.top_employers && outcomes.top_employers.length > 0 && (
                            <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
                                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                                    <BriefcaseIcon className="h-5 w-5 text-gray-600" />
                                    Where Graduates Work
                                </h3>
                                <div className="flex flex-wrap gap-3">
                                    {outcomes.top_employers.map((employer, i) => (
                                        <span key={i} className="bg-gradient-to-br from-gray-100 to-gray-200 text-gray-800 px-4 py-2 rounded-xl font-medium border border-gray-200 hover:shadow-md transition-shadow">
                                            {employer}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </section>

                    {/* ========== CAMPUS LIFE ========== */}
                    <section id="campus" className="scroll-mt-24">
                        <SectionHeader
                            icon={GlobeAltIcon}
                            title="Campus Life"
                            subtitle="Culture, environment, and student experience"
                        />

                        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
                            <p className="text-gray-700 leading-relaxed text-lg mb-6">
                                {strategic.campus_dynamics?.social_environment || 'Campus life information not available.'}
                            </p>

                            {/* What It Takes */}
                            {studentInsights.what_it_takes && studentInsights.what_it_takes.length > 0 && (
                                <div className="mt-8">
                                    <h3 className="font-bold text-gray-900 mb-4">What It Takes to Get In</h3>
                                    <ul className="space-y-2">
                                        {studentInsights.what_it_takes.slice(0, 5).map((item, i) => (
                                            <li key={i} className="flex items-start gap-3">
                                                <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                                                <span className="text-gray-700">{item}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    </section>

                </div>
            </div>
        </div>
    );
};

export default UniversityDetailPage;
