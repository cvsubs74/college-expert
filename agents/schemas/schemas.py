"""
Consolidated schemas for College Counselor Agent.

This file contains all Pydantic schemas used across the various sub-agents
in the College Counselor system.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# ============================================================================
# Student Profile Schemas
# ============================================================================

class Course(BaseModel):
    """A single course from a student's transcript."""
    course_name: str
    subject: str
    grade: str
    level: Literal['Regular', 'Honors', 'AP', 'IB', 'Other']
    year: int


class AcademicAnalysis(BaseModel):
    """Calculated metrics of academic performance."""
    unweighted_gpa: float = Field(description="GPA on a 4.0 scale.")
    weighted_gpa: float = Field(description="GPA with weights for Honors/AP/IB courses.")
    course_rigor: int = Field(description="Total count of AP, IB, and Honors courses.")
    grade_trend: Literal['Upward', 'Downward', 'Static'] = Field(description="The student's grade trend over time.")


class ExtracurricularSpike(BaseModel):
    """Identified extracurricular theme or spike."""
    spike: str = Field(description="The identified extracurricular spike (e.g., 'STEM Research', 'Social Justice').")
    justification: str = Field(description="A 1-sentence justification for the identified spike.")


class StandardizedTest(BaseModel):
    """A standardized test score."""
    test_name: str = Field(description="Name of the test (e.g., 'SAT', 'ACT', 'AP Biology').")
    score: str = Field(description="The score achieved (e.g., '1450', '34', '5').")
    date: Optional[str] = Field(default=None, description="Date taken (if available).")


class Extracurricular(BaseModel):
    """An extracurricular activity."""
    activity_name: str = Field(description="Name of the activity.")
    role: Optional[str] = Field(default=None, description="Role or position held.")
    description: str = Field(description="Brief description of involvement and achievements.")
    years: Optional[str] = Field(default=None, description="Years of participation (e.g., '9-12', '2 years').")


class Award(BaseModel):
    """An award or honor."""
    award_name: str = Field(description="Name of the award.")
    description: Optional[str] = Field(default=None, description="Description or significance of the award.")
    year: Optional[int] = Field(default=None, description="Year received.")


class StudentProfile(BaseModel):
    """A structured and analyzed representation of a student's profile."""
    courses: List[Course] = Field(description="A structured list of all courses taken.")
    academic_analysis: AcademicAnalysis = Field(description="Calculated metrics of the student's academic performance.")
    extracurricular_spike: ExtracurricularSpike = Field(description="The inferred extracurricular theme.")
    standardized_tests: List[StandardizedTest] = Field(description="A list of standardized test scores.")
    extracurriculars: List[Extracurricular] = Field(description="A list of extracurricular activities.")
    awards: List[Award] = Field(description="A list of awards and honors.")
    summary: str = Field(description="A brief, synthesized summary of the student's overall profile.")


# ============================================================================
# Quantitative Analyst Schemas
# ============================================================================

class CDSTrends(BaseModel):
    """A structured analysis of admissions statistics from CDS and university sources."""
    trend_summary: str = Field(description="A summary of the 5-year trajectory for the college's selectivity.")
    acceleration_analysis: str = Field(description="An analysis of the year-over-year rate of change in selectivity metrics.")
    c7_priorities: List[str] = Field(description="A ranked list of the college's admission priorities from the C7 table.")
    time_series_data: str = Field(description="A JSON string representing the raw time-series data extracted from the CDS documents.")
    average_unweighted_gpa: Optional[str] = Field(default=None, description="Average unweighted GPA of admitted students (e.g., '3.85')")
    average_weighted_gpa: Optional[str] = Field(default=None, description="Average weighted GPA of admitted students (e.g., '4.15')")
    uc_weighted_gpa: Optional[str] = Field(default=None, description="UC weighted GPA (for UC schools only, e.g., '4.20')")
    uc_capped_gpa: Optional[str] = Field(default=None, description="UC capped weighted GPA (for UC schools only, e.g., '4.00')")
    gpa_ranges: Optional[str] = Field(default=None, description="GPA ranges for admitted students (e.g., '25th-75th percentile: 3.7-4.0')")
    data_sources: str = Field(description="List of sources used (CDS, university admissions pages, etc.)")


# ============================================================================
# Brand Analyst Schemas
# ============================================================================

class OfficialNarrative(BaseModel):
    """A structured analysis of a college's official narrative from its website and blogs."""
    key_attributes: List[str] = Field(description="A list of key attributes and 'buzzwords' the college claims to look for.")
    ideal_student_summary: str = Field(description="A synthesized summary describing the 'ideal student' profile as promoted by the college.")


# ============================================================================
# Community Analyst Schemas
# ============================================================================

class AnecdotalProfile(BaseModel):
    """An anecdotal profile from forum posts."""
    decision: str = Field(description="Admission decision (e.g., 'Accepted', 'Rejected', 'Waitlisted').")
    gpa: Optional[str] = Field(default=None, description="GPA if mentioned.")
    test_scores: Optional[str] = Field(default=None, description="Test scores if mentioned (e.g., 'SAT 1500').")
    spike: Optional[str] = Field(default=None, description="Identified spike or major theme.")
    summary: str = Field(description="Brief summary of the profile.")


class ForumPatterns(BaseModel):
    """A structured analysis of anecdotal admissions patterns from public forums."""
    statistical_patterns: str = Field(description="Analysis of common statistical profiles (GPA, Test Scores) in the 'Accepted' vs. 'Rejected' clusters.")
    spike_patterns: str = Field(description="Analysis of common 'spikes' or 'majors' in the 'Accepted' vs. 'Rejected' clusters.")
    outlier_and_contradiction_analysis: str = Field(description="The most critical analysis: identifying outliers (e.g., low stats accepted) and contradictions with the official narrative.")
    sentiment_synthesis: str = Field(description="A summary of common reasoning themes from accepted and rejected students.")
    anecdotal_profiles: List[AnecdotalProfile] = Field(description="The raw list of extracted anecdotal profiles from the forum posts.")


# ============================================================================
# Career Outcomes Analyst Schemas
# ============================================================================

class CareerOutcomesData(BaseModel):
    """Structured career outcomes analysis for a university program."""
    employment_rate: Optional[str] = Field(default=None, description="Overall employment rate (e.g., '95% within 6 months')")
    median_salary: Optional[str] = Field(default=None, description="Median starting salary (e.g., '$85,000')")
    top_employers: List[str] = Field(default_factory=list, description="List of top employers hiring graduates")
    common_industries: List[str] = Field(default_factory=list, description="Common industries graduates enter")
    common_job_titles: List[str] = Field(default_factory=list, description="Common job titles for graduates")
    graduate_school_rate: Optional[str] = Field(default=None, description="Percentage pursuing graduate education")
    career_services: str = Field(default="", description="Description of career services and support available")
    notable_outcomes: str = Field(default="", description="Notable achievements, placements, or unique outcomes")
    data_availability: str = Field(description="Assessment of data availability: 'Comprehensive', 'Partial', or 'Limited'")
    summary: str = Field(description="Overall summary of career outcomes and prospects")


# ============================================================================
# Knowledge Base Analyst Schemas
# ============================================================================

class Citation(BaseModel):
    """Citation from File Search."""
    source: str = Field(description="Source document name")
    content: str = Field(description="Content snippet")


class KnowledgeBaseOutput(BaseModel):
    """Knowledge base search output."""
    operation: str = Field(description="Operation: search")
    success: bool = Field(description="Was search successful")
    message: str = Field(description="Status message")
    answer: str = Field(description="Answer from knowledge base search")
    citations: List[Citation] = Field(default_factory=list, description="Citations from knowledge base")
    suggested_questions: List[str] = Field(default_factory=list, description="Follow-up questions")


# ============================================================================
# Orchestrator Output Schema
# ============================================================================

class OrchestratorOutput(BaseModel):
    """Final output from the College Counselor agent."""
    result: str = Field(description="Markdown-formatted response with complete answer")
    suggested_questions: List[str] = Field(default_factory=list, description="Suggested follow-up questions for the user")


# ============================================================================
# Knowledge Base Creator Schemas
# ============================================================================

class UniversityIdentity(BaseModel):
    """University identity and profile information."""
    full_name: str = Field(description="Full university name")
    location: str = Field(description="City, State")
    setting: str = Field(description="Urban, Suburban, or Rural")
    university_type: str = Field(description="Public, Private, Liberal Arts, Research, etc.")
    religious_affiliation: Optional[str] = Field(default=None, description="Religious affiliation if any")
    total_undergrad_enrollment: Optional[str] = Field(default=None, description="Total undergraduate enrollment")
    student_faculty_ratio: Optional[str] = Field(default=None, description="Student-to-faculty ratio (e.g., '10:1')")
    average_class_size: Optional[str] = Field(default=None, description="Class size statistics")
    mission_statement: str = Field(description="Official mission statement")
    campus_culture: List[str] = Field(default_factory=list, description="3-5 adjectives describing campus culture")

class AdmissionsData(BaseModel):
    """Comprehensive admissions statistics."""
    total_applications: Optional[str] = Field(default=None, description="Total applications received")
    total_admitted: Optional[str] = Field(default=None, description="Total students admitted")
    acceptance_rate: Optional[str] = Field(default=None, description="Overall acceptance rate")
    yield_rate: Optional[str] = Field(default=None, description="Percentage of admitted students who enroll")
    ed_deadline: Optional[str] = Field(default=None, description="Early Decision deadline")
    ea_deadline: Optional[str] = Field(default=None, description="Early Action deadline")
    rd_deadline: Optional[str] = Field(default=None, description="Regular Decision deadline")
    ed_acceptance_rate: Optional[str] = Field(default=None, description="ED acceptance rate")
    ea_acceptance_rate: Optional[str] = Field(default=None, description="EA acceptance rate")
    rd_acceptance_rate: Optional[str] = Field(default=None, description="RD acceptance rate")
    gpa_range: Optional[str] = Field(default=None, description="25th-75th percentile GPA range")
    sat_range: Optional[str] = Field(default=None, description="25th-75th percentile SAT range")
    act_range: Optional[str] = Field(default=None, description="25th-75th percentile ACT range")
    test_policy: Optional[str] = Field(default=None, description="Test-Required, Test-Optional, or Test-Blind")
    percent_submitting_scores: Optional[str] = Field(default=None, description="% of admitted students submitting test scores")
    percent_top_10: Optional[str] = Field(default=None, description="% of admitted students in top 10% of class")
    holistic_factors: str = Field(description="Summary of CDS C7 holistic review factors and their importance")

class AcademicsData(BaseModel):
    """Academic programs and major-specific data."""
    colleges_schools: List[str] = Field(default_factory=list, description="List of undergraduate colleges/schools")
    application_process: str = Field(description="Apply to specific school/major or university as whole")
    internal_acceptance_rates: Optional[str] = Field(default=None, description="Acceptance rates by college/school if available")
    impacted_majors: List[str] = Field(default_factory=list, description="List of impacted/capped majors")
    top_10_majors: List[str] = Field(default_factory=list, description="Top 10 most popular majors")
    alternative_majors: str = Field(description="Alternative majors for competitive programs (formatted text)")
    changing_majors_policy: str = Field(description="How easy/difficult to change majors")
    internal_transfer_policy: str = Field(description="Process and competitiveness of internal transfers")

class FinancialsData(BaseModel):
    """Cost and financial aid information."""
    total_coa: Optional[str] = Field(default=None, description="Total cost of attendance")
    tuition_fees: Optional[str] = Field(default=None, description="Tuition and fees")
    room_board: Optional[str] = Field(default=None, description="Room and board costs")
    need_blind_domestic: Optional[bool] = Field(default=None, description="Need-blind for domestic students")
    need_blind_international: Optional[bool] = Field(default=None, description="Need-blind for international students")
    meets_full_need: Optional[bool] = Field(default=None, description="Meets 100% of demonstrated need")
    percent_receiving_aid: Optional[str] = Field(default=None, description="% receiving any financial aid")
    percent_need_based: Optional[str] = Field(default=None, description="% receiving need-based aid")
    average_need_award: Optional[str] = Field(default=None, description="Average need-based award")
    major_merit_scholarships: List[str] = Field(default_factory=list, description="List of major merit scholarships")
    merit_application_process: str = Field(description="How to apply for merit scholarships")

class StudentLifeOutcomes(BaseModel):
    """Student life, culture, and career outcomes."""
    housing_policy: str = Field(description="On-campus housing policy and guarantees")
    percent_on_campus: Optional[str] = Field(default=None, description="% of students living on campus")
    diversity_stats: str = Field(description="Key diversity statistics (geographic, racial/ethnic)")
    job_placement_rate: Optional[str] = Field(default=None, description="Job placement rate (e.g., 6 months post-grad)")
    average_starting_salary: Optional[str] = Field(default=None, description="Average starting salary")
    top_employers: List[str] = Field(default_factory=list, description="Top 5-10 hiring companies")
    top_grad_schools: List[str] = Field(default_factory=list, description="Top 5 graduate schools")

class UniversityKnowledgeBase(BaseModel):
    """Complete university knowledge base profile with raw research data."""
    university_name: str = Field(description="University name being researched")
    identity_data: str = Field(description="Raw identity and profile research data")
    admissions_data: str = Field(description="Raw admissions research data")
    academics_data: str = Field(description="Raw academics and major-specific research data")
    financials_data: str = Field(description="Raw cost and financial aid research data")
    student_life_data: str = Field(description="Raw student life and career outcomes research data")
    data_sources: List[str] = Field(default_factory=list, description="List of all sources used")
    research_date: str = Field(description="Date research was conducted")
    summary: str = Field(description="Executive summary of the university profile")
