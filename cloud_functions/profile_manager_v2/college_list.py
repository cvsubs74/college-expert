"""
College list management operations.
Handles adding/removing universities to/from user's college list (Launchpad).
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

from firestore_db import get_db

logger = logging.getLogger(__name__)


def add_university_to_list(user_id: str, university_id: str, university_data: dict) -> dict:
    """
    Add university to user's college list.
    
    Args:
        user_id: User's email
        university_id: University ID
        university_data: Dict with university_name, category, notes, etc.
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        
        list_item = {
            'university_id': university_id,
            'university_name': university_data.get('university_name', university_id),
            'category': university_data.get('category', 'target'),  #reach, target, safety
            'notes': university_data.get('notes', ''),
            'status': university_data.get('status', 'planning'),  # planning, applied, accepted, rejected
            'application_deadline': university_data.get('application_deadline'),
            'added_at': datetime.utcnow().isoformat()
        }
        
        success = db.add_to_college_list(user_id, university_id, list_item)
        
        if success:
            logger.info(f"[COLLEGE_LIST] Added {university_id} for {user_id}")
            return {
                "success": True,
                "message": "University added to list"
            }
        else:
            return {
                "success": False,
                "error": "Failed to add university"
            }
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Add failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def remove_university_from_list(user_id: str, university_id: str) -> dict:
    """
    Remove university from user's college list.
    
    Args:
        user_id: User's email
        university_id: University ID to remove
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        success = db.remove_from_college_list(user_id, university_id)
        
        if success:
            logger.info(f"[COLLEGE_LIST] Removed {university_id} for {user_id}")
            return {
                "success": True,
                "message": "University removed from list"
            }
        else:
            return {
                "success": False,
                "error": "Failed to remove university"
            }
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Remove failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_college_list(user_id: str) -> List[Dict]:
    """
    Get user's college list.
    
    Args:
        user_id: User's email
        
    Returns:
        List of university dicts
    """
    try:
        db = get_db()
        return db.get_college_list(user_id)
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Get list failed: {e}")
        return []


def update_list_item(user_id: str, university_id: str, updates: dict) -> dict:
    """
    Update college list item.
    
    Args:
        user_id: User's email
        university_id: University ID
        updates: Dict with fields to update (notes, category, status, etc.)
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        
        # Add updated timestamp
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        # Use add_to_college_list with merge=True behavior
        success = db.add_to_college_list(user_id, university_id, updates)
        
        if success:
            logger.info(f"[COLLEGE_LIST] Updated {university_id} for {user_id}")
            return {
                "success": True,
                "message": "List item updated"
            }
        else:
            return {
                "success": False,
                "error": "Failed to update list item"
            }
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST] Update failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
