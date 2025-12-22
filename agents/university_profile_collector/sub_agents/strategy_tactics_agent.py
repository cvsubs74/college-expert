"""
Strategy Tactics Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather application gaming strategies,
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

# Micro-agent 1: Major selection tactics
major_tactics_micro = LlmAgent(
    name="MajorTacticsMicro",
    model=MODEL_NAME,
    description="Fetches major selection strategies.",
    instruction="""Research major selection tactics for {university_name}:

Find 3-5 strategies for choosing major strategically.

Search: "{university_name}" easier majors to get into
Search: "{university_name}" major selection strategy admission
Search: site:talk.collegeconfidential.com "{university_name}" major

OUTPUT (JSON array):
[
  "Apply to less competitive major if not set on CS/Engineering",
  "Consider undeclared for Letters and Science",
  "Research major-specific admit rates before applying",
  "Some majors have lower acceptance rates - know before applying"
]""",
    tools=[google_search],
    output_key="major_selection_tactics",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: College/school ranking tactics
ranking_tactics_micro = LlmAgent(
    name="RankingTacticsMicro",
    model=MODEL_NAME,
    description="Fetches college ranking strategies.",
    instruction="""Research college ranking tactics for {university_name}:

Find 3-5 strategies for ranking colleges (if applicable, e.g., UC system).

Search: "{university_name}" college ranking strategy
Search: "{university_name}" which college to apply to

OUTPUT (JSON array):
[
  "Rank colleges based on GE requirements not just prestige",
  "Consider housing quality in ranking decisions",
  "Look at 4-year graduation rates by college"
]

If not applicable (school doesn't have college system), return [].""",
    tools=[google_search],
    output_key="college_ranking_tactics",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Alternate major strategy
alternate_major_micro = LlmAgent(
    name="AlternateMajorMicro",
    model=MODEL_NAME,
    description="Fetches alternate major strategies.",
    instruction="""Research alternate major strategies for {university_name}:

Find advice on selecting backup/alternate majors.

Search: "{university_name}" alternate major strategy
Search: "{university_name}" backup major admission
Search: "{university_name}" change major after admission

OUTPUT (JSON):
{
  "alternate_major_strategy": "If applying to competitive major, list backup in different college. Example: if applying to CS in Engineering, list Cognitive Science as alternate.",
  "internal_transfer_difficulty": "Competitive internal transfer process for impacted majors"
}""",
    tools=[google_search],
    output_key="alternate_major",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

tactics_parallel_collector = ParallelAgent(
    name="TacticsParallelCollector",
    sub_agents=[
        major_tactics_micro,
        ranking_tactics_micro,
        alternate_major_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

tactics_aggregator = LlmAgent(
    name="TacticsAggregator",
    model=MODEL_NAME,
    description="Aggregates all tactics outputs.",
    instruction="""Aggregate ALL strategy tactics micro-agent outputs.

=== INPUT DATA ===
- major_selection_tactics: array of major selection strategies
- college_ranking_tactics: array of ranking strategies
- alternate_major: object with alternate major advice

=== OUTPUT STRUCTURE ===
{
  "application_strategy": {
    "major_selection_tactics": <from major_selection_tactics>,
    "college_ranking_tactics": <from college_ranking_tactics>,
    "alternate_major_strategy": <from alternate_major.alternate_major_strategy>
  }
}

If arrays are empty, use []. Never use null for arrays.
Use ( ) instead of {}.""",
    output_key="strategy_tactics_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

strategy_tactics_agent = SequentialAgent(
    name="StrategyTacticsSequential",
    sub_agents=[tactics_parallel_collector, tactics_aggregator]
)
