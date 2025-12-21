"""
API Outcomes Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather all outcomes data,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

try:
    from ..api_tools import get_college_scorecard_data
except ImportError:
    from api_tools import get_college_scorecard_data

MODEL_NAME = "gemini-2.5-flash-lite"

# ==============================================================================
# MICRO-AGENTS: Each focuses on a specific piece of outcomes data
# ==============================================================================

# Micro-agent 1: Earnings data
earnings_micro = LlmAgent(
    name="EarningsMicro",
    model=MODEL_NAME,
    description="Fetches median earnings data.",
    instruction="""Research earnings outcomes for {university_name}:

1. median_earnings_10yr (int): Median earnings 10 years after enrollment
   - College Scorecard is authoritative source
   - Example: 87600 (dollars, no commas)
2. employment_rate_2yr (float): % employed 2 years after graduation
3. median_earnings_6yr (int): Earlier data point (optional)

Search: "{university_name} College Scorecard earnings"
Search: "{university_name} median salary after graduation"

OUTPUT (JSON):
{
  "median_earnings_10yr": 87600,
  "employment_rate_2yr": 95.0,
  "median_earnings_6yr": 72000,
  "notes": "Top 10% nationally"
}""",
    tools=[google_search],
    output_key="earnings",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Top employers
employers_micro = LlmAgent(
    name="EmployersMicro",
    model=MODEL_NAME,
    description="Fetches top employers list.",
    instruction="""Research top 7-10 employers hiring from {university_name}:

Look for:
- Career center reports
- LinkedIn alumni data
- Major tech: Google, Apple, Amazon, Microsoft, Meta
- Consulting: McKinsey, BCG, Bain, Deloitte
- Finance: Goldman Sachs, JPMorgan, Morgan Stanley

Search: "{university_name} top employers graduates"
Search: "{university_name} where do graduates work"

OUTPUT (JSON array of company names):
[
  "Google",
  "Goldman Sachs",
  "McKinsey & Company",
  "Amazon",
  "Deloitte",
  "Morgan Stanley",
  "Apple",
  "Microsoft"
]""",
    tools=[google_search],
    output_key="top_employers",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Retention and graduation rates
retention_micro = LlmAgent(
    name="RetentionMicro",
    model=MODEL_NAME,
    description="Fetches retention and graduation rates.",
    instruction="""Research retention/graduation for {university_name}:

1. freshman_retention_rate (float): % freshmen returning for sophomore year
2. graduation_rate_4_year (float): % graduating in 4 years
3. graduation_rate_6_year (float): % graduating in 6 years
4. grad_school_rate (float): % pursuing graduate school
5. loan_default_rate (float): Federal loan default rate

Search: "{university_name} retention rate graduation rate"
Search: "{university_name} Common Data Set Section B"

OUTPUT (JSON):
{
  "freshman_retention_rate": 98.0,
  "graduation_rate_4_year": 87.0,
  "graduation_rate_6_year": 96.0,
  "grad_school_rate": 35.0,
  "loan_default_rate": 1.2,
  "notes": "Top 5% nationally"
}""",
    tools=[google_search],
    output_key="retention",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT: Runs all micro-agents simultaneously
# ==============================================================================

outcomes_parallel_collector = ParallelAgent(
    name="OutcomesParallelCollector",
    sub_agents=[
        earnings_micro,
        employers_micro,
        retention_micro
    ]
)

# ==============================================================================
# AGGREGATOR: Combines all micro-agent outputs into final structure
# ==============================================================================

outcomes_aggregator = LlmAgent(
    name="OutcomesAggregator",
    model=MODEL_NAME,
    description="Aggregates all outcomes micro-agent outputs.",
    instruction="""Aggregate ALL micro-agent outputs into final outcomes structure.

=== INPUT DATA (from session state) ===
- earnings: median_earnings_10yr, employment_rate_2yr
- top_employers: array of company names
- retention: freshman_retention_rate, graduation rates, grad_school_rate

=== OUTPUT STRUCTURE ===
{
  "outcomes": {
    "median_earnings_10yr": <from earnings>,
    "employment_rate_2yr": <from earnings>,
    "top_employers": <from top_employers array>,
    "grad_school_rate": <from retention>,
    "loan_default_rate": <from retention>
  },
  "student_retention": {
    "freshman_retention_rate": <from retention>,
    "graduation_rate_4_year": <from retention>,
    "graduation_rate_6_year": <from retention>
  }
}

RULES:
1. Preserve ALL data from micro-agents
2. Use null for missing data
3. Output valid JSON only""",
    output_key="outcomes_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT: Sequential flow of parallel collection -> aggregation
# ==============================================================================

api_outcomes_agent = SequentialAgent(
    name="ApiOutcomesSequential",
    sub_agents=[outcomes_parallel_collector, outcomes_aggregator]
)
