import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import '../styles/ApplicationsPage.css';

// API URLs
const API_BASE_URL = import.meta.env.VITE_PROFILE_MANAGER_V2_URL || 'https://profile-manager-v2-pfnwjfp26a-ue.a.run.app';
const KB_URL = import.meta.env.VITE_KNOWLEDGE_BASE_UNIVERSITIES_URL || 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app';

export default function ApplicationsPage() {
    const { currentUser } = useAuth();
    const [schools, setSchools] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [essayHelpModal, setEssayHelpModal] = useState({ open: false, school: null });

    // Fetch user's schools with deadlines
    const fetchSchools = useCallback(async () => {
        if (!currentUser?.email) return;

        try {
            setLoading(true);
            const response = await fetch(`${API_BASE_URL}/get-deadlines`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_email: currentUser.email })
            });
            const data = await response.json();

            if (data.success) {
                // Group by university
                const schoolMap = {};
                data.deadlines.forEach(d => {
                    if (!schoolMap[d.university_id]) {
                        schoolMap[d.university_id] = {
                            university_id: d.university_id,
                            university_name: d.university_name,
                            deadlines: [],
                            essay_tips: []
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
                setError(data.error);
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
            <div className="essay-page">
                <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading your schools...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="essay-page">
                <div className="error-state">
                    <p>Error: {error}</p>
                    <button onClick={fetchSchools}>Retry</button>
                </div>
            </div>
        );
    }

    return (
        <div className="essay-page">
            {/* Header */}
            <header className="essay-header">
                <h1>Essay Assistant</h1>
                <p className="subtitle">Deadlines and essay guidance for your saved schools</p>
            </header>

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
                                        <h3>{school.university_name}</h3>
                                        {nextDeadline && (
                                            <div className={`deadline-badge ${getUrgencyClass(daysUntil)}`}>
                                                <span className="deadline-plan">{nextDeadline.plan_type}</span>
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
