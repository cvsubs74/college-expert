"""
Student Insights Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 4 micro-agents in parallel to gather crowdsourced student insights,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash"

# ==============================================================================
# MICRO-AGENTS
# ==============================================================================

# Micro-agent 1: What it takes to get in
what_it_takes_micro = LlmAgent(
    name="WhatItTakesMicro",
    model=MODEL_NAME,
    description="Fetches key success factors from students.",
    instruction="""Research what it takes to get into {university_name}:

Find 3-5 key success factors from student perspectives.

Search: site:talk.collegeconfidential.com "{university_name}" accepted profile
Search: site:reddit.com "{university_name}" what got me in

OUTPUT (JSON array):
[
  "Strong academic record with challenging coursework",
  "Demonstrated passion in 1-2 areas rather than scattered activities",
  "Authentic essays that show self-reflection",
  "Leadership in meaningful extracurriculars"
]""",
    tools=[google_search],
    output_key="what_it_takes",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Common activities of admitted students
activities_micro = LlmAgent(
    name="ActivitiesMicro",
    model=MODEL_NAME,
    description="Fetches common activities of admitted students.",
    instruction="""Research common activities of admitted students at {university_name}:

Find 5+ common activities mentioned in accepted profiles.

Search: "{university_name}" accepted students activities extracurriculars
Search: site:talk.collegeconfidential.com "{university_name}" accepted

OUTPUT (JSON array):
[
  "Research experience",
  "Leadership in school clubs",
  "Community service/volunteering",
  "Varsity athletics",
  "Music/arts involvement"
]""",
    tools=[google_search],
    output_key="common_activities",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Essay tips
essay_tips_micro = LlmAgent(
    name="EssayTipsMicro",
    model=MODEL_NAME,
    description="Fetches essay tips for applicants.",
    instruction="""Research essay tips for {university_name}:

Find 3-5 specific essay tips or advice.

Search: "{university_name}" essays that worked
Search: "{university_name}" supplemental essay tips reddit

OUTPUT (JSON array):
[
  "Be specific about why this school - reference unique programs",
  "Show, don't tell - use concrete examples",
  "Avoid cliches about loving to learn",
  "Connect your interests to specific resources at the school"
]""",
    tools=[google_search],
    output_key="essay_tips",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 4: Red flags to avoid
red_flags_micro = LlmAgent(
    name="RedFlagsMicro",
    model=MODEL_NAME,
    description="Fetches application red flags to avoid.",
    instruction="""Research application red flags for {university_name}:

Find 3-5 things to avoid in applications.

Search: "{university_name}" application mistakes avoid
Search: "{university_name}" rejection reasons admissions

OUTPUT (JSON array):
[
  "Grade decline senior year",
  "Generic essays that could apply anywhere",
  "List of activities without depth or impact",
  "Poor rec letters from teachers who don't know you well"
]""",
    tools=[google_search],
    output_key="red_flags",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

insights_parallel_collector = ParallelAgent(
    name="InsightsParallelCollector",
    sub_agents=[
        what_it_takes_micro,
        activities_micro,
        essay_tips_micro,
        red_flags_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

insights_aggregator = LlmAgent(
    name="InsightsAggregator",
    model=MODEL_NAME,
    description="Aggregates all student insights outputs.",
    instruction="""Aggregate ALL student insights micro-agent outputs.

=== INPUT DATA ===
- what_it_takes: array of success factors
- common_activities: array of activities
- essay_tips: array of essay advice
- red_flags: array of things to avoid

=== OUTPUT STRUCTURE ===
{
  "student_insights": {
    "what_it_takes": <from what_it_takes>,
    "common_activities": <from common_activities>,
    "essay_tips": <from essay_tips>,
    "red_flags": <from red_flags>,
    "insights": []
  }
}

Use ( ) instead of {}.""",
    output_key="student_insights_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

student_insights_agent = SequentialAgent(
    name="StudentInsightsSequential",
    sub_agents=[insights_parallel_collector, insights_aggregator]
)
