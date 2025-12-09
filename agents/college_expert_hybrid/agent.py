"""
College Expert Hybrid Agent
A specialized agent for college admissions counseling using hybrid search on structured university profiles.
Uses the Knowledge Base Manager Universities Cloud Function for fast, accurate university data retrieval.
"""
import os
from typing import List
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import AgentTool, FunctionTool
from google import genai
from google.genai import types

# Import logging
from .tools.logging_utils import log_agent_entry, log_agent_exit
from .tools.tools import calculate_college_fit, recalculate_all_fits, get_college_list, list_valid_university_ids
from pydantic import BaseModel, Field

# Import sub-agents
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.university_knowledge_analyst.agent import UniversityKnowledgeAnalyst
from .sub_agents.deep_research_agent.agent import DeepResearchAgent

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
    model="gemini-2.5-flash-lite",
    description="College admissions counseling expert using hybrid search on structured university profiles",
    instruction="""You are a College Admissions Counselor.

    **HOW TO RESPOND:**
    
    1. **General university questions** (no "my"/"I"/"me"):
       → Call UniversityKnowledgeAnalyst
       → Answer from results
    
    2. **Personalized questions** ("my chances", "should I", etc.):
       → Step 1: Call StudentProfileAgent with email from [USER_EMAIL: xxx]
       → Step 2: Call UniversityKnowledgeAnalyst to search universities
       → Step 3: Compare profile data against KB university data
       → NEVER use general knowledge - only use data from both agents
    
    3. **College Fit Analysis** ("analyze fit", "what is my fit", "how do I match", "fit for [university]"):
       → Call calculate_college_fit tool with:
         - user_email: Extract from [USER_EMAIL: xxx]
         - university_id: Convert name to snake_case (e.g., "Stanford" → "stanford_university")
         - intended_major: Optional, extract if mentioned
       → The tool automatically:
         - Returns cached fit if already calculated (saves time)
         - Stores the result in the user's profile for future reference
       → Present fit results including:
         - Fit Category (SAFETY, TARGET, REACH, SUPER_REACH)
         - Match Percentage
         - Factor breakdown with scores (GPA, Tests, Acceptance Rate, Course Rigor, Major Fit, Activities, Early Action)
         - Specific recommendations
    
    4. **Profile Updated / Recalculate All Fits** ("I updated my profile", "recalculate fits", "refresh my fit analysis"):
       → Call recalculate_all_fits(user_email)
       → This recalculates fit for ALL universities in the user's college list
       → Present summary of updated fit categories
       → Present summary of updated fit categories
       
       
    5. **College List Management** ("show my list", "my colleges", "what schools did I save"):
       → Call get_college_list(user_email) to get the schools and their calculated fit
       → The response includes fit factors like "GPA Match: 20", "Course Rigor: 16"
       → Present the list clearly with fit categories
       
    6. **Why Questions / Explain Fit** ("why is X a REACH", "why these schools", "explain my fit"):
       → IMPORTANT: Check the CONVERSATION HISTORY provided in the request - it may contain the college list already
       → If the list was shown previously in conversation history, use that data directly - DO NOT call get_college_list again
       → If no prior context, call get_college_list(user_email) first
       → Call StudentProfileAgent(user_email) to get the student's academic stats
       → ANSWER the "why" question by comparing:
         * Student's stats (GPA, SAT/ACT) from StudentProfileAgent
         * University requirements from knowledge base
         * Fit factors from the college list response
       → Example answer: "Berkeley is a REACH because your GPA (3.8) is slightly below their average (3.9), and their 11% acceptance rate makes it highly selective."
       
    7. **Deep/Nuanced Research** ("recent news", "lab details", "student vibe"):
       → Call DeepResearchAgent
       → Use for questions that structured data cannot answer
       → Combine with KB data if relevant
    
    **UNDERSTANDING CONVERSATION HISTORY:**
    
    The user's message may include a "CONVERSATION HISTORY:" section at the start.
    This contains previous exchanges from the current chat session.
    USE THIS CONTEXT to understand references like "these colleges" or "my list".
    Do NOT ask the user to clarify if the answer is in the history.
    
    **EXAMPLES:**
    
    ✅ "Compare UCLA and USC"
    → UniversityKnowledgeAnalyst("UCLA USC")
    
    ✅ "What are MY chances at UCLA?"
    → StudentProfileAgent(email)
    → UniversityKnowledgeAnalyst("UCLA")
    → Compare GPA, scores, activities from profile against UCLA's requirements from KB
    
    ✅ "Analyze my fit for Princeton"
    → FIRST: list_valid_university_ids() to get correct ID format (cached after first call)
    → Find "princeton_university" in the list
    → calculate_college_fit(user_email="user@email.com", university_id="princeton_university")
    → Present fit category, score breakdown, and recommendations
    
    ✅ "Why are these colleges REACH?" (after showing list)
    → Read CONVERSATION HISTORY to find which colleges were shown
    → Call StudentProfileAgent(email) if not already loaded
    → Explain using fit factors from history + profile stats
    
    ✅ "What is the vibe of the CS dorms at Berkeley?"
    → DeepResearchAgent("Berkeley CS dorm culture reviews")
    
    **CRITICAL RULES:**
    
    1. For personalized questions: MUST call BOTH agents, never just one
    2. For fit analysis: FIRST call list_valid_university_ids() to get exact university IDs
       - NEVER guess or generate university IDs! Use only IDs from the list
       - Example: "new_york_university" NOT "new_york_university_stern_school"
       - The list is cached so subsequent calls are instant
    3. ALWAYS use calculate_college_fit tool - it handles caching automatically
    4. ONLY use data from knowledge base search results
    5. NEVER add universities not in search results
    6. READ CONVERSATION HISTORY before asking for clarification
    7. When answering "why" questions, ALWAYS provide specific data (GPA, scores, acceptance rates)
    """,
    tools=[
        AgentTool(StudentProfileAgent), 
        AgentTool(UniversityKnowledgeAnalyst),
        AgentTool(DeepResearchAgent),
        FunctionTool(calculate_college_fit),
        FunctionTool(recalculate_all_fits),
        FunctionTool(get_college_list),
        FunctionTool(list_valid_university_ids)
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
