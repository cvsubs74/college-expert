"""
Credit Policies Agent - Uses ParallelAgent pattern with focused micro-agents.

This agent runs 3 micro-agents in parallel to gather AP, IB, and transfer policies,
then aggregates their outputs into a single structured result.
"""
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash-lite"

# ==============================================================================
# MICRO-AGENTS
# ==============================================================================

# Micro-agent 1: AP Credit Policy
ap_policy_micro = LlmAgent(
    name="APPolicyMicro",
    model=MODEL_NAME,
    description="Fetches AP credit policy.",
    instruction="""Research AP credit policy for {university_name}:

1. general_rule (str): "Score of 3+ grants credit", etc.
2. exceptions (list): Exams with special rules
3. usage (str): How AP credits can be used

Search: site:*.edu "{university_name}" AP credit policy score chart
Search: "{university_name}" registrar AP exam credit

OUTPUT (JSON):
{
  "ap_policy": {
    "general_rule": "Score of 4+ grants credit for most exams",
    "exceptions": ["No credit for AP Research", "CS requires 5"],
    "usage": "Can satisfy some major prerequisites and GE"
  }
}""",
    tools=[google_search],
    output_key="ap_policy",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 2: IB Credit Policy
ib_policy_micro = LlmAgent(
    name="IBPolicyMicro",
    model=MODEL_NAME,
    description="Fetches IB credit policy.",
    instruction="""Research IB credit policy for {university_name}:

1. general_rule (str): "HL 5+ only", "SL not accepted", etc.
2. diploma_bonus (bool): Extra benefits for full IB Diploma?

Search: "{university_name}" IB credit policy higher level
Search: "{university_name}" International Baccalaureate credit

OUTPUT (JSON):
{
  "ib_policy": {
    "general_rule": "HL exams with 5+ grant credit",
    "diploma_bonus": true
  }
}""",
    tools=[google_search],
    output_key="ib_policy",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# Micro-agent 3: Transfer Articulation
transfer_micro = LlmAgent(
    name="TransferMicro",
    model=MODEL_NAME,
    description="Fetches transfer credit policy.",
    instruction="""Research transfer credit policy for {university_name}:

1. tools (list): ["ASSIST.org", "Transferology", etc.]
2. restrictions (str): Credit limits, grade requirements

Search: site:assist.org "{university_name}"
Search: "{university_name}" transfer credit policy

OUTPUT (JSON):
{
  "transfer_articulation": {
    "tools": ["ASSIST.org", "Transferology"],
    "restrictions": "60 unit cap for community college credits"
  }
}

If no tools found, use empty list [].""",
    tools=[google_search],
    output_key="transfer_articulation",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# PARALLEL AGENT
# ==============================================================================

credit_parallel_collector = ParallelAgent(
    name="CreditParallelCollector",
    sub_agents=[
        ap_policy_micro,
        ib_policy_micro,
        transfer_micro
    ]
)

# ==============================================================================
# AGGREGATOR
# ==============================================================================

credit_aggregator = LlmAgent(
    name="CreditAggregator",
    model=MODEL_NAME,
    description="Aggregates all credit policy outputs.",
    instruction="""Aggregate ALL credit policy micro-agent outputs.

=== INPUT DATA ===
- ap_policy: AP credit rules
- ib_policy: IB credit rules
- transfer_articulation: transfer tools and restrictions

=== OUTPUT STRUCTURE ===
{
  "credit_policies": {
    "philosophy": "Generous Credit" or "Moderate" or "Strict",
    "ap_policy": <from ap_policy>,
    "ib_policy": <from ib_policy>,
    "transfer_articulation": <from transfer_articulation>
  }
}

Determine philosophy based on combined policies.
Use ( ) instead of {}.""",
    output_key="credit_policies_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)

# ==============================================================================
# MAIN AGENT
# ==============================================================================

credit_policies_agent = SequentialAgent(
    name="CreditPoliciesSequential",
    sub_agents=[credit_parallel_collector, credit_aggregator]
)
