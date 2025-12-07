"""
University Knowledge Base Tools - Interface to Knowledge Base Manager Universities Cloud Function
Provides hybrid search (BM25 + vector) for university profiles.
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

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


def search_universities(
    query: str,
    search_type: str = "hybrid",
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search universities using hybrid search (BM25 + vector).
    
    This searches the structured university profiles with detailed admissions data,
    academic programs, career outcomes, and strategic insights.
    
    Args:
        query: Natural language search query (e.g., "computer science research California")
        search_type: Search mode - "hybrid" (default), "semantic", or "keyword"
            - hybrid: Combines BM25 text + vector similarity (best quality)
            - semantic: Vector similarity only (conceptual matching)
            - keyword: BM25 text only (exact term matching)
        filters: Optional filters to narrow results:
            - state: State abbreviation (e.g., "CA", "IL")
            - type: "Public" or "Private"
            - acceptance_rate_max: Maximum acceptance rate (e.g., 25)
            - acceptance_rate_min: Minimum acceptance rate
            - market_position: e.g., "Public Ivy"
        limit: Maximum results to return (default: 10)
        
    Returns:
        Dictionary with:
        - success: Boolean indicating success
        - results: List of university matches with profiles
        - total: Number of results found
        - query: Original query
        
    Example:
        search_universities(
            query="top engineering programs California public",
            search_type="hybrid",
            filters={"state": "CA", "acceptance_rate_max": 30}
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
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"   Response success: {result.get('success')}")
        logger.info(f"   Results count: {result.get('total', 0)}")
        
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
