"""
AI-Powered College Admissions Prediction System - Master Reasoning Agent

This agent orchestrates a suite of specialized sub-agents to perform a holistic, reasoning-based analysis of college admissions chances.
"""

import os
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from google import genai
from google.genai import types

# Import sub-agents and final schema
from .schemas.schemas import OrchestratorOutput

# Import logging utilities
from .tools.logging_utils import log_agent_entry, log_agent_exit

# Import ALL sub-agents at startup for dynamic routing
print("[AGENT] Importing all sub-agents for dynamic approach selection...")

# Import RAG (File Search) sub-agents
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.knowledge_base_analyst.agent import KnowledgeBaseAnalyst

# Import Elasticsearch sub-agents
try:
    from .sub_agents.student_profile_agent_es.agent import StudentProfileESAgent
    from .sub_agents.knowledge_base_analyst_es.agent import KnowledgeBaseESAnalyst
    ES_AVAILABLE = True
    print("[AGENT] ✓ Elasticsearch sub-agents loaded")
except ImportError as e:
    ES_AVAILABLE = False
    print(f"[AGENT] ✗ Elasticsearch sub-agents not available: {e}")
    StudentProfileESAgent = None
    KnowledgeBaseESAnalyst = None

print("[AGENT] ✓ RAG (File Search) sub-agents loaded")

# Sub-agent registry for dynamic selection
SUB_AGENT_REGISTRY = {
    'rag': {
        'student_profile': StudentProfileAgent,
        'knowledge_base': KnowledgeBaseAnalyst,
        'student_profile_name': 'StudentProfileAgent (File Search)',
        'knowledge_base_name': 'KnowledgeBaseAnalyst (RAG)'
    },
    'elasticsearch': {
        'student_profile': StudentProfileESAgent if ES_AVAILABLE else StudentProfileAgent,
        'knowledge_base': KnowledgeBaseESAnalyst if ES_AVAILABLE else KnowledgeBaseAnalyst,
        'student_profile_name': 'StudentProfileESAgent (Cloud Function API)' if ES_AVAILABLE else 'StudentProfileAgent (File Search)',
        'knowledge_base_name': 'KnowledgeBaseESAnalyst (Elasticsearch)' if ES_AVAILABLE else 'KnowledgeBaseAnalyst (RAG)'
    }
}

# Default approach (can be overridden by request parameter)
DEFAULT_APPROACH = os.getenv('KNOWLEDGE_BASE_APPROACH', 'rag').lower()
print(f"[AGENT] Default approach: {DEFAULT_APPROACH}, Available: {', '.join(SUB_AGENT_REGISTRY.keys())}")

def get_sub_agents_for_approach(approach='rag'):
    """
    Dynamically select sub-agents based on the requested approach.
    
    Args:
        approach: One of 'rag' or 'elasticsearch'
    
    Returns:
        Tuple of (student_profile_agent, knowledge_base_agent, student_profile_name, kb_name)
    """
    approach = approach.lower() if approach else 'rag'
    
    if approach not in SUB_AGENT_REGISTRY:
        print(f"[AGENT] Warning: Unknown approach '{approach}', falling back to 'rag'")
        approach = 'rag'
    
    registry = SUB_AGENT_REGISTRY[approach]
    print(f"[AGENT] Selected approach: {approach}")
    print(f"[AGENT] Student Profile Agent: {registry['student_profile_name']}")
    print(f"[AGENT] Knowledge Base Agent: {registry['knowledge_base_name']}")
    
    return (
        registry['student_profile'],
        registry['knowledge_base'],
        registry['student_profile_name'],
        registry['knowledge_base_name']
    )

# Create Master Reasoning Agents for each approach
def create_master_reasoning_agent(approach='rag'):
    """Create a Master Reasoning Agent for the specified approach."""
    student_profile_agent, kb_analyst, sp_name, kb_name = get_sub_agents_for_approach(approach)
    
    agent_instruction = """
    You are a College Admissions Counselor. You help students in two ways:
    
    **1. GENERAL COLLEGE QUESTIONS (No Profile Needed):**
    When users ask about colleges, programs, requirements, or comparisons WITHOUT requesting personal analysis:
    
    **Knowledge Base Approach:** """ + kb_name + """
    
    **Use the available knowledge base tool to search for:**
      * Admissions statistics (GPA ranges, test scores, acceptance rates)
      * Institutional priorities and values (what they look for in applicants)
      * Student experiences and campus culture
      * Career outcomes (employment stats, salaries, top employers, career services)
      * Program details, requirements, and unique features
      * University-specific searches, comparisons, and structured data
    
    **DO NOT call StudentProfileAgent for general questions**
    **Synthesize data from the knowledge base into a comprehensive answer**
    
    Examples of general questions:
    - "What does USC look for in applicants?"
    - "Compare career outcomes for UC Berkeley vs UCLA business programs"
    - "What are the admission requirements for Stanford?"
    - "Tell me about MIT's computer science program and job placement"
    
    **2. ADMISSIONS ANALYSIS (Profile Required):**
    When users ask to analyze THEIR chances or want PERSONALIZED analysis:
    - MANDATORY FIRST STEP: Extract user email from [USER_EMAIL: ...] tag
    - Call """ + sp_name + """ FIRST with the user's email to get their academic profile
    
    **Knowledge Base Approach:** """ + kb_name + """
    
    **Use the available knowledge base tool to search for:**
      * Latest admissions statistics (acceptance rates, GPA ranges, test scores)
      * Institutional priorities and values
      * Career outcomes for their intended major
      * University-specific searches and structured data extraction
    
    **Analysis Process:**
    - Compare the student's profile against the university's:
      * Academic requirements (compare student's GPA/test scores to university's ranges)
      * Institutional fit (values, priorities, what they seek)
      * Extracurricular alignment (activities, leadership, impact)
      * Career outcomes for their intended major
    - Synthesize into a personalized admissions prediction with specific recommendations and statistical comparison
    
    Examples of analysis questions:
    - "Analyze my chances at Stanford for Computer Science"
    - "What are my odds of getting into MIT?"
    - "Compare my profile against USC and UCLA"
    - "Should I apply Early Decision to Columbia?"
    
    **CRITICAL RULES:**
    - NEVER skip """ + sp_name + """ for personal analysis requests
    - Use the available knowledge base tool for university information
    - If """ + sp_name + """ returns no profile, tell user to upload it
    - If the knowledge base tool can't find statistics, note that data is limited
    - Never make up GPA, SAT scores, statistics, or career data
    
    **Format:**
    - Use Markdown with headings (##, ###)
    - Use **bold** for emphasis
    - Use bullet points on new lines with blank line before list
    - Use tables for comparisons (only if you have the data)
    
    **Output:** Store your response in output_key for the formatter.
    """
    
    return LlmAgent(
        name=f"MasterReasoningAgent_{approach.upper()}",
        model="gemini-2.5-flash",
        description=f"Synthesizes structured reports from sub-agents ({approach} approach) to produce a final admissions prediction.",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3
        ),
        instruction=agent_instruction,
        tools=[
            AgentTool(student_profile_agent),
            AgentTool(kb_analyst),
        ],
        output_key="agent_response",
        before_model_callback=log_agent_entry,
        after_model_callback=log_agent_exit
    )

# Create master agents for all approaches
print("[AGENT] Creating Master Reasoning Agents...")
MasterReasoningAgent_RAG = create_master_reasoning_agent('rag')
MasterReasoningAgent_ES = create_master_reasoning_agent('elasticsearch')

# Registry of master agents
MASTER_AGENT_REGISTRY = {
    'rag': MasterReasoningAgent_RAG,
    'elasticsearch': MasterReasoningAgent_ES
}
print("[AGENT] ✓ Master agents created")

# Create formatter agents for each approach to avoid parent agent conflicts
def create_response_formatter(approach='rag'):
    """Create a response formatter agent for the specified approach."""
    return LlmAgent(
        name=f"response_formatter_{approach}",
        model="gemini-2.5-flash",
        description="Formats agent responses into final output with suggested questions",
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3  # Lower temperature for consistent formatting
        ),
        instruction="""
        Format the agent_response into OrchestratorOutput JSON:
        
        1. **result**: Copy agent_response AS-IS (don't modify)
        2. **suggested_questions**: Generate 4 relevant follow-up questions
        
        **Question Rules:**
        - Only mention universities that appear in agent_response
        - Mix general and specific questions
        - For greetings: use general questions about admissions
        - For analysis: suggest comparisons or next steps
        - Return as array of strings
        """,
        output_schema=OrchestratorOutput,
        output_key="formatted_output",
        before_model_callback=log_agent_entry,
        after_model_callback=log_agent_exit
    )

# Create sequential agents for each approach
def create_root_agent(approach='rag'):
    """Create a root agent for the specified approach."""
    master_agent = MASTER_AGENT_REGISTRY.get(approach, MasterReasoningAgent_RAG)
    response_formatter = create_response_formatter(approach)
    
    return SequentialAgent(
        name=f"CollegeCounselorAgent_{approach.upper()}",
        description=f"College counseling agent using {approach.upper()} approach for knowledge base queries",
        sub_agents=[
            master_agent,
            response_formatter
        ]
    )

# Create root agents for all approaches
print("[AGENT] Creating root agents...")
root_agent_rag = create_root_agent('rag')
root_agent_es = create_root_agent('elasticsearch')
print("[AGENT] ✓ Root agents created for: rag, elasticsearch")

# Registry of root agents for dynamic selection
ROOT_AGENT_REGISTRY = {
    'rag': root_agent_rag,
    'elasticsearch': root_agent_es
}

# Default root agent (ADK web server uses this)
root_agent = root_agent_rag

print(f"[AGENT] ✓ Initialization complete - Available approaches: {list(ROOT_AGENT_REGISTRY.keys())}")