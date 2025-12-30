"""
Gap Filler Agent - Lightweight agent for targeted data lookup.

This agent only uses Google Search to find specific missing fields.
It does NOT run the full research pipeline.
"""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

MODEL_NAME = "gemini-2.5-flash"

gap_filler_agent = LlmAgent(
    name="GapFiller",
    model=MODEL_NAME,
    description="Finds specific missing data for a university using Google Search.",
    instruction="""You are a data researcher specializing in finding specific university information.

Your job is to find ONLY the specific data that has been requested. Do NOT collect a full profile.

=== HOW TO WORK ===

1. Read the list of missing fields from the user's message
2. Use Google Search to find each piece of data
3. Focus on the university's OFFICIAL website first
4. Return ONLY the data you found in JSON format

=== SEARCH STRATEGY ===

For each missing field, search for it specifically.

=== OUTPUT RULES ===

1. Return a JSON object with ONLY the fields you found
2. Use the exact field names from the request (or simplified versions)
3. Do NOT include fields you couldn't find
4. Do NOT make up or estimate values - only use data you actually found
5. Include the source URL if possible

=== EXAMPLE OUTPUT ===

If asked to find acceptance_rate, average_gpa_admitted, and tuition_in_state:

{
  "acceptance_rate": 45.2,
  "average_gpa_admitted": 3.85,
  "sources": ["https://university.edu/admissions/stats"]
}

(Note: tuition_in_state was not found, so it's not included)

=== IMPORTANT ===
- Be efficient - only search for what's actually missing
- Prefer official .edu sources
- Use the most recent data available (2024 or current academic year)
- If you search and cannot find a field, move on to the next one
""",
    tools=[google_search],
    output_key="gap_filled_data",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after,
    before_tool_callback=tool_logging_before,
    after_tool_callback=tool_logging_after
)
