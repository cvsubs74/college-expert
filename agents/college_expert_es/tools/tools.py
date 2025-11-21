"""
Knowledge Base Tools - Interface to Knowledge Base Manager Cloud Function (ES)
Calls the knowledge base manager ES cloud function for document search and retrieval
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Knowledge Base Manager Cloud Function URL (ES)
KNOWLEDGE_BASE_MANAGER_ES_URL = os.environ.get('KNOWLEDGE_BASE_MANAGER_ES_URL', 'https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app')
# Profile Manager Cloud Function URL (ES)
PROFILE_MANAGER_ES_URL = os.environ.get('PROFILE_MANAGER_ES_URL', 'https://profile-manager-es-pfnwjfp26a-ue.a.run.app')

def search_knowledge_base(
    query: str,
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Search documents via the Knowledge Base Manager Cloud Function (ES).
    Knowledge base is a generic store accessible to all users.
    
    Args:
        query: Search query text
        model: Gemini model to use (default: gemini-2.5-flash) - kept for compatibility
        
    Returns:
        Dictionary with search results including documents and metadata
    """
    try:
        # Call the knowledge base manager cloud function
        url = f"{KNOWLEDGE_BASE_MANAGER_ES_URL}/search"
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": "knowledge_base_user"  # Generic user for knowledge base access
        }
        
        data = {
            "query": query,
            "user_id": "",  # Empty for generic knowledge base search
            "limit": 10  # Number of results to return
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            # Transform to match expected agent format
            # ES returns "results" not "documents"
            documents = []
            for doc in result.get("results", []):
                document = {
                    "id": doc["id"],
                    "score": doc.get("score", 1.0),
                    "filename": doc["document"].get("filename"),
                    "file_name": doc["document"].get("filename"),
                    "user_id": doc["document"].get("user_id"),
                    "indexed_at": doc["document"].get("indexed_at"),
                    "upload_date": doc["document"].get("upload_date"),
                    "title": doc["document"].get("filename", ""),
                    "content": doc["document"].get("content", ""),
                    "university": doc["document"].get("university_name", ""),
                    "university_name": doc["document"].get("university_name", ""),
                    "metadata": doc["document"].get("metadata", {}),
                    "file_size": doc["document"].get("file_size"),
                    "file_type": doc["document"].get("file_type"),
                    "num_chunks": doc["document"].get("num_chunks", 0)
                }
                documents.append(document)
            
            return {
                "success": True,
                "documents": documents,
                "total_found": result.get("total", len(documents)),
                "query": query,
                "answer": f"Found {len(documents)} relevant documents for: {query}",
                "citations": [{"source": doc["filename"], "text": doc["content"][:200] + "..."} for doc in documents[:3]]
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": f"❌ Search failed: {result.get('error', 'Unknown error')}"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Knowledge base search request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Knowledge base service unavailable: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Knowledge base search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Search failed: {str(e)}"
        }

def search_user_profile(
    user_email: str,
    query: str = "student academic profile transcript grades courses extracurriculars",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Search user profile via the Profile Manager Cloud Function (ES).
    
    This function calls the profile manager cloud function to retrieve user profile data.
    
    Args:
        user_email: The user's email address (e.g., user@gmail.com)
        query: The search query (default: general profile query)
        model: Gemini model to use (default: gemini-2.5-flash) - kept for compatibility
        
    Returns:
        Dictionary with profile content and metadata
        
    Example:
        search_user_profile(
            user_email="user@gmail.com",
            query="student academic profile"
        )
    """
    try:
        print(f"[USER_PROFILE] Searching profile for user: {user_email}")
        
        # Call the profile manager cloud function
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
        
        if result.get("success"):
            # Transform to match expected agent format
            documents = []
            for doc in result.get("documents", []):
                document = {
                    "id": doc["id"],
                    "score": doc.get("score", 1.0),
                    "filename": doc["document"].get("filename"),
                    "file_name": doc["document"].get("filename"),
                    "user_id": doc["document"].get("user_id"),
                    "indexed_at": doc["document"].get("indexed_at"),
                    "upload_date": doc["document"].get("upload_date"),
                    "title": doc["document"].get("filename", ""),
                    "content": doc["document"].get("content", ""),
                    "metadata": doc["document"].get("metadata", {})
                }
                documents.append(document)
            
            return {
                "success": True,
                "documents": documents,
                "total_found": result.get("total_found", len(documents)),
                "user_email": user_email,
                "answer": f"Found {len(documents)} profile documents for: {user_email}",
                "profile_data": documents[0]["content"] if documents else "No profile found"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": f"❌ Profile search failed: {result.get('error', 'Unknown error')}"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Profile search request failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Profile service unavailable: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Profile search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Profile search failed: {str(e)}"
        }

