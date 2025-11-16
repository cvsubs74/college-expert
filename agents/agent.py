"""
AI-Powered College Admissions Prediction System - Master Reasoning Agent

This agent orchestrates a suite of specialized sub-agents to perform a holistic, reasoning-based analysis of college admissions chances.
"""

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools.agent_tool import AgentTool
from google import genai
from google.genai import types

# Import sub-agents and final schema
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.quantitative_analyst.agent import QuantitativeAnalyst
from .sub_agents.brand_analyst.agent import BrandAnalyst
from .sub_agents.community_analyst.agent import CommunityAnalyst
from .sub_agents.knowledge_base_analyst.agent import KnowledgeBaseAnalyst
from .sub_agents.career_outcomes_analyst.agent import CareerOutcomesAnalyst
from .schemas.schemas import OrchestratorOutput

# Import logging utilities
from .tools.logging_utils import log_agent_entry, log_agent_exit

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
    - Call these agents for comprehensive information:
      * QuantitativeAnalyst (admissions statistics, acceptance rates, GPA/test score ranges)
      * BrandAnalyst (institutional priorities, values, what they look for)
      * CommunityAnalyst (student experiences, campus culture)
      * CareerOutcomesAnalyst (employment stats, salaries, top employers, career services)
      * KnowledgeBaseAnalyst (general university information, programs, requirements)
    - DO NOT call StudentProfileAgent for general questions
    - Synthesize all data into a comprehensive answer
    
    Examples of general questions:
    - "What does USC look for in applicants?"
    - "Compare career outcomes for UC Berkeley vs UCLA business programs"
    - "What are the admission requirements for Stanford?"
    - "Tell me about MIT's computer science program"
    
    **2. ADMISSIONS ANALYSIS (Profile Required):**
    When users ask to analyze THEIR chances or want PERSONALIZED analysis:
    - MANDATORY FIRST STEP: Extract user email from [USER_EMAIL: ...] tag
    - Call StudentProfileAgent FIRST with the user's email
    - Then call ALL other agents for the university:
      * QuantitativeAnalyst (compare student stats to university ranges)
      * BrandAnalyst (assess student fit with institutional priorities)
      * CommunityAnalyst (evaluate student's extracurricular alignment)
      * CareerOutcomesAnalyst (career prospects for student's intended major)
      * KnowledgeBaseAnalyst (program-specific information)
    - Synthesize all data into a personalized admissions prediction
    
    Examples of analysis questions:
    - "Analyze my chances at Stanford"
    - "What are my odds of getting into MIT for computer science?"
    - "Compare my profile against USC and UCLA"
    - "Should I apply Early Decision to Columbia?"
    
    **CRITICAL RULES:**
    - NEVER skip StudentProfileAgent for personal analysis requests
    - ALWAYS call all relevant agents for comprehensive answers
    - Only use data explicitly retrieved from tools
    - If StudentProfileAgent returns no profile, tell user to upload it
    - If agents return limited data, explicitly state what's missing
    - Never make up GPA, SAT scores, statistics, or career data
    
    **Format:**
    - Use Markdown with headings (##, ###)
    - Use **bold** for emphasis
    - Use bullet points on new lines with blank line before list
    - Use tables for comparisons (only if you have the data)
    - Remove citations from responses
    
    **Output:** Store your response in output_key for the formatter.
    """,
    tools=[
        AgentTool(StudentProfileAgent),
        AgentTool(QuantitativeAnalyst),
        AgentTool(BrandAnalyst),
        AgentTool(CommunityAnalyst),
        AgentTool(CareerOutcomesAnalyst),
        AgentTool(KnowledgeBaseAnalyst),
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