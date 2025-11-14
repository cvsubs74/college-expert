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
    """A structured analysis of 5-year Common Data Set trends."""
    trend_summary: str = Field(description="A summary of the 5-year trajectory for the college's selectivity.")
    acceleration_analysis: str = Field(description="An analysis of the year-over-year rate of change in selectivity metrics.")
    c7_priorities: List[str] = Field(description="A ranked list of the college's admission priorities from the C7 table.")
    time_series_data: str = Field(description="A JSON string representing the raw time-series data extracted from the CDS documents.")


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
