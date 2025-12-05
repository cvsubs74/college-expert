from typing import List, Optional
from pydantic import BaseModel, Field

# --- Metadata ---
class Location(BaseModel):
    city: str
    state: str
    type: str = Field(description="Public/Private")

class Metadata(BaseModel):
    official_name: str
    location: Location
    last_updated: str
    report_source_files: List[str] = []

# --- Strategic Profile ---
class AnalystTakeaway(BaseModel):
    category: str = Field(description="e.g., 'Selectivity', 'Financial', 'Academic'")
    insight: str
    implication: str

class RankingInfo(BaseModel):
    source: str = Field(description="e.g., 'US News', 'Niche', 'Forbes'")
    rank_overall: Optional[int] = None
    rank_category: Optional[str] = None  # e.g., "Public Universities"
    rank_in_category: Optional[int] = None
    year: Optional[int] = None

class CampusDynamics(BaseModel):  # NEW CLASS
    social_environment: str = Field(description="e.g., 'Socially Dead myth', 'Greek Life dominance'")
    transportation_impact: str = Field(description="e.g., 'Blue Line Trolley impact', 'Commuter school status'")
    research_impact: str = Field(description="e.g., 'Proximity to biotech', 'Undergrad research access'")

class StrategicProfile(BaseModel):
    executive_summary: str
    market_position: str
    admissions_philosophy: str
    rankings: List[RankingInfo] = []
    analyst_takeaways: List[AnalystTakeaway] = []
    campus_dynamics: Optional[CampusDynamics] = None

# --- Admissions Data ---
class EarlyAdmissionStats(BaseModel):
    plan_type: str = Field(description="ED, EA, REA, ED2")
    applications: Optional[int] = None
    admits: Optional[int] = None
    acceptance_rate: Optional[float] = None
    class_fill_percentage: Optional[float] = Field(None, description="% of class filled via this plan")

class CurrentStatus(BaseModel):
    overall_acceptance_rate: float = Field(description="percentage")
    in_state_acceptance_rate: Optional[float] = None
    out_of_state_acceptance_rate: Optional[float] = None
    international_acceptance_rate: Optional[float] = None
    transfer_acceptance_rate: Optional[float] = None
    admits_class_size: Optional[int] = None
    is_test_optional: bool
    test_policy_details: str = Field(description="e.g., 'Test Free', 'Test Required', 'Test Blind'")
    early_admission_stats: List[EarlyAdmissionStats] = []

class LongitudinalTrend(BaseModel):
    year: int = Field(description="e.g., 2025")
    cycle_name: str = Field(description="e.g., 'Class of 2029'")
    applications_total: int
    admits_total: int
    enrolled_total: int
    acceptance_rate_overall: float
    acceptance_rate_in_state: Optional[float] = None
    acceptance_rate_out_of_state: Optional[float] = None
    yield_rate: float
    waitlist_offered: Optional[int] = None
    waitlist_accepted: Optional[int] = None
    notes: str = Field(default="", description="e.g., 'First year of test-optional'")

class GPAProfile(BaseModel):
    weighted_middle_50: str = Field(description="e.g., '4.42-4.76'")
    unweighted_middle_50: str = ""
    average_weighted: Optional[float] = None
    percentile_25: Optional[str] = None
    percentile_75: Optional[str] = None
    notes: str = ""

class TestingProfile(BaseModel):
    sat_composite_middle_50: str = ""
    sat_reading_middle_50: Optional[str] = None
    sat_math_middle_50: Optional[str] = None
    act_composite_middle_50: str = ""
    act_english_middle_50: Optional[str] = None
    act_math_middle_50: Optional[str] = None
    submission_rate: Optional[float] = Field(None, description="percentage")
    policy_note: str = ""

class RegionBreakdown(BaseModel):
    region: str
    percentage: float

class GenderStats(BaseModel):  # NEW CLASS
    applicants: Optional[int] = None
    admits: Optional[int] = None
    acceptance_rate: Optional[float] = None
    note: str = ""

class GenderBreakdown(BaseModel):  # NEW CLASS
    men: Optional[GenderStats] = None
    women: Optional[GenderStats] = None
    non_binary: Optional[GenderStats] = None

class Demographics(BaseModel):
    first_gen_percentage: Optional[float] = None
    legacy_percentage: Optional[float] = None
    international_percentage: Optional[float] = None
    geographic_breakdown: List[RegionBreakdown] = []
    gender_breakdown: Optional[GenderBreakdown] = None    

class AdmittedStudentProfile(BaseModel):
    gpa: GPAProfile
    testing: TestingProfile
    demographics: Demographics

class AdmissionsData(BaseModel):
    current_status: CurrentStatus
    longitudinal_trends: List[LongitudinalTrend] = []
    admitted_student_profile: AdmittedStudentProfile

# --- Academic Structure ---
class Major(BaseModel):
    name: str = Field(description="e.g., 'Computer Science'")
    degree_type: str = Field(description="e.g., 'B.S.', 'B.A.'")
    is_impacted: bool = False
    acceptance_rate: Optional[float] = Field(None, description="Major-specific rate if different")
    average_gpa_admitted: Optional[float] = None
    prerequisite_courses: List[str] = Field(default=[], description="e.g., ['Calculus BC', 'Physics C']")
    special_requirements: str = ""
    admissions_pathway: str = Field(default="Direct Admit", description="e.g., 'Direct Admit only', 'Pre-Major'")
    internal_transfer_allowed: bool = True
    internal_transfer_gpa: Optional[float] = None
    notes: str = ""

class College(BaseModel):
    name: str
    admissions_model: str
    acceptance_rate_estimate: Optional[float] = None
    is_restricted_or_capped: bool = False
    strategic_fit_advice: str = Field(default="", description="Who should/shouldn't apply here")  # NEW
    housing_profile: str = Field(default="", description="Vibe of dorms/location")  # NEW
    student_archetype: str = Field(default="", description="The 'typical' student here")  # NEW
    majors: List[Major] = []

class AcademicStructure(BaseModel):
    structure_type: str = Field(default="Colleges", description="e.g., 'Colleges', 'Schools'")
    colleges: List[College] = []
    minors_certificates: List[str] = []

# --- Application Process ---
class ApplicationDeadline(BaseModel):
    plan_type: str = Field(description="e.g., 'Early Action', 'Regular Decision', 'ED2'")
    date: str = Field(description="ISO Date")
    is_binding: bool = False
    notes: str = ""

class SupplementalRequirement(BaseModel):
    target_program: str = Field(description="e.g., 'Architecture', 'School of Music', 'All'")
    requirement_type: str = Field(description="e.g., 'Portfolio', 'Audition', 'Video Intro', 'Essays'")
    deadline: str = ""
    details: str = ""

class HolisticFactors(BaseModel):
    primary_factors: List[str] = Field(default=[], description="e.g., 'Course Rigor', 'GPA', 'Essays'")
    secondary_factors: List[str] = []
    essay_importance: str = Field(default="High", description="Critical/High/Moderate/Low")
    demonstrated_interest: str = Field(default="Not Considered", description="Considered/Important/Not Considered")
    interview_policy: str = Field(default="Not Offered", description="Required/Recommended/Informational/Not Offered")
    legacy_consideration: str = Field(default="Unknown", description="Strong/Moderate/Minimal/None/Unknown")
    first_gen_boost: str = Field(default="Unknown", description="Strong/Moderate/Minimal/None/Unknown")
    specific_differentiators: str = ""

class ApplicationProcess(BaseModel):
    platforms: List[str] = Field(default=[], description="e.g., 'Common App', 'Coalition', 'UC Application'")
    application_deadlines: List[ApplicationDeadline] = []
    supplemental_requirements: List[SupplementalRequirement] = []
    holistic_factors: HolisticFactors = Field(default_factory=HolisticFactors)

# --- Financials ---
class InStateCosts(BaseModel):
    tuition: Optional[float] = None
    total_coa: Optional[float] = None
    housing: Optional[float] = None

class OutOfStateCosts(BaseModel):
    tuition: Optional[float] = None
    total_coa: Optional[float] = None
    supplemental_tuition: Optional[float] = None

class CostOfAttendanceBreakdown(BaseModel):
    academic_year: str = Field(default="", description="e.g., '2025-2026'")
    in_state: InStateCosts = Field(default_factory=InStateCosts)
    out_of_state: OutOfStateCosts = Field(default_factory=OutOfStateCosts)

class Scholarship(BaseModel):
    name: str = Field(description="e.g., 'Regents Scholarship'")
    type: str = Field(description="Merit/Need/Both")
    amount: str = ""
    deadline: str = ""
    benefits: str = Field(default="", description="e.g., 'Priority Registration', 'Housing Guarantee'")
    application_method: str = Field(default="", description="e.g., 'Automatic Consideration', 'Separate App'")

class Financials(BaseModel):
    tuition_model: str = Field(default="", description="e.g., 'Tuition Stability Plan', 'Annual Increase'")
    cost_of_attendance_breakdown: CostOfAttendanceBreakdown = Field(default_factory=CostOfAttendanceBreakdown)
    aid_philosophy: str = Field(default="", description="e.g., '100% Need Met', 'Merit Available', 'Need-Blind'")
    average_need_based_aid: Optional[float] = None
    average_merit_aid: Optional[float] = None
    percent_receiving_aid: Optional[float] = None
    scholarships: List[Scholarship] = []

# --- Credit Policies ---
class APPolicy(BaseModel):
    general_rule: str = Field(default="", description="e.g., 'Score of 3+ grants credit'")
    exceptions: List[str] = Field(default=[], description="e.g., 'No credit for Biology'")
    usage: str = Field(default="", description="e.g., 'Elective units only', 'Waives prerequisites'")

class IBPolicy(BaseModel):
    general_rule: str = Field(default="", description="e.g., 'HL 5+ only'")
    diploma_bonus: bool = False

class TransferArticulation(BaseModel):
    tools: List[str] = Field(default=[], description="e.g., 'ASSIST.org', 'Transferology'")
    restrictions: str = Field(default="", description="e.g., '70 unit cap'")

class CreditPolicies(BaseModel):
    philosophy: str = Field(default="", description="e.g., 'Generous Credit', 'Placement Only'")
    ap_policy: APPolicy = Field(default_factory=APPolicy)
    ib_policy: IBPolicy = Field(default_factory=IBPolicy)
    transfer_articulation: TransferArticulation = Field(default_factory=TransferArticulation)

# --- Student Insights ---
class StudentInsight(BaseModel):
    source: str = Field(description="e.g., 'Niche', 'College Confidential', 'Reddit'")
    category: str = Field(description="e.g., 'What It Takes', 'Essays', 'Activities'")
    insight: str

class StudentInsights(BaseModel):
    what_it_takes: List[str] = Field(default=[], description="Key factors from student perspectives")
    common_activities: List[str] = Field(default=[], description="Activities of admitted students")
    essay_tips: List[str] = Field(default=[], description="What works in essays")
    red_flags: List[str] = Field(default=[], description="Things to avoid")
    insights: List[StudentInsight] = []

class ApplicationStrategy(BaseModel):  
    major_selection_tactics: List[str] = Field(default=[], description="e.g., 'Don't list two selective majors'")
    college_ranking_tactics: List[str] = Field(default=[], description="e.g., 'Engineers should pick Warren'")
    alternate_major_strategy: str = Field(default="", description="How to pick a backup")

# --- Main Schema ---
class UniversityProfile(BaseModel):
    id: str = Field(alias="_id", description="slug, e.g., 'ut_austin'")
    metadata: Metadata
    strategic_profile: StrategicProfile
    admissions_data: AdmissionsData
    academic_structure: AcademicStructure
    application_process: ApplicationProcess
    application_strategy: ApplicationStrategy = Field(default_factory=ApplicationStrategy) # NEW SECTION
    financials: Financials
    credit_policies: CreditPolicies
    student_insights: StudentInsights

