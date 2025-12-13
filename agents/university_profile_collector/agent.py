import json
import logging
import os
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search, AgentTool, ToolContext

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
    description="Researches all majors with acceptance rates, prerequisites, WEEDER COURSES, and GPA FLOORS.",
    instruction="""Research: {university_name}

YOU MUST SEARCH for:
- Undergraduate majors list
- Impacted/capped majors lists
- "transferring into [Major] at [University]" to find HIDDEN PREREQUISITES
- Major-specific acceptance rates
- Departmental handbooks for GPA requirements

HIDDEN PREREQUISITES TO FIND:
- minimum_gpa_to_declare: GPA floor to switch INTO this major after enrolling
- weeder_courses: Courses that filter out students (e.g., "Organic Chemistry CHEM 140")
- direct_admit_only: If TRUE, NO internal transfers allowed - must apply as freshman

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
      "notes": "Extremely competitive, NO internal transfers"
    ),
    (
      "name": "Mechanical Engineering",
      "degree_type": "B.S.",
      "is_impacted": true,
      "acceptance_rate": 12.0,
      "average_gpa_admitted": 4.15,
      "prerequisite_courses": ["Calculus", "Physics", "Chemistry"],
      "minimum_gpa_to_declare": 3.2,
      "weeder_courses": ["ENGR 10 Intro to Engineering"],
      "special_requirements": null,
      "admissions_pathway": "Direct Admit",
      "internal_transfer_allowed": true,
      "direct_admit_only": false,
      "internal_transfer_gpa": 3.2,
      "notes": "Internal transfer possible but competitive"
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
      "notes": "Open major, easy to switch into"
    )
  ]
)

Use EXACT college names from the university.
Include 10-15 majors per college with REAL weeder courses.

ANTI-HALLUCINATION RULES:
- If you CANNOT FIND minimum_gpa_to_declare from official sources, use null. DO NOT GUESS.
- If weeder courses are unknown for a major, use empty array []. DO NOT INVENT course names.
- Only set direct_admit_only: true if the official page explicitly states "no internal transfers".

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
# PARALLEL RESEARCH GROUP (13 Agents)
# ==============================================================================

research_group = ParallelAgent(
    name="UniversityResearchGroup",
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
        outcomes_agent  # NEW AGENT 13
    ],
    description="Runs 13 specialized research agents in parallel."
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
- strategy_output: contains 'metadata', 'strategic_profile'
- admissions_current_output: contains 'current_status'
- admissions_trends_output: contains 'longitudinal_trends' (with waitlist_stats nested)
- admitted_profile_output: contains 'admitted_student_profile' (with racial_breakdown)
- colleges_output: contains 'academic_structure' with colleges array (majors = [] empty)
- majors_output: contains 'majors_by_college' dictionary keyed by college name
- application_output: contains 'application_process'
- strategy_tactics_output: contains 'application_strategy'
- financials_output: contains 'financials'
- scholarships_output: contains 'scholarships'
- credit_policies_output: contains 'credit_policies'
- student_insights_output: contains 'student_insights'
- outcomes_output: contains 'outcomes' and 'student_retention'

=== CRITICAL MERGE RULE FOR MAJORS ===
You MUST merge majors INTO each college. DO NOT keep majors_by_college as a separate field.

STEP BY STEP:
1. Take each college from academic_structure.colleges
2. Find the matching key in majors_by_college (e.g., "Jacobs School of Engineering")
3. Copy that array INTO the college's "majors" field

EXAMPLE:
If colleges_output has: 
  "colleges": [("name": "Jacobs School of Engineering", "majors": []), ...]
And majors_output has:
  "majors_by_college": ("Jacobs School of Engineering": [("name": "Computer Science", ...), ...])
  
RESULT should be:
  "colleges": [("name": "Jacobs School of Engineering", "majors": [("name": "Computer Science", ...)])]

DO NOT output majors_by_college as a separate field in academic_structure!

=== OTHER MERGE RULES ===
2. Add scholarships_output.scholarships INTO financials.scholarships
3. Create admissions_data object containing current_status, longitudinal_trends, admitted_student_profile
4. Add outcomes_output.outcomes as top-level "outcomes" field
5. Add outcomes_output.student_retention as top-level "student_retention" field

OUTPUT with EXACTLY this top-level structure:
(
  "_id": "university_name_slug",
  "metadata": ...,
  "strategic_profile": ...,
  "admissions_data": (
    "current_status": ...,
    "longitudinal_trends": [...with waitlist_stats nested...],
    "admitted_student_profile": (...with racial_breakdown...)
  ),
  "academic_structure": (
    "structure_type": "Colleges",
    "colleges": [
      (
        "name": "College Name",
        "majors": [...MERGED FROM majors_by_college...]
      )
    ],
    "minors_certificates": [...]
  ),
  "application_process": ...,
  "application_strategy": ...,
  "financials": (...WITH scholarships array...),
  "credit_policies": ...,
  "student_insights": ...,
  "outcomes": ...,
  "student_retention": ...
)

=== FORBIDDEN FIELDS (DO NOT CREATE) ===
- majors_by_college (must be merged into colleges)
- majors_by_academic_division
- waitlist_offered / waitlist_accepted (use waitlist_stats object instead)

=== REQUIRED NESTED FIELDS ===
- longitudinal_trends[].waitlist_stats object
- demographics.racial_breakdown object
- majors[].weeder_courses array
- majors[].minimum_gpa_to_declare number
- majors[].direct_admit_only boolean

OUTPUT valid JSON with curly braces (convert ( ) to curly braces).
""",
    output_key="final_profile"
)


# ==============================================================================
# FILE SAVER AGENT
# ==============================================================================

file_saver_agent = LlmAgent(
    name="FileSaver",
    model=MODEL_NAME,
    description="Saves the final profile to a JSON file.",
    instruction="""YOU MUST CALL the write_file tool to save the profile. This is mandatory.

=== STEP 1: Generate filename ===
Convert the university name to a lowercase slug:
- Replace spaces with underscores
- Remove punctuation
- Examples: "UC San Diego" -> "uc_san_diego.json"
           "Stanford University" -> "stanford_university.json"
           "University of California, Berkeley" -> "university_of_california_berkeley.json"

=== STEP 2: Prepare content ===
Take the complete JSON from {final_profile} and format it with proper indentation.

=== STEP 3: CALL THE TOOL ===
YOU MUST call write_file with these exact parameters:
- filename: the slug.json you generated
- content: the formatted JSON string

=== EXAMPLE TOOL CALL ===
write_file(filename="uc_san_diego.json", content=<the full JSON string>)

=== CRITICAL ===
- DO NOT skip this step
- DO NOT just describe what you would do
- ACTUALLY CALL the write_file tool
- After calling, confirm the file was saved successfully
""",
    tools=[write_file],
    output_key="save_result"
)


# ==============================================================================
# PIPELINES
# ==============================================================================

aggregator_pipeline = SequentialAgent(
    name="AggregatorPipeline",
    sub_agents=[profile_builder_agent, file_saver_agent],
    description="Builds structured profile, then saves to disk."
)

research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    sub_agents=[research_group, aggregator_pipeline],
    description="Parallel Research -> Profile Building -> File Save."
)


# ==============================================================================
# ROOT AGENT
# ==============================================================================

input_tool = AgentTool(agent=university_name_extractor)
research_tool = AgentTool(agent=research_pipeline)

root_agent = LlmAgent(
    name="UniversityProfileCollector",
    model=MODEL_NAME,
    description="Orchestrates comprehensive university data collection.",
    instruction="""When asked to research a university:
1. Call UniversityNameExtractor to get the university name
2. Call ResearchPipeline to gather data and save profile

Confirm save and summarize key findings including:
- Acceptance rate and trends
- Waitlist statistics (conversion rate)
- Top employers and median earnings (ROI)
- Retention and graduation rates""",
    tools=[input_tool, research_tool]
)
