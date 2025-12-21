import json
import logging
import os
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent, LoopAgent, BaseAgent
from google.adk.tools import google_search, AgentTool, ToolContext
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from typing import AsyncGenerator

# Import validation logic - support both module and direct execution
try:
    from .validation_logic import apply_all_fixes, fix_escape_sequences, fix_json_syntax
except ImportError:
    from validation_logic import apply_all_fixes, fix_escape_sequences, fix_json_syntax

# Import models for validation reference - support both module and direct execution
try:
    from .model import UniversityProfile
except ImportError:
    from model import UniversityProfile

# Configure logging
logger = logging.getLogger(__name__)

# Common config
MODEL_NAME = "gemini-2.5-flash"

# Get the research directory path
RESEARCH_DIR = os.path.join(os.path.dirname(__file__), 'research')

# ==============================================================================
# TOOL: Write File
# ==============================================================================

def write_file(
    tool_context: ToolContext,
    filename: str,
    content: str
) -> dict:
    """Writes content to a file in the research directory."""
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    target_path = os.path.join(RESEARCH_DIR, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Saved file to: {target_path}")
    return {"status": "success", "path": target_path}

# ==============================================================================
# STATE INITIALIZER - Ensures all output keys exist
# ==============================================================================

class StateInitializer(BaseAgent):
    """Initializes session state with expected output keys to prevent KeyError."""
    
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator:
        keys = [
            "university_name",  # Must be initialized before sub-agents run
            "strategy_output", "admissions_current_output", "admissions_trends_output",
            "admitted_profile_output", "colleges_output", "majors_output",
            "application_output", "strategy_tactics_output", "financials_output",
            "scholarships_output", "credit_policies_output", "student_insights_output",
            "outcomes_output"
        ]
        for key in keys:
            if key not in ctx.session.state:
                ctx.session.state[key] = "" if key == "university_name" else None
        logger.info(f"[StateInitializer] Initialized {len(keys)} output keys, university_name={ctx.session.state.get('university_name')}")
        # Empty generator - just for async signature
        if False:
            yield Event(author=self.name, content={})

state_initializer = StateInitializer(name="StateInitializer")

# ==============================================================================
# AGENT 0: University Name Extractor
# ==============================================================================

university_name_extractor = LlmAgent(
    name="UniversityNameExtractor",
    model=MODEL_NAME,
    description="Extracts the university name from the user's request.",
    instruction="""Extract the university name from the user's request.
Output ONLY the university name (e.g., 'Stanford University'). No other text.""",
    output_key="university_name"
)

# ==============================================================================
# AGENT 1: Strategy Agent -> Metadata + StrategicProfile
# ==============================================================================

strategy_agent = LlmAgent(
    name="StrategyAgent",
    model=MODEL_NAME,
    description="Researches university ranking, market position, and campus dynamics.",
    instruction="""Research the university: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. IPEDS (nces.ed.gov/ipeds): Official metadata, institution type, location

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.
2. U.S. News & World Report (usnews.com/best-colleges): Current rankings, market position
3. Niche (niche.com): Campus dynamics, social environment ratings, community "vibe"
4. Official University Website: Mission statement, admissions philosophy

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- site:usnews.com "{university_name}" ranking 2026 National Universities
- site:niche.com "{university_name}" campus life review
- "{university_name}" IPEDS institution profile
- "{university_name}" official admissions philosophy mission

OUTPUT JSON with EXACTLY this structure:

"metadata": (
  "official_name": "Full Official University Name",
  "location": (
    "city": "City Name",
    "state": "State Name or Abbreviation",
    "type": "Public" or "Private"
  ),
  "last_updated": "YYYY-MM-DD",
  "report_source_files": []
),
"strategic_profile": (
  "executive_summary": "2-3 sentence overview of the university",
  "market_position": "Public Ivy" or "Hidden Gem" or "Elite Private" etc,
  "admissions_philosophy": "Holistic review" or "Numbers-focused" or "Test-free" etc,
  "us_news_rank": 15,
  "analyst_takeaways": [
    (
      "category": "Selectivity",
      "insight": "Key finding from research",
      "implication": "What this means for applicants"
    ),
    (
      "category": "Value",
      "insight": "Another key finding",
      "implication": "Strategic recommendation"
    ),
    (
      "category": "Academic",
      "insight": "Third insight",
      "implication": "Action item for applicants"
    )
  ],
  "campus_dynamics": (
    "social_environment": "From Niche reviews - social atmosphere description",
    "transportation_impact": "How transport affects campus life",
    "research_impact": "Research opportunities and industry ties"
  )
)

CRITICAL: 
- us_news_rank must be INTEGER from usnews.com 2026 National Universities ranking
- Include AT LEAST 3 analyst_takeaways
- Use ( ) instead of curly braces
""",
    tools=[google_search],
    output_key="strategy_output"
)

# ==============================================================================
# AGENT 2: Admissions Current Agent -> CurrentStatus
# ==============================================================================

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

# ==============================================================================
# AGENT 3: Admissions Trends Agent -> LongitudinalTrends + WaitlistDetailedStats
# ==============================================================================

admissions_trends_agent = LlmAgent(
    name="AdmissionsTrendsAgent",
    model=MODEL_NAME,
    description="Researches historical admissions trends and WAITLIST mechanics.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Archives: Historical CDS reports (Section C) for 3-5 year trends
2. ApplyingToCollege (applyingtocollege.com): Real-time decision release dates
3. Expert Admissions: Waitlist activity analysis and "summer melt" trends

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- site:*.edu "{university_name}" Common Data Set 2023 2024 filetype:pdf
- "{university_name}" Common Data Set Section C2 waitlist 2024
- "{university_name}" acceptance rate history 2020 2021 2022 2023 2024
- site:applyingtocollege.com "{university_name}" decision date 2025
- "{university_name}" waitlist statistics admitted yield rate

=== WAITLIST REQUIREMENTS (The "Black Box") ===
From CDS Section C2, find:
- applicants OFFERED waitlist spots
- applicants who ACCEPTED waitlist spots  
- applicants ADMITTED from waitlist
- CALCULATE: waitlist_admit_rate = (admitted / accepted) * 100
- whether waitlist is RANKED or unranked

OUTPUT JSON with EXACTLY this structure:

"longitudinal_trends": [
  (
    "year": 2025,
    "cycle_name": "Class of 2029",
    "applications_total": 120000,
    "admits_total": 28000,
    "enrolled_total": 6500,
    "acceptance_rate_overall": 23.3,
    "acceptance_rate_in_state": 30.0,
    "acceptance_rate_out_of_state": 18.0,
    "yield_rate": 23.2,
    "waitlist_stats": (
      "year": 2025,
      "offered_spots": 15000,
      "accepted_spots": 10000,
      "admitted_from_waitlist": 2500,
      "waitlist_admit_rate": 25.0,
      "is_waitlist_ranked": false
    ),
    "notes": "Record number of applications"
  )
]

CRITICAL:
- Include AT LEAST 5 YEARS of data (2021-2025)
- Each year MUST have waitlist_stats
- If waitlist data hidden, note "Waitlist data not publicly disclosed" in notes
- Use null for unknown values. Use ( ) instead of curly braces
""",
    tools=[google_search],
    output_key="admissions_trends_output"
)

# ==============================================================================
# AGENT 4: Admitted Profile Agent -> AdmittedStudentProfile + RaceEthnicity
# ==============================================================================

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

# ==============================================================================
# AGENT 5: Colleges Agent -> AcademicStructure (without majors)
# ==============================================================================

colleges_agent = LlmAgent(
    name="CollegesAgent",
    model=MODEL_NAME,
    description="Researches college/school structure, housing, and student archetypes.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. CampusReel (campusreel.org): Student-led video tours of dorms and housing
2. Niche (niche.com): Letter grades on housing quality and campus life
3. Official University Website: List of ALL undergraduate schools and colleges

⚠️ WARNING: Example values are for STRUCTURE ONLY.
DO NOT copy examples. Use ONLY data from searches. Use null for missing data.

=== CRITICAL: FIND ALL SCHOOLS ===
You MUST find ALL undergraduate schools/colleges, not just the main one.
Common examples include:
- School of Engineering / Applied Science
- College of Arts & Sciences / Letters & Science
- School of Business (if offers undergrad)
- School of Nursing (if offers undergrad)
- School of Music / Arts (if offers undergrad)

=== REQUIRED SEARCHES ===
- "{university_name}" list of undergraduate schools colleges
- "{university_name}" School of Engineering undergraduate
- "{university_name}" all undergraduate programs schools
- site:niche.com "{university_name}" housing dorms review
- "{university_name}" residential colleges housing system

OUTPUT JSON with EXACTLY this structure:

"academic_structure": (
  "structure_type": "Colleges" or "Schools" or "Divisions",
  "colleges": [
    (
      "name": "School of Engineering",
      "admissions_model": "Direct Admit" or "Pre-Major" or "Lottery",
      "acceptance_rate_estimate": null,
      "is_restricted_or_capped": true,
      "strategic_fit_advice": "Strong STEM background required",
      "housing_profile": "Modern dorms with maker spaces",
      "student_archetype": "Ambitious problem-solvers",
      "majors": []
    ),
    (
      "name": "College of Arts and Sciences",
      "admissions_model": "Pre-Major",
      "acceptance_rate_estimate": null,
      "is_restricted_or_capped": false,
      "strategic_fit_advice": "Flexible major options",
      "housing_profile": "Traditional dorms",
      "student_archetype": "Intellectually curious",
      "majors": []
    )
  ],
  "minors_certificates": ["Data Science Minor", "Entrepreneurship Certificate"]
)

CRITICAL: 
- Include ALL undergraduate schools/colleges that offer bachelor's degrees
- Leave "majors": [] empty - MajorsAgent will populate it
- Use ( ) instead of curly braces
""",
    tools=[google_search],
    output_key="colleges_output"
)

# ==============================================================================
# AGENT 6: Majors Agent -> Majors with IMPACTION DETAILS
# ==============================================================================

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
      "special_requirements": null,
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
    output_key="majors_output"
)

# ==============================================================================
# AGENT 7: Application Agent -> ApplicationProcess
# ==============================================================================

application_agent = LlmAgent(
    name="ApplicationAgent",
    model=MODEL_NAME,
    description="Researches application requirements, deadlines, and evaluation factors.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Section C7: Which factors are "Very Important" vs "Considered"
2. Coalition for College / Common App: Application platforms and fee waiver info
3. Acceptd / Musical Theater Common Prescreen: Arts program requirements

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- "{university_name}" Common Data Set Section C7 important factors 2024
- site:commonapp.org "{university_name}" supplemental essays 2025
- "{university_name}" application deadline 2025 early decision regular
- "{university_name}" demonstrated interest interview policy
- site:acceptd.com "{university_name}" audition prescreen requirements

OUTPUT JSON with EXACTLY this structure:

"application_process": (
  "platforms": ["Common App", "Coalition App"],
  "application_deadlines": [
    (
      "plan_type": "Early Decision",
      "date": "2024-11-01",
      "is_binding": true,
      "notes": "Binding commitment"
    ),
    (
      "plan_type": "Regular Decision",
      "date": "2025-01-01",
      "is_binding": false,
      "notes": ""
    )
  ],
  "supplemental_requirements": [
    (
      "target_program": "All",
      "requirement_type": "Essays",
      "deadline": null,
      "details": "Two supplemental essays required: Why Us + Community"
    ),
    (
      "target_program": "Music",
      "requirement_type": "Audition",
      "deadline": "2024-12-01",
      "details": "Pre-screening recording required"
    )
  ],
  "holistic_factors": (
    "primary_factors": ["Course Rigor", "GPA", "Essays", "Recommendations"],
    "secondary_factors": ["Extracurriculars", "Talents", "Character"],
    "essay_importance": "Critical" or "High" or "Moderate" or "Low",
    "demonstrated_interest": "Important" or "Considered" or "Not Considered",
    "interview_policy": "Required" or "Recommended" or "Not Offered",
    "legacy_consideration": "Strong" or "Moderate" or "Minimal" or "None",
    "first_gen_boost": "Strong" or "Moderate" or "Minimal" or "None",
    "specific_differentiators": "Looking for intellectual curiosity and drive"
  )
)

Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="application_output"
)

# ==============================================================================
# AGENT 8: Strategy Tactics Agent -> ApplicationStrategy
# ==============================================================================

strategy_tactics_agent = LlmAgent(
    name="StrategyTacticsAgent",
    model=MODEL_NAME,
    description="Researches application gaming strategies and tactical advice.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Section C21: Statistical advantage of Early Decision vs Regular Decision
2. College Confidential Forums: Crowdsourced admissions quirks and gaming strategies
3. Road2College: Balancing academic fit with financial reality
4. Examplit: Analyzing successful profiles for narrative strategies

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- "{university_name}" early decision acceptance rate vs regular decision
- site:talk.collegeconfidential.com "{university_name}" major selection strategy
- site:road2college.com "{university_name}" application strategy
- "{university_name}" easier majors to get into transfer later
- "{university_name}" Common Data Set C21 early vs regular admit rate

OUTPUT JSON with EXACTLY this structure:

"application_strategy": (
  "major_selection_tactics": [
    "Apply to less competitive major if not set on CS/Engineering",
    "Consider undeclared for Letters and Science",
    "Research major-specific admit rates before applying"
  ],
  "college_ranking_tactics": [
    "Rank colleges based on GE requirements not just prestige",
    "Consider housing quality in ranking decisions"
  ],
  "alternate_major_strategy": "If applying to competitive major, list backup in different college. For example, if applying to CS in Engineering, list Cognitive Science in Letters and Science as alternate."
)

Include 3-5 tactics per category.
Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="strategy_tactics_output"
)

# ==============================================================================
# AGENT 9: Financials Agent -> Financials (without scholarships)
# ==============================================================================

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

# ==============================================================================
# AGENT 10: Scholarships Agent -> Scholarships
# ==============================================================================

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
    "benefits": "Priority registration, special advising, honors housing",
    "application_method": "Automatic Consideration"
  ),
  (
    "name": "Chancellor's Achievement Award",
    "type": "Merit",
    "amount": "$10,000/year",
    "deadline": "2025-02-01",
    "benefits": "Research funding opportunity",
    "application_method": "Separate Application"
  ),
  (
    "name": "Need-Based Grant",
    "type": "Need",
    "amount": "Varies based on FAFSA",
    "deadline": "FAFSA deadline",
    "benefits": "",
    "application_method": "FAFSA"
  )
]

Include 5-7 scholarships.
Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="scholarships_output"
)

# ==============================================================================
# AGENT 11: Credit Policies Agent -> CreditPolicies
# ==============================================================================

credit_policies_agent = LlmAgent(
    name="CreditPoliciesAgent",
    model=MODEL_NAME,
    description="Researches AP, IB, and transfer credit policies.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. Common Data Set Section D: Transfer admission stats and credit acceptance policies
2. Transferology / ASSIST.org: Specific transfer articulations
3. Official Registrar Websites: AP/IB score conversion charts

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- site:*.edu "{university_name}" AP credit policy 2024 score chart
- site:*.edu "{university_name}" IB credit policy higher level
- site:assist.org "{university_name}" transfer articulation
- "{university_name}" Common Data Set Section D transfer credits
- "{university_name}" registrar AP IB exam credit

OUTPUT JSON with EXACTLY this structure:

"credit_policies": (
  "philosophy": "Generous Credit" or "Moderate" or "Strict",
  "ap_policy": (
    "general_rule": "Score of 3+ grants credit for most exams",
    "exceptions": ["No credit for AP Research", "CS requires 5 for credit"],
    "usage": "Can satisfy GE requirements and some major prereqs"
  ),
  "ib_policy": (
    "general_rule": "HL exams with 5+ grant credit",
    "diploma_bonus": true
  ),
  "transfer_articulation": (
    "tools": ["ASSIST.org", "Transferology"],
    "restrictions": "60 unit cap for community college credits"
  )
)

Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="credit_policies_output"
)

# ==============================================================================
# AGENT 12: Student Insights Agent -> StudentInsights
# ==============================================================================

student_insights_agent = LlmAgent(
    name="StudentInsightsAgent",
    model=MODEL_NAME,
    description="Researches crowdsourced student insights and tips.",
    instruction="""Research: {university_name}

=== DATA SOURCES (Search these specifically) ===
1. StudentsReview: Uncensored faculty and social dynamics feedback
2. Unigo: Student-written reviews and ratings on campus safety
3. Niche: Student polls and "grades" on campus aspects
4. College Confidential: Real-time student discussions and "chance me" threads

⚠️ WARNING: Example values below are for STRUCTURE ONLY.
DO NOT copy example numbers. Use ONLY data from your searches.
If data cannot be found, use null - NEVER make up values.

=== REQUIRED SEARCHES ===
- site:studentsreview.com "{university_name}" review rating
- site:unigo.com "{university_name}" student reviews
- site:niche.com "{university_name}" student life poll
- site:talk.collegeconfidential.com "{university_name}" accepted profile 2024
- "{university_name}" essays that worked reddit

OUTPUT JSON with EXACTLY this structure:

"student_insights": (
  "what_it_takes": [
    "Strong academic record with challenging coursework",
    "Demonstrated passion in 1-2 areas rather than scattered activities",
    "Authentic essays that show self-reflection"
  ],
  "common_activities": [
    "Research experience",
    "Leadership in school clubs",
    "Community service",
    "Varsity athletics",
    "Music/arts involvement"
  ],
  "essay_tips": [
    "Be specific about why this school",
    "Show, don't tell",
    "Avoid cliches about loving to learn"
  ],
  "red_flags": [
    "Grade decline senior year",
    "Generic essays that could apply anywhere"
  ],
  "insights": []
)

Include 3-5 items per category.
Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="student_insights_output"
)

# ==============================================================================
# AGENT 13: Outcomes Agent -> CareerOutcomes + RetentionStats (NEW)
# ==============================================================================

outcomes_agent = LlmAgent(
    name="OutcomesAgent",
    model=MODEL_NAME,
    description="Determines the financial VALUE of the degree - ROI, earnings, retention.",
    instruction="""Research: {university_name}

YOU ARE RESPONSIBLE FOR DETERMINING THE FINANCIAL VALUE OF THIS DEGREE.

MANDATORY SOURCES:
1. College Scorecard: "median earnings 10 years after entry"
2. Common Data Set Section B: "freshman retention rate", "graduation rates"
3. Career Center reports: Top employers
4. LinkedIn Alumni data: Employment outcomes

DO NOT RELY ON ALUMNI BROCHURES - USE OFFICIAL DATA ONLY.

OUTPUT JSON with EXACTLY this structure:

"outcomes": (
  "median_earnings_10yr": 85000,
  "employment_rate_2yr": 92.0,
  "grad_school_rate": 25.0,
  "top_employers": [
    "Google",
    "Apple",
    "Meta",
    "Amazon",
    "Microsoft",
    "Deloitte",
    "Goldman Sachs"
  ],
  "loan_default_rate": 2.5
),
"student_retention": (
  "freshman_retention_rate": 96.0,
  "graduation_rate_4_year": 72.0,
  "graduation_rate_6_year": 91.0
)

CRITICAL:
- median_earnings_10yr must be an INTEGER (dollars per year, NOT a float)
- Rates are PERCENTAGES (e.g., 96.0 not 0.96)
- Include at least 5-7 top employers
- Use null for values you cannot find, BUT TRY HARD TO FIND THEM

ANTI-HALLUCINATION RULES:
- ONLY use College Scorecard for median_earnings_10yr. If not found, use null. DO NOT ESTIMATE.
- DO NOT use LinkedIn salary estimates, Glassdoor, or Payscale.
- For top_employers, only list companies mentioned in official Career Center reports or LinkedIn Alumni data.

Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="outcomes_output"
)

# ==============================================================================
# VALIDATION AGENTS  (New)
# ==============================================================================

class ValidationFixer(BaseAgent):
    """
    Applies deterministic Python fixes and validates against the schema.
    If valid, escalates to break the loop.
    If invalid, saves error details to state.
    """
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        profile_json = ctx.session.state.get("university_profile")
        if not profile_json:
            logger.warning("[ValidationFixer] No profile found in state.")
            yield Event(author=self.name)
            return

        try:
            # Parse if string
            if isinstance(profile_json, str):
                profile_json = fix_escape_sequences(profile_json)
                profile_json = fix_json_syntax(profile_json)
                try:
                    data = json.loads(profile_json)
                except json.JSONDecodeError as e:
                    ctx.session.state['validation_passed'] = False
                    ctx.session.state['validation_errors'] = f"JSON Decode Error: {e}"
                    yield Event(author=self.name)
                    return
            else:
                data = profile_json

            # Apply all deterministic fixes from validation_logic.py
            data, total_fixes = apply_all_fixes(data)
            
            # Update state with potentially fixed data
            ctx.session.state["university_profile"] = data
            if total_fixes > 0:
                logger.info(f"[ValidationFixer] Applied {total_fixes} deterministic fixes.")

            # Validate against Pydantic model
            try:
                UniversityProfile.model_validate(data)
                logger.info("[ValidationFixer] ✅ Profile matches schema!")
                ctx.session.state['validation_passed'] = True
                
                # IMPORTANT: Signal to LoopAgent to STOP
                yield Event(
                    author=self.name,
                    actions=EventActions(escalate=True)
                )
                
            except Exception as e:
                # Capture validation errors
                error_msg = str(e)
                # Try to get cleaner error message from Pydantic
                if hasattr(e, 'errors'):
                    details = []
                    for err in e.errors()[:3]:
                        loc = ".".join(str(l) for l in err['loc'])
                        msg = err['msg']
                        details.append(f"{loc}: {msg}")
                    error_msg = "; ".join(details)
                
                logger.warning(f"[ValidationFixer] ⚠️ Validation failed: {error_msg[:200]}...")
                ctx.session.state['validation_passed'] = False
                ctx.session.state['validation_errors'] = error_msg
                yield Event(author=self.name)

        except Exception as e:
            logger.error(f"[ValidationFixer] Critical Error: {e}")
            ctx.session.state['validation_passed'] = False
            ctx.session.state['validation_errors'] = f"Processing error: {str(e)}"
            yield Event(author=self.name)

llm_refiner_agent = LlmAgent(
    name="LlmRefinerAgent",
    model=MODEL_NAME,
    description="Fixes complex validation errors in the university profile JSON.",
    instruction="""You are a strict data validation agent.
Your Task: Fix the JSON object in state `university_profile` based on the validation errors in `validation_errors`.
    
RULES:
1. Read the full `university_profile` JSON.
2. Read the `validation_errors` from state.
3. Fix ONLY the fields mentioned in the errors.
4. Ensure the output strictly follows the schema.
5. If a field is required but missing/null, infer a reasonable value (e.g., 0 for numbers, "Not specified" for strings, [] for lists).
6. Output the FULL CORRECTED JSON.

Common Fixes:
- "Input should be a valid boolean" -> Convert "Yes"/"No" to true/false.
- "Input should be a valid integer" -> Convert strings to int, removing % or commas.
- "Field required" -> Add the field with a default value.
""",
    output_key="university_profile"
)

correction_loop = LoopAgent(
    name="CorrectionLoop",
    description="Iteratively fixes validation errors.",
    sub_agents=[
        ValidationFixer(name="ValidationFixer"),
        llm_refiner_agent
    ],
    max_iterations=3
)

# ==============================================================================
# PROFILE BUILDER AGENT
# ==============================================================================

profile_builder_agent = LlmAgent(
    name="ProfileBuilder",
    model=MODEL_NAME,
    description="Aggregates all research outputs into a structured UniversityProfile JSON.",
    instruction="""CRITICAL: You MUST aggregate ALL research outputs into a complete UniversityProfile.
DO NOT summarize, truncate, or omit ANY data from the sub-agent outputs.

=== INPUT DATA (from session state) ===
Read ALL of these state variables and include ALL their content:

1. strategy_output → Extract: metadata, strategic_profile (executive_summary, market_position, admissions_philosophy, us_news_rank, analyst_takeaways, campus_dynamics)
2. admissions_current_output → Extract: current_status (ALL acceptance rates, class size, test policy, early_admission_stats)
3. admissions_trends_output → Extract: longitudinal_trends (ALL 5 years of data including waitlist_stats)
4. admitted_profile_output → Extract: admitted_student_profile (gpa, testing, demographics with racial_breakdown)
5. colleges_output → Extract: academic_structure (structure_type, ALL colleges, minors_certificates)
6. majors_output → MERGE into colleges: For each college, add .majors array from majors_by_college
7. application_output → Extract: application_process (platforms, deadlines, supplemental_requirements, holistic_factors)
8. strategy_tactics_output → Extract: application_strategy (ALL tips and tactics)
9. financials_output → Extract: financials (tuition_and_fees, financial_aid_philosophy)
10. scholarships_output → MERGE into financials: Add ALL scholarships with full details (name, amount, eligibility)
11. credit_policies_output → Extract: credit_policies (ap_credits, ib_credits, transfer_articulation)
12. student_insights_output → Extract: student_insights (campus_dynamics, tips_and_hacks)
13. outcomes_output → Extract: outcomes (employment, median_earnings_10yr, top_employers) AND student_retention

=== OUTPUT STRUCTURE ===
Output this EXACT structure with ALL data preserved:

{
  "_id": "<snake_case of university_name>",
  "metadata": <from strategy_output>,
  "strategic_profile": <from strategy_output - PRESERVE ALL analyst_takeaways>,
  "admissions_data": {
    "current_status": <from admissions_current_output>,
    "longitudinal_trends": <from admissions_trends_output - ALL 5 years>,
    "admitted_student_profile": <from admitted_profile_output - ALL demographics>
  },
  "academic_structure": <from colleges_output WITH majors_output MERGED>,
  "application_process": <from application_output>,
  "application_strategy": <from strategy_tactics_output>,
  "financials": <from financials_output WITH scholarships_output MERGED>,
  "credit_policies": <from credit_policies_output>,
  "student_insights": <from student_insights_output>,
  "outcomes": <from outcomes_output>,
  "student_retention": <from outcomes_output>
}

=== RULES ===
1. PRESERVE ALL DATA - do not truncate or summarize
2. Include ALL array items (all years, all scholarships, all majors)
3. Include ALL nested objects with ALL their fields
4. Use null only for genuinely missing data
5. Ensure _id is snake_case of university name
6. Set last_updated to today's date
7. report_source_files should be empty list []
""",
    output_key="university_profile"
)

# ==============================================================================
# FILE SAVER AGENT
# ==============================================================================

file_saver_agent = LlmAgent(
    name="FileSaver",
    model=MODEL_NAME,
    description="Saves the final profile to a JSON file.",
    instruction="""YOU MUST CALL the write_file tool to save the profile.

=== STEP 1: Generate filename ===
Convert the university name to a lowercase slug:
- Replace spaces with underscores
- Remove punctuation
- Example: "UC San Diego" -> "uc_san_diego.json"

=== STEP 2: Prepare content ===
Take the complete JSON from {university_profile} and format it with proper indentation.

=== STEP 3: CALL THE TOOL ===
YOU MUST call write_file with these exact parameters:
- filename: the slug.json you generated
- content: the formatted JSON string
""",
    tools=[write_file],
    output_key="save_result"
)

# ==============================================================================
# PIPELINES
# ==============================================================================

# 1. Parallel Research
research_phase = ParallelAgent(
    name="ResearchPhase",
    sub_agents=[
        strategy_agent,
        admissions_current_agent,
        admissions_trends_agent,
        admitted_profile_agent,
        colleges_agent,
        majors_agent,
        application_agent,
        strategy_tactics_agent,
        financials_agent,
        scholarships_agent,
        credit_policies_agent,
        student_insights_agent,
        outcomes_agent
    ]
)

# 2. Sequential Pipeline (Build -> Save)
validation_and_save_pipeline = SequentialAgent(
    name="ValidationAndSavePipeline",
    sub_agents=[
        profile_builder_agent,
        file_saver_agent
    ]
)

# ==============================================================================
# ROOT AGENT
# ==============================================================================

input_tool = AgentTool(agent=university_name_extractor)
research_tool = AgentTool(
    agent=SequentialAgent(
        name="ResearchAndValidate",
        sub_agents=[state_initializer, research_phase, validation_and_save_pipeline]
    )
)

root_agent = LlmAgent(
    name="UniversityProfileCollector",
    model=MODEL_NAME,
    description="Orchestrates comprehensive university data collection with validation.",
    instruction="""When asked to research a university:
1. Call UniversityNameExtractor to get the university name
2. Call ResearchAndValidate to gather data, build profile, validate/fix it, and save it.

Confirm save and summarize key findings including:
- Acceptance rate and trends
- Waitlist statistics (conversion rate)
- Top employers and median earnings (ROI)
- Retention and graduation rates""",
    tools=[input_tool, research_tool]
)
