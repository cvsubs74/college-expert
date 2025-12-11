"""
Structured Student Profile Model
Pydantic model for caching parsed student profile data in ADK session state.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    """Structured student profile for college counseling."""
    
    # Personal Information
    name: Optional[str] = Field(default=None, description="Student's name")
    email: Optional[str] = Field(default=None, description="Student's email address")
    location: Optional[str] = Field(default=None, description="City/State location")
    high_school: Optional[str] = Field(default=None, description="High school name")
    graduation_year: Optional[int] = Field(default=None, description="Expected graduation year")
    
    # Academic Information
    gpa: Optional[float] = Field(default=None, description="GPA on 4.0 scale")
    gpa_weighted: Optional[float] = Field(default=None, description="Weighted GPA if different")
    class_rank: Optional[str] = Field(default=None, description="Class rank (e.g., '15/400')")
    course_rigor: Optional[str] = Field(default=None, description="Course rigor level (AP/IB/Honors)")
    
    # Test Scores
    sat_score: Optional[int] = Field(default=None, description="Total SAT score")
    sat_reading: Optional[int] = Field(default=None, description="SAT Reading/Writing score")
    sat_math: Optional[int] = Field(default=None, description="SAT Math score")
    act_score: Optional[int] = Field(default=None, description="ACT composite score")
    ap_tests: Optional[List[str]] = Field(default_factory=list, description="List of AP tests and scores")
    
    # Interests and Goals
    intended_major: Optional[str] = Field(default=None, description="Intended major/field of study")
    intended_major_secondary: Optional[str] = Field(default=None, description="Secondary major interest")
    career_goals: Optional[str] = Field(default=None, description="Career aspirations")
    academic_interests: Optional[List[str]] = Field(default_factory=list, description="Academic interests")
    
    # Extracurriculars
    extracurriculars: Optional[List[str]] = Field(default_factory=list, description="Activities and positions")
    leadership_roles: Optional[List[str]] = Field(default_factory=list, description="Leadership positions")
    volunteer_work: Optional[List[str]] = Field(default_factory=list, description="Community service")
    work_experience: Optional[List[str]] = Field(default_factory=list, description="Jobs/internships")
    
    # Awards and Achievements
    awards: Optional[List[str]] = Field(default_factory=list, description="Honors and awards")
    
    # College Preferences
    preferred_size: Optional[str] = Field(default=None, description="School size preference (small/medium/large)")
    preferred_location: Optional[str] = Field(default=None, description="Geographic preference")
    preferred_setting: Optional[str] = Field(default=None, description="Urban/suburban/rural preference")
    financial_need: Optional[bool] = Field(default=None, description="Needs financial aid")
    
    # Additional Context
    special_circumstances: Optional[str] = Field(default=None, description="First-gen, legacy, etc.")
    essay_topics: Optional[List[str]] = Field(default_factory=list, description="Essay topic ideas")
    
    # Raw profile text for fallback
    raw_profile_text: Optional[str] = Field(default=None, description="Original profile text")

    def get_summary(self) -> str:
        """Return a brief summary of the profile."""
        parts = []
        if self.name:
            parts.append(f"**Name**: {self.name}")
        if self.gpa:
            parts.append(f"**GPA**: {self.gpa}")
        if self.sat_score:
            parts.append(f"**SAT**: {self.sat_score}")
        if self.intended_major:
            parts.append(f"**Intended Major**: {self.intended_major}")
        if self.extracurriculars:
            parts.append(f"**Activities**: {len(self.extracurriculars)} listed")
        return " | ".join(parts) if parts else "No profile data"

    def has_academic_data(self) -> bool:
        """Check if essential academic data is present."""
        return any([self.gpa, self.sat_score, self.act_score])
    
    def has_intended_major(self) -> bool:
        """Check if intended major is specified."""
        return bool(self.intended_major)
