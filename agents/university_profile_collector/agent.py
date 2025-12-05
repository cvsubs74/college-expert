import logging
import os
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search, AgentTool, ToolContext

# Import models
from .model import UniversityProfile

# Configure logging
logger = logging.getLogger(__name__)

# Common config
MODEL_NAME = "gemini-2.5-flash"

# Get the research directory path
RESEARCH_DIR = os.path.join(os.path.dirname(__file__), 'research')

# --- Write File Tool ---
def write_file(
    tool_context: ToolContext,
    filename: str,
    content: str
) -> dict:
    """
    Writes content to a file in the research directory.
    """
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    target_path = os.path.join(RESEARCH_DIR, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Saved file to: {target_path}")
    return {"status": "success", "path": target_path}


# --- 0. Input Parsing Agent ---
university_name_extractor = LlmAgent(
    name="UniversityNameExtractor",
    model=MODEL_NAME,
    description="Extracts the university name from the user's request.",
    instruction="""You are an expert entity extractor.
    Analyze the user's request to identify the target university name.
    
    Output strictly the university name (e.g., 'University of Texas at Austin', 'Stanford University').
    Do not add any other text.
    """,
    output_key="university_name"
)

# --- Sub-Agents ---

# 1. Strategy Agent - Rankings, Market Position & Campus Dynamics
strategy_agent = LlmAgent(
    name="StrategyAgent",
    model=MODEL_NAME,
    description="Researches university rankings, market position, campus dynamics, and strategic profile.",
    instruction="""You are a Strategic Analyst. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "site:usnews.com {{university_name}} ranking" - US News rankings
2. "site:niche.com {{university_name}} rankings" - Niche grades & rankings
3. "site:forbes.com {{university_name}} ranking" - Forbes rankings
4. "{{university_name}} admissions philosophy" - How they evaluate applicants
5. "site:reddit.com {{university_name}} socially dead" - Social atmosphere
6. "{{university_name}} student transport guide trolley shuttle" - Transportation
7. "{{university_name}} research opportunities undergrad biotech" - Research/Industry ties

EXTRACT:
1. **Metadata**: Official name, city, state, public/private
2. **Rankings**: 
   - US News overall rank, rank among publics/privates
   - Niche overall grade
   - Forbes rank if available
3. **Strategic Profile**:
   - Executive summary (2-3 sentences)
   - Market position (e.g., "Public Ivy", "Hidden Gem", "Elite Private")
   - Admissions philosophy (holistic? test-free? numbers-focused?)
4. **Analyst Takeaways**: 3-5 key insights with implications
5. **Campus Dynamics** (NEW):
   - Social environment (e.g., "Socially Dead myth", "Greek Life dominance", "Commuter school vibe")
   - Transportation impact (e.g., "Blue Line Trolley access", "Isolated campus", "Walking distance to downtown")
   - Research/Industry ties (e.g., "Adjacent to biotech hub", "Strong undergrad research", "Industry internship pipeline")

Output as JSON with keys: 'metadata', 'strategic_profile' (including 'rankings' array AND 'campus_dynamics' object).
""",
    tools=[google_search],
    output_key="strategy_output"
)

# 2. Admissions Agent - Stats, Trends & Gender Data
admissions_agent = LlmAgent(
    name="AdmissionsAgent",
    model=MODEL_NAME,
    description="Researches admissions statistics including gender breakdowns from official and crowdsourced data.",
    instruction="""You are an Admissions Data Analyst. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "{{university_name}} Common Data Set" - Official stats (Section C)
2. "site:usnews.com {{university_name}} acceptance rate" - US News data
3. "site:niche.com {{university_name}} admissions" - Niche acceptance data & grades
4. "site:prepscholar.com {{university_name}}" - SAT/ACT ranges
5. "{{university_name}} early decision acceptance rate" - ED/EA advantage
6. "{{university_name}} waitlist statistics" - Waitlist data
7. "{{university_name}} acceptance rate by gender" - Men vs Women stats
8. "{{university_name}} common data set section C15" - Gender demographics
9. "site:univstats.com {{university_name}} gender admission" - Federal IPEDS gender data

EXTRACT:
1. **Current Status**:
   - Overall acceptance rate
   - In-state vs out-of-state rates (for public schools)
   - International acceptance rate
   - Transfer acceptance rate
   - Test policy (required/optional/blind/free)
   - Early Decision/Action stats (ED rate, ED2 rate, EA rate, % of class filled via ED)

2. **Longitudinal Trends** (last 3-5 years):
   - Applications, admits, enrolled each year
   - Acceptance rate trend (increasing/decreasing selectivity)
   - Waitlist offered/accepted numbers
   - Notable policy changes

3. **Admitted Student Profile**:
   - GPA: weighted middle 50%, unweighted if available
   - SAT: composite middle 50%, math/reading breakdowns
   - ACT: composite middle 50%, section breakdowns
   - Demographics: first-gen %, legacy %, geographic breakdown

4. **Gender Breakdown** (Crucial for STEM schools):
   - Men: Applicants count, Admits count, Acceptance Rate
   - Women: Applicants count, Admits count, Acceptance Rate
   - Note any significant disparity (e.g., "Engineering: Men 15%, Women 25%")

Output as JSON with key: 'admissions_data' (include 'gender_breakdown' in demographics).
""",
    tools=[google_search],
    output_key="admissions_output"
)

# 3. Academic Structure Agent - Majors, Programs & College Vibes
academic_structure_agent = LlmAgent(
    name="AcademicStructureAgent",
    model=MODEL_NAME,
    description="Researches academic programs, majors, and residential college dynamics.",
    instruction="""You are an Academic Programs Analyst. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "{{university_name}} undergraduate majors list" - All majors
2. "{{university_name}} colleges schools" - Academic structure
3. "site:niche.com {{university_name}} majors" - Popular majors & reviews
4. "{{university_name}} computer science acceptance rate" - CS-specific
5. "{{university_name}} engineering acceptance rate" - Engineering-specific
6. "{{university_name}} business acceptance rate" - Business-specific
7. "{{university_name}} impacted majors" - Which majors are competitive
8. "{{university_name}} change of major policy" - Internal transfer rules
9. "site:reddit.com {{university_name}} ranking colleges" - Student advice on residential colleges
10. "{{university_name}} college housing reviews" - College/dorm experiences

EXTRACT:
1. **Structure Type**: Colleges/Schools organization
2. **For Each College/School** (Crucial for residential college systems like UCSD, Rice, Yale):
   - Name (e.g., "Revelle College", "College of Engineering")
   - Admissions model (Direct Entry, Pre-Major, Separate Application)
   - Acceptance rate if different from overall
   - **Strategic Fit Advice**: Who should/shouldn't apply here (e.g., "Avoid Revelle if Engineering major - harsh GE requirements")
   - **Housing Profile**: Vibe/Architecture (e.g., "Brutalist concrete", "Resort-like modern", "Traditional dorms")
   - **Student Archetype**: The stereotypical student (e.g., "The Overachiever", "The STEM Nerd", "The Humanities Scholar")
   
3. **For Key Majors** (CS, Engineering, Business, Nursing, etc.):
   - Name and degree type
   - Is it impacted/capped/selective?
   - Major-specific acceptance rate if known
   - Average GPA of admitted students to this major
   - Prerequisite courses (e.g., "Must have Calculus BC")
   - Internal transfer policy (allowed? GPA required?)
   
4. **Minors/Certificates**: List available

Output as JSON with key: 'academic_structure'.
""",
    tools=[google_search],
    output_key="academic_structure_output"
)

# 4. Application Process Agent
application_agent = LlmAgent(
    name="ApplicationAgent",
    model=MODEL_NAME,
    description="Researches application requirements, deadlines, and evaluation factors.",
    instruction="""You are an Application Process Analyst. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "{{university_name}} application deadlines" - All deadlines
2. "{{university_name}} supplemental essays" - Essay requirements
3. "{{university_name}} what we look for applicants" - Evaluation criteria
4. "{{university_name}} demonstrated interest" - Does it matter?
5. "{{university_name}} interview policy" - Interview requirements
6. "{{university_name}} legacy admissions" - Legacy consideration
7. "site:niche.com {{university_name}} application" - Student tips

EXTRACT:
1. **Platforms**: Common App, Coalition, school-specific, UC App, etc.
2. **Deadlines**:
   - Early Decision (is it binding?)
   - Early Action
   - Regular Decision
   - ED2 if applicable
   - Scholarship priority deadlines
3. **Supplemental Requirements**:
   - Number and type of essays
   - Portfolio requirements (art, architecture)
   - Audition requirements (music, theater)
4. **Holistic Factors**:
   - Primary factors (GPA, rigor, essays, etc.)
   - Secondary factors
   - Essay importance (Critical/High/Moderate/Low)
   - Demonstrated interest policy
   - Interview policy
   - Legacy consideration strength
   - First-generation boost

Output as JSON with key: 'application_process'.
""",
    tools=[google_search],
    output_key="application_output"
)

# 5. Financials Agent
financials_agent = LlmAgent(
    name="FinancialsAgent",
    model=MODEL_NAME,
    description="Researches cost of attendance, financial aid, and scholarships.",
    instruction="""You are a Financial Aid Analyst. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "{{university_name}} cost of attendance" - Official COA
2. "{{university_name}} tuition fees" - In-state vs out-of-state
3. "{{university_name}} financial aid statistics" - Aid info
4. "{{university_name}} merit scholarships" - Merit-based aid
5. "{{university_name}} Common Data Set Section H" - Aid statistics

EXTRACT:
1. **Cost of Attendance** (current academic year):
   - In-state tuition, total COA, housing
   - Out-of-state tuition, total COA
2. **Aid Philosophy**: Need-blind? Meets 100% need? Merit available?
3. **Statistics**:
   - Average need-based aid
   - Average merit aid
   - Percent receiving any aid
4. **Key Scholarships**:
   - Name, type (merit/need), amount range
   - Deadlines and application method
   - Benefits beyond money (priority registration, housing, etc.)

Output as JSON with key: 'financials'.
""",
    tools=[google_search],
    output_key="financials_output"
)

# 6. Credit Policies Agent
credit_policies_agent = LlmAgent(
    name="CreditPoliciesAgent",
    model=MODEL_NAME,
    description="Researches AP, IB, and transfer credit policies.",
    instruction="""You are a Credit Policy Analyst. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "{{university_name}} AP credit policy" - AP scores and credits
2. "{{university_name}} IB credit policy" - IB handling
3. "{{university_name}} transfer credit" - Transfer policies
4. "site:assist.org {{university_name}}" - Articulation (CA schools)

EXTRACT:
1. **Philosophy**: Generous? Placement only? Major-specific restrictions?
2. **AP Policy**:
   - General rule (what scores get credit)
   - Exceptions (subjects denied credit)
   - Usage (elective only? satisfies requirements?)
3. **IB Policy**:
   - HL vs SL treatment
   - Diploma bonus
4. **Transfer Articulation**:
   - Tools used (ASSIST, Transferology)
   - Unit caps and restrictions

Output as JSON with key: 'credit_policies'.
""",
    tools=[google_search],
    output_key="credit_policies_output"
)

# 7. Student Insights & Application Strategy Agent
student_insights_agent = LlmAgent(
    name="StudentInsightsAgent",
    model=MODEL_NAME,
    description="Researches crowdsourced insights and application gaming strategies.",
    instruction="""You are a Student Insights & Tactical Strategist. Research the university: {{university_name}}.

SEARCH THESE SOURCES:
1. "site:niche.com {{university_name}} what it takes to get in" - Niche tips
2. "site:collegeconfidential.com {{university_name}} accepted stats" - CC admit profiles
3. "site:reddit.com {{university_name}} got accepted" - Reddit success stories
4. "{{university_name}} essays that worked" - Essay examples
5. "site:collegeconfidential.com {{university_name}} what activities" - Activities that help
6. "{{university_name}} what admissions officers look for" - Official guidance
7. "how to game {{university_name}} admissions" - Tactical advice
8. "site:reddit.com {{university_name}} alternate major strategy" - Major selection tricks
9. "site:collegeconfidential.com {{university_name}} alternate major" - Gaming major slots
10. "{{university_name}} ranking colleges for engineering" - College preference strategy

EXTRACT:
1. **What It Takes** (key success factors from student perspectives):
   - Common themes among accepted students
   - Unique qualities that stood out
   
2. **Common Activities** of admitted students:
   - Leadership roles, clubs, sports
   - Research, internships, jobs
   - Community service patterns
   
3. **Essay Tips**:
   - Topics that worked
   - Writing style preferences
   - Things to avoid
   
4. **Red Flags** (things to avoid):
   - Common rejection reasons mentioned
   - Mistakes students report making

5. **Application Strategy (Gaming the System)**:
   - **Major Selection Tactics**: Advice on primary vs. alternate majors (e.g., "Don't list two selective/capped majors", "Use undeclared as safety")
   - **College/Campus Ranking Tactics**: Strategic ordering of college preferences (e.g., "Engineers should pick Warren over Revelle")
   - **Alternate Major Strategy**: Best "safe" majors to list as backups (e.g., "Cognitive Science is good backup for CS rejects")

Output as JSON with keys: 'student_insights' AND 'application_strategy'.
""",
    tools=[google_search],
    output_key="student_insights_output"
)

# --- Parallel Group ---
research_group = ParallelAgent(
    name="UniversityResearchGroup",
    sub_agents=[
        strategy_agent,
        admissions_agent,
        academic_structure_agent,
        application_agent,
        financials_agent,
        credit_policies_agent,
        student_insights_agent
    ],
    description="Runs specialized research agents in parallel."
)

# --- Profile Builder Agent ---
profile_builder_agent = LlmAgent(
    name="ProfileBuilder",
    model=MODEL_NAME,
    description="Aggregates research outputs into a structured UniversityProfile JSON.",
    instruction="""You are the Lead Analyst. Create the final university profile as a JSON object.

SESSION STATE CONTAINS:
- university_name
- strategy_output: 'metadata', 'strategic_profile' (with 'rankings' AND 'campus_dynamics')
- admissions_output: 'admissions_data' (current_status, longitudinal_trends, admitted_student_profile with 'gender_breakdown')
- academic_structure_output: 'academic_structure' (colleges with 'strategic_fit_advice', 'housing_profile', 'student_archetype')
- application_output: 'application_process' (with holistic_factors)
- financials_output: 'financials'
- credit_policies_output: 'credit_policies'
- student_insights_output: 'student_insights' AND 'application_strategy' (NEW)

CREATE A COMPLETE JSON PROFILE with this structure:
{
  "_id": "<snake_case_slug>",
  "metadata": { "official_name": "...", "location": {...}, "last_updated": "...", "report_source_files": [] },
  "strategic_profile": { 
    "executive_summary": "...", 
    "market_position": "...", 
    "admissions_philosophy": "...", 
    "rankings": [...], 
    "analyst_takeaways": [...],
    "campus_dynamics": { "social_environment": "...", "transportation_impact": "...", "research_impact": "..." }
  },
  "admissions_data": {
    "current_status": { "overall_acceptance_rate": ..., "in_state_acceptance_rate": ..., "is_test_optional": ..., "test_policy_details": "...", "early_admission_stats": [...] },
    "longitudinal_trends": [...],
    "admitted_student_profile": { 
      "gpa": {...}, 
      "testing": {...}, 
      "demographics": { ..., "gender_breakdown": { "men": {...}, "women": {...} } } 
    }
  },
  "academic_structure": { 
    "structure_type": "...", 
    "colleges": [{ "name": "...", "strategic_fit_advice": "...", "housing_profile": "...", "student_archetype": "...", ... }], 
    "minors_certificates": [...] 
  },
  "application_process": { "platforms": [...], "application_deadlines": [...], "supplemental_requirements": [...], "holistic_factors": {...} },
  "application_strategy": { 
    "major_selection_tactics": [...], 
    "college_ranking_tactics": [...], 
    "alternate_major_strategy": "..." 
  },
  "financials": { "tuition_model": "...", "cost_of_attendance_breakdown": {...}, "aid_philosophy": "...", "scholarships": [...] },
  "credit_policies": { "philosophy": "...", "ap_policy": {...}, "ib_policy": {...}, "transfer_articulation": {...} },
  "student_insights": { "what_it_takes": [...], "common_activities": [...], "essay_tips": [...], "red_flags": [...] }
}

Output ONLY the valid JSON object, no markdown code blocks or extra text.
Fill reasonable defaults for any missing fields. Use null for truly unknown numeric values.
""",
    output_key="final_profile"
)


# --- File Saver Agent ---
file_saver_agent = LlmAgent(
    name="FileSaver",
    model=MODEL_NAME,
    description="Saves the final profile to a JSON file.",
    instruction=f"""You are a File Manager. Save the university profile to disk.

Session state contains:
- final_profile: The complete UniversityProfile JSON
- university_name: The name of the university

MUST call write_file with:
- filename: "<slug>.json" (e.g., "stanford_university.json")
- content: JSON string of final_profile

Confirm the file was saved.
""",
    tools=[write_file],
    output_key="save_result"
)

# --- Aggregator Pipeline ---
aggregator_pipeline = SequentialAgent(
    name="AggregatorPipeline",
    sub_agents=[
        profile_builder_agent,
        file_saver_agent
    ],
    description="Builds structured profile, then saves to disk."
)

# --- Research Pipeline ---
research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    sub_agents=[
        research_group,
        aggregator_pipeline
    ],
    description="Parallel Research -> Profile Building -> File Save."
)

# --- Agent Tools ---
input_tool = AgentTool(agent=university_name_extractor)
research_tool = AgentTool(agent=research_pipeline)

# --- Main Agent ---
root_agent = LlmAgent(
    name="UniversityProfileCollector",
    model=MODEL_NAME,
    description="Orchestrates comprehensive university data collection.",
    instruction="""You are the University Profile Collector.

When asked to research a university:

1. EXTRACT NAME: Call UniversityNameExtractor with user's message
2. RUN RESEARCH: Call ResearchPipeline

The pipeline will:
- Run 7 parallel research agents (strategy, admissions, academics, application, financials, credits, student insights)
- Aggregate into structured profile with campus dynamics, gender breakdown, college vibes, and application strategy
- Save to research/<university_slug>.json

After completion, confirm the profile was saved and summarize key findings.
""",
    tools=[
        input_tool,
        research_tool
    ]
)
