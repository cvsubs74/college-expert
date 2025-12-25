import { useState, useEffect } from 'react'
import './index.css'

const API_URL = import.meta.env.VITE_API_URL || ''

function App() {
  const [page, setPage] = useState('home')
  const [universityName, setUniversityName] = useState('')
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [sources, setSources] = useState([])
  const [selectedSource, setSelectedSource] = useState(null)
  const [editedUrl, setEditedUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null) // { type: 'success'|'error', message: string }
  const [validating, setValidating] = useState(null) // sourceKey being validated

  // Auto-hide toast after 5 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  useEffect(() => {
    if (!jobId || jobStatus?.status === 'completed' || jobStatus?.status === 'failed') return

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/api/discover/${jobId}`)
        const data = await res.json()
        setJobStatus(data)

        if (data.status === 'completed') {
          setSources(data.result)
          setPage('review')
        }
      } catch (err) {
        console.error('Poll error:', err)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [jobId, jobStatus?.status])

  async function startDiscovery() {
    if (!universityName.trim()) return
    setLoading(true)
    setError(null)
    setPage('discover')

    try {
      const res = await fetch(`${API_URL}/api/discover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ university_name: universityName })
      })
      const data = await res.json()
      setJobId(data.job_id)
      setJobStatus(data)
    } catch (err) {
      setError('Failed to start discovery: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  // State for validation results modal
  const [validationResult, setValidationResult] = useState(null)

  // State for API key configuration modal
  const [apiKeyModal, setApiKeyModal] = useState(null) // { keyName, keyConfig, sourceKey }
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [savingKey, setSavingKey] = useState(false)

  async function validateSource(sourceKey) {
    const universityId = sources.university_id
    setValidating(sourceKey)
    setValidationResult(null)
    try {
      const res = await fetch(`${API_URL}/api/sources/${universityId}/${sourceKey}/validate`, {
        method: 'POST'
      })
      const data = await res.json()

      if (data.validation?.accessible) {
        // Show validation result modal with sample data
        if (data.validation?.sample_data) {
          setValidationResult({
            sourceKey,
            url: data.url,
            sourceType: data.source_type,
            apiType: data.validation.api_type || (data.validation.is_pdf ? 'pdf' : data.validation.is_html ? 'web' : 'file'),
            sampleData: data.validation.sample_data,
            message: data.validation.message,
            statusCode: data.validation.status_code,
            contentType: data.validation.content_type
          })
          setToast({ type: 'success', message: data.validation.message || '✅ Validated!' })
        } else {
          setToast({ type: 'success', message: data.validation.message || `✅ URL validated: ${data.url}` })
        }
      } else if (data.validation?.needs_api_key) {
        // API needs a key - show configuration modal
        setApiKeyModal({
          keyName: data.validation.key_name,
          keyConfig: data.validation.key_config,
          sourceKey: sourceKey
        })
      } else {
        const errorMsg = data.validation?.error || `Status: ${data.validation?.status_code || 'Unknown'}`
        setToast({ type: 'error', message: `❌ Validation failed: ${errorMsg}` })
      }

      await loadSources(universityId)
    } catch (err) {
      setToast({ type: 'error', message: `Validation failed: ${err.message}` })
    } finally {
      setValidating(null)
    }
  }

  // State for test results preview
  const [testResult, setTestResult] = useState(null)

  async function testApiKey() {
    if (!apiKeyModal || !apiKeyInput.trim()) return

    setSavingKey(true)
    setTestResult(null)
    try {
      const testRes = await fetch(`${API_URL}/api/keys/${apiKeyModal.keyName}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_key: apiKeyInput })
      })
      const testData = await testRes.json()

      if (testData.success) {
        setTestResult(testData)
        setToast({ type: 'success', message: testData.message })
      } else {
        setToast({ type: 'error', message: `❌ ${testData.error}` })
      }
    } catch (err) {
      setToast({ type: 'error', message: `Test failed: ${err.message}` })
    } finally {
      setSavingKey(false)
    }
  }

  async function saveApiKey() {
    if (!apiKeyModal || !apiKeyInput.trim()) return

    setSavingKey(true)
    try {
      // Save the key
      const saveRes = await fetch(`${API_URL}/api/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key_name: apiKeyModal.keyName, api_key: apiKeyInput })
      })
      const saveData = await saveRes.json()

      if (saveData.success) {
        setToast({ type: 'success', message: '✅ API key saved!' })
        setApiKeyModal(null)
        setApiKeyInput('')
        setTestResult(null)

        // Re-validate the source
        setTimeout(() => validateSource(apiKeyModal.sourceKey), 500)
      } else {
        setToast({ type: 'error', message: `❌ Failed to save: ${saveData.error}` })
      }
    } catch (err) {
      setToast({ type: 'error', message: `Failed to save key: ${err.message}` })
    } finally {
      setSavingKey(false)
    }
  }

  async function updateSource(sourceKey) {
    const universityId = sources.university_id
    try {
      await fetch(`${API_URL}/api/sources/${universityId}/${sourceKey}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: editedUrl })
      })
      setSelectedSource(null)
      setEditedUrl('')
      await loadSources(universityId)
    } catch (err) {
      setError('Update failed: ' + err.message)
    }
  }

  async function loadSources(universityId) {
    try {
      const res = await fetch(`${API_URL}/api/sources/${universityId}`)
      const data = await res.json()
      setSources(data)
    } catch (err) {
      setError('Failed to load sources')
    }
  }

  async function finalizeSources(activeSources) {
    const universityId = sources.university_id
    try {
      await fetch(`${API_URL}/api/sources/${universityId}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(activeSources)
      })
      setToast({ type: 'success', message: '✅ Sources finalized and YAML exported successfully!' })
      setTimeout(() => {
        setPage('home')
        setJobId(null)
        setJobStatus(null)
        setSources([])
        setUniversityName('')
      }, 2000)
    } catch (err) {
      setToast({ type: 'error', message: `Finalization failed: ${err.message}` })
    }
  }

  // Home/Landing Page
  if (page === 'home') {
    return (
      <div className="min-h-screen">
        {/* Background */}
        <div className="stratia-bg-blobs">
          <div className="stratia-blob stratia-blob-1" />
          <div className="stratia-blob stratia-blob-2" />
        </div>

        {/* Navigation */}
        <nav className="glass-nav">
          <div className="container">
            <div className="nav-inner">
              <div className="logo">
                <div className="logo-icon">🔍</div>
                <span className="logo-text">Source Curator</span>
              </div>
              <div className="nav-links">
                <a href="#features" className="nav-link">Features</a>
                <a href="#how-it-works" className="nav-link">How It Works</a>
              </div>
            </div>
          </div>
        </nav>

        {/* Hero Section */}
        <section className="hero">
          <div className="container">
            <div className="hero-content">
              <div className="hero-badge">✨ Powered by AI</div>
              <h1 className="hero-title">
                Discover & Curate<br />
                <span className="hero-accent">University Data Sources</span>
              </h1>
              <p className="hero-subtitle">
                Automatically find official APIs, Common Data Sets, and institutional
                websites for any university. Validate, organize, and export curated
                source configurations in seconds.
              </p>

              <div className="hero-search">
                <input
                  type="text"
                  value={universityName}
                  onChange={e => setUniversityName(e.target.value)}
                  placeholder="Enter a university name..."
                  className="hero-input"
                  onKeyDown={e => e.key === 'Enter' && startDiscovery()}
                />
                <button
                  onClick={startDiscovery}
                  disabled={loading || !universityName.trim()}
                  className="hero-button"
                >
                  {loading ? <span className="loading-spinner" /> : '🚀'}
                  <span>Start Discovery</span>
                </button>
              </div>

              <div className="hero-stats">
                <div className="stat">
                  <span className="stat-value">5+</span>
                  <span className="stat-label">Data Tiers</span>
                </div>
                <div className="stat-divider" />
                <div className="stat">
                  <span className="stat-value">100%</span>
                  <span className="stat-label">Automated</span>
                </div>
                <div className="stat-divider" />
                <div className="stat">
                  <span className="stat-value">YAML</span>
                  <span className="stat-label">Export Format</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="features">
          <div className="container">
            <h2 className="section-title">Powerful Features</h2>
            <p className="section-subtitle">Everything you need to curate authoritative data sources</p>

            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon">🎯</div>
                <h3 className="feature-title">IPEDS Lookup</h3>
                <p className="feature-desc">Automatically retrieves official IPEDS IDs and connects to College Scorecard API for verified data.</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔎</div>
                <h3 className="feature-title">Smart Discovery</h3>
                <p className="feature-desc">AI-powered search finds official websites, Common Data Sets, admissions pages, and more.</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">✅</div>
                <h3 className="feature-title">URL Validation</h3>
                <p className="feature-desc">Automatically validates each discovered URL, checking accessibility and detecting errors.</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">📝</div>
                <h3 className="feature-title">YAML Export</h3>
                <p className="feature-desc">Generates clean, structured YAML configuration files ready for your data pipeline.</p>
              </div>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="how-it-works">
          <div className="container">
            <h2 className="section-title">How It Works</h2>
            <p className="section-subtitle">Three simple steps to curated data sources</p>

            <div className="steps">
              <div className="step">
                <div className="step-number">1</div>
                <h3 className="step-title">Enter University</h3>
                <p className="step-desc">Type any university name and our AI agents begin the discovery process.</p>
              </div>
              <div className="step-arrow">→</div>
              <div className="step">
                <div className="step-number">2</div>
                <h3 className="step-title">Review Sources</h3>
                <p className="step-desc">Review discovered sources, validate URLs, and make corrections if needed.</p>
              </div>
              <div className="step-arrow">→</div>
              <div className="step">
                <div className="step-number">3</div>
                <h3 className="step-title">Export Config</h3>
                <p className="step-desc">Finalize your selections and export a production-ready YAML configuration.</p>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="cta">
          <div className="container">
            <div className="cta-card">
              <h2 className="cta-title">Ready to Get Started?</h2>
              <p className="cta-subtitle">Enter a university name above to begin discovering data sources.</p>
              <button onClick={() => document.querySelector('.hero-input').focus()} className="cta-button">
                Try It Now →
              </button>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="footer">
          <div className="container">
            <p>Part of <strong>Stratia Admissions</strong> • Source Curator v1.0</p>
          </div>
        </footer>
      </div>
    )
  }

  // Discovery Progress Page
  if (page === 'discover') {
    return (
      <div className="min-h-screen app-page">
        <div className="stratia-bg-blobs">
          <div className="stratia-blob stratia-blob-1" />
          <div className="stratia-blob stratia-blob-2" />
        </div>

        <nav className="glass-nav">
          <div className="container">
            <div className="nav-inner">
              <div className="logo" onClick={() => setPage('home')} style={{ cursor: 'pointer' }}>
                <div className="logo-icon">🔍</div>
                <span className="logo-text">Source Curator</span>
              </div>
            </div>
          </div>
        </nav>

        <main className="app-main">
          <div className="container narrow">
            <div className="progress-card">
              <div className="progress-header">
                <h2 className="headline-medium">Discovering Sources</h2>
                <p className="body-medium">for <strong>{universityName}</strong></p>
              </div>

              <div className="progress-animation">
                <div className="pulse-ring" />
                <div className="pulse-ring delay-1" />
                <div className="pulse-ring delay-2" />
                <span className="progress-icon">🔍</span>
              </div>

              <div className="progress-steps">
                {jobStatus?.steps?.map((step, i) => (
                  <div
                    key={i}
                    className={`progress-step ${i === jobStatus.steps.length - 1 && jobStatus.status === 'running' ? 'active' : 'done'}`}
                  >
                    <span className="progress-step-icon">
                      {i === jobStatus.steps.length - 1 && jobStatus.status === 'running'
                        ? <span className="loading-spinner small" />
                        : '✓'
                      }
                    </span>
                    <span>{step.step}</span>
                  </div>
                ))}
              </div>

              {error && (
                <div className="error-banner">
                  <p>{error}</p>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Review Page
  if (page === 'review' && sources?.sources) {
    return (
      <div className="min-h-screen app-page">
        <div className="stratia-bg-blobs">
          <div className="stratia-blob stratia-blob-1" />
          <div className="stratia-blob stratia-blob-2" />
        </div>

        <nav className="glass-nav">
          <div className="container">
            <div className="nav-inner">
              <div className="logo" onClick={() => setPage('home')} style={{ cursor: 'pointer' }}>
                <div className="logo-icon">🔍</div>
                <span className="logo-text">Source Curator</span>
              </div>
              <div className="nav-tabs">
                <button className="nav-tab active">📝 Review</button>
                <button className="nav-tab" onClick={() => setPage('finalize')}>✓ Finalize</button>
              </div>
            </div>
          </div>
        </nav>

        <main className="app-main">
          <div className="container">
            {/* University Header */}
            <div className="university-header">
              <h1 className="headline-large">{sources.official_name}</h1>
              <div className="university-meta">
                <span className="meta-chip">IPEDS: {sources.ipeds_id}</span>
                <span className="meta-chip">{Object.keys(sources.sources || {}).length} Sources Found</span>
              </div>
            </div>

            {/* Source Cards Grid */}
            <div className="sources-grid">
              {Object.entries(sources.sources || {}).map(([key, source]) => {
                const s = source.primary || source
                const isActive = s.is_active
                const hasError = s.notes?.includes('404')
                const isValidating = validating === key

                return (
                  <div key={key} className="source-card">
                    <div className="source-header">
                      <div className="source-tier">Tier {s.tier}</div>
                      <div className={`source-status ${isActive ? 'active' : hasError ? 'error' : 'draft'}`}>
                        {isActive ? '✓ Active' : hasError ? '✗ Error' : '◐ Draft'}
                      </div>
                    </div>
                    <h3 className="source-name">{s.name || key}</h3>
                    <p className="source-url">{s.url}</p>
                    {s.notes && <p className={`source-notes ${hasError ? 'error' : ''}`}>{s.notes}</p>}
                    <div className="source-actions">
                      <button
                        className="btn-small tonal"
                        onClick={() => validateSource(key)}
                        disabled={isValidating}
                      >
                        {isValidating ? <span className="loading-spinner small" /> : '🔄'}
                        {isValidating ? 'Validating...' : 'Validate'}
                      </button>
                      <button className="btn-small outlined" onClick={() => {
                        setSelectedSource(key)
                        setEditedUrl(s.url || '')
                      }}>
                        ✏️ Edit
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="page-actions">
              <button className="stratia-btn-filled large" onClick={() => setPage('finalize')}>
                Continue to Finalize →
              </button>
            </div>
          </div>
        </main>

        {/* Edit Modal */}
        {selectedSource && (
          <div className="modal-overlay" onClick={() => setSelectedSource(null)}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <h3 className="headline-small">Edit Source URL</h3>
              <input
                type="text"
                value={editedUrl}
                onChange={e => setEditedUrl(e.target.value)}
                className="stratia-input"
              />
              <div className="modal-actions">
                <button className="stratia-btn-outlined" onClick={() => setSelectedSource(null)}>Cancel</button>
                <button className="stratia-btn-filled" onClick={() => updateSource(selectedSource)}>Save</button>
              </div>
            </div>
          </div>
        )}

        {/* Validation Results Modal */}
        {validationResult && (
          <div className="modal-overlay" onClick={() => setValidationResult(null)}>
            <div className="modal-content data-modal" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h3 className="headline-small">✅ API Data Retrieved</h3>
                <button className="modal-close" onClick={() => setValidationResult(null)}>×</button>
              </div>

              <div className="api-badge">{validationResult.apiType === 'college_scorecard' ? '📊 College Scorecard' : '🏛️ Urban IPEDS'}</div>
              <p className="source-url-small">{validationResult.url}</p>

              <div className="data-grid">
                {validationResult.apiType === 'college_scorecard' && validationResult.sampleData && (
                  <>
                    <div className="data-item">
                      <span className="data-label">School</span>
                      <span className="data-value">{validationResult.sampleData.school_name}</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Location</span>
                      <span className="data-value">{validationResult.sampleData.location}</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Admission Rate</span>
                      <span className="data-value highlight">
                        {validationResult.sampleData.admission_rate
                          ? `${(validationResult.sampleData.admission_rate * 100).toFixed(1)}%`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">In-State Tuition</span>
                      <span className="data-value">
                        {validationResult.sampleData.tuition_in_state
                          ? `$${validationResult.sampleData.tuition_in_state.toLocaleString()}`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Out-of-State Tuition</span>
                      <span className="data-value">
                        {validationResult.sampleData.tuition_out_of_state
                          ? `$${validationResult.sampleData.tuition_out_of_state.toLocaleString()}`
                          : 'N/A'}
                      </span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Student Size</span>
                      <span className="data-value">
                        {validationResult.sampleData.student_size?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                  </>
                )}

                {validationResult.apiType === 'urban_ipeds' && validationResult.sampleData && (
                  <>
                    <div className="data-item">
                      <span className="data-label">Year</span>
                      <span className="data-value">{validationResult.sampleData.year}</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Total Applicants</span>
                      <span className="data-value">
                        {validationResult.sampleData.applicants_total?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Total Admitted</span>
                      <span className="data-value">
                        {validationResult.sampleData.admissions_total?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Total Enrolled</span>
                      <span className="data-value">
                        {validationResult.sampleData.enrolled_total?.toLocaleString() || 'N/A'}
                      </span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Admission Rate</span>
                      <span className="data-value highlight">
                        {validationResult.sampleData.admit_rate
                          ? `${validationResult.sampleData.admit_rate}%`
                          : 'N/A'}
                      </span>
                    </div>
                  </>
                )}

                {/* Web Page Preview */}
                {validationResult.apiType === 'web' && validationResult.sampleData && (
                  <>
                    {validationResult.sampleData.title && (
                      <div className="data-item full-width">
                        <span className="data-label">Page Title</span>
                        <span className="data-value">{validationResult.sampleData.title}</span>
                      </div>
                    )}
                    {validationResult.sampleData.description && (
                      <div className="data-item full-width">
                        <span className="data-label">Description</span>
                        <span className="data-value small">{validationResult.sampleData.description}</span>
                      </div>
                    )}
                    {validationResult.sampleData.headings?.length > 0 && (
                      <div className="data-item full-width">
                        <span className="data-label">Content Headings</span>
                        <div className="headings-list">
                          {validationResult.sampleData.headings.map((h, i) => (
                            <span key={i} className="heading-tag">{h}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="data-item">
                      <span className="data-label">Links Found</span>
                      <span className="data-value">{validationResult.sampleData.link_count || 0}</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Data Tables</span>
                      <span className="data-value highlight">{validationResult.sampleData.table_count || 0}</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">Content Size</span>
                      <span className="data-value">{Math.round((validationResult.sampleData.content_length || 0) / 1024)} KB</span>
                    </div>
                  </>
                )}

                {/* PDF Preview */}
                {validationResult.apiType === 'pdf' && validationResult.sampleData && (
                  <>
                    <div className="data-item">
                      <span className="data-label">File Type</span>
                      <span className="data-value">📄 PDF Document</span>
                    </div>
                    <div className="data-item">
                      <span className="data-label">File Size</span>
                      <span className="data-value highlight">{Math.round((validationResult.sampleData.file_size || 0) / 1024)} KB</span>
                    </div>
                  </>
                )}
              </div>

              <div className="modal-actions">
                <button className="stratia-btn-filled" onClick={() => setValidationResult(null)}>Done</button>
              </div>
            </div>
          </div>
        )}

        {/* API Key Configuration Modal */}
        {apiKeyModal && (
          <div className="modal-overlay" onClick={() => { setApiKeyModal(null); setApiKeyInput('') }}>
            <div className="modal-content api-key-modal" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h3 className="headline-small">🔑 API Key Required</h3>
                <button className="modal-close" onClick={() => { setApiKeyModal(null); setApiKeyInput('') }}>×</button>
              </div>

              <div className="api-key-info">
                <h4>{apiKeyModal.keyConfig?.name || 'API Key'}</h4>
                <p className="api-key-desc">{apiKeyModal.keyConfig?.description}</p>

                <div className="api-key-steps">
                  <div className="step-item">
                    <span className="step-num">1</span>
                    <span>Get a free API key from:</span>
                  </div>
                  <a
                    href={apiKeyModal.keyConfig?.signup_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="signup-link"
                  >
                    {apiKeyModal.keyConfig?.signup_url} →
                  </a>

                  <div className="step-item">
                    <span className="step-num">2</span>
                    <span>Paste your API key and test it:</span>
                  </div>
                </div>

                <div className="api-key-input-row">
                  <input
                    type="text"
                    value={apiKeyInput}
                    onChange={e => { setApiKeyInput(e.target.value); setTestResult(null) }}
                    placeholder="Enter your API key..."
                    className="stratia-input api-key-input"
                    autoFocus
                  />
                  <button
                    className="stratia-btn-tonal"
                    onClick={testApiKey}
                    disabled={!apiKeyInput.trim() || savingKey}
                  >
                    {savingKey && !testResult ? <span className="loading-spinner small" /> : '🔍'} Test
                  </button>
                </div>

                {/* Test Results Preview */}
                {testResult && testResult.sample_data && (
                  <div className="test-results">
                    <div className="test-success-header">
                      <span>✅ {testResult.message}</span>
                      <span className="test-total">{testResult.total_available?.toLocaleString()} schools available</span>
                    </div>
                    <div className="sample-schools">
                      {testResult.sample_data.map((school, i) => (
                        <div key={i} className="sample-school">
                          <span className="school-name">{school.name}</span>
                          <span className="school-info">
                            {school.location} •
                            {school.admission_rate ? ` ${(school.admission_rate * 100).toFixed(0)}% admit` : ''} •
                            {school.tuition_in_state ? ` $${school.tuition_in_state.toLocaleString()}` : ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {apiKeyModal.keyConfig?.docs_url && (
                  <p className="docs-link">
                    📚 <a href={apiKeyModal.keyConfig.docs_url} target="_blank" rel="noopener noreferrer">
                      View API Documentation
                    </a>
                  </p>
                )}
              </div>

              <div className="modal-actions">
                <button className="stratia-btn-outlined" onClick={() => { setApiKeyModal(null); setApiKeyInput(''); setTestResult(null) }}>
                  Cancel
                </button>
                <button
                  className="stratia-btn-filled"
                  onClick={saveApiKey}
                  disabled={!testResult?.success || savingKey}
                >
                  {savingKey ? <><span className="loading-spinner small" /> Saving...</> : '✓ Save Key'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Toast Notification */}
        {toast && (
          <div className={`toast toast-${toast.type}`}>
            <span className="toast-message">{toast.message}</span>
            <button className="toast-close" onClick={() => setToast(null)}>×</button>
          </div>
        )}
      </div>
    )
  }

  // Finalize Page
  if (page === 'finalize' && sources?.sources) {
    return (
      <div className="min-h-screen app-page">
        <div className="stratia-bg-blobs">
          <div className="stratia-blob stratia-blob-1" />
          <div className="stratia-blob stratia-blob-2" />
        </div>

        <nav className="glass-nav">
          <div className="container">
            <div className="nav-inner">
              <div className="logo" onClick={() => setPage('home')} style={{ cursor: 'pointer' }}>
                <div className="logo-icon">🔍</div>
                <span className="logo-text">Source Curator</span>
              </div>
              <div className="nav-tabs">
                <button className="nav-tab" onClick={() => setPage('review')}>📝 Review</button>
                <button className="nav-tab active">✓ Finalize</button>
              </div>
            </div>
          </div>
        </nav>

        <main className="app-main">
          <div className="container narrow">
            <div className="finalize-card">
              <h2 className="headline-medium">Finalize Sources</h2>
              <p className="body-medium">Select which sources to activate for <strong>{sources.official_name}</strong></p>

              <div className="source-checklist">
                {Object.entries(sources.sources || {}).map(([key, source]) => {
                  const s = source.primary || source
                  return (
                    <label key={key} className="checklist-item">
                      <input type="checkbox" defaultChecked={s.is_active || s.tier === 1} />
                      <div className="checklist-content">
                        <span className="checklist-name">{s.name || key}</span>
                        <span className="checklist-tier">Tier {s.tier}</span>
                      </div>
                    </label>
                  )
                })}
              </div>

              <div className="finalize-actions">
                <button className="stratia-btn-outlined" onClick={() => setPage('review')}>
                  ← Back to Review
                </button>
                <button
                  className="stratia-btn-filled"
                  onClick={() => {
                    const checkboxes = document.querySelectorAll('.checklist-item input[type="checkbox"]')
                    const active = Array.from(checkboxes)
                      .filter(cb => cb.checked)
                      .map((cb, i) => Object.keys(sources.sources)[i])
                    finalizeSources(active)
                  }}
                >
                  ✓ Save & Export YAML
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* Toast Notification */}
        {toast && (
          <div className={`toast toast-${toast.type}`}>
            <span className="toast-message">{toast.message}</span>
            <button className="toast-close" onClick={() => setToast(null)}>×</button>
          </div>
        )}
      </div>
    )
  }

  return null
}

// Toast Component
function Toast({ toast, onClose }) {
  if (!toast) return null

  return (
    <div className={`toast ${toast.type}`}>
      <span className="toast-message">{toast.message}</span>
      <button className="toast-close" onClick={onClose}>×</button>
    </div>
  )
}

// Wrap App with Toast
function AppWithToast() {
  return <App />
}

export default App
