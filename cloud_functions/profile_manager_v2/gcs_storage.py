"""
GCS Storage utilities for profile document management.
Handles file upload, download, and deletion operations.
"""

import os
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

# GCS configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "college-counselling-478115-student-profiles")

# Initialize storage client
_storage_client = None


def get_storage_client():
    """Get or create GCS storage client."""
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def get_storage_bucket():
    """Get GCS bucket for student profiles."""
    try:
        client = get_storage_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        return bucket
    except Exception as e:
        logger.error(f"[GCS] Error getting bucket: {e}")
        raise


def get_storage_path(user_id: str, filename: str) -> str:
    """
    Generate Firebase Storage path for user profile.
    
    Args:
        user_id: User's email address
        filename: Original filename
        
    Returns:
        GCS path: user_id/filename
    """
    return f"{user_id}/{filename}"


def upload_file_to_gcs(user_id: str, filename: str, file_content: bytes, content_type: str = None) -> dict:
    """
    Upload file to GCS.
    
    Args:
        user_id: User's email address
        filename: Original filename
        file_content: Binary file content
        content_type: MIME type (optional)
        
    Returns:
        Dict with success status and GCS URL
    """
    try:
        bucket = get_storage_bucket()
        blob_path = get_storage_path(user_id, filename)
        blob = bucket.blob(blob_path)
        
        # Upload with content type (match ES implementation)
        blob.upload_from_string(file_content, content_type=content_type or 'application/octet-stream')
        
        # Get public URL (or signed URL if needed)
        gcs_url = f"gs://{GCS_BUCKET_NAME}/{blob_path}"
        
        logger.info(f"[GCS] Uploaded file: {gcs_url}")
        
        return {
            "success": True,
            "gcs_url": gcs_url,
            "blob_path": blob_path
        }
        
    except Exception as e:
        logger.error(f"[GCS] Upload failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def download_file_from_gcs(user_id: str, filename: str) -> dict:
    """
    Download file from GCS.
    
    Args:
        user_id: User's email address
        filename: Filename to download
        
    Returns:
        Dict with file content and metadata
    """
    try:
        bucket = get_storage_bucket()
        blob_path = get_storage_path(user_id, filename)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            return {
                "success": False,
                "error": "File not found"
            }
        
        # Download file content
        file_content = blob.download_as_bytes()
        
        logger.info(f"[GCS] Downloaded file: {blob_path}")
        
        return {
            "success": True,
            "file_content": file_content,
            "content_type": blob.content_type,
            "size": blob.size
        }
        
    except Exception as e:
        logger.error(f"[GCS] Download failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def delete_file_from_gcs(user_id: str, filename: str) -> dict:
    """
    Delete file from GCS.
    
    Args:
        user_id: User's email address
        filename: Filename to delete
        
    Returns:
        Dict with success status
    """
    try:
        bucket = get_storage_bucket()
        blob_path = get_storage_path(user_id, filename)
        blob = bucket.blob(blob_path)
        
        if blob.exists():
            blob.delete()
            logger.info(f"[GCS] Deleted file: {blob_path}")
            return {
                "success": True,
                "message": "File deleted successfully"
            }
        else:
            logger.warning(f"[GCS] File not found: {blob_path}")
            return {
                "success": True,  # Don't fail if file doesn't exist
                "message": "File not found (may have been already deleted)"
            }
        
    except Exception as e:
        logger.error(f"[GCS] Delete failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def list_user_files(user_id: str) -> list:
    """
    List all files for a user in GCS.
    
    Args:
        user_id: User's email address
        
    Returns:
        List of file metadata dicts
    """
    try:
        bucket = get_storage_bucket()
        prefix = f"{user_id}/"
        
        blobs = bucket.list_blobs(prefix=prefix)
        
        files = []
        for blob in blobs:
            files.append({
                "filename": blob.name.replace(prefix, ""),
                "size": blob.size,
                "content_type": blob.content_type,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "gcs_path": blob.name
            })
        
        logger.info(f"[GCS] Listed {len(files)} files for {user_id}")
        return files
        
    except Exception as e:
        logger.error(f"[GCS] List files failed: {e}")
        return []
