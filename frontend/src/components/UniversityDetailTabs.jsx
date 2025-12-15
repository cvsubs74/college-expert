import React from 'react';
import {
    MapPinIcon,
    CurrencyDollarIcon,
    AcademicCapIcon,
    UserGroupIcon,
    BriefcaseIcon,
    BuildingLibraryIcon,
    ChartBarIcon,
    CheckCircleIcon,
    CalendarIcon,
    StarIcon,
    GlobeAltIcon,
    SparklesIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const formatNumber = (num) => {
    if (num === 'N/A' || num === null || num === undefined) return 'N/A';
    return typeof num === 'number' ? num.toLocaleString() : num;
};

// --- Overview Tab ---
export const TabOverview = ({ uni, sentiment }) => {
    const profile = uni.fullProfile || {};
    const strategic = profile.strategic_profile || {};
    const metadata = profile.metadata || {};

    return (
        <div className="space-y-6">
            {/* Sentiment Banner */}
            {sentiment && sentiment.sentiment !== 'neutral' && (
                <div className={`p-4 rounded-lg border ${sentiment.sentiment === 'positive' ? 'bg-green-50 border-green-200 text-green-900' : 'bg-red-50 border-red-200 text-red-900'}`}>
                    <div className="flex items-center gap-2 mb-1">
                        <span className="text-xl">{sentiment.sentiment === 'positive' ? '📈' : '⚠️'}</span>
                        <h3 className="font-bold">Recent Intelligence</h3>
                    </div>
                    <p className="text-sm">{sentiment.headline}</p>
                </div>
            )}

            {/* Executive Summary */}
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <SparklesIcon className="h-5 w-5 text-blue-600" /> Executive Summary
                </h3>
                <p className="text-gray-700 leading-relaxed text-sm md:text-base">
                    {uni.summary}
                </p>
                {uni.market_position && (
                    <div className="mt-4 inline-block bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-xs font-bold border border-blue-100">
                        {uni.market_position}
                    </div>
                )}
            </div>

            {/* Key Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm text-center">
                    <div className="text-gray-500 text-xs mb-1">Acceptance</div>
                    <div className="text-2xl font-bold text-gray-900">{uni.admissions.acceptanceRate !== 'N/A' ? `${uni.admissions.acceptanceRate}%` : 'N/A'}</div>
                    <div className="w-full bg-gray-100 h-1.5 mt-2 rounded-full overflow-hidden">
                        <div className="bg-green-500 h-full" style={{ width: `${uni.admissions.acceptanceRate}%` }}></div>
                    </div>
                </div>
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm text-center">
                    <div className="text-gray-500 text-xs mb-1">US News Rank</div>
                    <div className="text-2xl font-bold text-blue-600">{uni.rankings.usNews !== 'N/A' ? `#${uni.rankings.usNews}` : 'N/A'}</div>
                </div>
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm text-center">
                    <div className="text-gray-500 text-xs mb-1">Total Cost (Out)</div>
                    <div className="text-2xl font-bold text-gray-900">${formatNumber(uni.financials.outStateCOA)}</div>
                </div>
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm text-center">
                    <div className="text-gray-500 text-xs mb-1">Median Earnings</div>
                    <div className="text-2xl font-bold text-green-600">${formatNumber(uni.outcomes.medianEarnings)}</div>
                </div>
            </div>

            {/* Strategic Takeaways */}
            {strategic.analyst_takeaways && (
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <LightBulbIcon className="h-5 w-5 text-yellow-500" /> Strategic Takeaways
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {strategic.analyst_takeaways.map((takeaway, idx) => (
                            <div key={idx} className="bg-gray-50 p-4 rounded-lg">
                                <span className="text-xs font-bold text-gray-500 uppercase block mb-1">{takeaway.category}</span>
                                <p className="text-sm text-gray-800 font-medium mb-1">{takeaway.insight}</p>
                                <p className="text-xs text-gray-600 italic">" {takeaway.implication} "</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// --- Academics Tab ---
export const TabAcademics = ({ uni }) => {
    const academic = uni.fullProfile?.academic_structure || {};
    const colleges = academic.colleges || [];

    return (
        <div className="space-y-6">
            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-4 rounded-xl border border-gray-200 flex items-center gap-3">
                    <BuildingLibraryIcon className="h-8 w-8 text-blue-500 bg-blue-50 p-1.5 rounded-full" />
                    <div>
                        <div className="text-sm text-gray-500">Structure</div>
                        <div className="font-bold text-gray-900">{academic.structure_type || 'Colleges'}</div>
                    </div>
                </div>
                {/* Add Faculty Ratio if in JSON, otherwise generic stats */}
            </div>

            {/* Colleges & Majors */}
            <div>
                <h3 className="text-lg font-bold text-gray-900 mb-4">Colleges & Schools</h3>
                <div className="grid grid-cols-1 gap-4">
                    {colleges.map((college, idx) => (
                        <div key={idx} className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow">
                            <div className="p-4 bg-gray-50 border-b border-gray-100 flex justify-between items-center">
                                <h4 className="font-bold text-gray-800">{college.name}</h4>
                                <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${college.admissions_model === 'Direct Admit' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                                    {college.admissions_model}
                                </span>
                            </div>
                            <div className="p-4">
                                <p className="text-sm text-gray-600 mb-3 italic">{college.strategic_fit_advice}</p>
                                {college.majors && college.majors.length > 0 && (
                                    <div>
                                        <div className="text-xs font-bold text-gray-400 uppercase mb-2">Notable Majors</div>
                                        <div className="flex flex-wrap gap-2">
                                            {college.majors.slice(0, 5).map((m, i) => (
                                                <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded border border-blue-100">
                                                    {m.name}
                                                </span>
                                            ))}
                                            {college.majors.length > 5 && (
                                                <span className="text-xs text-gray-400 px-2 py-1">+{college.majors.length - 5} more</span>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

// --- Admissions Tab ---
export const TabAdmissions = ({ uni }) => {
    const admissions = uni.fullProfile?.admissions_data || {};
    const process = uni.fullProfile?.application_process || {};

    return (
        <div className="space-y-6">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 flex items-center gap-4">
                <div className="bg-white p-3 rounded-full shadow-sm">
                    <ChartBarIcon className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                    <h3 className="font-bold text-blue-900 text-lg">Acceptance Rate: {admissions.current_status?.overall_acceptance_rate}%</h3>
                    <p className="text-sm text-blue-700">Competitiveness varies by major and residency.</p>
                </div>
            </div>

            {/* Timelines */}
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                    <h3 className="font-bold text-gray-900 flex items-center gap-2">
                        <CalendarIcon className="h-5 w-5 text-gray-500" /> Application Deadlines
                    </h3>
                </div>
                <table className="w-full text-sm text-left">
                    <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                        <tr>
                            <th className="px-6 py-3">Plan</th>
                            <th className="px-6 py-3">Date</th>
                            <th className="px-6 py-3">Binding?</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {process.application_deadlines?.map((d, i) => (
                            <tr key={i}>
                                <td className="px-6 py-3 font-medium text-gray-900">{d.plan_type}</td>
                                <td className="px-6 py-3 text-gray-600">{d.date}</td>
                                <td className="px-6 py-3">
                                    {d.is_binding ?
                                        <span className="text-red-600 font-bold text-xs bg-red-50 px-2 py-1 rounded">YES</span> :
                                        <span className="text-green-600 font-bold text-xs bg-green-50 px-2 py-1 rounded">NO</span>
                                    }
                                </td>
                            </tr>
                        )) || <tr><td colSpan="3" className="px-6 py-4 text-gray-500 italic">No deadlines available</td></tr>}
                    </tbody>
                </table>
            </div>

            {/* Requirements */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <CheckCircleIcon className="h-5 w-5 text-gray-500" /> Requirements Checklist
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {process.supplemental_requirements?.map((req, i) => (
                        <div key={i} className="flex gap-3 items-start p-3 bg-gray-50 rounded-lg">
                            <div className="mt-0.5"><CheckCircleIcon className="h-4 w-4 text-blue-500" /></div>
                            <div>
                                <span className="font-bold text-gray-800 text-sm block">{req.requirement_type}</span>
                                <p className="text-xs text-gray-600 mt-0.5">{req.details}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Class Profile */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4">Class Profile</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="text-center">
                        <div className="text-sm text-gray-500 mb-1">Middle 50% SAT</div>
                        <div className="text-xl font-bold text-indigo-600">{admissions.admitted_student_profile?.testing?.sat_composite_middle_50 || 'N/A'}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-sm text-gray-500 mb-1">Middle 50% ACT</div>
                        <div className="text-xl font-bold text-indigo-600">{admissions.admitted_student_profile?.testing?.act_composite_middle_50 || 'N/A'}</div>
                    </div>
                    <div className="text-center">
                        <div className="text-sm text-gray-500 mb-1">Avg GPA</div>
                        <div className="text-xl font-bold text-indigo-600">{admissions.admitted_student_profile?.gpa?.unweighted_middle_50 || admissions.admitted_student_profile?.gpa?.average_gpa_admitted || 'N/A'}</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

// --- Financials Tab ---
export const TabFinancials = ({ uni }) => {
    const fin = uni.fullProfile?.financials || {};
    const inState = fin.cost_of_attendance_breakdown?.in_state || {};
    const outState = fin.cost_of_attendance_breakdown?.out_of_state || {};

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Cost Card */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <CurrencyDollarIcon className="h-5 w-5 text-green-600" /> Estimated Annual Cost
                    </h3>
                    <div className="space-y-4">
                        <div className="flex justify-between items-center pb-2 border-b border-gray-100">
                            <span className="text-gray-600">Tuition (In-State)</span>
                            <span className="font-bold text-gray-900">${formatNumber(inState.tuition || fin.in_state_tuition)}</span>
                        </div>
                        <div className="flex justify-between items-center pb-2 border-b border-gray-100">
                            <span className="text-gray-600">Tuition (Out-of-State)</span>
                            <span className="font-bold text-gray-900">${formatNumber(outState.tuition || fin.out_of_state_tuition)}</span>
                        </div>
                        <div className="flex justify-between items-center pb-2 border-b border-gray-100">
                            <span className="text-gray-600">Room & Board</span>
                            <span className="font-bold text-gray-900">${formatNumber(inState.room_and_board || 'N/A')}</span>
                        </div>
                        <div className="flex justify-between items-center pt-2 bg-gray-50 p-2 rounded">
                            <span className="text-gray-900 font-bold">Total COA (Out)</span>
                            <span className="font-bold text-green-700 text-lg">${formatNumber(outState.total_coa || fin.estimated_coa)}</span>
                        </div>
                    </div>
                </div>

                {/* Scholarships Card */}
                <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
                    <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <SparklesIcon className="h-5 w-5 text-yellow-500" /> Scholarships & Aid
                    </h3>
                    {fin.scholarships && fin.scholarships.length > 0 ? (
                        <div className="space-y-3 max-h-60 overflow-y-auto">
                            {fin.scholarships.map((sch, i) => (
                                <div key={i} className="p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                                    <h4 className="font-bold text-yellow-900 text-sm mb-1">{sch.name}</h4>
                                    <div className="flex justify-between text-xs text-yellow-800">
                                        <span>{sch.amount}</span>
                                        <span>Deadline: {sch.deadline || 'Varies'}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-gray-500 italic text-sm">No specific scholarship data available.</p>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- Campus Tab ---
export const TabCampus = ({ uni }) => {
    const campus = uni.fullProfile?.strategic_profile?.campus_dynamics || {};
    const insights = uni.fullProfile?.student_insights || {};

    return (
        <div className="space-y-6">
            {/* Campus Vibe */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <GlobeAltIcon className="h-5 w-5 text-blue-500" /> Campus Vibe & Culture
                </h3>
                <p className="text-gray-700 leading-relaxed mb-4">
                    {campus.social_environment || 'Information not available.'}
                </p>
                <div className="flex flex-wrap gap-2">
                    {insights.campus_culture_tags?.map((tag, i) => (
                        <span key={i} className="bg-purple-50 text-purple-700 px-3 py-1 rounded-full text-sm font-medium border border-purple-100">
                            #{tag.replace(/\s+/g, '')}
                        </span>
                    ))}
                </div>
            </div>

            {/* Housing & Location */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <h4 className="font-bold text-gray-900 mb-2">Housing</h4>
                    <p className="text-sm text-gray-600 leading-relaxed">
                        {uni.fullProfile?.about?.housing || 'Housing details not available.'}
                    </p>
                </div>
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                    <h4 className="font-bold text-gray-900 mb-2">Location Context</h4>
                    <p className="text-sm text-gray-600 leading-relaxed">
                        {uni.location.city}, {uni.location.state} is a {uni.location.type} setting.
                        {campus.transportation_impact && <> {campus.transportation_impact}</>}
                    </p>
                </div>
            </div>
        </div>
    );
};

// --- Outcomes Tab ---
export const TabOutcomes = ({ uni }) => {
    const outcomes = uni.fullProfile?.outcomes || {};

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm text-center">
                <h3 className="font-bold text-gray-900 mb-2">Median 10-Year Earnings</h3>
                <div className="text-4xl font-bold text-green-600">${formatNumber(outcomes.median_earnings_10yr)}</div>
                <p className="text-sm text-gray-500 mt-2">vs National Average (~$50,000)</p>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <BriefcaseIcon className="h-5 w-5 text-gray-600" /> Top Employers
                </h3>
                {outcomes.top_employers && outcomes.top_employers.length > 0 ? (
                    <div className="flex flex-wrap gap-3">
                        {outcomes.top_employers.map((emp, i) => (
                            <span key={i} className="bg-gray-100 text-gray-800 px-4 py-2 rounded-lg font-medium border border-gray-200">
                                {emp}
                            </span>
                        ))}
                    </div>
                ) : (
                    <p className="text-gray-500 italic">No specific employer data available.</p>
                )}
            </div>
        </div>
    );
};
