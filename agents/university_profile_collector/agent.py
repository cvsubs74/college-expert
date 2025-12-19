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
MODEL_NAME = "gemini-3-flash-preview"

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

SEARCH for: US News National Universities ranking 2026, admissions philosophy, campus social life, transportation, research opportunities.

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
      "insight": "Acceptance rate dropped 15% in 3 years",
      "implication": "Apply early to maximize chances"
    )
  ],
  "campus_dynamics": (
    "social_environment": "Description of social atmosphere",
    "transportation_impact": "How transport affects campus life",
    "research_impact": "Research opportunities and industry ties"
  )
)

CRITICAL: 
- us_news_rank must be the US News National Universities ranking (integer).
- Search for the latest 2026 ranking specifically.
- Use EXACTLY these field names. 
- Use ( ) instead of curly braces in your output.
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

SEARCH for: Common Data Set 2024 Section C, acceptance rates, test policy, early admission stats.

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
- Use null for unknown values
- Use ( ) instead of curly braces in your output
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

YOU MUST SEARCH for: 
- Common Data Set Section C2 (WAITLIST data specifically)
- Admissions statistics 2024-2021
- Acceptance rate history
- Yield rates

WAITLIST REQUIREMENTS (The "Black Box"):
- Find: applicants OFFERED waitlist spots
- Find: applicants who ACCEPTED waitlist spots  
- Find: applicants ADMITTED from waitlist
- CALCULATE: waitlist_admit_rate = (admitted / accepted) * 100
- Find: whether waitlist is RANKED or unranked

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

Include at least 3-5 years of data.
If a school HIDES waitlist data, explicitly note "Waitlist data not publicly disclosed" in notes.
Use null for unknown values. Use ( ) instead of curly braces.
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

SEARCH for: 
- Common Data Set Section C (GPA, test scores)
- Common Data Set Section B2 (RACIAL/ETHNIC breakdown)
- PrepScholar admitted student stats
- Niche demographics
- IPEDS data

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

SEARCH for: colleges/schools list, residential college system, housing reviews, student archetypes.

OUTPUT JSON with EXACTLY this structure:

"academic_structure": (
  "structure_type": "Colleges" or "Schools" or "Divisions",
  "colleges": [
    (
      "name": "College of Engineering",
      "admissions_model": "Direct Admit" or "Pre-Major" or "Lottery",
      "acceptance_rate_estimate": 15.0,
      "is_restricted_or_capped": true,
      "strategic_fit_advice": "Strong STEM background required",
      "housing_profile": "Modern dorms with maker spaces",
      "student_archetype": "Ambitious problem-solvers",
      "majors": []
    ),
    (
      "name": "College of Letters and Science",
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

IMPORTANT: Leave "majors": [] empty - MajorsAgent will populate it.
Use ( ) instead of curly braces.
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

YOU MUST SEARCH for:
- Undergraduate majors list
- Impacted/capped majors lists
- "transferring into [Major] at [University]" to find HIDDEN PREREQUISITES
- Major-specific acceptance rates
- Departmental handbooks for GPA requirements
- "[Major] curriculum [University]" for course requirements
- "[Major] faculty [University]" for professors
- Department "People" or "Faculty" pages
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

SEARCH for: application deadlines 2025, supplemental essays, demonstrated interest, interview policy.

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

SEARCH for: Reddit major selection tips, easier majors, college ranking strategies, alternate major advice.

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

SEARCH for: cost of attendance 2024-2025, tuition, financial aid statistics.

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

SEARCH for: merit scholarships, Regents Scholarship, full ride, departmental scholarships.

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

SEARCH for: AP credit policy, IB credit policy, ASSIST.org, transfer articulation.

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

SEARCH for: Niche reviews, Reddit accepted profiles, essays that worked, mistakes to avoid.

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
    instruction="""Aggregate all research outputs into a single UniversityProfile.
    
INPUTS FROM SESSION STATE:
- university_name
- strategy_output
- admissions_current_output
- admissions_trends_output
- admitted_profile_output
- colleges_output
- majors_output
- application_output
- strategy_tactics_output
- financials_output
- scholarships_output
- credit_policies_output
- student_insights_output
- outcomes_output

TASK:
1. Merge `colleges_output["academic_structure"]` with majors. Matches on college name.
   - For each college in `academic_structure.colleges`, find matching key in `majors_by_college`.
   - Set `college.majors = majors_by_college[college_name]`.
   
2. Construct the final `UniversityProfile` JSON.
   - Combine all sections.
   - Ensure `_id` is snake_case of university name.
   - Ensure `last_updated` is today's date.
   - Ensure `report_source_files` is empty list [].

3. OUTPUT the complete JSON object in `university_profile` key.
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

# 2. Sequential Validation Loop (Build -> Fix -> Save)
validation_and_save_pipeline = SequentialAgent(
    name="ValidationAndSavePipeline",
    sub_agents=[
        profile_builder_agent,
        correction_loop,
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
        sub_agents=[research_phase, validation_and_save_pipeline]
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
