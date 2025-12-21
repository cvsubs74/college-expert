"""
University Profile Collector - Main Agent Orchestrator

Uses refactored agents with ParallelAgent + micro-agent pattern
for focused, reliable data collection.
"""
import logging
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import AgentTool

# Import logging callbacks for detailed timing
from logging_callbacks import tool_logging_before, tool_logging_after

# Import all sub-agents (now using ParallelAgent pattern internally)
from sub_agents import (
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

logger = logging.getLogger(__name__)
MODEL_NAME = "gemini-2.5-flash"

# ==============================================================================
# PIPELINES
# ==============================================================================

# 1. Sequential Research Phase (for timing visibility)
# Changed from ParallelAgent to SequentialAgent to track timing per sub-agent
research_phase = SequentialAgent(
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

root_agent = LlmAgent(
    name="UniversityProfileCollector",
    model=MODEL_NAME,
    description="Orchestrates comprehensive university data collection with parallel micro-agents.",
    instruction="""When asked to research a university:
1. Call UniversityNameExtractor to get the university name
2. Call ResearchAndSave to gather data, build profile, and save it.

Each API agent now uses focused micro-agents running in parallel:
- api_admissions_agent: 6 micro-agents (rates, ED stats, GPA, test scores, int'l, state)
- api_demographics_agent: 4 micro-agents (first-gen, geographic, gender, racial)
- api_financials_agent: 3 micro-agents (tuition/COA, aid, scholarships)
- api_outcomes_agent: 3 micro-agents (earnings, employers, retention)

Confirm save and summarize key findings including:
- Acceptance rate and admission stats
- Top employers and median earnings (ROI)
- Retention and graduation rates""",
    tools=[input_tool, research_tool],
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)

