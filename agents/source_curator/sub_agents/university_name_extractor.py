"""
UniversityNameExtractor - Extracts and normalizes university name from user input.
"""
from google.adk.agents import LlmAgent
from .shared_logging import agent_logging_before, agent_logging_after

MODEL_NAME = "gemini-2.5-flash-lite"

university_name_extractor = LlmAgent(
    name="UniversityNameExtractor",
    model=MODEL_NAME,
    description="Extracts university name from user input and creates a standardized ID.",
    instruction="""Extract the university name from the user's query and create standardized identifiers.

OUTPUT FORMAT (JSON only, no markdown):
{
  "university_name": "University of Southern California",
  "university_id": "university_of_southern_california",
  "common_abbreviations": ["USC", "Southern Cal"],
  "official_domain": "usc.edu"
}

RULES:
1. university_name: Use the full official name
2. university_id: lowercase, underscores for spaces, no punctuation
3. common_abbreviations: 2-3 common nicknames/abbreviations
4. official_domain: The main .edu domain

EXAMPLES:
- "USC" -> "University of Southern California", "university_of_southern_california"
- "MIT" -> "Massachusetts Institute of Technology", "massachusetts_institute_of_technology"
- "UC Berkeley" -> "University of California, Berkeley", "university_of_california_berkeley"
- "Stanford" -> "Stanford University", "stanford_university"
""",
    output_key="university_info",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
