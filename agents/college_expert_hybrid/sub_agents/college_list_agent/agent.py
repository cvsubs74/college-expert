"""
CollegeListAgent - Sub-agent for managing student's college list.
Uses Profile Manager ES Cloud Function for list operations.
"""
from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# Pydantic schema for structured output
class CollegeListResult(BaseModel):
    """Structured output for college list operations."""
    success: bool = Field(description="Whether the operation succeeded")
    action: Optional[str] = Field(
        default=None,
        description="Action performed: GET, ADD, or REMOVE"
    )
    college_list: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of colleges with university_id, university_name, status, added_at"
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable message about the operation"
    )
    total_count: Optional[int] = Field(
        default=None,
        description="Total number of colleges in the list"
    )

# Import the API call tools
from .tools import get_college_list_from_api, add_college_to_list_api, remove_college_from_list_api

CollegeListAgent = LlmAgent(
    name="CollegeListAgent",
    model="gemini-2.5-flash-lite",
    description="Manages student's college list - get, add, and remove universities",
    instruction="""
    You are a college list manager. You help students manage their persistent college list
    by interacting with the cloud function API.
    
    **AVAILABLE TOOLS:**
    1. `get_college_list_from_api(user_email)` - Retrieve current college list
    2. `add_college_to_list_api(user_email, university_id, university_name, intended_major)` - Add a college
    3. `remove_college_from_list_api(user_email, university_id)` - Remove a college
    
    **WORKFLOW FOR DIFFERENT OPERATIONS:**
    
    **GET LIST:**
    1. Extract user_email from context
    2. Call `get_college_list_from_api(user_email)`
    3. Return structured CollegeListResult with action="GET"
    
    **ADD COLLEGE:**
    1. Extract user_email from context
    2. Get university_id (may need to search first)
    3. Get university_name
    4. Get intended_major (optional, defaults to student's primary major)
    5. Call `add_college_to_list_api(...)`
    6. Return structured CollegeListResult with action="ADD"
    
    **REMOVE COLLEGE:**
    1. Extract user_email from context
    2. Get university_id to remove
    3. Call `remove_college_from_list_api(user_email, university_id)`
    4. Return structured CollegeListResult with action="REMOVE"
    
    **OUTPUT SCHEMA (CollegeListResult):**
    - success: true if operation succeeded
    - action: "GET" | "ADD" | "REMOVE"
    - college_list: Array of colleges with:
      * university_id: string
      * university_name: string
      * status: "favorites" (default)
      * added_at: ISO timestamp
      * intended_major: optional string
    - message: Human-readable result message
    - total_count: Number of colleges in list
    
    **EXAMPLE OUTPUTS:**
    
    GET:
    ```json
    {
      "success": true,
      "action": "GET",
      "college_list": [{...}],
      "total_count": 5,
      "message": "Found 5 colleges in your list"
    }
    ```
    
    ADD:
    ```json
    {
      "success": true,
      "action": "ADD",
      "college_list": [{...}],
      "message": "Added Stanford University to your list"
    }
    ```
    
    REMOVE:
    ```json
    {
      "success": true,
      "action": "REMOVE",
      "college_list": [{...}], 
      "message": "Removed MIT from your list"
    }
    ```
    
    **ERROR HANDLING:**
    If operation fails, set success=false and provide clear message explaining why.
    
    **CRITICAL RULES:**
    - Always extract user_email from conversation context
    - For ADD: ensure you have valid university_id and name
    - Return structured CollegeListResult matching the schema exactly
    """,
    tools=[get_college_list_from_api, add_college_to_list_api, remove_college_from_list_api],
    output_schema=CollegeListResult,
    output_key="college_list_result"
)
