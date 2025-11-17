"""
Knowledge Base Creator Agent

This agent orchestrates parallel research sub-agents to build comprehensive university profiles.
Each sub-agent uses the retriever+formatter pattern to avoid schema issues with tools.
"""

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.genai import types
from ...schemas.schemas import UniversityKnowledgeBase
from ...tools.logging_utils import log_agent_entry, log_agent_exit

# Import all sub-agents (each uses retriever+formatter pattern)
from .sub_agents.identity_researcher import IdentityResearcher
from .sub_agents.admissions_researcher import AdmissionsResearcher
from .sub_agents.academics_researcher import AcademicsResearcher
from .sub_agents.financials_researcher import FinancialsResearcher
from .sub_agents.student_life_researcher import StudentLifeResearcher

# ============================================================================
# Parallel Research Agent: Runs all 5 researchers simultaneously
# ============================================================================

parallel_researchers = ParallelAgent(
    name="ParallelUniversityResearchers",
    description="Runs 5 specialized research agents in parallel to gather comprehensive university data.",
    sub_agents=[
        IdentityResearcher,
        AdmissionsResearcher,
        AcademicsResearcher,
        FinancialsResearcher,
        StudentLifeResearcher
    ]
)

# ============================================================================
# Synthesizer Agent: Combines all research into final knowledge base
# ============================================================================

synthesizer_agent = LlmAgent(
    name="KnowledgeBaseSynthesizer",
    model="gemini-2.5-flash",
    description="Synthesizes all research findings into a comprehensive university knowledge base.",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2
    ),
    instruction="""
    You are a knowledge base synthesizer. You will receive RAW research data from 5 parallel agents.
    
    Each researcher provides data in TWO sections:
    1. RAW RESEARCH DATA - comprehensive search results with sources
    2. STRUCTURED Q&A SUMMARY - organized Q&A format
    
    **YOUR TASK:**
    1. Extract the complete RAW data (including Q&A and CITATIONS) from each researcher
    2. Store each researcher's full output in the corresponding field:
       - raw_identity_data → identity_data
       - raw_admissions_data → admissions_data
       - raw_academics_data → academics_data
       - raw_financials_data → financials_data
       - raw_student_life_data → student_life_data
    3. Extract the university name from the research data
    4. Add today's date as the research_date
    5. **COMPILE ALL CITATIONS:** Extract ALL citations from each researcher's "CITATIONS & SOURCES" section
       - Combine into a single comprehensive list in data_sources field
       - Remove duplicates but preserve all unique sources
       - Maintain full URLs and access dates
       - Number citations sequentially (1, 2, 3, ...)
    6. Write a comprehensive executive summary (2-3 paragraphs) covering:
       - University identity and culture
       - Admissions selectivity and key statistics (with 5-year trends)
       - Academic strengths and popular programs
       - Financial aid approach
       - Career outcomes and student success
    
    **DATA INTEGRATION:**
    - Preserve ALL raw research data - don't summarize or truncate
    - Include both the raw search results AND the Q&A summaries
    - Maintain data accuracy - don't add information not provided by researchers
    - Extract all source URLs mentioned in the research
    
    **FINAL OUTPUT:**
    A complete UniversityKnowledgeBase JSON object with full raw research data preserved.
    
    **STATE KEYS TO READ:**
    - { raw_identity_data? }
    - { raw_admissions_data? }
    - { raw_academics_data? }
    - { raw_financials_data? }
    - { raw_student_life_data? }
    """,
    output_schema=UniversityKnowledgeBase,
    output_key="university_knowledge_base"
)

# ============================================================================
# Main Knowledge Base Creator Agent
# ============================================================================

KnowledgeBaseCreator = SequentialAgent(
    name="KnowledgeBaseCreator",
    description="Creates comprehensive university knowledge base profiles by orchestrating parallel research agents.",
    sub_agents=[
        parallel_researchers,
        synthesizer_agent
    ]
)
