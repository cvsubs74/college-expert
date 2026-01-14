"""
College list management operations.
Handles adding/removing universities to/from user's college list (Launchpad).
"""

import logging
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

from firestore_db import get_db

logger = logging.getLogger(__name__)

# Knowledge base URL for enriching university data
KNOWLEDGE_BASE_UNIVERSITIES_URL = os.getenv(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)


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
    Get user's college list, enriched with university data from knowledge base.
    
    This mirrors the ES backend's handle_get_college_list() which fetches
    logo_url, location, and other data from the knowledgebase_universities index.
    
    Args:
        user_id: User's email
        
    Returns:
        List of university dicts enriched with KB data
    """
    try:
        db = get_db()
        items = db.get_college_list(user_id)
        
        if not items:
            return []
        
        # Collect university IDs for batch lookup
        university_ids = [item.get('university_id') for item in items if item.get('university_id')]
        
        # Fetch enrichment data from knowledge base API
        university_data = {}
        if university_ids:
            try:
                # Call the knowledge base API to get university details (batch get via POST)
                response = requests.post(
                    KNOWLEDGE_BASE_UNIVERSITIES_URL,
                    json={"university_ids": university_ids},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and data.get('universities'):
                        for uni in data['universities']:
                            uni_id = uni.get('university_id')
                            if uni_id:
                                # Extract location string from location object
                                location = uni.get('location', {})
                                location_str = None
                                if isinstance(location, dict):
                                    city = location.get('city', '')
                                    state = location.get('state', '')
                                    if city and state:
                                        location_str = f"{city}, {state}"
                                    elif state:
                                        location_str = state
                                elif isinstance(location, str):
                                    location_str = location
                                
                                # Get logo_url from profile if available
                                profile = uni.get('profile', {}) or {}
                                logo_url = uni.get('logo_url') or profile.get('logo_url')
                                
                                university_data[uni_id] = {
                                    'location': location_str,
                                    'acceptance_rate': uni.get('acceptance_rate'),
                                    'soft_fit_category': uni.get('soft_fit_category'),
                                    'us_news_rank': uni.get('us_news_rank'),
                                    'summary': uni.get('summary'),
                                    'logo_url': logo_url,
                                    'media': uni.get('media')
                                }
                        logger.info(f"[COLLEGE_LIST] Enriched {len(university_data)} universities with KB data")
                else:
                    logger.warning(f"[COLLEGE_LIST] KB batch-get returned {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[COLLEGE_LIST] Could not fetch university KB data: {e}")
            except Exception as e:
                logger.warning(f"[COLLEGE_LIST] Error parsing KB response: {e}")
        
        # Enrich items with knowledge base data
        enriched_items = []
        for item in items:
            uni_id = item.get('university_id')
            uni_info = university_data.get(uni_id, {})
            
            # Build enriched item
            enriched_item = {
                'university_id': uni_id,
                'university_name': item.get('university_name'),
                'status': item.get('status', 'favorites'),
                'category': item.get('category'),
                'order': item.get('order'),
                'added_at': item.get('added_at'),
                'notes': item.get('notes') or item.get('student_notes'),
                # Enriched fields from knowledge base
                'location': uni_info.get('location') or item.get('location'),
                'acceptance_rate': uni_info.get('acceptance_rate') or item.get('acceptance_rate'),
                'soft_fit_category': uni_info.get('soft_fit_category') or item.get('soft_fit_category'),
                'us_news_rank': uni_info.get('us_news_rank') or item.get('us_news_rank'),
                'summary': uni_info.get('summary') or item.get('summary'),
                'logo_url': uni_info.get('logo_url') or item.get('logo_url'),
            }
            enriched_items.append(enriched_item)
        
        return enriched_items
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
