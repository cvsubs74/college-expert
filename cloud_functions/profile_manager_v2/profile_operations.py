"""
Profile management operations.
Handles profile upload, merging, retrieval, and cleanup.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Optional

from firestore_db import get_db
from file_processing import extract_text_from_file_content
from profile_extraction import extract_profile_content, evaluate_profile_changes
from gcs_storage import upload_file_to_gcs, delete_file_from_gcs

logger = logging.getLogger(__name__)


def process_and_index_profile(user_id: str, filename: str, file_content: bytes, file_metadata: dict = None) -> dict:
    """
    Process uploaded profile document and save to Firestore.
    
    Workflow:
    1. Upload file to GCS
    2. Extract text from PDF/DOCX
    3. Use Gemini to convert to markdown and extract structured data
    4. Merge with existing profile in Firestore
    5. Track field sources
    
    Args:
        user_id: User's email address
        filename: Original filename
        file_content: Binary file content
        file_metadata: Optional metadata (content_type, etc.)
        
    Returns:
        Dict with success status and profile data
    """
    try:
        # Step 1: Upload to GCS
        content_type = file_metadata.get('content_type') if file_metadata else None
        gcs_result = upload_file_to_gcs(user_id, filename, file_content, content_type)
        
        if not gcs_result['success']:
            return gcs_result
        
        # Step 2: Extract text
        logger.info(f"[PROFILE] Extracting text from {filename}")
        raw_text = extract_text_from_file_content(file_content, filename)
        
        if not raw_text:
            logger.warning(f"[PROFILE] No text extracted from {filename}")
            raw_text = "Could not extract text from document."
        
        # Step 3: Use Gemini to process
        logger.info(f"[PROFILE] Processing with Gemini: {filename}")
        gemini_result = extract_profile_content(raw_text, filename)
        
        content_markdown = gemini_result.get('content_markdown', '')
        structured_profile = gemini_result.get('structured_profile', {})
        
        # Step 4: Merge with existing profile
        result = index_student_profile(
            user_id=user_id,
            filename=filename,
            content_markdown=content_markdown,
            metadata={
                'gcs_url': gcs_result['gcs_url'],
                'upload_date': datetime.utcnow().isoformat(),
                'file_size': len(file_content),
                'content_type': content_type
            },
            profile_data=structured_profile
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[PROFILE] Processing failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def index_student_profile(user_id: str, filename: str, content_markdown: str, 
                         metadata: dict = None, profile_data: dict = None) -> dict:
    """
    Index student profile in Firestore with FLATTENED schema.
    All profile fields stored at top level for direct access.
    MERGES data from multiple uploads instead of replacing.
    
    Args:
        user_id: User's email
        filename: Original filename
        content_markdown: Clean markdown content (from Gemini)
        metadata: Optional metadata (filename, upload time, gcs_url)
        profile_data: Flattened profile JSON (from Gemini)
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        
        # Get existing profile to merge with
        existing_profile = db.get_profile(user_id) or {}
        
        # Helper function to merge values (prefer non-null new values)
        def merge_scalar(old_val, new_val):
            return new_val if new_val is not None else old_val
        
        # Helper function to merge arrays (combine and deduplicate)
        def merge_arrays(old_arr, new_arr, key_field='name'):
            if not old_arr:
                return new_arr or []
            if not new_arr:
                return old_arr or []
            
            # Combine arrays, deduplicating by key field
            merged = list(old_arr)
            existing_keys = set()
            for item in old_arr:
                if isinstance(item, dict):
                    existing_keys.add(item.get(key_field, '').lower())
                else:
                    existing_keys.add(str(item).lower())
            
            for item in new_arr:
                if isinstance(item, dict):
                    key = item.get(key_field, '').lower()
                else:
                    key = str(item).lower()
                if key not in existing_keys:
                    merged.append(item)
            
            return merged
        
        # Append to raw content (track all uploaded files)
        existing_content = existing_profile.get('raw_content', '')
        if content_markdown:
            if existing_content:
                raw_content = f"{existing_content}\n\n---\n\n{content_markdown}"
            else:
                raw_content = content_markdown
        else:
            raw_content = existing_content
        
        # Track all uploaded filenames
        uploaded_files = existing_profile.get('uploaded_files', [])
        if filename and filename not in uploaded_files:
            uploaded_files.append(filename)
        
        # Build document
        document = {
            'user_id': user_id,
            'indexed_at': datetime.utcnow().isoformat(),
            'raw_content': raw_content,
            'original_filename': filename,
            'uploaded_files': uploaded_files,
        }
        
        # Add metadata
        if metadata:
            document.update(metadata)
        
        # Merge flattened profile data
        if profile_data:
            # Personal info - merge scalars
            document['name'] = merge_scalar(existing_profile.get('name'), profile_data.get('name'))
            document['school'] = merge_scalar(existing_profile.get('school'), profile_data.get('school'))
            document['location'] = merge_scalar(existing_profile.get('location'), profile_data.get('location'))
            document['grade'] = merge_scalar(existing_profile.get('grade'), profile_data.get('grade'))
            document['graduation_year'] = merge_scalar(existing_profile.get('graduation_year'), profile_data.get('graduation_year'))
            document['intended_major'] = merge_scalar(existing_profile.get('intended_major'), profile_data.get('intended_major'))
            
            # Academics - merge scalars
            document['gpa_weighted'] = merge_scalar(existing_profile.get('gpa_weighted'), profile_data.get('gpa_weighted'))
            document['gpa_unweighted'] = merge_scalar(existing_profile.get('gpa_unweighted'), profile_data.get('gpa_unweighted'))
            document['gpa_uc'] = merge_scalar(existing_profile.get('gpa_uc'), profile_data.get('gpa_uc'))
            document['class_rank'] = merge_scalar(existing_profile.get('class_rank'), profile_data.get('class_rank'))
            
            # Test scores
            document['sat_total'] = merge_scalar(existing_profile.get('sat_total'), profile_data.get('sat_total'))
            document['sat_math'] = merge_scalar(existing_profile.get('sat_math'), profile_data.get('sat_math'))
            document['sat_reading'] = merge_scalar(existing_profile.get('sat_reading'), profile_data.get('sat_reading'))
            document['act_composite'] = merge_scalar(existing_profile.get('act_composite'), profile_data.get('act_composite'))
            
            # Arrays - merge and deduplicate
            document['courses'] = merge_arrays(
                existing_profile.get('courses', []),
                profile_data.get('courses', []),
                'name'
            )
            document['ap_exams'] = merge_arrays(
                existing_profile.get('ap_exams', []),
                profile_data.get('ap_exams', []),
                'subject'
            )
            document['extracurriculars'] = merge_arrays(
                existing_profile.get('extracurriculars', []),
                profile_data.get('extracurriculars', []),
                'name'
            )
            document['leadership_roles'] = merge_arrays(
                existing_profile.get('leadership_roles', []),
                profile_data.get('leadership_roles', []),
                'title'
            )
            document['awards'] = merge_arrays(
                existing_profile.get('awards', []),
                profile_data.get('awards', []),
                'name'
            )
            document['work_experience'] = merge_arrays(
                existing_profile.get('work_experience', []),
                profile_data.get('work_experience', []),
                'title'
            )
            
            # Track field sources
            field_sources = existing_profile.get('field_sources', {})
            for field, value in profile_data.items():
                if value is not None:
                    if field not in field_sources:
                        field_sources[field] = []
                    if filename not in field_sources[field]:
                        field_sources[field].append(filename)
            document['field_sources'] = field_sources
        
        # Save to Firestore
        success = db.save_profile(user_id, document, merge=True)
        
        # Also save file metadata separately
        if metadata:
            db.save_file_metadata(user_id, filename, {
                'filename': filename,
                'upload_date': metadata.get('upload_date'),
                'file_size': metadata.get('file_size'),
                'content_type': metadata.get('content_type'),
                'gcs_url': metadata.get('gcs_url'),
                'processing_status': 'completed'
            })
        
        if success:
            logger.info(f"[PROFILE] Successfully indexed profile for {user_id}")
            return {
                "success": True,
                "message": "Profile indexed successfully",
                "uploaded_files": uploaded_files
            }
        else:
            return {
                "success": False,
                "error": "Failed to save profile to Firestore"
            }
        
    except Exception as e:
        logger.error(f"[PROFILE] Index failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def cleanup_profile_on_document_delete(user_id: str, filename: str) -> dict:
    """
    Clean up profile when a document is deleted.
    Removes fields that were only sourced from the deleted file.
    
    Args:
        user_id: User's email
        filename: Filename being deleted
        
    Returns:
        Dict with success status
    """
    try:
        db = get_db()
        profile = db.get_profile(user_id)
        
        if not profile:
            return {"success": True, "message": "No profile to clean up"}
        
        # Get field sources
        field_sources = profile.get('field_sources', {})
        
        # Fields to remove (only sourced from this file)
        fields_to_remove = []
        for field, sources in field_sources.items():
            if sources == [filename]:  # Only this file
                fields_to_remove.append(field)
            elif filename in sources:  # Multiple sources, just remove this one
                field_sources[field] = [s for s in sources if s != filename]
        
        # Remove fields
        for field in fields_to_remove:
            if field in profile:
                profile[field] = None  # Firestore will handle deletion
            if field in field_sources:
                del field_sources[field]
        
        # Update uploaded_files list
        uploaded_files = profile.get('uploaded_files', [])
        if filename in uploaded_files:
            uploaded_files.remove(filename)
        
        profile['field_sources'] = field_sources
        profile['uploaded_files'] = uploaded_files
        
        # Save updated profile
        db.save_profile(user_id, profile, merge=True)
        
        # Delete file metadata
        db.delete_file_metadata(user_id, filename)
        
        logger.info(f"[PROFILE] Cleaned up profile after deleting {filename}")
        
        return {
            "success": True,
            "fields_removed": fields_to_remove,
            "message": f"Removed {len(fields_to_remove)} fields"
        }
        
    except Exception as e:
        logger.error(f"[PROFILE] Cleanup failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_student_profile(user_id: str) -> Optional[Dict]:
    """
    Get student profile from Firestore.
    
    Args:
        user_id: User's email
        
    Returns:
        Profile dict or None
    """
    try:
        db = get_db()
        return db.get_profile(user_id)
    except Exception as e:
        logger.error(f"[PROFILE] Error getting profile: {e}")
        return None
