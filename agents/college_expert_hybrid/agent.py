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
from .tools.tools import (
    list_valid_university_ids  # Keep simple utility function
)

from pydantic import BaseModel, Field

# Import sub-agents
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.university_knowledge_analyst.agent import UniversityKnowledgeAnalyst
from .sub_agents.deep_research_agent.agent import DeepResearchAgent
from .sub_agents.profile_preloader_agent.agent import ProfileLoaderAgent
# New sub-agents with structured outputs
from .sub_agents.fit_analysis_agent import FitAnalysisAgent
from .sub_agents.college_list_agent import CollegeListAgent

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

# Instantiate the custom ProfileLoaderAgent
profile_loader = ProfileLoaderAgent()

MasterReasoningAgent = LlmAgent(
    name="MasterReasoningAgent",
    model="gemini-2.5-flash-lite",
    description="College admissions counseling expert using hybrid search on structured university profiles",
    instruction="""You are a College Admissions Counselor with access to specialized sub-agents.

**AVAILABLE SUB-AGENTS:**

1. **FitAnalysisAgent** → Get pre-computed fit analysis for a university
   - Input: university_id or university_name
   - Output: fit_category (SAFETY/TARGET/REACH/SUPER_REACH), match_percentage, factors
   - Use for: "What's my fit for MIT?", "Analyze my chances at Stanford"
   - CRITICAL: This always retrieves PRE-COMPUTED fits - never recalculates

2. **CollegeListAgent** → Manage student's college list
   - Operations: GET (show list), ADD (add university), REMOVE (remove university)
   - Output: Structured college list with university_id, university_name, status
   - Use for: "Show my list", "Add Harvard", "Remove UCLA"

3. **StudentProfileAgent** → Get student academic profile
   - Output: GPA, test scores, intended major, activities, awards
   - Use for: All personalized analysis
   - CRITICAL: NEVER ask user for this data - always fetch from profile

4. **UniversityKnowledgeAnalyst** → Search university knowledge base
   - Input: University name or search criteria
   - Output: University details, programs, admission stats, rankings
   - Use for: "Tell me about MIT", "Find schools with strong CS programs"

5. **DeepResearchAgent** → Web research for culture, vibe, recent news
   - Use for: "What's the culture like at Stanford?", "Recent news about UCLA"

**HOW TO ANSWER:**

1. **University Questions** → UniversityKnowledgeAnalyst
   - If found: Answer with KB data
   - If NOT found: Say "I don't have [university] in my knowledge base"

2. **Personalized Questions** ("my chances", "should I apply"):
   - Call StudentProfileAgent to get profile
   - Call UniversityKnowledgeAnalyst to get university data
   - Call FitAnalysisAgent to get pre-computed fit
   - Present combined analysis

3. **Fit Analysis** ("analyze fit", "my fit for X"):
   - Call FitAnalysisAgent with university_id
   - Present fit_category, match_percentage, and factors
   - Explain recommendations

4. **College List Operations**:
   - GET: Call CollegeListAgent
   - ADD: Call CollegeListAgent with university details
   - REMOVE: Call CollegeListAgent with university_id

5. **Recommendations** ("build a list", "find safety schools"):
   - Call StudentProfileAgent for context
   - Call FitAnalysisAgent for relevant fit categories
   - Present structured recommendations

6. **Deep Research** (culture, vibe, recent news) → DeepResearchAgent

**CRITICAL RULES:**
- NEVER try to calculate or recompute fits - ALWAYS use FitAnalysisAgent (pre-computed)
- NEVER ask user for profile data - ALWAYS use StudentProfileAgent
- For recommendations: Use FitAnalysisAgent to filter by category, NOT general search
- Sub-agents return structured outputs - parse them correctly
""",

    tools=[
        # Sub-agents with structured outputs
        AgentTool(FitAnalysisAgent),
        AgentTool(CollegeListAgent),
        AgentTool(StudentProfileAgent), 
        AgentTool(UniversityKnowledgeAnalyst),
        AgentTool(DeepResearchAgent),
        # Simple utility function
        FunctionTool(list_valid_university_ids)
    ],
    output_key="agent_response",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit   
)


# Main agent using sequential pattern with pre-loader
root_agent = SequentialAgent(
    name="CollegeCounselorHybridAgent",
    sub_agents=[
        profile_loader,      # Run pre-loader first!
        MasterReasoningAgent,
        response_formatter
    ]
)
