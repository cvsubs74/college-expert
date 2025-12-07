"""
University Knowledge Analyst - Sub-agent for searching structured university profiles.
Uses hybrid search (BM25 + vector) via the Knowledge Base Manager Universities Cloud Function.
"""
from google.adk.agents import LlmAgent
from ...tools.tools import search_universities, get_university, list_universities

UniversityKnowledgeAnalyst = LlmAgent(
    name="UniversityKnowledgeAnalyst",
    model="gemini-2.5-flash-lite",
    description="Searches and retrieves detailed university information using hybrid search",
    instruction="""
    You search the university knowledge base to find and retrieve university information.
    
    **TOOLS:**
    
    1. `search_universities(query, search_type, filters, limit)`
       - query: What to search for (e.g., "business undergraduate program")
       - search_type: "hybrid" (default), "semantic", or "keyword"
       - filters: {"state": "CA", "acceptance_rate_max": 25, "type": "Public"}
       - limit: Max results (default 10)
    
    2. `get_university(university_id)` - Get specific university by ID
    
    3. `list_universities()` - List all universities in knowledge base
    
    **SEARCH APPROACH:**
    
    - Search by program/criteria first: "business undergraduate program"
    - Let results show available universities
    - Use filters to narrow: state, acceptance rate, public/private
    
    **ANSWER FORMAT:**
    - Report what you found in the knowledge base
    - Include specific data: acceptance rates, GPA ranges, programs
    - Say if data is unavailable
    """,
    tools=[search_universities, get_university, list_universities],
    output_key="university_knowledge_results"
)
