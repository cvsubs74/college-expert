"""
Tools for FitAnalysisAgent - API calls to retrieve pre-computed fit data.
"""
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

PROFILE_MANAGER_URL = "https://profile-manager-es-pfnwjfp26a-ue.a.run.app"

def get_fit_from_api(user_email: str, university_id: str) -> Dict[str, Any]:
    """
    Retrieve pre-computed fit analysis from Profile Manager ES cloud function.
    
    Args:
        user_email: Student's email address
        university_id: University identifier (e.g., "stanford_university")
    
    Returns:
        Dictionary with fit data or error message
    """
    try:
        logger.info(f"[get_fit_from_api] Fetching fit for {university_id}, user={user_email}")
        
        # Call get-fits endpoint with limit=500 to get all fits
        response = requests.post(
            f"{PROFILE_MANAGER_URL}/get-fits",
            json={
                "user_email": user_email,
                "limit": 500
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"[get_fit_from_api] API returned status {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to fetch fits: HTTP {response.status_code}"
            }
        
        data = response.json()
        
        if not data.get("success"):
            logger.warning(f"[get_fit_from_api] API returned success=false")
            return {
                "success": False,
                "message": data.get("error", "Unknown error fetching fits")
            }
        
        # Find the specific university in the results
        results = data.get("results", [])
        university_fit = None
        
        for fit in results:
            if fit.get("university_id") == university_id:
                university_fit = fit
                break
        
        if not university_fit:
            logger.info(f"[get_fit_from_api] No fit found for {university_id}")
            return {
                "success": False,
                "message": f"No pre-computed fit found for {university_id}. It may need to be calculated first.",
                "university_id": university_id
            }
        
        # Return structured fit data
        logger.info(f"[get_fit_from_api] Found fit: {university_fit.get('fit_category')}")
        return {
            "success": True,
            "fit_category": university_fit.get("fit_category"),
            "match_percentage": university_fit.get("match_score") or university_fit.get("match_percentage"),
            "explanation": university_fit.get("explanation"),
            "factors": university_fit.get("factors", []),
            "recommendations": university_fit.get("recommendations", []),
            "university_id": university_fit.get("university_id"),
            "university_name": university_fit.get("university_name"),
            "message": f"Found {university_fit.get('fit_category')} fit with {university_fit.get('match_score', 0)}% match"
        }
        
    except requests.exceptions.Timeout:
        logger.error("[get_fit_from_api] Request timeout")
        return {
            "success": False,
            "message": "Request timeout while fetching fit data"
        }
    except Exception as e:
        logger.error(f"[get_fit_from_api] Error: {str(e)}")
        return {
            "success": False,
            "message": f"Error fetching fit data: {str(e)}"
        }
