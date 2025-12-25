"""
Source Discovery Tools - Tools for finding and validating university data sources.
"""
import os
import requests
import logging
from typing import Optional
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# Known IPEDS Unit IDs for universities
IPEDS_LOOKUP = {
    "university_of_southern_california": 123961,
    "stanford_university": 243744,
    "massachusetts_institute_of_technology": 166683,
    "mit": 166683,
    "yale_university": 130794,
    "harvard_university": 166027,
    "princeton_university": 186131,
    "university_of_california_berkeley": 110635,
    "ucla": 110662,
    "university_of_california_los_angeles": 110662,
    "columbia_university": 190150,
    "university_of_pennsylvania": 215062,
    "duke_university": 152651,
    "northwestern_university": 147767,
    "cornell_university": 190415,
    "brown_university": 217156,
    "dartmouth_college": 182670,
    "university_of_chicago": 144050,
    "johns_hopkins_university": 162928,
    "rice_university": 227757,
    "vanderbilt_university": 221999,
    "carnegie_mellon_university": 211440,
    "university_of_notre_dame": 152080,
    "georgetown_university": 131496,
    "university_of_michigan": 170976,
    "new_york_university": 193900,
    "boston_university": 164988,
    "georgia_institute_of_technology": 139755,
    "university_of_florida": 134130,
    "university_of_texas_austin": 228778,
    "california_institute_of_technology": 110404,
}


def lookup_ipeds_id(
    tool_context: ToolContext,
    university_id: str
) -> dict:
    """
    Look up the IPEDS Unit ID for a university.
    
    This is needed for deterministic API calls to IPEDS/College Scorecard.
    
    Args:
        university_id: Standardized university ID (e.g., "university_of_southern_california")
    
    Returns:
        Dictionary with ipeds_id or error message
    """
    normalized = university_id.lower().strip().replace(" ", "_")
    
    if normalized in IPEDS_LOOKUP:
        return {
            "success": True,
            "ipeds_id": IPEDS_LOOKUP[normalized],
            "university_id": normalized
        }
    
    # Try partial match
    for key, ipeds_id in IPEDS_LOOKUP.items():
        if key in normalized or normalized in key:
            return {
                "success": True,
                "ipeds_id": ipeds_id,
                "university_id": key,
                "match_type": "partial"
            }
    
    return {
        "success": False,
        "error": f"IPEDS ID not found for '{university_id}'. Will need manual lookup.",
        "suggestion": "Search at https://nces.ed.gov/ipeds/find-your-college"
    }


def validate_url(
    tool_context: ToolContext,
    url: str
) -> dict:
    """
    Validate that a URL is accessible and return metadata about the response.
    
    Args:
        url: URL to validate
    
    Returns:
        Dictionary with accessibility status and metadata
    """
    logger.info(f"Validating URL: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CollegeCounselor/1.0'
        }
        response = requests.head(url, timeout=15, allow_redirects=True, headers=headers)
        
        # Some servers don't support HEAD, try GET
        if response.status_code >= 400:
            response = requests.get(url, timeout=15, allow_redirects=True, headers=headers, stream=True)
        
        content_type = response.headers.get("Content-Type", "unknown")
        is_pdf = "pdf" in content_type.lower() or url.lower().endswith(".pdf")
        is_html = "html" in content_type.lower()
        
        return {
            "url": url,
            "accessible": response.status_code == 200,
            "status_code": response.status_code,
            "content_type": content_type,
            "is_pdf": is_pdf,
            "is_html": is_html,
            "final_url": response.url,
            "suggested_extraction_method": "PDF_EXTRACT" if is_pdf else "HTML_CSS_SELECTOR"
        }
    except requests.exceptions.Timeout:
        return {
            "url": url,
            "accessible": False,
            "error": "Request timed out after 15 seconds"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "url": url,
            "accessible": False,
            "error": f"Connection error: {str(e)}"
        }
    except Exception as e:
        return {
            "url": url,
            "accessible": False,
            "error": str(e)
        }


def get_api_source_config(
    tool_context: ToolContext,
    university_id: str,
    ipeds_id: int
) -> dict:
    """
    Generate API source configurations for College Scorecard and IPEDS.
    
    These are Tier 1 deterministic sources that don't require web discovery.
    
    Args:
        university_id: Standardized university ID
        ipeds_id: IPEDS Unit ID for API lookups
    
    Returns:
        Dictionary with API source configurations
    """
    api_key_configured = bool(os.getenv("DATA_GOV_API_KEY"))
    
    return {
        "college_scorecard": {
            "name": "College Scorecard API",
            "source_type": "API",
            "tier": 1,
            "url": "https://api.data.gov/ed/collegescorecard/v1/schools",
            "extraction_method": "API_JSON",
            "extraction_config": {
                "ipeds_id": ipeds_id,
                "api_key_env": "DATA_GOV_API_KEY",
                "fields": [
                    "latest.admissions.admission_rate.overall",
                    "latest.cost.tuition.in_state",
                    "latest.cost.tuition.out_of_state",
                    "latest.earnings.10_yrs_after_entry.median",
                    "latest.student.retention_rate.four_year.full_time",
                    "latest.completion.rate_suppressed.four_year"
                ]
            },
            "is_active": api_key_configured,
            "api_key_present": api_key_configured,
            "notes": "Tier 1 deterministic source for admissions and outcomes" if api_key_configured else "Set DATA_GOV_API_KEY to activate"
        },
        "urban_ipeds": {
            "name": "Urban Institute IPEDS API",
            "source_type": "API",
            "tier": 1,
            "url": "https://educationdata.urban.org/api/v1/college-university/ipeds",
            "extraction_method": "API_JSON",
            "extraction_config": {
                "unitid": ipeds_id,
                "endpoints": {
                    "admissions": f"/admissions-enrollment/2022/?unitid={ipeds_id}",
                    "tuition": f"/academic-year-tuition/2022/?unitid={ipeds_id}",
                    "demographics": f"/fall-enrollment/2022/?unitid={ipeds_id}"
                }
            },
            "is_active": True,
            "notes": "Tier 1 deterministic source for demographics and enrollment"
        }
    }
