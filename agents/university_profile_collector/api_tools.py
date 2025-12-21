"""
API Tools for University Data Collection.

These tools wrap College Scorecard and Urban Institute IPEDS APIs
and can be used by LlmAgent instances.
"""
import os
import logging
import requests
from typing import Optional, Dict
from google.adk.tools import ToolContext
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# API Configuration
SCORECARD_BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
SCORECARD_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
URBAN_BASE_URL = "https://educationdata.urban.org/api/v1/college-university/ipeds"

# IPEDS Unit ID Lookup
IPEDS_LOOKUP = {
    "stanford university": 243744,
    "massachusetts institute of technology": 166683,
    "mit": 166683,
    "yale university": 130794,
    "harvard university": 166027,
    "princeton university": 186131,
    "university of california-berkeley": 110635,
    "uc berkeley": 110635,
    "university of california berkeley": 110635,
    "university of southern california": 123961,
    "usc": 123961,
    "university of california-los angeles": 110662,
    "ucla": 110662,
    "columbia university": 190150,
    "university of pennsylvania": 215062,
    "duke university": 152651,
    "northwestern university": 147767,
    "cornell university": 190415,
    "brown university": 217156,
    "dartmouth college": 182670,
    "university of chicago": 144050,
    "johns hopkins university": 162928,
    "rice university": 227757,
    "vanderbilt university": 221999,
    "carnegie mellon university": 211440,
    "university of notre dame": 152080,
    "georgetown university": 131496,
    "university of michigan-ann arbor": 170976,
    "university of michigan": 170976,
    "new york university": 193900,
    "boston university": 164988,
    "georgia institute of technology": 139755,
    "georgia tech": 139755,
    "university of florida": 134130,
    "university of texas at austin": 228778,
    "california institute of technology": 110404,
    "caltech": 110404,
}


def _get_ipeds_id(university_name: str) -> Optional[int]:
    """Internal: Lookup IPEDS Unit ID for a university name."""
    name_lower = university_name.lower().strip()
    if name_lower in IPEDS_LOOKUP:
        return IPEDS_LOOKUP[name_lower]
    for key, unitid in IPEDS_LOOKUP.items():
        if key in name_lower or name_lower in key:
            return unitid
    return None


# =============================================================================
# COLLEGE SCORECARD API TOOLS
# =============================================================================

SCORECARD_FIELDS = [
    "id", "school.name", "school.city", "school.state",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.25th_percentile.critical_reading",
    "latest.admissions.sat_scores.25th_percentile.math",
    "latest.admissions.sat_scores.75th_percentile.critical_reading",
    "latest.admissions.sat_scores.75th_percentile.math",
    "latest.admissions.act_scores.25th_percentile.cumulative",
    "latest.admissions.act_scores.75th_percentile.cumulative",
    "latest.student.size",
    "latest.student.demographics.race_ethnicity.white",
    "latest.student.demographics.race_ethnicity.black",
    "latest.student.demographics.race_ethnicity.hispanic",
    "latest.student.demographics.race_ethnicity.asian",
    "latest.student.demographics.race_ethnicity.non_resident_alien",
    "latest.student.demographics.first_generation",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.aid.pell_grant_rate",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.student.retention_rate.four_year.full_time",
    "latest.completion.rate_suppressed.four_year",
]


def get_college_scorecard_data(
    tool_context: ToolContext,
    university_name: str
) -> dict:
    """
    Get university data from College Scorecard API.
    
    Returns admission rates, test scores, tuition, demographics, and outcomes.
    
    Args:
        university_name: Name of the university to look up
        
    Returns:
        Dictionary with university data including:
        - admission_rate: Overall acceptance rate (as decimal, e.g., 0.05 = 5%)
        - sat_25th/75th: SAT score ranges
        - act_25th/75th: ACT score ranges
        - tuition_in_state/out_of_state: Tuition costs
        - median_earnings_10yr: Median earnings 10 years after entry
        - retention_rate: Freshman retention rate
        - graduation_rate_4yr: 4-year graduation rate
        - demographics: Race/ethnicity breakdown
    """
    if not SCORECARD_API_KEY:
        return {"error": "No API key configured. Set DATA_GOV_API_KEY environment variable."}
    
    params = {
        "api_key": SCORECARD_API_KEY,
        "school.name": university_name,
        "fields": ",".join(SCORECARD_FIELDS),
        "per_page": 1
    }
    
    try:
        response = requests.get(SCORECARD_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return {"error": f"No data found for '{university_name}'"}
        
        school = results[0]
        
        # Transform to cleaner format
        return {
            "school_name": school.get("school.name"),
            "city": school.get("school.city"),
            "state": school.get("school.state"),
            "admission_rate": school.get("latest.admissions.admission_rate.overall"),
            "sat_reading_25th": school.get("latest.admissions.sat_scores.25th_percentile.critical_reading"),
            "sat_reading_75th": school.get("latest.admissions.sat_scores.75th_percentile.critical_reading"),
            "sat_math_25th": school.get("latest.admissions.sat_scores.25th_percentile.math"),
            "sat_math_75th": school.get("latest.admissions.sat_scores.75th_percentile.math"),
            "act_25th": school.get("latest.admissions.act_scores.25th_percentile.cumulative"),
            "act_75th": school.get("latest.admissions.act_scores.75th_percentile.cumulative"),
            "student_size": school.get("latest.student.size"),
            "tuition_in_state": school.get("latest.cost.tuition.in_state"),
            "tuition_out_of_state": school.get("latest.cost.tuition.out_of_state"),
            "pell_grant_rate": school.get("latest.aid.pell_grant_rate"),
            "median_earnings_10yr": school.get("latest.earnings.10_yrs_after_entry.median"),
            "retention_rate": school.get("latest.student.retention_rate.four_year.full_time"),
            "graduation_rate_4yr": school.get("latest.completion.rate_suppressed.four_year"),
            "demographics": {
                "white": school.get("latest.student.demographics.race_ethnicity.white"),
                "black": school.get("latest.student.demographics.race_ethnicity.black"),
                "hispanic": school.get("latest.student.demographics.race_ethnicity.hispanic"),
                "asian": school.get("latest.student.demographics.race_ethnicity.asian"),
                "international": school.get("latest.student.demographics.race_ethnicity.non_resident_alien"),
                "first_generation": school.get("latest.student.demographics.first_generation"),
            }
        }
    except Exception as e:
        logger.error(f"Scorecard API error: {e}")
        return {"error": str(e)}


# =============================================================================
# URBAN INSTITUTE IPEDS API TOOLS
# =============================================================================

def get_ipeds_admissions_data(
    tool_context: ToolContext,
    university_name: str
) -> dict:
    """
    Get admissions data from Urban Institute IPEDS API.
    
    Returns application counts, admission counts, and enrollment data.
    
    Args:
        university_name: Name of the university to look up
        
    Returns:
        Dictionary with:
        - applications: Number of applications received
        - admitted: Number of students admitted
        - enrolled: Number of students enrolled
        - calculated_acceptance_rate: Calculated from admitted/applications
    """
    unitid = _get_ipeds_id(university_name)
    if not unitid:
        return {"error": f"Could not find IPEDS ID for '{university_name}'"}
    
    try:
        url = f"{URBAN_BASE_URL}/admissions-enrollment/2022/"
        response = requests.get(url, params={"unitid": unitid, "sex": 99}, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return {"error": f"No IPEDS data found for unitid {unitid}"}
        
        record = results[0]
        applications = record.get("number_applied")
        admitted = record.get("number_admitted")
        enrolled = record.get("number_enrolled_total")
        
        acceptance_rate = None
        if applications and admitted:
            acceptance_rate = round((admitted / applications) * 100, 2)
        
        return {
            "unitid": unitid,
            "applications": applications,
            "admitted": admitted,
            "enrolled": enrolled,
            "calculated_acceptance_rate_percent": acceptance_rate
        }
    except Exception as e:
        logger.error(f"IPEDS API error: {e}")
        return {"error": str(e)}


def get_ipeds_tuition_data(
    tool_context: ToolContext,
    university_name: str
) -> dict:
    """
    Get tuition data from Urban Institute IPEDS API.
    
    Args:
        university_name: Name of the university to look up
        
    Returns:
        Dictionary with in-state and out-of-state tuition and fees.
    """
    unitid = _get_ipeds_id(university_name)
    if not unitid:
        return {"error": f"Could not find IPEDS ID for '{university_name}'"}
    
    try:
        url = f"{URBAN_BASE_URL}/academic-year-tuition/2021/"
        response = requests.get(url, params={"unitid": unitid, "level_of_study": 1}, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return {"error": f"No tuition data found for unitid {unitid}"}
        
        # Find the record with tuition data
        tuition_data = {}
        for r in results:
            if r.get("tuition_type") == 3:  # In-state
                tuition_data["in_state_tuition"] = r.get("tuition_fees")
            elif r.get("tuition_type") == 4:  # Out-of-state
                tuition_data["out_of_state_tuition"] = r.get("tuition_fees")
        
        return tuition_data if tuition_data else {"in_state_tuition": results[0].get("tuition_fees")}
    except Exception as e:
        logger.error(f"IPEDS tuition API error: {e}")
        return {"error": str(e)}
