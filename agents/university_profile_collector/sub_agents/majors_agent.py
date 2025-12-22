"""
Majors Agent -> Majors with IMPACTION DETAILS - LLM-based research agent.
"""
from google.adk.agents import LlmAgent
from .shared_logging import (
    agent_logging_before, agent_logging_after,
    tool_logging_before, tool_logging_after
)
from google.adk.tools import google_search

MODEL_NAME = "gemini-2.5-flash"

majors_agent = LlmAgent(
    name="MajorsAgent",
    model=MODEL_NAME,
    description="Researches all majors with acceptance rates, prerequisites, WEEDER COURSES, GPA FLOORS, CURRICULUM, and PROFESSORS.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. College Scorecard (collegescorecard.ed.gov): Earnings data broken down by major
2. Official Department Catalogs: Prerequisite courses, degree types, curriculum

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.
3. Acceptd (acceptd.com): Performing arts major requirements (auditions/portfolios)

=== REQUIRED SEARCHES ===
- site:*.edu "{university_name}" undergraduate majors list catalog
- "{university_name}" impacted capped majors 2024
- "{university_name}" transfer into [Major] prerequisites GPA requirement
- site:collegescorecard.ed.gov "{university_name}" earnings by field of study
- "{university_name}" [Major] curriculum requirements core courses

=== ADDITIONAL SEARCHES ===
- "transferring INTO [Major] at {university_name}" for HIDDEN PREREQUISITES
- Major-specific acceptance rates
- Departmental handbooks for GPA requirements
- "[Major] faculty {university_name}" for professors
- RateMyProfessors for top-rated professors

HIDDEN PREREQUISITES TO FIND:
- minimum_gpa_to_declare: GPA floor to switch INTO this major after enrolling
- weeder_courses: Courses that filter out students (e.g., "Organic Chemistry CHEM 140")
- direct_admit_only: If TRUE, NO internal transfers allowed - must apply as freshman

CURRICULUM TO FIND:
- core_courses: Required courses that every student in the major must take
- electives: Popular elective options within the major
- total_units: Total units required for graduation
- major_units: Units specifically for the major

PROFESSORS TO FIND:
- Notable faculty who teach in the major
- Department chair or program director
- Research-active professors with student mentorship

OUTPUT JSON with EXACTLY this structure:

"majors_by_college": (
  "College of Engineering": [
    (
      "name": "Computer Science",
      "degree_type": "B.S.",
      "is_impacted": true,
      "acceptance_rate": 8.0,
      "average_gpa_admitted": 4.25,
      "prerequisite_courses": ["Calculus BC", "Physics C", "AP CS A"],
      "minimum_gpa_to_declare": 3.5,
      "weeder_courses": ["CSE 21 Discrete Math", "CSE 30 Systems Programming"],
      \"special_requirements\": null,  // STRING or null ONLY - NEVER use an array
      "admissions_pathway": "Direct Admit",
      "internal_transfer_allowed": false,
      "direct_admit_only": true,
      "internal_transfer_gpa": null,
      "curriculum": (
        "core_courses": [
          "CSE 11 Intro to Programming",
          "CSE 12 Data Structures",
          "CSE 15L Software Tools",
          "CSE 20 Discrete Math",
          "CSE 21 Algorithms",
          "CSE 30 Computer Organization",
          "CSE 100 Advanced Data Structures",
          "CSE 101 Design and Analysis of Algorithms",
          "CSE 110 Software Engineering"
        ],
        "electives": [
          "CSE 150A Machine Learning",
          "CSE 158 Data Mining",
          "CSE 167 Computer Graphics",
          "CSE 190 Topics in CS"
        ],
        "total_units": 180,
        "major_units": 72
      ),
      "notable_professors": [
        "Dr. Sanjoy Dasgupta (Machine Learning)",
        "Dr. Leo Porter (CS Education, Software Engineering)",
        "Dr. Mihir Bellare (Cryptography)"
      ],
      "notes": "Extremely competitive, NO internal transfers"
    )
  ],
  "College of Letters and Science": [
    (
      "name": "Economics",
      "degree_type": "B.A.",
      "is_impacted": false,
      "acceptance_rate": null,
      "average_gpa_admitted": null,
      "prerequisite_courses": [],
      "minimum_gpa_to_declare": 2.0,
      "weeder_courses": ["ECON 100A Microeconomics"],
      "special_requirements": null,
      "admissions_pathway": "Pre-Major",
      "internal_transfer_allowed": true,
      "direct_admit_only": false,
      "internal_transfer_gpa": 2.0,
      "curriculum": (
        "core_courses": [
          "ECON 1 Principles of Microeconomics",
          "ECON 2 Principles of Macroeconomics",
          "ECON 100A Microeconomic Theory",
          "ECON 100B Macroeconomic Theory",
          "ECON 120A Econometrics"
        ],
        "electives": [
          "ECON 131 Public Economics",
          "ECON 135 Financial Economics",
          "ECON 171 Decisions Under Uncertainty"
        ],
        "total_units": 180,
        "major_units": 52
      ),
      "notable_professors": [
        "Dr. James Hamilton (Macroeconomics, Time Series)",
        "Dr. Gordon Dahl (Labor Economics)"
      ],
      "notes": "Open major, easy to switch into"
    )
  ]
)

Use EXACT college names from the university.
Include 10-15 majors per college with curriculum details for TOP 5 most popular majors.

ANTI-HALLUCINATION RULES:
- If you CANNOT FIND minimum_gpa_to_declare from official sources, use null. DO NOT GUESS.
- If weeder courses are unknown for a major, use empty array []. DO NOT INVENT course names.
- Only set direct_admit_only: true if the official page explicitly states "no internal transfers".
- For curriculum, only include REAL course names from the university catalog. DO NOT INVENT COURSES.
- For professors, only include REAL faculty names from department websites. DO NOT INVENT NAMES.
- If curriculum or professors are not found, set curriculum: null and notable_professors: [].

Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="majors_output",
    before_agent_callback=agent_logging_before,
    after_agent_callback=agent_logging_after
)
