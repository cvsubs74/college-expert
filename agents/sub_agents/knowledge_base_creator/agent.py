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
        temperature=0.1,
        max_output_tokens=8000
    ),
    instruction="""
    You are a knowledge base synthesizer. You will receive RAW research data from 5 parallel agents.
    
    **YOUR TASK - SIMPLE AND DIRECT:**
    1. Copy the raw research data from each researcher to the corresponding field:
       - Copy raw_identity_data to identity_data field
       - Copy raw_admissions_data to admissions_data field  
       - Copy raw_academics_data to academics_data field
       - Copy raw_financials_data to financials_data field
       - Copy raw_student_life_data to student_life_data field
    
    2. Extract university name from the research data (look for university name in any field)
    3. Set research_date to today's date
    4. Extract source URLs from the research data and add to data_sources list
    5. Write a brief executive summary (1-2 paragraphs) about the university
    
    **IMPORTANT - KEEP IT SIMPLE:**
    - DO NOT reformat or restructure the raw data
    - DO NOT extract or transform data - just copy it as-is
    - DO NOT analyze or process the raw content
    - Preserve ALL original research data completely
    - The raw data fields should contain the EXACT output from researchers
    
    **DATA SOURCES:**
    - Look for URLs in the research data and add them to data_sources list
    - Remove duplicates if found
    - If no URLs found, data_sources can be empty list
    
    **EXECUTIVE SUMMARY:**
    - Brief overview of university identity, academics, and key characteristics
    - Keep it concise and high-level
    
    **STATE KEYS TO READ:**
    - { raw_identity_data? }
    - { raw_admissions_data? }
    - { raw_academics_data? }
    - { raw_financials_data? }
    - { raw_student_life_data? }
    
    **ERROR HANDLING:**
    - If any raw data field is missing or empty, use "Data not available" as fallback
    - If university name cannot be determined, use "Unknown University" as fallback
    - Always ensure all required fields are populated
    
    **OUTPUT:**
    Return UniversityKnowledgeBase JSON with all fields populated.
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
