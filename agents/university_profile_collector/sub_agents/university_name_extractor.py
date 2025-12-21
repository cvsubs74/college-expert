"""
UniversityNameExtractor - Extracts university name from user input.
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)

MODEL_NAME = "gemini-2.5-flash-lite"

university_name_extractor = LlmAgent(
    name="UniversityNameExtractor",
    model=MODEL_NAME,
    description="Extracts the university name from the user's request.",
    instruction="""Extract the university name from the user's request.
Output ONLY the university name (e.g., 'Stanford University'). No other text.""",
    output_key="university_name",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
