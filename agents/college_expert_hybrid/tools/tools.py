"""
University Knowledge Base Tools - Interface to Knowledge Base Manager Universities Cloud Function
Provides semantic search using Elasticsearch's ELSER model for university profiles.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from google import genai
from google.genai import types
from google.adk.tools import ToolContext  # ADK ToolContext for session state access

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Knowledge Base Manager Universities Cloud Function URL
KNOWLEDGE_BASE_UNIVERSITIES_URL = os.environ.get(
    'KNOWLEDGE_BASE_UNIVERSITIES_URL', 
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app'
)

# Profile Manager Cloud Function URL (ES)
PROFILE_MANAGER_ES_URL = os.environ.get(
    'PROFILE_MANAGER_ES_URL', 
    'https://profile-manager-es-pfnwjfp26a-ue.a.run.app'
)

# Note: Profile caching is now handled via ADK ToolContext.state['temp:student_profile']
# for session-scoped data that persists across tool calls within the same agent invocation.


def search_universities(
    query: str,
    search_type: str = "semantic",
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search universities using semantic search (ELSER) with optional filters.
    
    IMPORTANT: Use filters when the user specifies criteria like location, acceptance rate,
    or public/private type. Combining filters with semantic search gives the best results.
    
    This searches structured university profiles with detailed admissions data (SAT/ACT scores,
    GPA ranges), academic programs, career outcomes, and strategic insights.
    
    Args:
        query: Natural language search query describing what you're looking for.
            Examples: "strong computer science program", "business and psychology",
            "top research university", "good financial aid"
            
        search_type: Search mode - "semantic" (default), "hybrid", or "keyword"
            - semantic: ELSER-powered semantic search (RECOMMENDED - best for understanding intent)
            - hybrid: Combines semantic + BM25 text search (good for mixed queries)
            - keyword: BM25 text only (good for exact name matches)
            
        filters: IMPORTANT - Use these to narrow results when user specifies criteria!
            Available filters:
            - state: State abbreviation, e.g., "CA", "NY", "IL", "MA", "TX"
            - type: "Public" or "Private"
            - acceptance_rate_max: Maximum acceptance rate, e.g., 15 = under 15% (USE FOR "low acceptance rate", "selective", "competitive")
            - acceptance_rate_min: Minimum acceptance rate, e.g., 10 = above 10%
            - market_position: e.g., "Public Ivy", "Elite Private"
            
        limit: Maximum results to return (default: 10)
        
    Returns:
        Dictionary with:
        - success: Boolean indicating success
        - results: List of university matches, each containing:
            - university_id, official_name, location, acceptance_rate
            - profile: Full profile with admissions_data, outcomes, financials, etc.
        - total: Number of results found
        - query: Original query
        
    EXAMPLES - Use filters for precise queries:
    
        # "Best universities in California with low acceptance rates" (MUST use acceptance_rate_max!)
        search_universities(
            query="best university",
            filters={"state": "CA", "acceptance_rate_max": 15}
        )
        
        # "Find public universities in California with low acceptance rates"
        search_universities(
            query="strong academics",
            filters={"state": "CA", "type": "Public", "acceptance_rate_max": 25}
        )
        
        # "What are the top private universities in Massachusetts?"
        search_universities(
            query="top university",
            filters={"state": "MA", "type": "Private"}
        )
        
        # "Universities with acceptance rate between 10-25%"
        search_universities(
            query="competitive university",
            filters={"acceptance_rate_min": 10, "acceptance_rate_max": 25}
        )
        
        # "Find schools in New York"
        search_universities(
            query="university",
            filters={"state": "NY"}
        )
    """
    try:
        url = KNOWLEDGE_BASE_UNIVERSITIES_URL
        
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "query": query,
            "search_type": search_type,
            "limit": limit
        }
        
        if filters:
            data["filters"] = filters
        
        logger.info(f"="*60)
        logger.info(f"🔍 TOOL: search_universities")
        logger.info(f"   Query: {query}")
        logger.info(f"   Search Type: {search_type}")
        logger.info(f"   Filters: {filters}")
        logger.info(f"   Limit: {limit}")
        logger.info(f"   URL: {url}")
        logger.info(f"="*60)
        
        # Retry logic to handle Elasticsearch cold starts
        import time
        max_retries = 3
        result = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=data, headers=headers, timeout=45)  # Increased timeout
                response.raise_for_status()
                result = response.json()
                
                if result.get("success"):
                    break  # Success, exit retry loop
                elif attempt < max_retries - 1:
                    # If not successful and not last attempt, retry after delay
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"   Search attempt {attempt + 1} failed, retrying in {wait_time}s...")
                    time.sleep(wait_time)
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"   Request timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
        
        logger.info(f"   Response success: {result.get('success') if result else False}")
        logger.info(f"   Results count: {result.get('total', 0) if result else 0}")
        
        if result.get("success"):
            universities = []
            for uni in result.get("results", []):
                profile = uni.get("profile", {})
                
                # Extract key information for the agent
                university_data = {
                    "university_id": uni.get("university_id"),
                    "official_name": uni.get("official_name"),
                    "location": uni.get("location", {}),
                    "acceptance_rate": uni.get("acceptance_rate"),
                    "market_position": uni.get("market_position"),
                    "median_earnings_10yr": uni.get("median_earnings_10yr"),
                    "score": uni.get("score", 0),
                    
                    # Key profile sections for analysis
                    "strategic_profile": profile.get("strategic_profile", {}),
                    "admissions_data": profile.get("admissions_data", {}),
                    "academic_structure": profile.get("academic_structure", {}),
                    "application_strategy": profile.get("application_strategy", {}),
                    "student_insights": profile.get("student_insights", {}),
                    "outcomes": profile.get("outcomes", {}),
                    "credit_policies": profile.get("credit_policies", {})
                }
                universities.append(university_data)
            
            return {
                "success": True,
                "universities": universities,
                "total": result.get("total", len(universities)),
                "query": query,
                "search_type": search_type,
                "filters": filters,
                "message": f"Found {len(universities)} universities matching: {query}"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": f"Search failed: {result.get('error', 'Unknown error')}"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"University search request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"University knowledge base unavailable: {str(e)}"
        }
    except Exception as e:
        logger.error(f"University search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Search failed: {str(e)}"
        }


def list_valid_university_ids(tool_context: ToolContext = None) -> Dict[str, Any]:
    """
    Get a list of all valid university IDs in the knowledge base.
    
    IMPORTANT: Call this tool BEFORE calculating fit analysis to get the correct
    university ID format. The agent should NOT guess or generate university IDs - 
    always use the exact IDs from this list.
    
    The result is cached in session state so repeated calls are fast.
    
    Returns:
        Dictionary with:
        - success: True if retrieved successfully
        - universities: List of {id, name} objects
        - total: Number of universities
        
    Example Response:
        {
            "success": True,
            "universities": [
                {"id": "new_york_university", "name": "New York University"},
                {"id": "stanford_university", "name": "Stanford University"},
                ...
            ],
            "total": 50
        }
    """
    try:
        logger.info(f"="*60)
        logger.info(f"📋 TOOL: list_valid_university_ids")
        logger.info(f"="*60)
        
        # Check cache first - use session-scoped key (no temp: prefix) for persistence across turns
        cache_key = '_cache:valid_university_ids'
        if tool_context and hasattr(tool_context, 'state'):
            cached_list = tool_context.state.get(cache_key)
            if cached_list:
                logger.info(f"   Using cached university list ({cached_list.get('total', 0)} universities)")
                return cached_list
        
        # Fetch from knowledge base
        url = f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}/"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            universities = result.get("universities", [])
            # Create a simplified list with just id and name
            uni_list = [
                {
                    "id": u.get("university_id"),
                    "name": u.get("official_name")
                }
                for u in universities if u.get("university_id")
            ]
            
            response_data = {
                "success": True,
                "universities": uni_list,
                "total": len(uni_list),
                "message": f"Found {len(uni_list)} universities in knowledge base"
            }
            
            # Cache in session state
            if tool_context and hasattr(tool_context, 'state'):
                tool_context.state[cache_key] = response_data
                logger.info(f"   Cached university list in session state")
            
            logger.info(f"   Retrieved {len(uni_list)} universities")
            return response_data
        else:
            return {
                "success": False,
                "error": result.get("error", "Failed to list universities"),
                "universities": []
            }
            
    except Exception as e:
        logger.error(f"List universities failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "universities": []
        }


def get_university(university_id: str) -> Dict[str, Any]:
    """
    Get a specific university profile by ID.
    
    Args:
        university_id: The university identifier (e.g., "ucb", "ucla", "usc")
        
    Returns:
        Dictionary with complete university profile
        
    Example:
        get_university("ucb")  # Get UC Berkeley profile
    """
    try:
        logger.info(f"="*60)
        logger.info(f"📋 TOOL: get_university")
        logger.info(f"   University ID: {university_id}")
        logger.info(f"="*60)
        
        url = f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}/?id={university_id}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"   Response success: {result.get('success')}")
        
        if result.get("success"):
            university = result.get("university", {})
            return {
                "success": True,
                "university": university,
                "message": f"Retrieved profile for: {university.get('official_name', university_id)}"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "University not found"),
                "message": f"Could not find university: {university_id}"
            }
            
    except Exception as e:
        logger.error(f"Get university failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to retrieve university: {str(e)}"
        }


def list_universities() -> Dict[str, Any]:
    """
    List all available universities in the knowledge base.
    
    Returns:
        Dictionary with list of all universities (name, location, acceptance rate)
        
    Example:
        list_universities()
    """
    try:
        logger.info(f"="*60)
        logger.info(f"📚 TOOL: list_universities")
        logger.info(f"="*60)
        
        url = KNOWLEDGE_BASE_UNIVERSITIES_URL
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"   Response success: {result.get('success')}")
        logger.info(f"   Universities count: {result.get('total', 0)}")
        
        if result.get("success"):
            return {
                "success": True,
                "universities": result.get("universities", []),
                "total": result.get("total", 0),
                "message": f"Found {result.get('total', 0)} universities in knowledge base"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": "Failed to list universities"
            }
            
    except Exception as e:
        logger.error(f"List universities failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list universities: {str(e)}"
        }


def get_college_list(user_email: str) -> Dict[str, Any]:
    """
    Retrieve the user's current college list.
    
    Args:
        user_email: The user's email address (e.g., user@gmail.com)
        
    Returns:
        Dictionary with college list items
    """
    try:
        logger.info(f"="*60)
        logger.info(f"📋 TOOL: get_college_list")
        logger.info(f"   User Email: {user_email}")
        logger.info(f"="*60)
        
        # Use endpoint directly if available, or fall back to profile search
        # Based on backend code, it's a separate endpoint: /get-college-list
        url = f"{PROFILE_MANAGER_ES_URL}/get-college-list"
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": user_email
        }
        
        # Support both GET params and likely POST body in backend
        params = {"user_email": user_email}
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            college_list = result.get("college_list", [])
            logger.info(f"   Found {len(college_list)} colleges")
            
            # Format list for easy reading
            formatted_list = []
            for item in college_list:
                uni_name = item.get('university_name', 'Unknown University')
                fit_data = item.get('fit_analysis', {})
                fit = fit_data.get('fit_category', 'Not Analyzed')
                
                # Add key factors if available to explain "Why"
                factors = fit_data.get('factors', [])
                factor_summary = ""
                if factors:
                    # Get top 2 impactful factors
                    top_factors = sorted(factors, key=lambda x: abs(x.get('score', 0)), reverse=True)[:2]
                    factor_strs = [f"{f.get('name')}: {f.get('score')}" for f in top_factors]
                    factor_summary = f" (Key Factors: {', '.join(factor_strs)})"
                
                formatted_list.append(f"- {uni_name} [Fit: {fit}]{factor_summary}")
            
            return {
                "success": True,
                "college_list": college_list,
                "formatted_list": "\n".join(formatted_list) if formatted_list else "College list is empty",
                "count": len(college_list)
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": f"Failed to retrieve college list: {result.get('error')}"
            }
            
    except Exception as e:
        logger.error(f"Get college list failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Service unavailable: {str(e)}"
        }


def search_user_profile(
    user_email: str,
    query: str = "student academic profile transcript grades courses extracurriculars"
) -> Dict[str, Any]:
    """
    Search user profile via the Profile Manager Cloud Function.
    
    Args:
        user_email: The user's email address (e.g., user@gmail.com)
        query: The search query (default: general profile query)
        
    Returns:
        Dictionary with profile content and metadata
        
    Example:
        search_user_profile(user_email="user@gmail.com")
    """
    try:
        logger.info(f"="*60)
        logger.info(f"👤 TOOL: search_user_profile")
        logger.info(f"   User Email: {user_email}")
        logger.info(f"   Query: {query}")
        logger.info(f"="*60)
        
        url = f"{PROFILE_MANAGER_ES_URL}/search"
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": user_email
        }
        
        data = {
            "query": query,
            "user_email": user_email,
            "limit": 5
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"   Response success: {result.get('success')}")
        logger.info(f"   Documents count: {len(result.get('documents', []))}")
        
        if result.get("success"):
            documents = []
            for doc in result.get("documents", []):
                document = {
                    "id": doc.get("id"),
                    "score": doc.get("score", 1.0),
                    "filename": doc.get("document", {}).get("filename"),
                    "content": doc.get("document", {}).get("content", ""),
                    "metadata": doc.get("document", {}).get("metadata", {})
                }
                documents.append(document)
            
            return {
                "success": True,
                "documents": documents,
                "total_found": result.get("total_found", len(documents)),
                "user_email": user_email,
                "profile_data": documents[0]["content"] if documents else "No profile found",
                "message": f"Found {len(documents)} profile documents for: {user_email}"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": f"Profile search failed: {result.get('error', 'Unknown error')}"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Profile search request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Profile service unavailable: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Profile search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Profile search failed: {str(e)}"
        }


# ============================================
# COLLEGE FIT ANALYSIS TOOL
# ============================================
import re
from datetime import datetime


def parse_student_profile_data(profile_content: str) -> Dict[str, Any]:
    """Extract structured academic data from profile text content."""
    if not profile_content:
        return {}
    
    content = profile_content if isinstance(profile_content, str) else str(profile_content)
    
    def extract_float(pattern, text, default=None):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        return default
    
    def extract_int(pattern, text, default=None):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                pass
        return default
    
    # GPA extraction
    weighted_gpa = extract_float(r'Weighted\s*GPA[:\s]+(\d+\.\d+)', content)
    if not weighted_gpa:
        weighted_gpa = extract_float(r'GPA\s*\(Weighted\)[:\s]+(\d+\.\d+)', content)
    
    unweighted_gpa = extract_float(r'Unweighted\s*GPA[:\s]+(\d+\.\d+)', content)
    uc_gpa = extract_float(r'UC\s*(?:Weighted\s*)?GPA[:\s]+(\d+\.\d+)', content)
    
    # Test scores
    sat_score = extract_int(r'SAT[:\s]+(\d{4})', content)
    act_score = extract_int(r'ACT[:\s]+(\d{2})', content)
    
    # AP courses and scores
    ap_scores = {}
    ap_pattern = r'AP\s+([A-Za-z\s]+?):\s*(\d)'
    for match in re.finditer(ap_pattern, content):
        ap_scores[match.group(1).strip()] = int(match.group(2))
    
    ap_count = len(ap_scores)
    if ap_count == 0:
        ap_list_match = re.search(r'AP\s+Courses?[:\s]+(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if ap_list_match:
            ap_count = len(re.findall(r'AP\s+[A-Za-z]+', ap_list_match.group(1)))
    
    # Intended major
    major_match = re.search(r'(?:Intended\s+)?Major[:\s]+([^\n,]+)', content, re.IGNORECASE)
    intended_major = major_match.group(1).strip() if major_match else None
    
    # Leadership detection
    has_leadership = bool(re.search(r'(?:President|Vice President|Captain|Leader|Founder|Director|Chair)', content, re.IGNORECASE))
    
    # Awards count
    awards_section = re.search(r'AWARDS?[:\s]+(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
    awards_count = len(re.findall(r'\n\s*[-•]', awards_section.group(1))) if awards_section else 0
    
    return {
        'weighted_gpa': weighted_gpa or uc_gpa,
        'unweighted_gpa': unweighted_gpa,
        'sat_score': sat_score,
        'act_score': act_score,
        'ap_scores': ap_scores,
        'ap_count': max(ap_count, len(ap_scores)),
        'intended_major': intended_major,
        'has_leadership': has_leadership,
        'awards_count': awards_count
    }


def refine_fit_with_llm(
    deterministic_result: Dict[str, Any],
    student_profile: Dict[str, Any],
    university_data: Dict[str, Any],
    acceptance_rate: float
) -> Dict[str, Any]:
    """
    Use LLM to refine the fit analysis by considering qualitative factors.
    
    Args:
        deterministic_result: The initial deterministic scoring result
        student_profile: Student's academic profile data
        university_data: University profile data
        acceptance_rate: University's acceptance rate
        
    Returns:
        Refined fit result with adjusted category and AI-generated explanation
    """
    try:
        logger.info(f"[FIT LLM] Starting LLM refinement for {deterministic_result.get('university_name')}")
        
        # Apply acceptance rate guardrails first
        det_category = deterministic_result.get('fit_category', 'REACH')
        det_percentage = deterministic_result.get('match_percentage', 50)
        
        # Guardrails based on acceptance rate
        max_category = 'SAFETY'
        if acceptance_rate < 7:
            max_category = 'SUPER_REACH'
        elif acceptance_rate < 15:
            max_category = 'REACH'
        elif acceptance_rate < 30:
            max_category = 'TARGET'
        
        category_order = ['SUPER_REACH', 'REACH', 'TARGET', 'SAFETY']
        det_idx = category_order.index(det_category) if det_category in category_order else 0
        max_idx = category_order.index(max_category)
        
        # Cap the category if deterministic is too optimistic
        if det_idx > max_idx:
            det_category = max_category
            logger.info(f"[FIT LLM] Capped category from {deterministic_result.get('fit_category')} to {det_category} due to {acceptance_rate}% acceptance rate")
        
        # Prepare context for LLM
        uni_name = deterministic_result.get('university_name', 'Unknown')
        factors_text = "\n".join([
            f"- {f['name']}: {f['score']}/{f['max']} pts - {f['detail']}"
            for f in deterministic_result.get('factors', [])
        ])
        
        student_summary = f"""
GPA: Weighted {student_profile.get('weighted_gpa', 'N/A')}, Unweighted {student_profile.get('unweighted_gpa', 'N/A')}
SAT: {student_profile.get('sat_score', 'N/A')}
ACT: {student_profile.get('act_score', 'N/A')}
AP Courses: {student_profile.get('ap_count', 0)} courses with average score {student_profile.get('ap_avg', 'N/A')}
Activities: {len(student_profile.get('activities', []))} activities
Awards: {len(student_profile.get('awards', []))} awards
""".strip()
        
        uni_summary = f"""
University: {uni_name}
Acceptance Rate: {acceptance_rate}%
SAT Range: {university_data.get('sat_range', 'N/A')}
GPA Range: {university_data.get('gpa_range', 'N/A')}
Type: {university_data.get('type', 'N/A')}
""".strip()

        prompt = f"""You are an expert college admissions counselor. Analyze this student's fit for {uni_name}.

STUDENT PROFILE:
{student_summary}

UNIVERSITY DATA:
{uni_summary}

DETERMINISTIC SCORING RESULT:
Category: {det_category}
Match: {det_percentage}%
Factor Breakdown:
{factors_text}

TASK:
1. Review the deterministic scoring against the student profile and university selectivity
2. Consider that {uni_name} has a {acceptance_rate}% acceptance rate
3. For highly selective schools (<15%), even strong profiles are typically REACH
4. Validate or adjust the category: SAFETY (>70% chance), TARGET (40-70%), REACH (15-40%), SUPER_REACH (<15%)

STYLE GUIDELINES for "explanation":
- **Direct Address**: Speak directly to the student using "You" and "Your" (e.g., "Your GPA is strong...", NOT "The student's GPA...").
- **Markdown Formatting**: Use **bolding** for key terms, bullet points for lists, and line breaks for readability.
- **Tone**: Professional, encouraging, but realistic.

Respond in JSON format ONLY:
{{
  "final_category": "REACH",
  "confidence": 85,
  "adjustment_reason": "Brief reason if category was adjusted, or empty if validated",
  "explanation": "2-3 paragraph personalized analysis of your fit including: 1) Overall assessment with category and percentage, 2) Key strengths and areas of concern, 3) Specific recommendations for your application. Use Markdown!"
}}"""

        # Call Gemini
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )
        
        result_text = response.text.strip()
        logger.info(f"[FIT LLM] Got response from LLM")
        
        # Parse JSON response
        llm_result = json.loads(result_text)
        
        final_category = llm_result.get('final_category', det_category).upper()
        explanation = llm_result.get('explanation', '')
        adjustment_reason = llm_result.get('adjustment_reason', '')
        
        # Ensure category is valid
        if final_category not in category_order:
            final_category = det_category
        
        # Apply guardrails again to LLM result
        final_idx = category_order.index(final_category)
        if final_idx > max_idx:
            final_category = max_category
            logger.info(f"[FIT LLM] Re-capped LLM category to {final_category}")
        
        logger.info(f"[FIT LLM] Final category: {final_category} (was {deterministic_result.get('fit_category')})")
        
        return {
            "success": True,
            "final_category": final_category,
            "explanation": explanation,
            "adjustment_reason": adjustment_reason,
            "llm_refined": True
        }
        
    except Exception as e:
        logger.error(f"[FIT LLM] Error in LLM refinement: {e}")
        # Fall back to deterministic result
        return {
            "success": False,
            "final_category": deterministic_result.get('fit_category', 'REACH'),
            "explanation": "",
            "adjustment_reason": "",
            "llm_refined": False,
            "error": str(e)
        }


def parse_test_range(test_string: str) -> tuple:
    """Parse test score range like '1510-1560' into (min, max)."""
    if not test_string:
        return (1200, 1400)
    try:
        if '-' in str(test_string):
            parts = str(test_string).split('-')
            return (int(parts[0].strip()), int(parts[1].strip()))
        return (int(test_string), int(test_string))
    except:
        return (1200, 1400)


def sanitize_for_json(obj):
    """Ensure all values are JSON-serializable and replace None with appropriate defaults."""
    if obj is None:
        return ""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj if item is not None]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def get_cached_fit_analysis(user_email: str, university_id: str) -> Dict[str, Any]:
    """Check if fit analysis already exists in the user's college_list."""
    try:
        response = requests.get(
            f"{PROFILE_MANAGER_ES_URL}/get-college-list",
            headers={'X-User-Email': user_email},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            college_list = data.get('college_list', [])
            for college in college_list:
                if college.get('university_id') == university_id:
                    fit = college.get('fit_analysis')
                    if fit and fit.get('fit_category'):
                        logger.info(f"[FIT CACHE] Found cached fit for {university_id}: {fit.get('fit_category')}")
                        return sanitize_for_json(fit)
        return {}  # Return empty dict instead of None
    except Exception as e:
        logger.warning(f"[FIT CACHE] Failed to check cache: {e}")
        return {}  # Return empty dict instead of None


def store_fit_analysis(user_email: str, university_id: str, fit_analysis: Dict[str, Any]) -> bool:
    """Store fit analysis result in the user's profile college_list."""
    try:
        response = requests.post(
            f"{PROFILE_MANAGER_ES_URL}/update-fit-analysis",
            json={
                'user_email': user_email,
                'university_id': university_id,
                'fit_analysis': fit_analysis
            },
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        if response.status_code == 200:
            logger.info(f"[FIT STORE] Stored fit for {university_id} in profile")
            return True
        else:
            logger.warning(f"[FIT STORE] Failed to store fit: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[FIT STORE] Error storing fit: {e}")
        return False


def calculate_college_fit(
    user_email: str,
    university_id: str,
    intended_major: str = "",
    force_recalculate: bool = False,
    tool_context: ToolContext = None  # ADK provides this automatically
) -> Dict[str, Any]:
    """
    Calculate college fit using deterministic 7-factor scoring algorithm.
    
    This tool analyzes a student's profile against a university's admission data
    to determine fit category (Safety, Target, Reach, Super Reach) and provides
    specific recommendations.
    
    The result is automatically stored in the student's profile under their college_list.
    If a fit analysis already exists and force_recalculate is False, returns the cached result.
    
    Args:
        user_email: Student's email to fetch their profile
        university_id: University identifier (e.g., "princeton_university", "stanford_university")
        intended_major: Student's intended major (optional, for major-fit scoring)
        force_recalculate: If True, recalculate even if cached result exists
    
    Returns:
        Dictionary with:
        - fit_category: SAFETY, TARGET, REACH, or SUPER_REACH
        - match_percentage: 0-100 overall match score
        - factors: List of scoring factors with details
        - recommendations: Specific improvement suggestions
    
    Example:
        calculate_college_fit(
            user_email="student@gmail.com",
            university_id="stanford_university",
            intended_major="Computer Science"
        )
    """
    logger.info(f"[FIT ANALYSIS] Starting fit calculation for {user_email} -> {university_id}")
    
    # Check for cached result first (unless force_recalculate is True)
    if not force_recalculate:
        cached_fit = get_cached_fit_analysis(user_email, university_id)
        if cached_fit.get('fit_category'):  # Check if valid cached result
            logger.info(f"[FIT ANALYSIS] Returning cached fit for {university_id}")
            cached_fit['from_cache'] = True
            cached_fit['success'] = True
            return cached_fit
    
    try:
        # Step 1: Fetch student profile using ADK session state for caching
        profile_result = None
        profile_cache_key = '_cache:student_profile'  # Session-scoped (no temp: prefix) for cross-turn persistence
        
        # Check if profile is cached in session state
        if tool_context and hasattr(tool_context, 'state'):
            cached_profile = tool_context.state.get(profile_cache_key)
            if cached_profile:
                logger.info(f"[FIT] Using ADK session-cached profile for {user_email}")
                profile_result = cached_profile
        
        # If not cached, fetch fresh and cache in session state
        if not profile_result:
            logger.info(f"[FIT] Fetching fresh profile for {user_email}")
            profile_result = search_user_profile(user_email)
            # Cache in ADK session state if context is available
            if tool_context and hasattr(tool_context, 'state'):
                tool_context.state[profile_cache_key] = profile_result
                logger.info(f"[FIT] Cached profile in ADK session state")
        
        logger.info(f"[FIT] Profile result success: {profile_result.get('success')}")
        
        # search_user_profile returns 'profile_data' not 'content'
        if not profile_result.get('success') or not profile_result.get('profile_data'):
            return {
                "success": False,
                "error": "Could not fetch student profile",
                "message": "Please upload your academic profile first"
            }
        
        profile_content = profile_result.get('profile_data', '')
        student_profile = parse_student_profile_data(profile_content)
        
        logger.info(f"[FIT] Parsed profile: GPA={student_profile.get('weighted_gpa')}, SAT={student_profile.get('sat_score')}")
        
        # Step 2: Fetch university data (with caching)
        university_data = None
        uni_cache_key = f'_cache:uni_{university_id}'  # Session-scoped, cache per university
        
        # Check if university data is cached in session state
        if tool_context and hasattr(tool_context, 'state'):
            cached_uni = tool_context.state.get(uni_cache_key)
            if cached_uni:
                logger.info(f"[FIT] Using ADK session-cached university data for {university_id}")
                university_data = cached_uni
        
        # If not cached, fetch fresh and cache in session state
        if not university_data:
            logger.info(f"[FIT] Fetching fresh university data for {university_id}")
            university_data = get_university(university_id)
            # Cache in ADK session state if context is available
            if tool_context and hasattr(tool_context, 'state'):
                tool_context.state[uni_cache_key] = university_data
                logger.info(f"[FIT] Cached university data in ADK session state")
        
        logger.info(f"[FIT] University data success: {university_data.get('success')}")
        
        # get_university returns {success, university}, where university contains the profile
        if not university_data.get('success') or not university_data.get('university'):
            return {
                "success": False,
                "error": f"University not found: {university_id}",
                "message": "University data not available in knowledge base"
            }
        
        # The university object contains acceptance_rate at top level and profile key with detailed data
        university_obj = university_data.get('university', {})
        uni_profile = university_obj.get('profile', {})
        
        logger.info(f"[FIT] University profile keys: {list(uni_profile.keys())[:10] if uni_profile else 'None'}")
        
        # Step 3: Calculate comprehensive fit
        factors = []
        recommendations = []
        total_score = 0
        max_score = 150
        
        # Extract admissions data - check multiple possible locations
        admissions = uni_profile.get('admissions_data', {})
        if not admissions:
            admissions = uni_profile.get('admissions', {})
        
        current_status = admissions.get('current_status', {})
        admitted_profile = admissions.get('admitted_student_profile', {})
        
        # Check for acceptance rate at multiple levels
        acceptance_rate = current_status.get('overall_acceptance_rate')
        if acceptance_rate is None:
            acceptance_rate = university_obj.get('acceptance_rate', 50)
        
        gpa_data = admitted_profile.get('gpa', {})
        try:
            uni_gpa_25 = float(str(gpa_data.get('percentile_25', '3.5')).replace('"', ''))
            uni_gpa_75 = float(str(gpa_data.get('percentile_75', '4.0')).replace('"', ''))
        except:
            uni_gpa_25, uni_gpa_75 = 3.5, 4.0
        
        testing_data = admitted_profile.get('testing', {})
        sat_range = testing_data.get('sat_composite_middle_50', '1200-1400')
        act_range = testing_data.get('act_composite_middle_50', '26-32')
        
        student_gpa = student_profile.get('weighted_gpa') or student_profile.get('unweighted_gpa') or 3.5
        student_sat = student_profile.get('sat_score')
        student_act = student_profile.get('act_score')
        ap_count = student_profile.get('ap_count', 0)
        ap_scores = student_profile.get('ap_scores', {})
        has_leadership = student_profile.get('has_leadership', False)
        awards_count = student_profile.get('awards_count', 0)
        
        # ============ FACTOR 1: GPA Match (40 points) ============
        if student_gpa >= uni_gpa_75 + 0.1:
            gpa_score = 40
            gpa_detail = f"Your {student_gpa:.2f} exceeds 75th percentile ({uni_gpa_75})"
        elif student_gpa >= uni_gpa_75:
            gpa_score = 36
            gpa_detail = f"Your {student_gpa:.2f} is at 75th percentile"
        elif student_gpa >= (uni_gpa_25 + uni_gpa_75) / 2:
            gpa_score = 28
            gpa_detail = f"Your {student_gpa:.2f} is above median admits"
        elif student_gpa >= uni_gpa_25:
            gpa_score = 20
            gpa_detail = f"Your {student_gpa:.2f} is at 25th percentile"
        elif student_gpa >= uni_gpa_25 - 0.15:
            gpa_score = 12
            gpa_detail = f"Your {student_gpa:.2f} is slightly below typical range"
        else:
            gpa_score = 5
            gpa_detail = f"Your {student_gpa:.2f} is below typical admits"
            recommendations.append("Focus on strong upward trend in remaining semesters")
        
        total_score += gpa_score
        factors.append({'name': 'GPA Match', 'score': gpa_score, 'max': 40, 'detail': gpa_detail})
        
        # ============ FACTOR 2: Test Scores (25 points) ============
        sat_25, sat_75 = parse_test_range(sat_range)
        act_25, act_75 = parse_test_range(act_range)
        
        test_score = 0
        test_detail = "No test scores provided"
        
        if student_sat:
            if student_sat >= sat_75:
                test_score = 25
                test_detail = f"Your SAT {student_sat} exceeds 75th percentile ({sat_75})"
            elif student_sat >= (sat_25 + sat_75) / 2:
                test_score = 20
                test_detail = f"Your SAT {student_sat} is in middle 50% ({sat_25}-{sat_75})"
            elif student_sat >= sat_25:
                test_score = 12
                test_detail = f"Your SAT {student_sat} is at 25th percentile"
            else:
                test_score = 5
                test_detail = f"Your SAT {student_sat} is below typical range"
                recommendations.append("Consider retaking SAT to reach middle 50% range")
        elif student_act:
            if student_act >= act_75:
                test_score = 25
                test_detail = f"Your ACT {student_act} exceeds 75th percentile ({act_75})"
            elif student_act >= (act_25 + act_75) / 2:
                test_score = 20
                test_detail = f"Your ACT {student_act} is in middle 50%"
            elif student_act >= act_25:
                test_score = 12
                test_detail = f"Your ACT {student_act} is at 25th percentile"
            else:
                test_score = 5
                test_detail = f"Your ACT {student_act} is below typical range"
        else:
            if current_status.get('is_test_optional'):
                test_score = 15
                test_detail = "Test optional - consider submitting if scores are strong"
            else:
                test_score = 8
                recommendations.append("Submit test scores as they are considered")
        
        total_score += test_score
        factors.append({'name': 'Test Scores', 'score': test_score, 'max': 25, 'detail': test_detail})
        
        # ============ FACTOR 3: Acceptance Rate (25 points) ============
        if acceptance_rate >= 60:
            rate_score = 25
            rate_detail = f"{acceptance_rate}% acceptance - accessible"
        elif acceptance_rate >= 40:
            rate_score = 20
            rate_detail = f"{acceptance_rate}% acceptance - moderately selective"
        elif acceptance_rate >= 25:
            rate_score = 16
            rate_detail = f"{acceptance_rate}% acceptance - selective"
        elif acceptance_rate >= 15:
            rate_score = 12
            rate_detail = f"{acceptance_rate}% acceptance - highly selective"
        elif acceptance_rate >= 10:
            rate_score = 8
            rate_detail = f"{acceptance_rate}% acceptance - very competitive"
        elif acceptance_rate >= 5:
            rate_score = 5
            rate_detail = f"{acceptance_rate}% acceptance - extremely selective"
        else:
            rate_score = 2
            rate_detail = f"{acceptance_rate}% acceptance - ultra-selective (Ivy-tier)"
        
        total_score += rate_score
        factors.append({'name': 'Acceptance Rate', 'score': rate_score, 'max': 25, 'detail': rate_detail})
        
        # ============ FACTOR 4: Course Rigor (20 points) ============
        ap_course_pts = min(10, ap_count * 1.2)
        high_scores = sum(1 for s in ap_scores.values() if s >= 4)
        quality_pts = min(10, high_scores * 2)
        
        rigor_score = int(ap_course_pts + quality_pts)
        rigor_detail = f"{ap_count} AP courses"
        if high_scores > 0:
            rigor_detail += f", {high_scores} scores of 4+"
        
        if rigor_score < 10 and acceptance_rate < 20:
            recommendations.append("Consider taking additional AP courses")
        
        total_score += rigor_score
        factors.append({'name': 'Course Rigor', 'score': rigor_score, 'max': 20, 'detail': rigor_detail})
        
        # ============ FACTOR 5: Major Fit (15 points) ============
        major_to_check = intended_major or student_profile.get('intended_major', '')
        major_score = 8
        major_detail = "No specific major selected"
        
        if major_to_check:
            academic_structure = uni_profile.get('academic_structure', {})
            all_majors = []
            for college in academic_structure.get('colleges', []):
                for major in college.get('majors', []):
                    all_majors.append(major.get('name', '').lower())
            
            major_lower = major_to_check.lower()
            
            if any(major_lower in m for m in all_majors):
                major_score = 15
                major_detail = f"{major_to_check} is offered"
            elif any(m.startswith(major_lower[:4]) for m in all_majors):
                major_score = 10
                major_detail = f"Related programs to {major_to_check} available"
            else:
                major_score = 5
                major_detail = f"{major_to_check} may not be directly offered"
                recommendations.append(f"Verify {major_to_check} availability or consider related majors")
        
        total_score += major_score
        factors.append({'name': 'Major Fit', 'score': major_score, 'max': 15, 'detail': major_detail})
        
        # ============ FACTOR 6: Activities (15 points) ============
        activity_score = 5
        activity_details = []
        
        if has_leadership:
            activity_score += 4
            activity_details.append("Leadership experience")
        if awards_count >= 3:
            activity_score += 3
            activity_details.append(f"{awards_count} awards")
        elif awards_count >= 1:
            activity_score += 1
        
        activity_score = min(15, activity_score)
        activity_detail = ", ".join(activity_details) if activity_details else "Activities noted"
        
        total_score += activity_score
        factors.append({'name': 'Activities', 'score': activity_score, 'max': 15, 'detail': activity_detail})
        
        # ============ FACTOR 7: Early Action Boost (10 points) ============
        early_stats = current_status.get('early_admission_stats', [])
        early_score = 0
        early_detail = "No significant early advantage"
        
        for stat in early_stats:
            early_rate = stat.get('acceptance_rate', 0)
            plan_type = stat.get('plan_type', '')
            if early_rate and early_rate > acceptance_rate * 1.5:
                early_score = 10
                early_detail = f"{plan_type}: {early_rate}% vs {acceptance_rate}% regular"
                recommendations.append(f"Apply {plan_type} for higher acceptance rate")
                break
            elif early_rate and early_rate > acceptance_rate * 1.2:
                early_score = 6
                early_detail = f"{plan_type} offers modest boost ({early_rate}%)"
                break
        
        total_score += early_score
        factors.append({'name': 'Early Action', 'score': early_score, 'max': 10, 'detail': early_detail})
        
        # ============ CALCULATE FINAL CATEGORY ============
        match_percentage = int((total_score / max_score) * 100)
        
        if match_percentage >= 75:
            fit_category = 'SAFETY'
        elif match_percentage >= 55:
            fit_category = 'TARGET'
        elif match_percentage >= 35:
            fit_category = 'REACH'
        else:
            fit_category = 'SUPER_REACH'
        
        if not recommendations:
            if fit_category == 'SAFETY':
                recommendations.append("Strong match - focus on compelling essays")
            elif fit_category == 'TARGET':
                recommendations.append("Good fit - emphasize unique qualities")
        
        # Get university name from multiple sources
        uni_name = university_obj.get('official_name') or uni_profile.get('metadata', {}).get('official_name') or university_id.replace('_', ' ').title()
        
        # Generate detailed explanation
        explanation_parts = []
        explanation_parts.append(f"**Overall Assessment: {fit_category}** ({match_percentage}% match)")
        explanation_parts.append("")
        explanation_parts.append(f"Based on your academic profile and {uni_name}'s admission data, here's a detailed breakdown:")
        explanation_parts.append("")
        
        # Add factor explanations
        for factor in factors:
            score_pct = int((factor['score'] / factor['max']) * 100) if factor['max'] > 0 else 0
            if score_pct >= 75:
                strength = "✅ Strong"
            elif score_pct >= 50:
                strength = "🟡 Moderate"
            else:
                strength = "⚠️ Area for improvement"
            explanation_parts.append(f"**{factor['name']}** ({factor['score']}/{factor['max']} pts): {strength}")
            explanation_parts.append(f"  - {factor['detail']}")
            explanation_parts.append("")
        
        # Add category-specific summary
        if fit_category == 'SAFETY':
            explanation_parts.append("🟢 **Summary**: Your profile exceeds this school's typical admitted student profile. Strong likelihood of admission with a compelling application.")
        elif fit_category == 'TARGET':
            explanation_parts.append("🔵 **Summary**: Your profile aligns well with this school's admitted student profile. Reasonable chance of admission with strong essays and activities.")
        elif fit_category == 'REACH':
            explanation_parts.append("🟠 **Summary**: Your profile is below the typical admitted student. You'll need exceptional essays, activities, or other distinguishing factors.")
        else:
            explanation_parts.append("🔴 **Summary**: This is a significant reach. Consider strengthening your application with unique experiences, awards, or strong recommendations.")
        
        deterministic_explanation = "\n".join(explanation_parts)
        
        logger.info(f"[FIT] Deterministic result for {uni_name}: {fit_category} ({match_percentage}%)")
        
        # Build preliminary result for LLM refinement
        preliminary_result = {
            "fit_category": fit_category,
            "match_percentage": match_percentage,
            "university_name": uni_name,
            "factors": factors,
        }
        
        # Prepare university data for LLM
        sat_range = 'N/A'
        gpa_range = 'N/A'
        uni_type = university_obj.get('location', {}).get('type', 'N/A')
        
        try:
            admissions = uni_profile.get('admissions_data', {}) or uni_profile.get('admissions', {})
            admitted_profile = admissions.get('admitted_student_profile', {})
            
            sat_data = admitted_profile.get('test_scores', {}).get('sat', {})
            if sat_data:
                sat_range = f"{sat_data.get('composite_25th', 'N/A')}-{sat_data.get('composite_75th', 'N/A')}"
            
            gpa_data = admitted_profile.get('gpa', {})
            if gpa_data:
                gpa_range = f"{gpa_data.get('25th_percentile', 'N/A')}-{gpa_data.get('75th_percentile', 'N/A')}"
        except:
            pass
        
        university_llm_data = {
            "sat_range": sat_range,
            "gpa_range": gpa_range,
            "type": uni_type,
        }
        
        # Call LLM for hybrid refinement
        llm_result = refine_fit_with_llm(
            preliminary_result,
            student_profile,
            university_llm_data,
            acceptance_rate
        )
        
        # Use LLM results if successful, otherwise use deterministic
        if llm_result.get('success') and llm_result.get('llm_refined'):
            final_category = llm_result.get('final_category', fit_category)
            final_explanation = llm_result.get('explanation', deterministic_explanation)
            adjustment_reason = llm_result.get('adjustment_reason', '')
            is_llm_refined = True
            logger.info(f"[FIT] LLM refined: {fit_category} -> {final_category}")
        else:
            final_category = fit_category
            final_explanation = deterministic_explanation
            adjustment_reason = ''
            is_llm_refined = False
            logger.info(f"[FIT] Using deterministic result (LLM failed): {final_category}")
        
        fit_result = {
            "success": True,
            "fit_category": final_category,
            "match_percentage": match_percentage,
            "university_name": uni_name,
            "university_id": university_id,
            "factors": factors,
            "recommendations": recommendations[:5],
            "explanation": final_explanation,
            "adjustment_reason": adjustment_reason,
            "llm_refined": is_llm_refined,
            "deterministic_category": fit_category,
            "total_score": total_score,
            "max_score": max_score,
            "calculated_at": datetime.utcnow().isoformat(),
            "from_cache": False
        }
        
        # Store the fit result in the user's profile
        store_fit_analysis(user_email, university_id, fit_result)
        
        # Sanitize before returning to ensure ADK compatibility
        return sanitize_for_json(fit_result)
        
    except Exception as e:
        logger.error(f"[FIT ERROR] {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Fit analysis failed: {str(e)}"
        }


def recalculate_all_fits(user_email: str) -> Dict[str, Any]:
    """
    Recalculate fit analysis for all universities in the user's college list.
    Call this when the user's profile has been updated.
    
    Args:
        user_email: Student's email address
    
    Returns:
        Dictionary with:
        - success: True if recalculation was successful
        - updated_count: Number of universities recalculated
        - fit_results: Dictionary mapping university_id to fit_category
    
    Example:
        recalculate_all_fits(user_email="student@gmail.com")
    """
    logger.info(f"[FIT RECALC] Recalculating all fits for {user_email}")
    
    try:
        # Get user's college list
        response = requests.get(
            f"{PROFILE_MANAGER_ES_URL}/get-college-list",
            headers={'X-User-Email': user_email},
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": "Failed to fetch college list",
                "updated_count": 0
            }
        
        data = response.json()
        college_list = data.get('college_list', [])
        
        if not college_list:
            return {
                "success": True,
                "message": "No colleges in list to recalculate",
                "updated_count": 0,
                "fit_results": {}
            }
        
        fit_results = {}
        updated_count = 0
        
        for college in college_list:
            university_id = college.get('university_id')
            intended_major = college.get('intended_major', '')
            
            logger.info(f"[FIT RECALC] Recalculating {university_id}")
            
            # Force recalculate by passing force_recalculate=True
            fit = calculate_college_fit(
                user_email=user_email,
                university_id=university_id,
                intended_major=intended_major,
                force_recalculate=True
            )
            
            if fit.get('success'):
                fit_results[university_id] = fit.get('fit_category')
                updated_count += 1
        
        logger.info(f"[FIT RECALC] Completed: {updated_count} universities updated")
        
        return {
            "success": True,
            "message": f"Recalculated fit for {updated_count} universities",
            "updated_count": updated_count,
            "fit_results": fit_results
        }
        
    except Exception as e:
        logger.error(f"[FIT RECALC ERROR] {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"Recalculation failed: {str(e)}"
        }
