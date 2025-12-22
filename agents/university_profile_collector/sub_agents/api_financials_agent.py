"""
API Financials Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather all financial data,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

try:
    from ..api_tools import get_college_scorecard_data, get_ipeds_tuition_data
except ImportError:
    from api_tools import get_college_scorecard_data, get_ipeds_tuition_data

MODEL_NAME = "gemini-2.5-flash"

# ==============================================================================
# MICRO-AGENTS: Each focuses on a specific piece of financial data
# ==============================================================================

# Micro-agent 1: Tuition and Cost of Attendance
tuition_coa_micro = LlmAgent(
    name="TuitionCOAMicro",
    model=MODEL_NAME,
    description="Fetches tuition and cost of attendance.",
    instruction="""Research tuition/COA for {university_name}:

1. tuition_model (str): "Tuition Stability Plan", "Annual Increase (~3%)", "Unified"
2. academic_year (str): "2024-2025"
3. For IN-STATE: tuition, total_coa, housing (floats)
4. For OUT-OF-STATE: tuition, total_coa (floats)

Search: "{university_name} cost of attendance 2024-2025"
Search: "{university_name} tuition and fees"

OUTPUT (JSON):
{
  "tuition_model": "Annual Increase (~3%)",
  "academic_year": "2024-2025",
  "in_state": {"tuition": 14500.0, "total_coa": 36000.0, "housing": 15000.0},
  "out_of_state": {"tuition": 46000.0, "total_coa": 68000.0}
}

For private schools, in_state and out_of_state are usually the same.""",
    tools=[google_search],
    output_key="tuition_coa",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Financial Aid Philosophy and Statistics
financial_aid_micro = LlmAgent(
    name="FinancialAidMicro",
    model=MODEL_NAME,
    description="Fetches financial aid data.",
    instruction="""Research financial aid for {university_name}:

1. aid_philosophy (str): "Need-Blind", "Need-Aware", "Meets 100% of Need"
2. average_need_based_aid (float): Average need-based package dollars
3. average_merit_aid (float): Average merit scholarship dollars
4. percent_receiving_aid (float): % receiving any aid (e.g., 65.0)
5. meets_full_need (bool): Whether school meets 100% demonstrated need

Search: "{university_name} financial aid statistics"
Search: "{university_name} average financial aid package"

OUTPUT (JSON):
{
  "aid_philosophy": "Need-Blind / Meets 100% of Need",
  "average_need_based_aid": 55000.0,
  "average_merit_aid": 15000.0,
  "percent_receiving_aid": 52.0,
  "meets_full_need": true,
  "notes": "No loans for families under $75K"
}""",
    tools=[google_search],
    output_key="financial_aid",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Named Scholarships
scholarships_micro = LlmAgent(
    name="ScholarshipsMicro",
    model=MODEL_NAME,
    description="Fetches 3-5 major scholarships.",
    instruction="""Research TOP 3-5 scholarships at {university_name}:

For each scholarship:
- name (str): Scholarship name
- type (str): "Merit", "Need-Based", "Full-Ride"
- amount (str): "$10,000/year", "Full Tuition", etc.
- eligibility (str): Key requirements
- application_method (str): "Automatic Consideration", "Separate Application"

Search: "{university_name} scholarships merit aid"
Search: "{university_name} full ride scholarship"

OUTPUT (JSON array):
[
  {
    "name": "Regents Scholarship",
    "type": "Full-Ride",
    "amount": "Full Tuition + Stipend",
    "eligibility": "Top 1% of applicants",
    "application_method": "Automatic Consideration"
  }
]""",
    tools=[google_search],
    output_key="scholarships",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT: Runs all micro-agents simultaneously
# ==============================================================================

financials_parallel_collector = ParallelAgent(
    name="FinancialsParallelCollector",
    sub_agents=[
        tuition_coa_micro,
        financial_aid_micro,
        scholarships_micro
    ]
)

# ==============================================================================
# AGGREGATOR: Combines all micro-agent outputs into final structure
# ==============================================================================

financials_aggregator = LlmAgent(
    name="FinancialsAggregator",
    model=MODEL_NAME,
    description="Aggregates all financial micro-agent outputs.",
    instruction="""Aggregate ALL micro-agent outputs into final financials structure.

=== INPUT DATA (from session state) ===
- tuition_coa: tuition_model, academic_year, in_state, out_of_state costs
- financial_aid: aid_philosophy, average aid amounts, meets_full_need
- scholarships: array of scholarship objects

=== OUTPUT STRUCTURE ===
{
  "tuition_model": <from tuition_coa>,
  "cost_of_attendance_breakdown": {
    "academic_year": <from tuition_coa>,
    "in_state": <from tuition_coa>,
    "out_of_state": <from tuition_coa>
  },
  "financial_aid_philosophy": <from financial_aid.aid_philosophy>,
  "average_need_based_aid": <from financial_aid>,
  "average_merit_aid": <from financial_aid>,
  "percent_receiving_aid": <from financial_aid>,
  "scholarships": <from scholarships array>
}

RULES:
1. Preserve ALL data from micro-agents
2. Use null for missing data
3. Output valid JSON only""",
    output_key="financials_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT: Sequential flow of parallel collection -> aggregation
# ==============================================================================

api_financials_agent = SequentialAgent(
    name="ApiFinancialsSequential",
    sub_agents=[financials_parallel_collector, financials_aggregator]
)
