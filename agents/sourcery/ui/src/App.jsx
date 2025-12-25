import { useState, useRef } from 'react'
import './index.css'

// Agent URL - Data Discovery Agent deployed via ADK
const AGENT_URL = import.meta.env.VITE_AGENT_URL || 'http://localhost:8000'
const APP_NAME = 'sourcery' // Agent app name

// Helper: Parse agent result that may be wrapped in markdown code blocks
const parseAgentResult = (result) => {
  // If result has a 'result' field with markdown-wrapped JSON
  if (result.result && typeof result.result === 'string') {
    let jsonStr = result.result
    // Remove markdown code blocks
    const codeBlockMatch = jsonStr.match(/```(?:json)?\s*([\s\S]*?)```/)
    if (codeBlockMatch) {
      jsonStr = codeBlockMatch[1]
    }
    try {
      return JSON.parse(jsonStr.trim())
    } catch (e) {
      console.error('[Sourcery] Failed to parse result JSON:', e)
      return result
    }
  }
  return result
}

function App() {
  const [page, setPage] = useState('landing')
  const [goal, setGoal] = useState('')
  const [schemaMode, setSchemaMode] = useState(null) // 'discover' or 'provide'
  const [userSchema, setUserSchema] = useState('') // For user-provided schema
  const [analysis, setAnalysis] = useState(null)
  const [selectedCategories, setSelectedCategories] = useState([])
  const [schema, setSchema] = useState(null)
  const [configId, setConfigId] = useState(null)
  const [sources, setSources] = useState([])
  // Phase 2-3: Sample sources and structure patterns
  const [entityType, setEntityType] = useState('')
  const [samples, setSamples] = useState([])
  const [patterns, setPatterns] = useState(null)
  const [entities, setEntities] = useState([])
  const [selectedEntities, setSelectedEntities] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Session management for ADK protocol
  const sessionIdRef = useRef(null)

  // Helper: Send message to ADK agent
  const sendToAgent = async (userMessage) => {
    try {
      // Create session if not exists
      if (!sessionIdRef.current) {
        console.log('[Sourcery] Creating new session...')
        const sessionRes = await fetch(`${AGENT_URL}/apps/${APP_NAME}/users/user/sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{"user_input":"Hello"}'
        })
        const sessionData = await sessionRes.json()
        sessionIdRef.current = sessionData.id
        console.log('[Sourcery] Session created:', sessionIdRef.current)
      }

      // Send message to agent via /run endpoint
      console.log('[Sourcery] Sending message:', userMessage.substring(0, 100) + '...')

      const escapedMessage = userMessage
        .replace(/\\/g, '\\\\')
        .replace(/"/g, '\\"')
        .replace(/\n/g, '\\n')
        .replace(/\r/g, '\\r')
        .replace(/\t/g, '\\t')

      const requestBody = `{"app_name":"${APP_NAME}","user_id":"user","session_id":"${sessionIdRef.current}","new_message":{"parts":[{"text":"${escapedMessage}"}]}}`

      const runRes = await fetch(`${AGENT_URL}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: requestBody
      })

      const response = await runRes.json()
      console.log('[Sourcery] Response:', response)

      // Extract data from response events
      const events = Array.isArray(response) ? response : (response.events || [])

      // Look for functionResponse in the last event (tool response)
      for (let i = events.length - 1; i >= 0; i--) {
        const event = events[i]
        if (event?.content?.parts) {
          for (const part of event.content.parts) {
            // Check for functionResponse (tool output)
            if (part.functionResponse?.response) {
              console.log('[Sourcery] Found functionResponse:', part.functionResponse.response)
              return part.functionResponse.response
            }
            // Check for text part
            if (part.text) {
              try {
                return JSON.parse(part.text)
              } catch {
                return { result: part.text }
              }
            }
          }
        }
      }

      return { error: 'No response from agent' }
    } catch (err) {
      console.error('[Sourcery] Agent error:', err)
      throw err
    }
  }

  // Analyze goal - calls SchemaDiscoveryAgent
  const handleAnalyzeGoal = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await sendToAgent(`Discover schema for: ${goal}`)
      console.log('[Sourcery] Schema discovery result:', result)

      // Extract schema from result - agent returns schema_json as string
      const schemaResult = result.schema_generation_result || result

      // Parse schema_json if it's a string (may be double-escaped)
      let parsedSchema = schemaResult.schema || schemaResult.schema_json
      if (typeof parsedSchema === 'string') {
        try {
          // First attempt: direct parse
          parsedSchema = JSON.parse(parsedSchema)
        } catch (e) {
          console.log('[Sourcery] First parse failed, trying to unescape...')
          try {
            // Second attempt: it might be double-escaped, unescape first
            const unescaped = parsedSchema
              .replace(/\\\\"/g, '"')
              .replace(/\\"/g, '"')
              .replace(/\\\\/g, '\\')
            parsedSchema = JSON.parse(unescaped)
          } catch (e2) {
            console.error('[Sourcery] Failed to parse schema_json:', e2)
            // Keep as-is if parsing fails
          }
        }
      }

      // Handle categories - could be array of strings or array of objects
      let categories = schemaResult.categories || []
      if (categories.length > 0 && typeof categories[0] === 'string') {
        // Convert string array to object array for UI
        categories = categories.map(name => ({
          name: name,
          description: name,
          priority: 'high',
          fields: []
        }))
      }

      if (parsedSchema || categories.length > 0) {
        setAnalysis({
          entity_type: schemaResult.entity_type || 'entity',
          entity_type_plural: schemaResult.entity_type_plural || 'entities',
          categories: categories,
          schema: parsedSchema
        })
        setSelectedCategories(categories.map(c => c.name))
        setEntityType(schemaResult.entity_type || 'entity')
        setSchema(parsedSchema)
        setConfigId(`config_${Date.now()}`)
        // Go directly to schema review if we have a schema
        setPage(parsedSchema ? 'schema' : 'categories')
      } else {
        setError('Failed to generate schema from goal')
      }
    } catch (e) {
      setError(e.message || 'Failed to analyze goal')
    }
    setLoading(false)
  }

  // Generate schema (uses analysis already obtained)
  const handleGenerateSchema = async () => {
    setLoading(true)
    setError(null)
    try {
      // Re-run with selected categories to get refined schema
      const selectedCats = analysis.categories.filter(c => selectedCategories.includes(c.name))
      const result = await sendToAgent(`Generate JSON schema for goal: ${goal}\n\nSelected categories:\n${JSON.stringify(selectedCats, null, 2)}`)

      const schemaResult = result.schema_generation_result || result
      if (schemaResult.schema) {
        setSchema(schemaResult.schema)
        setConfigId(`config_${Date.now()}`)
        setPage('schema')
      } else {
        // Use the original analysis schema
        setSchema(analysis.schema || schemaResult)
        setConfigId(`config_${Date.now()}`)
        setPage('schema')
      }
    } catch (e) {
      setError(e.message || 'Failed to generate schema')
    }
    setLoading(false)
  }

  // Discover sample entities - calls SampleDiscoveryAgent
  const handleDiscoverSamples = async () => {
    setLoading(true)
    setError(null)
    try {
      const schemaStr = JSON.stringify(schema, null, 2)
      const result = await sendToAgent(`Find samples for: ${goal}\n\nWith schema:\n${schemaStr}`)

      console.log('[Sourcery] Sample discovery result:', result)
      const samplesResult = result.sample_discovery_result || result

      if (samplesResult.samples) {
        setSamples(samplesResult.samples)
        setEntityType(samplesResult.entity_type || entityType)
        setPage('samples')
      } else {
        setError('Failed to discover sample entities')
      }
    } catch (e) {
      setError(e.message || 'Failed to discover samples')
    }
    setLoading(false)
  }

  // Derive structure patterns - calls StructureDiscoveryAgent
  const handleDeriveStructure = async () => {
    setLoading(true)
    setError(null)
    try {
      const samplesStr = JSON.stringify(samples, null, 2)
      const result = await sendToAgent(`Derive patterns from samples: ${samplesStr}\n\nEntity type: ${entityType}\nGoal: ${goal}`)

      console.log('[Sourcery] Structure discovery result:', result)
      const patternsResult = result.structure_discovery_result || result

      if (patternsResult.source_patterns) {
        setPatterns(patternsResult.source_patterns)
        setPage('patterns')
      } else {
        setError('Failed to derive structure patterns')
      }
    } catch (e) {
      setError(e.message || 'Failed to derive structure')
    }
    setLoading(false)
  }

  // Discover full entity list - calls EntityDiscoveryAgent
  const handleDiscoverEntities = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await sendToAgent(`Discover entities for: ${goal}\n\nOf type: ${entityType}`)

      console.log('[Sourcery] Entity discovery result:', result)
      const entityResult = result.entity_discovery_result || result

      if (entityResult.categories) {
        setEntities(entityResult.categories)
        // Pre-select all high priority entities
        const preSelected = entityResult.categories.flatMap(cat =>
          cat.entities.filter(e => e.priority === 'high').map(e => e.slug)
        )
        setSelectedEntities(preSelected)
        setPage('entities')
      } else {
        setError('Failed to discover entities')
      }
    } catch (e) {
      setError(e.message || 'Failed to discover entities')
    }
    setLoading(false)
  }

  // Discover sources (simplified - uses samples)
  const handleDiscoverSources = async () => {
    setLoading(true)
    setError(null)
    try {
      // Use the patterns from samples as sources
      if (patterns) {
        const allSources = [
          ...(patterns.universal || []),
          ...(patterns.parametric || [])
        ]
        setSources(allSources)
        setPage('sources')
      } else {
        setError('No source patterns available')
      }
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  // Save config (local for now)
  const handleSaveConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      // Save config to localStorage for now
      const config = {
        id: configId,
        goal,
        schema,
        entity_type: entityType,
        source_patterns: patterns,
        entities: selectedEntities,
        created_at: new Date().toISOString()
      }
      localStorage.setItem(`sourcery_config_${configId}`, JSON.stringify(config))
      console.log('[Sourcery] Config saved:', config)
      setPage('complete')
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  // Toggle category selection
  const toggleCategory = (name) => {
    setSelectedCategories(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    )
  }

  // Toggle entity selection
  const toggleEntity = (slug) => {
    setSelectedEntities(prev =>
      prev.includes(slug) ? prev.filter(s => s !== slug) : [...prev, slug]
    )
  }

  // Landing Page
  if (page === 'landing') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
          <div className="dm-blob dm-blob-3" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo">
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
            <div className="dm-nav-actions">
              <button className="dm-btn dm-btn-ghost">Documentation</button>
              <button className="dm-btn dm-btn-primary" onClick={() => setPage('goal')}>
                Get Started →
              </button>
            </div>
          </div>
        </nav>

        <section className="dm-hero">
          <div className="dm-hero-content">
            <div className="dm-badge">🔮 AI-Powered Data Discovery</div>
            <h1 className="dm-hero-title">Data <span>Sorcery</span></h1>
            <p className="dm-hero-subtitle">
              Describe what you need. AI finds the sources. You get structured, verified data.
              Turn any research goal into a comprehensive data collection pipeline.
            </p>
            <div className="dm-hero-actions">
              <button className="dm-btn dm-btn-primary dm-btn-large" onClick={() => setPage('goal')}>
                🔮 Start Discovering Data
              </button>
              <button className="dm-btn dm-btn-secondary dm-btn-large">📺 Watch Demo</button>
            </div>
          </div>
        </section>


        <section className="dm-pipeline">
          <div className="dm-pipeline-header">
            <p className="dm-section-label">How It Works</p>
            <h2 className="dm-section-title">From Goal to Gold in 6 Steps</h2>
            <p className="dm-section-subtitle">Our AI-powered pipeline transforms your research goals into curated, verified data</p>
          </div>
          <div className="dm-pipeline-steps">
            {[
              { icon: '🎯', title: 'Define Goal', desc: 'Describe your data needs' },
              { icon: '📋', title: 'Build Schema', desc: 'AI generates structure' },
              { icon: '🔍', title: 'Find Sources', desc: 'Discover APIs & data' },
              { icon: '✓', title: 'Validate', desc: 'Human verification' },
              { icon: '⚡', title: 'Extract', desc: 'Pull verified data' },
              { icon: '📊', title: 'Export', desc: 'JSON to cloud' }
            ].map((step, i) => (
              <div className="dm-step" key={i}>
                <div className="dm-step-icon">{step.icon}</div>
                <h3 className="dm-step-title">{step.title}</h3>
                <p className="dm-step-desc">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="dm-features">
          <div className="dm-pipeline-header">
            <p className="dm-section-label">Why Sourcery</p>
            <h2 className="dm-section-title">Data Curation, Reimagined</h2>
          </div>
          <div className="dm-features-grid">
            {[
              { icon: '🧠', title: 'Goal-Driven Schema', desc: 'Describe your research goal in plain English. Our AI generates the perfect data schema for your needs.' },
              { icon: '🌐', title: 'Multi-Source Discovery', desc: 'Automatically discover APIs, PDFs, and websites that contain the data you need.' },
              { icon: '👤', title: 'Human-in-the-Loop', desc: 'Every source is validated by you. Preview data before extraction. Full control over quality.' },
              { icon: '☁️', title: 'Cloud Persistence', desc: 'Schemas, sources, and extracted data are saved to Google Cloud Storage.' },
              { icon: '🔌', title: 'Database Connectors', desc: 'Export curated data to any database. Coming soon: Elasticsearch, PostgreSQL.' },
              { icon: '🔄', title: 'Reusable Configs', desc: 'Save your data mining configs as YAML. Rerun extraction on new entities anytime.' }
            ].map((f, i) => (
              <div className="dm-feature-card" key={i}>
                <div className="dm-feature-icon">{f.icon}</div>
                <h3 className="dm-feature-title">{f.title}</h3>
                <p className="dm-feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="dm-cta">
          <div className="dm-cta-card">
            <h2 className="dm-cta-title">Ready to Mine Your Data?</h2>
            <p className="dm-cta-subtitle">Start with a goal. End with structured, verified data in minutes.</p>
            <button className="dm-btn dm-btn-primary dm-btn-large" onClick={() => setPage('goal')}>🚀 Start Free</button>
          </div>
        </section>

        <footer className="dm-footer">
          <p>© 2024 Sourcery. Built with 🔮 for data explorers.</p>
        </footer>
      </div >
    )
  }

  // Step indicator component - matches agent-driven workflow
  const StepIndicator = ({ current }) => (
    <div className="dm-steps-indicator">
      {['Goal', 'Schema', 'Samples', 'Patterns', 'Entities', 'Sources', 'Done'].map((step, i) => (
        <div key={i} className={`dm-step-dot ${i + 1 <= current ? 'active' : ''} ${i + 1 === current ? 'current' : ''}`}>
          <span className="dm-step-num">{i + 1}</span>
          <span className="dm-step-label">{step}</span>
        </div>
      ))}
    </div>
  )

  // Goal Input Page
  if (page === 'goal') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content">
            <StepIndicator current={1} />
            <h1 className="dm-wizard-title">What data do you need?</h1>
            <p className="dm-wizard-subtitle">Describe your research goal in plain English. Be specific about what information you want to collect.</p>

            <div className="dm-goal-input-wrapper">
              <textarea
                className="dm-goal-input"
                placeholder="Example: I want to collect data about US universities including admissions statistics, tuition costs, student demographics, available majors, and campus life information."
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                rows={6}
              />
            </div>

            <div className="dm-examples">
              <p className="dm-examples-label">Try an example:</p>
              <div className="dm-example-chips">
                <button className="dm-chip" onClick={() => setGoal("Collect comprehensive data about US universities including admissions rates, tuition, student demographics, available programs, and campus culture to evaluate student-university fit.")}>
                  🎓 University Research
                </button>
                <button className="dm-chip" onClick={() => setGoal("Gather data about tech companies including employee count, funding rounds, product offerings, and company culture to evaluate potential employers.")}>
                  🏢 Company Research
                </button>
                <button className="dm-chip" onClick={() => setGoal("Collect real estate data including property prices, neighborhood statistics, school ratings, and amenities to find the best areas to live.")}>
                  🏠 Real Estate Data
                </button>
              </div>
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('landing')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={!goal.trim()} onClick={() => setPage('schema-choice')}>
                Continue →
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Schema Choice Page
  if (page === 'schema-choice') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content">
            <StepIndicator current={2} />
            <h1 className="dm-wizard-title">How would you like to define your schema?</h1>
            <p className="dm-wizard-subtitle">Choose whether to provide your own schema or let AI discover one based on your goal.</p>

            <div className="dm-choice-grid">
              <div
                className={`dm-choice-card ${schemaMode === 'discover' ? 'selected' : ''}`}
                onClick={() => setSchemaMode('discover')}
              >
                <div className="dm-choice-icon">🔍</div>
                <h3 className="dm-choice-title">AI Discovery</h3>
                <p className="dm-choice-desc">
                  Let our AI research what data is available and suggest a comprehensive schema based on your goal.
                </p>
                <ul className="dm-choice-pros">
                  <li>✓ Discovers fields you might not know about</li>
                  <li>✓ Based on available data sources</li>
                  <li>✓ Best for exploratory research</li>
                </ul>
              </div>

              <div
                className={`dm-choice-card ${schemaMode === 'provide' ? 'selected' : ''}`}
                onClick={() => setSchemaMode('provide')}
              >
                <div className="dm-choice-icon">📋</div>
                <h3 className="dm-choice-title">Provide Schema</h3>
                <p className="dm-choice-desc">
                  Upload or paste your own JSON Schema if you already know exactly what fields you need.
                </p>
                <ul className="dm-choice-pros">
                  <li>✓ Full control over data structure</li>
                  <li>✓ Faster if you know what you need</li>
                  <li>✓ Use existing schema definitions</li>
                </ul>
              </div>
            </div>

            {schemaMode === 'provide' && (
              <div className="dm-schema-input-wrapper">
                <label className="dm-input-label">Paste your JSON Schema:</label>
                <textarea
                  className="dm-schema-input"
                  placeholder='{"type": "object", "properties": {...}}'
                  value={userSchema}
                  onChange={(e) => setUserSchema(e.target.value)}
                  rows={10}
                />
              </div>
            )}

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('goal')}>← Back</button>
              <button
                className="dm-btn dm-btn-primary dm-btn-large"
                disabled={!schemaMode || (schemaMode === 'provide' && !userSchema.trim()) || loading}
                onClick={async () => {
                  if (schemaMode === 'discover') {
                    await handleAnalyzeGoal()
                  } else {
                    // Parse and use user-provided schema
                    try {
                      const parsed = JSON.parse(userSchema)
                      setSchema(parsed)
                      setConfigId(`dm_${Date.now()}`)
                      setPage('schema')
                    } catch (e) {
                      setError('Invalid JSON Schema. Please check your syntax.')
                    }
                  }
                }}
              >
                {loading ? '🔄 Processing...' : schemaMode === 'discover' ? 'Discover Schema →' : 'Use My Schema →'}
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Categories Selection Page
  if (page === 'categories') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content">
            <StepIndicator current={2} />
            <h1 className="dm-wizard-title">Select Data Categories</h1>
            <p className="dm-wizard-subtitle">{analysis?.summary || 'Choose which categories of data you want to collect.'}</p>

            <div className="dm-categories-grid">
              {analysis?.categories?.map((cat, i) => (
                <div
                  key={i}
                  className={`dm-category-card ${selectedCategories.includes(cat.name) ? 'selected' : ''}`}
                  onClick={() => toggleCategory(cat.name)}
                >
                  <div className="dm-category-header">
                    <span className="dm-category-checkbox">{selectedCategories.includes(cat.name) ? '✓' : ''}</span>
                    <h3 className="dm-category-name">{cat.name}</h3>
                    <span className={`dm-priority-badge ${cat.priority}`}>{cat.priority}</span>
                  </div>
                  <p className="dm-category-desc">{cat.description}</p>
                  <div className="dm-category-fields">
                    {cat.fields?.map((field, j) => (
                      <span key={j} className="dm-field-tag">{field}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('goal')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={selectedCategories.length === 0 || loading} onClick={handleGenerateSchema}>
                {loading ? '🔄 Generating...' : `Generate Schema (${selectedCategories.length}) →`}
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Schema Review Page
  if (page === 'schema') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content dm-wide">
            <StepIndicator current={2} />
            <h1 className="dm-wizard-title">Review Your Schema</h1>
            <p className="dm-wizard-subtitle">This JSON Schema defines the structure of data we'll collect. Next, we'll find sample sources.</p>

            <div className="dm-schema-container">
              <pre className="dm-schema-preview">{JSON.stringify(schema, null, 2)}</pre>
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('schema-choice')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={loading} onClick={handleDiscoverSamples}>
                {loading ? '🔄 Finding Samples...' : 'Discover Samples →'}
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Samples Review Page - Show 5 sample entities with their sources
  if (page === 'samples') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content dm-wide">
            <StepIndicator current={3} />
            <h1 className="dm-wizard-title">Sample {entityType} Sources</h1>
            <p className="dm-wizard-subtitle">
              We found sources for 5 sample {entityType}s. Review these to help derive source patterns.
            </p>

            <div className="dm-samples-grid">
              {samples.map((sample, i) => (
                <div key={i} className="dm-sample-card">
                  <h3 className="dm-sample-name">{sample.name}</h3>
                  <div className="dm-sample-sources">
                    {sample.sources?.map((src, j) => (
                      <div key={j} className="dm-sample-source">
                        <span className={`dm-source-type ${src.type?.toLowerCase()}`}>{src.type}</span>
                        <span className="dm-source-name-small">{src.name}</span>
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="dm-source-url-small">
                          {src.url?.substring(0, 40)}...
                        </a>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('schema')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={loading} onClick={handleDeriveStructure}>
                {loading ? '🔄 Analyzing Patterns...' : 'Derive Structure →'}
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Patterns Review Page - Show derived YAML structure
  if (page === 'patterns') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content dm-wide">
            <StepIndicator current={4} />
            <h1 className="dm-wizard-title">Source Patterns</h1>
            <p className="dm-wizard-subtitle">
              We derived these source patterns from the samples. This structure will be used for all {entityType}s.
            </p>

            <div className="dm-patterns-container">
              {patterns?.universal?.length > 0 && (
                <div className="dm-pattern-section">
                  <h3 className="dm-pattern-type">🌍 Universal Sources</h3>
                  <p className="dm-pattern-desc">Same for all {entityType}s</p>
                  {patterns.universal.map((p, i) => (
                    <div key={i} className="dm-pattern-card">
                      <span className={`dm-source-type ${p.type?.toLowerCase()}`}>{p.type}</span>
                      <strong>{p.name}</strong>
                      <code>{p.base_url}</code>
                    </div>
                  ))}
                </div>
              )}

              {patterns?.parametric?.length > 0 && (
                <div className="dm-pattern-section">
                  <h3 className="dm-pattern-type">🔧 Parametric Sources</h3>
                  <p className="dm-pattern-desc">URL pattern with entity-specific parts</p>
                  {patterns.parametric.map((p, i) => (
                    <div key={i} className="dm-pattern-card">
                      <span className={`dm-source-type ${p.type?.toLowerCase()}`}>{p.type}</span>
                      <strong>{p.name}</strong>
                      <code>{p.url_pattern}</code>
                    </div>
                  ))}
                </div>
              )}

              {patterns?.entity_specific_discovery && (
                <div className="dm-pattern-section">
                  <h3 className="dm-pattern-type">🔍 Entity-Specific</h3>
                  <p className="dm-pattern-desc">Discovered per {entityType}</p>
                  <div className="dm-pattern-card">
                    <strong>Discovery Queries:</strong>
                    <ul>
                      {patterns.entity_specific_discovery.queries?.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('samples')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={loading} onClick={handleDiscoverEntities}>
                {loading ? '🔄 Finding Entities...' : 'Discover Entities →'}
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Entity Selection Page
  if (page === 'entities') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content dm-wide">
            <StepIndicator current={5} />
            <h1 className="dm-wizard-title">Select {entityType}s to Mine</h1>
            <p className="dm-wizard-subtitle">
              Choose which {entityType}s to collect data for. {selectedEntities.length} selected.
            </p>

            <div className="dm-entities-container">
              {entities.map((category, i) => (
                <div key={i} className="dm-entity-category">
                  <h3 className="dm-entity-category-name">{category.name}</h3>
                  <p className="dm-entity-category-desc">{category.description}</p>
                  <div className="dm-entity-list">
                    {category.entities?.map((entity, j) => (
                      <div
                        key={j}
                        className={`dm-entity-chip ${selectedEntities.includes(entity.slug) ? 'selected' : ''}`}
                        onClick={() => toggleEntity(entity.slug)}
                      >
                        <span className="dm-entity-check">{selectedEntities.includes(entity.slug) ? '✓' : ''}</span>
                        {entity.name}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('patterns')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={selectedEntities.length === 0 || loading} onClick={handleSaveConfig}>
                {loading ? '🔄 Saving...' : `Save Config (${selectedEntities.length} ${entityType}s) →`}
              </button>
            </div>
          </div>
        </section>
      </div>
    )
  }

  // Sources Review Page
  if (page === 'sources') {
    return (
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content dm-wide">
            <StepIndicator current={4} />
            <h1 className="dm-wizard-title">Review Data Sources</h1>
            <p className="dm-wizard-subtitle">We found these sources that can fill your schema. Review and approve them.</p>

            <div className="dm-sources-grid">
              {sources.map((source, i) => (
                <div key={i} className="dm-source-card">
                  <div className="dm-source-header">
                    <span className={`dm-source-type ${source.type?.toLowerCase()}`}>{source.type}</span>
                    <span className={`dm-reliability ${source.reliability}`}>{source.reliability}</span>
                  </div>
                  <h3 className="dm-source-name">{source.name}</h3>
                  <p className="dm-source-desc">{source.description}</p>
                  <a href={source.url} target="_blank" rel="noopener noreferrer" className="dm-source-url">{source.url}</a>
                  <div className="dm-source-fields">
                    <strong>Covers:</strong> {source.fields_covered?.join(', ')}
                  </div>
                  {source.api_key_required && <div className="dm-api-badge">🔑 API Key Required</div>}
                </div>
              ))}
            </div>

            {error && <div className="dm-error">{error}</div>}

            <div className="dm-wizard-actions">
              <button className="dm-btn dm-btn-ghost" onClick={() => setPage('schema')}>← Back</button>
              <button className="dm-btn dm-btn-primary dm-btn-large" disabled={loading} onClick={handleSaveConfig}>
                {loading ? '🔄 Saving...' : '💾 Save Config →'}
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
      <div className="dm-app">
        <div className="dm-bg">
          <div className="dm-blob dm-blob-1" />
          <div className="dm-blob dm-blob-2" />
        </div>

        <nav className="dm-nav">
          <div className="dm-nav-inner">
            <div className="dm-logo" onClick={() => setPage('landing')}>
              <div className="dm-logo-icon">🔮</div>
              <span className="dm-logo-text">Sourcery</span>
            </div>
          </div>
        </nav>

        <section className="dm-wizard">
          <div className="dm-wizard-content">
            <div className="dm-complete-icon">🎉</div>
            <h1 className="dm-wizard-title">Config Saved!</h1>
            <p className="dm-wizard-subtitle">Your data mining config has been saved. You can now use it to extract data.</p>

            <div className="dm-config-info">
              <div className="dm-config-id">Config ID: <strong>{configId}</strong></div>
            </div>

            <div className="dm-wizard-actions" style={{ justifyContent: 'center' }}>
              <button className="dm-btn dm-btn-secondary dm-btn-large" onClick={() => {
                setPage('landing')
                setGoal('')
                setAnalysis(null)
                setSchema(null)
                setSources([])
              }}>
                🎯 Start New Mining
              </button>
              <button className="dm-btn dm-btn-primary dm-btn-large">
                ⚡ Extract Data Now
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
