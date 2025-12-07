# College Expert Hybrid Agent

A specialized college admissions counseling agent that uses **hybrid search** (BM25 + vector) on structured university profiles.

## Features

- **Hybrid Search**: Combines keyword matching with semantic understanding for best search quality
- **Structured Data**: Access to comprehensive university profiles with admissions data, academic programs, career outcomes
- **Personalized Analysis**: Can analyze student profiles against university requirements
- **Multiple Search Modes**: Hybrid (default), semantic, and keyword search options

## Architecture

```
college_expert_hybrid/
├── agent.py                 # Main agent with MasterReasoningAgent
├── __init__.py
├── requirements.txt
├── .env
├── tools/
│   ├── tools.py            # API tools for cloud functions
│   ├── logging_utils.py    # Logging callbacks
│   └── __init__.py
└── sub_agents/
    ├── university_knowledge_analyst/
    │   ├── agent.py        # Sub-agent for university search
    │   └── __init__.py
    └── student_profile_agent/
        ├── agent.py        # Sub-agent for profile retrieval
        └── __init__.py
```

## Tools

### search_universities(query, search_type, filters, limit)
Search university profiles using hybrid search.

**Parameters:**
- `query`: Natural language query
- `search_type`: "hybrid" (default), "semantic", or "keyword"
- `filters`: Optional dict with state, type, acceptance_rate_max, etc.
- `limit`: Max results (default 10)

**Example:**
```python
search_universities(
    query="computer science research California",
    search_type="hybrid",
    filters={"state": "CA", "acceptance_rate_max": 30}
)
```

### get_university(university_id)
Get a specific university profile by ID.

### list_universities()
List all available universities in the knowledge base.

### search_user_profile(user_email)
Retrieve a student's academic profile for personalized analysis.

## Environment Variables

- `GEMINI_API_KEY`: Your Gemini API key
- `KNOWLEDGE_BASE_UNIVERSITIES_URL`: Universities knowledge base cloud function URL
- `PROFILE_MANAGER_ES_URL`: Profile manager cloud function URL

## Running Locally

```bash
cd agents/college_expert_hybrid
adk web
```

## Example Queries

**General Questions:**
- "What does UCLA look for in applicants?"
- "Compare UC Berkeley and USC for computer science"
- "What are the career outcomes for business majors at top UC schools?"
- "Which California universities have the highest acceptance rates?"

**Personalized Analysis (requires profile):**
- "Analyze my chances at Stanford"
- "What are my odds of getting into UCLA?"
- "Compare my profile against USC and UC Berkeley"

## Search Types

| Type | Best For | Description |
|------|----------|-------------|
| hybrid | Most queries | Combines BM25 text + vector similarity |
| semantic | Conceptual queries | Vector similarity only |
| keyword | Exact matches | BM25 text search only |

## Filters

| Filter | Example | Description |
|--------|---------|-------------|
| state | "CA" | State abbreviation |
| type | "Public" | Public or Private |
| acceptance_rate_max | 25 | Max acceptance rate |
| acceptance_rate_min | 10 | Min acceptance rate |
| market_position | "Public Ivy" | University category |
