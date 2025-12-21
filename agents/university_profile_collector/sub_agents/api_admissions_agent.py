"""
API Admissions Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 6 micro-agents in parallel to gather all admissions data,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

try:
    from ..api_tools import get_college_scorecard_data, get_ipeds_admissions_data
except ImportError:
    from api_tools import get_college_scorecard_data, get_ipeds_admissions_data

MODEL_NAME = "gemini-2.5-flash-lite"

# ==============================================================================
# MICRO-AGENTS: Each focuses on a specific piece of admissions data
# ==============================================================================

# Micro-agent 1: Current acceptance rates and test policy
current_rates_micro = LlmAgent(
    name="CurrentRatesMicro",
    model=MODEL_NAME,
    description="Fetches current acceptance rates and test policy.",
    instruction="""Research ONLY these 5 fields for {university_name}:

1. overall_acceptance_rate (float): As NUMBER (e.g., 5.65 not "5.65%")
2. is_test_optional (bool): Whether tests are optional
3. test_policy_details (str): Full description of test policy
4. admits_class_size (int): Number admitted in most recent cycle
5. transfer_acceptance_rate (float): Transfer acceptance rate as NUMBER

Search: "{university_name} acceptance rate 2024", "{university_name} test policy"

OUTPUT (JSON only):
{
  "overall_acceptance_rate": 5.65,
  "is_test_optional": false,
  "test_policy_details": "SAT or ACT required since 2024",
  "admits_class_size": 2418,
  "transfer_acceptance_rate": 7.2
}""",
    tools=[google_search],
    output_key="current_rates",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: Early Decision/Early Action statistics
early_decision_micro = LlmAgent(
    name="EarlyDecisionMicro",
    model=MODEL_NAME,
    description="Fetches ED/EA statistics.",
    instruction="""Research Early Decision/Early Action for {university_name}:

For EACH early plan (ED, EA, ED2, REA), get:
- plan_type: "ED", "EA", "ED2", or "REA"
- applications: Number received
- admits: Number admitted
- acceptance_rate: As NUMBER (e.g., 17.95)
- class_fill_percentage: % of class filled (may be null)

Search: "{university_name} early decision acceptance rate 2024"

OUTPUT (JSON array):
[
  {"plan_type": "ED", "applications": 5048, "admits": 906, "acceptance_rate": 17.95, "class_fill_percentage": 45.0}
]

If no early plans, return: []""",
    tools=[google_search],
    output_key="early_admission_stats",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: GPA Profile
gpa_profile_micro = LlmAgent(
    name="GPAProfileMicro",
    model=MODEL_NAME,
    description="Fetches GPA statistics for admitted students.",
    instruction="""Research GPA data for admitted students at {university_name}:

1. weighted_middle_50 (str): "X.XX-X.XX" format
2. unweighted_middle_50 (str): "X.XX-X.XX" format (max 4.0)
3. average_weighted (float): Average weighted GPA
4. percentile_25 (str): 25th percentile
5. percentile_75 (str): 75th percentile
6. notes (str): Context about GPA calculation

Search: "{university_name} admitted student GPA", "{university_name} class profile"

OUTPUT (JSON):
{
  "weighted_middle_50": "4.42-4.76",
  "unweighted_middle_50": "3.85-3.98",
  "average_weighted": 4.18,
  "percentile_25": "4.42",
  "percentile_75": "4.76",
  "notes": "89% in top 10% of class"
}""",
    tools=[google_search],
    output_key="gpa_profile",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 4: Test Scores (SAT/ACT)
test_scores_micro = LlmAgent(
    name="TestScoresMicro",
    model=MODEL_NAME,
    description="Fetches SAT/ACT statistics.",
    instruction="""Research SAT/ACT scores for {university_name}:

1. sat_composite_middle_50 (str): "XXXX-XXXX" format
2. sat_reading_middle_50 (str): "XXX-XXX"
3. sat_math_middle_50 (str): "XXX-XXX"
4. act_composite_middle_50 (str): "XX-XX"
5. submission_rate (float): % who submitted scores
6. policy_note (str): Superscore policy, etc.

Search: "{university_name} SAT scores admitted students"

OUTPUT (JSON):
{
  "sat_composite_middle_50": "1500-1570",
  "sat_reading_middle_50": "730-780",
  "sat_math_middle_50": "770-800",
  "act_composite_middle_50": "34-36",
  "submission_rate": 61.0,
  "policy_note": "Superscore accepted"
}""",
    tools=[google_search],
    output_key="testing_profile",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 5: International acceptance rate
international_rate_micro = LlmAgent(
    name="InternationalRateMicro",
    model=MODEL_NAME,
    description="Fetches international acceptance rate.",
    instruction="""Find the international student acceptance rate for {university_name}:

Search: "{university_name} international acceptance rate"
Search: "{university_name} international students admission statistics"

OUTPUT (JSON):
{
  "international_acceptance_rate": 4.3,
  "international_applications": 8500,
  "international_admits": 365,
  "notes": "Lower rate than domestic applicants"
}

Use null for unavailable data.""",
    tools=[google_search],
    output_key="international_rates",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 6: In-state vs Out-of-state rates (for public schools)
state_rates_micro = LlmAgent(
    name="StateRatesMicro",
    model=MODEL_NAME,
    description="Fetches in-state vs out-of-state acceptance rates.",
    instruction="""For {university_name}, find in-state vs out-of-state acceptance rates:

Note: Only applicable for PUBLIC universities. Private schools use same rate for all.

Search: "{university_name} in-state acceptance rate"
Search: "{university_name} out-of-state acceptance rate"

OUTPUT (JSON):
{
  "in_state_acceptance_rate": 18.5,
  "out_of_state_acceptance_rate": 8.2,
  "is_public": true,
  "notes": "Significant preference for in-state residents"
}

For private schools, set both rates to null and is_public to false.""",
    tools=[google_search],
    output_key="state_rates",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT: Runs all micro-agents simultaneously
# ==============================================================================

admissions_parallel_collector = ParallelAgent(
    name="AdmissionsParallelCollector",
    sub_agents=[
        current_rates_micro,
        early_decision_micro,
        gpa_profile_micro,
        test_scores_micro,
        international_rate_micro,
        state_rates_micro
    ]
)

# ==============================================================================
# AGGREGATOR: Combines all micro-agent outputs into final structure
# ==============================================================================

admissions_aggregator = LlmAgent(
    name="AdmissionsAggregator",
    model=MODEL_NAME,
    description="Aggregates all micro-agent outputs into final admissions structure.",
    instruction="""Aggregate ALL micro-agent outputs into the final admissions structure.

=== INPUT DATA (from session state) ===
- current_rates: overall_acceptance_rate, is_test_optional, test_policy_details, admits_class_size, transfer_acceptance_rate
- early_admission_stats: array of ED/EA statistics
- gpa_profile: GPA middle 50%, averages
- testing_profile: SAT/ACT ranges
- international_rates: international acceptance rate
- state_rates: in-state vs out-of-state rates

=== OUTPUT STRUCTURE ===
{
  "current_status": {
    "overall_acceptance_rate": <from current_rates>,
    "in_state_acceptance_rate": <from state_rates, null if private>,
    "out_of_state_acceptance_rate": <from state_rates, null if private>,
    "international_acceptance_rate": <from international_rates>,
    "transfer_acceptance_rate": <from current_rates>,
    "admits_class_size": <from current_rates>,
    "is_test_optional": <from current_rates>,
    "test_policy_details": <from current_rates>,
    "early_admission_stats": <from early_admission_stats array>
  },
  "admitted_student_profile": {
    "gpa": <from gpa_profile>,
    "testing": <from testing_profile>
  }
}

RULES:
1. All percentages as NUMBERS (5.65 not "5.65%")
2. Preserve ALL data from micro-agents
3. Use null for missing data
4. Output valid JSON only""",
    output_key="admissions_current_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT: Sequential flow of parallel collection -> aggregation
# ==============================================================================

api_admissions_agent = SequentialAgent(
    name="ApiAdmissionsSequential",
    sub_agents=[admissions_parallel_collector, admissions_aggregator]
)
