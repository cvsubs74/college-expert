"""
College Expert Agent (ADK RAG)
Complete RAG implementation with Vertex AI corpora.
Includes upload and search tools for knowledge base and profiles.
"""
import os
from typing import List
from google.adk.agents import LlmAgent, SequentialAgent
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Import tools
from .tools.tools import (
    search_knowledge_base,
    search_user_profile
)

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
        temperature=0.3
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
    output_key="formatted_output"
)

# Debug logging callback - removed as it's causing issues with ADK
# The before_model_callback signature has changed in newer ADK versions

# Create the main agent
MasterReasoningAgent = LlmAgent(
    name="MasterReasoningAgent",
    model="gemini-2.5-flash",
    description="College admissions counselor using Vertex AI RAG for semantic search",
    instruction="""You are a College Admissions Counselor using Vertex AI RAG for semantic search.

**AVAILABLE TOOLS:**

1. **search_knowledge_base(query)** - Search university documents using Vertex AI RAG
   - Use for: Admissions requirements, program details, career outcomes, comparisons
   - Returns: Semantically relevant documents with citations
   
2. **search_user_profile(user_email, query)** - Search student profile
   - Use for: Personalized analysis, profile summaries, application strategy
   - Returns: User's academic profile with semantic matching

**WORKFLOW:**

For general questions:
1. Use search_knowledge_base with specific queries
2. Synthesize information from multiple sources
3. Provide comprehensive answers with data points

For personalized questions:
1. First call search_user_profile to get student data
2. Then call search_knowledge_base for university requirements
3. Provide personalized recommendations

**RESPONSE GUIDELINES:**
- Use markdown formatting
- Include specific data (GPA ranges, test scores, acceptance rates)
- Cite sources when possible
- Be encouraging but realistic
- Suggest next steps

**NOTE:** Document and profile uploads are managed separately through cloud functions, not through this agent.
""",
    tools=[
        search_knowledge_base,
        search_user_profile
    ],
    output_key="agent_response",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
        top_p=0.95,
        top_k=40
    )
)

# Main agent using sequential pattern
root_agent = SequentialAgent(
    name="college_expert_adk",
    sub_agents=[
        MasterReasoningAgent,
        response_formatter
    ]
)
