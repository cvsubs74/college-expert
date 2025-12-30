"""
Tools for University Profile Collector agents.
"""
import os
import json
import logging
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# Get the research directory path
RESEARCH_DIR = os.path.join(os.path.dirname(__file__), 'research')

# GCS configuration
GCS_BUCKET = os.environ.get("RESEARCH_BUCKET", "college-counselling-478115-research")
GCS_PREFIX = "university_profiles/"


def get_gcs_client():
    """Get GCS client if available."""
    try:
        from google.cloud import storage
        return storage.Client()
    except Exception as e:
        logger.warning(f"Could not initialize GCS client: {e}")
        return None


def write_file(
    tool_context: ToolContext,
    filename: str,
    content: str
) -> dict:
    """
    Writes content to a file in the research directory AND uploads to GCS.
    
    Args:
        tool_context: ADK tool context
        filename: Name of the file (e.g., 'stanford_university.json')
        content: The JSON content to write
    
    Returns:
        dict with status, local_path, and gcs_uri
    """
    result = {"status": "success"}
    
    # 1. Save locally
    os.makedirs(RESEARCH_DIR, exist_ok=True)
    target_path = os.path.join(RESEARCH_DIR, filename)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Saved file locally: {target_path}")
    result["local_path"] = target_path
    
    # 2. Upload to GCS
    gcs_client = get_gcs_client()
    if gcs_client:
        try:
            bucket = gcs_client.bucket(GCS_BUCKET)
            blob_name = f"{GCS_PREFIX}{filename}"
            blob = bucket.blob(blob_name)
            blob.upload_from_string(content, content_type="application/json")
            gcs_uri = f"gs://{GCS_BUCKET}/{blob_name}"
            logger.info(f"Uploaded to GCS: {gcs_uri}")
            result["gcs_uri"] = gcs_uri
        except Exception as e:
            logger.warning(f"Failed to upload to GCS: {e}")
            result["gcs_error"] = str(e)
    else:
        result["gcs_error"] = "GCS client not available"
    
    return result


def list_research_profiles() -> dict:
    """
    Lists all university profiles saved in GCS.
    
    Returns:
        dict with profiles list
    """
    gcs_client = get_gcs_client()
    if not gcs_client:
        return {"error": "GCS client not available", "profiles": []}
    
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
        
        return {"profiles": profiles}
    except Exception as e:
        logger.error(f"Failed to list profiles from GCS: {e}")
        return {"error": str(e), "profiles": []}


def get_research_profile(filename: str) -> dict:
    """
    Fetches a university profile from GCS.
    
    Args:
        filename: Name of the file (e.g., 'stanford_university.json')
    
    Returns:
        dict with profile data or error
    """
    gcs_client = get_gcs_client()
    if not gcs_client:
        return {"error": "GCS client not available"}
    
    try:
        bucket = gcs_client.bucket(GCS_BUCKET)
        blob_name = f"{GCS_PREFIX}{filename}"
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            return {"error": f"Profile not found: {filename}"}
        
        content = blob.download_as_string()
        profile = json.loads(content)
        
        return {
            "success": True,
            "filename": filename,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Failed to fetch profile from GCS: {e}")
        return {"error": str(e)}
