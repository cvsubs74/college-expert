"""
Strategy Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather metadata and strategic profile,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

MODEL_NAME = "gemini-2.5-flash"

# ==============================================================================
# MICRO-AGENTS
# ==============================================================================

# Micro-agent 1: Metadata (official name, location, type)
metadata_micro = LlmAgent(
    name="MetadataMicro",
    model=MODEL_NAME,
    description="Fetches basic university metadata.",
    instruction="""Research basic metadata for {university_name}:

1. official_name (str): Full official university name
2. city (str): City location
3. state (str): State name or abbreviation
4. type (str): "Public" or "Private"
5. last_updated (str): Today's date in YYYY-MM-DD format

Search: "{university_name} official" site:*.edu
Search: "{university_name} IPEDS institution profile"

CRITICAL: The "type" field MUST be INSIDE the "location" object, NOT at the metadata root level.

OUTPUT (JSON):
{
  "official_name": "Brown University",
  "location": {
    "city": "Providence",
    "state": "Rhode Island",
    "type": "Private"
  },
  "last_updated": "<today's date YYYY-MM-DD>",
  "report_source_files": []
}""",
    tools=[google_search],
    output_key="metadata",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)

# Micro-agent 2: Rankings and market position
rankings_micro = LlmAgent(
    name="RankingsMicro",
    model=MODEL_NAME,
    description="Fetches rankings and market position.",
    instruction="""Research rankings for {university_name}:

1. us_news_rank (int): Current US News National Universities rank (INTEGER)
2. market_position (str): "Elite Private", "Public Ivy", "Hidden Gem", etc.
3. executive_summary (str): 2-3 sentence overview

Search: site:usnews.com "{university_name}" ranking 2026
Search: "{university_name}" market position reputation

OUTPUT (JSON):
{
  "us_news_rank": 9,
  "market_position": "Elite Private",
  "executive_summary": "Brown University is an Ivy League research institution known for its open curriculum...",
  "admissions_philosophy": "Holistic review emphasizing intellectual curiosity"
}""",
    tools=[google_search],
    output_key="rankings",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)

# Micro-agent 3: Campus dynamics
campus_dynamics_micro = LlmAgent(
    name="CampusDynamicsMicro",
    model=MODEL_NAME,
    description="Fetches campus environment info.",
    instruction="""Research campus dynamics for {university_name}:

1. social_environment (str): Social atmosphere description from Niche
2. transportation_impact (str): How transport affects campus life
3. research_impact (str): Research opportunities and industry ties

Search: site:niche.com "{university_name}" campus life review
Search: "{university_name}" research opportunities undergraduate

OUTPUT (JSON):
{
  "campus_dynamics": {
    "social_environment": "Collaborative and intellectually vibrant atmosphere",
    "transportation_impact": "Walkable campus, RIPTA bus access",
    "research_impact": "Strong undergraduate research opportunities"
  }
}""",
    tools=[google_search],
    output_key="campus_dynamics",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)

# Micro-agent 4: Analyst takeaways
analyst_takeaways_micro = LlmAgent(
    name="AnalystTakeawaysMicro",
    model=MODEL_NAME,
    description="Generates strategic analyst takeaways.",
    instruction="""Generate 3+ strategic analyst takeaways for {university_name}:

For each takeaway:
- category (str): "Selectivity", "Value", "Academic", "Culture"
- insight (str): Key finding
- implication (str): What this means for applicants

Search: "{university_name}" admissions strategy
Search: "{university_name}" unique advantages

OUTPUT (JSON array):
[
  {
    "category": "Selectivity",
    "insight": "Extremely competitive with sub-6% acceptance rate",
    "implication": "Apply ED to maximize chances"
  },
  {
    "category": "Academic",
    "insight": "Open curriculum allows maximum flexibility",
    "implication": "Emphasize intellectual curiosity in essays"
  },
  {
    "category": "Culture",
    "insight": "Known for collaborative rather than competitive environment",
    "implication": "Highlight collaborative projects and teamwork"
  }
]

CRITICAL: NEVER return a simple list of strings like ["insight1", "insight2"]. 
ALWAYS return an array of objects with category, insight, implication keys as shown above.""",
    tools=[google_search],
    output_key="analyst_takeaways",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

strategy_parallel_collector = ParallelAgent(
    name="StrategyParallelCollector",
    sub_agents=[
        metadata_micro,
        rankings_micro,
        campus_dynamics_micro,
        analyst_takeaways_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

strategy_aggregator = LlmAgent(
    name="StrategyAggregator",
    model=MODEL_NAME,
    description="Aggregates all strategy micro-agent outputs.",
    instruction="""Aggregate ALL micro-agent outputs into final strategy structure.

=== INPUT DATA ===
- metadata: official_name, location, last_updated
- rankings: us_news_rank, market_position, executive_summary, admissions_philosophy
- campus_dynamics: social_environment, transportation_impact, research_impact
- analyst_takeaways: array of takeaways

=== OUTPUT STRUCTURE ===
{
  "metadata": <from metadata>,
  "strategic_profile": {
    "executive_summary": <from rankings>,
    "market_position": <from rankings>,
    "admissions_philosophy": <from rankings>,
    "us_news_rank": <from rankings - INTEGER>,
    "analyst_takeaways": <from analyst_takeaways array>,
    "campus_dynamics": <from campus_dynamics>
  }
}

CRITICAL: us_news_rank must be INTEGER. Use ( ) instead of {}.""",
    output_key="strategy_output"
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

strategy_agent = SequentialAgent(
    name="StrategySequential",
    sub_agents=[strategy_parallel_collector, strategy_aggregator]
)
