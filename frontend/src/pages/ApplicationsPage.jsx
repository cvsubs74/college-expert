import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import { useAuth } from '../context/AuthContext';
import { getCollegeList, getEssayTracker, getScholarshipTracker } from '../services/api';
import NotesAffordance from '../components/roadmap/NotesAffordance';
import '../styles/ApplicationsPage.css';

// API URLs
// Aggregated deadlines come from counselor_agent (the read-side aggregator
// that owns this logic). profile_manager_v2 does not expose /get-deadlines.
const COUNSELOR_AGENT_URL = import.meta.env.VITE_COUNSELOR_AGENT_URL || 'https://us-east1-college-counselling-478115.cloudfunctions.net/counselor-agent';
const KB_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL || 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

export default function ApplicationsPage({ embedded = false }) {
    const navigate = useNavigate();
    const { currentUser } = useAuth();
    const [schools, setSchools] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [essayHelpModal, setEssayHelpModal] = useState({ open: false, school: null });

    // Per-school expansion state for the mini-dashboard. Keyed by
    // university_id; missing or false = collapsed. Default-collapsed so the
    // page stays scannable for users with many schools.
    const [expandedSchools, setExpandedSchools] = useState({});

    const toggleSchoolExpanded = (universityId) => {
        setExpandedSchools((prev) => ({ ...prev, [universityId]: !prev[universityId] }));
    };

    // Fetch user's schools with deadlines
    const fetchSchools = useCallback(async () => {
        if (!currentUser?.email) return;

        try {
            setLoading(true);

            // Fetch four user-data sources in parallel:
            //   - deadlines  (counselor_agent — per-school deadline list)
            //   - college_list (notes field per school for NotesAffordance)
            //   - essay_tracker / scholarship_tracker (mini-dashboard rows)
            // Tracker fetches are best-effort: failures yield empty arrays
            // rather than blocking the whole page.
            const [deadlinesResp, listResp, essayResp, scholarshipResp] = await Promise.all([
                fetch(`${COUNSELOR_AGENT_URL}/deadlines`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_email: currentUser.email })
                }).then(r => r.json()),
                getCollegeList(currentUser.email).catch(() => ({ college_list: [] })),
                getEssayTracker(currentUser.email).catch(() => ({ essays: [] })),
                getScholarshipTracker(currentUser.email).catch(() => ({ scholarships: [] })),
            ]);

            if (deadlinesResp.success) {
                // Build a lookup of notes per university_id from the college_list.
                const notesByUniversity = {};
                const collegeListArr = Array.isArray(listResp?.college_list)
                    ? listResp.college_list
                    : [];
                collegeListArr.forEach((c) => {
                    if (c?.university_id) {
                        notesByUniversity[c.university_id] = c.notes || '';
                    }
                });

                // Bucket essays / scholarships by university for the
                // mini-dashboard. Items without a university_id are skipped
                // (e.g., shared Common App essays without a school binding —
                // those live on the Essays tab, not a per-school card).
                const essaysByUniversity = {};
                const essaysArr = Array.isArray(essayResp?.essays) ? essayResp.essays : [];
                essaysArr.forEach((e) => {
                    if (!e?.university_id) return;
                    (essaysByUniversity[e.university_id] ||= []).push(e);
                });

                const scholarshipsByUniversity = {};
                const scholarshipsArr = Array.isArray(scholarshipResp?.scholarships)
                    ? scholarshipResp.scholarships
                    : [];
                scholarshipsArr.forEach((s) => {
                    if (!s?.university_id) return;
                    (scholarshipsByUniversity[s.university_id] ||= []).push(s);
                });

                // Group deadlines by university and seed each school's notes.
                const schoolMap = {};
                deadlinesResp.deadlines.forEach(d => {
                    if (!schoolMap[d.university_id]) {
                        schoolMap[d.university_id] = {
                            university_id: d.university_id,
                            university_name: d.university_name,
                            deadlines: [],
                            essay_tips: [],
                            notes: notesByUniversity[d.university_id] || '',
                            essays: essaysByUniversity[d.university_id] || [],
                            scholarships: scholarshipsByUniversity[d.university_id] || [],
                        };
                    }
                    schoolMap[d.university_id].deadlines.push(d);
                });

                // Fetch essay tips from knowledge base for each school
                const schoolsWithEssays = await Promise.all(
                    Object.values(schoolMap).map(async (school) => {
                        try {
                            const kbResponse = await fetch(`${KB_URL}?university_id=${school.university_id}`);
                            const kbData = await kbResponse.json();
                            if (kbData.success && kbData.university?.profile) {
                                const profile = kbData.university.profile;
                                school.essay_tips = profile.student_insights?.essay_tips || [];
                                school.supplemental_requirements = profile.application_process?.supplemental_requirements || [];
                            }
                        } catch (e) {
                            console.error('Failed to fetch KB data for', school.university_id);
                        }
                        return school;
                    })
                );

                setSchools(schoolsWithEssays);
            } else {
                setError(deadlinesResp.error);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [currentUser?.email]);

    useEffect(() => {
        fetchSchools();
    }, [fetchSchools]);

    const getNextDeadline = (deadlines) => {
        if (!deadlines?.length) return null;
        const sorted = deadlines.sort((a, b) => new Date(a.date) - new Date(b.date));
        return sorted[0];
    };

    const getDaysUntil = (dateStr) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = Math.ceil((date - now) / (1000 * 60 * 60 * 24));
        return diff;
    };

    const getUrgencyClass = (days) => {
        if (days <= 7) return 'urgent';
        if (days <= 30) return 'soon';
        return 'later';
    };

    if (loading) {
        return (
            <div className={embedded ? '' : 'essay-page'}>
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading your schools...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className={embedded ? '' : 'essay-page'}>
                <div className="error-state">
                    <p>Error: {error}</p>
                    <button onClick={fetchSchools}>Retry</button>
                </div>
            </div>
        );
    }

    return (
        <div className={embedded ? '' : 'essay-page'}>
            {/* Header — hidden when embedded inside the consolidated Roadmap tab */}
            {!embedded && (
                <header className="essay-header">
                    <h1>Essay Assistant</h1>
                    <p className="subtitle">Deadlines and essay guidance for your saved schools</p>
                </header>
            )}

            {/* School Cards */}
            <div className="school-cards">
                {schools.length === 0 ? (
                    <div className="empty-state">
                        <p>No schools in your list yet. Add schools from the Discover page!</p>
                    </div>
                ) : (
                    schools.map(school => {
                        const nextDeadline = getNextDeadline(school.deadlines);
                        const daysUntil = nextDeadline ? getDaysUntil(nextDeadline.date) : null;

                        return (
                            <div key={school.university_id} className="essay-card">
                                {/* Card Header with Deadline */}
                                <div className="essay-card-header">
                                    <div className="school-info">
                                        <div className="flex items-start justify-between gap-2">
                                            <h3>{school.university_name}</h3>
                                            <NotesAffordance
                                                userEmail={currentUser?.email}
                                                collection="college_list"
                                                itemId={school.university_id}
                                                initialValue={school.notes}
                                                emptyLabel="Add notes about this school"
                                            />
                                        </div>
                                        {nextDeadline && (
                                            <div className={`deadline-badge ${getUrgencyClass(daysUntil)}`}>
                                                <span className="deadline-plan">{nextDeadline.deadline_type}</span>
                                                <span className="deadline-date">
                                                    {new Date(nextDeadline.date).toLocaleDateString('en-US', {
                                                        month: 'short',
                                                        day: 'numeric',
                                                        year: 'numeric'
                                                    })}
                                                </span>
                                                <span className="deadline-days">
                                                    {daysUntil > 0 ? `${daysUntil} days` : daysUntil === 0 ? 'Today!' : 'Passed'}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Essay Section */}
                                <div className="essay-card-body">
                                    {/* Supplemental Requirements */}
                                    {school.supplemental_requirements?.length > 0 && (
                                        <div className="essay-requirements">
                                            <h4>📝 Essay Requirements</h4>
                                            {school.supplemental_requirements.map((req, i) => (
                                                <div key={i} className="requirement-item">
                                                    <span className="req-type">{req.requirement_type}</span>
                                                    <p>{req.details}</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    {/* Essay Tips */}
                                    {school.essay_tips?.length > 0 && (
                                        <div className="essay-tips">
                                            <h4>💡 Essay Tips</h4>
                                            <ul>
                                                {school.essay_tips.slice(0, 3).map((tip, i) => (
                                                    <li key={i}>{tip}</li>
                                                ))}
                                            </ul>
                                            {school.essay_tips.length > 3 && (
                                                <span className="more-tips">+{school.essay_tips.length - 3} more tips</span>
                                            )}
                                        </div>
                                    )}

                                    {/* Mini-dashboard toggle */}
                                    <MiniDashboard
                                        school={school}
                                        isExpanded={!!expandedSchools[school.university_id]}
                                        onToggle={() => toggleSchoolExpanded(school.university_id)}
                                        onNavigate={(deepLink) => navigate(deepLink)}
                                    />

                                    {/* Action Button */}
                                    <button
                                        className="ai-help-btn"
                                        onClick={() => setEssayHelpModal({ open: true, school })}
                                    >
                                        ✨ Get AI Essay Help
                                    </button>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Essay Help Modal */}
            {essayHelpModal.open && (
                <EssayHelpModal
                    school={essayHelpModal.school}
                    onClose={() => setEssayHelpModal({ open: false, school: null })}
                />
            )}
        </div>
    );
}

// MiniDashboard — collapsible per-school summary rendered inside the
// Colleges-tab cards. Aggregates the user's existing data (deadlines,
// essays, scholarships) into one drill-in view so the user doesn't have
// to bounce between tabs to see per-school progress.
//
// All data is sourced from the parent's already-fetched school object;
// this component is purely presentational + click-routing.
function MiniDashboard({ school, isExpanded, onToggle, onNavigate }) {
    const deadlines = Array.isArray(school.deadlines) ? school.deadlines : [];
    const essays = Array.isArray(school.essays) ? school.essays : [];
    const scholarships = Array.isArray(school.scholarships) ? school.scholarships : [];

    // Progress: % essays at status=final, % scholarships at status=applied|received.
    // We deliberately count "final" essays as done (rather than e.g. "review")
    // since final is the explicit terminal state in the essay status enum.
    // Scholarships count "applied" OR "received" as forward progress —
    // applied is the user-actionable terminal state, received is the bonus.
    const essaysDone = essays.filter((e) => (e.status || '').toLowerCase() === 'final').length;
    const scholarshipsApplied = scholarships.filter((s) => {
        const st = (s.status || '').toLowerCase();
        return st === 'applied' || st === 'received';
    }).length;
    const essayPct = essays.length ? Math.round((essaysDone / essays.length) * 100) : 0;
    const scholarshipPct = scholarships.length
        ? Math.round((scholarshipsApplied / scholarships.length) * 100)
        : 0;

    // Empty card-level state: nothing to expand into. Hide the toggle entirely
    // rather than offering a click that opens an empty drawer.
    if (deadlines.length === 0 && essays.length === 0 && scholarships.length === 0) {
        return null;
    }

    return (
        <div className="mt-4 border-t border-stone-200 pt-3">
            <button
                type="button"
                onClick={onToggle}
                aria-expanded={isExpanded}
                className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide
                    text-[#1A4D2E] hover:text-[#2D6B45] transition-colors"
            >
                {isExpanded ? (
                    <ChevronUpIcon className="w-4 h-4" />
                ) : (
                    <ChevronDownIcon className="w-4 h-4" />
                )}
                {isExpanded ? 'Hide progress' : 'Show progress'}
            </button>

            {isExpanded && (
                <div className="mt-3 space-y-4 text-sm">
                    {/* All deadlines (the card header shows just the next one) */}
                    {deadlines.length > 0 && (
                        <section>
                            <h4 className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B] mb-2">
                                Deadlines ({deadlines.length})
                            </h4>
                            <ul className="space-y-1">
                                {[...deadlines]
                                    .sort((a, b) => new Date(a.date) - new Date(b.date))
                                    .map((d, i) => (
                                        <li key={`${d.deadline_type}-${d.date}-${i}`} className="flex items-baseline justify-between gap-2">
                                            <span className="text-[#4A4A4A]">{d.deadline_type || 'Deadline'}</span>
                                            <span className="text-[#6B6B6B] text-xs whitespace-nowrap">{d.date}</span>
                                        </li>
                                    ))}
                            </ul>
                        </section>
                    )}

                    {/* Essays for this school. Each row jumps to the Essays tab. */}
                    {essays.length > 0 && (
                        <section>
                            <div className="flex items-baseline justify-between mb-2">
                                <h4 className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">
                                    Essays ({essaysDone}/{essays.length})
                                </h4>
                                <ProgressBar pct={essayPct} />
                            </div>
                            <ul className="space-y-1">
                                {essays.map((e) => (
                                    <li key={e.essay_id}>
                                        <button
                                            type="button"
                                            onClick={() => onNavigate(`/roadmap?tab=essays&essay_id=${e.essay_id}`)}
                                            className="w-full text-left flex items-baseline justify-between gap-2
                                                px-2 py-1 -mx-2 rounded hover:bg-[#F8F6F0] transition-colors"
                                        >
                                            <span className="text-[#4A4A4A] truncate">
                                                {e.prompt_text || e.prompt || 'Essay'}
                                            </span>
                                            <StatusPill value={e.status || 'not_started'} kind="essay" />
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    )}

                    {/* Scholarships for this school. Same click-to-jump pattern. */}
                    {scholarships.length > 0 && (
                        <section>
                            <div className="flex items-baseline justify-between mb-2">
                                <h4 className="text-xs font-semibold uppercase tracking-wide text-[#6B6B6B]">
                                    Scholarships ({scholarshipsApplied}/{scholarships.length} applied)
                                </h4>
                                <ProgressBar pct={scholarshipPct} />
                            </div>
                            <ul className="space-y-1">
                                {scholarships.map((s) => (
                                    <li key={s.scholarship_id}>
                                        <button
                                            type="button"
                                            onClick={() => onNavigate(`/roadmap?tab=scholarships&scholarship_id=${s.scholarship_id}`)}
                                            className="w-full text-left flex items-baseline justify-between gap-2
                                                px-2 py-1 -mx-2 rounded hover:bg-[#F8F6F0] transition-colors"
                                        >
                                            <span className="text-[#4A4A4A] truncate">{s.scholarship_name || 'Scholarship'}</span>
                                            <StatusPill value={s.status || 'not_applied'} kind="scholarship" />
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    )}
                </div>
            )}
        </div>
    );
}

function ProgressBar({ pct }) {
    return (
        <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-20 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                <div
                    className="h-full bg-[#1A4D2E] transition-all"
                    style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
                />
            </div>
            <span className="text-xs text-[#6B6B6B] tabular-nums w-9 text-right">{pct}%</span>
        </div>
    );
}

const STATUS_PILL_STYLES = {
    // Essays
    not_started: 'bg-stone-100 text-stone-600',
    draft: 'bg-blue-100 text-blue-700',
    review: 'bg-amber-100 text-amber-700',
    final: 'bg-emerald-100 text-emerald-700',
    // Scholarships
    not_applied: 'bg-stone-100 text-stone-600',
    applied: 'bg-blue-100 text-blue-700',
    received: 'bg-emerald-100 text-emerald-700',
    not_eligible: 'bg-red-100 text-red-600',
};

const STATUS_PILL_LABELS = {
    not_started: 'Not started',
    draft: 'Draft',
    review: 'Review',
    final: 'Final',
    not_applied: 'Not applied',
    applied: 'Applied',
    received: 'Received',
    not_eligible: 'Not eligible',
};

function StatusPill({ value }) {
    const cls = STATUS_PILL_STYLES[value] || 'bg-stone-100 text-stone-600';
    const label = STATUS_PILL_LABELS[value] || value;
    return (
        <span className={`text-xs px-2 py-0.5 rounded-full whitespace-nowrap ${cls}`}>
            {label}
        </span>
    );
}

// Essay Help Modal Component
function EssayHelpModal({ school, onClose }) {
    const [prompt, setPrompt] = useState('');
    const [response, setResponse] = useState('');
    const [loading, setLoading] = useState(false);

    const suggestedPrompts = [
        `What should I focus on for my ${school.university_name} essay?`,
        `How can I make my ${school.university_name} supplemental essay stand out?`,
        `What are common mistakes to avoid for ${school.university_name}?`,
        `Help me brainstorm ideas for my ${school.university_name} "Why Us" essay`
    ];

    const handleAskAI = async () => {
        if (!prompt.trim()) return;

        setLoading(true);
        setResponse('');

        // For now, provide a structured response template
        // This can be connected to actual AI streaming later
        setTimeout(() => {
            setResponse(`## Essay Guidance for ${school.university_name}

### Key Themes to Address
Based on ${school.university_name}'s values and what they look for:

${school.essay_tips?.map((tip, i) => `${i + 1}. ${tip}`).join('\n\n') || '- Be authentic and specific\n- Show genuine interest in programs\n- Connect your experiences to their values'}

### Your Prompt: "${prompt}"

**Suggested Approach:**
1. Start with a specific anecdote or moment
2. Connect to ${school.university_name}'s unique offerings
3. Show what you'll contribute to their community
4. Be specific about programs, professors, or opportunities

### Next Steps
- Draft an outline based on these themes
- Use specific details from your research
- Have someone review for authenticity`);
            setLoading(false);
        }, 1000);
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>Essay Help: {school.university_name}</h2>
                    <button className="close-btn" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {/* Suggested Prompts */}
                    <div className="suggested-prompts">
                        <p>Quick questions:</p>
                        <div className="prompt-chips">
                            {suggestedPrompts.map((p, i) => (
                                <button
                                    key={i}
                                    className="prompt-chip"
                                    onClick={() => setPrompt(p)}
                                >
                                    {p}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Input */}
                    <div className="prompt-input">
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Ask anything about your essay..."
                            rows={3}
                        />
                        <button
                            className="ask-btn"
                            onClick={handleAskAI}
                            disabled={!prompt.trim() || loading}
                        >
                            {loading ? 'Thinking...' : 'Ask AI'}
                        </button>
                    </div>

                    {/* Response */}
                    {response && (
                        <div className="ai-response">
                            <pre>{response}</pre>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
