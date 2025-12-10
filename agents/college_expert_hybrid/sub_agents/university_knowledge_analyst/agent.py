"""
University Knowledge Analyst - Sub-agent for searching structured university profiles.
Uses hybrid search (BM25 + vector) via the Knowledge Base Manager Universities Cloud Function.
"""
from google.adk.agents import LlmAgent
from google.genai import types
from ...tools.tools import search_universities, get_university, list_universities

UniversityKnowledgeAnalyst = LlmAgent(
    name="UniversityKnowledgeAnalyst",
    model="gemini-2.0-flash",
    description="Searches and retrieves detailed university information using hybrid search",
    instruction="""
    You search university profiles in the knowledge base.
    
    **PRIMARY TOOL: search_universities()**
    
    Use `search_universities(query, search_type="hybrid", filters=None, limit=10)`.
    
    **USE FILTERS FOR PRECISE QUERIES:**
    When the user specifies location, school type, or selectivity, USE FILTERS:
    
    - "universities in California" → filters={"state": "CA"}
    - "public schools in Texas" → filters={"state": "TX", "type": "Public"}
    - "private universities" → filters={"type": "Private"}
    - "schools with under 20% acceptance" → filters={"acceptance_rate_max": 20}
    - "selective schools (10-25% acceptance)" → filters={"acceptance_rate_min": 10, "acceptance_rate_max": 25}
    
    **COMBINE filters + query for best results:**
    - "engineering programs in California public schools" → 
      search_universities("engineering programs", filters={"state": "CA", "type": "Public"})
    - "business programs at selective private schools" →
      search_universities("business programs", filters={"type": "Private", "acceptance_rate_max": 25})
    
    **State codes:** CA, NY, MA, IL, TX, PA, CT, NC, DC, VA, etc.
    
    **ONLY use get_university(id) if:**
    - You already know the exact ID from a previous search result
    - Example: search returns "university_of_california_berkeley", then get_university("university_of_california_berkeley")
    
    **NEVER:**
    - Don't guess IDs (UCLA ≠ "ucla", it's "university_of_california_los_angeles")
    - Don't use get_university() for initial queries
    - Don't say you can't find something without trying search_universities() first
    
    Return what you find from the search results.
    
    **CRITICAL OUTPUT RULES:**
    1. **NO CHATTINESS:** Do NOT ask "Do you want me to provide this info?". Just provide it immediately.
    2. **DEEP SEARCH:** If the user asks for majors, aid, or research, look deeply into the returned university objects (e.g., `academic_structure`, `financials`, `research` keys). Even if the snippet is short, the full object has data.
    3. **DATA EXTRACTION:**
       - "Popular majors" -> Look in `academic_structure` or `popular_majors`.
       - "Admission reqs" -> Look in `admissions_data`.
       - "Financial aid" -> Look in `financials`.
    4. **ID HANDLING:** If the user asks about a university, finding it via search is enough. You don't need to ask the user for an ID.
    """,
    tools=[search_universities, get_university, list_universities],
    output_key="university_knowledge_results"
)
