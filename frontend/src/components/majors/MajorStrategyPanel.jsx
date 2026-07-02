import React, { useState, useEffect, useMemo } from 'react';
import {
    AcademicCapIcon,
    MagnifyingGlassIcon,
    ExclamationTriangleIcon,
    ArrowPathIcon,
    CheckBadgeIcon
} from '@heroicons/react/24/outline';
import { getUniversityMajors } from '../../services/api';

// ============================================================================
// MAJOR STRATEGY PANEL — facts-only view of the KB's trust-labeled major data
// (GET ?id=X&action=majors). Trust rules, in order of importance:
//   1. Every claim carries a basis (kb_verified / kb_reported / opinion).
//   2. Held-nulls render as explicit "not published" sentences — never blank,
//      never estimated.
//   3. is_impacted:false is NEVER rendered as "not impacted"/"safe" — only an
//      "Officially impacted" chip when value === true. (Verified UIUC CS is
//      is_impacted:false at a ~7% admit rate; that's the trap.)
//   4. entry_path 'unclear' gets NO badge — the school's verbatim wording is
//      shown in quotes instead. A guessed door-policy badge is the worst
//      trust failure.
// ============================================================================

const ENTRY_PATH_BADGES = {
    direct_admit: { label: 'Direct admit', className: 'bg-green-100 text-green-800 border border-green-200' },
    pre_major: { label: 'Pre-major', className: 'bg-blue-100 text-blue-800 border border-blue-200' },
    secondary_application: { label: 'Secondary application', className: 'bg-orange-100 text-orange-800 border border-orange-200' },
    open_declaration: { label: 'Open declaration', className: 'bg-teal-100 text-teal-800 border border-teal-200' }
};

const BASIS_LABELS = {
    kb_verified: 'official',
    kb_reported: 'reported'
};

// Small purple chip marking counselor-opinion content (basis: 'opinion').
const CounselorTakeChip = () => (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-purple-100 text-purple-700 border border-purple-200 whitespace-nowrap">
        Counselor take
    </span>
);

// Hedged rendering for a legacy reported percentage (strip any stray '%').
const formatReportedRate = (rate) => `Reported ~${String(rate).replace(/%\s*$/, '')}% (unverified)`;

// One major row: name, entry-path badge (or verbatim quote for 'unclear'),
// risk callouts, door-policy line, hedged reported stats.
const MajorRow = ({ major }) => {
    const entryPath = major.entry_path || {};
    const badge = ENTRY_PATH_BADGES[entryPath.value];
    const basisLabel = BASIS_LABELS[entryPath.basis];
    const doorPolicy = major.door_policy || {};
    const reported = major.reported_stats;

    // door_policy details line (only claims the KB actually holds)
    const doorParts = [];
    if (doorPolicy.direct_admit_only === true) doorParts.push('Direct admit only');
    if (doorPolicy.internal_transfer_allowed === true) {
        doorParts.push(`Internal transfer allowed${doorPolicy.internal_transfer_gpa ? ` (GPA ≥ ${doorPolicy.internal_transfer_gpa})` : ''}`);
    } else if (doorPolicy.internal_transfer_allowed === false) {
        doorParts.push('Internal transfer not allowed');
    } else if (doorPolicy.internal_transfer_gpa) {
        doorParts.push(`Internal transfer GPA bar: ${doorPolicy.internal_transfer_gpa}`);
    }

    return (
        <li className="py-3 border-b border-[#E0DED8] last:border-b-0" data-testid="major-row">
            <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-[#2C2C2C]">{major.name}</span>
                    {major.degree_type && (
                        <span className="text-xs text-[#6B6B6B]">{major.degree_type}</span>
                    )}
                    {/* Only an explicit official designation gets the impacted chip.
                        value === false / null renders NOTHING — absence of the
                        designation is not evidence the door is easy. */}
                    {major.is_impacted?.value === true && (
                        <span className="stratia-chip bg-red-100 text-red-700 border border-red-200">
                            Officially impacted
                        </span>
                    )}
                    {major.entry_risk === 'elevated' && (
                        <span className="text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                            Elevated entry risk
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-1.5">
                    {badge ? (
                        <>
                            <span className={`stratia-chip ${badge.className}`}>{badge.label}</span>
                            {basisLabel && (
                                <span className="text-[10px] text-[#6B6B6B]">({basisLabel})</span>
                            )}
                        </>
                    ) : entryPath.raw ? (
                        // 'unclear' — no badge; the school's verbatim wording instead.
                        <span className="text-xs text-[#6B6B6B] italic max-w-[280px] text-right">
                            "{entryPath.raw}"
                        </span>
                    ) : (
                        <span className="text-xs text-[#6B6B6B]">Entry path not published.</span>
                    )}
                </div>
            </div>

            {/* Capped door — the honest competitiveness signal. */}
            {major.entry_risk === 'capped_door' && (
                <div className="mt-2 bg-amber-50 border border-amber-300 rounded-lg p-3" role="note">
                    <p className="text-sm text-amber-900 font-medium flex items-start gap-2">
                        <ExclamationTriangleIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                        If you're not admitted to this major directly, you can't switch in later.
                    </p>
                    {entryPath.raw && (
                        <details className="mt-2 ml-6">
                            <summary className="text-xs text-amber-800 cursor-pointer select-none">
                                School's own wording
                            </summary>
                            <p className="text-xs text-amber-800 italic mt-1">"{entryPath.raw}"</p>
                        </details>
                    )}
                </div>
            )}

            {/* door_policy details when the KB holds them */}
            {doorParts.length > 0 && (
                <p className="mt-1.5 text-xs text-[#6B6B6B]">{doorParts.join(' · ')}</p>
            )}

            {/* Reported (legacy, unprovenanced) stats — always hedged, never a
                factor input. Absent admit rate gets an explicit sentence. */}
            <p className="mt-1.5 text-xs text-[#9A9A9A]">
                {reported?.acceptance_rate != null
                    ? formatReportedRate(reported.acceptance_rate)
                    : 'No per-major admit rate published.'}
                {reported?.average_gpa_admitted != null && (
                    <span> · Reported avg admitted GPA {reported.average_gpa_admitted} (unverified)</span>
                )}
                {reported?.minimum_gpa_to_declare != null && (
                    <span> · Reported minimum GPA to declare {reported.minimum_gpa_to_declare} (unverified)</span>
                )}
            </p>
        </li>
    );
};

const MajorStrategyPanel = ({ universityId, universityName }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [query, setQuery] = useState('');

    const fetchMajors = async () => {
        setLoading(true);
        setError(null);
        const result = await getUniversityMajors(universityId);
        if (result?.success) {
            setData(result);
        } else {
            setError(result?.error || 'Failed to load major facts');
        }
        setLoading(false);
    };

    useEffect(() => {
        if (universityId) fetchMajors();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [universityId]);

    // Client-side filter over loaded data: majors by name; a college also
    // survives if its own name matches.
    const filteredColleges = useMemo(() => {
        const colleges = data?.colleges || [];
        const q = query.trim().toLowerCase();
        if (!q) return colleges;
        return colleges
            .map(college => {
                const collegeMatches = (college.name || '').toLowerCase().includes(q);
                const majors = (college.majors || []).filter(m =>
                    (m.name || '').toLowerCase().includes(q));
                if (collegeMatches && majors.length === 0) {
                    return { ...college, majors: college.majors || [] };
                }
                return { ...college, majors };
            })
            .filter(college => (college.majors || []).length > 0
                || (college.name || '').toLowerCase().includes(q));
    }, [data, query]);

    // Loading skeleton
    if (loading) {
        return (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100" data-testid="majors-loading">
                <div className="animate-pulse space-y-4">
                    <div className="h-5 bg-gray-200 rounded w-1/3" />
                    <div className="h-4 bg-gray-100 rounded w-1/2" />
                    <div className="h-24 bg-gray-100 rounded" />
                    <div className="h-24 bg-gray-100 rounded" />
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 text-center">
                <ExclamationTriangleIcon className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                <p className="text-gray-700 mb-1">Couldn't load major facts.</p>
                <p className="text-sm text-gray-500 mb-4">{error}</p>
                <button
                    onClick={fetchMajors}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-[#1A4D2E] text-white rounded-lg text-sm font-medium hover:bg-[#143D24] transition-colors"
                >
                    <ArrowPathIcon className="h-4 w-4" />
                    Try again
                </button>
            </div>
        );
    }

    const verified = data?.verification_status === 'verified';
    const tactics = data?.strategy_notes?.major_selection_tactics?.items || [];
    const alternateStrategy = data?.strategy_notes?.alternate_major_strategy?.text;
    const dataNotes = data?.data_notes || [];

    return (
        <div className="space-y-6">
            {/* Header: what this data is and how much to trust it */}
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                    <div>
                        <h2 className="font-bold text-gray-900 flex items-center gap-2">
                            <AcademicCapIcon className="h-5 w-5 text-[#1A4D2E]" />
                            Majors at {data?.official_name || universityName}
                        </h2>
                        {data?.data_year && (
                            <p className="text-xs text-gray-500 mt-1">{data.data_year} admissions cycle data</p>
                        )}
                    </div>
                    <div className="text-right">
                        {verified ? (
                            <span className="stratia-chip bg-green-100 text-green-800 border border-green-200 inline-flex items-center gap-1">
                                <CheckBadgeIcon className="h-3.5 w-3.5" />
                                From official publications
                            </span>
                        ) : (
                            <>
                                <span className="stratia-chip bg-white text-gray-600 border border-gray-300">
                                    Reported — not yet verified
                                </span>
                                <p className="text-[11px] text-gray-500 mt-1 max-w-[260px]">
                                    Gathered from earlier research, not yet checked against the school's official publications.
                                </p>
                            </>
                        )}
                    </div>
                </div>

                {/* Client-side major filter */}
                <div className="relative mt-4">
                    <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6B6B6B]" />
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Filter majors..."
                        aria-label="Filter majors"
                        className="pl-9 pr-4 py-2 w-full sm:w-72 rounded-full border border-[#E0DED8] bg-white text-sm
                            focus:outline-none focus:border-[#1A4D2E] focus:ring-2 focus:ring-[#D6E8D5] transition-all"
                    />
                </div>
            </div>

            {/* Colleges */}
            {filteredColleges.length === 0 ? (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 text-center text-sm text-gray-500">
                    {query
                        ? `No majors match "${query}".`
                        : 'No majors are stored for this school yet.'}
                </div>
            ) : (
                filteredColleges.map((college, idx) => (
                    <div key={idx} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100" data-testid="college-section">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                            <h3 className="font-semibold text-gray-900">{college.name}</h3>
                            {college.admissions_model && (
                                <span className="stratia-chip bg-[#F8F6F0] text-[#4A4A4A] border border-[#E0DED8]">
                                    {college.admissions_model}
                                </span>
                            )}
                            {college.is_restricted_or_capped === true && (
                                <span className="stratia-chip bg-amber-100 text-amber-800 border border-amber-300">
                                    Capped
                                </span>
                            )}
                        </div>

                        {/* College-level reported acceptance estimate — hedged */}
                        {college.acceptance_rate_estimate?.value != null && (
                            <p className="text-xs text-[#9A9A9A] mb-1">
                                Reported acceptance estimate: {String(college.acceptance_rate_estimate.value)} (unverified)
                            </p>
                        )}

                        {/* Counselor opinion, clearly labeled as such */}
                        {college.strategic_fit_advice?.text && (
                            <div className="flex items-start gap-2 mt-2 bg-purple-50 border border-purple-100 rounded-lg p-3">
                                <CounselorTakeChip />
                                <p className="text-sm text-gray-700">{college.strategic_fit_advice.text}</p>
                            </div>
                        )}

                        <ul className="mt-3">
                            {(college.majors || []).map((major, mIdx) => (
                                <MajorRow key={mIdx} major={major} />
                            ))}
                        </ul>
                    </div>
                ))
            )}

            {/* Footer: counselor tactics (opinion) + data notes (provenance) */}
            {(tactics.length > 0 || alternateStrategy) && (
                <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                    <div className="flex items-center gap-2 mb-3">
                        <h3 className="font-semibold text-gray-900">Major selection tactics</h3>
                        <CounselorTakeChip />
                    </div>
                    <ul className="space-y-2">
                        {tactics.map((tactic, idx) => (
                            <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                                <span className="text-purple-400 mt-0.5">•</span>
                                {tactic}
                            </li>
                        ))}
                    </ul>
                    {alternateStrategy && (
                        <p className="text-sm text-gray-700 mt-3 pt-3 border-t border-gray-100">
                            <span className="font-medium">Alternate-major strategy:</span> {alternateStrategy}
                        </p>
                    )}
                </div>
            )}

            {dataNotes.length > 0 && (
                <ul className="text-xs text-[#9A9A9A] space-y-1 px-2" data-testid="data-notes">
                    {dataNotes.map((note, idx) => (
                        <li key={idx}>{note}</li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default MajorStrategyPanel;
