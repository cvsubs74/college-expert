"""
Colleges Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather academic structure info,
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

# Micro-agent 1: List of undergraduate colleges/schools
colleges_list_micro = LlmAgent(
    name="CollegesListMicro",
    model=MODEL_NAME,
    description="Fetches list of undergraduate colleges/schools.",
    instruction="""Find ALL undergraduate colleges/schools at {university_name}:

⚠️ CRITICAL: Use the CURRENT academic catalog only (the most recent available).
If a page shows "ARCHIVED CATALOGUE", search for the current version.

For each college/school:
- name (str): Full name
- admissions_model (str): "Direct Admit", "Pre-Major", "Lottery"
- is_restricted_or_capped (bool): Whether admission is restricted

MUST FIND ALL including:
- School of Engineering / Applied Science
- College of Arts & Sciences
- School of Business (if undergrad)
- School of Nursing (if undergrad)
- School of Music/Arts (if undergrad)

Search: "{university_name}" list of undergraduate schools colleges current
Search: "{university_name}" all undergraduate programs current catalog

OUTPUT (JSON array):
[
  {
    "name": "School of Engineering",
    "admissions_model": "Direct Admit",
    "is_restricted_or_capped": true
  },
  {
    "name": "College of Arts and Sciences",
    "admissions_model": "Pre-Major",
    "is_restricted_or_capped": false
  }
]""",
    tools=[google_search],
    output_key="colleges_list",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Housing and student archetypes
housing_micro = LlmAgent(
    name="HousingMicro",
    model=MODEL_NAME,
    description="Fetches housing and student archetype info.",
    instruction="""Research housing and student archetypes for {university_name}:

For each college/school, find:
- housing_profile (str): Dorm quality, facilities
- student_archetype (str): Typical student type
- strategic_fit_advice (str): Who should apply

Search: site:niche.com "{university_name}" housing dorms review
Search: "{university_name}" residential colleges

OUTPUT (JSON):
{
  "housing_info": [
    {
      "college_name": "School of Engineering",
      "housing_profile": "Modern dorms with maker spaces",
      "student_archetype": "Ambitious problem-solvers",
      "strategic_fit_advice": "Strong STEM background required"
    }
  ]
}""",
    tools=[google_search],
    output_key="housing_info",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Minors and certificates
minors_micro = LlmAgent(
    name="MinorsMicro",
    model=MODEL_NAME,
    description="Fetches minors and certificate programs.",
    instruction="""Find available minors and certificate programs at {university_name}:

Search: "{university_name}" undergraduate minors list
Search: "{university_name}" certificate programs undergrad

OUTPUT (JSON array):
[
  "Data Science Minor",
  "Entrepreneurship Certificate",
  "Writing Minor",
  "Computer Science Minor"
]

Include 5-10 most popular/notable minors and certificates.""",
    tools=[google_search],
    output_key="minors_certificates",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

colleges_parallel_collector = ParallelAgent(
    name="CollegesParallelCollector",
    sub_agents=[
        colleges_list_micro,
        housing_micro,
        minors_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

colleges_aggregator = LlmAgent(
    name="CollegesAggregator",
    model=MODEL_NAME,
    description="Aggregates all colleges micro-agent outputs.",
    instruction="""Aggregate ALL micro-agent outputs into final academic_structure.

=== INPUT DATA ===
- colleges_list: array of colleges with basic info
- housing_info: array with housing profiles and archetypes
- minors_certificates: array of minor/certificate names

=== AGGREGATION RULES ===
1. Merge housing_info into colleges_list by matching college_name
2. Add "majors": [] to each college (MajorsAgent fills this)

=== OUTPUT STRUCTURE ===
{
  "academic_structure": {
    "structure_type": "Colleges" or "Schools",
    "colleges": [
      {
        "name": <from colleges_list>,
        "admissions_model": <from colleges_list>,
        "is_restricted_or_capped": <from colleges_list>,
        "housing_profile": <merged from housing_info>,
        "student_archetype": <merged from housing_info>,
        "strategic_fit_advice": <merged from housing_info>,
        "majors": []
      }
    ],
    "minors_certificates": <from minors_certificates>
  }
}

Use ( ) instead of {}.""",
    output_key="colleges_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

colleges_agent = SequentialAgent(
    name="CollegesSequential",
    sub_agents=[colleges_parallel_collector, colleges_aggregator]
)
