"""
FitAnalysisAgent - Sub-agent for retrieving pre-computed college fit analysis.
Uses Profile Manager ES Cloud Function to fetch fit data from Elasticsearch.
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Pydantic schema for structured output
class FitAnalysisResult(BaseModel):
    """Structured output for college fit analysis."""
    success: bool = Field(description="Whether fit analysis was found")
    fit_category: Optional[str] = Field(
        default=None,
        description="Fit category: SAFETY, TARGET, REACH, or SUPER_REACH"
    )
    match_percentage: Optional[int] = Field(
        default=None,
        description="Match score from 0-100"
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation of why this is the fit category"
    )
    factors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of factors contributing to the fit"
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improving chances"
    )
    university_id: Optional[str] = Field(
        default=None,
        description="University ID"
    )
    university_name: Optional[str] = Field(
        default=None,
        description="Official university name"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable message about the result"
    )

# Import the API call tool
from .tools import get_fit_from_api

FitAnalysisAgent = LlmAgent(
    name="FitAnalysisAgent",
    model="gemini-2.5-flash-lite",
    description="Retrieves pre-computed college fit analysis for a specific university",
    instruction="""
    You are a college fit analysis specialist. Your job is to retrieve PRE-COMPUTED fit analysis
    data from the cloud function. You NEVER calculate or recompute fits - only fetch existing ones.
    
    **AVAILABLE TOOL:**
    `get_fit_from_api(user_email, university_id)` - Retrieve fit analysis from cloud function
    
    **REQUIRED INPUTS:**
    - user_email: Student's email address
    - university_id: University identifier (e.g., "stanford_university", "mit")
    
    **WORKFLOW:**
    1. Extract user_email from conversation context
    2. Extract or search for university_id
    3. Call `get_fit_from_api(user_email, university_id)` to retrieve fit
    4. Return structured FitAnalysisResult
    
    **OUTPUT SCHEMA (FitAnalysisResult):**
    - success: true if fit found, false otherwise
    - fit_category: SAFETY | TARGET | REACH | SUPER_REACH
    - match_percentage: 0-100
    - explanation: Why this category
    - factors: List of contributing factors
    - recommendations: List of improvement suggestions
    - university_id: University ID
    - university_name: University name
    - message: Human-readable message
    
    **IF FIT NOT FOUND:**
    Set success=false and provide helpful message like:
    "No pre-computed fit found for this university. Run fit calculation first."
    
    **CRITICAL RULES:**
    - NEVER try to calculate or recompute fits yourself
    - ALWAYS fetch from the cloud function
    - If fit doesn't exist, clearly state it needs to be computed
    - Return structured FitAnalysisResult matching the schema exactly
    """,
    tools=[get_fit_from_api],
    output_schema=FitAnalysisResult,
    output_key="fit_analysis_result"
)
