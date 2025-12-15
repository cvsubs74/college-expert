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
    list_valid_university_ids  # Utility function
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
from .sub_agents.profile_update_agent.agent import ProfileUpdateAgent

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
    
    **CRITICAL: Questions must be STUDENT-FOCUSED, not AI-focused**
    
    **BAD Examples (AI-meta, avoid these)**:
    - "Can you confirm if X was removed?" (checking AI's work)
    - "What other courses would you like to add or remove?" (too generic)
    - "Would you like to review your entire course list?" (asking about data review)
    
    **GOOD Examples (student/college planning focus)**:
    - "What colleges should I target with my current GPA?" (actionable planning)
    - "How can I strengthen my extracurriculars for top schools?" (improvement strategy)
    - "Should I take more AP courses senior year?" (academic planning)
    - "What's my fit for UC Berkeley?" (specific college assessment)
    
    **Question Rules by Context**:
    
    1. **Profile Updates** (GPA, courses, activities added/removed):
       - Suggest fit analysis impact: "How does this change affect my fit for [university]?"
       - Academic strategy: "What other courses would boost my application?"
       - College targeting: "What reach schools should I consider now?"
       - Timeline planning: "When should I take my next SAT to improve my score?"
    
    2. **Fit Analysis** (for specific university):
       - Compare similar schools: "How does [university] compare to [similar university]?"
       - Gap filling: "What can I do to improve my chances at [university]?"
       - Alternative suggestions: "What similar schools should I also consider?"
       - Early decision: "Should I apply Early Decision to [university]?"
    
    3. **University Information**:
       - Fit check: "What's my fit for [university]?"
       - Program details: "What makes [university's] [major] program special?"
       - Comparison: "How does [university] compare to [peer university]?"
       - Application strategy: "What's the best application strategy for [university]?"
    
    4. **Greetings/General**:
       - "What colleges match my profile?"
       - "How can I improve my college applications?"
       - "Show me my college list progress"
       - "What reach schools should I target?"
    
    **ALWAYS**:
    - Focus on college planning, applications, or academic strategy
    - Make questions actionable and specific
    - Only mention universities from agent_response
    - Never ask the student to verify AI's work
    - Think: "What would help them get into college?" not "What would help me verify my output?"
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

1. **ProfileUpdateAgent** → Updates student profile (GPA, test scores, activities)
   - Use for: "Update my GPA to 3.9", "Add Tennis activity", "Change major to CS"
   - Delegate ALL update requests to this agent immediately.

2. **FitAnalysisAgent** → Get pre-computed fit analysis for a university
   - Input: university_id or university_name
   - Output: fit_category (SAFETY/TARGET/REACH/SUPER_REACH), match_percentage, factors
   - Use for: "What's my fit for MIT?", "Analyze my chances at Stanford"
   - CRITICAL: This always retrieves PRE-COMPUTED fits - never recalculates

3. **CollegeListAgent** → Manage student's college list
   - Operations: GET (show list), ADD (add university), REMOVE (remove university)
   - Output: Structured college list with university_id, university_name, status
   - Use for: "Show my list", "Add Harvard", "Remove UCLA"

4. **StudentProfileAgent** → Get student academic profile
   - Output: GPA, test scores, intended major, activities, awards
   - Use for: All personalized analysis
   - CRITICAL: NEVER ask user for this data - always fetch from profile

5. **UniversityKnowledgeAnalyst** → Search university knowledge base
   - Input: University name or search criteria
   - Output: University details, programs, admission stats, rankings
   - Use for: "Tell me about MIT", "Find schools with strong CS programs"

6. **DeepResearchAgent** → Web research for culture, vibe, recent news
   - Use for: "What's the culture like at Stanford?", "Recent news about UCLA"

**HOW TO ANSWER:**

1. **Profile Updates** → ProfileUpdateAgent
   - If user asks to change/update/add to their profile, ALWAYS call ProfileUpdateAgent.

2. **University Questions** → UniversityKnowledgeAnalyst
   - If found: Answer with KB data
   - If NOT found: Say "I don't have [university] in my knowledge base"

3. **Personalized Questions** ("my chances", "should I apply"):
   - Call StudentProfileAgent to get profile
   - Call UniversityKnowledgeAnalyst to get university data
   - Call FitAnalysisAgent to get pre-computed fit
   - Present combined analysis

4. **Fit Analysis** ("analyze fit", "my fit for X"):
   - Call FitAnalysisAgent with university_id
   - Present fit_category, match_percentage, and factors
   - Explain recommendations

5. **College List Operations**:
   - GET: Call CollegeListAgent
   - ADD: Call CollegeListAgent with university details
   - REMOVE: Call CollegeListAgent with university_id

6. **Recommendations** ("build a list", "find safety schools"):
   - Call StudentProfileAgent for context
   - Call FitAnalysisAgent for relevant fit categories
   - Present structured recommendations

7. **Deep Research** (culture, vibe, recent news) → DeepResearchAgent

**CRITICAL RULES:**
- NEVER try to calculate or recompute fits - ALWAYS use FitAnalysisAgent (pre-computed)
- NEVER ask user for profile data - ALWAYS use StudentProfileAgent
- For recommendations: Use FitAnalysisAgent to filter by category, NOT general search
- Sub-agents return structured outputs - parse them correctly
""",

    tools=[
        # Sub-agents with structured outputs
        AgentTool(ProfileUpdateAgent),
        AgentTool(FitAnalysisAgent),
        AgentTool(CollegeListAgent),
        AgentTool(StudentProfileAgent), 
        AgentTool(UniversityKnowledgeAnalyst),
        AgentTool(DeepResearchAgent),
        # Utility functions
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
