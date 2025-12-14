"""
Tools for CollegeListAgent - API calls for college list operations.
"""
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PROFILE_MANAGER_URL = "https://profile-manager-es-pfnwjfp26a-ue.a.run.app"

def get_college_list_from_api(user_email: str) -> Dict[str, Any]:
    """
    Retrieve student's college list from Profile Manager ES cloud function.
    
    Args:
        user_email: Student's email address
    
    Returns:
        Dictionary with college list data or error message
    """
    try:
        logger.info(f"[get_college_list_from_api] Fetching list for {user_email}")
        
        response = requests.post(
            f"{PROFILE_MANAGER_URL}/get-college-list",
            json={"user_email": user_email},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"[get_college_list_from_api] API returned status {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to fetch college list: HTTP {response.status_code}",
                "college_list": []
            }
        
        data = response.json()
        
        if not data.get("success"):
            return {
                "success": False,
                "message": data.get("error", "Unknown error fetching college list"),
                "college_list": []
            }
        
        college_list = data.get("college_list", [])
        logger.info(f"[get_college_list_from_api] Found {len(college_list)} colleges")
        
        return {
            "success": True,
            "action": "GET",
            "college_list": college_list,
            "total_count": len(college_list),
            "message": f"Found {len(college_list)} colleges in your list"
        }
        
    except Exception as e:
        logger.error(f"[get_college_list_from_api] Error: {str(e)}")
        return {
            "success": False,
            "message": f"Error fetching college list: {str(e)}",
            "college_list": []
        }


def add_college_to_list_api(
    user_email: str,
    university_id: str,
    university_name: str,
    intended_major: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a college to student's list via Profile Manager ES cloud function.
    
    Args:
        user_email: Student's email address
        university_id: University identifier (e.g., "stanford_university")
        university_name: Official university name
        intended_major: Optional intended major for this university
    
    Returns:
        Dictionary with updated college list or error message
    """
    try:
        logger.info(f"[add_college_to_list_api] Adding {university_id} for {user_email}")
        
        payload = {
            "user_email": user_email,
            "action": "add",
            "university": {
                "id": university_id,
                "name": university_name
            }
        }
        
        if intended_major:
            payload["intended_major"] = intended_major
        
        response = requests.post(
            f"{PROFILE_MANAGER_URL}/update-college-list",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"[add_college_to_list_api] API returned status {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to add college: HTTP {response.status_code}",
                "college_list": []
            }
        
        data = response.json()
        
        if not data.get("success"):
            return {
                "success": False,
                "message": data.get("error", "Unknown error adding college"),
                "college_list": []
            }
        
        college_list = data.get("college_list", [])
        logger.info(f"[add_college_to_list_api] Successfully added {university_name}")
        
        return {
            "success": True,
            "action": "ADD",
            "college_list": college_list,
            "total_count": len(college_list),
            "message": f"Added {university_name} to your list"
        }
        
    except Exception as e:
        logger.error(f"[add_college_to_list_api] Error: {str(e)}")
        return {
            "success": False,
            "message": f"Error adding college: {str(e)}",
            "college_list": []
        }


def remove_college_from_list_api(user_email: str, university_id: str) -> Dict[str, Any]:
    """
    Remove a college from student's list via Profile Manager ES cloud function.
    
    Args:
        user_email: Student's email address
        university_id: University identifier to remove
    
    Returns:
        Dictionary with updated college list or error message
    """
    try:
        logger.info(f"[remove_college_from_list_api] Removing {university_id} for {user_email}")
        
        response = requests.post(
            f"{PROFILE_MANAGER_URL}/update-college-list",
            json={
                "user_email": user_email,
                "action": "remove",
                "university": {"id": university_id}
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"[remove_college_from_list_api] API returned status {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to remove college: HTTP {response.status_code}",
                "college_list": []
            }
        
        data = response.json()
        
        if not data.get("success"):
            return {
                "success": False,
                "message": data.get("error", "Unknown error removing college"),
                "college_list": []
            }
        
        college_list = data.get("college_list", [])
        logger.info(f"[remove_college_from_list_api] Successfully removed {university_id}")
        
        return {
            "success": True,
            "action": "REMOVE",
            "college_list": college_list,
            "total_count": len(college_list),
            "message": f"Removed {university_id} from your list"
        }
        
    except Exception as e:
        logger.error(f"[remove_college_from_list_api] Error: {str(e)}")
        return {
            "success": False,
            "message": f"Error removing college: {str(e)}",
            "college_list": []
        }
