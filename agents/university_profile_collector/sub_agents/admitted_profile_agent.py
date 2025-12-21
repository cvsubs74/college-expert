"""
Admitted Profile Agent -> AdmittedStudentProfile + RaceEthnicity - LLM-based research agent.
"""
from google.adk.agents import LlmAgent
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash-lite"

admitted_profile_agent = LlmAgent(
    name="AdmittedProfileAgent",
    model=MODEL_NAME,
    description="Researches admitted student statistics including GPA, test scores, and FULL demographics.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Sections C9-C11: GPA distribution, class rank, mid-50% test scores
2. IPEDS: Federal demographic breakdowns (race, ethnicity, gender)
3. PrepScholar (prepscholar.com): "What are my chances?" data, admitted student scattergrams
4. Cappex: Additional admitted student profiles

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- "{university_name}" Common Data Set Section C GPA test scores 2024
- site:prepscholar.com "{university_name}" SAT ACT scores admitted students
- "{university_name}" IPEDS demographics race ethnicity 2024
- "{university_name}" admitted student profile GPA middle 50

OUTPUT JSON with EXACTLY this structure:

"admitted_student_profile": (
  "gpa": (
    "weighted_middle_50": "4.10-4.30",
    "unweighted_middle_50": "3.80-4.00",
    "average_weighted": 4.20,
    "percentile_25": "3.95" or null,
    "percentile_75": "4.00" or null,
    "notes": "Most admits have straight A's in honors/AP"
  ),
  "testing": (
    "sat_composite_middle_50": "1400-1520",
    "sat_reading_middle_50": "700-760",
    "sat_math_middle_50": "720-780",
    "act_composite_middle_50": "31-35",
    "submission_rate": 75.0,
    "policy_note": "Test optional but recommended"
  ),
  "demographics": (
    "first_gen_percentage": 25.0,
    "legacy_percentage": 10.0,
    "international_percentage": 15.0,
    "geographic_breakdown": [
      ("region": "California", "percentage": 60.0),
      ("region": "Other US States", "percentage": 25.0),
      ("region": "International", "percentage": 15.0)
    ],
    "gender_breakdown": (
      "men": (
        "applicants": 50000,
        "admits": 12000,
        "acceptance_rate": 24.0,
        "note": ""
      ),
      "women": (
        "applicants": 55000,
        "admits": 14000,
        "acceptance_rate": 25.5,
        "note": ""
      ),
      "non_binary": null
    ),
    "racial_breakdown": (
      "white": 35.0,
      "black_african_american": 5.0,
      "hispanic_latino": 22.0,
      "asian": 30.0,
      "native_american_alaskan": 0.5,
      "pacific_islander": 0.3,
      "two_or_more_races": 6.0,
      "unknown": 1.2,
      "non_resident_alien": null
    ),
    "religious_affiliation": null
  )
)

CRITICAL: Get FULL racial breakdown from Common Data Set Section B2 or IPEDS.
Use null for unknown values. Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="admitted_profile_output"
)
