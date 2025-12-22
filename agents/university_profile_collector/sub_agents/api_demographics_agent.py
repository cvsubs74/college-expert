"""
API Demographics Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 4 micro-agents in parallel to gather all demographics data,
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
# MICRO-AGENTS: Each focuses on a specific piece of demographics data
# ==============================================================================

# Micro-agent 1: First-generation and legacy percentages
first_gen_legacy_micro = LlmAgent(
    name="FirstGenLegacyMicro",
    model=MODEL_NAME,
    description="Fetches first-gen and legacy percentages.",
    instruction="""Research first-generation and legacy data for {university_name}:

1. first_gen_percentage (float): % first-generation college students (e.g., 19.0)
2. legacy_percentage (float): % legacy students (alumni children) (e.g., 10.5)

Search: "{university_name} first generation students"
Search: "{university_name} legacy admissions"

OUTPUT (JSON):
{
  "first_gen_percentage": 19.0,
  "legacy_percentage": 10.5,
  "notes": "Legacy defined as alumni children"
}

Use null if unavailable.""",
    tools=[google_search],
    output_key="first_gen_legacy",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Geographic distribution
geographic_micro = LlmAgent(
    name="GeographicMicro",
    model=MODEL_NAME,
    description="Fetches geographic distribution.",
    instruction="""Research geographic distribution at {university_name}:

Return a list of regions/states with percentages:
- Include top 5-10 sending states
- Include "International" percentage
- For public schools: in-state vs out-of-state critical

Search: "{university_name} student demographics by state"
Search: "{university_name} where do students come from"

OUTPUT (JSON array):
[
  {"region": "California", "percentage": 25.0},
  {"region": "New York", "percentage": 12.0},
  {"region": "International", "percentage": 15.0}
]""",
    tools=[google_search],
    output_key="geographic_breakdown",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Gender breakdown with detailed stats
gender_micro = LlmAgent(
    name="GenderMicro",
    model=MODEL_NAME,
    description="Fetches gender-based admissions stats.",
    instruction="""Research gender breakdown for {university_name}:

For each gender (men, women), get:
- applicants: Number of applicants
- admits: Number admitted
- acceptance_rate: As NUMBER (e.g., 6.86)
- note: Context

Search: "{university_name} admissions by gender"
Search: "{university_name} Common Data Set Section C1"

OUTPUT (JSON):
{
  "men": {"applicants": 19666, "admits": 1350, "acceptance_rate": 6.86, "note": ""},
  "women": {"applicants": 31650, "admits": 1336, "acceptance_rate": 4.22, "note": ""},
  "non_binary": null
}""",
    tools=[google_search],
    output_key="gender_breakdown",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 4: Racial/ethnic breakdown (IPEDS categories)
racial_micro = LlmAgent(
    name="RacialMicro",
    model=MODEL_NAME,
    description="Fetches racial/ethnic breakdown.",
    instruction="""Research racial/ethnic demographics for {university_name}:

All values as NUMBERS (percentages):
- white
- black_african_american
- hispanic_latino
- asian
- native_american_alaskan
- pacific_islander
- two_or_more_races
- unknown
- non_resident_alien (international students)

Search: "{university_name} student demographics race"
Search: "{university_name} diversity statistics"

OUTPUT (JSON):
{
  "white": 39.84,
  "black_african_american": 6.84,
  "hispanic_latino": 11.95,
  "asian": 16.51,
  "native_american_alaskan": 0.14,
  "pacific_islander": 0.13,
  "two_or_more_races": 7.46,
  "unknown": 1.41,
  "non_resident_alien": 15.71
}""",
    tools=[google_search],
    output_key="racial_breakdown",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT: Runs all micro-agents simultaneously
# ==============================================================================

demographics_parallel_collector = ParallelAgent(
    name="DemographicsParallelCollector",
    sub_agents=[
        first_gen_legacy_micro,
        geographic_micro,
        gender_micro,
        racial_micro
    ]
)

# ==============================================================================
# AGGREGATOR: Combines all micro-agent outputs into final structure
# ==============================================================================

demographics_aggregator = LlmAgent(
    name="DemographicsAggregator",
    model=MODEL_NAME,
    description="Aggregates all demographics micro-agent outputs.",
    instruction="""Aggregate ALL micro-agent outputs into final demographics structure.

=== INPUT DATA (from session state) ===
- first_gen_legacy: first_gen_percentage, legacy_percentage
- geographic_breakdown: array of regions with percentages
- gender_breakdown: men/women/non_binary stats
- racial_breakdown: IPEDS racial categories

=== OUTPUT STRUCTURE ===
{
  "demographics": {
    "first_gen_percentage": <from first_gen_legacy>,
    "legacy_percentage": <from first_gen_legacy>,
    "geographic_breakdown": <from geographic_breakdown array>,
    "gender_breakdown": <from gender_breakdown>,
    "racial_breakdown": <from racial_breakdown>,
    "religious_affiliation": null
  }
}

RULES:
1. All percentages as NUMBERS
2. Preserve ALL data from micro-agents
3. Use null for missing data
4. Output valid JSON only""",
    output_key="admitted_profile_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT: Sequential flow of parallel collection -> aggregation
# ==============================================================================

api_demographics_agent = SequentialAgent(
    name="ApiDemographicsSequential",
    sub_agents=[demographics_parallel_collector, demographics_aggregator]
)
