"""
College Expert Hybrid Agent
A specialized agent for college admissions counseling using hybrid search on structured university profiles.
Uses the Knowledge Base Manager Universities Cloud Function for fast, accurate university data retrieval.
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

# Import sub-agents
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.university_knowledge_analyst.agent import UniversityKnowledgeAnalyst

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
    model="gemini-2.5-flash-lite",
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


# Create the main reasoning agent
MasterReasoningAgent = LlmAgent(
    name="MasterReasoningAgent",
    model="gemini-2.5-flash",
    description="College admissions counseling expert using hybrid search on structured university profiles",
    instruction="""You are a College Admissions Counselor.

    The user's email is in the message as [USER_EMAIL: xxx@example.com]. Always extract and use it when calling StudentProfileAgent.
    
    ONLY recommend universities that are returned from the knowledge base search. Do not add universities from your general knowledge.
    
    Use your tools to answer questions about universities and student profiles.
    """,
    tools=[
        AgentTool(StudentProfileAgent), 
        AgentTool(UniversityKnowledgeAnalyst)
    ],
    output_key="agent_response",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit   
)


# Main agent using sequential pattern
root_agent = SequentialAgent(
    name="CollegeCounselorHybridAgent",
    sub_agents=[
        MasterReasoningAgent,
        response_formatter
    ]
)
