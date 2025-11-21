"""
Student Profile Tools - Interface to Profile Manager Cloud Function
Calls the profile manager ES cloud function for student profile search and retrieval
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Profile Manager Cloud Function URL
PROFILE_MANAGER_ES_URL = os.environ.get('PROFILE_MANAGER_ES_URL', 'https://profile-manager-es-pfnwjfp26a-ue.a.run.app')

def search_student_profile(user_id: str = "", query: str = "", size: int = 10) -> Dict[str, Any]:
    """
    Search student profiles via the Profile Manager Cloud Function.
    
    Args:
        user_id: Student ID to filter profiles
        query: Search query text within profile content
        size: Maximum number of results to return
    
    Returns:
        Dictionary with search results including profiles and metadata
    """
    try:
        # Call the profile manager cloud function
        url = f"{PROFILE_MANAGER_ES_URL}/profiles"
        params = {
            "user_id": user_id,
            "size": size,
            "from": 0
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": user_id
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            # Transform to match expected agent format
            profiles = []
            for doc in data.get("documents", []):
                profile = {
                    "id": doc["id"],
                    "filename": doc["document"].get("filename"),
                    "file_name": doc["document"].get("filename"),
                    "user_id": doc["document"].get("user_id"),
                    "indexed_at": doc["document"].get("indexed_at"),
                    "upload_date": doc["document"].get("upload_date"),
                    "content": doc["document"].get("content", ""),
                    "metadata": doc["document"].get("metadata", {}),
                    "file_size": doc["document"].get("file_size"),
                    "file_type": doc["document"].get("file_type"),
                    "score": 1.0  # Default score since API doesn't return relevance scores
                }
                profiles.append(profile)
            
            return {
                "success": True,
                "query": query,
                "user_id": user_id,
                "total": data.get("total", 0),
                "profiles": profiles,
                "filters_applied": bool(user_id and user_id.strip())
            }
        else:
            return {
                "success": False,
                "error": data.get("error", "Unknown error"),
                "profiles": []
            }
            
    except Exception as e:
        logger.error(f"Student profile search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "profiles": []
        }

def get_student_profile_by_id(profile_id: str, user_id: str = "") -> Dict[str, Any]:
    """
    Retrieve a specific student profile by ID via the Profile Manager Cloud Function.
    
    Args:
        profile_id: The profile ID to retrieve
        user_id: The user ID for authorization (optional)
    
    Returns:
        Dictionary with profile content and metadata
    """
    try:
        # For now, we'll implement this by listing all profiles and finding the one we want
        result = list_student_profiles(user_id, size=100, from_index=0)
        
        if result["success"]:
            # Find the profile with the matching ID
            for profile in result["profiles"]:
                if profile["id"] == profile_id:
                    return {
                        "success": True,
                        "profile": profile
                    }
            
            return {
                "success": False,
                "error": f"Profile {profile_id} not found",
                "profile_id": profile_id
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to get student profile {profile_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "profile_id": profile_id
        }

def list_student_profiles(user_id: str, size: int = 20, from_index: int = 0) -> Dict[str, Any]:
    """
    List all student profiles for a specific user via the Profile Manager Cloud Function.
    
    Args:
        user_id: The user ID to filter profiles
        size: Number of profiles to return
        from_index: Starting index for pagination
    
    Returns:
        Dictionary with list of user profiles
    """
    try:
        # Call the profile manager cloud function
        url = f"{PROFILE_MANAGER_ES_URL}/profiles"
        params = {
            "user_id": user_id,
            "size": size,
            "from": from_index
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": user_id
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            # Transform to match expected agent format
            profiles = []
            for doc in data.get("documents", []):
                profile = {
                    "id": doc["id"],
                    "filename": doc["document"].get("filename"),
                    "file_name": doc["document"].get("filename"),
                    "user_id": doc["document"].get("user_id"),
                    "indexed_at": doc["document"].get("indexed_at"),
                    "upload_date": doc["document"].get("upload_date"),
                    "metadata": doc["document"].get("metadata", {}),
                    "content_length": len(doc["document"].get("content", "")),
                    "file_size": doc["document"].get("file_size"),
                    "file_type": doc["document"].get("file_type")
                }
                profiles.append(profile)
            
            return {
                "success": True,
                "profiles": profiles,
                "total": data.get("total", 0),
                "from": from_index,
                "size": size
            }
        else:
            return {
                "success": False,
                "error": data.get("error", "Unknown error"),
                "profiles": []
            }
            
    except Exception as e:
        logger.error(f"Failed to list student profiles for {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "profiles": []
        }

def get_student_profile_metadata(profile_id: str, user_id: str = "") -> Dict[str, Any]:
    """
    Get structured metadata for a specific student profile via the Profile Manager Cloud Function.
    
    Args:
        profile_id: The profile ID to retrieve metadata for
        user_id: The user ID for authorization (optional)
    
    Returns:
        Dictionary with structured metadata
    """
    try:
        # Get the full profile first
        result = get_student_profile_by_id(profile_id, user_id)
        
        if not result["success"]:
            return result
        
        profile = result["profile"]
        metadata = profile.get("metadata", {})
        extracted_data = metadata.get("extracted_data", {})
        
        return {
            "success": True,
            "profile_id": profile_id,
            "filename": profile["filename"],
            "file_name": profile["file_name"],
            "user_id": profile["user_id"],
            "personal_info": extracted_data.get("personal_info", {}),
            "academic_info": extracted_data.get("academic_info", {}),
            "test_scores": extracted_data.get("test_scores", []),
            "courses": extracted_data.get("courses", []),
            "extracurriculars": extracted_data.get("extracurriculars", []),
            "awards": extracted_data.get("awards", []),
            "essays": extracted_data.get("essays", {}),
            "indexed_at": profile["indexed_at"],
            "upload_date": profile["upload_date"],
            "file_size": profile["file_size"],
            "file_type": profile["file_type"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get metadata for student profile {profile_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "profile_id": profile_id
        }

def delete_student_profile(profile_id: str, user_id: str = "") -> Dict[str, Any]:
    """
    Delete a student profile via the Profile Manager Cloud Function.
    
    Args:
        profile_id: The profile ID to delete
        user_id: The user ID for authorization
    
    Returns:
        Dictionary with deletion result
    """
    try:
        # Call the profile manager cloud function
        url = f"{PROFILE_MANAGER_ES_URL}/profiles/{profile_id}"
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": user_id
        }
        
        data = {"user_id": user_id}
        
        response = requests.delete(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            logger.info(f"Successfully deleted student profile {profile_id}")
            return {
                "success": True,
                "profile_id": profile_id,
                "message": result.get("message", "Student profile deleted successfully")
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "profile_id": profile_id
            }
            
    except Exception as e:
        logger.error(f"Failed to delete student profile {profile_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "profile_id": profile_id
        }
