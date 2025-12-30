import { useState, useEffect, useRef } from 'react'
import './index.css'

// API URLs
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8082'
const RESEARCH_AGENT_URL = import.meta.env.VITE_RESEARCH_AGENT_URL || 'https://university-profile-collector-pfnwjfp26a-ue.a.run.app'

function App() {
    const [page, setPage] = useState('landing')
    const [universityName, setUniversityName] = useState('')
    const [existingUniversities, setExistingUniversities] = useState([])
    const [researchProfiles, setResearchProfiles] = useState([])
    const [selectedExisting, setSelectedExisting] = useState(null)
    const [selectedResearch, setSelectedResearch] = useState(null)
    const [profile, setProfile] = useState(null)
    const [validationReport, setValidationReport] = useState(null)
    const [comparison, setComparison] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [researchProgress, setResearchProgress] = useState('')
    const [agentLogs, setAgentLogs] = useState([])
    const [currentAgent, setCurrentAgent] = useState('')
    const [filledFields, setFilledFields] = useState([])  // Track fields filled by gap analysis
    const [gapFillRuns, setGapFillRuns] = useState(0)     // Track how many gap fill runs

    // Fetch existing universities and research profiles on mount
    useEffect(() => {
        fetchUniversities()
        fetchResearchProfiles()
    }, [])

    const fetchUniversities = async () => {
        try {
            const res = await fetch(`${API_URL}/universities`)
            const data = await res.json()
            if (data.success) {
                setExistingUniversities(data.universities)
            }
        } catch (e) {
            console.error('Failed to fetch universities:', e)
        }
    }

    const fetchResearchProfiles = async () => {
        try {
            const res = await fetch(`${API_URL}/research-profiles`)
            const data = await res.json()
            if (data.success) {
                setResearchProfiles(data.profiles || [])
            }
        } catch (e) {
            console.error('Failed to fetch research profiles:', e)
        }
    }

    // Load a research profile from GCS
    const loadResearchProfile = async (filename) => {
        setLoading(true)
        setError(null)

        try {
            const res = await fetch(`${API_URL}/research-profile?filename=${encodeURIComponent(filename)}`)
            const data = await res.json()

            if (data.success) {
                const profileData = data.profile.university_profile || data.profile
                setProfile(profileData)
                setUniversityName(profileData?.metadata?.official_name || filename.replace('.json', ''))

                // Auto-validate
                await handleValidate(profileData)
                setPage('report')
            } else {
                setError(data.error || 'Failed to load profile')
            }
        } catch (e) {
            setError(e.message)
        }

        setLoading(false)
    }

    // Research a university using the university_profile_collector agent
    // Uses the /research proxy endpoint to avoid CORS issues
    const handleResearch = async () => {
        setLoading(true)
        setError(null)
        setAgentLogs([])
        setCurrentAgent('')
        setResearchProgress('🚀 Starting research...')
        setPage('research')

        const addLog = (agent, message, type = 'info') => {
            const timestamp = new Date().toLocaleTimeString()
            const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
            setAgentLogs(prev => [...prev.slice(-50), { id, timestamp, agent, message, type }])
        }

        try {
            addLog('System', `Starting research for: ${universityName}`, 'start')
            addLog('System', 'This may take 5-10 minutes. The agent is calling multiple APIs and LLMs...', 'info')
            setCurrentAgent('ResearchCoordinator')
            setResearchProgress('🔍 Researching university data...')

            // Call the /research proxy endpoint on our cloud function
            // This avoids CORS by calling the agent server-side
            const res = await fetch(`${API_URL}/research`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ university_name: universityName })
            })

            const data = await res.json()

            if (!res.ok || !data.success) {
                throw new Error(data.error || `Research failed: ${res.status}`)
            }

            addLog('System', `Research completed! Processing ${data.events_count || 0} events...`, 'complete')
            setResearchProgress('Research complete! Loading profile...')
            setCurrentAgent('')

            // Check if profile was returned
            if (data.profile) {
                const loadedProfile = data.profile.university_profile || data.profile
                setProfile(loadedProfile)
                addLog('System', '📄 Profile loaded successfully!', 'complete')

                // Auto-validate
                await handleValidate(loadedProfile)
                setPage('report')
                setLoading(false)
                return
            }

            // Try to fetch profile from GCS
            addLog('System', `Looking for profile: ${data.filename}`, 'info')
            try {
                const profileRes = await fetch(`${API_URL}/research-profile?filename=${encodeURIComponent(data.filename)}`)
                const profileData = await profileRes.json()

                if (profileData.success && profileData.profile) {
                    const loadedProfile = profileData.profile.university_profile || profileData.profile
                    setProfile(loadedProfile)
                    addLog('System', '📄 Profile loaded from cloud storage!', 'complete')

                    // Auto-validate
                    await handleValidate(loadedProfile)
                    setPage('report')
                    setLoading(false)
                    return
                }
            } catch (e) {
                console.log('Profile fetch from GCS failed:', e)
            }

            // Profile not found
            setError('Research completed but profile not yet available. Try refreshing the page.')
            addLog('System', '⚠️ Profile not found in cloud storage', 'error')

        } catch (e) {
            addLog('System', `❌ Error: ${e.message}`, 'error')
            setError(e.message)
        }

        setLoading(false)
    }


    // Handle file upload
    const handleFileUpload = async (event) => {
        const file = event.target.files[0]
        if (!file) return

        try {
            const text = await file.text()
            const json = JSON.parse(text)

            // Handle nested wrapper
            const profileData = json.university_profile || json
            setProfile(profileData)
            setError(null)

            // Auto-validate
            await handleValidate(profileData)
            setPage('report')
        } catch (e) {
            setError('Failed to parse JSON file: ' + e.message)
        }
    }

    // Validate profile
    const handleValidate = async (profileData = profile) => {
        try {
            const res = await fetch(`${API_URL}/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile: profileData })
            })

            const data = await res.json()
            setValidationReport(data)
        } catch (e) {
            console.error('Validation failed:', e)
        }
    }

    // Compare with ES
    const handleCompare = async () => {
        setLoading(true)

        try {
            const universityId = profile?._id || profile?.university_id ||
                (profile?.metadata?.official_name || '').toLowerCase().replace(/\s+/g, '_')

            const res = await fetch(`${API_URL}/compare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    university_id: universityId,
                    new_profile: profile
                })
            })

            const data = await res.json()
            setComparison(data)
            setPage('compare')
        } catch (e) {
            setError(e.message)
        }

        setLoading(false)
    }

    // Ingest to ES
    const handleIngest = async () => {
        setLoading(true)
        setError(null)

        try {
            const res = await fetch(`${API_URL}/ingest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profile, overwrite: true })
            })

            const data = await res.json()

            if (data.success) {
                setPage('complete')
            } else {
                setError(data.error || 'Ingestion failed')
            }
        } catch (e) {
            setError(e.message)
        }

        setLoading(false)
    }

    // Fill gaps using agent with Google Search
    const handleFillGaps = async () => {
        setLoading(true)
        setError(null)

        try {
            const fieldsToFill = validationReport?.null_fields || []

            if (fieldsToFill.length === 0) {
                setError('No missing fields to fill!')
                setLoading(false)
                return
            }

            const res = await fetch(`${API_URL}/fill-gaps`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile,
                    fields_to_fill: fieldsToFill.slice(0, 30)  // Limit to 30 fields per run
                })
            })

            const data = await res.json()

            if (data.updated_profile) {
                // Update profile with merged data
                setProfile(data.updated_profile)

                // Track newly filled fields (append to existing)
                const newlyFilled = data.filled_fields || []
                if (newlyFilled.length > 0) {
                    setFilledFields(prev => [...prev, ...newlyFilled])
                    setGapFillRuns(prev => prev + 1)
                }

                // Re-validate to update missing count
                await handleValidate(data.updated_profile)

                if (!data.success) {
                    setError(data.error || 'Some fields could not be found')
                }
            } else {
                setError(data.error || 'Gap filling failed - no data returned')
            }
        } catch (e) {
            setError(`Gap filling failed: ${e.message}`)
        }

        setLoading(false)
    }


    // Step Indicator
    const StepIndicator = ({ current }) => (
        <div className="um-steps">
            {['Input', 'Research', 'Report', 'Compare', 'Ingest'].map((step, i) => (
                <div key={i} className={`um-step ${i + 1 <= current ? 'active' : ''} ${i + 1 === current ? 'current' : ''}`}>
                    <span className="um-step-num">{i + 1}</span>
                    <span className="um-step-label">{step}</span>
                </div>
            ))}
        </div>
    )

    // Landing Page
    if (page === 'landing') {
        return (
            <div className="um-app">
                <div className="um-bg">
                    <div className="um-blob um-blob-1" />
                    <div className="um-blob um-blob-2" />
                </div>

                <nav className="um-nav">
                    <div className="um-nav-inner">
                        <div className="um-logo">
                            <span className="um-logo-icon">⛏️</span>
                            <span className="um-logo-text">UniMiner</span>
                        </div>
                    </div>
                </nav>

                <section className="um-hero">
                    <div className="um-hero-content">
                        <div className="um-badge">🎓 University Research Pipeline</div>
                        <h1 className="um-hero-title">Uni<span>Miner</span></h1>
                        <p className="um-hero-subtitle">
                            Research universities, validate data quality, fill gaps with APIs,
                            and push verified profiles to Elasticsearch.
                        </p>
                        <div className="um-hero-actions">
                            <button className="um-btn um-btn-primary um-btn-large" onClick={() => setPage('input')}>
                                ⛏️ Start Mining
                            </button>
                        </div>
                    </div>
                </section>

                <section className="um-pipeline">
                    <div className="um-pipeline-header">
                        <p className="um-section-label">How It Works</p>
                        <h2 className="um-section-title">Research → Validate → Enrich → Ingest</h2>
                    </div>
                    <div className="um-pipeline-steps">
                        {[
                            { icon: '🎯', title: 'Select', desc: 'Choose a university' },
                            { icon: '🔬', title: 'Research', desc: 'Run collector agent' },
                            { icon: '📊', title: 'Validate', desc: 'Quality report' },
                            { icon: '🔧', title: 'Fill Gaps', desc: 'API enrichment' },
                            { icon: '✅', title: 'Ingest', desc: 'Push to ES' }
                        ].map((step, i) => (
                            <div className="um-step-card" key={i}>
                                <div className="um-step-icon">{step.icon}</div>
                                <h3 className="um-step-title">{step.title}</h3>
                                <p className="um-step-desc">{step.desc}</p>
                            </div>
                        ))}
                    </div>
                </section>
            </div>
        )
    }

    // Input Page
    if (page === 'input') {
        return (
            <div className="um-app">
                <div className="um-bg">
                    <div className="um-blob um-blob-1" />
                    <div className="um-blob um-blob-2" />
                </div>

                <nav className="um-nav">
                    <div className="um-nav-inner">
                        <div className="um-logo" onClick={() => setPage('landing')}>
                            <span className="um-logo-icon">⛏️</span>
                            <span className="um-logo-text">UniMiner</span>
                        </div>
                    </div>
                </nav>

                <section className="um-wizard">
                    <div className="um-wizard-content">
                        <StepIndicator current={1} />
                        <h1 className="um-wizard-title">Select a University</h1>
                        <p className="um-wizard-subtitle">
                            Enter a new university to research, or select an existing one to update.
                        </p>

                        <div className="um-input-section">
                            <label className="um-label">Research New University</label>
                            <input
                                type="text"
                                className="um-input"
                                placeholder="e.g., Stanford University"
                                value={universityName}
                                onChange={(e) => setUniversityName(e.target.value)}
                            />

                            <div className="um-examples">
                                <p className="um-examples-label">Try:</p>
                                <div className="um-chips">
                                    {['Stanford University', 'MIT', 'Harvard University', 'UCLA'].map(name => (
                                        <button key={name} className="um-chip" onClick={() => setUniversityName(name)}>
                                            {name}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {existingUniversities.length > 0 && (
                            <div className="um-input-section">
                                <label className="um-label">Or Update Existing ({existingUniversities.length})</label>
                                <select
                                    className="um-select"
                                    value={selectedExisting || ''}
                                    onChange={(e) => {
                                        setSelectedExisting(e.target.value)
                                        const uni = existingUniversities.find(u => u.university_id === e.target.value)
                                        if (uni) setUniversityName(uni.official_name)
                                    }}
                                >
                                    <option value="">Select existing university...</option>
                                    {existingUniversities.map(u => (
                                        <option key={u.university_id} value={u.university_id}>
                                            {u.official_name} (#{u.us_news_rank || 'N/A'})
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        {researchProfiles.length > 0 && (
                            <div className="um-input-section">
                                <label className="um-label">📦 Research Profiles from Cloud ({researchProfiles.length})</label>
                                <select
                                    className="um-select"
                                    value={selectedResearch || ''}
                                    onChange={(e) => {
                                        setSelectedResearch(e.target.value)
                                        if (e.target.value) {
                                            loadResearchProfile(e.target.value)
                                        }
                                    }}
                                >
                                    <option value="">Select a completed research...</option>
                                    {researchProfiles.map(p => (
                                        <option key={p.filename} value={p.filename}>
                                            {p.name.replace(/_/g, ' ')} ({new Date(p.updated).toLocaleDateString()})
                                        </option>
                                    ))}
                                </select>
                                <p className="um-examples-label">Profiles from previous research runs (saved in GCS)</p>
                            </div>
                        )}

                        <div className="um-input-section">
                            <label className="um-label">Or Upload Local JSON</label>
                            <input
                                type="file"
                                accept=".json"
                                className="um-input"
                                onChange={handleFileUpload}
                            />
                        </div>

                        {error && <div className="um-error">{error}</div>}

                        <div className="um-wizard-actions">
                            <button className="um-btn um-btn-ghost" onClick={() => setPage('landing')}>
                                ← Back
                            </button>
                            <button
                                className="um-btn um-btn-primary um-btn-large"
                                disabled={!universityName.trim() || loading}
                                onClick={handleResearch}
                            >
                                {loading ? '⏳ Loading...' : '🔬 Start New Research →'}
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        )
    }

    // Research Page (loading)
    if (page === 'research') {
        // Research is triggered by handleResearch which sets page to 'research'
        // No auto-start here - that caused render loops

        return (
            <div className="um-app">
                <div className="um-bg">
                    <div className="um-blob um-blob-1" />
                    <div className="um-blob um-blob-2" />
                </div>

                <nav className="um-nav">
                    <div className="um-nav-inner">
                        <div className="um-logo">
                            <span className="um-logo-icon">⛏️</span>
                            <span className="um-logo-text">UniMiner</span>
                        </div>
                    </div>
                </nav>

                <section className="um-wizard">
                    <div className="um-wizard-content um-wide">
                        <StepIndicator current={2} />
                        <h1 className="um-wizard-title">Researching {universityName}</h1>

                        {/* Current agent indicator */}
                        {currentAgent && (
                            <div className="um-current-agent">
                                <span className="um-agent-badge">🤖 {currentAgent}</span>
                            </div>
                        )}

                        {/* Progress message */}
                        <p className="um-wizard-subtitle">{researchProgress}</p>

                        {/* Live agent log */}
                        <div className="um-agent-log">
                            <div className="um-log-header">
                                <span>📋 Agent Activity Log</span>
                                {loading && <span className="um-log-live">● LIVE</span>}
                            </div>
                            <div className="um-log-scroll" id="agent-log">
                                {agentLogs.length === 0 && (
                                    <div className="um-log-empty">Waiting for agent to start...</div>
                                )}
                                {agentLogs.map((log) => (
                                    <div key={log.id} className={`um-log-entry um-log-${log.type}`}>
                                        <span className="um-log-time">{log.timestamp}</span>
                                        <span className="um-log-agent">{log.agent}</span>
                                        <span className="um-log-msg">{log.message}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {error && <div className="um-error">{error}</div>}

                        <div className="um-wizard-actions">
                            <button
                                className="um-btn um-btn-ghost"
                                onClick={() => { setPage('input'); setLoading(false); setAgentLogs([]); }}
                            >
                                ← Cancel
                            </button>
                            {!loading && (
                                <button
                                    className="um-btn um-btn-primary"
                                    onClick={() => { setError(null); handleResearch(); }}
                                >
                                    🔄 Retry Research
                                </button>
                            )}
                        </div>
                    </div>
                </section>
            </div>
        )
    }

    // Report Page
    if (page === 'report') {
        const score = validationReport?.quality_score || 0
        const scoreColor = score >= 90 ? '#22c55e' : score >= 70 ? '#eab308' : '#ef4444'
        const missingCount = validationReport?.null_field_count || 0
        const populatedCount = validationReport?.populated_fields || 0

        // Group missing fields by category
        const groupMissingFields = () => {
            const fields = validationReport?.null_fields || []
            const groups = {}

            fields.forEach(field => {
                let category = 'General'
                let readable = field

                if (field.includes('admissions_data') || field.includes('admission') || field.includes('acceptance')) {
                    category = 'Admissions'
                    readable = field.split('.').pop().replace(/_/g, ' ')
                } else if (field.includes('financials') || field.includes('tuition') || field.includes('scholarship') || field.includes('aid')) {
                    category = 'Financials'
                    readable = field.split('.').pop().replace(/_/g, ' ')
                } else if (field.includes('outcomes') || field.includes('earning') || field.includes('employment') || field.includes('retention')) {
                    category = 'Outcomes'
                    readable = field.split('.').pop().replace(/_/g, ' ')
                } else if (field.includes('application') || field.includes('essay') || field.includes('deadline')) {
                    category = 'Application'
                    readable = field.split('.').pop().replace(/_/g, ' ')
                } else if (field.includes('academic') || field.includes('college') || field.includes('major')) {
                    category = 'Academics'
                    readable = field.split('.').pop().replace(/_/g, ' ')
                } else if (field.includes('demographic')) {
                    category = 'Demographics'
                    readable = field.split('.').pop().replace(/_/g, ' ')
                }

                if (!groups[category]) groups[category] = []
                groups[category].push({
                    path: field,
                    readable: readable.charAt(0).toUpperCase() + readable.slice(1)
                })
            })

            return groups
        }

        const groupedMissing = groupMissingFields()
        const categories = Object.keys(groupedMissing).sort()

        return (
            <div className="um-app">
                <div className="um-bg">
                    <div className="um-blob um-blob-1" />
                    <div className="um-blob um-blob-2" />
                </div>

                <nav className="um-nav">
                    <div className="um-nav-inner">
                        <div className="um-logo" onClick={() => setPage('landing')}>
                            <span className="um-logo-icon">⛏️</span>
                            <span className="um-logo-text">UniMiner</span>
                        </div>
                    </div>
                </nav>

                <section className="um-wizard">
                    <div className="um-wizard-content um-full-width">
                        <StepIndicator current={3} />

                        {/* Header with stats */}
                        <div className="um-report-header">
                            <div className="um-report-title">
                                <h1>{profile?.metadata?.official_name || universityName}</h1>
                                <p className="um-report-meta">
                                    Data Quality Report {gapFillRuns > 0 && `• ${gapFillRuns} gap fill run${gapFillRuns > 1 ? 's' : ''}`}
                                </p>
                            </div>
                            <div className="um-report-stats">
                                <div className="um-stat" style={{ borderColor: scoreColor }}>
                                    <span className="um-stat-value" style={{ color: scoreColor }}>{score}%</span>
                                    <span className="um-stat-label">Complete</span>
                                </div>
                                <div className="um-stat">
                                    <span className="um-stat-value">{populatedCount}</span>
                                    <span className="um-stat-label">Populated</span>
                                </div>
                                <div className="um-stat um-stat-warning">
                                    <span className="um-stat-value">{missingCount}</span>
                                    <span className="um-stat-label">Missing</span>
                                </div>
                            </div>
                        </div>

                        {/* Error/Success Messages */}
                        {error && <div className="um-error-box">⚠️ {error}</div>}

                        {/* Filled Fields Section (shows after gap fill) */}
                        {filledFields.length > 0 && (
                            <div className="um-success-card">
                                <h3>✅ Filled by Gap Analysis ({filledFields.length} fields)</h3>
                                <div className="um-filled-fields">
                                    {filledFields.map((field, i) => (
                                        <span key={i} className="um-filled-tag">{field}</span>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Missing Fields Section */}
                        {missingCount > 0 ? (
                            <div className="um-missing-section">
                                <h2>⚠️ Missing Data ({missingCount} fields)</h2>
                                <p className="um-missing-hint">
                                    Click "Fill Gaps" to use AI search to find this data. You can run multiple times until all gaps are filled.
                                </p>

                                <div className="um-missing-grid">
                                    {categories.map(category => (
                                        <div key={category} className="um-missing-category">
                                            <h3>{category} <span className="um-count">{groupedMissing[category].length}</span></h3>
                                            <ul>
                                                {groupedMissing[category].slice(0, 10).map((field, i) => (
                                                    <li key={i}>{field.readable}</li>
                                                ))}
                                                {groupedMissing[category].length > 10 && (
                                                    <li className="um-more">+{groupedMissing[category].length - 10} more...</li>
                                                )}
                                            </ul>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <div className="um-success-card um-complete">
                                <h3>🎉 All Fields Complete!</h3>
                                <p>This profile has all required data. Ready to compare and ingest to Elasticsearch.</p>
                            </div>
                        )}

                        {/* Actions */}
                        <div className="um-report-actions">
                            <button className="um-btn um-btn-ghost" onClick={() => setPage('input')}>
                                ← New Research
                            </button>
                            <button
                                className="um-btn um-btn-secondary um-btn-large"
                                disabled={loading || missingCount === 0}
                                onClick={handleFillGaps}
                            >
                                {loading ? '⏳ Finding data...' : `🔍 Fill Gaps (${Math.min(30, missingCount)} fields)`}
                            </button>
                            <button
                                className="um-btn um-btn-primary um-btn-large"
                                disabled={loading}
                                onClick={handleCompare}
                            >
                                Compare with ES →
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        )
    }


    // Compare Page
    if (page === 'compare') {
        return (
            <div className="um-app">
                <div className="um-bg">
                    <div className="um-blob um-blob-1" />
                    <div className="um-blob um-blob-2" />
                </div>

                <nav className="um-nav">
                    <div className="um-nav-inner">
                        <div className="um-logo" onClick={() => setPage('landing')}>
                            <span className="um-logo-icon">⛏️</span>
                            <span className="um-logo-text">UniMiner</span>
                        </div>
                    </div>
                </nav>

                <section className="um-wizard">
                    <div className="um-wizard-content um-wide">
                        <StepIndicator current={4} />
                        <h1 className="um-wizard-title">ES Comparison</h1>

                        {!comparison?.exists_in_es ? (
                            <div className="um-info-card">
                                <h3>🆕 New University</h3>
                                <p>This university is not yet in Elasticsearch. Ingestion will create a new record.</p>
                            </div>
                        ) : (
                            <>
                                <div className="um-diff-summary">
                                    <div className="um-diff-stat um-change">
                                        <span className="um-diff-num">{comparison?.summary?.total_changes || 0}</span>
                                        <span className="um-diff-label">Changes</span>
                                    </div>
                                    <div className="um-diff-stat um-add">
                                        <span className="um-diff-num">{comparison?.summary?.total_additions || 0}</span>
                                        <span className="um-diff-label">New Fields</span>
                                    </div>
                                    <div className="um-diff-stat um-remove">
                                        <span className="um-diff-num">{comparison?.summary?.total_removals || 0}</span>
                                        <span className="um-diff-label">Removed</span>
                                    </div>
                                </div>

                                {comparison?.critical_changes?.length > 0 && (
                                    <div className="um-critical-changes">
                                        <h3>⚠️ Critical Changes</h3>
                                        {comparison.critical_changes.map((c, i) => (
                                            <div key={i} className="um-change-item">
                                                <span className="um-field">{c.field}</span>
                                                <span className="um-old">{JSON.stringify(c.old)}</span>
                                                <span className="um-arrow">→</span>
                                                <span className="um-new">{JSON.stringify(c.new)}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {comparison?.changes?.length > 0 && (
                                    <div className="um-changes-list">
                                        <h3>All Changes ({comparison.changes.length})</h3>
                                        <div className="um-changes-scroll">
                                            {comparison.changes.slice(0, 30).map((c, i) => (
                                                <div key={i} className="um-change-item">
                                                    <span className="um-field">{c.field}</span>
                                                    <span className="um-old">{JSON.stringify(c.old)?.substring(0, 50)}</span>
                                                    <span className="um-arrow">→</span>
                                                    <span className="um-new">{JSON.stringify(c.new)?.substring(0, 50)}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}

                        {error && <div className="um-error">{error}</div>}

                        <div className="um-wizard-actions">
                            <button className="um-btn um-btn-ghost" onClick={() => setPage('report')}>
                                ← Back to Report
                            </button>
                            <button
                                className="um-btn um-btn-primary um-btn-large"
                                disabled={loading}
                                onClick={handleIngest}
                            >
                                {loading ? '⏳ Ingesting...' : '✅ Approve & Ingest'}
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        )
    }

    // Complete Page
    if (page === 'complete') {
        return (
            <div className="um-app">
                <div className="um-bg">
                    <div className="um-blob um-blob-1" />
                    <div className="um-blob um-blob-2" />
                </div>

                <nav className="um-nav">
                    <div className="um-nav-inner">
                        <div className="um-logo" onClick={() => setPage('landing')}>
                            <span className="um-logo-icon">⛏️</span>
                            <span className="um-logo-text">UniMiner</span>
                        </div>
                    </div>
                </nav>

                <section className="um-wizard">
                    <div className="um-wizard-content">
                        <StepIndicator current={5} />
                        <div className="um-success">
                            <div className="um-success-icon">✅</div>
                            <h1 className="um-wizard-title">Successfully Ingested!</h1>
                            <p className="um-wizard-subtitle">
                                {profile?.metadata?.official_name || universityName} has been pushed to Elasticsearch.
                            </p>
                        </div>

                        <div className="um-wizard-actions">
                            <button
                                className="um-btn um-btn-primary um-btn-large"
                                onClick={() => {
                                    setProfile(null)
                                    setValidationReport(null)
                                    setComparison(null)
                                    setUniversityName('')
                                    setPage('input')
                                }}
                            >
                                ⛏️ Mine Another
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        )
    }

    return null
}

export default App
