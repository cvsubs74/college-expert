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
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .schemas.schemas import OrchestratorOutput

# Import logging utilities
from .tools.logging_utils import log_agent_entry, log_agent_exit

# Get knowledge base approach from environment variable
KNOWLEDGE_BASE_APPROACH = os.getenv('KNOWLEDGE_BASE_APPROACH', 'rag').lower()

# Select the appropriate knowledge base analyst based on environment variable
# Import only the required sub-agent to avoid dependency issues
if KNOWLEDGE_BASE_APPROACH == 'elasticsearch':
    try:
        from .sub_agents.knowledge_base_analyst_ES.agent import KnowledgeBaseESAnalyst
        SELECTED_KB_ANALYST = KnowledgeBaseESAnalyst
        KB_ANALYST_NAME = "KnowledgeBaseESAnalyst (Elasticsearch)"
    except ImportError as e:
        print(f"[AGENT] Warning: Could not import Elasticsearch analyst: {e}")
        print("[AGENT] Falling back to RAG approach")
        from .sub_agents.knowledge_base_analyst.agent import KnowledgeBaseAnalyst
        SELECTED_KB_ANALYST = KnowledgeBaseAnalyst
        KB_ANALYST_NAME = "KnowledgeBaseAnalyst (RAG)"
        KNOWLEDGE_BASE_APPROACH = 'rag'
elif KNOWLEDGE_BASE_APPROACH == 'firestore':
    try:
        from .sub_agents.knowledge_base_analyst_FS.agent import KnowledgeBaseAnalystFS
        SELECTED_KB_ANALYST = KnowledgeBaseAnalystFS
        KB_ANALYST_NAME = "KnowledgeBaseAnalystFS (Firestore)"
    except ImportError as e:
        print(f"[AGENT] Warning: Could not import Firestore analyst: {e}")
        print("[AGENT] Falling back to RAG approach")
        from .sub_agents.knowledge_base_analyst.agent import KnowledgeBaseAnalyst
        SELECTED_KB_ANALYST = KnowledgeBaseAnalyst
        KB_ANALYST_NAME = "KnowledgeBaseAnalyst (RAG)"
        KNOWLEDGE_BASE_APPROACH = 'rag'
else:  # default to rag
    from .sub_agents.knowledge_base_analyst.agent import KnowledgeBaseAnalyst
    SELECTED_KB_ANALYST = KnowledgeBaseAnalyst
    KB_ANALYST_NAME = "KnowledgeBaseAnalyst (RAG)"

print(f"[AGENT] Using knowledge base approach: {KNOWLEDGE_BASE_APPROACH}")
print(f"[AGENT] Selected analyst: {KB_ANALYST_NAME}")

# The Master Reasoning Agent
MasterReasoningAgent = LlmAgent(
    name="MasterReasoningAgent",
    model="gemini-2.5-flash",
    description="Synthesizes structured reports from sub-agents to produce a final admissions prediction.",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3  # Lower temperature to reduce hallucination and increase factual accuracy
    ),
    instruction="""
    You are a College Admissions Counselor. You help students in two ways:
    
    **1. GENERAL COLLEGE QUESTIONS (No Profile Needed):**
    When users ask about colleges, programs, requirements, or comparisons WITHOUT requesting personal analysis:
    
    **Knowledge Base Approach:** """ + KB_ANALYST_NAME + """
    
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
    - Call StudentProfileAgent FIRST with the user's email to get their academic profile
    
    **Knowledge Base Approach:** """ + KB_ANALYST_NAME + """
    
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
    - NEVER skip StudentProfileAgent for personal analysis requests
    - Use the available knowledge base tool for university information
    - If StudentProfileAgent returns no profile, tell user to upload it
    - If the knowledge base tool can't find statistics, note that data is limited
    - Never make up GPA, SAT scores, statistics, or career data
    
    **Format:**
    - Use Markdown with headings (##, ###)
    - Use **bold** for emphasis
    - Use bullet points on new lines with blank line before list
    - Use tables for comparisons (only if you have the data)
    
    **Output:** Store your response in output_key for the formatter.
    """,
    tools=[
        AgentTool(StudentProfileAgent),
        AgentTool(SELECTED_KB_ANALYST),
    ],
    output_key="agent_response",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit
)

# Formatter agent - formats the response into OrchestratorOutput with suggested questions
response_formatter = LlmAgent(
    name="response_formatter",
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

# Main agent using sequential pattern
root_agent = SequentialAgent(
    name="CollegeCounselorAgent",
    sub_agents=[
        MasterReasoningAgent,
        response_formatter
    ]
)