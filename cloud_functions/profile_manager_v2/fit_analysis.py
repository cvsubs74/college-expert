"""
College fit analysis operations.
Stores and retrieves fit analysis results.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from firestore_db import get_db

logger = logging.getLogger(__name__)


def save_fit_analysis(user_id: str, university_id: str, fit_data: dict) -> dict:
    """
    Save college fit analysis result.
    
    Args:
        user_id: User's email
        university_id: University ID
        fit_data: Fit analysis data (score, analysis, strengths, etc.)
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        
        # Add computed timestamp
        fit_data['computed_at'] = datetime.utcnow().isoformat()
        fit_data['university_id'] = university_id
        
        success = db.save_college_fit(user_id, university_id, fit_data)
        
        if success:
            logger.info(f"[FIT_ANALYSIS] Saved fit for {university_id}, user {user_id}")
            return {
                "success": True,
                "message": "Fit analysis saved"
            }
        else:
            return {
                "success": False,
                "error": "Failed to save fit analysis"
            }
        
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Save failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_fit_analysis(user_id: str, university_id: str) -> Optional[Dict]:
    """
    Get fit analysis for a specific university.
    
    Args:
        user_id: User's email
        university_id: University ID
        
    Returns:
        Fit analysis dict or None
    """
    try:
        db = get_db()
        return db.get_college_fit(user_id, university_id)
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Get fit failed: {e}")
        return None


def get_all_fits(user_id: str) -> List[Dict]:
    """
    Get all fit analyses for a user.
    
    Args:
        user_id: User's email
        
    Returns:
        List of fit analysis dicts
    """
    try:
        db = get_db()
        fits = db.get_all_fits(user_id)
        
        # Enrich fits with missing logo_url and location
        for fit in fits:
            # Construct location if missing
            if not fit.get('location'):
                city = fit.get('city')
                state = fit.get('state')
                if city and state:
                    fit['location'] = f"{city}, {state}"
                elif city:
                    fit['location'] = city
                elif state:
                    fit['location'] = state

            if not fit.get('logo_url'):
                university_id = fit.get('university_id')
                if university_id:
                    fit['logo_url'] = f"https://storage.googleapis.com/college-counselor-media/universities/{university_id}/logo.png"
        
        return fits
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Get all fits failed: {e}")
        return []


def delete_fit_analysis(user_id: str, university_id: str) -> dict:
    """
    Delete fit analysis for a university.
    
    Args:
        user_id: User's email
        university_id: University ID
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        success = db.delete_college_fit(user_id, university_id)
        
        if success:
            logger.info(f"[FIT_ANALYSIS] Deleted fit for {university_id}")
            return {
                "success": True,
                "message": "Fit analysis deleted"
            }
        else:
            return {
                "success": False,
                "error": "Failed to delete fit analysis"
            }
        
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS] Delete failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
