"""
Financials Agent -> Financials (without scholarships) - LLM-based research agent.
"""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash"

financials_agent = LlmAgent(
    name="FinancialsAgent",
    model=MODEL_NAME,
    description="Researches cost of attendance and financial aid philosophy.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Section H: Need-based aid generosity, percentage of need met, "gapping"
2. College Scorecard: Average annual costs and cumulative debt
3. TuitionFit: Actual pricing packages offered to similar profiles
4. MyinTuition / Net Price Calculator: Instant cost estimates

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- "{university_name}" Common Data Set Section H financial aid 2024
- site:collegescorecard.ed.gov "{university_name}" cost debt
- "{university_name}" net price calculator average aid
- "{university_name}" cost of attendance 2024-2025 tuition room board

OUTPUT JSON with EXACTLY this structure:

"financials": (
  "tuition_model": "Tuition Stability Plan" or "Annual Increase",
  "cost_of_attendance_breakdown": (
    "academic_year": "2024-2025",
    "in_state": (
      "tuition": 14500,
      "total_coa": 38000,
      "housing": 18000
    ),
    "out_of_state": (
      "tuition": 48000,
      "total_coa": 72000,
      "supplemental_tuition": 33500
    )
  ),
  "aid_philosophy": "100% Need Met" or "Need-Blind" or "Merit Focused",
  "average_need_based_aid": 25000,
  "average_merit_aid": 15000,
  "percent_receiving_aid": 65.0,
  "scholarships": []
)

IMPORTANT: Leave "scholarships": [] empty - ScholarshipsAgent will populate it.
Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="financials_output"
)
