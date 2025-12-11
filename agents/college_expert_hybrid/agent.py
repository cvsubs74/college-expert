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
    calculate_college_fit, 
    get_college_list, 
    list_valid_university_ids, 
    add_college_to_list,
    # Profile tool - returns full markdown content
    get_student_profile_data,
    # Profile update tool - single natural language interface
    update_profile
)

from pydantic import BaseModel, Field

# Import sub-agents
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.university_knowledge_analyst.agent import UniversityKnowledgeAnalyst
from .sub_agents.deep_research_agent.agent import DeepResearchAgent
from .sub_agents.profile_preloader_agent.agent import ProfileLoaderAgent

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
    model="gemini-2.0-flash",
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
    model="gemini-2.0-flash",
    description="College admissions counseling expert using hybrid search on structured university profiles",
    instruction="""You are a College Admissions Counselor with access to a university knowledge base.

**PROFILE ACCESS:**
The student's profile is pre-loaded as formatted markdown. Use this tool to access it:

1. **get_student_profile_data()** → Returns the complete student profile as markdown
   - Contains: GPA, SAT/ACT scores, intended major, courses, extracurriculars, awards
   - Read the markdown directly to extract any information you need
   - DO NOT ask the user for this information - it's all in the profile!

**PROFILE UPDATES:**
When the student asks to update their profile:

2. **update_profile(instruction)** → Update anything in the profile using natural language
   Examples:
   - update_profile("Update the GPA to 3.95")
   - update_profile("Add a new extracurricular: Chess Club President")
   - update_profile("Change intended major to Computer Science")
   - update_profile("Add AP Biology score of 5")

**CRITICAL: NEVER ask the user for profile information - use get_student_profile_data() instead!**

**HOW TO ANSWER:**

1. **University Questions** → Search KB using UniversityKnowledgeAnalyst
   - If found: Answer with KB data
   - If NOT found: Say "I don't have [university] in my knowledge base" and offer alternatives

2. **Personalized Questions** ("my chances", "should I apply", "based on my profile"):
   → Call get_student_profile_data() to get full profile markdown
   → Read GPA, SAT scores, major directly from the markdown
   → Search university with UniversityKnowledgeAnalyst
   → Compare profile data to university requirements

3. **Fit Analysis** ("analyze fit", "my fit for X"):
   → Call get_student_profile_data() to get the student's intended major and stats
   → Search university first with UniversityKnowledgeAnalyst
   → Use calculate_college_fit with the student's intended major
   → Present category, percentage, factor breakdown

4. **College List** → get_college_list(email="auto")

5. **Add to List** → add_college_to_list(email="auto", university_name, major)

6. **Recommendations** ("build a list", "find safety schools", "recommend colleges"):
   → Call get_student_profile_data() to get GPA, test scores, intended major from markdown
   → Search relevant universities with UniversityKnowledgeAnalyst
   → Compare profile metrics to university admission data
   → DO NOT ask for more information - read it from the profile markdown!

7. **Deep Research** ("vibe", "culture", "recent news") → DeepResearchAgent

8. **Profile Updates** ("update my GPA", "change my major", "add this activity"):
   → Use update_profile(instruction) with a clear description of the change
   → Confirm the update was successful

**RULES:**
- ALWAYS call profile tools to get student data - NEVER ask the user
- If a profile tool returns "not found", use reasonable defaults
- Acronyms work! MIT, UCLA, UCB, USC are all searchable
- NEVER ask clarifying questions for recommendations - just search and provide results
""",

    tools=[
        # Profile tool - returns full markdown content
        FunctionTool(get_student_profile_data),
        # Profile update tool - natural language interface
        FunctionTool(update_profile),
        # Sub-agents
        AgentTool(StudentProfileAgent), 
        AgentTool(UniversityKnowledgeAnalyst),
        AgentTool(DeepResearchAgent),
        # College list tools
        FunctionTool(calculate_college_fit),
        FunctionTool(get_college_list),
        FunctionTool(add_college_to_list),
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
