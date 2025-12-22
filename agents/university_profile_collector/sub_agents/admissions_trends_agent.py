"""
Admissions Trends Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 2 micro-agents in parallel to gather historical trends and waitlist data,
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

# Micro-agent 1: Historical admissions trends (5 years)
longitudinal_micro = LlmAgent(
    name="LongitudinalMicro",
    model=MODEL_NAME,
    description="Fetches 5 years of historical admissions data.",
    instruction="""Research 5 years of admissions data for {university_name}:

For each year (2021-2025), find:
- year (int): 2025, 2024, 2023, 2022, 2021
- cycle_name (str): "Class of 2029", etc.
- applications_total (int)
- admits_total (int)
- enrolled_total (int)
- acceptance_rate_overall (float): As NUMBER
- yield_rate (float): enrolled/admits as %
- notes (str): Notable events

Search: "{university_name}" Common Data Set 2023-2024
Search: "{university_name}" acceptance rate history 2020-2024

OUTPUT (JSON array, 5 years):
[
  {
    "year": 2025,
    "cycle_name": "Class of 2029",
    "applications_total": 47813,
    "admits_total": 3325,
    "enrolled_total": null,
    "acceptance_rate_overall": 6.95,
    "yield_rate": null,
    "notes": ""
  }
]""",
    tools=[google_search],
    output_key="longitudinal_trends",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Waitlist statistics per year
waitlist_micro = LlmAgent(
    name="WaitlistMicro",
    model=MODEL_NAME,
    description="Fetches waitlist statistics.",
    instruction="""Research waitlist statistics for {university_name}:

For each available year, find (from CDS Section C2):
- year (int)
- offered_spots (int): Students offered waitlist
- accepted_spots (int): Students who accepted
- admitted_from_waitlist (int): Admitted from waitlist
- waitlist_admit_rate (float): admitted/accepted as %
- is_waitlist_ranked (bool)

Search: "{university_name}" Common Data Set Section C2 waitlist
Search: "{university_name}" waitlist statistics 2024

OUTPUT (JSON object by year):
{
  "2024": {
    "year": 2024,
    "offered_spots": 3704,
    "accepted_spots": 2288,
    "admitted_from_waitlist": 118,
    "waitlist_admit_rate": 5.16,
    "is_waitlist_ranked": false
  },
  "2023": {
    "year": 2023,
    "offered_spots": 4540,
    "accepted_spots": 2840,
    "admitted_from_waitlist": 73,
    "waitlist_admit_rate": 2.57,
    "is_waitlist_ranked": false
  }
}

Use null for unavailable data.""",
    tools=[google_search],
    output_key="waitlist_stats",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

trends_parallel_collector = ParallelAgent(
    name="TrendsParallelCollector",
    sub_agents=[
        longitudinal_micro,
        waitlist_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

trends_aggregator = LlmAgent(
    name="TrendsAggregator",
    model=MODEL_NAME,
    description="Aggregates trends and waitlist data.",
    instruction="""Aggregate longitudinal trends with waitlist stats.

=== INPUT DATA ===
- longitudinal_trends: array of 5 years of admissions data
- waitlist_stats: object with waitlist stats by year

=== AGGREGATION RULES ===
For each year in longitudinal_trends:
1. Look up waitlist_stats for that year
2. Add "waitlist_stats" field to that year's entry

=== OUTPUT STRUCTURE ===
{
  "longitudinal_trends": [
    {
      "year": 2025,
      "cycle_name": "Class of 2029",
      "applications_total": <from longitudinal>,
      "admits_total": <from longitudinal>,
      "enrolled_total": <from longitudinal>,
      "acceptance_rate_overall": <from longitudinal>,
      "yield_rate": <from longitudinal>,
      "waitlist_stats": <merged from waitlist_stats for this year>,
      "notes": <from longitudinal>
    }
  ]
}

Use ( ) instead of {}.""",
    output_key="admissions_trends_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

admissions_trends_agent = SequentialAgent(
    name="AdmissionsTrendsSequential",
    sub_agents=[trends_parallel_collector, trends_aggregator]
)
