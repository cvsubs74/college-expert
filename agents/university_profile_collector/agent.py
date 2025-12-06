import json
import logging
import os
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search, AgentTool, ToolContext

# Import models for validation reference
from .model import UniversityProfile

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
    description="Researches university rankings, market position, and campus dynamics.",
    instruction="""Research the university: {university_name}

SEARCH for: rankings (US News, Niche, Forbes), admissions philosophy, campus social life, transportation, research opportunities.

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
  "rankings": [
    (
      "source": "US News",
      "rank_overall": 35,
      "rank_category": "National Universities",
      "rank_in_category": 10,
      "year": 2025
    ),
    (
      "source": "Niche",
      "rank_overall": null,
      "rank_category": "Best Public Universities",
      "rank_in_category": 8,
      "year": 2025
    )
  ],
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

CRITICAL: Use EXACTLY these field names. Use ( ) instead of curly braces in your output.
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

SEARCH for: Common Data Set 2024, acceptance rates, test policy, early admission stats.

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
# AGENT 3: Admissions Trends Agent -> LongitudinalTrends
# ==============================================================================

admissions_trends_agent = LlmAgent(
    name="AdmissionsTrendsAgent",
    model=MODEL_NAME,
    description="Researches historical admissions trends over 3-5 years.",
    instruction="""Research: {university_name}

SEARCH for: admissions statistics 2024-2021, acceptance rate history, yield rates, waitlist data.

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
    "waitlist_offered": 15000,
    "waitlist_accepted": 10000,
    "notes": "Record number of applications"
  )
]

Include at least 3-5 years of data.
Use null for unknown values. Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="admissions_trends_output"
)


# ==============================================================================
# AGENT 4: Admitted Profile Agent -> AdmittedStudentProfile
# ==============================================================================

admitted_profile_agent = LlmAgent(
    name="AdmittedProfileAgent",
    model=MODEL_NAME,
    description="Researches admitted student statistics including GPA, test scores, and demographics.",
    instruction="""Research: {university_name}

SEARCH for: Common Data Set section C, PrepScholar stats, middle 50 scores, demographics, gender breakdown.

OUTPUT JSON with EXACTLY this structure:

"admitted_student_profile": (
  "gpa": (
    "weighted_middle_50": "4.10-4.30",
    "unweighted_middle_50": "3.80-4.00",
    "average_weighted": 4.20,
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
    )
  )
)

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
# AGENT 6: Majors Agent -> Majors by College
# ==============================================================================

majors_agent = LlmAgent(
    name="MajorsAgent",
    model=MODEL_NAME,
    description="Researches all majors with acceptance rates, prerequisites, and transfer policies.",
    instruction="""Research: {university_name}

SEARCH for: undergraduate majors list, impacted/capped majors, major-specific acceptance rates, internal transfer policies.

OUTPUT JSON with EXACTLY this structure:

"majors_by_college": (
  "College of Engineering": [
    (
      "name": "Computer Science",
      "degree_type": "B.S.",
      "is_impacted": true,
      "acceptance_rate": 8.0,
      "average_gpa_admitted": 4.25,
      "prerequisite_courses": ["Calculus AB/BC", "Physics", "Programming experience"],
      "special_requirements": null,
      "admissions_pathway": "Direct Admit",
      "internal_transfer_allowed": false,
      "internal_transfer_gpa": null,
      "notes": "Extremely competitive, apply directly as freshman"
    ),
    (
      "name": "Mechanical Engineering",
      "degree_type": "B.S.",
      "is_impacted": true,
      "acceptance_rate": 12.0,
      "average_gpa_admitted": 4.15,
      "prerequisite_courses": ["Calculus", "Physics"],
      "special_requirements": null,
      "admissions_pathway": "Direct Admit",
      "internal_transfer_allowed": true,
      "internal_transfer_gpa": 3.5,
      "notes": "Internal transfer possible with high GPA"
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
      "special_requirements": null,
      "admissions_pathway": "Pre-Major",
      "internal_transfer_allowed": true,
      "internal_transfer_gpa": 2.5,
      "notes": "Open major, easy to switch into"
    )
  ]
)

Use EXACT college names from the university.
Include 10-15 majors per college.
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
  ]
)

Include 3-5 items per category.
Use ( ) instead of curly braces.
""",
    tools=[google_search],
    output_key="student_insights_output"
)


# ==============================================================================
# PARALLEL RESEARCH GROUP (12 Agents)
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
        student_insights_agent
    ],
    description="Runs 12 specialized research agents in parallel."
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
- admissions_trends_output: contains 'longitudinal_trends'
- admitted_profile_output: contains 'admitted_student_profile'
- colleges_output: contains 'academic_structure'
- majors_output: contains 'majors_by_college'
- application_output: contains 'application_process'
- strategy_tactics_output: contains 'application_strategy'
- financials_output: contains 'financials'
- scholarships_output: contains 'scholarships'
- credit_policies_output: contains 'credit_policies'
- student_insights_output: contains 'student_insights'

MERGE RULES:
1. For each college in academic_structure.colleges, find matching key in majors_by_college 
   and copy the majors array into college.majors
2. Add scholarships_output.scholarships into financials.scholarships
3. Create admissions_data object containing current_status, longitudinal_trends, admitted_student_profile

OUTPUT with EXACTLY this top-level structure:
(
  "_id": "university_name_slug",
  "metadata": (from strategy_output),
  "strategic_profile": (from strategy_output),
  "admissions_data": (
    "current_status": (from admissions_current_output),
    "longitudinal_trends": (from admissions_trends_output),
    "admitted_student_profile": (from admitted_profile_output)
  ),
  "academic_structure": (from colleges_output WITH majors merged in),
  "application_process": (from application_output),
  "application_strategy": (from strategy_tactics_output),
  "financials": (from financials_output WITH scholarships merged in),
  "credit_policies": (from credit_policies_output),
  "student_insights": (from student_insights_output)
)

CRITICAL RULES:
- Output ONLY valid JSON with curly braces (convert any ( ) back to curly braces)
- Use EXACT field names shown above
- Do NOT invent new fields
- Do NOT create fields like "majors_by_academic_division" 
- Majors go INSIDE each college object, not at top level
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
    instruction="""Save the university profile to disk.

Call write_file with:
- filename: "<slug>.json" (e.g., "stanford_university.json", "uc_san_diego.json")
- content: JSON string of final_profile from session state (properly formatted with indentation)
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

Confirm save and summarize key findings.""",
    tools=[input_tool, research_tool]
)
