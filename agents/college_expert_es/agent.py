"""
College Expert Agent
A specialized agent for college admissions counseling using university knowledge base and student profile.
"""
import os
from typing import List
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import AgentTool
from google import genai
from google.genai import types

# Import logging
from .tools.logging_utils import log_agent_entry, log_agent_exit
from pydantic import BaseModel, Field

# Import RAG-specific tools
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.knowledge_base_analyst.agent import KnowledgeBaseAnalyst

# Configure logging
import logging
logger = logging.getLogger(__name__)

class OrchestratorOutput(BaseModel):
    """Final output from the College Counselor agent."""
    result: str = Field(description="Markdown-formatted response with complete answer")
    suggested_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions for the user")

# Create response formatter
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

# Create the main agent with sub_agents
MasterReasoningAgent = LlmAgent(
    name="MasterReasoningAgent",
    model="gemini-2.5-flash",
    description="College admissions counseling expert using student profile and knowledge base",
    instruction="""You are a College Admissions Counselor. You help students in two ways:
    
    **1. GENERAL COLLEGE QUESTIONS (No Profile Needed):**
    When users ask about colleges, programs, requirements, or comparisons WITHOUT requesting personal analysis:
    
    **Use the KnowledgeBaseAnalyst tool to search for:**
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
    
    **Then use KnowledgeBaseAnalyst to search for:**
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
    - Use KnowledgeBaseAnalyst for university information
    - If StudentProfileAgent returns no profile, tell user to upload it
    - If KnowledgeBaseAnalyst can't find statistics, note that data is limited
    - Never make up GPA, SAT scores, statistics, or career data
    
    **Format:**
    - Use Markdown with headings (##, ###)
    - Use **bold** for emphasis
    - Use bullet points on new lines with blank line before list
    - Use tables for comparisons (only if you have the data)
    """,
    tools=[
        AgentTool(StudentProfileAgent), 
        AgentTool(KnowledgeBaseAnalyst)
    ],
    output_key="agent_response",
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

