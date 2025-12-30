"""
UniMiner Cloud Function

Validates university profiles, fills gaps using APIs, compares with ES data,
and handles ingestion workflows.

Endpoints:
  GET  /health           - Health check
  GET  /universities     - List universities from ES
  POST /validate         - Validate profile against schema
  POST /fill-gaps        - Fill missing fields with College Scorecard
  POST /compare          - Deep diff with existing ES data
  POST /ingest           - Push profile to ES
"""

import os
import json
import logging
import requests
import functions_framework
from typing import Any, Dict, List, Optional
from flask import jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== CONFIGURATION ==============

ES_CLOUD_ID = os.getenv("ES_CLOUD_ID")
ES_API_KEY = os.getenv("ES_API_KEY")
ES_UNIVERSITIES_INDEX = os.getenv("ES_UNIVERSITIES_INDEX", "knowledgebase_universities")

KB_UNIVERSITIES_URL = os.getenv(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)

COLLEGE_SCORECARD_API_KEY = os.getenv("COLLEGE_SCORECARD_API_KEY")
SCORECARD_BASE_URL = "https://api.data.gov/ed/collegescorecard/v1"

# GCS configuration for research profiles
GCS_BUCKET = os.getenv("RESEARCH_BUCKET", "college-counselling-478115-research")
GCS_PREFIX = "university_profiles/"

# CORS headers
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}


# ============== ELASTICSEARCH CLIENT ==============

def get_elasticsearch_client():
    """Create and return Elasticsearch client."""
    from elasticsearch import Elasticsearch
    
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("ES_CLOUD_ID and ES_API_KEY must be set")
    
    return Elasticsearch(
        cloud_id=ES_CLOUD_ID,
        api_key=ES_API_KEY
    )


def get_gcs_client():
    """Get GCS client if available."""
    try:
        from google.cloud import storage
        return storage.Client()
    except Exception as e:
        logger.warning(f"Could not initialize GCS client: {e}")
        return None


# ============== HELPER FUNCTIONS ==============

def normalize_university_id(name: str) -> str:
    """Create normalized university ID from name."""
    slug = name.lower()
    slug = slug.replace(" ", "_")
    slug = slug.replace(",", "")
    slug = slug.replace("-", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    slug = "_".join(filter(None, slug.split("_")))
    return slug


def find_null_fields(obj: Any, path: str = "") -> List[str]:
    """Recursively find all null/missing fields in an object."""
    nulls = []
    if obj is None:
        return [path] if path else []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            if value is None:
                nulls.append(new_path)
            elif isinstance(value, (dict, list)):
                nulls.extend(find_null_fields(value, new_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            nulls.extend(find_null_fields(item, f"{path}[{i}]"))
    
    return nulls


def count_fields(obj: Any) -> tuple:
    """Count populated and null fields in an object."""
    if obj is None:
        return 0, 1
    
    populated = 0
    null_count = 0
    
    if isinstance(obj, dict):
        for value in obj.values():
            if value is None:
                null_count += 1
            elif isinstance(value, (dict, list)):
                p, n = count_fields(value)
                populated += p
                null_count += n
            else:
                populated += 1
    elif isinstance(obj, list):
        for item in obj:
            p, n = count_fields(item)
            populated += p
            null_count += n
    else:
        return 1, 0
    
    return populated, null_count


def deep_diff(old: Any, new: Any, path: str = "") -> tuple:
    """Recursively compare two objects and return changes, additions, removals."""
    changes = []
    additions = []
    removals = []
    
    if type(old) != type(new):
        changes.append({"field": path, "old": old, "new": new, "type": "type_change"})
        return changes, additions, removals
    
    if isinstance(old, dict):
        old_keys = set(old.keys())
        new_keys = set(new.keys())
        
        for key in new_keys - old_keys:
            new_path = f"{path}.{key}" if path else key
            additions.append({"field": new_path, "value": new[key]})
        
        for key in old_keys - new_keys:
            new_path = f"{path}.{key}" if path else key
            removals.append({"field": new_path, "old_value": old[key]})
        
        for key in old_keys & new_keys:
            new_path = f"{path}.{key}" if path else key
            if old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    c, a, r = deep_diff(old[key], new[key], new_path)
                    changes.extend(c)
                    additions.extend(a)
                    removals.extend(r)
                elif isinstance(old[key], list) and isinstance(new[key], list):
                    if old[key] != new[key]:
                        changes.append({"field": new_path, "old": old[key], "new": new[key], "type": "list_change"})
                else:
                    changes.append({"field": new_path, "old": old[key], "new": new[key], "type": "value_change"})
    
    return changes, additions, removals


# ============== COLLEGE SCORECARD API ==============

def search_scorecard(school_name: str) -> Optional[Dict]:
    """Search College Scorecard for a university by name."""
    if not COLLEGE_SCORECARD_API_KEY:
        logger.warning("COLLEGE_SCORECARD_API_KEY not set")
        return None
    
    try:
        response = requests.get(
            f"{SCORECARD_BASE_URL}/schools",
            params={
                "api_key": COLLEGE_SCORECARD_API_KEY,
                "school.name": school_name,
                "fields": ",".join([
                    "id", "school.name", "school.city", "school.state",
                    "admissions.admission_rate.overall",
                    "cost.tuition.in_state", "cost.tuition.out_of_state",
                    "earnings.10_yrs_after_entry.median",
                    "student.retention_rate.four_year.full_time",
                    "completion.rate_suppressed.overall",
                    "aid.median_debt_suppressed.overall"
                ]),
                "per_page": 1
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            return data["results"][0]
        return None
        
    except Exception as e:
        logger.error(f"College Scorecard search failed: {e}")
        return None


def fill_from_scorecard(profile: Dict, scorecard_data: Dict) -> Dict:
    """Fill profile fields from College Scorecard data."""
    updated = dict(profile)
    filled = []
    
    mappings = {
        "admissions.admission_rate.overall": ["admissions_data", "current_status", "overall_acceptance_rate"],
        "earnings.10_yrs_after_entry.median": ["outcomes", "median_earnings_10yr"],
        "student.retention_rate.four_year.full_time": ["student_retention", "freshman_retention_rate"],
        "cost.tuition.in_state": ["financials", "cost_of_attendance_breakdown", "in_state", "tuition"],
        "cost.tuition.out_of_state": ["financials", "cost_of_attendance_breakdown", "out_of_state", "tuition"],
        "school.city": ["metadata", "location", "city"],
        "school.state": ["metadata", "location", "state"]
    }
    
    for scorecard_path, profile_path in mappings.items():
        value = scorecard_data
        for key in scorecard_path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
            if value is None:
                break
        
        if value is not None:
            current = updated
            for key in profile_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            if current.get(profile_path[-1]) is None:
                current[profile_path[-1]] = value
                filled.append(".".join(profile_path))
    
    return updated, filled


# ============== API HANDLERS ==============

def handle_health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "uniminer"})


def handle_list_universities():
    """List all universities from Elasticsearch."""
    try:
        response = requests.get(KB_UNIVERSITIES_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            universities = data.get("universities", [])
            return jsonify({
                "success": True,
                "count": len(universities),
                "universities": [
                    {
                        "university_id": u.get("university_id"),
                        "official_name": u.get("official_name"),
                        "acceptance_rate": u.get("acceptance_rate"),
                        "us_news_rank": u.get("us_news_rank"),
                        "soft_fit_category": u.get("soft_fit_category")
                    }
                    for u in universities
                ]
            })
        return jsonify({"success": False, "error": data.get("error")})
    except Exception as e:
        logger.error(f"List universities failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def handle_list_research_profiles():
    """List all research profiles from GCS."""
    gcs_client = get_gcs_client()
    if not gcs_client:
        return jsonify({"success": False, "error": "GCS not available", "profiles": []})
    
    try:
        bucket = gcs_client.bucket(GCS_BUCKET)
        blobs = bucket.list_blobs(prefix=GCS_PREFIX)
        
        profiles = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                name = blob.name.replace(GCS_PREFIX, '').replace('.json', '')
                profiles.append({
                    "name": name,
                    "filename": blob.name.split('/')[-1],
                    "gcs_uri": f"gs://{GCS_BUCKET}/{blob.name}",
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "size": blob.size
                })
        
        return jsonify({"success": True, "profiles": profiles})
    except Exception as e:
        logger.error(f"Failed to list profiles from GCS: {e}")
        return jsonify({"success": False, "error": str(e), "profiles": []})


def handle_get_research_profile():
    """Fetch a research profile from GCS."""
    filename = request.args.get("filename")
    if not filename:
        return jsonify({"success": False, "error": "filename parameter required"})
    
    # Ensure .json extension
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    
    gcs_client = get_gcs_client()
    if not gcs_client:
        return jsonify({"success": False, "error": "GCS not available"})
    
    try:
        bucket = gcs_client.bucket(GCS_BUCKET)
        blob_name = f"{GCS_PREFIX}{filename}"
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            return jsonify({"success": False, "error": f"Profile not found: {filename}"})
        
        content = blob.download_as_string()
        profile = json.loads(content)
        
        return jsonify({
            "success": True,
            "filename": filename,
            "profile": profile
        })
    except Exception as e:
        logger.error(f"Failed to fetch profile from GCS: {e}")
        return jsonify({"success": False, "error": str(e)})


def handle_validate():
    """Validate a profile against schema and return quality report."""
    data = request.get_json()
    profile = data.get("profile", {})
    
    # Handle nested wrapper
    if "university_profile" in profile:
        profile = profile["university_profile"]
    
    # Find null fields and count
    null_fields = find_null_fields(profile)
    populated, null_count = count_fields(profile)
    total = populated + null_count
    quality_score = (populated / total * 100) if total > 0 else 0
    
    # Identify critical missing fields
    critical_fields = [
        "metadata.official_name",
        "admissions_data.current_status.overall_acceptance_rate",
        "strategic_profile.us_news_rank",
        "outcomes.median_earnings_10yr"
    ]
    missing_critical = [f for f in critical_fields if f in null_fields]
    
    return jsonify({
        "valid": len(missing_critical) == 0,
        "quality_score": round(quality_score, 1),
        "total_fields": total,
        "populated_fields": populated,
        "null_field_count": null_count,
        "null_fields": null_fields[:100],
        "missing_critical": missing_critical
    })


def handle_fill_gaps():
    """
    Fill missing fields by calling the university_profile_collector agent
    with a targeted prompt specifying exactly which fields need data.
    """
    data = request.get_json()
    profile = data.get("profile", {})
    fields_to_fill = data.get("fields_to_fill", [])
    
    # Get university name
    metadata = profile.get("metadata", {})
    if "university_profile" in profile:
        metadata = profile["university_profile"].get("metadata", {})
    
    university_name = metadata.get("official_name", "")
    
    if not university_name:
        return jsonify({
            "success": False,
            "error": "Cannot determine university name",
            "filled_fields": [],
            "still_missing": fields_to_fill
        })
    
    if not fields_to_fill:
        return jsonify({
            "success": True,
            "message": "No fields to fill",
            "filled_fields": [],
            "still_missing": [],
            "updated_profile": profile
        })
    
    # Group fields by category for a focused search
    field_groups = categorize_missing_fields(fields_to_fill[:30])  # Limit to 30 fields
    
    # Build a targeted prompt for the agent
    prompt = build_gap_filling_prompt(university_name, field_groups, profile)
    
    logger.info(f"Calling agent to fill {len(fields_to_fill)} gaps for {university_name}")
    
    try:
        # Step 1: Create session
        session_url = f"{RESEARCH_AGENT_URL}/apps/university_profile_collector/users/gap_filler/sessions"
        session_res = requests.post(
            session_url,
            json={"user_input": "Hello"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        session_res.raise_for_status()
        session_data = session_res.json()
        session_id = session_data.get("id")
        logger.info(f"Gap-filling session created: {session_id}")
        
        # Step 2: Call /run with targeted prompt
        run_url = f"{RESEARCH_AGENT_URL}/run"
        run_res = requests.post(
            run_url,
            json={
                "app_name": "university_profile_collector",
                "user_id": "gap_filler",
                "session_id": session_id,
                "new_message": {
                    "parts": [{"text": prompt}]
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 min timeout for gap filling
        )
        run_res.raise_for_status()
        events = run_res.json()
        
        logger.info(f"Gap-filling agent returned {len(events) if isinstance(events, list) else 'unknown'} events")
        
        # Extract the gap-filled data from agent response
        filled_data = extract_gap_data_from_events(events)
        
        # Merge filled data into profile
        if filled_data:
            updated_profile = merge_gap_data(profile, filled_data)
            filled_fields = list(filled_data.keys())
            still_missing = [f for f in fields_to_fill if f not in filled_fields]
            
            return jsonify({
                "success": True,
                "filled_fields": filled_fields,
                "still_missing": still_missing,
                "source": "agent_google_search",
                "updated_profile": updated_profile
            })
        else:
            return jsonify({
                "success": False,
                "error": "Agent could not find additional data",
                "filled_fields": [],
                "still_missing": fields_to_fill,
                "updated_profile": profile
            })
            
    except requests.exceptions.Timeout:
        logger.error("Gap-filling timed out")
        return jsonify({
            "success": False,
            "error": "Gap-filling timed out. Try again with fewer fields.",
            "filled_fields": [],
            "still_missing": fields_to_fill,
            "updated_profile": profile
        })
    except Exception as e:
        logger.error(f"Gap-filling failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "filled_fields": [],
            "still_missing": fields_to_fill,
            "updated_profile": profile
        })


def categorize_missing_fields(fields: List[str]) -> Dict[str, List[str]]:
    """Group missing fields by category for focused searches."""
    categories = {
        "admissions": [],
        "academics": [],
        "financials": [],
        "outcomes": [],
        "application": [],
        "other": []
    }
    
    for field in fields:
        if "admission" in field.lower() or "acceptance" in field.lower() or "gpa" in field.lower():
            categories["admissions"].append(field)
        elif "academic" in field.lower() or "major" in field.lower() or "college" in field.lower():
            categories["academics"].append(field)
        elif "financial" in field.lower() or "tuition" in field.lower() or "scholarship" in field.lower():
            categories["financials"].append(field)
        elif "outcome" in field.lower() or "earning" in field.lower() or "employment" in field.lower():
            categories["outcomes"].append(field)
        elif "application" in field.lower() or "essay" in field.lower() or "deadline" in field.lower():
            categories["application"].append(field)
        else:
            categories["other"].append(field)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def build_gap_filling_prompt(university_name: str, field_groups: Dict[str, List[str]], profile: dict) -> str:
    """Build a targeted prompt for the agent to find specific missing data."""
    prompt = f"""TARGETED DATA SEARCH for {university_name}

I already have partial data for this university. I need you to find ONLY the following missing information using Google Search.

=== MISSING DATA TO FIND ===

"""
    
    for category, fields in field_groups.items():
        prompt += f"\n### {category.upper()} ({len(fields)} missing fields):\n"
        for field in fields[:10]:  # Limit fields per category
            # Make field name readable
            readable = field.split('.')[-1].replace('_', ' ').title()
            prompt += f"- {readable}\n"
    
    prompt += """

=== SEARCH INSTRUCTIONS ===

1. Use Google Search to find CURRENT, OFFICIAL data for each missing field
2. Focus on the university's official website and reputable sources
3. Return data in JSON format with the field paths as keys

=== IMPORTANT ===
- Only return data you ACTUALLY FIND - do not make up values
- If you cannot find a specific field, skip it (do not include null)
- Use the most recent data available

=== OUTPUT FORMAT ===
Return a JSON object with the filled fields. Example:
{
  "acceptance_rate": 45.2,
  "average_gpa_admitted": 3.8,
  "tuition_in_state": 12500
}
"""
    
    return prompt


def extract_gap_data_from_events(events) -> dict:
    """Extract gap-filled data from agent events."""
    if not events:
        return {}
    
    filled_data = {}
    
    # Look for JSON data in agent responses
    event_list = events if isinstance(events, list) else []
    
    for event in event_list:
        content = event.get("content", {})
        parts = content.get("parts", [])
        
        for part in parts:
            text = part.get("text", "")
            
            # Try to find JSON in the response
            if "{" in text and "}" in text:
                try:
                    # Extract JSON from text
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    json_str = text[start:end]
                    data = json.loads(json_str)
                    if isinstance(data, dict):
                        filled_data.update(data)
                except json.JSONDecodeError:
                    pass
    
    return filled_data


def merge_gap_data(profile: dict, filled_data: dict) -> dict:
    """
    Deep merge filled gap data into the profile.
    Only fills in None/null values, doesn't overwrite existing data.
    """
    import copy
    
    def deep_merge(target, source, filled_paths=None, current_path=""):
        """Recursively merge source into target, only filling None values."""
        if filled_paths is None:
            filled_paths = []
            
        if not isinstance(source, dict):
            return target if target is not None else source
            
        if not isinstance(target, dict):
            target = {}
            
        for key, value in source.items():
            path = f"{current_path}.{key}" if current_path else key
            
            if key not in target or target[key] is None:
                # Target doesn't have this key or it's None - fill it
                target[key] = value
                filled_paths.append(path)
            elif isinstance(value, dict) and isinstance(target.get(key), dict):
                # Both are dicts - recurse
                deep_merge(target[key], value, filled_paths, path)
            elif isinstance(target.get(key), dict) and value is not None:
                # Target is dict but source is value - don't overwrite
                pass
            # If target already has a non-None value, keep it
            
        return target
    
    updated = copy.deepcopy(profile)
    
    # Handle wrapped profile
    target = updated.get("university_profile", updated)
    
    # Track what was actually filled
    filled_paths = []
    
    for field_key, value in filled_data.items():
        if "." in field_key:
            # Handle dot-notation paths like "admissions_data.current_status.testing"
            parts = field_key.split(".")
            obj = target
            for part in parts[:-1]:
                # Handle array notation like colleges[0]
                if "[" in part:
                    array_name = part.split("[")[0]
                    idx = int(part.split("[")[1].rstrip("]"))
                    if array_name not in obj:
                        obj[array_name] = []
                    while len(obj[array_name]) <= idx:
                        obj[array_name].append({})
                    obj = obj[array_name][idx]
                else:
                    if part not in obj or obj[part] is None:
                        obj[part] = {}
                    obj = obj[part] if isinstance(obj.get(part), dict) else {}
            
            final_key = parts[-1]
            if obj.get(final_key) is None:
                obj[final_key] = value
                filled_paths.append(field_key)
        else:
            # Top-level key - deep merge if it's a dict
            if isinstance(value, dict):
                if field_key not in target or target[field_key] is None:
                    target[field_key] = {}
                if isinstance(target.get(field_key), dict):
                    deep_merge(target[field_key], value, filled_paths, field_key)
                else:
                    target[field_key] = value
                    filled_paths.append(field_key)
            else:
                if target.get(field_key) is None:
                    target[field_key] = value
                    filled_paths.append(field_key)
    
    logger.info(f"Deep merge filled {len(filled_paths)} paths: {filled_paths[:10]}...")
    
    return updated



def handle_compare():
    """Compare new profile with existing ES data."""
    data = request.get_json()
    university_id = data.get("university_id")
    new_profile = data.get("new_profile", {})
    
    # Fetch existing from ES
    try:
        response = requests.get(
            f"{KB_UNIVERSITIES_URL}/get",
            params={"university_id": university_id},
            timeout=30
        )
        
        if not response.ok:
            return jsonify({
                "exists_in_es": False,
                "message": "University not found in Elasticsearch"
            })
        
        result = response.json()
        if not result.get("success"):
            return jsonify({
                "exists_in_es": False,
                "message": "University not found in Elasticsearch"
            })
        
        existing = result.get("profile", {})
        
    except Exception as e:
        return jsonify({
            "exists_in_es": False,
            "message": str(e)
        })
    
    # Deep diff
    changes, additions, removals = deep_diff(existing, new_profile)
    
    # Identify critical changes
    critical_keywords = ["acceptance_rate", "us_news_rank", "median_earnings", "graduation_rate"]
    critical_changes = [
        c for c in changes 
        if any(kw in c["field"] for kw in critical_keywords)
    ]
    
    return jsonify({
        "exists_in_es": True,
        "changes": changes[:100],
        "additions": additions[:50],
        "removals": removals[:50],
        "critical_changes": critical_changes,
        "summary": {
            "total_changes": len(changes),
            "total_additions": len(additions),
            "total_removals": len(removals),
            "has_critical_changes": len(critical_changes) > 0
        }
    })


def handle_ingest():
    """Push profile to Elasticsearch."""
    data = request.get_json()
    profile = data.get("profile", {})
    
    # Unwrap university_profile if present (same logic as ingest_universities_es.py)
    if 'university_profile' in profile:
        unwrapped = profile['university_profile']
        # Merge any root-level fields
        for key in profile:
            if key != 'university_profile' and key not in unwrapped:
                unwrapped[key] = profile[key]
        profile = unwrapped
    
    # Ensure _id is set
    university_id = profile.get("_id") or profile.get("university_id")
    if not university_id and "metadata" in profile:
        name = profile["metadata"].get("official_name", "")
        university_id = normalize_university_id(name)
    
    if not university_id:
        return jsonify({"success": False, "error": "Cannot determine university_id"}), 400
    
    profile["_id"] = university_id
    
    logger.info(f"Ingesting {university_id} to Elasticsearch...")
    
    try:
        response = requests.post(
            KB_UNIVERSITIES_URL,
            json={"profile": profile},
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        # Try to parse response even on error
        try:
            result = response.json()
        except:
            result = {"error": response.text}
        
        if response.ok and result.get("success"):
            return jsonify({
                "success": True,
                "university_id": university_id,
                "soft_fit_category": result.get("soft_fit_category"),
                "message": f"Successfully ingested {university_id}"
            })
        else:
            error_msg = result.get("error", f"HTTP {response.status_code}: {response.reason}")
            logger.error(f"Ingest failed: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), response.status_code or 500
            
    except requests.exceptions.Timeout:
        logger.error("Ingest request timed out")
        return jsonify({"success": False, "error": "Request timed out - the profile may be too large"}), 504
    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500



# ============== RESEARCH PROXY ==============

# Agent URL (for server-side calls, no CORS issues)
RESEARCH_AGENT_URL = os.getenv(
    "RESEARCH_AGENT_URL",
    "https://university-profile-collector-pfnwjfp26a-ue.a.run.app"
)


def handle_research():
    """
    Proxy research requests to the university_profile_collector agent.
    This runs server-side to avoid CORS issues from browser.
    """
    data = request.get_json() or {}
    university_name = data.get("university_name", "").strip()
    
    if not university_name:
        return jsonify({"success": False, "error": "university_name is required"}), 400
    
    logger.info(f"Starting research for: {university_name}")
    
    try:
        # Step 1: Create session
        session_url = f"{RESEARCH_AGENT_URL}/apps/university_profile_collector/users/uniminer/sessions"
        session_res = requests.post(
            session_url,
            json={"user_input": "Hello"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        session_res.raise_for_status()
        session_data = session_res.json()
        session_id = session_data.get("id")
        logger.info(f"Session created: {session_id}")
        
        # Step 2: Call /run endpoint (blocking, returns when complete)
        run_url = f"{RESEARCH_AGENT_URL}/run"
        run_res = requests.post(
            run_url,
            json={
                "app_name": "university_profile_collector",
                "user_id": "uniminer",
                "session_id": session_id,
                "new_message": {
                    "parts": [{"text": f"Research {university_name}"}]
                }
            },
            headers={"Content-Type": "application/json"},
            timeout=600  # 10 min timeout for long research
        )
        run_res.raise_for_status()
        events = run_res.json()
        
        logger.info(f"Research completed, got {len(events) if isinstance(events, list) else 'unknown'} events")
        
        # Step 3: Try to find the saved profile
        normalized_name = normalize_university_id(university_name)
        filename = f"{normalized_name}.json"
        
        # Wait a moment for GCS write to complete
        import time
        time.sleep(2)
        
        # Try to fetch from GCS
        gcs_client = get_gcs_client()
        profile = None
        if gcs_client:
            try:
                bucket = gcs_client.bucket(GCS_BUCKET)
                blob = bucket.blob(f"{GCS_PREFIX}{filename}")
                if blob.exists():
                    content = blob.download_as_string()
                    profile = json.loads(content)
                    logger.info(f"Profile fetched from GCS: {filename}")
            except Exception as e:
                logger.warning(f"Could not fetch from GCS: {e}")
        
        return jsonify({
            "success": True,
            "university_name": university_name,
            "filename": filename,
            "profile": profile,
            "events_count": len(events) if isinstance(events, list) else 0
        })
        
    except requests.exceptions.Timeout:
        logger.error("Research timed out after 10 minutes")
        return jsonify({"success": False, "error": "Research timed out. The university may have too much data to process."}), 504
    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ============== MAIN ENTRY POINT ==============

@functions_framework.http
def uniminer(request):
    """Main entry point for the UniMiner cloud function."""
    
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return ("", 204, CORS_HEADERS)
    
    # Parse path
    path = request.path.rstrip("/")
    method = request.method
    
    # Route to handlers
    try:
        if path == "/health" or path == "":
            response = handle_health()
        elif path == "/universities" and method == "GET":
            response = handle_list_universities()
        elif path == "/research-profiles" and method == "GET":
            response = handle_list_research_profiles()
        elif path == "/research-profile" and method == "GET":
            response = handle_get_research_profile()
        elif path == "/validate" and method == "POST":
            response = handle_validate()
        elif path == "/fill-gaps" and method == "POST":
            response = handle_fill_gaps()
        elif path == "/compare" and method == "POST":
            response = handle_compare()
        elif path == "/ingest" and method == "POST":
            response = handle_ingest()
        elif path == "/research" and method == "POST":
            response = handle_research()
        else:
            response = jsonify({"error": f"Unknown endpoint: {path}"}), 404
        
        # Add CORS headers
        if isinstance(response, tuple):
            return (response[0], response[1], CORS_HEADERS)
        else:
            return (response, 200, CORS_HEADERS)
            
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return (jsonify({"error": str(e)}), 500, CORS_HEADERS)
