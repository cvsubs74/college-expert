import React, { useState } from 'react';
import {
    UserCircleIcon,
    AcademicCapIcon,
    ChartBarIcon,
    TrophyIcon,
    BriefcaseIcon,
    SparklesIcon,
    BookOpenIcon,
    StarIcon,
    MapPinIcon,
    CalendarIcon,
    ClockIcon,
    CheckCircleIcon,
    UserGroupIcon
} from '@heroicons/react/24/outline';
import { StarIcon as StarIconSolid } from '@heroicons/react/24/solid';

// ============================================================================
// TAB NAVIGATION - Amber theme matching landing page
// ============================================================================
const TabButton = ({ id, label, icon: Icon, isActive, onClick }) => {
    return (
        <button
            onClick={() => onClick(id)}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all ${isActive
                ? 'bg-amber-600 text-white shadow-md'
                : 'text-gray-600 hover:bg-amber-50'
                }`}
        >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
        </button>
    );
};

// ============================================================================
// HIGHLIGHT BADGE - Amber theme
// ============================================================================
const HighlightBadge = ({ children }) => {
    return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
            {children}
        </span>
    );
};

// ============================================================================
// STAT CARD - Amber accent
// ============================================================================
const StatCard = ({ label, value, subtext, icon: Icon }) => {
    return (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-sm text-gray-500 font-medium">{label}</p>
                    <p className="text-3xl font-bold text-amber-600 mt-1">
                        {value || 'N/A'}
                    </p>
                    {subtext && <p className="text-xs text-gray-400 mt-1">{subtext}</p>}
                </div>
                {Icon && (
                    <div className="p-2.5 rounded-xl bg-amber-100">
                        <Icon className="h-5 w-5 text-amber-600" />
                    </div>
                )}
            </div>
        </div>
    );
};

// ============================================================================
// SECTION CARD - Amber/gray theme
// ============================================================================
const SectionCard = ({ title, icon: Icon, children, badge, className = '' }) => {
    return (
        <div className={`rounded-xl border border-gray-200 overflow-hidden ${className}`}>
            <div className="bg-amber-50 px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Icon className="h-5 w-5 text-amber-600" />
                    <h3 className="font-semibold text-gray-900">{title}</h3>
                </div>
                {badge && <HighlightBadge>{badge}</HighlightBadge>}
            </div>
            <div className="bg-gray-50 p-4">
                {children}
            </div>
        </div>
    );
};

// ============================================================================
// ACTIVITY CARD - With formatted descriptions (bullet points + truncation)
// ============================================================================
const ActivityCard = ({ activity }) => {
    const [expanded, setExpanded] = React.useState(false);
    const description = activity.description || '';

    // Parse description into bullet points or paragraphs
    const formatDescription = (text) => {
        if (!text) return [];
        // Split by newlines, bullet characters, or semicolons that look like list separators
        const lines = text.split(/[\n\r]+|(?:^|\s)[•\-\*]\s|;\s*(?=[A-Z])/).filter(line => line.trim());
        return lines.map(line => line.trim()).filter(Boolean);
    };

    const bulletPoints = formatDescription(description);
    const maxItems = 3;
    const isTruncated = bulletPoints.length > maxItems;
    const displayItems = expanded ? bulletPoints : bulletPoints.slice(0, maxItems);

    return (
        <div className="bg-white rounded-xl p-4 border border-gray-200 hover:border-amber-200 hover:shadow-md transition-all">
            <div className="flex items-start justify-between mb-2">
                <h4 className="font-semibold text-gray-900">{activity.name}</h4>
                {activity.role && (
                    <HighlightBadge>{activity.role}</HighlightBadge>
                )}
            </div>
            {bulletPoints.length > 0 && (
                <div className="mb-3">
                    <ul className="space-y-1.5 text-sm text-gray-600">
                        {displayItems.map((item, i) => (
                            <li key={i} className="flex items-start gap-2">
                                <span className="text-amber-500 mt-1.5">•</span>
                                <span>{item}</span>
                            </li>
                        ))}
                    </ul>
                    {isTruncated && (
                        <button
                            onClick={() => setExpanded(!expanded)}
                            className="text-xs text-amber-600 hover:text-amber-700 font-medium mt-2"
                        >
                            {expanded ? 'Show less' : `Show ${bulletPoints.length - maxItems} more...`}
                        </button>
                    )}
                </div>
            )}
            <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                {activity.grades && (
                    <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                        <CalendarIcon className="h-3.5 w-3.5" /> Grades {activity.grades}
                    </span>
                )}
                {activity.hours_per_week && (
                    <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded">
                        <ClockIcon className="h-3.5 w-3.5" /> {activity.hours_per_week} hrs/week
                    </span>
                )}
            </div>
            {activity.achievements && activity.achievements.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                    {activity.achievements.map((a, i) => (
                        <span key={i} className="inline-flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-700 rounded-lg text-xs border border-amber-100">
                            <TrophyIcon className="h-3 w-3" /> {a}
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

// ============================================================================
// COURSE PILL - Subject-based color coding
// ============================================================================
const CoursePill = ({ course }) => {
    // Detect subject category from course name
    const detectSubject = (name) => {
        const lowerName = name?.toLowerCase() || '';

        // English / Language Arts
        if (lowerName.includes('english') || lowerName.includes('literature') || lowerName.includes('writing') ||
            lowerName.includes('composition') || lowerName.includes('reading')) return 'English';

        // Math
        if (lowerName.includes('math') || lowerName.includes('algebra') || lowerName.includes('geometry') ||
            lowerName.includes('calculus') || lowerName.includes('statistics') || lowerName.includes('trigonometry') ||
            lowerName.includes('pre-calc') || lowerName.includes('precalc')) return 'Math';

        // Science
        if (lowerName.includes('biology') || lowerName.includes('chemistry') || lowerName.includes('physics') ||
            lowerName.includes('science') || lowerName.includes('chem') || lowerName.includes('bio') ||
            lowerName.includes('anatomy') || lowerName.includes('environmental')) return 'Science';

        // History / Social Studies
        if (lowerName.includes('history') || lowerName.includes('government') || lowerName.includes('economics') ||
            lowerName.includes('geography') || lowerName.includes('geo') || lowerName.includes('civics') ||
            lowerName.includes('social') || lowerName.includes('politics') || lowerName.includes('push')) return 'History';

        // Foreign Languages
        if (lowerName.includes('spanish') || lowerName.includes('french') || lowerName.includes('german') ||
            lowerName.includes('chinese') || lowerName.includes('japanese') || lowerName.includes('latin') ||
            lowerName.includes('italian') || lowerName.includes('language')) return 'Language';

        // Business / Economics
        if (lowerName.includes('business') || lowerName.includes('marketing') || lowerName.includes('accounting') ||
            lowerName.includes('finance') || lowerName.includes('entrepreneur') || lowerName.includes('econ')) return 'Business';

        // Arts / Music
        if (lowerName.includes('art') || lowerName.includes('music') || lowerName.includes('theater') ||
            lowerName.includes('drama') || lowerName.includes('dance') || lowerName.includes('band') ||
            lowerName.includes('choir') || lowerName.includes('orchestra')) return 'Arts';

        // Technology / Computer Science
        if (lowerName.includes('computer') || lowerName.includes('programming') || lowerName.includes('coding') ||
            lowerName.includes('python') || lowerName.includes('java') || lowerName.includes('tech') ||
            lowerName.includes('data') || lowerName.includes('web') || lowerName.includes('cyber')) return 'Tech';

        // Health / PE
        if (lowerName.includes('health') || lowerName.includes('physical') || lowerName.includes('pe ') ||
            lowerName.includes('fitness') || lowerName.includes('wellness')) return 'Health';

        // Leadership / Other
        if (lowerName.includes('leadership') || lowerName.includes('student council')) return 'Leadership';

        // Psychology
        if (lowerName.includes('psych')) return 'Psychology';

        return 'General';
    };

    // Detect course level (AP, Honors, etc.)
    const detectLevel = (name, explicitType) => {
        if (explicitType && explicitType !== 'Regular') return explicitType;
        const lowerName = name?.toLowerCase() || '';
        if (lowerName.match(/\bap\b/) || lowerName.includes('ap ')) return 'AP';
        if (lowerName.includes('honors') || lowerName.includes('honor')) return 'Honors';
        if (lowerName.includes('ib ') || lowerName.match(/\bib\b/)) return 'IB';
        return null;
    };

    const subject = detectSubject(course.name);
    const level = detectLevel(course.name, course.type);

    // Subject-based color palette (no gray!)
    const subjectColors = {
        'English': 'bg-blue-100 text-blue-800 border-blue-200',
        'Math': 'bg-purple-100 text-purple-800 border-purple-200',
        'Science': 'bg-emerald-100 text-emerald-800 border-emerald-200',
        'History': 'bg-amber-100 text-amber-800 border-amber-200',
        'Language': 'bg-rose-100 text-rose-800 border-rose-200',
        'Business': 'bg-cyan-100 text-cyan-800 border-cyan-200',
        'Arts': 'bg-pink-100 text-pink-800 border-pink-200',
        'Tech': 'bg-indigo-100 text-indigo-800 border-indigo-200',
        'Health': 'bg-lime-100 text-lime-800 border-lime-200',
        'Leadership': 'bg-orange-100 text-orange-800 border-orange-200',
        'Psychology': 'bg-violet-100 text-violet-800 border-violet-200',
        'General': 'bg-slate-100 text-slate-700 border-slate-200',
    };
    const color = subjectColors[subject] || subjectColors['General'];

    return (
        <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border ${color} text-sm`}>
            <span className="font-medium">{course.name}</span>
            {level && (
                <span className="text-xs font-semibold bg-white/60 px-1.5 py-0.5 rounded">{level}</span>
            )}
            {(course.semester1_grade || course.semester2_grade) && (
                <span className="text-xs font-bold bg-white/50 px-1.5 py-0.5 rounded">
                    {course.semester1_grade}/{course.semester2_grade}
                </span>
            )}
        </div>
    );
};

// ============================================================================
// EMPTY STATE
// ============================================================================
const EmptyState = ({ icon: Icon, title, subtitle }) => (
    <div className="text-center py-12 bg-white rounded-xl border border-gray-100">
        <Icon className="h-12 w-12 mx-auto text-gray-300 mb-3" />
        <p className="text-gray-500 font-medium">{title}</p>
        {subtitle && <p className="text-gray-400 text-sm mt-1">{subtitle}</p>}
    </div>
);

// ============================================================================
// OVERVIEW TAB - Uses FLAT profile fields from ES
// ============================================================================
const OverviewTab = ({ profileData }) => {
    // Flat profile fields - direct access (no nested structure)
    const name = profileData.name || 'Student';
    const school = profileData.school;
    const location = profileData.location;
    const grade = profileData.grade;
    const gpaWeighted = profileData.gpa_weighted;
    const gpaUnweighted = profileData.gpa_unweighted;
    const satTotal = profileData.sat_total;
    const satMath = profileData.sat_math;
    const satReading = profileData.sat_reading;
    const actComposite = profileData.act_composite;

    // Calculate quick stats
    const apCount = profileData.ap_exams?.length || 0;
    const activityCount = profileData.extracurriculars?.length || 0;
    const awardCount = profileData.awards?.length || 0;

    return (
        <div className="space-y-6">
            {/* Student Info Card - Subtle light design */}
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl p-6 border border-amber-100">
                <div className="flex items-center gap-5">
                    <div className="w-16 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-full flex items-center justify-center shadow-lg">
                        <UserCircleIcon className="h-9 w-9 text-white" />
                    </div>
                    <div className="flex-1">
                        <h2 className="text-2xl font-bold text-gray-900">{name}</h2>
                        <div className="flex flex-wrap items-center gap-4 mt-2 text-gray-600">
                            {school && (
                                <span className="flex items-center gap-1.5 text-sm">
                                    <AcademicCapIcon className="h-4 w-4 text-amber-600" /> {school}
                                </span>
                            )}
                            {location && (
                                <span className="flex items-center gap-1.5 text-sm">
                                    <MapPinIcon className="h-4 w-4 text-amber-600" /> {location}
                                </span>
                            )}
                            {grade && (
                                <span className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-sm font-medium">
                                    Grade {grade}
                                </span>
                            )}
                        </div>
                    </div>
                    {profileData.intended_major && (
                        <div className="text-right hidden md:block">
                            <p className="text-xs text-gray-500 uppercase tracking-wide">Intended Major</p>
                            <p className="text-lg font-semibold text-amber-700 mt-1">{profileData.intended_major}</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Key Stats - Using flat field names */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard label="Weighted GPA" value={gpaWeighted} icon={ChartBarIcon} />
                <StatCard label="Unweighted GPA" value={gpaUnweighted} icon={ChartBarIcon} />
                <StatCard
                    label="SAT Total"
                    value={satTotal}
                    subtext={satMath && satReading ? `M: ${satMath} | R: ${satReading}` : undefined}
                    icon={BookOpenIcon}
                />
                <StatCard label="ACT Composite" value={actComposite} icon={BookOpenIcon} />
            </div>

            {/* Quick Glance */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-xl p-5 border border-gray-200 flex items-center gap-4">
                    <div className="p-3 bg-amber-100 rounded-xl">
                        <AcademicCapIcon className="h-6 w-6 text-amber-600" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold text-gray-900">{apCount}</p>
                        <p className="text-sm text-gray-500">AP Exams</p>
                    </div>
                </div>
                <div className="bg-white rounded-xl p-5 border border-gray-200 flex items-center gap-4">
                    <div className="p-3 bg-amber-100 rounded-xl">
                        <SparklesIcon className="h-6 w-6 text-amber-600" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold text-gray-900">{activityCount}</p>
                        <p className="text-sm text-gray-500">Activities</p>
                    </div>
                </div>
                <div className="bg-white rounded-xl p-5 border border-gray-200 flex items-center gap-4">
                    <div className="p-3 bg-amber-100 rounded-xl">
                        <TrophyIcon className="h-6 w-6 text-amber-600" />
                    </div>
                    <div>
                        <p className="text-2xl font-bold text-gray-900">{awardCount}</p>
                        <p className="text-sm text-gray-500">Awards</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

// ============================================================================
// ACADEMICS TAB - Uses FLAT profile fields
// ============================================================================
const AcademicsTab = ({ profileData }) => {
    // Flat fields - ap_exams and courses are at top level
    const apExams = profileData.ap_exams || [];
    const courses = profileData.courses || [];

    // Group courses by grade level
    const coursesByGrade = {};
    courses.forEach(c => {
        const grade = c.grade_level || 'Other';
        if (!coursesByGrade[grade]) coursesByGrade[grade] = [];
        coursesByGrade[grade].push(c);
    });

    return (
        <div className="space-y-6">
            {/* AP Exams */}
            {apExams.length > 0 && (
                <SectionCard title="AP Exams" icon={AcademicCapIcon} color="purple" badge={`${apExams.length} exams`}>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {apExams.map((ap, i) => (
                            <div key={i} className="bg-white rounded-xl p-4 flex items-center justify-between border border-gray-100">
                                <span className="font-medium text-gray-700">{ap.subject}</span>
                                <div className="flex items-center gap-2">
                                    <span className={`text-2xl font-bold ${ap.score >= 4 ? 'text-green-600' :
                                        ap.score >= 3 ? 'text-amber-600' : 'text-red-500'
                                        }`}>
                                        {ap.score}
                                    </span>
                                    {ap.score >= 4 && <StarIconSolid className="h-5 w-5 text-amber-400" />}
                                </div>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}

            {/* Courses */}
            {Object.keys(coursesByGrade).length > 0 ? (
                <SectionCard title="Academic Courses" icon={BookOpenIcon} color="blue" badge={`${courses.length} courses`}>
                    <div className="space-y-5">
                        {Object.keys(coursesByGrade).sort((a, b) => {
                            // Sort numerically, putting 'Other' at the end
                            if (a === 'Other') return 1;
                            if (b === 'Other') return -1;
                            return parseInt(a) - parseInt(b);
                        }).map(grade => (
                            <div key={grade}>
                                <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
                                    <span className="w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs">
                                        {grade === 'Other' ? '?' : grade}
                                    </span>
                                    {grade === 'Other' ? 'Other Courses' : `${grade}th Grade`}
                                </h4>
                                <div className="flex flex-wrap gap-2">
                                    {coursesByGrade[grade].map((course, i) => (
                                        <CoursePill key={i} course={course} />
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            ) : (
                <EmptyState icon={BookOpenIcon} title="No courses added yet" subtitle="Add your academic courses to showcase your rigor" />
            )}
        </div>
    );
};

// ============================================================================
// ACTIVITIES TAB
// ============================================================================
const ActivitiesTab = ({ profileData }) => {
    const extracurriculars = profileData.extracurriculars || [];
    const leadership = profileData.leadership_roles || [];
    const specialPrograms = profileData.special_programs || [];

    return (
        <div className="space-y-6">
            {/* Extracurriculars */}
            {extracurriculars.length > 0 ? (
                <SectionCard
                    title="Extracurricular Activities"
                    icon={SparklesIcon}
                    color="rose"
                    badge={`${extracurriculars.length} activities`}
                >
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {extracurriculars.map((ec, i) => (
                            <ActivityCard key={i} activity={ec} />
                        ))}
                    </div>
                </SectionCard>
            ) : (
                <EmptyState icon={SparklesIcon} title="No activities added yet" subtitle="Add your extracurricular activities" />
            )}

            {/* Leadership */}
            {leadership.length > 0 && (
                <SectionCard title="Leadership Roles" icon={UserGroupIcon} color="green">
                    <div className="flex flex-wrap gap-2">
                        {leadership.map((role, i) => (
                            <span key={i} className="bg-white px-4 py-2 rounded-xl text-sm font-medium text-gray-700 border border-green-200 flex items-center gap-2">
                                <CheckCircleIcon className="h-4 w-4 text-green-500" />
                                {role}
                            </span>
                        ))}
                    </div>
                </SectionCard>
            )}

            {/* Special Programs */}
            {specialPrograms.length > 0 && (
                <SectionCard title="Special Programs" icon={StarIcon} color="indigo">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {specialPrograms.map((sp, i) => (
                            <div key={i} className="bg-white rounded-xl p-4 border border-gray-100">
                                <p className="font-semibold text-gray-900">{sp.name}</p>
                                {sp.description && <p className="text-sm text-gray-600 mt-1">{sp.description}</p>}
                                {sp.grade && <p className="text-xs text-indigo-600 mt-2">Grade {sp.grade}</p>}
                            </div>
                        ))}
                    </div>
                </SectionCard>
            )}
        </div>
    );
};

// ============================================================================
// ACHIEVEMENTS TAB
// ============================================================================
const AchievementsTab = ({ profileData }) => {
    const awards = profileData.awards || [];

    return (
        <div className="space-y-6">
            {awards.length > 0 ? (
                <SectionCard title="Awards & Honors" icon={TrophyIcon} color="amber" badge={`${awards.length} awards`}>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {awards.map((award, i) => (
                            <div key={i} className="bg-white rounded-xl p-4 flex items-start gap-4 border border-gray-100 hover:border-amber-200 transition-colors">
                                <div className="p-2.5 bg-amber-100 rounded-xl shrink-0">
                                    <TrophyIcon className="h-6 w-6 text-amber-600" />
                                </div>
                                <div>
                                    <p className="font-semibold text-gray-900">{award.name}</p>
                                    {award.grade && (
                                        <p className="text-sm text-amber-600 mt-1">Awarded in Grade {award.grade}</p>
                                    )}
                                    {award.description && (
                                        <p className="text-sm text-gray-500 mt-1">{award.description}</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </SectionCard>
            ) : (
                <EmptyState icon={TrophyIcon} title="No awards added yet" subtitle="Add your awards and honors to highlight your achievements" />
            )}
        </div>
    );
};

// ============================================================================
// EXPERIENCE TAB
// ============================================================================
const ExperienceTab = ({ profileData }) => {
    const workExperience = profileData.work_experience || [];

    return (
        <div className="space-y-6">
            {workExperience.length > 0 ? (
                <SectionCard title="Work Experience" icon={BriefcaseIcon} color="teal">
                    <div className="space-y-4">
                        {workExperience.map((work, i) => (
                            <div key={i} className="bg-white rounded-xl p-5 border border-gray-100">
                                <div className="flex items-start justify-between">
                                    <div>
                                        <p className="text-lg font-semibold text-gray-900">{work.employer}</p>
                                        <p className="text-teal-600 font-medium">{work.role}</p>
                                    </div>
                                    {work.hours_per_week && (
                                        <span className="text-sm text-teal-600 bg-teal-50 px-3 py-1 rounded-full border border-teal-200">
                                            {work.hours_per_week} hrs/week
                                        </span>
                                    )}
                                </div>
                                {work.grades && (
                                    <p className="text-sm text-gray-500 mt-2 flex items-center gap-1">
                                        <CalendarIcon className="h-4 w-4" /> Grades {work.grades}
                                    </p>
                                )}
                                {work.description && (
                                    <p className="text-gray-600 mt-3">{work.description}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </SectionCard>
            ) : (
                <EmptyState icon={BriefcaseIcon} title="No work experience added yet" subtitle="Add any jobs, internships, or volunteer positions" />
            )}
        </div>
    );
};

// ============================================================================
// MAIN PROFILE VIEW COMPONENT
// ============================================================================
const ProfileViewCard = ({ profileData }) => {
    const [activeTab, setActiveTab] = useState('overview');

    if (!profileData) {
        return (
            <div className="text-center py-16 bg-gradient-to-br from-gray-50 to-slate-100 rounded-2xl">
                <UserCircleIcon className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                <h3 className="text-xl font-semibold text-gray-500">No Profile Data</h3>
                <p className="text-gray-400 mt-2">Upload a profile document to get started</p>
            </div>
        );
    }

    const tabs = [
        { id: 'overview', label: 'Overview', icon: UserCircleIcon },
        { id: 'academics', label: 'Academics', icon: AcademicCapIcon },
        { id: 'activities', label: 'Activities', icon: SparklesIcon },
        { id: 'achievements', label: 'Achievements', icon: TrophyIcon },
        { id: 'experience', label: 'Experience', icon: BriefcaseIcon },
    ];

    return (
        <div className="space-y-6">
            {/* Tab Navigation */}
            <div className="bg-white rounded-2xl p-2 shadow-sm border border-gray-200">
                <div className="flex gap-1 overflow-x-auto">
                    {tabs.map(tab => (
                        <TabButton
                            key={tab.id}
                            id={tab.id}
                            label={tab.label}
                            icon={tab.icon}
                            isActive={activeTab === tab.id}
                            onClick={setActiveTab}
                        />
                    ))}
                </div>
            </div>

            {/* Tab Content */}
            <div className="min-h-[400px]">
                {activeTab === 'overview' && <OverviewTab profileData={profileData} />}
                {activeTab === 'academics' && <AcademicsTab profileData={profileData} />}
                {activeTab === 'activities' && <ActivitiesTab profileData={profileData} />}
                {activeTab === 'achievements' && <AchievementsTab profileData={profileData} />}
                {activeTab === 'experience' && <ExperienceTab profileData={profileData} />}
            </div>
        </div>
    );
};

export default ProfileViewCard;
