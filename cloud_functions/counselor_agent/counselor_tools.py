
import os
import logging
import requests
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Service URLs
PROFILE_MANAGER_URL = os.getenv('PROFILE_MANAGER_URL', 'http://localhost:8080')
KNOWLEDGE_BASE_UNIVERSITIES_URL = os.getenv('KNOWLEDGE_BASE_UNIVERSITIES_URL', 'http://localhost:8082')

def get_student_profile(user_email):
    """Fetch student profile from Profile Manager service."""
    try:
        url = f"{PROFILE_MANAGER_URL}/get-profile"
        response = requests.get(url, params={'user_email': user_email}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('profile', {})
        else:
            logger.error(f"Failed to fetch profile: {response.status_code} {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None

def get_college_list(user_email):
    """Fetch user's college list from Profile Manager service."""
    try:
        url = f"{PROFILE_MANAGER_URL}/get-college-list"
        response = requests.get(url, params={'user_email': user_email}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('college_list', [])
        else:
            logger.error(f"Failed to fetch college list: {response.status_code} {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching college list: {e}")
        return []
        
def get_all_fits(user_email):
    """Fetch user's fit analysis for all colleges. Returns dict keyed by university_id."""
    try:
        url = f"{PROFILE_MANAGER_URL}/get-fits"
        response = requests.get(url, params={'user_email': user_email}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            fits_list = data.get('fits', [])
            
            # Convert list to dict keyed by university_id for easy lookup
            if isinstance(fits_list, list):
                return {fit.get('university_id'): fit for fit in fits_list if fit.get('university_id')}
            elif isinstance(fits_list, dict):
                return fits_list
            else:
                return {}
        else:
            logger.error(f"Failed to fetch fits: {response.status_code} {response.text}")
            return {}
    except Exception as e:
        logger.error(f"Error fetching fits: {e}")
        return {}

def get_university_data(university_id):
    """Fetch full university data from Knowledge Base service."""
    try:
        url = f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}"
        response = requests.get(url, params={'id': university_id}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('university', {}).get('profile', {})
        else:
            logger.warning(f"University not found: {university_id}")
            return None
    except Exception as e:
        logger.error(f"Error fetching university data: {e}")
        return None

def extract_deadlines(university_data):
    """
    Extract application deadlines from university profile JSON.
    Returns list of objects: { 'type': 'Regular Decision', 'date': '2026-01-01', 'notes': '...' }
    """
    deadlines = []
    
    if not university_data:
        return deadlines
        
    app_process = university_data.get('application_process', {})
    raw_deadlines = app_process.get('application_deadlines', [])
    
    # Deadline types to EXCLUDE (not relevant for high school senior Fall admissions)
    excluded_types = ['summer semester', 'spring semester', 'summer session', 'spring session']
    
    for item in raw_deadlines:
        # Standardize structure
        d_date = item.get('date') or item.get('deadline')
        d_type = item.get('plan_type') or item.get('type', 'Regular Decision')
        d_notes = item.get('notes', '')
        
        # Skip summer/spring semester deadlines
        if d_type and d_type.lower() in excluded_types:
            continue
        
        if d_date:
            # Filter out non-date strings if possible, or keep them if useful
            # e.g., "Varies" is useful info
            deadlines.append({
                'type': d_type,
                'date': d_date,
                'notes': d_notes
            })
            
    return deadlines

def fetch_aggregated_deadlines(user_email):
    """
    Fetch all deadlines for the user's college list.
    """
    college_list = get_college_list(user_email)
    aggregated = []
    
    for college in college_list:
        uni_id = college.get('university_id')
        uni_name = college.get('university_name', uni_id)
        
        uni_data = get_university_data(uni_id)
        uni_deadlines = extract_deadlines(uni_data)
        
        for d in uni_deadlines:
            aggregated.append({
                'university_id': uni_id,
                'university_name': uni_name,
                'deadline_type': d['type'],
                'date': d['date'],
                'notes': d['notes']
            })
            
    # Sort by date (handling non-dates by putting them last)
    def sort_key(x):
        d = x['date']
        # Check if YYYY-MM-DD
        if len(d) == 10 and d[4] == '-' and d[7] == '-':
            return d
        return "9999-99-99" # Push non-dates to end
        
    aggregated.sort(key=sort_key)
    
    return aggregated

def extract_scholarships(university_data):
    """Extract scholarships from university profile."""
    if not university_data:
        return []
    
    financials = university_data.get('financials', {})
    return financials.get('scholarships', [])

def get_targeted_university_context(user_email):
    """
    Fetch targeted sections from university profiles for chat context:
    - Application deadlines
    - Scholarships (name, type, amount, deadline, application_method)
    - Financial aid info (aid_philosophy, average_need_based_aid, average_merit_aid)
    
    Returns compact dict keyed by university_id for efficient context injection.
    """
    college_list = get_college_list(user_email)
    context = {}
    
    for college in college_list:
        uni_id = college.get('university_id')
        uni_name = college.get('university_name', uni_id)
        
        uni_data = get_university_data(uni_id)
        if not uni_data:
            continue
            
        # Extract targeted sections
        financials = uni_data.get('financials', {})
        app_process = uni_data.get('application_process', {})
        
        context[uni_id] = {
            'name': uni_name,
            'deadlines': app_process.get('application_deadlines', []),
            'scholarships': financials.get('scholarships', []),
            'aid_philosophy': financials.get('aid_philosophy'),
            'avg_need_aid': financials.get('average_need_based_aid'),
            'avg_merit_aid': financials.get('average_merit_aid'),
            'percent_receiving_aid': financials.get('percent_receiving_aid')
        }
        
    return context
