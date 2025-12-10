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
from .tools.tools import calculate_college_fit, recalculate_all_fits, get_college_list, list_valid_university_ids, add_college_to_list
from pydantic import BaseModel, Field

# Import sub-agents
from .sub_agents.student_profile_agent.agent import StudentProfileAgent
from .sub_agents.university_knowledge_analyst.agent import UniversityKnowledgeAnalyst
from .sub_agents.deep_research_agent.agent import DeepResearchAgent
from .sub_agents.profile_preloader_agent.agent import ProfileLoaderAgent # Import new agent

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

# Create the main reasoning agent
MasterReasoningAgent = LlmAgent(
    name="MasterReasoningAgent",
    model="gemini-2.0-flash",
    description="College admissions counseling expert using hybrid search on structured university profiles",
    instruction="""You are a College Admissions Counselor with access to a university knowledge base.

**PROFILE & EMAIL HANDLING:**
The user's email is automatically handled and their profile is PRE-LOADED into your tools.
- You do NOT need to ask for the email.
- You do NOT need to verify the profile.
- Just call the tools (StudentProfileAgent, calculate_college_fit) and they will automatically use the loaded profile using the context.

**HOW TO ANSWER:**

1. **University Questions** → Search KB using UniversityKnowledgeAnalyst
   - If found: Answer with KB data
   - If NOT found: Say "I don't have [university] in my knowledge base" and offer to search for similar schools

2. **Personalized Questions** ("my chances", "should I apply", "based on my profile"):
   → Step 1: StudentProfileAgent(email="auto") - the tool will pick up the cached profile
   → Step 2: UniversityKnowledgeAnalyst(university name)
   → Step 3: Answer by comparing profile to university data

3. **Fit Analysis** ("analyze fit", "my fit for X", "what are my chances at X"):
   → Step 1: UniversityKnowledgeAnalyst(university name) - to confirm it exists and get details
   → Step 2: If found in KB, extract university_id from the result
   → Step 3: calculate_college_fit(email="auto", university_id, major)
   → Step 4: Present category, percentage, factor breakdown, recommendations
   
   IMPORTANT: For acronyms (MIT, UCLA, UCB), the KB search will find them! 
   Always search first - don't assume a university isn't in the KB.

4. **College List** → get_college_list(email="auto")

5. **Add to List** ("add X to my list", "save this college"):
   → add_college_to_list(email="auto", university_name, major)
   → This will automatically calculate fit and save it.

6. **Strategic Questions** ("what should I emphasize", "safety schools", "balanced list"):
   → Get profile with StudentProfileAgent
   → Search relevant universities with UniversityKnowledgeAnalyst  
   → Provide specific recommendations based on profile + KB data
   → NEVER just ask for more info - give your best answer

7. **Deep Research** ("vibe", "culture", "recent news") → DeepResearchAgent

**RULES:**
- ALWAYS answer the question.
- Profile data is already loaded. Use it!
- For fit analysis: ALWAYS search KB first to verify university exists
- Acronyms work! MIT, UCLA, UCB, USC are all searchable
- If data is missing from KB, say so clearly and offer alternatives

**IMPORTANT:**
- The email and profile are handled by the system.
- Focus on ADVICE and ANALYSIS.
""",
    tools=[
        AgentTool(StudentProfileAgent), 
        AgentTool(UniversityKnowledgeAnalyst),
        AgentTool(DeepResearchAgent),
        FunctionTool(calculate_college_fit),
        FunctionTool(recalculate_all_fits),
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
