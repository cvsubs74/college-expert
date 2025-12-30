"""
University Profile Collector - Main Agent Orchestrator

Uses refactored agents with ParallelAgent + micro-agent pattern
for focused, reliable data collection.
"""
import logging
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import AgentTool

# Import logging callbacks for detailed timing (optional - may not be deployed)
try:
    from .logging_callbacks import tool_logging_before, tool_logging_after
except ImportError:
    # Fallback: no-op callbacks if module not available
    tool_logging_before = None
    tool_logging_after = None

# Import all sub-agents (now using ParallelAgent pattern internally)
from .sub_agents import (
    state_initializer,
    university_name_extractor,
    strategy_agent,
    admissions_trends_agent,
    colleges_agent,
    majors_agent,
    application_agent,
    strategy_tactics_agent,
    scholarships_agent,
    credit_policies_agent,
    student_insights_agent,
    api_admissions_agent,      # Now uses ParallelAgent with 6 micro-agents
    api_financials_agent,      # Now uses ParallelAgent with 3 micro-agents
    api_outcomes_agent,        # Now uses ParallelAgent with 3 micro-agents
    api_demographics_agent,    # Now uses ParallelAgent with 4 micro-agents
    profile_builder_agent,
    file_saver_agent
)
from .sub_agents.gap_filler_agent import gap_filler_agent

logger = logging.getLogger(__name__)
MODEL_NAME = "gemini-2.5-flash"

# ==============================================================================
# PIPELINES
# ==============================================================================

# 1. Sequential Research Phase (for timing visibility)
# Changed from ParallelAgent to SequentialAgent to track timing per sub-agent
research_phase = ParallelAgent(
    name="ResearchPhase",
    sub_agents=[
        strategy_agent,              # LLM + google_search: Strategy/vibe
        api_admissions_agent,        # ParallelAgent: 6 micro-agents for admissions
        admissions_trends_agent,     # LLM + google_search: Historical trends
        api_demographics_agent,      # ParallelAgent: 4 micro-agents for demographics
        colleges_agent,              # LLM + google_search: College structure
        majors_agent,                # LLM + google_search: Major details
        application_agent,           # LLM + google_search: Deadlines
        strategy_tactics_agent,      # LLM + google_search: Application tips
        api_financials_agent,        # ParallelAgent: 3 micro-agents for financials
        scholarships_agent,          # LLM + google_search: Scholarships
        credit_policies_agent,       # LLM + google_search: AP/IB credits
        student_insights_agent,      # LLM + google_search: Student insights
        api_outcomes_agent           # ParallelAgent: 3 micro-agents for outcomes
    ]
)

# 2. Build and Save Pipeline
build_and_save_pipeline = SequentialAgent(
    name="BuildAndSavePipeline",
    sub_agents=[
        profile_builder_agent,
        file_saver_agent
    ]
)

# ==============================================================================
# ROOT AGENT
# ==============================================================================

input_tool = AgentTool(agent=university_name_extractor)
research_tool = AgentTool(
    agent=SequentialAgent(
        name="ResearchAndSave",
        sub_agents=[state_initializer, research_phase, build_and_save_pipeline]
    )
)
gap_fill_tool = AgentTool(agent=gap_filler_agent)

root_agent = LlmAgent(
    name="UniversityProfileCollector",
    model=MODEL_NAME,
    description="Orchestrates comprehensive university data collection with parallel micro-agents.",
    instruction="""You are a university data research coordinator. You can handle two types of requests:

=== TYPE 1: FULL RESEARCH ===
When asked to "Research [university name]" or collect data for a university:
1. Call UniversityNameExtractor to get the university name
2. Call ResearchAndSave to gather all data, build profile, and save it
3. Summarize key findings

=== TYPE 2: TARGETED GAP FILLING ===
When you see "TARGETED DATA SEARCH for [university name]" in the message:
1. This is a request to find SPECIFIC missing fields, not full research
2. Call GapFiller directly with the full user message
3. GapFiller will use Google Search to find only the specific missing data
4. Return the JSON data that GapFiller finds

HOW TO DETECT GAP FILLING:
- The message will contain "TARGETED DATA SEARCH" and list specific fields to find
- It will have sections like "### ADMISSIONS (X missing fields)"
- Do NOT run full research for these requests

EXAMPLE GAP FILLING REQUEST:
"TARGETED DATA SEARCH for Stanford University
=== MISSING DATA TO FIND ===
### ADMISSIONS (2 missing fields):
- Acceptance Rate
- Average GPA Admitted"

For this, call GapFiller, NOT ResearchAndSave.

=== TOOLS AVAILABLE ===
- UniversityNameExtractor: Gets clean university name from user input
- ResearchAndSave: Full research pipeline (takes 5-10 minutes)
- GapFiller: Quick targeted search for specific missing data (1-2 minutes)

Choose the right tool based on the request type.""",
    tools=[input_tool, research_tool, gap_fill_tool],
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)
