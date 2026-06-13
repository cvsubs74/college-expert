"""
Scholarships Agent -> Scholarships - LLM-based research agent.
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash"

scholarships_agent = LlmAgent(
    name="ScholarshipsAgent",
    model=MODEL_NAME,
    description="Researches all available scholarships.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Section H2A: "Institutional non-need-based scholarship or grant aid" (merit aid)
2. Fastweb: External scholarship matches
3. Road2College (R2C Insights): Merit aid generosity rankings
4. EducationUSA: International student scholarship opportunities

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- "{university_name}" merit scholarship Regents full ride
- "{university_name}" Common Data Set H2A non-need scholarship
- site:fastweb.com "{university_name}" scholarship
- "{university_name}" departmental scholarships honors program
- "{university_name}" international student scholarship

OUTPUT JSON with EXACTLY this structure:

"scholarships": [
  (
    "name": "Regents Scholarship",
    "type": "Merit",
    "amount": "$40,000 over 4 years",
    "deadline": "Automatic consideration",
    "deadline_date": null,
    "benefits": "Priority registration, special advising, honors housing",
    "application_method": "Automatic Consideration"
  ),
  (
    "name": "Chancellor's Achievement Award",
    "type": "Merit",
    "amount": "$10,000/year",
    "deadline": "February 1, 2026 (separate application)",
    "deadline_date": "2026-02-01",
    "benefits": "Research funding opportunity",
    "application_method": "Separate Application"
  ),
  (
    "name": "Need-Based Grant",
    "type": "Need",
    "amount": "Varies based on FAFSA",
    "deadline": "FAFSA deadline",
    "deadline_date": null,
    "benefits": "",
    "application_method": "FAFSA"
  )
]

For "deadline_date": give the scholarship's application deadline as ISO
"YYYY-MM-DD" for the UPCOMING cycle, or null when there is no separate fixed
date (Automatic Consideration, "Varies", "Rolling", or FAFSA/CSS-driven).
Always keep the human-readable description in "deadline".

Include 5-7 scholarships.
Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="scholarships_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
