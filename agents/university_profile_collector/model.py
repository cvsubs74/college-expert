"""
University Profile Data Model

This module defines the complete data structure for university profiles.
Each class is annotated with:
- AGENT: Which sub-agent is responsible for fetching this data
- [REQUIRED] / [OPTIONAL]: Whether the field must be populated
- Source: Where to find this data (search hints)
- Example: Sample values

AGENT MAPPING (13 Agents):
1. StrategyAgent -> Metadata, StrategicProfile
2. AdmissionsCurrentAgent -> CurrentStatus
3. AdmissionsTrendsAgent -> LongitudinalTrends (includes WaitlistDetailedStats)
4. AdmittedProfileAgent -> AdmittedStudentProfile (GPA, Testing, Demographics, RaceEthnicity)
5. CollegesAgent -> College structure, housing, archetypes
6. MajorsAgent -> Major details per college (includes Impaction Details)
7. ApplicationAgent -> Deadlines, supplementals, holistic factors
8. StrategyTacticsAgent -> ApplicationStrategy (gaming tactics)
9. FinancialsAgent -> Cost of attendance, aid philosophy
10. ScholarshipsAgent -> All scholarships
11. CreditPoliciesAgent -> AP/IB/Transfer policies
12. StudentInsightsAgent -> Crowdsourced tips
13. OutcomesAgent -> Career ROI, Retention, Earnings
"""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


# ==============================================================================
# AGENT: StrategyAgent
# Responsible for: Metadata + StrategicProfile
# Sources: Official website, US News, Niche, Forbes, Reddit
# ==============================================================================

class Location(BaseModel):
    """Geographic location of the university."""
    city: str = Field(
        description="[REQUIRED] City name. Source: Official website. Example: 'San Diego'"
    )
    state: str = Field(
        description="[REQUIRED] State abbreviation or name. Source: Official website. Example: 'California' or 'CA'"
    )
    type: str = Field(
        description="[REQUIRED] Institution type. Values: 'Public' or 'Private'. Source: Official website"
    )


class Metadata(BaseModel):
    """Basic identifying information about the university."""
    official_name: str = Field(
        description="[REQUIRED] Full official name. Source: Official website. Example: 'University of California, San Diego'"
    )
    location: Location = Field(
        description="[REQUIRED] Geographic location details"
    )
    last_updated: str = Field(
        description="[REQUIRED] ISO date of data collection. Format: 'YYYY-MM-DD'. Auto-generated"
    )
    report_source_files: List[str] = Field(
        default=[],
        description="[OPTIONAL] List of source files used. Auto-populated"
    )


class AnalystTakeaway(BaseModel):
    """Key insight with strategic implication."""
    category: str = Field(
        description="[REQUIRED] Category of insight. Examples: 'Selectivity', 'Financial', 'Academic', 'Culture'"
    )
    insight: str = Field(
        description="[REQUIRED] The key finding. Example: 'Acceptance rate dropped 15% in 3 years'"
    )
    implication: str = Field(
        description="[REQUIRED] What this means for applicants. Example: 'Apply ED to maximize chances'"
    )



class CampusDynamics(BaseModel):
    """Campus culture, transportation, and research environment."""
    social_environment: str = Field(
        description="[REQUIRED] Social atmosphere description. Source: Reddit, Niche reviews. "
                    "Examples: 'Socially Dead myth - actually vibrant', 'Greek Life dominant', 'Commuter school vibe'"
    )
    transportation_impact: str = Field(
        description="[REQUIRED] How transportation affects campus life. Source: Reddit, student reviews. "
                    "Examples: 'Blue Line Trolley connects to downtown', 'Isolated campus needs car', 'Walking campus'"
    )
    research_impact: str = Field(
        description="[REQUIRED] Research opportunities and industry connections. Source: Official research page. "
                    "Examples: 'Adjacent to biotech hub', 'Strong undergrad research programs', 'Industry internship pipeline'"
    )


class StrategicProfile(BaseModel):
    """High-level strategic overview of the university."""
    executive_summary: str = Field(
        description="[REQUIRED] 2-3 sentence overview. Captures essence of the school for quick understanding"
    )
    market_position: str = Field(
        description="[REQUIRED] How the school is perceived. Examples: 'Public Ivy', 'Hidden Gem', 'Elite Private', 'Regional Leader'"
    )
    admissions_philosophy: str = Field(
        description="[REQUIRED] How they evaluate applicants. Examples: 'Holistic review', 'Numbers-focused', 'Test-free pioneer'"
    )
    us_news_rank: Optional[int] = Field(
        default=None,
        description="[REQUIRED] US News National Universities ranking. Source: Search 'site:usnews.com {university} ranking'. Example: 15"
    )
    analyst_takeaways: List[AnalystTakeaway] = Field(
        default=[],
        description="[REQUIRED] 3-5 key strategic insights with implications for applicants"
    )
    campus_dynamics: Optional[CampusDynamics] = Field(
        default=None,
        description="[REQUIRED] Campus culture, transportation, research environment details"
    )


# ==============================================================================
# AGENT: AdmissionsCurrentAgent
# Responsible for: CurrentStatus (latest admissions cycle data)
# Sources: Common Data Set Section C, US News, Niche, Official admissions
# ==============================================================================

class EarlyAdmissionStats(BaseModel):
    """Statistics for a specific early admission plan."""
    plan_type: str = Field(
        description="[REQUIRED] Type of early plan. Values: 'ED' (Early Decision), 'EA' (Early Action), "
                    "'REA' (Restrictive Early Action), 'ED2' (Early Decision 2)"
    )
    applications: Optional[int] = Field(
        default=None,
        description="[OPTIONAL] Number of applications received for this plan. Source: Common Data Set"
    )
    admits: Optional[int] = Field(
        default=None,
        description="[OPTIONAL] Number admitted through this plan. Source: Common Data Set"
    )
    acceptance_rate: Optional[float] = Field(
        default=None,
        description="[REQUIRED if plan exists] Acceptance rate as percentage. Example: 18.5"
    )
    class_fill_percentage: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Percentage of class filled via this plan. Example: 45.0 means 45% of class"
    )


class CurrentStatus(BaseModel):
    """Current admissions cycle statistics."""
    overall_acceptance_rate: float = Field(
        description="[REQUIRED] Overall acceptance rate as percentage. Source: Common Data Set Section C. Example: 23.5"
    )
    in_state_acceptance_rate: Optional[float] = Field(
        default=None,
        description="[REQUIRED for public schools] In-state acceptance rate. Source: Common Data Set"
    )
    out_of_state_acceptance_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Out-of-state acceptance rate. Source: Common Data Set"
    )
    international_acceptance_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] International student acceptance rate. Often lower than domestic"
    )
    transfer_acceptance_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Transfer student acceptance rate. Source: Common Data Set Section D"
    )
    admits_class_size: Optional[int] = Field(
        default=None,
        description="[OPTIONAL] Total number of students in admitted class"
    )
    is_test_optional: bool = Field(
        description="[REQUIRED] Whether standardized tests are optional. True/False"
    )
    test_policy_details: str = Field(
        description="[REQUIRED] Detailed test policy. Values: 'Test Required', 'Test Optional', "
                    "'Test Free', 'Test Blind', 'Test Flexible'"
    )
    early_admission_stats: List[EarlyAdmissionStats] = Field(
        default=[],
        description="[REQUIRED] Stats for each early admission plan offered (ED, EA, REA, ED2)"
    )


# ==============================================================================
# AGENT: AdmissionsTrendsAgent
# Responsible for: LongitudinalTrends (includes WaitlistDetailedStats)
# Sources: Common Data Set archives, Prep Scholar, news articles
# ==============================================================================

class WaitlistDetailedStats(BaseModel):
    """Detailed breakdown of waitlist outcomes (The 'Black Box')."""
    year: int = Field(
        description="[REQUIRED] Cycle year. Example: 2024"
    )
    offered_spots: Optional[int] = Field(
        default=None,
        description="[REQUIRED] Total students offered a waitlist spot. Source: Common Data Set Section C2"
    )
    accepted_spots: Optional[int] = Field(
        default=None,
        description="[REQUIRED] Total students who accepted a waitlist spot. Source: Common Data Set Section C2"
    )
    admitted_from_waitlist: Optional[int] = Field(
        default=None,
        description="[REQUIRED] Total students admitted from the waitlist. Source: Common Data Set Section C2"
    )
    waitlist_admit_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Calculated conversion rate: (admitted / accepted) * 100"
    )
    is_waitlist_ranked: bool = Field(
        default=False,
        description="[REQUIRED] Whether waitlist positions are ranked. Source: Common Data Set Section C2"
    )


class LongitudinalTrend(BaseModel):
    """Admissions data for a single year."""
    year: int = Field(
        description="[REQUIRED] Application year. Example: 2025 (for Class of 2029)"
    )
    cycle_name: str = Field(
        description="[REQUIRED] Graduating class name. Example: 'Class of 2029'"
    )
    applications_total: int = Field(
        description="[REQUIRED] Total applications received. Source: Common Data Set/news"
    )
    admits_total: int = Field(
        description="[REQUIRED] Total students admitted"
    )
    enrolled_total: Optional[int] = Field(
        default=None,
        description="[REQUIRED] Total students enrolled (matriculated)"
    )
    acceptance_rate_overall: float = Field(
        description="[REQUIRED] Overall acceptance rate as percentage"
    )
    acceptance_rate_in_state: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] In-state acceptance rate for this year"
    )
    acceptance_rate_out_of_state: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Out-of-state acceptance rate for this year"
    )
    yield_rate: Optional[float] = Field(
        default=None,
        description="[REQUIRED] Percentage of admitted students who enrolled. Example: 42.5"
    )
    waitlist_stats: Optional[WaitlistDetailedStats] = Field(
        default=None,
        description="[REQUIRED] Detailed waitlist statistics. REPLACES flat waitlist fields"
    )
    notes: str = Field(
        default="",
        description="[OPTIONAL] Notable events. Examples: 'First year of test-optional', 'Record applications'"
    )


# ==============================================================================
# AGENT: AdmittedProfileAgent
# Responsible for: GPA, Testing, Demographics (includes RaceEthnicity)
# Sources: Common Data Set Sections C, PrepScholar, Niche, IPEDS
# ==============================================================================

class GPAProfile(BaseModel):
    """GPA statistics of admitted students."""
    weighted_middle_50: Optional[str] = Field(
        default=None,
        description="[REQUIRED] Weighted GPA middle 50% range. Format: 'X.XX-X.XX'. Example: '4.42-4.76'"
    )
    unweighted_middle_50: Optional[str] = Field(
        default="",
        description="[OPTIONAL] Unweighted GPA middle 50%. Example: '3.85-4.00'"
    )
    average_weighted: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Average weighted GPA. Example: 4.58"
    )
    percentile_25: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] 25th percentile GPA"
    )
    percentile_75: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] 75th percentile GPA"
    )
    notes: str = Field(
        default="",
        description="[OPTIONAL] Additional GPA context. Example: 'Recalculated without PE/non-academic'"
    )


class TestingProfile(BaseModel):
    """Standardized test statistics of admitted students."""
    sat_composite_middle_50: Optional[str] = Field(
        default=None,
        description="[REQUIRED] SAT composite middle 50%. Format: 'XXXX-XXXX'. Example: '1400-1530'"
    )
    sat_reading_middle_50: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] SAT Reading/Writing section middle 50%"
    )
    sat_math_middle_50: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] SAT Math section middle 50%"
    )
    act_composite_middle_50: Optional[str] = Field(
        default=None,
        description="[REQUIRED] ACT composite middle 50%. Format: 'XX-XX'. Example: '31-35'"
    )
    act_english_middle_50: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] ACT English section middle 50%"
    )
    act_math_middle_50: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] ACT Math section middle 50%"
    )
    submission_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Percentage of admits who submitted test scores. Example: 65.0"
    )
    policy_note: str = Field(
        default="",
        description="[OPTIONAL] Test policy notes. Example: 'Scores optional but considered if submitted'"
    )


class RegionBreakdown(BaseModel):
    """Geographic distribution of students."""
    region: str = Field(
        description="[REQUIRED] Region or state name. Examples: 'California', 'Northeast', 'International'"
    )
    percentage: float = Field(
        description="[REQUIRED] Percentage from this region. Example: 35.5"
    )


class GenderStats(BaseModel):
    """Admissions statistics by gender."""
    applicants: Optional[int] = Field(
        default=None,
        description="[OPTIONAL] Number of applicants of this gender"
    )
    admits: Optional[int] = Field(
        default=None,
        description="[OPTIONAL] Number admitted of this gender"
    )
    acceptance_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Acceptance rate for this gender. Important for STEM schools"
    )
    note: str = Field(
        default="",
        description="[OPTIONAL] Notes. Example: 'Higher rate for women in Engineering'"
    )


class GenderBreakdown(BaseModel):
    """Gender-based admissions breakdown."""
    men: Optional[GenderStats] = Field(
        default=None,
        description="[REQUIRED] Male applicant/admit statistics"
    )
    women: Optional[GenderStats] = Field(
        default=None,
        description="[REQUIRED] Female applicant/admit statistics"
    )
    non_binary: Optional[GenderStats] = Field(
        default=None,
        description="[OPTIONAL] Non-binary statistics if reported"
    )


class RaceEthnicityStats(BaseModel):
    """Detailed US Census/IPEDS racial and ethnic breakdown."""
    white: Optional[float] = Field(default=None)
    black_african_american: Optional[float] = Field(default=None)
    hispanic_latino: Optional[float] = Field(default=None)
    asian: Optional[float] = Field(default=None)
    native_american_alaskan: Optional[float] = Field(default=None)
    pacific_islander: Optional[float] = Field(default=None)
    two_or_more_races: Optional[float] = Field(default=None)
    unknown: Optional[float] = Field(default=None)
    non_resident_alien: Optional[float] = Field(default=None, description="International students")


class Demographics(BaseModel):
    """Demographic breakdown of admitted students."""
    first_gen_percentage: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Percentage who are first-generation college students"
    )
    legacy_percentage: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Percentage who are legacy admits"
    )
    international_percentage: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Percentage who are international students"
    )
    geographic_breakdown: List[RegionBreakdown] = Field(
        default=[],
        description="[REQUIRED] Distribution by region/state. At least top 3-5 regions"
    )
    gender_breakdown: Optional[GenderBreakdown] = Field(
        default=None,
        description="[REQUIRED] Gender-based admissions stats. Source: Common Data Set C15, IPEDS"
    )
    racial_breakdown: Optional[RaceEthnicityStats] = Field(
        default=None,
        description="[REQUIRED] Detailed racial breakdown. Source: Common Data Set Section B"
    )
    religious_affiliation: Optional[str] = Field(
        default=None,
        description="[OPTIONAL] Religious affiliation if applicable. Source: Official About page or CDS Section A"
    )


class AdmittedStudentProfile(BaseModel):
    """Complete profile of admitted students."""
    gpa: GPAProfile = Field(
        description="[REQUIRED] GPA statistics"
    )
    testing: TestingProfile = Field(
        description="[REQUIRED] Test score statistics"
    )
    demographics: Demographics = Field(
        description="[REQUIRED] Demographic breakdown including gender and race"
    )


class AdmissionsData(BaseModel):
    """Complete admissions data section."""
    current_status: CurrentStatus = Field(
        description="[REQUIRED] Latest cycle admissions stats"
    )
    longitudinal_trends: List[LongitudinalTrend] = Field(
        default=[],
        description="[REQUIRED] 3-5 years of historical trend data"
    )
    admitted_student_profile: AdmittedStudentProfile = Field(
        description="[REQUIRED] Profile of admitted students"
    )


# ==============================================================================
# AGENT: MajorsAgent
# Responsible for: Major details within each college
# Sources: Official major pages, impacted majors lists, department sites
# ==============================================================================

class Major(BaseModel):
    """Detailed information about a specific major."""
    name: str = Field(
        description="[REQUIRED] Major name. Examples: 'Computer Science', 'Economics', 'Mechanical Engineering'"
    )
    degree_type: str = Field(
        description="[REQUIRED] Degree type. Values: 'B.S.', 'B.A.', 'B.F.A.', 'B.B.A.'"
    )
    is_impacted: bool = Field(
        default=False,
        description="[REQUIRED] Whether major is impacted/capped/selective. True = harder to get into"
    )
    acceptance_rate: Optional[Union[float, str]] = Field(
        default=None,
        description="[OPTIONAL] Major-specific acceptance rate if different from overall. Example: '8.5%'"
    )
    average_gpa_admitted: Optional[Union[float, str]] = Field(
        default=None,
        description="[OPTIONAL] Average GPA of students admitted to this major"
    )
    prerequisite_courses: List[str] = Field(
        default=[],
        description="[REQUIRED if impacted] High school courses required. Examples: ['Calculus BC', 'Physics C', 'AP CS']"
    )
    minimum_gpa_to_declare: Optional[Union[float, str]] = Field(
        default=None,
        description="[OPTIONAL] Minimum GPA required to switch into this major after enrolling. Source: Department catalog"
    )
    weeder_courses: List[str] = Field(
        default=[],
        description="[OPTIONAL] Notorious filter courses. Source: Reddit, Student reviews. Example: 'Organic Chemistry (CHEM 35)'"
    )
    special_requirements: Optional[str] = Field(
        default="",
        description="[OPTIONAL] Extra requirements. Examples: 'Portfolio required', 'Audition needed'"
    )
    admissions_pathway: str = Field(
        default="Direct Admit",
        description="[REQUIRED] How students enter. Values: 'Direct Admit', 'Pre-Major', 'Apply as Sophomore'"
    )
    internal_transfer_allowed: bool = Field(
        default=True,
        description="[REQUIRED] Whether internal transfer into this major is allowed"
    )
    direct_admit_only: bool = Field(
        default=False,
        description="[REQUIRED] If true, NO internal transfers allowed. Source: Official major page"
    )
    internal_transfer_gpa: Optional[Union[float, str]] = Field(
        default=None,
        description="[OPTIONAL] Minimum GPA to transfer into this major. Example: 3.5"
    )
    notes: Optional[str] = Field(
        default="",
        description="[OPTIONAL] Additional notes. Example: 'Extremely competitive, consider alternate major'"
    )


# ==============================================================================
# AGENT: CollegesAgent
# Responsible for: College/School structure, housing, archetypes
# Sources: Official college pages, Reddit, housing reviews, Niche
# ==============================================================================

class College(BaseModel):
    """A college or school within the university."""
    name: str = Field(
        description="[REQUIRED] College/School name. Examples: 'Revelle College', 'School of Engineering'"
    )
    admissions_model: str = Field(
        description="[REQUIRED] How admissions works. Values: 'Direct Admit', 'Pre-Major System', "
                    "'Separate Application', 'Common Admit then Declare'"
    )
    acceptance_rate_estimate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] College-specific acceptance rate if different from overall"
    )
    is_restricted_or_capped: bool = Field(
        default=False,
        description="[REQUIRED] Whether enrollment is restricted/capped"
    )
    strategic_fit_advice: str = Field(
        default="",
        description="[REQUIRED] Who should/shouldn't apply. Source: Reddit, student advice. "
                    "Example: 'Avoid if Engineering major - harsh GE requirements'"
    )
    housing_profile: str = Field(
        default="",
        description="[REQUIRED] Housing/dorm vibe. Source: Housing reviews, Reddit. "
                    "Examples: 'Brutalist concrete towers', 'Resort-style modern', 'Traditional quads'"
    )
    student_archetype: str = Field(
        default="",
        description="[REQUIRED] Stereotypical student type. Source: Reddit, Niche. "
                    "Examples: 'The Overachiever', 'The STEM Nerd', 'The Humanities Scholar', 'The Pre-Med'"
    )
    majors: List[Major] = Field(
        default=[],
        description="[REQUIRED] All majors offered by this college. MUST BE POPULATED BY MajorsAgent"
    )


class AcademicStructure(BaseModel):
    """Academic organization of the university."""
    structure_type: str = Field(
        default="Colleges",
        description="[REQUIRED] How university is organized. Values: 'Colleges', 'Schools', 'Divisions'"
    )
    colleges: List[College] = Field(
        default=[],
        description="[REQUIRED] All colleges/schools at the university. Each must have majors populated"
    )
    minors_certificates: List[str] = Field(
        default=[],
        description="[REQUIRED] Available minors and certificate programs"
    )


# ==============================================================================
# AGENT: ApplicationAgent
# Responsible for: Deadlines, supplementals, holistic factors
# Sources: Official admissions page, Common App requirements, Niche
# ==============================================================================

class ApplicationDeadline(BaseModel):
    """Deadline for a specific application plan."""
    plan_type: str = Field(
        description="[REQUIRED] Application plan type. Values: 'Early Decision', 'Early Action', "
                    "'Regular Decision', 'ED2', 'Rolling'"
    )
    date: Optional[str] = Field(
        description="[REQUIRED] Deadline date. Format: ISO date 'YYYY-MM-DD'. Example: '2024-11-01'"
    )
    is_binding: bool = Field(
        default=False,
        description="[REQUIRED] Whether this plan is binding. True for ED/ED2"
    )
    notes: str = Field(
        default="",
        description="[OPTIONAL] Additional notes. Example: 'Financial aid deadlines may differ'"
    )


class SupplementalRequirement(BaseModel):
    """Additional application requirements beyond Common App."""
    target_program: str = Field(
        description="[REQUIRED] Which program requires this. Examples: 'All', 'Architecture', 'School of Music'"
    )
    requirement_type: str = Field(
        description="[REQUIRED] Type of requirement. Values: 'Essays', 'Portfolio', 'Audition', "
                    "'Video Introduction', 'Interview', 'Resume'"
    )
    deadline: Optional[str] = Field(
        default="",
        description="[OPTIONAL] Specific deadline if different from main deadline"
    )
    details: str = Field(
        default="",
        description="[OPTIONAL] Detailed requirements. Example: '2 essays: Why Us (250 words) + Activity (150 words)'"
    )


class HolisticFactors(BaseModel):
    """Factors considered in holistic admissions review."""
    primary_factors: List[str] = Field(
        default=[],
        description="[REQUIRED] Most important factors. Examples: 'Course Rigor', 'GPA', 'Essays', 'Recommendations'"
    )
    secondary_factors: List[str] = Field(
        default=[],
        description="[REQUIRED] Secondary factors. Examples: 'Extracurriculars', 'Talents', 'Character'"
    )
    essay_importance: str = Field(
        default="High",
        description="[REQUIRED] How important essays are. Values: 'Critical', 'High', 'Moderate', 'Low'"
    )
    demonstrated_interest: str = Field(
        default="Not Considered",
        description="[REQUIRED] DI policy. Values: 'Important', 'Considered', 'Not Considered'"
    )
    interview_policy: str = Field(
        default="Not Offered",
        description="[REQUIRED] Interview policy. Values: 'Required', 'Recommended', 'Evaluative', 'Informational', 'Not Offered'"
    )
    legacy_consideration: str = Field(
        default="Unknown",
        description="[REQUIRED] Legacy impact. Values: 'Strong', 'Moderate', 'Minimal', 'None', 'Unknown'"
    )
    first_gen_boost: str = Field(
        default="Unknown",
        description="[REQUIRED] First-gen consideration. Values: 'Strong', 'Moderate', 'Minimal', 'None', 'Unknown'"
    )
    specific_differentiators: str = Field(
        default="",
        description="[OPTIONAL] What makes their process unique. Example: 'Values intellectual curiosity over achievements'"
    )


class ApplicationProcess(BaseModel):
    """Complete application process information."""
    platforms: List[str] = Field(
        default=[],
        description="[REQUIRED] Application platforms accepted. Examples: 'Common App', 'Coalition', 'UC Application'"
    )
    application_deadlines: List[ApplicationDeadline] = Field(
        default=[],
        description="[REQUIRED] All application deadlines"
    )
    supplemental_requirements: List[SupplementalRequirement] = Field(
        default=[],
        description="[REQUIRED] All supplemental requirements"
    )
    holistic_factors: HolisticFactors = Field(
        default_factory=HolisticFactors,
        description="[REQUIRED] Holistic review factors"
    )


# ==============================================================================
# AGENT: FinancialsAgent
# Responsible for: Cost of attendance, aid philosophy
# Sources: Official financial aid page, Common Data Set Section H, Net Price Calculator
# ==============================================================================

class InStateCosts(BaseModel):
    """Costs for in-state students (public schools)."""
    tuition: Optional[float] = Field(
        default=None,
        description="[REQUIRED for public] In-state tuition only. Example: 14500.00"
    )
    total_coa: Optional[float] = Field(
        default=None,
        description="[REQUIRED for public] Total cost of attendance (tuition + room + board + fees)"
    )
    housing: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Housing/room cost only"
    )


class OutOfStateCosts(BaseModel):
    """Costs for out-of-state students."""
    tuition: Optional[float] = Field(
        default=None,
        description="[REQUIRED] Out-of-state tuition only. Example: 46000.00"
    )
    total_coa: Optional[float] = Field(
        default=None,
        description="[REQUIRED] Total out-of-state cost of attendance"
    )
    supplemental_tuition: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Additional fees for certain programs (e.g., Engineering)"
    )


class CostOfAttendanceBreakdown(BaseModel):
    """Complete cost breakdown."""
    academic_year: str = Field(
        default="",
        description="[REQUIRED] Academic year. Format: 'YYYY-YYYY'. Example: '2024-2025'"
    )
    in_state: InStateCosts = Field(
        default_factory=InStateCosts,
        description="[REQUIRED for public] In-state cost breakdown"
    )
    out_of_state: OutOfStateCosts = Field(
        default_factory=OutOfStateCosts,
        description="[REQUIRED] Out-of-state cost breakdown"
    )


# ==============================================================================
# AGENT: ScholarshipsAgent
# Responsible for: All scholarship information
# Sources: Official scholarships page, merit scholarship listings
# ==============================================================================

class Scholarship(BaseModel):
    """Information about a specific scholarship."""
    name: str = Field(
        description="[REQUIRED] Scholarship name. Example: 'Regents Scholarship'"
    )
    type: str = Field(
        description="[REQUIRED] Scholarship type. Values: 'Merit', 'Need', 'Both', 'Athletic', 'Departmental'"
    )
    amount: str = Field(
        default="",
        description="[REQUIRED] Award amount. Examples: '$10,000/year', 'Full Tuition', '$5,000 one-time'"
    )
    deadline: str = Field(
        default="",
        description="[OPTIONAL] Application deadline if separate from regular admission"
    )
    benefits: str = Field(
        default="",
        description="[REQUIRED] Non-monetary benefits. Examples: 'Priority Registration', 'Housing Guarantee', 'Mentorship'"
    )
    application_method: str = Field(
        default="",
        description="[REQUIRED] How to apply. Values: 'Automatic Consideration', 'Separate Application', 'Nomination Required'"
    )


class Financials(BaseModel):
    """Complete financial information."""
    tuition_model: str = Field(
        default="",
        description="[REQUIRED] Tuition policy. Examples: 'Tuition Stability Plan (locked 4 years)', 'Annual Increase (~3%)'"
    )
    cost_of_attendance_breakdown: CostOfAttendanceBreakdown = Field(
        default_factory=CostOfAttendanceBreakdown,
        description="[REQUIRED] Complete cost breakdown"
    )
    aid_philosophy: str = Field(
        default="",
        description="[REQUIRED] Aid approach. Examples: '100% Need Met', 'Need-Blind Admissions', 'Merit Focused'"
    )
    average_need_based_aid: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Average need-based aid package. Example: 25000.00"
    )
    average_merit_aid: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Average merit aid amount"
    )
    percent_receiving_aid: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Percentage of students receiving any aid. Example: 65.0"
    )
    scholarships: List[Scholarship] = Field(
        default=[],
        description="[REQUIRED] At least 3-5 major scholarships. POPULATED BY ScholarshipsAgent"
    )


# ==============================================================================
# AGENT: CreditPoliciesAgent
# Responsible for: AP, IB, and Transfer credit policies
# Sources: Official credit policy pages, ASSIST.org, Transferology
# ==============================================================================

class APPolicy(BaseModel):
    """Advanced Placement credit policy."""
    general_rule: str = Field(
        default="",
        description="[REQUIRED] Basic AP policy. Examples: 'Score of 3+ grants credit', 'Only 4+ for STEM courses'"
    )
    exceptions: List[str] = Field(
        default=[],
        description="[OPTIONAL] Subjects with different rules. Examples: ['No credit for English', 'CS requires 5']"
    )
    usage: str = Field(
        default="",
        description="[REQUIRED] How AP credits can be used. Examples: 'Elective units only', 'Satisfies prerequisites', "
                    "'Can skip intro courses'"
    )


class IBPolicy(BaseModel):
    """International Baccalaureate credit policy."""
    general_rule: str = Field(
        default="",
        description="[REQUIRED] Basic IB policy. Examples: 'HL 5+ only', 'SL not accepted', '6+ for science'"
    )
    diploma_bonus: bool = Field(
        default=False,
        description="[REQUIRED] Whether completing full IB Diploma gives extra credit/benefits"
    )


class TransferArticulation(BaseModel):
    """Transfer credit policies."""
    tools: List[str] = Field(
        default=[],
        description="[REQUIRED] Tools for checking transfer credits. Examples: ['ASSIST.org', 'Transferology', 'TES']"
    )
    restrictions: str = Field(
        default="",
        description="[OPTIONAL] Transfer credit limits. Examples: '60 unit cap', 'No upper-division credit', 'Must be C or better'"
    )


class CreditPolicies(BaseModel):
    """Complete credit policy information."""
    philosophy: str = Field(
        default="",
        description="[REQUIRED] Overall approach. Examples: 'Generous Credit', 'Placement Only', 'Strict Limits'"
    )
    ap_policy: APPolicy = Field(
        default_factory=APPolicy,
        description="[REQUIRED] AP credit policy"
    )
    ib_policy: IBPolicy = Field(
        default_factory=IBPolicy,
        description="[REQUIRED] IB credit policy"
    )
    transfer_articulation: TransferArticulation = Field(
        default_factory=TransferArticulation,
        description="[REQUIRED] Transfer credit policy"
    )


# ==============================================================================
# AGENT: StudentInsightsAgent
# Responsible for: Crowdsourced tips and success factors
# Sources: Niche, Reddit, College Confidential, student blogs
# ==============================================================================

class StudentInsight(BaseModel):
    """A single insight from a specific source."""
    source: str = Field(
        description="[REQUIRED] Where this insight came from. Examples: 'Niche', 'Reddit', 'College Confidential'"
    )
    category: str = Field(
        description="[REQUIRED] Insight category. Examples: 'What It Takes', 'Essays', 'Activities', 'Red Flags'"
    )
    insight: str = Field(
        description="[REQUIRED] The actual insight/tip"
    )


class StudentInsights(BaseModel):
    """Crowdsourced insights from current and admitted students."""
    what_it_takes: List[str] = Field(
        default=[],
        description="[REQUIRED] 3-5 key success factors from student perspectives. "
                    "Examples: ['Strong STEM background', 'Genuine intellectual curiosity', 'Leadership in 1-2 activities']"
    )
    common_activities: List[str] = Field(
        default=[],
        description="[REQUIRED] 5-10 activities commonly seen in admitted students. "
                    "Examples: ['Research with professors', 'Olympiad participation', 'Nonprofit founder']"
    )
    essay_tips: List[str] = Field(
        default=[],
        description="[REQUIRED] 3-5 essay writing tips. "
                    "Examples: ['Be specific about Why Us', 'Show intellectual depth', 'Avoid generic community service']"
    )
    red_flags: List[str] = Field(
        default=[],
        description="[REQUIRED] 2-3 things to avoid. "
                    "Examples: ['Mentioning rankings as reason', 'Generic essays', 'No demonstrated interest in major']"
    )
    insights: List[Union[StudentInsight, str]] = Field(
        default=[],
        description="[OPTIONAL] Additional sourced insights"
    )


# ==============================================================================
# AGENT: StrategyTacticsAgent
# Responsible for: Application gaming tactics and strategies
# Sources: Reddit, College Confidential, admissions consultants
# ==============================================================================

class ApplicationStrategy(BaseModel):
    """Tactical strategies for maximizing admission chances."""
    major_selection_tactics: List[str] = Field(
        default=[],
        description="[REQUIRED] Tactics for choosing primary/alternate majors. "
                    "Examples: ['Don't list two capped majors', 'Use Undeclared as safety', 'List less popular major in same college']"
    )
    college_ranking_tactics: List[str] = Field(
        default=[],
        description="[REQUIRED for residential college systems] How to rank colleges strategically. "
                    "Examples: ['Engineers should pick Warren over Revelle', 'Seventh has easiest GEs']"
    )
    alternate_major_strategy: str = Field(
        default="",
        description="[REQUIRED] Best backup major strategies. "
                    "Example: 'Cognitive Science is good CS backup - still in same division, can try to transfer'"
    )


# ==============================================================================
# AGENT: OutcomesAgent (NEW)
# Responsible for: Career ROI, Salary, Retention
# Sources: College Scorecard, PCSC, Official Outcome Reports
# ==============================================================================

class RetentionStats(BaseModel):
    """Student retention and graduation rates."""
    freshman_retention_rate: Optional[float] = Field(
        default=None,
        description="[REQUIRED] % of freshmen returning for sophomore year. Source: Common Data Set Section B"
    )
    graduation_rate_4_year: Optional[float] = Field(
        default=None,
        description="[REQUIRED] 4-year graduation rate. Source: Common Data Set Section B"
    )
    graduation_rate_6_year: Optional[float] = Field(
        default=None,
        description="[REQUIRED] 6-year graduation rate. Source: Common Data Set Section B"
    )


class CareerOutcomes(BaseModel):
    """Post-graduation career statistics."""
    median_earnings_10yr: Optional[int] = Field(
        default=None,
        description="[REQUIRED] Median earnings 10 years after entry. Source: College Scorecard"
    )
    employment_rate_2yr: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] % employed 2 years after graduation"
    )
    grad_school_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] % continuing to graduate school"
    )
    top_employers: List[str] = Field(
        default=[],
        description="[REQUIRED] Top companies hiring graduates. Source: Career Center reports, LinkedIn Alumni"
    )
    loan_default_rate: Optional[float] = Field(
        default=None,
        description="[OPTIONAL] Federal loan default rate"
    )


# ==============================================================================
# MAIN SCHEMA: UniversityProfile
# Combines all sections into complete profile
# ==============================================================================

class UniversityProfile(BaseModel):
    """
    Complete university profile aggregated from all sub-agents.
    
    AGENT RESPONSIBILITIES:
    - StrategyAgent: id, metadata, strategic_profile
    - AdmissionsCurrentAgent: admissions_data.current_status
    - AdmissionsTrendsAgent: admissions_data.longitudinal_trends
    - AdmittedProfileAgent: admissions_data.admitted_student_profile
    - CollegesAgent: academic_structure.colleges (without majors)
    - MajorsAgent: academic_structure.colleges[].majors
    - ApplicationAgent: application_process
    - StrategyTacticsAgent: application_strategy
    - FinancialsAgent: financials (without scholarships)
    - ScholarshipsAgent: financials.scholarships
    - CreditPoliciesAgent: credit_policies
    - StudentInsightsAgent: student_insights
    - OutcomesAgent: outcomes, student_retention
    """
    id: str = Field(
        alias="_id",
        description="[REQUIRED] URL-safe slug identifier. Format: snake_case. Example: 'uc_san_diego'"
    )
    metadata: Metadata = Field(
        description="[REQUIRED] Basic university information. AGENT: StrategyAgent"
    )
    strategic_profile: StrategicProfile = Field(
        description="[REQUIRED] Strategic overview and rankings. AGENT: StrategyAgent"
    )
    admissions_data: AdmissionsData = Field(
        description="[REQUIRED] All admissions statistics. AGENTS: AdmissionsCurrentAgent, AdmissionsTrendsAgent, AdmittedProfileAgent"
    )
    academic_structure: AcademicStructure = Field(
        description="[REQUIRED] Academic organization. AGENTS: CollegesAgent, MajorsAgent"
    )
    application_process: ApplicationProcess = Field(
        description="[REQUIRED] Application requirements. AGENT: ApplicationAgent"
    )
    application_strategy: ApplicationStrategy = Field(
        default_factory=ApplicationStrategy,
        description="[REQUIRED] Gaming tactics. AGENT: StrategyTacticsAgent"
    )
    financials: Financials = Field(
        description="[REQUIRED] Cost and aid. AGENTS: FinancialsAgent, ScholarshipsAgent"
    )
    credit_policies: CreditPolicies = Field(
        description="[REQUIRED] Credit policies. AGENT: CreditPoliciesAgent"
    )
    student_insights: StudentInsights = Field(
        description="[REQUIRED] Crowdsourced tips. AGENT: StudentInsightsAgent"
    )
    outcomes: CareerOutcomes = Field(
        default_factory=CareerOutcomes,
        description="[REQUIRED] Career ROI stats. AGENT: OutcomesAgent"
    )
    student_retention: RetentionStats = Field(
        default_factory=RetentionStats,
        description="[REQUIRED] Retention and graduation rates. AGENT: OutcomesAgent"
    )