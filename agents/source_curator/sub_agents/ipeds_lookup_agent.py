"""
IPEDS Lookup Agent - Looks up IPEDS ID for a university.

This agent uses custom FunctionTools only (no google_search).
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

try:
    from ..tools import lookup_ipeds_id, get_api_source_config
except ImportError:
    from tools import lookup_ipeds_id, get_api_source_config

MODEL_NAME = "gemini-2.5-flash-lite"

ipeds_lookup_agent = LlmAgent(
    name="IPEDSLookupAgent",
    model=MODEL_NAME,
    description="Looks up IPEDS Unit ID and generates API source configs for a university.",
    instruction="""You are an IPEDS lookup agent. Your job is to:

1. Get the university_name from session state
2. Call lookup_ipeds_id with the university name
3. If IPEDS ID found, call get_api_source_config with the university_id and ipeds_id

Store the results in your output for the next agent to use.

OUTPUT (JSON):
{
  "university_id": "university_of_southern_california",
  "ipeds_id": 123961,
  "ipeds_lookup_success": true,
  "api_sources": {
    "college_scorecard": {...},
    "urban_ipeds": {...}
  }
}

If IPEDS lookup fails:
{
  "university_id": "university_of_southern_california",
  "ipeds_id": null,
  "ipeds_lookup_success": false,
  "api_sources": {},
  "error": "IPEDS ID not found, manual lookup required"
}
""",
    tools=[lookup_ipeds_id, get_api_source_config],
    output_key="ipeds_data",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)
