"""
Admissions Current Agent -> CurrentStatus - LLM-based research agent.
"""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash-lite"

admissions_current_agent = LlmAgent(
    name="AdmissionsCurrentAgent",
    model=MODEL_NAME,
    description="Researches current admissions cycle statistics.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Section C: Primary source for acceptance rates, waitlist, testing policies
2. IPEDS Admissions Component: Verified admissions data released annually
3. Expert Admissions (expertadmissions.com): Qualitative updates on recent cycle trends

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- site:*.edu "{university_name}" Common Data Set 2024-2025 filetype:pdf
- "{university_name}" Common Data Set Section C acceptance rate 2024
- site:expertadmissions.com "{university_name}" admissions 2025
- "{university_name}" test optional policy 2025

OUTPUT JSON with EXACTLY this structure:

"current_status": (
  "overall_acceptance_rate": 23.5,
  "in_state_acceptance_rate": 30.0,
  "out_of_state_acceptance_rate": 18.0,
  "international_acceptance_rate": 15.0,
  "transfer_acceptance_rate": 45.0,
  "admits_class_size": 6500,
  "is_test_optional": true,
  "test_policy_details": "Test Optional" or "Test Required" or "Test Free" or "Test Blind",
  "early_admission_stats": [
    (
      "plan_type": "ED" or "EA" or "REA" or "ED2",
      "applications": 5000,
      "admits": 1200,
      "acceptance_rate": 24.0,
      "class_fill_percentage": 45.0
    )
  ]
)

CRITICAL: 
- Rates are PERCENTAGES (e.g., 23.5 not 0.235)
- Data should come from CDS Section C
- Use null for unknown values
- Use ( ) instead of curly braces
""",
    tools=[google_search],
    output_key="admissions_current_output"
)
