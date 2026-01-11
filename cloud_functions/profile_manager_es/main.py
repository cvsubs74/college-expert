"""
Google Cloud Function for managing student profiles in Elasticsearch.
Handles upload, list, and delete operations for student profiles.
"""

import os
import re
import tempfile
import time
import requests
import functions_framework
from flask import jsonify, request
from google.cloud import storage
from elasticsearch import Elasticsearch, NotFoundError
import hashlib
from datetime import datetime
import json
import logging
import io
import fitz  # PyMuPDF - better PDF extraction than PyPDF2
from docx import Document
from google import genai
from google.genai import types
from PIL import Image

from essay_copilot import (
    generate_essay_starters,
    get_copilot_suggestion,
    get_draft_feedback,
    save_essay_draft,
    get_essay_drafts,
    essay_chat,
    get_starter_context
)

from profile_chat import profile_chat


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ... (rest of imports and config)

def extract_text_from_file_content(file_content, filename):
    """Extract text from file content based on extension.
    Uses PyMuPDF (fitz) for PDFs which produces clean, properly formatted text.
    """
    try:
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_ext == 'pdf':
            try:
                # Use PyMuPDF (fitz) for better text extraction
                pdf_doc = fitz.open(stream=file_content, filetype="pdf")
                text_parts = []
                
                for page_num, page in enumerate(pdf_doc):
                    # Extract text with proper layout preservation
                    page_text = page.get_text("text")  # "text" mode preserves paragraphs
                    if page_text.strip():
                        text_parts.append(page_text)
                
                pdf_doc.close()
                
                # Join pages with double newlines for clear separation
                text = "\n\n".join(text_parts)
                
                # Clean up any remaining word-per-line formatting issues
                text = clean_extracted_text(text)
                
                logger.info(f"[PDF EXTRACTION] Extracted {len(text)} chars from {filename}")
                return text
                
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return None
                
        elif file_ext == 'docx':
            try:
                docx_file = io.BytesIO(file_content)
                doc = Document(docx_file)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return clean_extracted_text(text)
            except Exception as e:
                logger.error(f"DOCX extraction failed: {e}")
                return None
                
        elif file_ext in ['txt', 'text', 'md', 'csv']:
            return file_content.decode('utf-8', errors='ignore')
            
        else:
            # Try plain text as fallback
            return file_content.decode('utf-8', errors='ignore')
            
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return None


def clean_extracted_text(text):
    """
    Clean up PDF extraction artifacts like word-per-line formatting.
    Joins fragmented words while preserving intentional paragraph breaks.
    """
    if not text:
        return text
    
    lines = text.split('\n')
    cleaned = []
    buffer = []
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            # Empty line = paragraph break
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append('')
        elif stripped.startswith('●') or stripped.startswith('•') or stripped.startswith('-') or stripped.startswith('*'):
            # Bullet point - save buffer and start new line with bullet
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append(stripped)
        elif len(stripped) == 1 or (len(stripped) <= 3 and stripped.isalpha()):
            # Very short word fragment - likely poorly extracted, add to buffer
            buffer.append(stripped)
        elif stripped.endswith(':') or any(stripped.lower().startswith(h) for h in ['grade', 'gpa', 'sat', 'act', 'school', 'major', 'awards', 'activities']):
            # Section header - save buffer and start new line
            if buffer:
                cleaned.append(' '.join(buffer))
                buffer = []
            cleaned.append(stripped)
        else:
            buffer.append(stripped)
    
    # Don't forget remaining buffer
    if buffer:
        cleaned.append(' '.join(buffer))
    
    # Join and clean up excessive spacing
    result = '\n'.join(cleaned)
    result = result.replace('\n\n\n', '\n\n')  # Max 2 newlines
    
    return result.strip()








def extract_profile_content_with_gemini(file_content, filename):
    """
    Extract and format student profile document using Gemini.
    Converts PDF/DOCX text to clean, well-formatted Markdown AND structured JSON.
    """
    try:
        # Extract raw text content from PDF/DOCX
        raw_text = extract_text_from_file_content(file_content, filename)
        
        if not raw_text:
            raw_text = "Could not extract text from document."
            logger.warning(f"[EXTRACTION] No text extracted from {filename}")
        
        # Use Gemini to convert raw text to clean markdown
        content_markdown = convert_to_markdown_with_gemini(raw_text, filename)
        
        # Also extract structured profile for visual display (ProfileViewCard)
        structured_profile = extract_structured_profile_with_gemini(raw_text)
        
        return {
            "raw_content": raw_text,  # Original extracted text (for search)
            "content_markdown": content_markdown,  # Clean markdown (for display)
            "structured_profile": structured_profile,  # Structured JSON (for ProfileViewCard)
            "filename": filename
        }
            
    except Exception as e:
        logger.error(f"[EXTRACTION ERROR] Failed to extract content: {e}")
        return {
            "raw_content": raw_text if 'raw_text' in dir() else "Error processing file",
            "content_markdown": f"# Student Profile\n\nError processing file: {str(e)}",
            "structured_profile": None,
            "error": str(e)
        }


def convert_to_markdown_with_gemini(raw_text: str, filename: str) -> str:
    """
    Use Gemini to convert raw profile text to clean, well-formatted Markdown.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("[GEMINI] No API key, returning raw text as markdown")
            return f"# Student Profile\n\n{raw_text}"
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Convert this student profile text into clean, well-formatted Markdown.

RAW TEXT:
{raw_text[:15000]}

FORMATTING REQUIREMENTS:
1. Create a clear heading structure with # for main title, ## for sections, ### for subsections
2. Use these sections (in order):
   - # Student Profile: [Name]
   - ## Personal Information (school, location, ethnicity if mentioned)
   - ## Intended Major
   - ## Academic Summary (GPA: weighted, unweighted, UC if available)
   - ## AP Exam Scores (as a bullet list with scores)
   - ## Course History (organize by grade level 9-12, list courses with grades)
   - ## Extracurricular Activities (name, years, description, achievements)
   - ## Awards & Honors
   - ## Work Experience
   - ## Special Programs & Certifications
   - ## Leadership Roles
3. Use bullet points (-) for lists
4. Use **bold** for important values like GPA, test scores
5. Keep descriptions concise but complete
6. Use emojis sparingly for section headers (📊 for academics, 🏆 for activities, etc.)
7. Preserve ALL information from the original document

Return ONLY the markdown content, no explanations.
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        markdown_content = response.text.strip()
        
        # Remove any markdown code block wrapper if present
        if markdown_content.startswith('```markdown'):
            markdown_content = markdown_content[len('```markdown'):].strip()
        if markdown_content.startswith('```'):
            markdown_content = markdown_content[3:].strip()
        if markdown_content.endswith('```'):
            markdown_content = markdown_content[:-3].strip()
        
        logger.info(f"[GEMINI] Converted profile to markdown ({len(markdown_content)} chars)")
        return markdown_content
        
    except Exception as e:
        logger.error(f"[GEMINI] Markdown conversion error: {e}")
        # Fallback: return raw text with basic header
        return f"# Student Profile\n\n{raw_text}"


def extract_structured_profile_with_gemini(raw_text: str) -> dict:
    """
    Extract complete structured profile from raw text using Gemini.
    Returns FLATTENED JSON with top-level fields for ES indexing.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("[GEMINI] No API key, returning empty structured profile")
            return None
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Extract ALL information from this student profile into structured JSON.
Be thorough - extract EVERY piece of information present. Use null for missing fields.

STUDENT PROFILE TEXT:
{raw_text[:20000]}

REQUIRED JSON SCHEMA (FLAT structure - all fields at top level):
{{
  "name": "student's full name or null",
  "school": "high school name or null",
  "location": "city, state or null",
  "grade": integer 9-12 or null,
  "graduation_year": integer or null,
  "intended_major": "primary intended major or null",
  
  "gpa_weighted": float or null,
  "gpa_unweighted": float or null,
  "gpa_uc": float or null,
  "class_rank": "e.g. '15/400' or null",
  
  "sat_total": integer or null,
  "sat_math": integer or null,
  "sat_reading": integer or null,
  "act_composite": integer or null,
  
  "ap_exams": [
    {{"subject": "AP Subject Name", "score": integer 1-5}}
  ],
  "courses": [
    {{
      "name": "course name",
      "type": "AP" or "Honors" or "IB" or "Regular",
      "grade_level": integer 9-12,
      "semester1_grade": "A" or "B+" etc or null,
      "semester2_grade": "A" or "B+" etc or null
    }}
  ],
  "extracurriculars": [
    {{
      "name": "activity name",
      "role": "position/role or null",
      "description": "brief description or null",
      "grades": "e.g. '9-12' or '11-12'",
      "hours_per_week": integer or null,
      "achievements": ["achievement 1", "achievement 2"]
    }}
  ],
  "leadership_roles": ["role 1", "role 2"],
  "special_programs": [
    {{"name": "program name", "description": "description or null", "grade": integer or null}}
  ],
  "awards": [
    {{"name": "award name", "grade": integer or null, "description": "description or null"}}
  ],
  "work_experience": [
    {{
      "employer": "company/organization name",
      "role": "job title",
      "grades": "e.g. '10-11'",
      "hours_per_week": integer or null,
      "description": "job description or null"
    }}
  ]
}}

EXTRACTION RULES:
1. Extract EVERY activity, course, award mentioned - don't summarize
2. For AP exams, include ALL subjects and scores found
3. For courses, categorize type based on name (AP Physics = "AP", Honors English = "Honors")
4. Parse grades like "A/A-" as semester1_grade: "A", semester2_grade: "A-"
5. For activities without hours, estimate based on involvement level or use null
6. Include ALL leadership positions in BOTH extracurriculars and leadership_roles
7. Return ONLY valid JSON, no markdown formatting or explanation

TRANSCRIPT-SPECIFIC RULES (IMPORTANT):
8. Look for "Cumulative" GPA - use cumulative weighted GPA for gpa_weighted, cumulative unweighted for gpa_unweighted
9. Extract EVERY course from ALL grade levels (9, 10, 11, 12) - parse markdown tables if present
10. For class rank, look for patterns like "1 of 487" or "15/400" - format as "1/487"
11. Extract graduation year from "Expected Graduation" or class year
12. Look for AP exam SCORES (1-5) separate from AP courses - scores are typically listed with year or after course tables

Return ONLY the JSON object."""

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            start_idx = 1 if lines[0].startswith('```') else 0
            end_idx = len(lines) - 1 if lines[-1] == '```' else len(lines)
            response_text = '\n'.join(lines[start_idx:end_idx])
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        profile = json.loads(response_text)
        
        # Ensure arrays exist (flattened structure)
        array_keys = ['courses', 'extracurriculars', 'leadership_roles', 'special_programs', 'awards', 'work_experience', 'ap_exams']
        for key in array_keys:
            if key not in profile or profile[key] is None:
                profile[key] = []
        
        # Enhanced logging for debugging
        logger.info(f"[GEMINI] Extracted flattened profile:")
        logger.info(f"  - Name: {profile.get('name')}, School: {profile.get('school')}")
        logger.info(f"  - GPA weighted: {profile.get('gpa_weighted')}, unweighted: {profile.get('gpa_unweighted')}")
        logger.info(f"  - SAT: {profile.get('sat_total')}, ACT: {profile.get('act_composite')}")
        logger.info(f"  - Class rank: {profile.get('class_rank')}, Grad year: {profile.get('graduation_year')}")
        logger.info(f"  - Courses: {len(profile.get('courses', []))}, AP exams: {len(profile.get('ap_exams', []))}")
        logger.info(f"  - Activities: {len(profile.get('extracurriculars', []))}, Awards: {len(profile.get('awards', []))}")
        return profile
        
    except json.JSONDecodeError as e:
        logger.error(f"[GEMINI] JSON parse error in structured extraction: {e}")
        logger.error(f"[GEMINI] Response was: {response_text[:500]}...")
        return None
    except Exception as e:
        logger.error(f"[GEMINI] Structured extraction error: {e}")
        return None



def evaluate_profile_change_impact(old_content: str, new_content: str) -> dict:
    """
    Use LLM to determine if profile changes would affect college fit calculations.
    Returns: {"should_recompute": bool, "reason": str, "changes_detected": []}
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""You are a college admissions expert. Compare these two student profile versions and determine if the changes would affect college fit/match calculations.

CHANGES THAT WOULD AFFECT FIT (should_recompute = true):
- GPA (weighted/unweighted) changes
- SAT/ACT score changes or additions
- Class rank changes
- Intended major or field of study changes
- State residency changes
- High school type changes

CHANGES THAT WOULD NOT AFFECT FIT (should_recompute = false):
- Spelling/grammar corrections
- Formatting changes
- Activity or extracurricular descriptions
- Essay content updates
- Leadership role descriptions
- Award descriptions (unless academic GPA-related)

OLD PROFILE (first 2000 chars):
{old_content[:2000]}

NEW PROFILE (first 2000 chars):
{new_content[:2000]}

Respond ONLY with valid JSON (no markdown):
{{"should_recompute": true or false, "reason": "one sentence explanation", "changes_detected": ["list of specific changes found"]}}
"""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        logger.info(f"[PROFILE_CHANGE] Evaluation result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[PROFILE_CHANGE] LLM evaluation error: {e}")
        # Default to not recomputing on error (safe fallback)
        return {
            "should_recompute": False,
            "reason": f"Evaluation failed: {str(e)}",
            "changes_detected": []
        }





# Get configuration from environment variables

ES_CLOUD_ID = os.getenv("ES_CLOUD_ID")
ES_API_KEY = os.getenv("ES_API_KEY")
ES_INDEX_NAME = os.getenv("ES_INDEX_NAME", "student_profiles")  # Main index for student profiles
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "college-counselling-478115-student-profiles")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Separate indices for college list and fit analysis
ES_LIST_ITEMS_INDEX = os.getenv("ES_LIST_ITEMS_INDEX", "student_college_list")
ES_FITS_INDEX = os.getenv("ES_FITS_INDEX", "student_college_fits")
ES_CREDITS_INDEX = os.getenv("ES_CREDITS_INDEX", "user_credits")
ES_CHAT_CONVERSATIONS_INDEX = os.getenv("ES_CHAT_CONVERSATIONS_INDEX", "fit_chat_conversations")

# Note: genai.Client is created per-request in each function



def normalize_university_id(university_id):
    """
    Normalize university ID to ensure consistent matching between indices.
    Handles variations like:
    - 'the_ohio_state_university' -> 'ohio_state_university'
    - 'rutgers_university-new_brunswick' -> 'rutgers_university_new_brunswick'
    - 'university_of_minnesota_twin_cities_slug' -> 'university_of_minnesota_twin_cities'
    """
    if not university_id:
        return ''
    
    normalized = university_id.lower().strip()
    
    # Remove leading 'the_'
    if normalized.startswith('the_'):
        normalized = normalized[4:]
    
    # Remove trailing '_slug'
    if normalized.endswith('_slug'):
        normalized = normalized[:-5]
    
    # Replace hyphens with underscores
    normalized = normalized.replace('-', '_')
    
    # Replace spaces with underscores (for IDs like 'auburn university')
    normalized = normalized.replace(' ', '_')
    
    # Remove any double underscores
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    
    return normalized


# Initialize GCS client
storage_client = storage.Client()

def get_elasticsearch_client():
    """Create and return Elasticsearch client."""
    try:
        client = Elasticsearch(
            cloud_id=ES_CLOUD_ID,
            api_key=ES_API_KEY,
            request_timeout=30
        )
        
        # Test connection
        client.info()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        raise

def get_storage_bucket():
    """Get or create GCS bucket."""
    try:
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        if not bucket.exists():
            bucket = storage_client.create_bucket(GCS_BUCKET_NAME, location="us-east1")
            logger.info(f"[STORAGE] Created bucket: {GCS_BUCKET_NAME}")
        return bucket
    except Exception as e:
        logger.error(f"[STORAGE ERROR] {str(e)}")
        raise

def get_storage_path(user_id, filename):
    """Generate Firebase Storage path for user profile."""
    # Sanitize email for path
    sanitized_id = user_id.replace('@', '_').replace('.', '_').lower()
    return f"profiles/{sanitized_id}/{filename}"


# ============== CREDIT MANAGEMENT ==============

FREE_TIER_CREDITS = 3
MONTHLY_TIER_CREDITS = 20
SEASON_PASS_CREDITS = 150  # Best Value
CREDIT_PACK_SIZE = 10
CREDIT_PACK_PRICE = 9.00  # $9 for 10 credits

def get_user_credits(user_id: str) -> dict:
    """Get user's credit balance and tier info.
    
    Returns:
        {
            "user_id": "...",
            "tier": "free" | "pro",
            "credits_total": 50,
            "credits_used": 12,
            "credits_remaining": 38,
            "subscription_active": true/false,
            "subscription_expires": "..."
        }
    """
    try:
        client = get_elasticsearch_client()
        import hashlib
        doc_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        try:
            result = client.get(index=ES_CREDITS_INDEX, id=doc_id)
            return result['_source']
        except Exception:
            # No credits record - initialize as free tier
            return initialize_user_credits(user_id, "free")
    except Exception as e:
        logger.error(f"[CREDITS] Error getting credits for {user_id}: {e}")
        return {
            "user_id": user_id,
            "tier": "free",
            "credits_total": FREE_TIER_CREDITS,
            "credits_used": 0,
            "credits_remaining": FREE_TIER_CREDITS,
            "subscription_active": False
        }

def initialize_user_credits(user_id: str, tier: str = "free") -> dict:
    """Initialize credit record for new user."""
    try:
        client = get_elasticsearch_client()
        import hashlib
        doc_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        if tier == "free":
            credits = FREE_TIER_CREDITS
        elif tier == "season_pass":
            credits = SEASON_PASS_CREDITS
        else:
             credits = MONTHLY_TIER_CREDITS
        
        doc = {
            "user_id": user_id,
            "tier": tier,
            "credits_total": credits,
            "credits_used": 0,
            "credits_remaining": credits,
            "subscription_active": tier == "pro",
            "subscription_expires": None,
            "purchase_history": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        client.index(index=ES_CREDITS_INDEX, id=doc_id, body=doc)
        logger.info(f"[CREDITS] Initialized {tier} tier for {user_id} with {credits} credits")
        return doc
    except Exception as e:
        logger.error(f"[CREDITS] Error initializing credits: {e}")
        raise

def check_credits_available(user_id: str, credits_needed: int = 1) -> dict:
    """Check if user has enough credits.
    
    Returns:
        {
            "has_credits": true/false,
            "credits_remaining": 38,
            "credits_needed": 1
        }
    """
    credits = get_user_credits(user_id)
    remaining = credits.get("credits_remaining", 0)
    
    return {
        "has_credits": remaining >= credits_needed,
        "credits_remaining": remaining,
        "credits_needed": credits_needed,
        "tier": credits.get("tier", "free")
    }

def deduct_credit(user_id: str, credit_count: int = 1, reason: str = "fit_analysis") -> dict:
    """Deduct credit(s) from user's balance.
    
    Returns:
        {
            "success": true/false,
            "credits_remaining": 37,
            "credits_deducted": 1,
            "reason": "fit_analysis"
        }
    """
    try:
        client = get_elasticsearch_client()
        import hashlib
        doc_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        # Get current balance
        credits = get_user_credits(user_id)
        remaining = credits.get("credits_remaining", 0)
        
        if remaining < credit_count:
            return {
                "success": False,
                "error": "insufficient_credits",
                "credits_remaining": remaining,
                "credits_needed": credit_count
            }
        
        # Update balance
        new_remaining = remaining - credit_count
        new_used = credits.get("credits_used", 0) + credit_count
        
        client.update(
            index=ES_CREDITS_INDEX,
            id=doc_id,
            body={
                "doc": {
                    "credits_used": new_used,
                    "credits_remaining": new_remaining,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"[CREDITS] Deducted {credit_count} from {user_id}. Remaining: {new_remaining}")
        return {
            "success": True,
            "credits_remaining": new_remaining,
            "credits_deducted": credit_count,
            "reason": reason
        }
    except Exception as e:
        logger.error(f"[CREDITS] Error deducting credit: {e}")
        return {"success": False, "error": str(e)}

def add_credits(user_id: str, credit_count: int, source: str = "credit_pack") -> dict:
    """Add credits to user's balance (from pack purchase or subscription).
    
    Returns:
        {
            "success": true/false,
            "credits_added": 50,
            "credits_remaining": 88,
            "source": "credit_pack"
        }
    """
    try:
        client = get_elasticsearch_client()
        import hashlib
        doc_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        # Get or create credit record
        credits = get_user_credits(user_id)
        
        new_total = credits.get("credits_total", 0) + credit_count
        new_remaining = credits.get("credits_remaining", 0) + credit_count
        
        # Add to purchase history
        history = credits.get("purchase_history", [])
        history.append({
            "date": datetime.utcnow().isoformat(),
            "source": source,
            "credits": credit_count
        })
        
        client.update(
            index=ES_CREDITS_INDEX,
            id=doc_id,
            body={
                "doc": {
                    "credits_total": new_total,
                    "credits_remaining": new_remaining,
                    "purchase_history": history,
                    "updated_at": datetime.utcnow().isoformat()
                }
            },
            upsert={
                "user_id": user_id,
                "tier": "free",
                "credits_total": credit_count,
                "credits_used": 0,
                "credits_remaining": credit_count,
                "subscription_active": False,
                "purchase_history": history,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"[CREDITS] Added {credit_count} to {user_id}. New balance: {new_remaining}")
        return {
            "success": True,
            "credits_added": credit_count,
            "credits_remaining": new_remaining,
            "source": source
        }
    except Exception as e:
        logger.error(f"[CREDITS] Error adding credits: {e}")
        return {"success": False, "error": str(e)}

def upgrade_subscription(user_id: str, subscription_expires: str = None, plan_type: str = 'monthly') -> dict:
    """Upgrade user to Monthly or Season Pass tier."""
    try:
        client = get_elasticsearch_client()
        import hashlib
        doc_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        # Determine credits based on plan
        credits_to_add = SEASON_PASS_CREDITS if plan_type == 'season_pass' else MONTHLY_TIER_CREDITS
        source = "season_pass" if plan_type == 'season_pass' else "monthly_subscription"
        tier_name = "season_pass" if plan_type == 'season_pass' else "monthly"
        
        # Get existing credits (don't lose them)
        existing = get_user_credits(user_id)
        existing_remaining = existing.get("credits_remaining", 0)
        
        # Add credits to existing balance
        new_remaining = existing_remaining + credits_to_add
        new_total = existing.get("credits_total", 0) + credits_to_add
        
        history = existing.get("purchase_history", [])
        history.append({
            "date": datetime.utcnow().isoformat(),
            "source": source,
            "credits": credits_to_add
        })
        
        client.update(
            index=ES_CREDITS_INDEX,
            id=doc_id,
            body={
                "doc": {
                    "tier": tier_name,
                    "credits_total": new_total,
                    "credits_remaining": new_remaining,
                    "subscription_active": True,
                    "subscription_expires": subscription_expires,
                    "purchase_history": history,
                    "updated_at": datetime.utcnow().isoformat()
                }
            },
            upsert={
                "user_id": user_id,
                "tier": tier_name,
                "credits_total": credits_to_add,
                "credits_used": 0,
                "credits_remaining": credits_to_add,
                "subscription_active": True,
                "subscription_expires": subscription_expires,
                "purchase_history": history,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"[CREDITS] Upgraded {user_id} to {tier_name}. Credits: {new_remaining}")
        return {
            "success": True,
            "tier": tier_name,
            "credits_remaining": new_remaining
        }
    except Exception as e:
        logger.error(f"[CREDITS] Error upgrading subscription: {e}")
        return {"success": False, "error": str(e)}

# ============== END CREDIT MANAGEMENT ==============

def index_student_profile(user_id, filename, content_markdown, metadata=None, profile_data=None):
    """Index student profile in Elasticsearch with FLATTENED schema.
    All profile fields stored at top level for direct access.
    MERGES data from multiple uploads instead of replacing.
    
    Args:
        user_id: User's email
        filename: Original filename
        content_markdown: Clean markdown content (from Gemini)
        metadata: Optional minimal metadata (filename, upload time, gcs_url later)
        profile_data: Flattened profile JSON (from extract_structured_profile_with_gemini)
    """
    try:
        client = get_elasticsearch_client()
        
        # Use user_id as document ID (one profile per user)
        import hashlib
        document_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        # Fetch existing profile to merge with
        existing_profile = {}
        try:
            existing_doc = client.get(index=ES_INDEX_NAME, id=document_id)
            existing_profile = existing_doc.get('_source', {})
            logger.info(f"[ES] Found existing profile for {user_id}, will merge data")
        except Exception as e:
            logger.info(f"[ES] No existing profile for {user_id}, creating new")
        
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
        raw_content = existing_content
        if content_markdown:
            if existing_content:
                raw_content = f"{existing_content}\n\n---\n\n{content_markdown}"
            else:
                raw_content = content_markdown
        
        # Track all uploaded filenames
        existing_filenames = existing_profile.get('uploaded_files', [])
        if filename and filename not in existing_filenames:
            existing_filenames.append(filename)
        
        # Core document fields
        document = {
            "user_id": user_id,
            "indexed_at": datetime.utcnow().isoformat(),
            "raw_content": raw_content,
            "original_filename": filename,
            "uploaded_files": existing_filenames,
        }
        
        # Add metadata (including GCS path for original file download)
        if metadata:
            document.update(metadata)
        
        # Merge flattened profile data
        if profile_data:
            # Personal info - merge scalars (prefer new non-null values)
            document["name"] = merge_scalar(existing_profile.get("name"), profile_data.get("name"))
            document["school"] = merge_scalar(existing_profile.get("school"), profile_data.get("school"))
            document["location"] = merge_scalar(existing_profile.get("location"), profile_data.get("location"))
            document["grade"] = merge_scalar(existing_profile.get("grade"), profile_data.get("grade"))
            document["graduation_year"] = merge_scalar(existing_profile.get("graduation_year"), profile_data.get("graduation_year"))
            document["intended_major"] = merge_scalar(existing_profile.get("intended_major"), profile_data.get("intended_major"))
            
            # Academics - merge scalars
            document["gpa_weighted"] = merge_scalar(existing_profile.get("gpa_weighted"), profile_data.get("gpa_weighted"))
            document["gpa_unweighted"] = merge_scalar(existing_profile.get("gpa_unweighted"), profile_data.get("gpa_unweighted"))
            document["gpa_uc"] = merge_scalar(existing_profile.get("gpa_uc"), profile_data.get("gpa_uc"))
            document["class_rank"] = merge_scalar(existing_profile.get("class_rank"), profile_data.get("class_rank"))
            
            # Test scores - merge scalars
            document["sat_total"] = merge_scalar(existing_profile.get("sat_total"), profile_data.get("sat_total"))
            document["sat_math"] = merge_scalar(existing_profile.get("sat_math"), profile_data.get("sat_math"))
            document["sat_reading"] = merge_scalar(existing_profile.get("sat_reading"), profile_data.get("sat_reading"))
            document["act_composite"] = merge_scalar(existing_profile.get("act_composite"), profile_data.get("act_composite"))
            
            # Arrays - MERGE instead of replace
            document["ap_exams"] = merge_arrays(existing_profile.get("ap_exams", []), profile_data.get("ap_exams", []), "subject")
            document["courses"] = merge_arrays(existing_profile.get("courses", []), profile_data.get("courses", []), "name")
            document["extracurriculars"] = merge_arrays(existing_profile.get("extracurriculars", []), profile_data.get("extracurriculars", []), "name")
            document["leadership_roles"] = list(set(existing_profile.get("leadership_roles", []) + profile_data.get("leadership_roles", [])))
            document["special_programs"] = merge_arrays(existing_profile.get("special_programs", []), profile_data.get("special_programs", []), "name")
            document["awards"] = merge_arrays(existing_profile.get("awards", []), profile_data.get("awards", []), "name")
            document["work_experience"] = merge_arrays(existing_profile.get("work_experience", []), profile_data.get("work_experience", []), "employer")
            
            logger.info(f"[ES] Merged profile: {len(document.get('extracurriculars', []))} activities, {len(document.get('awards', []))} awards")
        else:
            # Preserve existing data if no new profile_data
            for key in ['name', 'school', 'location', 'grade', 'graduation_year', 'intended_major',
                       'gpa_weighted', 'gpa_unweighted', 'gpa_uc', 'class_rank',
                       'sat_total', 'sat_math', 'sat_reading', 'act_composite',
                       'ap_exams', 'courses', 'extracurriculars', 'leadership_roles',
                       'special_programs', 'awards', 'work_experience']:
                if key in existing_profile:
                    document[key] = existing_profile[key]
        
        # NEW: Track field sources (which document contributed which field)
        field_sources = existing_profile.get('field_sources', {})
        
        if profile_data:
            # Track all fields that have non-null values from this document
            for field_name, value in profile_data.items():
                if value is not None and value != [] and value != '':
                    # Initialize sources list if field is new
                    if field_name not in field_sources:
                        field_sources[field_name] = []
                    
                    # Add this filename as a source if not already tracked
                    if filename not in field_sources[field_name]:
                        field_sources[field_name].append(filename)
                        logger.info(f"[FIELD_TRACKING] {field_name} += {filename}")
        
        # Store field sources in document
        document['field_sources'] = field_sources
        
        # Index document
        response = client.index(index=ES_INDEX_NAME, id=document_id, body=document)
        
        logger.info(f"[ES] Indexed profile {document_id} for user {user_id}")
        logger.info(f"[ES] Fields: name={document.get('name')}, gpa={document.get('gpa_weighted')}, sat={document.get('sat_total')}")
        return {
            "success": True,
            "document_id": document_id,
            "message": "Profile indexed successfully"
        }
        
    except Exception as e:
        logger.error(f"[ES ERROR] Failed to index profile: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def search_student_profiles(user_id, query_text="", size=10, from_index=0):
    """Search student profiles for a user."""
    try:
        es_client = get_elasticsearch_client()
        
        # Get the single merged profile document for this user
        import hashlib
        document_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        try:
            doc = es_client.get(index=ES_INDEX_NAME, id=document_id)
            source = doc.get('_source', {})
        except:
            # No profile found
            return {
                "success": True,
                "total": 0,
                "documents": [],
                "size": size,
                "from": from_index
            }
        
        # Get list of uploaded files
        uploaded_files = source.get('uploaded_files', [])
        indexed_at = source.get('indexed_at', '')
        
        # Convert each filename into a document for the UI
        documents = []
        for filename in uploaded_files:
            documents.append({
                "name": filename,
                "display_name": filename,
                "create_time": indexed_at,
                "update_time": indexed_at,
                "state": "ACTIVE",
                "size_bytes": 0,
                "mime_type": "application/octet-stream",
                "id": f"{document_id}_{filename}",
                "document": {"filename": filename}
            })
        
        # Apply query filter
        if query_text:
            query_lower = query_text.lower()
            documents = [doc for doc in documents if query_lower in doc['display_name'].lower()]
        
        total = len(documents)
        documents = documents[from_index:from_index + size]
        
        return {
            "success": True,
            "total": total,
            "documents": documents,
            "size": size,
            "from": from_index
        }
        
    except Exception as e:
        logger.error(f"[ES ERROR] Search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "profiles": []
        }

def handle_search(request):
    """Handle profile search request."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
            
        user_id = data.get('user_email') or data.get('user_id')
        if not user_id:
            return add_cors_headers({'error': 'User ID/Email is required'}, 400)
            
        query = data.get('query', '')
        limit = int(data.get('limit', 5))
        
        result = search_student_profiles(user_id, query, limit)
        
        if result['success']:
            # Transform for agent compatibility if needed
            if query:
                result['answer'] = f"Found {len(result['documents'])} profile documents matching '{query}'"
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers(result, 500)
            
    except Exception as e:
        logger.error(f"[SEARCH_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }, 500)

    except Exception as e:
        logger.error(f"[SEARCH_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }, 500)

def cleanup_profile_on_document_delete(user_id, filename):
    """Remove fields that are only sourced from the deleted document."""
    try:
        es_client = get_elasticsearch_client()
        
        # Get user's profile
        import hashlib
        document_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        try:
            doc = es_client.get(index=ES_INDEX_NAME, id=document_id)
            profile = doc.get('_source', {})
        except:
            logger.warning(f"[CLEANUP] No profile found for {user_id}")
            return
        
        field_sources = profile.get('field_sources', {})
        if not field_sources:
            logger.info(f"[CLEANUP] No field_sources tracking for {user_id}, skipping cleanup")
            return
        
        fields_to_remove = []
        
        # Check each field's sources
        for field_name, sources in list(field_sources.items()):
            if filename in sources:
                # Remove this document from the sources list
                sources.remove(filename)
                logger.info(f"[CLEANUP] Removed {filename} from {field_name} sources")
                
                # If no sources left, mark field for removal
                if len(sources) == 0:
                    fields_to_remove.append(field_name)
                    del field_sources[field_name]
                    logger.info(f"[CLEANUP] {field_name} has no sources left, will be removed")
        
        # Remove orphaned fields from profile
        for field in fields_to_remove:
            if field in profile:
                del profile[field]
                logger.info(f"[CLEANUP] Deleted orphaned field: {field}")
        
        # Remove from uploaded_files list
        uploaded_files = profile.get('uploaded_files', [])
        if filename in uploaded_files:
            uploaded_files.remove(filename)
            profile['uploaded_files'] = uploaded_files
            logger.info(f"[CLEANUP] Removed {filename} from uploaded_files")
        
        # Update profile in ES
        profile['field_sources'] = field_sources
        es_client.index(index=ES_INDEX_NAME, id=document_id, body=profile)
        logger.info(f"[CLEANUP] Profile updated for {user_id} after deleting {filename}")
        
    except Exception as e:
        logger.error(f"[CLEANUP ERROR] Failed to cleanup profile: {e}")
        # Don't fail the delete operation if cleanup fails

def handle_delete_profile(request):
    """Handle delete profile request (RAG compatible)."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
            
        # RAG frontend sends: { document_name, user_email, filename }
        # ES needs document_id. 
        document_id = data.get('document_id') or data.get('document_name')
        user_id = data.get('user_email')
        filename = data.get('filename')
        
        if not document_id:
             return add_cors_headers({'error': 'Document ID is required'}, 400)
        
        # If filename not provided, use document_id as filename (backward compatibility)
        if not filename:
            filename = document_id
            
        # NEW: Clean up profile before deleting the file
        if user_id and filename:
            cleanup_profile_on_document_delete(user_id, filename)
             
        # If we only have filename and user_id, we might need to search for the ID
        # But for now assuming document_id is passed correctly or is the filename
        
        result = delete_student_profile(document_id, user_id=user_id, filename=filename)
        
        if result['success']:
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers(result, 500)
            
    except Exception as e:
        logger.error(f"[DELETE_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Delete failed: {str(e)}'
        }, 500)

def handle_get_content(request):
    """Get profile content (RAG compatible)."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
            
        user_id = data.get('user_email')
        filename = data.get('filename')
        
        if not user_id or not filename:
            return add_cors_headers({'error': 'User Email and Filename are required'}, 400)
            
        # Search ES for the document to get content
        # We search by user_id and filename
        es_client = get_elasticsearch_client()
        
        search_body = {
            "size": 1,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id.keyword": user_id}},
                        {"term": {"filename.keyword": filename}}
                    ]
                }
            }
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] > 0:
            hit = response['hits']['hits'][0]
            source = hit['_source']
            
            return add_cors_headers({
                'success': True,
                'content': source.get('content', ''),
                'mime_type': 'text/plain', # ES stores text
                'display_name': source.get('filename', filename),
                'file_size': source.get('file_size', 0),
                'upload_time': source.get('upload_date', ''),
                'is_pdf': False # ES content is text
            }, 200)
        else:
            return add_cors_headers({
                'success': False,
                'error': 'Document not found'
            }, 404)
            
    except Exception as e:
        logger.error(f"[GET_CONTENT_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Get content failed: {str(e)}'
        }, 500)

def handle_download_document(request):
    """Download document as file."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
            
        user_id = data.get('user_email')
        filename = data.get('filename')
        
        if not user_id or not filename:
            return add_cors_headers({'error': 'User Email and Filename are required'}, 400)
            
        # Get the GCS path from Elasticsearch
        es_client = get_elasticsearch_client()
        
        # Use user_id as document ID to get the full profile
        import hashlib
        document_id = hashlib.sha256(user_id.encode()).hexdigest()
        
        try:
            doc = es_client.get(index=ES_INDEX_NAME, id=document_id)
            source = doc.get('_source', {})
            
            # Get GCS path (stored during upload)
            gcs_path = source.get('gcs_path')
            
            if not gcs_path:
                return add_cors_headers({
                    'success': False,
                    'error': 'File not found in storage. Please re-upload the document.'
                }, 404)
            
            # Fetch file from GCS
            storage_client = storage.Client()
            bucket = storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(gcs_path)
            
            if not blob.exists():
                return add_cors_headers({
                    'success': False,
                    'error': 'File no longer exists in storage'
                }, 404)
            
            # Download file content
            file_content = blob.download_as_bytes()
            
            # Return original file with proper headers
            from flask import make_response
            response = make_response(file_content)
            response.headers['Content-Type'] = blob.content_type or 'application/octet-stream'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Add CORS headers directly to response
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-User-Email'
            
            return response
            
        except Exception as e:
            logger.error(f"[DOWNLOAD ERROR] Document not found: {e}")
            return add_cors_headers({
                'success': False,
                'error': 'Document not found'
            }, 404)
            
    except Exception as e:
        logger.error(f"[DOWNLOAD ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }, 500)


def handle_get_structured_profile(request):
    """Get profile data for visual display in ProfileViewCard.
    
    Returns FLAT profile fields directly from ES document.
    All fields (name, gpa_weighted, sat_total, courses, etc.) are at the top level.
    """
    try:
        user_id = request.args.get('user_email') or request.args.get('user_id')
        
        if not user_id:
            user_id = request.headers.get('X-User-Email')
        
        if not user_id:
            return add_cors_headers({'success': False, 'error': 'User email is required'}, 400)
        
        # Search for user's most recent profile
        es_client = get_elasticsearch_client()
        
        search_body = {
            "size": 1,
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_id.keyword": user_id}}
                    ]
                }
            },
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] > 0:
            hit = response['hits']['hits'][0]
            source = hit['_source']
            
            # Build flat profile response - all fields at top level
            profile = {
                # Personal - support both onboarding and legacy fields
                "name": source.get("student_name") or source.get("name"),
                "school": source.get("high_school") or source.get("school"),
                "location": source.get("state") or source.get("location"),
                "grade": source.get("grade_level") or source.get("grade"),
                "graduation_year": source.get("graduation_year"),
                "intended_major": source.get("intended_majors") or source.get("intended_major"),
                
                # Academics
                "gpa_weighted": source.get("gpa_weighted"),
                "gpa_unweighted": source.get("gpa_unweighted"),
                "gpa_uc": source.get("gpa_uc"),
                "class_rank": source.get("class_rank"),
                
                # Test scores
                "sat_total": source.get("sat_composite") or source.get("sat_total"),
                "sat_math": source.get("sat_math"),
                "sat_reading": source.get("sat_reading"),
                "act_composite": source.get("act_composite"),
                
                # Arrays
                "ap_exams": source.get("ap_exams", []),
                "ap_courses_count": source.get("ap_courses_count"),
                "courses": source.get("courses", []),
                "extracurriculars": source.get("extracurriculars", []),
                "leadership_roles": source.get("leadership_roles", []),
                "special_programs": source.get("special_programs", []),
                "awards": source.get("awards", []),
                "work_experience": source.get("work_experience", []),
                
                # Onboarding-specific fields
                "top_activity": source.get("top_activity"),
                "activity_type": source.get("activity_type"),
                "preferred_locations": source.get("preferred_locations", []),
                "school_size_preference": source.get("school_size_preference"),
                "campus_type_preference": source.get("campus_type_preference"),
                "onboarding_status": source.get("onboarding_status"),
                "onboarding_completed_at": source.get("onboarding_completed_at")
            }
            
            logger.info(f"[GET_PROFILE] Returning flat profile for {user_id}")
            return add_cors_headers({
                'success': True,
                'profile': profile,
                'filename': source.get('original_filename')
            }, 200)
        
        else:
            # No profile found
            return add_cors_headers({
                'success': False,
                'error': 'No profile found for user',
                'profile': None
            }, 404)
            
    except Exception as e:
        logger.error(f"[GET_PROFILE ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Get profile failed: {str(e)}'
        }, 500)

def delete_student_profile(document_id, user_id=None, filename=None):
    """Delete student profile file from GCS.
    
    Args:
        document_id: Legacy parameter (not used for GCS)
        user_id: User's email address
        filename: Filename to delete from GCS
    """
    try:
        # We need user_id and filename to delete from GCS
        if not user_id or not filename:
            logger.error(f"[DELETE ERROR] Missing user_id or filename")
            return {
                "success": False,
                "error": "User ID and filename are required"
            }
        
        # Delete file from GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob_path = f"{user_id}/{filename}"
        blob = bucket.blob(blob_path)
        
        if blob.exists():
            blob.delete()
            logger.info(f"[GCS] Deleted file: gs://{GCS_BUCKET_NAME}/{blob_path}")
            return {
                "success": True,
                "message": "File deleted successfully from storage"
            }
        else:
            logger.warning(f"[GCS] File not found: gs://{GCS_BUCKET_NAME}/{blob_path}")
            return {
                "success": True,  # Don't fail if file doesn't exist
                "message": "File not found in storage (may have been already deleted)"
            }
        
    except Exception as e:
        logger.error(f"[DELETE ERROR] Failed to delete file: {e}")
        return {
            "success": False,
            "error": str(e)
        }



# ============================================
# FIT ANALYSIS ENGINE
# ============================================

# Note: 're' imported at module level

def build_profile_content_from_fields(profile_doc):
    """
    Build profile content text from flat ES fields.
    Used when profile was created via onboarding (no raw 'content' field).
    """
    lines = ["Student Profile Summary\n"]
    
    # Personal info
    name = profile_doc.get('student_name') or profile_doc.get('name')
    school = profile_doc.get('high_school') or profile_doc.get('school')
    grade = profile_doc.get('grade_level') or profile_doc.get('grade')
    state = profile_doc.get('state') or profile_doc.get('location')
    
    if name:
        lines.append(f"Name: {name}")
    if school:
        lines.append(f"High School: {school}")
    if grade:
        lines.append(f"Grade: {grade}")
    if state:
        lines.append(f"State: {state}")
    
    # GPA
    gpa_weighted = profile_doc.get('gpa_weighted')
    gpa_unweighted = profile_doc.get('gpa_unweighted')
    gpa_uc = profile_doc.get('gpa_uc')
    
    if gpa_weighted:
        lines.append(f"Weighted GPA: {gpa_weighted}")
    if gpa_unweighted:
        lines.append(f"Unweighted GPA: {gpa_unweighted}")
    if gpa_uc:
        lines.append(f"UC GPA: {gpa_uc}")
    
    # Test scores
    sat_total = profile_doc.get('sat_composite') or profile_doc.get('sat_total')
    act_composite = profile_doc.get('act_composite')
    
    if sat_total:
        lines.append(f"SAT Score: {sat_total}")
    if act_composite:
        lines.append(f"ACT Score: {act_composite}")
    
    # Coursework
    ap_count = profile_doc.get('ap_courses_count')
    ap_exams = profile_doc.get('ap_exams', [])
    courses = profile_doc.get('courses', [])
    
    if ap_count:
        lines.append(f"AP/IB Courses: {ap_count}")
    if ap_exams:
        exam_list = ', '.join([f"{e.get('subject', 'Unknown')} ({e.get('score', 'N/A')})" for e in ap_exams[:5]])
        lines.append(f"AP Exams: {exam_list}")
    if courses:
        course_list = ', '.join([c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in courses[:10]])
        lines.append(f"Courses: {course_list}")
    
    # Extracurriculars
    extracurriculars = profile_doc.get('extracurriculars', [])
    top_activity = profile_doc.get('top_activity')
    
    if top_activity:
        lines.append(f"Top Activity: {top_activity}")
    if extracurriculars:
        ec_list = ', '.join([e.get('activity', str(e)) if isinstance(e, dict) else str(e) for e in extracurriculars[:5]])
        lines.append(f"Activities: {ec_list}")
    
    # Intended major
    intended_majors = profile_doc.get('intended_majors') or profile_doc.get('intended_major')
    if intended_majors:
        if isinstance(intended_majors, list):
            lines.append(f"Intended Major(s): {', '.join(intended_majors)}")
        else:
            lines.append(f"Intended Major: {intended_majors}")
    
    # Awards
    awards = profile_doc.get('awards', [])
    if awards:
        award_list = ', '.join([a.get('name', str(a)) if isinstance(a, dict) else str(a) for a in awards[:5]])
        lines.append(f"Awards: {award_list}")
    
    content = '\n'.join(lines)
    logger.info(f"[PROFILE BUILDER] Built profile content: {len(content)} chars, {len(lines)} lines")
    return content


def parse_student_profile(profile_content):
    """
    Extract structured academic data from profile text content using LLM.
    Pure LLM-based extraction - no fallback to regex.
    """
    if not profile_content:
        return {}
    
    content = profile_content if isinstance(profile_content, str) else str(profile_content)
    
    # Use LLM-based extraction (handles varied formats better)
    try:
        llm_result = parse_student_profile_llm(content)
        if llm_result:
            logger.info(f"[PROFILE PARSE] LLM extraction successful: GPA={llm_result.get('weighted_gpa')}, SAT={llm_result.get('sat_score')}")
            return llm_result
    except Exception as e:
        logger.error(f"[PROFILE PARSE] LLM extraction failed: {e}")
    
    # Return empty dict if LLM fails (no fallback)
    return {}


def parse_student_profile_llm(profile_content):
    """
    Use Gemini to extract structured data from any student profile format.
    More robust than regex for varied profile formats.
    """
    try:
        # Configure Gemini using new google.genai SDK
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.warning("[PROFILE PARSE LLM] No GEMINI_API_KEY found")
            return None
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Extract the following fields from this student profile. 
Return ONLY valid JSON with these exact keys (use null for missing values):

{{
  "weighted_gpa": <float or null>,
  "unweighted_gpa": <float or null>,
  "uc_gpa": <float or null>,
  "sat_score": <integer or null>,
  "act_score": <integer or null>,
  "ap_count": <integer>,
  "ap_scores": {{}},
  "intended_major": <string or null>,
  "has_leadership": <boolean>,
  "awards_count": <integer>,
  "activities_count": <integer>,
  "test_optional": <boolean - true if no test scores mentioned>
}}

STUDENT PROFILE:
{profile_content[:4000]}

Return ONLY the JSON object, no markdown formatting."""

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        
        result = json.loads(response_text)
        
        # Normalize the result
        return {
            'weighted_gpa': result.get('weighted_gpa') or result.get('uc_gpa'),
            'unweighted_gpa': result.get('unweighted_gpa'),
            'sat_score': result.get('sat_score'),
            'act_score': result.get('act_score'),
            'ap_scores': result.get('ap_scores', {}),
            'ap_count': result.get('ap_count', 0),
            'intended_major': result.get('intended_major'),
            'has_leadership': result.get('has_leadership', False),
            'awards_count': result.get('awards_count', 0),
            'activities_count': result.get('activities_count', 0),
            'test_optional': result.get('test_optional', False)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[PROFILE PARSE LLM] JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"[PROFILE PARSE LLM] Error: {e}")
        return None


def calculate_fit_with_llm(student_profile_text, university_data, intended_major='', student_profile_json=None):
    """
    Calculate fit using comprehensive LLM reasoning with selectivity override rules.
    Acts as an expert private college admissions counselor with 20+ years experience.
    
    Args:
        student_profile_text: Text content of student profile (for backwards compatibility)
        university_data: Full university profile JSON
        intended_major: Student's intended major
        student_profile_json: Full student profile as JSON dict (new - for complete context)
    """
    # Note: time imported at module level
    
    # Handle None university_data
    if university_data is None:
        logger.error("[LLM_FIT] university_data is None!")
        return {
            "fit_category": "REACH",
            "match_percentage": 50,
            "explanation": "Unable to analyze - university data not available.",
            "factors": [],
            "recommendations": ["Try refreshing the university data"],
            "university_name": "Unknown",
            "calculated_at": datetime.utcnow().isoformat(),
            "selectivity_tier": "UNKNOWN",
            "acceptance_rate": 0
        }
    
    try:
        # DEBUG: Log the actual student profile being analyzed
        logger.info(f"[LLM_FIT] Student profile text length: {len(student_profile_text)} chars")
        if student_profile_json:
            logger.info(f"[LLM_FIT] Student profile JSON has {len(student_profile_json)} fields")
        if len(student_profile_text) < 100:
            logger.warning(f"[LLM_FIT] ALERT: Profile text is very short! Content: {student_profile_text}")
        else:
            logger.info(f"[LLM_FIT] Profile preview: {student_profile_text[:300]}...")
        
        # Extract university details - handle both nested (profile.metadata) and flat structures
        # The API returns: university.profile.metadata and university.profile.admissions_data
        profile_data = university_data.get('profile', university_data)  # Fall back to university_data if no profile key
        
        # Get university name - try nested structure first, then flat
        uni_metadata = profile_data.get('metadata', {})
        uni_name = uni_metadata.get('official_name') or university_data.get('official_name', 'University')
        
        # Get acceptance rate - try nested structure first, then flat
        admissions = profile_data.get('admissions_data', {})
        current_status = admissions.get('current_status', {})
        acceptance_rate = current_status.get('overall_acceptance_rate')
        
        # Fallback to top-level acceptance_rate if nested not found
        if acceptance_rate is None:
            acceptance_rate = university_data.get('acceptance_rate', 50)
        
        # Ensure acceptance_rate is a number
        if isinstance(acceptance_rate, str):
            try:
                acceptance_rate = float(acceptance_rate.replace('%', ''))
            except:
                acceptance_rate = 50
        
        # Convert to float if needed
        try:
            acceptance_rate = float(acceptance_rate)
        except (TypeError, ValueError):
            acceptance_rate = 50
        
        # Get admitted student profile for comparison
        admitted_profile = admissions.get('admitted_student_profile', {})
        
        # DEBUG: Log what we extracted
        logger.info(f"[LLM_FIT] University: {uni_name}, Acceptance Rate: {acceptance_rate}%, Selectivity will be: {'ULTRA_SELECTIVE' if acceptance_rate < 8 else 'HIGHLY_SELECTIVE' if acceptance_rate < 15 else 'SELECTIVE'}")
        
        # Pass ENTIRE university profile to LLM for comprehensive recommendations
        # User requested: pass entire profile instead of extracting selected pieces
        # This gives LLM access to ALL data: essays, scholarships, majors, strategies, etc.
        uni_profile_full = json.dumps(profile_data, default=str)
        
        # Also serialize student profile JSON if available
        student_profile_json_str = ""
        if student_profile_json:
            student_profile_json_str = json.dumps(student_profile_json, default=str)
            logger.info(f"[LLM_FIT] Student profile JSON size: {len(student_profile_json_str)} chars")
        
        logger.info(f"[LLM_FIT] Full university profile size: {len(uni_profile_full)} chars (~{len(uni_profile_full)//4} tokens)")
        
        # Determine selectivity tier and category floor
        if acceptance_rate < 8:
            selectivity_tier = "ULTRA_SELECTIVE"
            category_floor = "SUPER_REACH"
            selectivity_note = "This is an ULTRA-SELECTIVE school (<8% acceptance). Even perfect applicants are often rejected. MINIMUM category is SUPER_REACH."
        elif acceptance_rate < 15:
            selectivity_tier = "HIGHLY_SELECTIVE"
            category_floor = "REACH"
            selectivity_note = "This is a HIGHLY SELECTIVE school (8-15% acceptance). Only top students have a chance. MINIMUM category is REACH."
        elif acceptance_rate < 25:
            selectivity_tier = "VERY_SELECTIVE"
            category_floor = None
            selectivity_note = "This is a VERY SELECTIVE school (15-25% acceptance). Strong applicants compete."
        elif acceptance_rate < 40:
            selectivity_tier = "SELECTIVE"
            category_floor = None
            selectivity_note = "This is a SELECTIVE school (25-40% acceptance). Standard competitive admissions."
        else:
            selectivity_tier = "ACCESSIBLE"
            category_floor = None
            selectivity_note = "This is an ACCESSIBLE school (>40% acceptance). Strong students are very likely admitted."
        
        # Build student profile section - include BOTH text and structured JSON
        student_section = f"""{student_profile_text}
Intended Major: {intended_major or 'Undecided'}"""
        
        if student_profile_json_str:
            student_section += f"""

**COMPLETE STUDENT PROFILE DATA (structured):**
{student_profile_json_str}"""
        
        prompt = f"""You are a private college admissions counselor with 20+ years of experience placing students at Ivy League and top-50 universities. You have deep knowledge of how selective admissions works and understand that even excellent students face rejection at highly selective schools.

**STUDENT PROFILE:**
{student_section}

**COMPLETE UNIVERSITY DATA (use this for all recommendations):**
{uni_profile_full}

**SELECTIVITY CONTEXT:**
Acceptance Rate: {acceptance_rate}%
Selectivity Tier: {selectivity_tier}
{selectivity_note}

**SCORING FRAMEWORK:**

1. **ACADEMIC STRENGTH (40 points max)**
   - GPA vs admitted student profile: 0-20 points
     * GPA > school's 75th percentile → 18-20 points
     * GPA at school's 50th percentile → 12-14 points
     * GPA at school's 25th percentile → 6-8 points
     * GPA below 25th percentile → 0-5 points
   - Test Scores (SAT/ACT): 0-12 points
   - Course Rigor (AP/IB/Honors count): 0-8 points

2. **HOLISTIC PROFILE (30 points max)**
   - Extracurricular depth & impact: 0-12 points
   - Leadership positions & scope: 0-8 points
   - Awards & recognition: 0-5 points
   - Unique factors (first-gen, hooks): 0-5 points

3. **MAJOR FIT (15 points max)**
   - Major availability & strength: 0-8 points
   - Related activities/demonstrated interest: 0-4 points
   - Clarity of academic goals: 0-3 points

4. **SELECTIVITY ADJUSTMENT (-15 to +5)**
   - <8% acceptance: -15 points (SUPER_REACH floor)
   - 8-15% acceptance: -10 points (REACH floor)
   - 15-25% acceptance: -5 points
   - 25-40% acceptance: 0 points
   - >40% acceptance: +5 points (SAFETY possible)

**CATEGORY ASSIGNMENT (after selectivity adjustment):**
- **SAFETY** (score 75-100): Student significantly exceeds averages AND acceptance rate >40%
- **TARGET** (score 55-74): Student matches averages AND acceptance rate >25%
- **REACH** (score 35-54): Student slightly below averages OR acceptance rate 10-25%
- **SUPER_REACH** (score 0-34): Student below averages OR acceptance rate <10%

**CRITICAL RULES:**
1. Schools with <8% acceptance CANNOT be SAFETY or TARGET for ANY student
2. Schools with 8-15% acceptance CANNOT be SAFETY for ANY student
3. If student profile lacks GPA or test scores, they cannot qualify for SAFETY at any school
4. Always cite specific data from the student profile (actual GPA, actual activities)

**YOUR TASK:**
Analyze this student's fit for {uni_name}. Be realistic about chances at selective schools.

**8-CATEGORY COMPREHENSIVE RECOMMENDATION SYSTEM:**
You have access to COMPLETE university data. Generate recommendations across ALL 8 categories:

**CATEGORY 1: ESSAY ANGLES** (use application_process.supplemental_requirements and student_insights.essay_tips)
- Generate 2-3 specific essay angles for this student
- Reference ACTUAL essay prompts from the school if available
- Connect specific student experiences to specific school values/programs

**CATEGORY 2: APPLICATION TIMELINE** (use application_process.application_deadlines)
- Recommend which plan (ED/EA/RD) based on student's competitiveness
- Include financial aid deadlines from financials
- Provide key preparation milestones

**CATEGORY 3: SCHOLARSHIP MATCHES** (use financials.scholarships)
- Identify scholarships this student might qualify for
- Match based on student's GPA, activities, and demographics
- Include deadlines and application methods

**CATEGORY 4: TEST STRATEGY** (use admissions_data.admitted_student_profile.testing)
- Compare student's scores to school's middle 50%
- Recommend submit/don't submit based on competitive position
- Include school's test submission rate for context

**CATEGORY 5: MAJOR STRATEGY** (use academic_structure.colleges[].majors[])
- Find student's intended major in the data
- Check if impacted, prerequisites, internal transfer difficulty
- Recommend backup major if appropriate

**CATEGORY 6: DEMONSTRATED INTEREST** (use application_process.holistic_factors.demonstrated_interest)
- If school tracks interest, give specific tactics
- Include interview policy guidance
- Mention any optional elements that show commitment

**CATEGORY 7: RED FLAGS TO AVOID** (use student_insights.red_flags)
- Customize school-specific warnings to this student
- What mistakes would hurt THIS student's application

**CATEGORY 8: TOP STRATEGIC RECOMMENDATIONS** (synthesize all analysis)
- 3 most impactful actions this student should take
- Each must address a gap and reference school-specific context

**OUTPUT FORMAT - Return ONLY valid JSON:**
{{
  "match_percentage": <integer 0-100>,
  "fit_category": "<SAFETY|TARGET|REACH|SUPER_REACH>",
  "explanation": "<5-6 sentence analysis: Start with category justification citing acceptance rate. Mention 2-3 specific student strengths. Acknowledge gaps. End with what could strengthen the application.>",
  "factors": [
    {{ "name": "Academic", "score": <0-40>, "max": 40, "detail": "<cite actual GPA/scores from profile vs school's admitted profile>" }},
    {{ "name": "Holistic", "score": <0-30>, "max": 30, "detail": "<cite specific activities/leadership from profile>" }},
    {{ "name": "Major Fit", "score": <0-15>, "max": 15, "detail": "<assess major availability and student's demonstrated interest>" }},
    {{ "name": "Selectivity", "score": <-15 to +5>, "max": 5, "detail": "<{acceptance_rate}% acceptance rate impact>" }}
  ],
  "gap_analysis": {{
    "primary_gap": "<name of factor with lowest % score and why>",
    "secondary_gap": "<name of second lowest % score factor and why>",
    "student_strengths": ["<specific strength 1>", "<specific strength 2>", "<specific strength 3>"]
  }},
  "essay_angles": [
    {{
      "essay_prompt": "<actual essay prompt from school if available, or 'Why Us' / 'Personal Statement'>",
      "angle": "<specific angle for this student to take>",
      "student_hook": "<specific experience from their profile to highlight>",
      "school_hook": "<specific program/value/resource at {uni_name} to reference>",
      "word_limit": <word limit if known, or null>,
      "tip": "<relevant tip from student_insights.essay_tips if available>"
    }}
  ],
  "application_timeline": {{
    "recommended_plan": "<Early Decision I|Early Decision II|Early Action|Regular Decision|Rolling>",
    "deadline": "<date in YYYY-MM-DD format>",
    "is_binding": <true|false>,
    "rationale": "<why this plan is best for this student's profile and circumstances>",
    "financial_aid_deadline": "<date if different from app deadline>",
    "key_milestones": [
      "<milestone 1 with date, e.g., 'Request teacher recs by October 1'>",
      "<milestone 2 with date>",
      "<milestone 3 with date>"
    ]
  }},
  "scholarship_matches": [
    {{
      "name": "<scholarship name from financials.scholarships>",
      "amount": "<amount or range>",
      "deadline": "<deadline or 'automatic consideration'>",
      "match_reason": "<why this student qualifies - cite specific profile elements>",
      "application_method": "<how to apply>"
    }}
  ],
  "test_strategy": {{
    "recommendation": "<Submit|Don't Submit|Consider Submitting>",
    "student_sat": <student's SAT if available, or null>,
    "student_act": <student's ACT if available, or null>,
    "school_sat_middle_50": "<e.g., 1340-1500>",
    "school_act_middle_50": "<e.g., 30-33>",
    "school_submission_rate": <percentage of applicants who submit>,
    "student_score_position": "<above|in|below> middle 50%",
    "rationale": "<explanation of why submit or not>"
  }},
  "major_strategy": {{
    "intended_major": "<student's intended major>",
    "is_available": <true|false>,
    "college_within_university": "<which college/school offers this major>",
    "is_impacted": <true|false|unknown>,
    "acceptance_rate_estimate": <if available, or null>,
    "prerequisites_met": "<assessment of whether student has needed courses>",
    "backup_major": "<recommended alternative major at this school>",
    "internal_transfer_difficulty": "<easy|moderate|difficult|unknown>",
    "strategic_tip": "<from application_strategy.major_selection_tactics if relevant>"
  }},
  "demonstrated_interest_tips": [
    "<specific tactic 1 based on school's DI tracking>",
    "<specific tactic 2>",
    "<specific tactic 3>"
  ],
  "red_flags_to_avoid": [
    "<specific red flag from student_insights.red_flags customized to this student>",
    "<another relevant red flag>"
  ],
  "recommendations": [
    {{
      "action": "<specific, actionable recommendation>",
      "addresses_gap": "<which factor this improves: Academic|Holistic|Major Fit>",
      "school_specific_context": "<how this connects to {uni_name}'s specific programs/values/resources>",
      "timeline": "<when to do this: before application|during senior year|in essays|etc>",
      "impact": "<how this strengthens the application>"
    }},
    {{
      "action": "<second most important recommendation>",
      "addresses_gap": "<which factor>",
      "school_specific_context": "<school-specific connection>",
      "timeline": "<when>",
      "impact": "<outcome>"
    }},
    {{
      "action": "<third most important recommendation>",
      "addresses_gap": "<which factor>",
      "school_specific_context": "<school-specific connection>",
      "timeline": "<when>",
      "impact": "<outcome>"
    }}
  ]
}}"""

        # Call Gemini with retry logic
        max_retries = 2
        client = genai.Client(api_key=GEMINI_API_KEY)
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=prompt
                )
                
                # Parse output
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```'):
                    lines = response_text.split('\n')
                    start_idx = 1 if lines[0].startswith('```') else 0
                    end_idx = len(lines) - 1 if lines[-1] == '```' else len(lines)
                    response_text = '\n'.join(lines[start_idx:end_idx])
                    if response_text.startswith('json'):
                        response_text = response_text[4:].strip()
                
                result = json.loads(response_text)
                
                # Validate required fields
                if 'fit_category' not in result or 'match_percentage' not in result:
                    raise ValueError("Missing required fields in LLM response")
                
                # === POST-PROCESSING: SELECTIVITY OVERRIDE ===
                original_category = result['fit_category']
                
                # Apply selectivity floor - this CANNOT be overridden
                if category_floor == "SUPER_REACH" and original_category in ['SAFETY', 'TARGET', 'REACH']:
                    result['fit_category'] = 'SUPER_REACH'
                    logger.info(f"[LLM_FIT] Selectivity override: {original_category} -> SUPER_REACH (acceptance rate {acceptance_rate}%)")
                elif category_floor == "REACH" and original_category in ['SAFETY', 'TARGET']:
                    result['fit_category'] = 'REACH'
                    logger.info(f"[LLM_FIT] Selectivity override: {original_category} -> REACH (acceptance rate {acceptance_rate}%)")
                elif category_floor == "TARGET" and original_category == 'SAFETY':
                    result['fit_category'] = 'TARGET'
                    logger.info(f"[LLM_FIT] Selectivity override: {original_category} -> TARGET (acceptance rate {acceptance_rate}%)")
                
                # === POST-PROCESSING: SELECTIVITY CEILING ===
                # Enforce alignment with soft_fit_category thresholds:
                # >50% acceptance = SAFETY (ceiling)
                # 25-50% = TARGET or SAFETY (ceiling)
                # This prevents LLM from calling a 60% acceptance school "TARGET"
                if acceptance_rate >= 50 and result['fit_category'] in ['TARGET', 'REACH', 'SUPER_REACH']:
                    logger.info(f"[LLM_FIT] Ceiling override: {result['fit_category']} -> SAFETY (acceptance rate {acceptance_rate}% >= 50%)")
                    result['fit_category'] = 'SAFETY'
                elif acceptance_rate >= 25 and result['fit_category'] in ['REACH', 'SUPER_REACH']:
                    logger.info(f"[LLM_FIT] Ceiling override: {result['fit_category']} -> TARGET (acceptance rate {acceptance_rate}% >= 25%)")
                    result['fit_category'] = 'TARGET'
                
                # Validate category is in allowed list
                valid_categories = ['SAFETY', 'TARGET', 'REACH', 'SUPER_REACH']
                if result['fit_category'] not in valid_categories:
                    result['fit_category'] = 'REACH'
                
                # Add metadata
                result['university_name'] = uni_name
                result['calculated_at'] = datetime.utcnow().isoformat()
                result['selectivity_tier'] = selectivity_tier
                result['acceptance_rate'] = acceptance_rate
                
                logger.info(f"[LLM_FIT] {uni_name}: {result['fit_category']} ({result['match_percentage']}%) - Selectivity: {selectivity_tier}")
                return result
                
            except json.JSONDecodeError as je:
                logger.warning(f"[LLM_FIT] JSON parse error (attempt {attempt+1}): {str(je)[:100]}")
                if attempt < max_retries:
                    time.sleep(0.5)
                    continue
                raise
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning(f"[LLM_FIT] Rate limited, waiting... (attempt {attempt+1})")
                    time.sleep(2 ** attempt)
                    continue
                raise

    except Exception as e:
        logger.error(f"[LLM_FIT_ERROR] {uni_name if 'uni_name' in dir() else 'Unknown'}: {str(e)}")
        # Return a sensible fallback based on acceptance rate with proper selectivity floor
        if acceptance_rate < 8:
            fallback_category = 'SUPER_REACH'
        elif acceptance_rate < 15:
            fallback_category = 'REACH'
        elif acceptance_rate < 40:
            fallback_category = 'TARGET'
        else:
            fallback_category = 'SAFETY'
            
        return {
            "fit_category": fallback_category,
            "match_percentage": 50,
            "explanation": f"Detailed analysis unavailable. Based on {acceptance_rate}% acceptance rate ({selectivity_tier if 'selectivity_tier' in dir() else 'unknown selectivity'}), categorized as {fallback_category}.",
            "factors": [
                {"name": "Academic", "score": 20, "max": 40, "detail": "Unable to fully analyze"},
                {"name": "Holistic", "score": 15, "max": 30, "detail": "Unable to fully analyze"},
                {"name": "Major Fit", "score": 8, "max": 15, "detail": "Unable to fully analyze"},
                {"name": "Selectivity", "score": 0, "max": 5, "detail": f"{acceptance_rate}% acceptance rate"}
            ],
            "recommendations": ["Complete profile for accurate analysis"],
            "university_name": university_data.get('metadata', {}).get('official_name', 'University'),
            "calculated_at": datetime.utcnow().isoformat(),
            "selectivity_tier": selectivity_tier if 'selectivity_tier' in dir() else "UNKNOWN",
            "acceptance_rate": acceptance_rate
        }


def calculate_fit_for_college(user_id, university_id, intended_major=''):
    """
    Calculate fit analysis for a specific college.
    Fetches student profile and university data, then calculates fit.
    """
    try:
        client = get_elasticsearch_client()
        
        # Get student profile
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            logger.warning(f"[FIT] No profile found for user: {user_id}")
            return None
        
        profile_doc = response['hits']['hits'][0]['_source']
        
        # Pass the ENTIRE student profile as JSON to the LLM
        # Remove internal/metadata fields that aren't useful
        fields_to_exclude = ['indexed_at', 'updated_at', 'created_at', '_id', 'embedding', 'chunk_id', 'user_id']
        profile_data_clean = {k: v for k, v in profile_doc.items() if k not in fields_to_exclude and v}
        
        # Also get the content field for backwards compatibility (some prompts reference profile text)
        profile_content = profile_doc.get('content', '')
        if not profile_content or len(profile_content.strip()) < 50:
            logger.info(f"[FIT] Building profile content from flat fields for {user_id}")
            profile_content = build_profile_content_from_fields(profile_doc)
        
        # Log profile summary
        logger.info(f"[FIT] Student profile has {len(profile_data_clean)} fields, content length: {len(profile_content)}")
        
        # Parse student profile (for legacy code compatibility)
        student_profile = parse_student_profile(profile_content)
        
        # Fetch university data via KB API (has correct data structure with acceptance_rate)
        university_data = fetch_university_profile(university_id)
        
        if university_data:
            # Log the acceptance rate for debugging
            profile_data = university_data.get('profile', university_data)
            admissions = profile_data.get('admissions_data', {})
            current_status = admissions.get('current_status', {})
            acc_rate = current_status.get('overall_acceptance_rate') or university_data.get('acceptance_rate', 'N/A')
            logger.info(f"[FIT] Fetched university {university_id}: acceptance_rate={acc_rate}%")
        
        if not university_data:
            logger.warning(f"[FIT] University data not found: {university_id}")
            return {
                'fit_category': 'TARGET',
                'match_percentage': 50,
                'factors': [{'name': 'Data Unavailable', 'score': 0, 'max': 0, 'detail': 'University data not in knowledge base'}],
                'recommendations': ['University data not available for analysis'],
                'university_name': university_id.replace('_', ' ').title(),
                'calculated_at': datetime.utcnow().isoformat()
            }
        
        # Calculate comprehensive fit using PURE LLM reasoning
        # Pass BOTH the text content AND the full profile JSON
        fit_analysis = calculate_fit_with_llm(profile_content, university_data, intended_major, profile_data_clean)
        
        logger.info(f"[FIT] Calculated fit for {user_id} -> {university_id}: {fit_analysis['fit_category']} ({fit_analysis['match_percentage']}%)")
        
        return fit_analysis
        
    except Exception as e:
        logger.error(f"[FIT ERROR] {str(e)}")
        return None


def handle_update_college_list(request):
    """Add or remove a college from user's college list (new v2 architecture)."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_id') or data.get('user_email')
        action = data.get('action')  # 'add' or 'remove'
        university = data.get('university')  # {id, name}
        intended_major = data.get('intended_major', '')
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        if not action or action not in ['add', 'remove']:
            return add_cors_headers({'error': 'Action must be "add" or "remove"'}, 400)
        if not university or not university.get('id'):
            return add_cors_headers({'error': 'University with id is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Get the ID from the request - but we need to look up the EXACT ES ID from KB
        # because cached data (like precomputed fits) may have old normalized (lowercase) IDs
        requested_uni_id = university['id']
        
        # Try to find the exact ES ID from the knowledge base
        # This handles cases where frontend sends lowercase ID from cached data
        exact_es_id = None
        try:
            # First try the requested ID directly
            kb_response = requests.get(
                f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}?university_id={requested_uni_id}",
                timeout=10
            )
            if kb_response.status_code == 200:
                kb_data = kb_response.json()
                if kb_data.get('success') and kb_data.get('university'):
                    exact_es_id = kb_data['university'].get('_id') or requested_uni_id
                    logger.info(f"[LIST] Found exact ES ID: {exact_es_id}")
        except Exception as e:
            logger.warning(f"[LIST] Could not lookup exact ES ID: {e}")
        
        # Use exact ES ID if found, otherwise fall back to requested ID
        original_uni_id = exact_es_id if exact_es_id else requested_uni_id
        logger.info(f"[LIST] Using university ID: {original_uni_id} (requested: {requested_uni_id})")
        
        # NOTE: We use a sanitized version for doc_id generation (to avoid special chars)
        # but store the exact ID for fetching university profiles
        sanitized_id = original_uni_id.replace(' ', '_').replace('-', '_')
        
        # Generate unique document ID for this user+university pair
        email_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        doc_id = f"{email_hash}_{sanitized_id}"
        
        if action == 'add':
            # Check if already exists
            try:
                existing = es_client.get(index=ES_LIST_ITEMS_INDEX, id=doc_id)
                if existing:
                    # Already in list - return current list
                    return add_cors_headers({
                        'success': True,
                        'message': 'College already in list',
                        'college_list': get_user_college_list(es_client, user_id)
                    }, 200)
            except NotFoundError:
                pass  # Document doesn't exist, proceed to create
            except Exception as e:
                logger.warning(f"[LIST] Unexpected error checking document: {e}")
            
            # If intended_major not provided, extract from user's profile
            if not intended_major:
                intended_major = get_intended_major_from_profile(es_client, user_id)
                logger.info(f"[LIST] Auto-populated intended_major from profile: {intended_major}")
            
            # Create new list item document with EXACT ES ID (not normalized)
            # NOTE: intended_major is NOT stored per-college - always read from profile
            list_doc = {
                'user_email': user_id,
                'university_id': original_uni_id,  # Use EXACT ES ID for fetching profiles
                'university_name': university.get('name', ''),
                'status': 'favorites',
                'application_plan': None,  # User's chosen deadline type: 'ED', 'ED2', 'EA', 'REA', 'RD', null
                'application_status': 'planning',  # planning, drafting, submitted, decision
                'application_tasks': {
                    'common_app_complete': False,
                    'essays_complete': False,
                    'supplements_complete': False,
                    'test_scores_sent': False,
                    'recommendations_requested': False,
                    'recommendations_received': False,
                    'transcript_sent': False,
                    'fee_paid': False,
                    'submitted': False,
                    'interview_scheduled': False
                },
                'added_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            es_client.index(index=ES_LIST_ITEMS_INDEX, id=doc_id, body=list_doc, refresh=True)
            logger.info(f"[LIST] Added {university['id']} for {user_id} with major: {intended_major}")
            
        elif action == 'remove':
            # Delete the document
            try:
                es_client.delete(index=ES_LIST_ITEMS_INDEX, id=doc_id, refresh=True)
                logger.info(f"[LIST] Removed {university['id']} for {user_id}")
            except Exception as e:
                logger.warning(f"[LIST] Document not found or already deleted: {e}")

        elif action == 'update':
            # Update specific fields
            update_doc = {}
            if 'selected_major' in data:
                update_doc['selected_major'] = data['selected_major']
            
            # Allow updating other future fields here if needed
            
            if update_doc:
                try:
                    es_client.update(
                        index=ES_LIST_ITEMS_INDEX, 
                        id=doc_id, 
                        body={"doc": update_doc}, 
                        refresh=True
                    )
                    logger.info(f"[LIST] Updated {university['id']} for {user_id}: {update_doc}")
                except NotFoundError:
                     # If doc doesn't exist, create it (auto-add) but simpler
                    if 'selected_major' in update_doc:
                        list_doc = {
                            'user_email': user_id,
                            'university_id': original_uni_id,
                            'university_name': university.get('name', ''),
                            'status': 'favorites',
                            'selected_major': update_doc['selected_major'],
                            'added_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        }
                        es_client.index(index=ES_LIST_ITEMS_INDEX, id=doc_id, body=list_doc, refresh=True)
                        logger.info(f"[LIST] Auto-added {university['id']} during update")
                except Exception as e:
                    logger.error(f"[LIST] Update failed: {e}")
                    raise e
        
        # Fetch updated college list
        college_list = get_user_college_list(es_client, user_id)
        
        return add_cors_headers({
            'success': True,
            'action': action,
            'university_id': university['id'],
            'college_list': college_list,
            'message': f'College {"updated" if action == "update" else "added to" if action == "add" else "removed from"} list'
        }, 200)
        
    except Exception as e:
        logger.error(f"[COLLEGE_LIST ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to update college list: {str(e)}'
        }, 500)


def get_user_college_list(es_client, user_id):
    """Helper to fetch user's college list from the new index."""
    search_body = {
        "size": 500,
        "query": {"term": {"user_email": user_id}},
        "sort": [{"added_at": {"order": "desc"}}]
    }
    response = es_client.search(index=ES_LIST_ITEMS_INDEX, body=search_body)
    
    college_list = []
    for hit in response['hits']['hits']:
        item = hit['_source']
        college_list.append({
            'university_id': item.get('university_id'),
            'university_name': item.get('university_name'),
            'status': item.get('status', 'favorites'),
            'application_plan': item.get('application_plan'),  # ED, EA, RD, etc.
            'application_status': item.get('application_status', 'planning'),
            'application_tasks': item.get('application_tasks', {}),
            'added_at': item.get('added_at')
            # NOTE: intended_major removed - always read from profile
        })
    return college_list


def get_intended_major_from_profile(es_client, user_id):
    """Extract intended major from user's profile content (markdown)."""
    try:
        # Search for user's profile in the legacy index to get content
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "_source": ["content"],
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return ''
        
        content = response['hits']['hits'][0]['_source'].get('content', '')
        
        # Parse intended major from markdown content
        # Look for patterns like "## Intended Major\n*   Business" or "Intended Major: Business"
        patterns = [
            r'##\s*Intended\s+Major\s*\n+\*?\s*(.+?)(?:\n|$)',  # Markdown header format
            r'Intended\s+Major[:\s]+(.+?)(?:\n|$)',  # Simple label format
            r'\*+Intended\s+Major\*+[:\s]+(.+?)(?:\n|$)',  # Bold format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                major = match.group(1).strip()
                # Clean up common formatting
                major = major.strip('*').strip()
                if major:
                    logger.info(f"[PROFILE] Found intended_major: {major}")
                    return major
        
        return ''
    except Exception as e:
        logger.error(f"[PROFILE] Error extracting intended_major: {e}")
        return ''


def handle_bulk_remove_colleges(request):
    """
    Remove multiple colleges from user's college list at once.
    
    POST /bulk-remove-colleges
    {
        "user_email": "student@gmail.com",
        "university_ids": ["harvard_university_slug", "mit_slug", "stanford_slug"]
    }
    
    Returns:
    {
        "success": true,
        "removed_count": 3,
        "remaining_count": 5,
        "college_list": [...]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_id') or data.get('user_email')
        university_ids = data.get('university_ids', [])
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        if not university_ids or not isinstance(university_ids, list):
            return add_cors_headers({'error': 'university_ids must be a non-empty array'}, 400)
        
        logger.info(f"[BULK_REMOVE] Removing {len(university_ids)} colleges for user {user_id}")
        
        es_client = get_elasticsearch_client()
        
        # Normalize all university IDs for consistent matching
        normalized_ids = [normalize_university_id(uid) for uid in university_ids]
        
        # Generate doc IDs and delete each document
        email_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        removed_count = 0
        
        for normalized_id in normalized_ids:
            doc_id = f"{email_hash}_{normalized_id}"
            try:
                es_client.delete(index=ES_LIST_ITEMS_INDEX, id=doc_id, refresh=False)
                removed_count += 1
                logger.info(f"[BULK_REMOVE] Deleted {normalized_id}")
            except Exception as e:
                logger.warning(f"[BULK_REMOVE] Could not delete {normalized_id}: {e}")
        
        # Refresh the index
        es_client.indices.refresh(index=ES_LIST_ITEMS_INDEX)
        
        # Get updated college list
        college_list = get_user_college_list(es_client, user_id)
        
        logger.info(f"[BULK_REMOVE] Removed {removed_count} colleges for user {user_id}")
        
        return add_cors_headers({
            'success': True,
            'removed_count': removed_count,
            'remaining_count': len(college_list),
            'college_list': college_list,
            'message': f'Removed {removed_count} colleges from list'
        }, 200)
        
    except Exception as e:
        logger.error(f"[BULK_REMOVE ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to remove colleges: {str(e)}'
        }, 500)


# ============================================
# DEADLINE TRACKER FUNCTIONS
# ============================================

def get_user_deadlines(user_id: str) -> dict:
    """
    Get all application deadlines for universities in user's college list.
    Pulls deadline data from university knowledge base and combines with user's application plan.
    
    Returns:
        dict with deadlines sorted by date
    """
    try:
        from elasticsearch import Elasticsearch
        
        es_client = get_elasticsearch_client()
        
        # Step 1: Get user's saved schools with their application plans
        search_body = {
            "size": 500,
            "query": {"term": {"user_email": user_id}},
            "_source": ["university_id", "university_name", "application_plan", "status"]
        }
        list_response = es_client.search(index=ES_LIST_ITEMS_INDEX, body=search_body)
        
        if list_response['hits']['total']['value'] == 0:
            return {
                "success": True,
                "deadlines": [],
                "message": "No schools saved yet"
            }
        
        # Build lookup of user's application plans
        user_plans = {}
        for hit in list_response['hits']['hits']:
            item = hit['_source']
            uni_id = item.get('university_id')
            user_plans[uni_id] = {
                'application_plan': item.get('application_plan'),
                'university_name': item.get('university_name'),
                'status': item.get('status')
            }
        
        university_ids = list(user_plans.keys())
        
        # Fetch deadline data from universities via the knowledge base API
        deadlines = []
        
        for uni_id in university_ids:
            try:
                # Use the existing fetch_university_profile helper which handles ID variations
                uni_data = fetch_university_profile(uni_id)
                
                if not uni_data:
                    logger.warning(f"[DEADLINES] Could not find university {uni_id}")
                    continue
                
                # Get full profile from the fetched data
                profile = uni_data.get('profile', uni_data)
                uni_name = user_plans[uni_id].get('university_name') or uni_data.get('official_name', uni_id)
                user_plan = user_plans[uni_id].get('application_plan')
                
                # Extract application_deadlines from the university profile
                app_process = profile.get('application_process', {})
                app_deadlines = app_process.get('application_deadlines', [])
                
                if not app_deadlines:
                    # Try alternate paths
                    app_deadlines = profile.get('application_deadlines', [])
                
                if not app_deadlines:
                    logger.info(f"[DEADLINES] No deadlines found for {uni_id}")
                    continue
                
                for deadline in app_deadlines:
                    plan_type = deadline.get('plan_type', 'Unknown')
                    date_str = deadline.get('date')
                    is_binding = deadline.get('is_binding', False)
                    notes = deadline.get('notes', '')
                    
                    # Determine if this is the user's chosen plan
                    is_user_plan = False
                    if user_plan:
                        # Match user plan to deadline type
                        plan_lower = plan_type.lower()
                        user_plan_lower = user_plan.lower()
                        if user_plan_lower in plan_lower or plan_lower.startswith(user_plan_lower[:2]):
                            is_user_plan = True
                    
                    deadlines.append({
                        'university_id': uni_id,
                        'university_name': uni_name,
                        'plan_type': plan_type,
                        'date': date_str,
                        'is_binding': is_binding,
                        'is_user_plan': is_user_plan,
                        'notes': notes,
                        'user_application_plan': user_plan
                    })
                    
            except Exception as e:
                logger.warning(f"[DEADLINES] Error fetching {uni_id}: {e}")
                continue
        
        # Sort by date
        def parse_date(d):
            try:
                return datetime.strptime(d.get('date', '9999-12-31'), '%Y-%m-%d')
            except:
                return datetime(9999, 12, 31)
        
        deadlines.sort(key=parse_date)
        
        logger.info(f"[DEADLINES] Fetched {len(deadlines)} deadlines for {user_id}")
        
        return {
            "success": True,
            "deadlines": deadlines,
            "university_count": len(university_ids)
        }
        
    except Exception as e:
        logger.error(f"[DEADLINES] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def update_application_plan(user_id: str, university_id: str, application_plan: str) -> dict:
    """
    Update the user's chosen application plan (ED, EA, RD, etc.) for a specific university.
    
    Args:
        user_id: User's email
        university_id: The university ID
        application_plan: The plan type ('ED', 'ED2', 'EA', 'REA', 'RD', or None)
    
    Returns:
        dict with success status
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Normalize ID for lookup
        normalized_id = normalize_university_id(university_id)
        doc_id = f"{user_id}_{normalized_id}"
        
        # Get existing document
        try:
            existing = es_client.get(index=ES_LIST_ITEMS_INDEX, id=doc_id)
        except:
            return {
                "success": False,
                "error": f"University {university_id} not found in your college list"
            }
        
        # Update the application_plan field
        update_body = {
            "doc": {
                "application_plan": application_plan,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        es_client.update(index=ES_LIST_ITEMS_INDEX, id=doc_id, body=update_body, refresh=True)
        
        logger.info(f"[DEADLINES] Updated application_plan to {application_plan} for {user_id}/{university_id}")
        
        return {
            "success": True,
            "university_id": university_id,
            "application_plan": application_plan,
            "message": f"Application plan set to {application_plan or 'None'}"
        }
        
    except Exception as e:
        logger.error(f"[DEADLINES] Update error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def update_application_status(user_id: str, university_id: str, status: str) -> dict:
    """
    Update the application status (planning, drafting, submitted, decision) for a specific university.
    
    Args:
        user_id: User's email
        university_id: The university ID
        status: One of 'planning', 'drafting', 'submitted', 'decision'
    
    Returns:
        dict with success status
    """
    valid_statuses = ['planning', 'drafting', 'submitted', 'decision']
    if status not in valid_statuses:
        return {
            "success": False,
            "error": f"Invalid status. Must be one of: {valid_statuses}"
        }
    
    try:
        es_client = get_elasticsearch_client()
        
        # Normalize ID for lookup
        normalized_id = normalize_university_id(university_id)
        doc_id = f"{user_id}_{normalized_id}"
        
        # Get existing document
        try:
            existing = es_client.get(index=ES_LIST_ITEMS_INDEX, id=doc_id)
        except:
            return {
                "success": False,
                "error": f"University {university_id} not found in your college list"
            }
        
        # Update the application_status field
        update_body = {
            "doc": {
                "application_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        es_client.update(index=ES_LIST_ITEMS_INDEX, id=doc_id, body=update_body, refresh=True)
        
        logger.info(f"[APPS] Updated application_status to {status} for {user_id}/{university_id}")
        
        return {
            "success": True,
            "university_id": university_id,
            "application_status": status,
            "message": f"Application status updated to {status}"
        }
        
    except Exception as e:
        logger.error(f"[APPS] Update status error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def update_application_task(user_id: str, university_id: str, task_name: str, completed: bool) -> dict:
    """
    Update a specific application task (checklist item) for a university.
    
    Args:
        user_id: User's email
        university_id: The university ID
        task_name: Name of the task (e.g., 'essays_complete', 'test_scores_sent')
        completed: Boolean indicating if task is completed
    
    Returns:
        dict with success status and updated task list
    """
    valid_tasks = [
        'common_app_complete', 'essays_complete', 'supplements_complete',
        'test_scores_sent', 'recommendations_requested', 'recommendations_received',
        'transcript_sent', 'fee_paid', 'submitted', 'interview_scheduled'
    ]
    
    if task_name not in valid_tasks:
        return {
            "success": False,
            "error": f"Invalid task. Must be one of: {valid_tasks}"
        }
    
    try:
        es_client = get_elasticsearch_client()
        
        # Normalize ID for lookup
        normalized_id = normalize_university_id(university_id)
        doc_id = f"{user_id}_{normalized_id}"
        
        # Get existing document
        try:
            existing = es_client.get(index=ES_LIST_ITEMS_INDEX, id=doc_id)
            current_tasks = existing['_source'].get('application_tasks', {})
        except:
            return {
                "success": False,
                "error": f"University {university_id} not found in your college list"
            }
        
        # Update the specific task
        current_tasks[task_name] = completed
        
        # Calculate progress percentage
        completed_count = sum(1 for v in current_tasks.values() if v)
        progress = int((completed_count / len(valid_tasks)) * 100)
        
        # Update document
        update_body = {
            "doc": {
                "application_tasks": current_tasks,
                "updated_at": datetime.utcnow().isoformat()
            }
        }
        
        es_client.update(index=ES_LIST_ITEMS_INDEX, id=doc_id, body=update_body, refresh=True)
        
        logger.info(f"[APPS] Updated task {task_name}={completed} for {user_id}/{university_id}")
        
        return {
            "success": True,
            "university_id": university_id,
            "task_name": task_name,
            "completed": completed,
            "application_tasks": current_tasks,
            "progress_percent": progress,
            "message": f"Task '{task_name}' {'completed' if completed else 'uncompleted'}"
        }
        
    except Exception as e:
        logger.error(f"[APPS] Update task error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_application_progress(user_id: str) -> dict:
    """
    Get aggregated application progress stats for the Overview view.
    
    Returns counts by status and overall completion percentages.
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Get all schools for user
        search_body = {
            "size": 500,
            "query": {"term": {"user_email": user_id}},
            "_source": ["university_id", "university_name", "application_status", 
                       "application_tasks", "application_plan"]
        }
        response = es_client.search(index=ES_LIST_ITEMS_INDEX, body=search_body)
        
        # Initialize counters
        status_counts = {'planning': 0, 'drafting': 0, 'submitted': 0, 'decision': 0}
        total_tasks_completed = 0
        total_tasks_possible = 0
        schools = []
        
        for hit in response['hits']['hits']:
            item = hit['_source']
            status = item.get('application_status', 'planning')
            tasks = item.get('application_tasks', {})
            
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count tasks
            completed = sum(1 for v in tasks.values() if v)
            total = len(tasks) or 10  # Default 10 tasks
            total_tasks_completed += completed
            total_tasks_possible += total
            
            schools.append({
                'university_id': item.get('university_id'),
                'university_name': item.get('university_name'),
                'application_status': status,
                'application_plan': item.get('application_plan'),
                'progress_percent': int((completed / total) * 100) if total > 0 else 0,
                'tasks_completed': completed,
                'tasks_total': total
            })
        
        return {
            "success": True,
            "total_schools": len(schools),
            "status_counts": status_counts,
            "overall_progress": int((total_tasks_completed / total_tasks_possible) * 100) if total_tasks_possible > 0 else 0,
            "schools": schools
        }
        
    except Exception as e:
        logger.error(f"[APPS] Get progress error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

def handle_get_college_list(request):
    """Get user's college list from the new separated index, enriched with university data."""
    try:
        # Support both GET params and POST body
        if request.method == 'GET':
            user_id = request.args.get('user_id') or request.args.get('user_email')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id') or data.get('user_email')
        
        if not user_id:
            user_id = request.headers.get('X-User-Email')
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Query the new separated list items index
        search_body = {
            "size": 500,  # Support up to 500 universities in list
            "query": {
                "term": {"user_email": user_id}
            },
            "sort": [{"added_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_LIST_ITEMS_INDEX, body=search_body)
        
        # Collect all university IDs from the list
        university_ids = []
        list_items = []
        for hit in response['hits']['hits']:
            item = hit['_source']
            uni_id = item.get('university_id')
            if uni_id:
                university_ids.append(uni_id)
            list_items.append(item)
        
        # Fetch university data from knowledge base to get soft_fit_category, etc.
        university_data = {}
        if university_ids:
            try:
                # Multi-get from university knowledge base index
                uni_response = es_client.search(
                    index='knowledgebase_universities',
                    body={
                        "size": len(university_ids),
                        "query": {
                            "terms": {"university_id": university_ids}
                        },
                        "_source": ["university_id", "official_name", "location", "acceptance_rate", 
                                   "soft_fit_category", "us_news_rank", "summary", "logo_url", "profile.logo_url"]
                    }
                )
                for hit in uni_response['hits']['hits']:
                    uni = hit['_source']
                    university_data[uni.get('university_id')] = {
                        'location': uni.get('location', {}),
                        'acceptance_rate': uni.get('acceptance_rate'),
                        'soft_fit_category': uni.get('soft_fit_category'),
                        'us_news_rank': uni.get('us_news_rank'),
                        'summary': uni.get('summary'),
                        'logo_url': uni.get('logo_url') or (uni.get('profile', {}).get('logo_url') if uni.get('profile') else None)
                    }
                logger.info(f"[GET_COLLEGE_LIST] Enriched {len(university_data)} universities with KB data")
            except Exception as e:
                logger.warning(f"[GET_COLLEGE_LIST] Could not fetch university KB data: {e}")
        
        # Convert individual docs to list items, enriched with university data
        college_list = []
        for item in list_items:
            uni_id = item.get('university_id')
            uni_info = university_data.get(uni_id, {})
            
            # Format location string
            location = uni_info.get('location', {})
            location_str = None
            if location:
                city = location.get('city', '')
                state = location.get('state', '')
                if city and state:
                    location_str = f"{city}, {state}"
                elif state:
                    location_str = state
            
            college_list.append({
                'university_id': uni_id,
                'university_name': item.get('university_name'),
                'status': item.get('status', 'favorites'),
                'order': item.get('order'),
                'added_at': item.get('added_at'),
                # NOTE: intended_major removed - always read from profile
                'notes': item.get('student_notes'),
                # Enriched fields from knowledge base
                'location': location_str,
                'acceptance_rate': uni_info.get('acceptance_rate'),
                'soft_fit_category': uni_info.get('soft_fit_category'),
                'us_news_rank': uni_info.get('us_news_rank'),
                'summary': uni_info.get('summary'),
                'logo_url': uni_info.get('logo_url')
            })
        
        return add_cors_headers({
            'success': True,
            'college_list': college_list,
            'count': len(college_list)
        }, 200)
        
    except Exception as e:
        logger.error(f"[GET_COLLEGE_LIST ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to get college list: {str(e)}'
        }, 500)


def handle_update_fit_analysis(request):
    """Update fit analysis for a college in user's list."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_id') or data.get('user_email')
        university_id = data.get('university_id')
        fit_analysis = data.get('fit_analysis')  # {fit_category, match_percentage, factors, recommendations}
        
        if not user_id or not university_id:
            return add_cors_headers({'error': 'User ID and University ID are required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Find user's profile document
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({'error': 'No profile found for user'}, 404)
        
        doc_id = response['hits']['hits'][0]['_id']
        current_doc = response['hits']['hits'][0]['_source']
        college_list = current_doc.get('college_list', [])
        
        # Find and update the specific college's fit analysis
        updated = False
        for college in college_list:
            if college.get('university_id') == university_id:
                college['fit_analysis'] = fit_analysis
                college['fit_analyzed_at'] = datetime.utcnow().isoformat()
                updated = True
                break
        
        if not updated:
            return add_cors_headers({'error': 'University not found in college list'}, 404)
        
        # Update document
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={"doc": {"college_list": college_list}}
        )
        
        logger.info(f"[ES] Updated fit analysis for {university_id} for user {user_id}")
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'fit_analysis': fit_analysis,
            'message': 'Fit analysis updated'
        }, 200)
        
    except Exception as e:
        logger.error(f"[FIT_ANALYSIS ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to update fit analysis: {str(e)}'
        }, 500)


def handle_compute_single_fit(request):
    """
    Compute fit analysis for a single university with caching.
    
    POST /compute-single-fit
    {
        "user_email": "student@gmail.com",
        "university_id": "harvard_university_slug",
        "force_recompute": false  // Optional: force recomputation even if cached
    }
    
    Returns:
    {
        "success": true,
        "university_id": "harvard_university_slug",
        "university_name": "Harvard University",
        "fit_analysis": {...},
        "from_cache": true/false
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_email') or data.get('user_id')
        university_id = data.get('university_id')
        intended_major = data.get('intended_major', '')
        force_recompute = data.get('force_recompute', False)
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        if not university_id:
            return add_cors_headers({'error': 'University ID is required'}, 400)
        
        logger.info(f"[COMPUTE_SINGLE_FIT] Request for {university_id} for user {user_id}, force={force_recompute}")
        
        # IMPORTANT: Lookup exact ES ID from Knowledge Base
        # Frontend may send cached lowercase IDs from precomputed fits
        requested_university_id = university_id
        try:
            kb_response = requests.get(
                f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}?university_id={university_id}",
                timeout=10
            )
            if kb_response.status_code == 200:
                kb_data = kb_response.json()
                if kb_data.get('success') and kb_data.get('university'):
                    exact_es_id = kb_data['university'].get('_id')
                    if exact_es_id and exact_es_id != university_id:
                        logger.info(f"[COMPUTE_SINGLE_FIT] Resolved exact ES ID: {exact_es_id} (was: {university_id})")
                        university_id = exact_es_id
        except Exception as e:
            logger.warning(f"[COMPUTE_SINGLE_FIT] Could not lookup exact ES ID: {e}")
        
        es_client = get_elasticsearch_client()
        
        # If intended_major not provided, get it from user's profile
        if not intended_major:
            # Get from flat profile field first, fallback to content extraction
            try:
                search_body = {
                    "size": 1,
                    "query": {"term": {"user_id.keyword": user_id}},
                    "_source": ["intended_major", "content"],
                    "sort": [{"indexed_at": {"order": "desc"}}]
                }
                response = es_client.search(index=ES_INDEX_NAME, body=search_body)
                if response['hits']['total']['value'] > 0:
                    profile_doc = response['hits']['hits'][0]['_source']
                    intended_major = profile_doc.get('intended_major', '')
                    if not intended_major:
                        # Fallback to extracting from content
                        intended_major = get_intended_major_from_profile(es_client, user_id)
                    logger.info(f"[COMPUTE_SINGLE_FIT] Auto-fetched intended_major from profile: '{intended_major}'")
            except Exception as e:
                logger.warning(f"[COMPUTE_SINGLE_FIT] Could not fetch intended_major: {e}")
        
        # Check credits before computing (skip for cache hits, handled below)
        skip_credit_check = data.get('skip_credit_check', False)  # For internal/batch calls
        credit_check = check_credits_available(user_id, 1)
        if not credit_check['has_credits'] and not skip_credit_check:
            return add_cors_headers({
                'success': False,
                'error': 'insufficient_credits',
                'message': 'You need more credits to run fit analysis',
                'credits_remaining': credit_check['credits_remaining'],
                'upgrade_required': True
            }, 402)  # 402 Payment Required
        
        email_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        doc_id = f"{email_hash}_{university_id}"
        
        # Check cache first (unless force_recompute is True)
        # Cache hits are FREE - no credit deducted
        if not force_recompute:
            try:
                cached = es_client.get(index=ES_FITS_INDEX, id=doc_id)
                cached_fit = cached['_source']
                logger.info(f"[COMPUTE_SINGLE_FIT] Cache HIT for {university_id}")
                
                # Deserialize JSON string fields back to objects
                def deserialize_field(value, default):
                    if value is None:
                        return default
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except:
                            return value
                    return value
                
                fit_analysis = {
                    'university_id': cached_fit.get('university_id'),
                    'university_name': cached_fit.get('university_name'),
                    'fit_category': cached_fit.get('fit_category'),
                    'match_percentage': cached_fit.get('match_score'),
                    'explanation': cached_fit.get('explanation'),
                    'factors': cached_fit.get('factors', []),
                    'recommendations': deserialize_field(cached_fit.get('recommendations'), []),
                    'gap_analysis': deserialize_field(cached_fit.get('gap_analysis'), {}),
                    'essay_angles': deserialize_field(cached_fit.get('essay_angles'), []),
                    'application_timeline': deserialize_field(cached_fit.get('application_timeline'), {}),
                    'scholarship_matches': deserialize_field(cached_fit.get('scholarship_matches'), []),
                    'test_strategy': deserialize_field(cached_fit.get('test_strategy'), {}),
                    'major_strategy': deserialize_field(cached_fit.get('major_strategy'), {}),
                    'demonstrated_interest_tips': deserialize_field(cached_fit.get('demonstrated_interest_tips'), []),
                    'red_flags_to_avoid': deserialize_field(cached_fit.get('red_flags_to_avoid'), []),
                    'computed_at': cached_fit.get('computed_at')
                }
                
                return add_cors_headers({
                    'success': True,
                    'university_id': university_id,
                    'university_name': fit_analysis.get('university_name', university_id),
                    'fit_analysis': fit_analysis,
                    'from_cache': True
                }, 200)
                
            except Exception as e:
                # Cache miss or error - proceed to compute
                logger.info(f"[COMPUTE_SINGLE_FIT] Cache MISS for {university_id}: {e}")
        
        # Compute fit analysis (LLM call)
        logger.info(f"[COMPUTE_SINGLE_FIT] Computing fit for {university_id}")
        fit_analysis = calculate_fit_for_college(user_id, university_id, intended_major)
        
        if not fit_analysis:
            return add_cors_headers({
                'success': False,
                'error': 'Failed to compute fit analysis',
                'university_id': university_id
            }, 500)
        
        # Deduct credit AFTER successful computation (cache miss)
        if not skip_credit_check:
            deduct_result = deduct_credit(user_id, 1, f"fit_analysis_{university_id}")
            if not deduct_result['success']:
                logger.warning(f"[CREDITS] Failed to deduct credit for {user_id}: {deduct_result}")
        
        logger.info(f"[COMPUTE_SINGLE_FIT] Result: {fit_analysis.get('fit_category')} ({fit_analysis.get('match_percentage')}%)")
        
        # Save to cache (ES_FITS_INDEX)
        def serialize_field(value, default='[]'):
            if value is None:
                return default
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            return str(value)
        
        fit_doc = {
            'user_email': user_id,
            'university_id': university_id,
            'university_name': fit_analysis.get('university_name'),
            'computed_at': datetime.utcnow().isoformat(),
            'fit_category': fit_analysis.get('fit_category'),
            'match_score': fit_analysis.get('match_percentage', fit_analysis.get('match_score')),
            'explanation': fit_analysis.get('explanation'),
            'factors': fit_analysis.get('factors', []),
            'recommendations': serialize_field(fit_analysis.get('recommendations', []), '[]'),
            'gap_analysis': serialize_field(fit_analysis.get('gap_analysis', {}), '{}'),
            'essay_angles': serialize_field(fit_analysis.get('essay_angles', []), '[]'),
            'application_timeline': serialize_field(fit_analysis.get('application_timeline', {}), '{}'),
            'scholarship_matches': serialize_field(fit_analysis.get('scholarship_matches', []), '[]'),
            'test_strategy': serialize_field(fit_analysis.get('test_strategy', {}), '{}'),
            'major_strategy': serialize_field(fit_analysis.get('major_strategy', {}), '{}'),
            'demonstrated_interest_tips': serialize_field(fit_analysis.get('demonstrated_interest_tips', []), '[]'),
            'red_flags_to_avoid': serialize_field(fit_analysis.get('red_flags_to_avoid', []), '[]'),
            'acceptance_rate': fit_analysis.get('acceptance_rate'),
            'us_news_rank': fit_analysis.get('us_news_rank'),
            'location': fit_analysis.get('location'),
            'market_position': fit_analysis.get('market_position')
        }
        
        try:
            es_client.index(index=ES_FITS_INDEX, id=doc_id, body=fit_doc)
            logger.info(f"[COMPUTE_SINGLE_FIT] Saved to cache: {doc_id}")
        except Exception as e:
            logger.warning(f"[COMPUTE_SINGLE_FIT] Failed to cache fit: {e}")
        
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'university_name': fit_analysis.get('university_name', university_id),
            'fit_analysis': fit_analysis,
            'from_cache': False
        }, 200)
        
    except Exception as e:
        logger.error(f"[COMPUTE_SINGLE_FIT ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to compute fit: {str(e)}'
        }, 500)


def handle_recalculate_all_fits(request):
    """Recalculate fit analysis for all colleges in user's list."""
    try:
        # Get user_id from request
        if request.method == 'GET':
            user_id = request.args.get('user_id') or request.args.get('user_email')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id') or data.get('user_email')
        
        if not user_id:
            user_id = request.headers.get('X-User-Email')
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Find user's profile
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({'error': 'No profile found for user'}, 404)
        
        doc_id = response['hits']['hits'][0]['_id']
        current_doc = response['hits']['hits'][0]['_source']
        
        college_list = current_doc.get('college_list', [])
        
        if not college_list:
            return add_cors_headers({
                'success': True,
                'message': 'No colleges in list to recalculate',
                'college_list': [],
                'count': 0
            }, 200)
        
        # Get intended_major from profile (not stored per-college)
        intended_major = get_intended_major_from_profile(es_client, user_id) or current_doc.get('intended_major', '')
        logger.info(f"[FIT] Using intended_major from profile: '{intended_major}'")
        
        # Recalculate fit for each college
        updated_count = 0
        for college in college_list:
            university_id = college.get('university_id')
            
            logger.info(f"[FIT] Recalculating fit for {university_id} with major='{intended_major}'")
            new_fit = calculate_fit_for_college(user_id, university_id, intended_major)
            
            if new_fit:
                college['fit_analysis'] = new_fit
                updated_count += 1
        
        # Update document
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={
                "doc": {
                    "college_list": college_list,
                    "fits_recalculated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"[FIT] Recalculated {updated_count} fits for user {user_id}")
        return add_cors_headers({
            'success': True,
            'message': f'Recalculated fit for {updated_count} colleges',
            'college_list': college_list,
            'count': updated_count
        }, 200)
        
    except Exception as e:
        logger.error(f"[RECALCULATE_FITS ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to recalculate fits: {str(e)}'
        }, 500)


# ============================================
# PRE-COMPUTED FIT MATRIX ENDPOINTS
# ============================================

KNOWLEDGE_BASE_UNIVERSITIES_URL = os.getenv(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)


def fetch_all_universities():
    """Fetch all universities from the knowledge base."""
    try:
        response = requests.get(f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}?action=list", timeout=30)
        data = response.json()
        
        if data.get('success'):
            return data.get('universities', [])
        else:
            logger.error(f"[KB] Failed to fetch universities: {data.get('error')}")
            return []
    except Exception as e:
        logger.error(f"[KB] Error fetching universities: {e}")
        return []


def fetch_university_profile(university_id, max_retries=3):
    """Fetch full university profile from knowledge base with retry logic."""
    # Note: time imported at module level
    
    # Build list of candidate IDs to try (handles variations in storage format)
    # IMPORTANT: Try the ORIGINAL ID first (preserves casing like University_of_Chicago)
    # Then try normalized/lowercased variants as fallbacks
    candidate_ids = []
    
    # FIRST: Try the exact original ID as provided (preserves casing)
    original_id = university_id.strip()
    candidate_ids.append(original_id)
    if not original_id.endswith('_slug'):
        candidate_ids.append(f"{original_id}_slug")
    
    # SECOND: Try lowercased variant
    base_id = university_id.lower().strip()
    
    # Remove _slug suffix if present for base processing
    if base_id.endswith('_slug'):
        base_id = base_id[:-5]
    
    # Original ID (with _slug variant)
    if not university_id.endswith('_slug'):
        candidate_ids.append(f"{university_id}_slug")
    candidate_ids.append(university_id)
    
    # Try hyphenated variants for location-based universities
    # e.g., university_of_wisconsin_madison -> university_of_wisconsin-madison
    # Common patterns: city/campus names after university name
    location_suffixes = ['madison', 'berkeley', 'austin', 'boulder', 'ann_arbor', 
                         'chapel_hill', 'los_angeles', 'new_brunswick', 'twin_cities',
                         'urbana_champaign', 'college_park', 'columbus', 'seattle']
    
    for suffix in location_suffixes:
        underscore_suffix = f"_{suffix}"
        hyphen_suffix = f"-{suffix}"
        if underscore_suffix in base_id:
            # Create hyphenated variant
            hyphenated_id = base_id.replace(underscore_suffix, hyphen_suffix)
            if hyphenated_id not in candidate_ids:
                candidate_ids.append(hyphenated_id)
                candidate_ids.append(f"{hyphenated_id}_slug")
    
    # Also try general underscore-to-hyphen for the last segment
    # e.g., rutgers_university_new_brunswick -> rutgers_university-new_brunswick
    parts = base_id.rsplit('_', 1)
    if len(parts) == 2 and len(parts[1]) > 3:
        hyphen_variant = f"{parts[0]}-{parts[1]}"
        if hyphen_variant not in candidate_ids:
            candidate_ids.append(hyphen_variant)
            candidate_ids.append(f"{hyphen_variant}_slug")
    
    logger.info(f"[KB] Trying candidate IDs for {university_id}: {candidate_ids[:5]}...")
    
    for uid in candidate_ids:
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}?university_id={uid}",
                    timeout=30
                )
                data = response.json()
                
                if data.get('success'):
                    uni_data = data.get('university')
                    if uni_data:  # Ensure it's not empty
                        logger.info(f"[KB] Found university with ID: {uid}")
                        return uni_data
                
                # If 404/not found, break retry loop and try next candidate ID
                if 'NotFoundError' in str(data.get('error', '')) or not data.get('success'):
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[KB] Error fetching {uid} (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                
            except Exception as e:
                logger.error(f"[KB] Unexpected error fetching {uid}: {e}")
                break
    
    logger.warning(f"[KB] University not found after trying all variants: {university_id}")
    return None


def handle_compute_all_fits(request):
    """
    Compute fit analysis for universities in batches.
    Supports incremental processing to avoid timeouts.
    
    POST /compute-all-fits
    {
        "user_email": "student@gmail.com",
        "batch_size": 10,      // Optional, default 10
        "offset": 0            // Optional, default 0
    }
    
    Returns:
    {
        "success": true,
        "computed": 10,
        "offset": 0,
        "batch_size": 10,
        "total_universities": 100,
        "has_more": true,
        "next_offset": 10,
        "fits_computed_at": "2024-12-10T22:00:00Z"
    }
    
    Client can orchestrate batches by calling with increasing offsets until has_more is false.
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_email') or data.get('user_id')
        batch_size = data.get('batch_size', 10)  # Default 10 universities per batch
        offset = data.get('offset', 0)  # Starting offset
        
        if not user_id:
            user_id = request.headers.get('X-User-Email')
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        
        # Validate batch_size
        if batch_size < 1:
            batch_size = 1
        elif batch_size > 50:
            batch_size = 50  # Cap at 50 to prevent timeouts
        
        logger.info(f"[COMPUTE_ALL_FITS] Starting batch for user {user_id}: offset={offset}, batch_size={batch_size}")
        
        es_client = get_elasticsearch_client()
        
        # Step 1: Get student profile
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({
                'success': False,
                'error': 'No profile found for user. Please upload a profile first.'
            }, 404)
        
        doc_id = response['hits']['hits'][0]['_id']
        profile_source = response['hits']['hits'][0]['_source']
        
        # Pass the ENTIRE student profile as JSON to the LLM
        fields_to_exclude = ['indexed_at', 'updated_at', 'created_at', '_id', 'embedding', 'chunk_id', 'user_id', 'college_fits']
        profile_data_clean = {k: v for k, v in profile_source.items() if k not in fields_to_exclude and v}
        
        profile_content = profile_source.get('content', '')
        
        # If content is empty (e.g., onboarding profiles), build from flat fields
        if not profile_content or len(profile_content.strip()) < 50:
            logger.info(f"[COMPUTE_ALL_FITS] Building profile content from flat fields for {user_id}")
            profile_content = build_profile_content_from_fields(profile_source)
        
        # Get existing computed fits (to merge with new batch)
        existing_fits_json = profile_source.get('college_fits', '{}')
        try:
            existing_fits = json.loads(existing_fits_json) if existing_fits_json else {}
        except:
            existing_fits = {}
        
        # Step 2: Get universities from USER'S COLLEGE LIST (from separate index)
        # The college list is stored in ES_LIST_ITEMS_INDEX, not in the profile doc
        list_search_body = {
            "size": 500,
            "query": {"term": {"user_email": user_id}},
            "sort": [{"added_at": {"order": "desc"}}]
        }
        
        list_response = es_client.search(index=ES_LIST_ITEMS_INDEX, body=list_search_body)
        
        if list_response['hits']['total']['value'] == 0:
            return add_cors_headers({
                'success': True,
                'computed': 0,
                'total_universities': 0,
                'has_more': False,
                'message': 'No universities in college list. Add universities first.'
            }, 200)
        
        # Build list of universities to compute fits for
        all_universities = []
        for hit in list_response['hits']['hits']:
            item = hit['_source']
            uni_id = item.get('university_id')
            uni_name = item.get('university_name', uni_id)
            if uni_id:
                all_universities.append({
                    'university_id': uni_id,
                    'official_name': uni_name,
                    'location': item.get('location', {}),
                    'acceptance_rate': item.get('acceptance_rate'),
                    'us_news_rank': item.get('us_news_rank'),
                    'market_position': item.get('market_position')
                })
        
        total_universities = len(all_universities)
        logger.info(f"[COMPUTE_ALL_FITS] Found {total_universities} universities in user's college list")
        
        # Step 3: Get the batch to process
        batch_universities = all_universities[offset:offset + batch_size]
        
        if not batch_universities:
            # No more universities to process
            return add_cors_headers({
                'success': True,
                'computed': 0,
                'offset': offset,
                'batch_size': batch_size,
                'total_universities': total_universities,
                'has_more': False,
                'message': 'All universities already processed'
            }, 200)
        
        logger.info(f"[COMPUTE_ALL_FITS] Processing batch: {len(batch_universities)} universities (offset {offset})")
        
        # Step 4: Compute fit for each university in batch
        batch_fits = {}
        computed_count = 0
        error_count = 0
        
        for uni_summary in batch_universities:
            university_id = uni_summary.get('university_id')
            
            try:
                # Fetch full profile for this university
                uni_profile = fetch_university_profile(university_id)
                
                if not uni_profile:
                    logger.warning(f"[COMPUTE_ALL_FITS] Could not fetch profile for {university_id}")
                    error_count += 1
                    continue
                
                # Calculate fit using PURE LLM reasoning
                # Pass full student profile JSON for complete context
                fit_analysis = calculate_fit_with_llm(profile_content, uni_profile, '', profile_data_clean)
                
                # Store computed fit with all 8 categories
                fit_result = {
                    'fit_category': fit_analysis.get('fit_category', 'UNKNOWN'),
                    'match_percentage': fit_analysis.get('match_percentage', 0),
                    'match_score': fit_analysis.get('match_percentage', 0),
                    'university_name': uni_summary.get('official_name', university_id),
                    'explanation': fit_analysis.get('explanation', ''),
                    'factors': fit_analysis.get('factors', []),
                    'gap_analysis': fit_analysis.get('gap_analysis', {}),
                    # 8 new recommendation categories
                    'recommendations': fit_analysis.get('recommendations', []),
                    'essay_angles': fit_analysis.get('essay_angles', []),
                    'application_timeline': fit_analysis.get('application_timeline', {}),
                    'scholarship_matches': fit_analysis.get('scholarship_matches', []),
                    'test_strategy': fit_analysis.get('test_strategy', {}),
                    'major_strategy': fit_analysis.get('major_strategy', {}),
                    'demonstrated_interest_tips': fit_analysis.get('demonstrated_interest_tips', []),
                    'red_flags_to_avoid': fit_analysis.get('red_flags_to_avoid', []),
                    # Metadata
                    'location': uni_summary.get('location', {}),
                    'acceptance_rate': uni_summary.get('acceptance_rate'),
                    'us_news_rank': uni_summary.get('us_news_rank'),
                    'market_position': uni_summary.get('market_position'),
                    'computed_at': datetime.utcnow().isoformat()
                }
                
                batch_fits[university_id] = fit_result
                computed_count += 1
                
                logger.info(f"[COMPUTE_ALL_FITS] [{offset + computed_count}/{total_universities}] {uni_summary.get('official_name', university_id)} -> {fit_analysis.get('fit_category')}")
                
                # Small delay to prevent API rate limiting
                time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"[COMPUTE_ALL_FITS] Error computing fit for {university_id}: {e}")
                error_count += 1
        
        # Step 5: Write each fit as individual document to ES_FITS_INDEX (new v2 architecture)
        email_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        fits_computed_at = datetime.utcnow().isoformat()
        
        for university_id, fit_result in batch_fits.items():
            doc_id = f"{email_hash}_{university_id}"
            
            # Serialize all complex nested objects as JSON strings for ES compatibility
            def serialize_field(value, default='[]'):
                if value is None:
                    return default
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                return str(value)
            
            fit_doc = {
                'user_email': user_id,
                'university_id': university_id,
                'university_name': fit_result.get('university_name'),
                'computed_at': fits_computed_at,
                'fit_category': fit_result.get('fit_category'),
                'match_score': fit_result.get('match_percentage', fit_result.get('match_score')),
                'explanation': fit_result.get('explanation'),
                'factors': fit_result.get('factors', []),
                # Core recommendations - serialized as JSON strings
                'recommendations': serialize_field(fit_result.get('recommendations', []), '[]'),
                'gap_analysis': serialize_field(fit_result.get('gap_analysis', {}), '{}'),
                # 8 new recommendation categories - all serialized as JSON strings
                'essay_angles': serialize_field(fit_result.get('essay_angles', []), '[]'),
                'application_timeline': serialize_field(fit_result.get('application_timeline', {}), '{}'),
                'scholarship_matches': serialize_field(fit_result.get('scholarship_matches', []), '[]'),
                'test_strategy': serialize_field(fit_result.get('test_strategy', {}), '{}'),
                'major_strategy': serialize_field(fit_result.get('major_strategy', {}), '{}'),
                'demonstrated_interest_tips': serialize_field(fit_result.get('demonstrated_interest_tips', []), '[]'),
                'red_flags_to_avoid': serialize_field(fit_result.get('red_flags_to_avoid', []), '[]'),
                # Metadata
                'acceptance_rate': fit_result.get('acceptance_rate'),
                'us_news_rank': fit_result.get('us_news_rank'),
                'location': fit_result.get('location'),
                'market_position': fit_result.get('market_position')
            }
            es_client.index(index=ES_FITS_INDEX, id=doc_id, body=fit_doc)
        
        logger.info(f"[COMPUTE_ALL_FITS] Saved {len(batch_fits)} fits to ES_FITS_INDEX")
        
        # Calculate if there are more batches
        next_offset = offset + batch_size
        has_more = next_offset < total_universities
        
        logger.info(f"[COMPUTE_ALL_FITS] Batch complete: {computed_count} computed, {error_count} errors, has_more={has_more}")
        
        return add_cors_headers({
            'success': True,
            'computed': computed_count,
            'errors': error_count,
            'offset': offset,
            'batch_size': batch_size,
            'total_universities': total_universities,
            'total_computed': len(batch_fits),
            'has_more': has_more,
            'next_offset': next_offset if has_more else None,
            'fits_computed_at': fits_computed_at,
            'message': f'Computed fit for {computed_count} universities (batch {offset // batch_size + 1})'
        }, 200)
        
    except Exception as e:
        logger.error(f"[COMPUTE_ALL_FITS ERROR] {str(e)}", exc_info=True)
        return add_cors_headers({
            'success': False,
            'error': f'Failed to compute fits: {str(e)}'
        }, 500)


# --- Fit Chat with Context Injection ---
def fit_chat(user_id: str, university_id: str, question: str, conversation_history: list = None) -> dict:
    """
    Chat about a specific fit analysis using profile + fit data as context.
    Uses gemini-2.5-flash-lite with context injection.
    
    Args:
        user_id: The user's email
        university_id: The university ID to chat about
        question: User's question
        conversation_history: List of {role, content} dicts for context
    
    Returns:
        dict with answer and updated conversation history
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        es_client = get_elasticsearch_client()
        
        # Load user profile
        profile_query = {
            "query": {"term": {"user_id.keyword": user_id}},
            "size": 1
        }
        profile_response = es_client.search(index=ES_INDEX_NAME, body=profile_query)
        
        if profile_response['hits']['total']['value'] == 0:
            return {
                "success": False,
                "error": "User profile not found"
            }
        
        user_profile = profile_response['hits']['hits'][0]['_source']
        
        # Load fit analysis for this university
        # Match the ID format exactly as stored (same pattern as handle_get_fits)
        normalized_uni_id = normalize_university_id(university_id)
        
        # Query matching handle_get_fits pattern - use fields without .keyword
        fit_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"user_email": user_id}}
                    ],
                    "should": [
                        {"term": {"university_id": university_id}},
                        {"term": {"university_id": normalized_uni_id}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 1
        }
        
        logger.info(f"[FIT_CHAT] Querying ES with user_email={user_id}, university_id={university_id}, normalized={normalized_uni_id}")
        fit_response = es_client.search(index=ES_FITS_INDEX, body=fit_query)
        
        if fit_response['hits']['total']['value'] == 0:
            logger.warning(f"[FIT_CHAT] No fit found for user={user_id}, uni_id={university_id}, normalized={normalized_uni_id}")
            return {
                "success": False,
                "error": f"No fit analysis found for {university_id}. Please run a fit analysis first."
            }
        
        fit_data = fit_response['hits']['hits'][0]['_source']
        university_name = fit_data.get('university_name', university_id)
        
        # Build context with profile and fit data
        # Pass the ENTIRE user profile as-is - no need to extract specific fields
        # The profile is already JSON from Elasticsearch
        profile_summary = user_profile
        
        # Remove internal/metadata fields that aren't useful for the LLM
        fields_to_exclude = ['indexed_at', 'updated_at', 'created_at', '_id', 'embedding', 'chunk_id']
        profile_summary = {k: v for k, v in profile_summary.items() if k not in fields_to_exclude and v}
        
        # Extract key fit fields
        fit_summary = {
            "university_name": university_name,
            "fit_category": fit_data.get("fit_category"),
            "match_score": fit_data.get("match_score"),
            "acceptance_rate": fit_data.get("acceptance_rate"),
            "us_news_rank": fit_data.get("us_news_rank"),
            "gap_analysis": fit_data.get("gap_analysis"),
            "recommendations": fit_data.get("recommendations"),
            "detailed_analysis": fit_data.get("detailed_analysis"),
        }
        
        # Fetch university profile from knowledge base for additional context (majors, programs, etc.)
        university_profile = fetch_university_profile(university_id)
        university_summary = {}
        if university_profile:
            profile_data = university_profile.get('profile', university_profile)
            academic = profile_data.get('academic_structure', {})
            
            # Extract colleges and majors
            colleges_info = []
            for college in academic.get('colleges', []):
                college_majors = []
                for major in college.get('majors', []):
                    if isinstance(major, dict):
                        college_majors.append(major.get('name', str(major)))
                    else:
                        college_majors.append(str(major))
                colleges_info.append({
                    "name": college.get('name', 'Unknown'),
                    "majors": college_majors
                })
            
            # Pass ENTIRE university profile as context (same approach as calculate_fit_with_llm)
            # This ensures chat has access to ALL data including SAT ranges, admissions stats, etc.
            university_summary = profile_data
            logger.info(f"[FIT_CHAT] Loaded FULL university profile with {len(colleges_info)} colleges")
        else:
            logger.warning(f"[FIT_CHAT] Could not fetch university profile for {university_id}")
        
        profile_json = json.dumps(profile_summary, indent=2, default=str)
        fit_json = json.dumps(fit_summary, indent=2, default=str)
        university_json = json.dumps(university_summary, indent=2, default=str) if university_summary else "Not available"
        
        system_prompt = f"""You are a college admissions advisor helping a student understand their fit with {university_name}. Answer questions using ONLY the data provided below.

STUDENT PROFILE:
{profile_json}

FIT ANALYSIS FOR {university_name}:
{fit_json}

UNIVERSITY INFORMATION (Colleges, Majors, Programs):
{university_json}

RULES:
- Base answers on the data provided above
- When asked about majors/programs, use the UNIVERSITY INFORMATION section
- Explain factors affecting the fit score
- Give actionable advice when asked
- Be encouraging but realistic
- Format responses in markdown when helpful
- If information is not in the data, say so honestly

SUGGESTED QUESTIONS:
Also provide 3 suggested follow-up questions that would be most useful for this student to ask next.
"Useful" means:
1. Helps the student understand their admission chances specifically
2. Explores academic fit (majors, classes) or social fit
3. Finds actionable steps to improve their application
IMPORTANT: Keep questions short and concise (max 15 words).

RESPONSE FORMAT:
Return a JSON object with this structure:
{{
  "answer": "your markdown answer here...",
  "suggested_questions": ["question 1", "question 2", "question 3"]
}}
"""
        
        # Build conversation for Gemini
        contents = []
        
        # Add system context
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=system_prompt)]
        ))
        
        # Add conversation history
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            # Skip tool outputs/empty messages
            if not content:
                continue
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=content)]
            ))
        
        # Add current question
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=question)]
        ))
        
        # Call Gemini with JSON mode
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        
        # Parse JSON response
        try:
            response_data = json.loads(response.text)
            answer = response_data.get("answer", response.text)
            suggested_questions = response_data.get("suggested_questions", [])
        except json.JSONDecodeError:
            # Fallback if model fails to return JSON
            logger.warning("[FIT_CHAT] Model failed to return valid JSON, using raw text")
            answer = response.text
            suggested_questions = []

        # Update history - keep only text content for history
        updated_history = conversation_history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        logger.info(f"[FIT_CHAT] Q: '{question[:30]}...' -> A: {len(answer)} chars, Suggestions: {len(suggested_questions)}")
        
        return {
            "success": True,
            "answer": answer,
            "suggested_questions": suggested_questions,
            "conversation_history": updated_history,
            "university_name": university_name,
            "university_id": university_id
        }
        
    except Exception as e:
        logger.error(f"Fit chat failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# FIT CHAT CONVERSATION HISTORY FUNCTIONS
# ============================================

def save_fit_chat_conversation(user_id: str, university_id: str, university_name: str, 
                               messages: list, conversation_id: str = None, title: str = None) -> dict:
    """
    Save or update a fit chat conversation.
    
    Args:
        user_id: The user's email
        university_id: The university ID
        university_name: The university display name
        messages: List of {role, content} message dicts
        conversation_id: Optional existing ID to update (None creates new)
        title: Optional conversation title (auto-generated if not provided)
    
    Returns:
        dict with success status and conversation_id
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"{user_id}_{university_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Auto-generate title from first user message if not provided
        if not title and messages:
            for msg in messages:
                if msg.get('role') == 'user':
                    first_question = msg.get('content', '')[:50]
                    title = first_question + ('...' if len(msg.get('content', '')) > 50 else '')
                    break
        
        if not title:
            title = f"Chat with {university_name}"
        
        # Build document
        doc = {
            "user_email": user_id,
            "university_id": university_id,
            "university_name": university_name,
            "conversation_id": conversation_id,
            "title": title,
            "messages": json.dumps(messages),
            "message_count": len(messages),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Check if updating existing
        doc_id = conversation_id
        try:
            existing = es_client.get(index=ES_CHAT_CONVERSATIONS_INDEX, id=doc_id)
            # Preserve original created_at
            doc["created_at"] = existing['_source'].get('created_at', doc["created_at"])
        except:
            pass  # New document
        
        # Save to ES
        es_client.index(index=ES_CHAT_CONVERSATIONS_INDEX, id=doc_id, body=doc)
        
        logger.info(f"[CHAT_HISTORY] Saved conversation {conversation_id} for {user_id}/{university_id}")
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "title": title
        }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] Save failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def list_fit_chat_conversations(user_id: str, university_id: str = None, limit: int = 20) -> dict:
    """
    List saved conversations for a user, optionally filtered by university.
    
    Args:
        user_id: The user's email
        university_id: Optional filter by university
        limit: Max conversations to return
    
    Returns:
        dict with success status and conversations list
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Build query - use .keyword for exact matching on text fields
        must_clauses = [{"term": {"user_email.keyword": user_id}}]
        if university_id:
            must_clauses.append({"term": {"university_id.keyword": university_id}})
        
        search_body = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"updated_at": {"order": "desc"}}],
            "size": limit,
            "_source": ["conversation_id", "university_id", "university_name", "title", 
                       "message_count", "created_at", "updated_at"]
        }
        
        response = es_client.search(index=ES_CHAT_CONVERSATIONS_INDEX, body=search_body)
        
        conversations = []
        for hit in response['hits']['hits']:
            conv = hit['_source']
            conversations.append({
                "conversation_id": conv.get("conversation_id"),
                "university_id": conv.get("university_id"),
                "university_name": conv.get("university_name"),
                "title": conv.get("title"),
                "message_count": conv.get("message_count", 0),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at")
            })
        
        logger.info(f"[CHAT_HISTORY] Listed {len(conversations)} conversations for {user_id}")
        
        return {
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] List failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "conversations": []
        }


def load_fit_chat_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Load a specific conversation by ID.
    
    Args:
        user_id: The user's email (for ownership verification)
        conversation_id: The conversation ID to load
    
    Returns:
        dict with success status and full conversation data
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Get by ID
        try:
            result = es_client.get(index=ES_CHAT_CONVERSATIONS_INDEX, id=conversation_id)
        except:
            return {
                "success": False,
                "error": "Conversation not found"
            }
        
        conversation = result['_source']
        
        # Verify ownership
        if conversation.get("user_email") != user_id:
            return {
                "success": False,
                "error": "Not authorized to access this conversation"
            }
        
        # Parse messages
        messages = []
        try:
            messages = json.loads(conversation.get("messages", "[]"))
        except:
            pass
        
        logger.info(f"[CHAT_HISTORY] Loaded conversation {conversation_id} for {user_id}")
        
        return {
            "success": True,
            "conversation": {
                "conversation_id": conversation.get("conversation_id"),
                "university_id": conversation.get("university_id"),
                "university_name": conversation.get("university_name"),
                "title": conversation.get("title"),
                "messages": messages,
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at")
            }
        }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] Load failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def delete_fit_chat_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Delete a conversation by ID.
    
    Args:
        user_id: The user's email (for ownership verification)
        conversation_id: The conversation ID to delete
    
    Returns:
        dict with success status
    """
    try:
        es_client = get_elasticsearch_client()
        
        # First verify ownership
        try:
            result = es_client.get(index=ES_CHAT_CONVERSATIONS_INDEX, id=conversation_id)
            if result['_source'].get("user_email") != user_id:
                return {
                    "success": False,
                    "error": "Not authorized to delete this conversation"
                }
        except:
            return {
                "success": False,
                "error": "Conversation not found"
            }
        
        # Delete
        es_client.delete(index=ES_CHAT_CONVERSATIONS_INDEX, id=conversation_id)
        
        logger.info(f"[CHAT_HISTORY] Deleted conversation {conversation_id} for {user_id}")
        
        return {
            "success": True,
            "deleted": conversation_id
        }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] Delete failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

def handle_get_fits(request):
    """
    Get pre-computed fits for a user from the new separated fits index.
    
    POST /get-fits
    {
        "user_email": "student@gmail.com",
        "filters": {
            "category": "SAFETY",      // Optional: SAFETY, TARGET, REACH, SUPER_REACH
            "state": "CA",             // Optional: state filter
            "exclude_ids": ["ucsd"]    // Optional: exclude these ids
        },
        "limit": 10,
        "sort_by": "rank"              // "rank" or "match_score"
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_email') or data.get('user_id')
        filters = data.get('filters', {})
        limit = data.get('limit', 500)  # Default to all fits
        sort_by = data.get('sort_by', 'rank')
        
        if not user_id:
            user_id = request.headers.get('X-User-Email')
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Build query for the fits index
        must_clauses = [{"term": {"user_email": user_id}}]
        
        # Apply filters directly in ES query
        category_filter = filters.get('category', '').upper() if filters.get('category') else None
        if category_filter:
            must_clauses.append({"term": {"fit_category": category_filter}})
        
        exclude_ids = filters.get('exclude_ids', [])
        must_not_clauses = []
        if exclude_ids:
            # Normalize exclude IDs for consistent matching
            normalized_exclude_ids = [normalize_university_id(uid) for uid in exclude_ids]
            must_not_clauses.append({"terms": {"university_id": normalized_exclude_ids}})
        
        # If state filter is present, fetch more to account for client-side filtering
        state_filter_present = bool(filters.get('state'))
        fetch_size = limit * 10 if state_filter_present else limit  # Fetch more to filter client-side
        
        search_body = {
            "size": min(fetch_size, 200),  # Cap at 200 to avoid excessive fetches
            "query": {
                "bool": {
                    "must": must_clauses,
                    "must_not": must_not_clauses
                }
            }
        }
        
        # Add sort
        if sort_by == 'rank':
            search_body["sort"] = [{"us_news_rank": {"order": "asc", "missing": "_last"}}]
        elif sort_by == 'match_score':
            search_body["sort"] = [{"match_score": {"order": "desc"}}]
        
        response = es_client.search(index=ES_FITS_INDEX, body=search_body)
        
        # Convert ES hits to results
        results = []
        for hit in response['hits']['hits']:
            fit = hit['_source']
            
            # Apply state filter (if present, do client-side since location is nested)
            state_filter = filters.get('state', '').upper() if filters.get('state') else None
            if state_filter:
                location = fit.get('location', {})
                state_value = location.get('state', '').upper()
                # Handle common abbreviation variations
                state_abbrev_map = {
                    'CALIFORNIA': 'CA', 'CA': 'CA',
                    'NEW YORK': 'NY', 'NY': 'NY',
                    'MASSACHUSETTS': 'MA', 'MA': 'MA',
                    'TEXAS': 'TX', 'TX': 'TX',
                    'FLORIDA': 'FL', 'FL': 'FL',
                    'PENNSYLVANIA': 'PA', 'PA': 'PA',
                    'OHIO': 'OH', 'OH': 'OH',
                    'WASHINGTON': 'WA', 'WA': 'WA',
                    'NORTH CAROLINA': 'NC', 'NC': 'NC',
                    'NEW JERSEY': 'NJ', 'NJ': 'NJ',
                    'COLORADO': 'CO', 'CO': 'CO',
                    'NEBRASKA': 'NE', 'NE': 'NE',
                }
                normalized_filter = state_abbrev_map.get(state_filter, state_filter)
                normalized_value = state_abbrev_map.get(state_value, state_value)
                if normalized_value != normalized_filter:
                    continue
            
            # Parse recommendations - may be JSON string (new format) or array (old format)
            recommendations = fit.get('recommendations', [])
            if isinstance(recommendations, str):
                try:
                    recommendations = json.loads(recommendations)
                except json.JSONDecodeError:
                    recommendations = []
            
            # Parse gap_analysis - may be JSON string (new format) or dict (old format)
            gap_analysis = fit.get('gap_analysis', {})
            if isinstance(gap_analysis, str):
                try:
                    gap_analysis = json.loads(gap_analysis)
                except json.JSONDecodeError:
                    gap_analysis = {}
            
            # Helper to parse JSON string fields for all 8 categories
            def parse_json_field(field_name, default):
                value = fit.get(field_name, default)
                if isinstance(value, str):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return default
                return value if value is not None else default
            
            results.append({
                'university_id': fit.get('university_id'),  # Use EXACT ES ID (no normalization)
                'university_name': fit.get('university_name'),
                'fit_category': fit.get('fit_category'),
                'match_score': fit.get('match_score'),
                'explanation': fit.get('explanation'),
                'factors': fit.get('factors', []),
                'recommendations': recommendations,
                'gap_analysis': gap_analysis,
                # 8 new recommendation categories
                'essay_angles': parse_json_field('essay_angles', []),
                'application_timeline': parse_json_field('application_timeline', {}),
                'scholarship_matches': parse_json_field('scholarship_matches', []),
                'test_strategy': parse_json_field('test_strategy', {}),
                'major_strategy': parse_json_field('major_strategy', {}),
                'demonstrated_interest_tips': parse_json_field('demonstrated_interest_tips', []),
                'red_flags_to_avoid': parse_json_field('red_flags_to_avoid', []),
                # Metadata
                'acceptance_rate': fit.get('acceptance_rate'),
                'us_news_rank': fit.get('us_news_rank'),
                'location': fit.get('location'),
                'market_position': fit.get('market_position'),
                'computed_at': fit.get('computed_at')
            })
        
        # Apply limit after filtering (important when state filter expands fetch size)
        results = results[:limit]
        
        # --- SOFT FIT FALLBACK ---
        # If no precomputed fits found AND category filter is present,
        # fall back to fetching universities by soft_fit_category from knowledge base API
        is_soft_fit_fallback = False
        soft_fit_error = None
        if len(results) == 0 and category_filter:
            try:
                import requests
                logger.info(f"[GET_FITS] No precomputed fits found, falling back to soft_fit_category API for {category_filter}")
                
                # Call the knowledge-base-manager-universities API (GET returns all universities)
                KB_UNIVERSITIES_URL = os.environ.get('KB_UNIVERSITIES_URL', 'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app')
                api_response = requests.get(KB_UNIVERSITIES_URL, timeout=30)
                api_response.raise_for_status()
                api_data = api_response.json()
                
                if api_data.get('success') and api_data.get('universities'):
                    # Filter by soft_fit_category on client side
                    matching_unis = [
                        uni for uni in api_data['universities']
                        if uni.get('soft_fit_category') == category_filter
                    ]
                    
                    # Apply exclude_ids filter  
                    if exclude_ids:
                        normalized_exclude = set(normalize_university_id(uid) for uid in exclude_ids)
                        matching_unis = [
                            uni for uni in matching_unis
                            if normalize_university_id(uni.get('university_id', '')) not in normalized_exclude
                        ]
                    
                    # Apply state filter if present
                    state_filter = filters.get('state', '').upper() if filters.get('state') else None
                    if state_filter:
                        matching_unis = [
                            uni for uni in matching_unis
                            if isinstance(uni.get('location'), dict) and 
                               state_filter in uni.get('location', {}).get('state', '').upper()
                        ]
                    
                    # Sort by US News rank (ascending, nulls last)
                    matching_unis.sort(key=lambda x: (x.get('us_news_rank') is None, x.get('us_news_rank') or 999))
                    
                    # Apply limit
                    matching_unis = matching_unis[:limit]
                    
                    logger.info(f"[GET_FITS] Found {len(matching_unis)} universities with soft_fit_category={category_filter}")
                    
                    for uni in matching_unis:
                        location = uni.get('location', {})
                        results.append({
                            'university_id': uni.get('university_id'),  # Use EXACT ES ID
                            'university_name': uni.get('official_name'),
                            'fit_category': uni.get('soft_fit_category'),
                            'match_score': None,  # No personalized score for soft fits
                            'explanation': f"Based on acceptance rate ({uni.get('acceptance_rate')}%)",
                            'factors': [],
                            'recommendations': [],
                            'gap_analysis': {},
                            'essay_angles': [],
                            'application_timeline': {},
                            'scholarship_matches': [],
                            'test_strategy': {},
                            'major_strategy': {},
                            'demonstrated_interest_tips': [],
                            'red_flags_to_avoid': [],
                            'acceptance_rate': uni.get('acceptance_rate'),
                            'us_news_rank': uni.get('us_news_rank'),
                            'location': location,
                            'market_position': uni.get('market_position'),
                            'is_soft_fit': True  # Flag to indicate this is acceptance-rate based
                        })
                    
                    is_soft_fit_fallback = len(results) > 0
                else:
                    logger.warning(f"[GET_FITS] Knowledge base API returned no universities")
                
            except Exception as fallback_err:
                logger.error(f"[GET_FITS] Soft fit fallback error: {fallback_err}")
                soft_fit_error = str(fallback_err)
        
        return add_cors_headers({
            'success': True,
            'results': results,
            'total': response['hits']['total']['value'] if not is_soft_fit_fallback else len(results),
            'returned': len(results),
            'fits_ready': len(results) > 0,
            'is_soft_fit_fallback': is_soft_fit_fallback,
            'fallback_attempted': len(results) == 0 and category_filter is not None,
            'soft_fit_error': soft_fit_error if 'soft_fit_error' in dir() else None,
            'filters_applied': filters
        }, 200)
        
    except Exception as e:
        logger.error(f"[GET_FITS ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to get fits: {str(e)}'
        }, 500)


def handle_update_profile(request):
    """Update the student's profile content and structured JSON.
    
    Updates BOTH:
    - content: The markdown representation
    - structured_profile: The JSON for ProfileViewCard display
    
    Expects the caller (agent) to provide the complete updated markdown content.
    The structured_profile is automatically re-extracted from the updated content.
    """
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_id') or data.get('user_email')
        content = data.get('content')  # Full updated markdown content
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        if not content:
            return add_cors_headers({'error': 'Content is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Find user's profile document
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({'error': 'No profile found for user'}, 404)
        
        doc_id = response['hits']['hits'][0]['_id']
        
        # Re-extract structured profile from updated content
        logger.info(f"[UPDATE_PROFILE] Re-extracting structured profile for {user_id}")
        structured_profile = None
        extraction_error = None
        try:
            structured_profile = extract_structured_profile_with_gemini(content)
            logger.info(f"[UPDATE_PROFILE] Extracted structured profile with {len(structured_profile.get('extracurriculars', []))} activities")
        except Exception as extract_err:
            extraction_error = str(extract_err)
            logger.warning(f"[UPDATE_PROFILE] Could not extract structured profile: {extract_err}")
        
        # Build update document - always update content, optionally update structured_profile
        update_doc = {
            "content": content,
            "content_updated_at": datetime.utcnow().isoformat()
        }
        
        if structured_profile:
            update_doc["structured_profile"] = structured_profile
        
        # Update both fields in ES
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={"doc": update_doc}
        )
        
        # Build response message based on what was updated
        if structured_profile:
            message = 'Successfully updated profile (content and structured data)'
        else:
            message = 'Updated profile content, but structured data could not be refreshed'
        
        logger.info(f"[UPDATE_PROFILE] Updated content + structured_profile for user {user_id}")
        return add_cors_headers({
            'success': True,
            'message': message,
            'structured_profile_updated': structured_profile is not None,
            'extraction_error': extraction_error
        }, 200)
        
    except Exception as e:
        logger.error(f"[UPDATE_PROFILE ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to update profile: {str(e)}'
        }, 500)


def handle_update_structured_field(request):
    """Update a specific field in the structured_profile JSON directly.
    
    This is the SAFE way to update profile fields - no risk of data loss.
    
    Expected request body:
    {
        "user_email": "user@example.com",
        "field_path": "test_scores.sat.total",  # Dot-notation path
        "value": 1500,  # New value (any JSON type)
        "operation": "set"  # Optional: "set", "append", "remove" (default: "set")
    }
    """
    
    # SECURITY: Allowlist of valid FLAT field paths (no nested paths)
    ALLOWED_FIELD_PATHS = {
        # Scalar fields (set operation)
        "gpa_weighted",
        "gpa_unweighted", 
        "gpa_uc",
        "class_rank",
        "sat_total",
        "sat_math",
        "sat_reading",
        "act_composite",
        "intended_major",
        "name",
        "school",
        "location",
        "grade",
        "graduation_year",
        # Array fields (append/remove operations)
        "extracurriculars",
        "awards",
        "courses",
        "leadership_roles",
        "special_programs",
        "work_experience",
        "ap_exams"
    }
    
    # Type coercion map for data integrity (flat field names)
    TYPE_COERCION = {
        "gpa_weighted": float,
        "gpa_unweighted": float,
        "gpa_uc": float,
        "sat_total": int,
        "sat_math": int,
        "sat_reading": int,
        "act_composite": int,
        "graduation_year": int,
        "grade": int,
    }
    
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_id') or data.get('user_email')
        field_path = data.get('field_path')
        value = data.get('value')
        operation = data.get('operation', 'set')  # set, append, remove
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        if not field_path:
            return add_cors_headers({'error': 'Field path is required'}, 400)
        if value is None and operation == 'set':
            return add_cors_headers({'error': 'Value is required for set operation'}, 400)
        
        # SECURITY: Validate field path against allowlist
        if field_path not in ALLOWED_FIELD_PATHS:
            logger.warning(f"[UPDATE_STRUCTURED_FIELD] Rejected invalid field path: {field_path}")
            return add_cors_headers({
                'error': f'Invalid field path: {field_path}',
                'allowed_paths': list(ALLOWED_FIELD_PATHS)
            }, 400)
        
        # Type coercion for scalar values
        if field_path in TYPE_COERCION and value is not None:
            try:
                value = TYPE_COERCION[field_path](value)
            except (ValueError, TypeError) as e:
                return add_cors_headers({
                    'error': f'Invalid value type for {field_path}',
                    'message': f'Expected {TYPE_COERCION[field_path].__name__}, got {type(value).__name__}'
                }, 400)
        
        # Validate operation
        if operation not in ('set', 'append', 'remove', 'remove_at'):
            return add_cors_headers({'error': f'Invalid operation: {operation}'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Find user's profile document
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({'error': 'No profile found for user'}, 404)
        
        doc = response['hits']['hits'][0]
        doc_id = doc['_id']
        doc_source = doc['_source']
        
        # Get old value (flat field - direct access)
        old_value = doc_source.get(field_path)
        
        # Prepare update based on operation
        if operation == 'set':
            new_value = value
        elif operation == 'append':
            # Append to array
            current_array = doc_source.get(field_path, [])
            if not isinstance(current_array, list):
                current_array = [current_array] if current_array else []
            current_array.append(value)
            new_value = current_array
        elif operation == 'remove':
            # Remove from array by value/name match
            current_array = doc_source.get(field_path, [])
            if isinstance(current_array, list):
                if isinstance(value, dict) and 'name' in value:
                    # Match by name for dict items
                    new_value = [item for item in current_array 
                                if not (isinstance(item, dict) and item.get('name') == value.get('name'))]
                else:
                    new_value = [item for item in current_array if item != value]
            else:
                new_value = current_array
        elif operation == 'remove_at':
            # Remove from array by index
            current_array = doc_source.get(field_path, [])
            if isinstance(current_array, list) and isinstance(value, int):
                index = value
                if 0 <= index < len(current_array):
                    removed_item = current_array[index]
                    new_value = current_array[:index] + current_array[index + 1:]
                    logger.info(f"[UPDATE_STRUCTURED_FIELD] Removed item at index {index} from {field_path}: {removed_item}")
                else:
                    return add_cors_headers({'error': f'Index {index} out of range for array of length {len(current_array)}'}, 400)
            else:
                return add_cors_headers({'error': 'remove_at requires array field and integer index'}, 400)
        else:
            return add_cors_headers({'error': f'Unknown operation: {operation}'}, 400)
        
        # Update ES with the flat field directly
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={
                "doc": {
                    field_path: new_value,
                    "updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"[UPDATE_STRUCTURED_FIELD] Updated {field_path}: {old_value} -> {value} for {user_id}")
        
        # IMPORTANT: Trigger fit recalculation if a "fit-affecting" field was updated
        FIT_AFFECTING_FIELDS = {
            'intended_major', 'gpa_weighted', 'gpa_unweighted', 'sat_total', 
            'sat_math', 'sat_reading', 'act_composite', 'extracurriculars', 
            'awards', 'courses', 'ap_exams', 'leadership_roles'
        }
        
        fit_recomputation_results = []
        if field_path in FIT_AFFECTING_FIELDS:
            logger.info(f"[UPDATE_STRUCTURED_FIELD] Fit-affecting field '{field_path}' updated - triggering SYNCHRONOUS fit recomputation for {user_id}")
            try:
                # Get user's college list from the document we already have
                college_list = doc_source.get('college_list', [])
                if college_list:
                    # Limit to first 10 universities to keep response time reasonable
                    MAX_RECOMPUTE = 10
                    universities_to_recompute = college_list[:MAX_RECOMPUTE]
                    logger.info(f"[FIT_RECOMPUTE] Recomputing fits for {len(universities_to_recompute)} universities (max {MAX_RECOMPUTE})")
                    
                    # Get intended_major from profile (never stored per-college)
                    if field_path == 'intended_major':
                        # Use the newly updated value
                        intended_major_for_fit = new_value if new_value else ''
                    else:
                        # Use profile's top-level intended_major field
                        intended_major_for_fit = doc_source.get('intended_major', '')
                    logger.info(f"[FIT_RECOMPUTE] Using intended_major from profile: '{intended_major_for_fit}'")
                    
                    for college in universities_to_recompute:
                        university_id = college.get('university_id')
                        if university_id:
                            try:
                                logger.info(f"[FIT_RECOMPUTE] Recomputing fit for {university_id}")
                                result = calculate_fit_for_college(user_id, university_id, intended_major_for_fit)
                                if result:
                                    fit_recomputation_results.append({
                                        'university_id': university_id,
                                        'success': True,
                                        'fit_category': result.get('fit_category')
                                    })
                                else:
                                    fit_recomputation_results.append({
                                        'university_id': university_id,
                                        'success': False,
                                        'error': 'No result returned'
                                    })
                            except Exception as fit_err:
                                logger.warning(f"[FIT_RECOMPUTE] Error recomputing {university_id}: {fit_err}")
                                fit_recomputation_results.append({
                                    'university_id': university_id,
                                    'success': False,
                                    'error': str(fit_err)
                                })
                    
                    logger.info(f"[FIT_RECOMPUTE] Completed fit recomputation for {len(fit_recomputation_results)} universities")
                else:
                    logger.info(f"[FIT_RECOMPUTE] No college list found for user {user_id}")
            except Exception as recompute_err:
                logger.warning(f"[UPDATE_STRUCTURED_FIELD] Could not trigger fit recomputation: {recompute_err}")
        
        return add_cors_headers({
            'success': True,
            'message': f'Successfully updated {field_path}',
            'field_path': field_path,
            'old_value': old_value,
            'new_value': value,
            'operation': operation,
            'fit_recomputation_triggered': field_path in FIT_AFFECTING_FIELDS,
            'fit_recomputation_results': fit_recomputation_results if fit_recomputation_results else None
        }, 200)
        
    except Exception as e:
        logger.error(f"[UPDATE_STRUCTURED_FIELD ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to update field: {str(e)}'
        }, 500)


def handle_save_onboarding_profile(request):
    """
    Save onboarding wizard data to user's profile.
    Creates or updates the structured profile with onboarding data.
    """
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_email') or data.get('user_id')
        profile_data = data.get('profile_data', {})
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        
        logger.info(f"[SAVE_ONBOARDING] Saving onboarding profile for {user_id}")
        
        es_client = get_elasticsearch_client()
        
        # Check if profile already exists
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        # Flatten onboarding data for direct field storage
        flat_fields = {
            'onboarding_status': profile_data.get('onboarding_status', 'completed'),
            'onboarding_completed_at': profile_data.get('onboarding_completed_at', datetime.utcnow().isoformat()),
        }
        
        # Student info
        if 'student_info' in profile_data:
            si = profile_data['student_info']
            flat_fields['student_name'] = si.get('name', '')
            flat_fields['grade_level'] = si.get('grade', '')  # Use grade_level to avoid ES mapping conflict
            flat_fields['high_school'] = si.get('high_school', '')
            flat_fields['state'] = si.get('state', '')
        
        # Academic profile
        if 'academic_profile' in profile_data:
            ap = profile_data['academic_profile']
            if ap.get('gpa', {}).get('weighted'):
                flat_fields['gpa_weighted'] = float(ap['gpa']['weighted'])
            
            # Safely handle test_scores which may have null sat/act
            test_scores = ap.get('test_scores') or {}
            sat_data = test_scores.get('sat') or {}
            act_data = test_scores.get('act') or {}
            
            if sat_data.get('composite'):
                flat_fields['sat_composite'] = int(sat_data['composite'])
            if act_data.get('composite'):
                flat_fields['act_composite'] = int(act_data['composite'])
            
            flat_fields['ap_courses_count'] = ap.get('ap_courses', 0)
        
        # Interests
        if 'interests' in profile_data:
            interests = profile_data['interests']
            flat_fields['intended_majors'] = interests.get('intended_majors', [])
            flat_fields['top_activity'] = interests.get('top_activity', '')
            flat_fields['activity_type'] = interests.get('activity_type', '')
        
        # Preferences
        if 'preferences' in profile_data:
            prefs = profile_data['preferences']
            flat_fields['preferred_locations'] = prefs.get('preferred_locations', [])
            flat_fields['school_size_preference'] = prefs.get('school_size', '')
            flat_fields['campus_type_preference'] = prefs.get('campus_type', '')
        
        # Set flag to trigger fit recomputation on next Launchpad visit
        flat_fields['needs_fit_recomputation'] = True
        flat_fields['last_change_reason'] = 'Profile created/updated via onboarding'
        flat_fields['profile_updated_at'] = datetime.utcnow().isoformat()
        flat_fields['updated_at'] = datetime.utcnow().isoformat()
        
        if response['hits']['total']['value'] > 0:
            # Update existing profile
            doc_id = response['hits']['hits'][0]['_id']
            es_client.update(
                index=ES_INDEX_NAME,
                id=doc_id,
                body={"doc": flat_fields}
            )
            logger.info(f"[SAVE_ONBOARDING] Updated existing profile for {user_id}")
        else:
            # Create new profile document
            new_doc = {
                'user_id': user_id,
                'display_name': f"Onboarding Profile - {user_id}",
                'indexed_at': datetime.utcnow().isoformat(),
                'content': f"Profile created via onboarding wizard for {profile_data.get('student_info', {}).get('name', user_id)}",
                **flat_fields
            }
            es_client.index(index=ES_INDEX_NAME, body=new_doc)
            logger.info(f"[SAVE_ONBOARDING] Created new profile for {user_id}")
        
        return add_cors_headers({
            'success': True,
            'message': 'Onboarding profile saved successfully',
            'user_email': user_id
        }, 200)
        
    except Exception as e:
        logger.error(f"[SAVE_ONBOARDING ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to save onboarding profile: {str(e)}'
        }, 500)


def handle_reset_all_profile(request):
    """
    Reset all profile data for a user.
    Deletes: profile document, all fit analyses, and optionally the college list.
    
    POST /reset-all-profile
    {
        "user_email": "student@gmail.com",
        "delete_college_list": true  // Optional - also delete college list
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_email') or data.get('user_id')
        delete_college_list = data.get('delete_college_list', False)
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        
        logger.info(f"[RESET_ALL_PROFILE] Starting reset for {user_id}")
        
        es_client = get_elasticsearch_client()
        deleted_counts = {
            'profile': 0,
            'fits': 0,
            'college_list': 0
        }
        
        # 1. Delete user's profile document(s)
        try:
            delete_query = {
                "query": {"term": {"user_id.keyword": user_id}}
            }
            profile_result = es_client.delete_by_query(index=ES_INDEX_NAME, body=delete_query)
            deleted_counts['profile'] = profile_result.get('deleted', 0)
            logger.info(f"[RESET_ALL_PROFILE] Deleted {deleted_counts['profile']} profile documents")
        except Exception as e:
            logger.warning(f"[RESET_ALL_PROFILE] Error deleting profile: {e}")
        
        # 2. Delete all fit analyses
        try:
            # Fits have user_email field stored - use term query
            fits_query = {
                "query": {"term": {"user_email.keyword": user_id}}
            }
            fits_result = es_client.delete_by_query(index=ES_FITS_INDEX, body=fits_query)
            deleted_counts['fits'] = fits_result.get('deleted', 0)
            logger.info(f"[RESET_ALL_PROFILE] Deleted {deleted_counts['fits']} fit analyses")
        except Exception as e:
            logger.warning(f"[RESET_ALL_PROFILE] Error deleting fits: {e}")
        
        # 3. Optionally delete college list
        if delete_college_list:
            try:
                list_query = {
                    "query": {"term": {"user_email": user_id}}
                }
                list_result = es_client.delete_by_query(index=ES_LIST_ITEMS_INDEX, body=list_query)
                deleted_counts['college_list'] = list_result.get('deleted', 0)
                logger.info(f"[RESET_ALL_PROFILE] Deleted {deleted_counts['college_list']} college list items")
            except Exception as e:
                logger.warning(f"[RESET_ALL_PROFILE] Error deleting college list: {e}")
        
        logger.info(f"[RESET_ALL_PROFILE] Reset complete for {user_id}: {deleted_counts}")
        
        return add_cors_headers({
            'success': True,
            'deleted': deleted_counts,
            'message': f"Profile reset complete. Deleted {deleted_counts['profile']} profile(s), {deleted_counts['fits']} fits, {deleted_counts['college_list']} college list items."
        }, 200)
        
    except Exception as e:
        logger.error(f"[RESET_ALL_PROFILE ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Reset failed: {str(e)}'
        }, 500)


# ============================================
# FIT INFOGRAPHIC GENERATION (DEPRECATED)
# Frontend now uses static CSS template - no AI image generation needed
# ============================================

def handle_generate_fit_infographic(request):
    """
    DEPRECATED: Infographic image generation is disabled.
    The frontend now uses a static CSS template with dynamic data.
    This endpoint returns a stub response for backward compatibility.
    """
    data = request.get_json() or {}
    university_id = data.get('university_id', '')
    
    logger.info(f"[GENERATE_FIT_IMAGE] DEPRECATED - Request for {university_id} ignored (using static template)")
    
    return add_cors_headers({
        'success': True,
        'university_id': university_id,
        'university_name': university_id.replace('_', ' ').title() if university_id else '',
        'infographic_url': None,
        'from_cache': True,
        'deprecated': True,
        'message': 'Infographic generation is deprecated. Frontend uses static template.'
    }, 200)


def handle_generate_fit_infographic_data(request):
    """
    DEPRECATED: Returns empty infographic data.
    The frontend now computes and renders fit data directly from the fit analysis response.
    """
    data = request.get_json() if request.method == 'POST' else {}
    university_id = request.args.get('university_id') or data.get('university_id', '')
    
    logger.info(f"[GENERATE_FIT_DATA] DEPRECATED - Request for {university_id} ignored")
    
    return add_cors_headers({
        'success': True,
        'university_id': university_id,
        'infographic_data': None,
        'deprecated': True,
        'message': 'Infographic data generation is deprecated. Use fit analysis response directly.'
    }, 200)



    if isinstance(clean_data.get('recommendations'), str):
        try:
            clean_data['recommendations'] = json.loads(clean_data['recommendations'])
        except:
            pass
    
    fit_json = json.dumps(clean_data, indent=2)
    
    # Simple prompt that works well with Gemini image generation
    prompt = f"""Create an infographic for the content below. This should be focused more on where the student stands in terms of admission chances into the school, the reasons and what action items the student needs to take to improve his/her chances.

{fit_json}
"""
    
    return prompt


def handle_generate_fit_infographic(request):
    """
    DEPRECATED: Infographic generation is disabled.
    The frontend now uses a static CSS template with dynamic data instead of AI-generated images.
    
    POST /generate-fit-image
    Returns a stub response indicating the feature is deprecated.
    """
    try:
        data = request.get_json() or {}
        user_email = data.get('user_email') or data.get('user_id')
        university_id = data.get('university_id')
        
        logger.info(f"[GENERATE_FIT_IMAGE] DEPRECATED - Request for {university_id} ignored (using static template)")
        
        # Return success with no URL - frontend will use static template
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'university_name': university_id.replace('_', ' ').title() if university_id else '',
            'infographic_url': None,  # No URL - frontend uses static CSS template
            'from_cache': True,
            'deprecated': True,
            'message': 'Infographic generation is deprecated. Frontend uses static template with dynamic data.'
        }, 200)
        
        # Check cache first (unless force_regenerate is True)
        if not force_regenerate:
            try:
                cached = es_client.get(index=ES_FITS_INDEX, id=doc_id)
                cached_fit = cached['_source']
                infographic_url = cached_fit.get('infographic_url')
                
                if infographic_url:
                    logger.info(f"[GENERATE_FIT_IMAGE] Cache HIT - returning existing URL: {infographic_url}")
                    return add_cors_headers({
                        'success': True,
                        'university_id': university_id,
                        'university_name': cached_fit.get('university_name', university_id),
                        'infographic_url': infographic_url,
                        'from_cache': True
                    }, 200)
                    
            except Exception as e:
                logger.info(f"[GENERATE_FIT_IMAGE] No cached URL found: {e}")
        
        # Fetch fit data from ES
        try:
            fit_doc = es_client.get(index=ES_FITS_INDEX, id=doc_id)
            fit_data = fit_doc['_source']
        except Exception as e:
            logger.error(f"[GENERATE_FIT_IMAGE] Fit data not found: {e}")
            return add_cors_headers({
                'success': False,
                'error': 'Fit analysis not found. Please compute fit first.',
                'university_id': university_id
            }, 404)
        
        # Get student name from profile
        student_name = "Student"
        try:
            profile_query = {
                "size": 1,
                "query": {"term": {"user_id.keyword": user_email}},
                "_source": ["student_name", "name"]
            }
            profile_result = es_client.search(index=ES_INDEX_NAME, body=profile_query)
            if profile_result['hits']['total']['value'] > 0:
                profile = profile_result['hits']['hits'][0]['_source']
                student_name = profile.get('student_name') or profile.get('name') or "Student"
        except Exception as e:
            logger.warning(f"[GENERATE_FIT_IMAGE] Could not fetch student name: {e}")
        
        university_name = fit_data.get('university_name', university_id.replace('_', ' ').title())
        
        # Build the prompt
        prompt = generate_fit_infographic_prompt(fit_data, student_name, university_name)
        logger.info(f"[GENERATE_FIT_IMAGE] Generated prompt for {university_name}")
        
        # Call Gemini image generation (Nano Banana Pro)
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model="gemini-3-pro-image-preview",  # Nano Banana Pro
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    candidate_count=1
                )
            )
            
            # Extract image from response
            image_data = None
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_data = part.inline_data.data
                    break
            
            if not image_data:
                logger.error("[GENERATE_FIT_IMAGE] Gemini Pro did not return an image")
                return add_cors_headers({
                    'success': False,
                    'error': 'Gemini Pro did not return an image. Check API logs.',
                    'university_id': university_id
                }, 500)
            
            # Verify image health
            Image.open(io.BytesIO(image_data)).verify()
            logger.info(f"[GENERATE_FIT_IMAGE] Got valid image data, size: {len(image_data)} bytes")
            
        except Exception as e:
            logger.error(f"[GENERATE_FIT_IMAGE] Gemini API error: {str(e)}")
            return add_cors_headers({
                'success': False,
                'error': f'Image generation failed: {str(e)}',
                'university_id': university_id
            }, 500)
        
        # Upload to GCS
        try:
            storage_client = storage.Client()
            bucket = storage_client.bucket(FIT_IMAGES_BUCKET)
            
            # Create blob path with timestamp: {email_hash}/{university_id}_{timestamp}.png
            blob_path = f"{email_hash}/{university_id}_{int(time.time())}.png"
            blob = bucket.blob(blob_path)
            
            # Upload the image
            import base64
            if isinstance(image_data, str):
                image_bytes = base64.b64decode(image_data)
            else:
                image_bytes = image_data
            
            blob.upload_from_string(image_bytes, content_type='image/png')
            
            # Make the blob publicly readable
            blob.make_public()
            
            infographic_url = blob.public_url
            logger.info(f"[GENERATE_FIT_IMAGE] Uploaded to GCS: {infographic_url}")
            
        except Exception as e:
            logger.error(f"[GENERATE_FIT_IMAGE] GCS upload error: {str(e)}")
            return add_cors_headers({
                'success': False,
                'error': f'Failed to upload image: {str(e)}',
                'university_id': university_id
            }, 500)
        
        # Update ES with the URL
        try:
            es_client.update(
                index=ES_FITS_INDEX,
                id=doc_id,
                body={
                    "doc": {
                        "infographic_url": infographic_url,
                        "infographic_generated_at": datetime.utcnow().isoformat()
                    }
                }
            )
            logger.info(f"[GENERATE_FIT_IMAGE] Updated ES with infographic URL")
        except Exception as e:
            logger.warning(f"[GENERATE_FIT_IMAGE] Failed to update ES: {e}")
        
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'university_name': university_name,
            'infographic_url': infographic_url,
            'from_cache': False
        }, 200)
        
    except Exception as e:
        logger.error(f"[GENERATE_FIT_IMAGE ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to generate infographic: {str(e)}'
        }, 500)


def handle_generate_fit_infographic_data(request):
    """
    Generate structured infographic data using Gemini with structured output.
    Returns JSON that the frontend can render as a beautiful infographic component.
    
    POST /generate-fit-infographic-data
    {
        "user_email": "student@gmail.com",
        "university_id": "stanford_university"
    }
    
    Returns:
    {
        "success": true,
        "infographic_data": {
            "title": "...",
            "subtitle": "...",
            "themeColor": "amber",
            "matchScore": 68,
            "fitCategory": "REACH",
            "universityInfo": {...},
            "strengths": [...],
            "improvements": [...],
            "actionPlan": [...],
            "conclusion": "..."
        }
    }
    """
    try:
        if request.method == 'OPTIONS':
            return add_cors_headers({}, 200)
        
        data = request.get_json() if request.is_json else {}
        user_email = data.get('user_email') or request.args.get('user_email')
        university_id = data.get('university_id') or request.args.get('university_id')
        
        if not user_email or not university_id:
            return add_cors_headers({
                'success': False,
                'error': 'user_email and university_id are required'
            }, 400)
        
        sanitized_email = sanitize_email_for_storage(user_email)
        doc_id = f"{sanitized_email}_{university_id}"
        
        # Get fit data from ES
        try:
            fit_doc = es_client.get(index=ES_FITS_INDEX, id=doc_id)
            fit_data = fit_doc['_source']
        except NotFoundError:
            return add_cors_headers({
                'success': False,
                'error': 'Fit analysis not found. Please run fit analysis first.'
            }, 404)
        
        # Get student name from profile
        student_name = "Student"
        try:
            profile_doc = es_client.get(index=ES_PROFILES_INDEX, id=sanitized_email)
            if profile_doc['found']:
                profile = profile_doc['_source']
                student_name = profile.get('student_name') or profile.get('name') or "Student"
        except Exception as e:
            logger.warning(f"[GENERATE_FIT_DATA] Could not fetch student name: {e}")
        
        university_name = fit_data.get('university_name', university_id.replace('_', ' ').title())
        
        # Parse factors for structured output
        factors = fit_data.get('factors', [])
        strengths = []
        improvements = []
        
        for factor in factors:
            if isinstance(factor, dict):
                name = factor.get('name', '')
                score = factor.get('score', 0)
                max_score = factor.get('max', factor.get('max_score', 100))
                detail = factor.get('detail', '')
                
                factor_info = {
                    "name": name,
                    "score": score,
                    "maxScore": max_score,
                    "percentage": round((score / max_score * 100) if max_score > 0 else 0),
                    "detail": detail
                }
                
                if max_score > 0 and (score / max_score) >= 0.6:
                    strengths.append(factor_info)
                else:
                    improvements.append(factor_info)
        
        # Parse recommendations
        recommendations = fit_data.get('recommendations', [])
        if isinstance(recommendations, str):
            try:
                recommendations = json.loads(recommendations)
            except:
                recommendations = []
        
        action_plan = []
        for i, rec in enumerate(recommendations[:3]):
            if isinstance(rec, dict):
                action_plan.append({
                    "step": i + 1,
                    "action": rec.get('action', ''),
                    "addressesGap": rec.get('addresses_gap', ''),
                    "timeline": rec.get('timeline', ''),
                    "impact": rec.get('impact', '')
                })
            elif isinstance(rec, str):
                action_plan.append({
                    "step": i + 1,
                    "action": rec,
                    "addressesGap": "",
                    "timeline": "",
                    "impact": ""
                })
        
        # Parse gap analysis
        gap_analysis = fit_data.get('gap_analysis', {})
        if isinstance(gap_analysis, str):
            try:
                gap_analysis = json.loads(gap_analysis)
            except:
                gap_analysis = {}
        
        # Build structured infographic data
        fit_category = fit_data.get('fit_category', 'TARGET')
        
        # Map fit category to theme color
        theme_colors = {
            'SAFETY': 'emerald',
            'TARGET': 'amber',
            'REACH': 'orange',
            'SUPER_REACH': 'rose'
        }
        
        location = fit_data.get('location', {})
        if isinstance(location, str):
            location_str = location
        else:
            location_str = f"{location.get('city', '')}, {location.get('state', '')}"
        
        infographic_data = {
            "title": f"{student_name}'s Path to {university_name}",
            "subtitle": "Understanding Your Fit & Action Plan",
            "themeColor": theme_colors.get(fit_category, 'amber'),
            "matchScore": fit_data.get('match_score', fit_data.get('match_percentage', 70)),
            "fitCategory": fit_category,
            "explanation": fit_data.get('explanation', ''),
            "universityInfo": {
                "name": university_name,
                "location": location_str,
                "acceptanceRate": fit_data.get('acceptance_rate', 'N/A'),
                "usNewsRank": fit_data.get('us_news_rank', 'N/A'),
                "marketPosition": fit_data.get('market_position', '')
            },
            "strengths": strengths,
            "improvements": improvements,
            "actionPlan": action_plan,
            "gapAnalysis": {
                "primaryGap": gap_analysis.get('primary_gap', ''),
                "secondaryGap": gap_analysis.get('secondary_gap', ''),
                "studentStrengths": gap_analysis.get('student_strengths', [])
            },
            "conclusion": f"Based on your profile, {university_name} is classified as a {fit_category} school. " + 
                         (fit_data.get('explanation', '')[:200] + "..." if len(fit_data.get('explanation', '')) > 200 else fit_data.get('explanation', ''))
        }
        
        logger.info(f"[GENERATE_FIT_DATA] Generated infographic data for {university_name}")
        
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'university_name': university_name,
            'infographic_data': infographic_data
        }, 200)
        
    except Exception as e:
        logger.error(f"[GENERATE_FIT_DATA ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to generate infographic data: {str(e)}'
        }, 500)


def handle_check_fit_recomputation(request):
    """
    Check if user's profile has needs_fit_recomputation flag set.
    
    GET /check-fit-recomputation?user_email=student@gmail.com
    """
    try:
        user_id = request.args.get('user_email') or request.args.get('user_id')
        
        if not user_id:
            data = request.get_json() or {}
            user_id = data.get('user_email') or data.get('user_id')
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "_source": ["needs_fit_recomputation", "profile_updated_at"]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({
                'success': True,
                'needs_recomputation': False,
                'reason': 'No profile found'
            }, 200)
        
        profile = response['hits']['hits'][0]['_source']
        needs_recomputation = profile.get('needs_fit_recomputation', False)
        
        return add_cors_headers({
            'success': True,
            'needs_recomputation': needs_recomputation,
            'profile_updated_at': profile.get('profile_updated_at')
        }, 200)
        
    except Exception as e:
        logger.error(f"[CHECK_FIT_RECOMP ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': str(e)
        }, 500)


def handle_update_profile_content(request):
    """Update the raw content section of the student's profile."""
    try:
        data = request.get_json()
        if not data:
            return add_cors_headers({'error': 'No data provided'}, 400)
        
        user_id = data.get('user_id') or data.get('user_email')
        update_type = data.get('update_type')  # 'append', 'replace', 'remove'
        content = data.get('content')
        
        if not user_id:
            return add_cors_headers({'error': 'User ID is required'}, 400)
        if not update_type:
            return add_cors_headers({'error': 'Update type is required'}, 400)
        if not content:
            return add_cors_headers({'error': 'Content is required'}, 400)
        
        es_client = get_elasticsearch_client()
        
        # Find user's profile document
        search_body = {
            "size": 1,
            "query": {"term": {"user_id.keyword": user_id}},
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({'error': 'No profile found for user'}, 404)
        
        doc_id = response['hits']['hits'][0]['_id']
        current_doc = response['hits']['hits'][0]['_source']
        current_content = current_doc.get('content', '')
        
        # Apply update based on type
        if update_type == 'append':
            new_content = f"{current_content}\n\n{content}"
        elif update_type == 'replace':
            new_content = content
        elif update_type == 'remove':
            new_content = current_content.replace(content, '')
        else:
            return add_cors_headers({'error': 'Update type must be append, replace, or remove'}, 400)
        
        # Evaluate if changes affect fit calculations using LLM
        needs_fit_recomputation = False
        change_evaluation = {}
        
        if current_content and new_content != current_content:
            logger.info(f"[UPDATE_CONTENT] Evaluating profile changes for fit impact...")
            change_evaluation = evaluate_profile_change_impact(current_content, new_content)
            needs_fit_recomputation = change_evaluation.get('should_recompute', False)
            logger.info(f"[UPDATE_CONTENT] Fit recomputation needed: {needs_fit_recomputation}")
        
        # Build update document
        update_doc = {
            "content": new_content,
            "content_updated_at": datetime.utcnow().isoformat(),
            "profile_updated_at": datetime.utcnow().isoformat()
        }
        
        # Set recomputation flag if LLM determined it's needed
        if needs_fit_recomputation:
            update_doc["needs_fit_recomputation"] = True
            update_doc["last_change_reason"] = change_evaluation.get('reason', 'Unknown')
            update_doc["last_change_details"] = change_evaluation.get('changes_detected', [])
        
        # Update document
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={"doc": update_doc}
        )
        
        logger.info(f"[UPDATE_CONTENT] {update_type} content for user {user_id}")
        return add_cors_headers({
            'success': True,
            'update_type': update_type,
            'message': f'Successfully {update_type}ed content',
            'needs_fit_recomputation': needs_fit_recomputation,
            'change_evaluation': change_evaluation
        }, 200)
        
    except Exception as e:
        logger.error(f"[UPDATE_CONTENT ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to update content: {str(e)}'
        }, 500)


# --- CORS Headers ---

def add_cors_headers(response, status_code=200):
    """Add CORS headers to response and return proper format."""
    if isinstance(response, dict):
        response = (json.dumps(response), status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-User-Email',
            'Access-Control-Max-Age': '3600'
        })
    elif isinstance(response, tuple) and len(response) >= 2:
        # Add CORS headers to existing tuple response
        if len(response) == 2:
            data, status = response
            headers = {}
        else:
            data, status, headers = response
        # Merge headers
        headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-User-Email',
            'Access-Control-Max-Age': '3600'
        })
        response = (data, status, headers)
    return response

@functions_framework.http
def profile_manager_es_http_entry(request):
    """HTTP Cloud Function that acts as a controller for profile operations."""
    
    # Enable CORS
    if request.method == 'OPTIONS':
        return add_cors_headers({'status': 'ok'}, 200)
    
    # Parse path to determine resource type and action
    path_parts = request.path.strip('/').split('/')
    
    if not path_parts or len(path_parts) == 0:
        return add_cors_headers({'error': 'Not Found'}, 404)
    
    resource_type = path_parts[0]
    logger.info(f"Processing {request.method} request for resource_type: {resource_type}, path: {request.path}")
    
    try:
        # --- UPLOAD ROUTE ---
        if resource_type == 'upload-profile' and request.method == 'POST':
            # Handle multipart file upload
            if 'file' not in request.files:
                return add_cors_headers({'error': 'No file provided'}, 400)
            
            file = request.files['file']
            user_id = request.form.get('user_id')
            
            if not user_id:
                # Try to get from current user (Firebase auth)
                user_id = request.headers.get('X-User-Email', 'anonymous')
            
            if not file.filename:
                return add_cors_headers({'error': 'No file selected'}, 400)
            
            try:
                # Read file content
                file_content = file.read()
                filename = file.filename
                
                # Upload original file to GCS for later download
                storage_client = storage.Client()
                bucket = storage_client.bucket(GCS_BUCKET_NAME)
                blob_path = f"{user_id}/{filename}"
                blob = bucket.blob(blob_path)
                
                # Upload with original content type
                from mimetypes import guess_type
                content_type, _ = guess_type(filename)
                blob.upload_from_string(file_content, content_type=content_type or 'application/octet-stream')
                
                logger.info(f"[GCS] Uploaded original file to: gs://{GCS_BUCKET_NAME}/{blob_path}")
                
                # Extract and convert to markdown using Gemini
                extracted_content = extract_profile_content_with_gemini(file_content, filename)
                content_markdown = extracted_content.get('content_markdown', '')
                structured_profile = extracted_content.get('structured_profile')  # New: structured JSON
                
                if not content_markdown:
                    # Fallback to raw content if markdown conversion failed
                    content_markdown = extracted_content.get('raw_content', 'Error: Could not extract content')
                
                # Index in Elasticsearch with markdown AND flattened profile data
                # Also store GCS path for original file download
                result = index_student_profile(
                    user_id, 
                    filename, 
                    content_markdown,
                    profile_data=structured_profile,
                    metadata={'gcs_path': blob_path}
                )
                
                if result["success"]:
                    # Include list of extracted fields for frontend display
                    extracted_fields = []
                    if structured_profile:
                        if structured_profile.get('gpa'):
                            extracted_fields.append('GPA')
                        if structured_profile.get('sat_composite') or structured_profile.get('sat_total'):
                            extracted_fields.append('SAT')
                        if structured_profile.get('act_composite'):
                            extracted_fields.append('ACT')
                        if structured_profile.get('activities'):
                            extracted_fields.append('Activities')
                        if structured_profile.get('awards') or structured_profile.get('honors'):
                            extracted_fields.append('Awards')
                        if structured_profile.get('courses') or structured_profile.get('ap_courses'):
                            extracted_fields.append('Courses')
                        if structured_profile.get('intended_major') or structured_profile.get('intended_majors'):
                            extracted_fields.append('Major')
                        if structured_profile.get('student_name') or structured_profile.get('name'):
                            extracted_fields.append('Name')
                        if structured_profile.get('grade_level') or structured_profile.get('grade'):
                            extracted_fields.append('Grade')
                        if structured_profile.get('high_school') or structured_profile.get('school'):
                            extracted_fields.append('School')
                    
                    result['extracted_fields'] = extracted_fields
                    return add_cors_headers(result, 200)
                else:
                    return add_cors_headers(result, 500)
                    
            except Exception as e:
                logger.error(f"[UPLOAD_ES ERROR] {str(e)}")
                return add_cors_headers({
                    'success': False,
                    'error': f'Upload failed: {str(e)}'
                }, 500)

        
        # --- SEARCH ROUTE ---
        elif resource_type == 'search' and request.method == 'POST':
            return handle_search(request)
        
        # --- PROFILES ROUTE (Standard REST) ---
        elif resource_type == 'profiles' or resource_type == 'list-profiles':
            if request.method == 'GET':
                # List profiles for user
                user_id = request.args.get('user_id') or request.args.get('user_email')
                size = int(request.args.get('size', 20))
                from_index = int(request.args.get('from', 0))  # Use 'from' like knowledge base manager ES
                
                if not user_id:
                    # Try to get from headers (Firebase auth)
                    user_id = request.headers.get('X-User-Email', 'anonymous')
                
                result = search_student_profiles(user_id, '', size, from_index)
                
                if result['success']:
                    return add_cors_headers(result, 200)
                else:
                    return add_cors_headers(result, 500)
        
        # --- DELETE ROUTE (RAG Compatible) ---
        elif resource_type == 'delete-profile' and request.method == 'DELETE':
            return handle_delete_profile(request)
            
        # --- GET CONTENT ROUTE (RAG Compatible) ---
        elif resource_type == 'get-profile-content' and request.method == 'POST':
            return handle_get_content(request)
        
        # --- DOWNLOAD DOCUMENT ROUTE ---
        elif resource_type == 'download-document' and request.method == 'POST':
            return handle_download_document(request)
        
        # --- GET STRUCTURED PROFILE (for ProfileViewCard) ---
        elif resource_type == 'get-profile' and request.method == 'GET':
            return handle_get_structured_profile(request)
        
        # --- COLLEGE LIST ROUTES ---
        elif resource_type == 'update-college-list' and request.method == 'POST':
            return handle_update_college_list(request)
        
        elif resource_type == 'bulk-remove-colleges' and request.method == 'POST':
            return handle_bulk_remove_colleges(request)
        
        elif resource_type == 'get-college-list':
            return handle_get_college_list(request)
        
        elif resource_type == 'update-fit-analysis' and request.method == 'POST':
            return handle_update_fit_analysis(request)
        
        elif resource_type == 'recalculate-fits':
            return handle_recalculate_all_fits(request)
        
        # --- PRE-COMPUTED FIT MATRIX ROUTES ---
        elif resource_type == 'compute-all-fits' and request.method == 'POST':
            return handle_compute_all_fits(request)
        
        elif resource_type == 'compute-single-fit' and request.method == 'POST':
            return handle_compute_single_fit(request)
        
        elif resource_type == 'get-fits' and request.method == 'POST':
            return handle_get_fits(request)
        
        # --- FIT INFOGRAPHIC GENERATION ---
        elif resource_type == 'generate-fit-image' and request.method == 'POST':
            return handle_generate_fit_infographic(request)
        
        elif resource_type == 'generate-fit-infographic-data' and request.method in ['GET', 'POST']:
            return handle_generate_fit_infographic_data(request)
        
        # --- PROFILE UPDATE ROUTES ---
        elif resource_type == 'update-profile' and request.method == 'POST':
            return handle_update_profile(request)
        
        elif resource_type == 'update-profile-content' and request.method == 'POST':
            return handle_update_profile_content(request)
        
        elif resource_type == 'update-structured-field' and request.method == 'POST':
            return handle_update_structured_field(request)
        
        # --- SEARCH USER PROFILE (for agent tools) ---
        elif resource_type == 'search-user-profile' and request.method == 'POST':
            return handle_search(request)
        
        # --- ONBOARDING ROUTES ---
        elif resource_type == 'save-onboarding-profile' and request.method == 'POST':
            return handle_save_onboarding_profile(request)
        
        # --- RESET ALL PROFILE DATA ---
        elif resource_type == 'reset-all-profile' and request.method == 'POST':
            return handle_reset_all_profile(request)
        
        # --- CHECK FIT RECOMPUTATION NEEDED ---
        elif resource_type == 'check-fit-recomputation':
            return handle_check_fit_recomputation(request)
        
        # --- CREDITS MANAGEMENT ---
        elif resource_type == 'get-credits':
            user_email = request.args.get('user_email') or request.headers.get('X-User-Email')
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            credits = get_user_credits(user_email)
            return add_cors_headers({'success': True, 'credits': credits}, 200)
        
        elif resource_type == 'check-credits' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            credits_needed = data.get('credits_needed', 1)
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = check_credits_available(user_email, credits_needed)
            return add_cors_headers({'success': True, **result}, 200)
        
        elif resource_type == 'deduct-credit' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            credit_count = data.get('credit_count', 1)
            reason = data.get('reason', 'fit_analysis')
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = deduct_credit(user_email, credit_count, reason)
            return add_cors_headers(result, 200 if result['success'] else 400)
        
        elif resource_type == 'add-credits' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            credit_count = data.get('credit_count', CREDIT_PACK_SIZE)
            source = data.get('source', 'credit_pack')
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = add_credits(user_email, credit_count, source)
            return add_cors_headers(result, 200 if result['success'] else 500)
        
        elif resource_type == 'upgrade-subscription' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            subscription_expires = data.get('subscription_expires')
            plan_type = data.get('plan_type', 'monthly')
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = upgrade_subscription(user_email, subscription_expires, plan_type)
            return add_cors_headers(result, 200 if result['success'] else 500)
        
        # --- FIT CHAT (Context Injection) ---
        elif resource_type == 'fit-chat' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            question = data.get('question', '')
            history = data.get('conversation_history', [])
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            if not university_id or not question:
                return add_cors_headers({'success': False, 'error': 'university_id and question required'}, 400)
            
            result = fit_chat(user_email, university_id, question, history)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION SAVE ---
        elif resource_type == 'fit-chat-save' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            university_name = data.get('university_name', university_id)
            messages = data.get('messages', [])
            conversation_id = data.get('conversation_id')  # Optional for updates
            title = data.get('title')  # Optional, auto-generated if not provided
            
            if not user_email or not university_id:
                return add_cors_headers({'success': False, 'error': 'user_email and university_id required'}, 400)
            if not messages:
                return add_cors_headers({'success': False, 'error': 'messages required'}, 400)
            
            result = save_fit_chat_conversation(user_email, university_id, university_name, 
                                               messages, conversation_id, title)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION LIST ---
        elif resource_type == 'fit-chat-list' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id') or request.args.get('university_id')  # Optional filter
            limit = int(data.get('limit') or request.args.get('limit') or 20)
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = list_fit_chat_conversations(user_email, university_id, limit)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION LOAD ---
        elif resource_type == 'fit-chat-load' and request.method in ['GET', 'POST']:
            if request.method == 'POST':
                data = request.get_json() or {}
            else:
                data = {}
            user_email = data.get('user_email') or request.args.get('user_email') or request.headers.get('X-User-Email')
            conversation_id = data.get('conversation_id') or request.args.get('conversation_id')
            
            if not user_email or not conversation_id:
                return add_cors_headers({'success': False, 'error': 'user_email and conversation_id required'}, 400)
            
            result = load_fit_chat_conversation(user_email, conversation_id)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # --- FIT CHAT CONVERSATION DELETE ---
        elif resource_type == 'fit-chat-delete' and request.method in ['POST', 'DELETE']:
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            conversation_id = data.get('conversation_id')
            
            if not user_email or not conversation_id:
                return add_cors_headers({'success': False, 'error': 'user_email and conversation_id required'}, 400)
            
            result = delete_fit_chat_conversation(user_email, conversation_id)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        # ============================================
        # DEADLINE TRACKER ENDPOINTS
        # ============================================
        
        elif resource_type == 'get-deadlines' and request.method in ['GET', 'POST']:
            # Get all deadlines for user's saved schools
            if request.method == 'GET':
                user_email = request.args.get('user_email')
            else:
                data = request.get_json() or {}
                user_email = data.get('user_email')
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = get_user_deadlines(user_email)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'update-application-plan' and request.method == 'POST':
            # Update user's application plan for a specific university
            data = request.get_json() or {}
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            application_plan = data.get('application_plan')  # Can be None to clear
            
            if not user_email or not university_id:
                return add_cors_headers({'success': False, 'error': 'user_email and university_id required'}, 400)
            
            result = update_application_plan(user_email, university_id, application_plan)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        elif resource_type == 'update-application-status' and request.method == 'POST':
            # Update application status (planning, drafting, submitted, decision)
            data = request.get_json() or {}
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            status = data.get('status')
            
            if not user_email or not university_id or not status:
                return add_cors_headers({'success': False, 'error': 'user_email, university_id, and status required'}, 400)
            
            result = update_application_status(user_email, university_id, status)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        elif resource_type == 'update-application-task' and request.method == 'POST':
            # Update a specific application task/checklist item
            data = request.get_json() or {}
            user_email = data.get('user_email')
            university_id = data.get('university_id')
            task_name = data.get('task_name')
            completed = data.get('completed', False)
            
            if not user_email or not university_id or not task_name:
                return add_cors_headers({'success': False, 'error': 'user_email, university_id, and task_name required'}, 400)
            
            result = update_application_task(user_email, university_id, task_name, completed)
            return add_cors_headers(result, 200 if result.get('success') else 400)
        
        elif resource_type == 'get-application-progress' and request.method in ['GET', 'POST']:
            # Get aggregated application progress stats
            if request.method == 'GET':
                user_email = request.args.get('user_email')
            else:
                data = request.get_json() or {}
                user_email = data.get('user_email')
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = get_application_progress(user_email)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        # --- ESSAY COPILOT ENDPOINTS ---
        elif resource_type == 'essay-starters' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_text = data.get('prompt_text') or data.get('prompt')
            notes = data.get('notes', '')
            
            if not user_email or not prompt_text:
                return add_cors_headers({'success': False, 'error': 'user_email and prompt_text required'}, 400)
            
            result = generate_essay_starters(user_email, university_id, prompt_text, notes)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'starter-context' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            selected_hook = data.get('selected_hook') or data.get('hook')
            prompt_text = data.get('prompt_text') or data.get('prompt')
            
            if not user_email or not selected_hook:
                return add_cors_headers({'success': False, 'error': 'user_email and selected_hook required'}, 400)
            
            result = get_starter_context(user_email, university_id, selected_hook, prompt_text or '')
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'essay-copilot' and request.method == 'POST':
            data = request.get_json() or {}
            prompt_text = data.get('prompt_text') or data.get('prompt')
            current_text = data.get('current_text') or data.get('text', '')
            action = data.get('action', 'suggest')  # complete, suggest, expand
            
            if not prompt_text:
                return add_cors_headers({'success': False, 'error': 'prompt_text required'}, 400)
            
            result = get_copilot_suggestion(prompt_text, current_text, action)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'essay-feedback' and request.method == 'POST':
            data = request.get_json() or {}
            prompt_text = data.get('prompt_text') or data.get('prompt')
            draft_text = data.get('draft_text') or data.get('draft', '')
            university_name = data.get('university_name', '')
            
            if not prompt_text or not draft_text:
                return add_cors_headers({'success': False, 'error': 'prompt_text and draft_text required'}, 400)
            
            result = get_draft_feedback(prompt_text, draft_text, university_name)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'essay-chat' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_text = data.get('prompt_text') or data.get('prompt', '')
            current_text = data.get('current_text') or data.get('text', '')
            user_question = data.get('question', '')
            
            if not user_email or not university_id or not user_question:
                return add_cors_headers({'success': False, 'error': 'user_email, university_id, and question required'}, 400)
            
            result = essay_chat(user_email, university_id, prompt_text, current_text, user_question)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'profile-chat' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            question = data.get('question', '')
            conversation_history = data.get('conversation_history', [])
            
            if not user_email or not question:
                return add_cors_headers({'success': False, 'error': 'user_email and question required'}, 400)
            
            result = profile_chat(user_email, question, conversation_history)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'save-essay-draft' and request.method == 'POST':
            data = request.get_json() or {}
            user_email = data.get('user_email') or request.headers.get('X-User-Email')
            university_id = data.get('university_id')
            prompt_index = data.get('prompt_index', 0)
            prompt_text = data.get('prompt_text') or data.get('prompt', '')
            draft_text = data.get('draft_text') or data.get('draft', '')
            notes = data.get('notes', [])
            version = data.get('version', 0)
            version_name = data.get('version_name', '')
            
            if not user_email or not university_id:
                return add_cors_headers({'success': False, 'error': 'user_email and university_id required'}, 400)
            
            result = save_essay_draft(user_email, university_id, prompt_index, prompt_text, draft_text, notes, version, version_name)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        elif resource_type == 'get-essay-drafts' and request.method in ['GET', 'POST']:
            if request.method == 'GET':
                user_email = request.args.get('user_email')
                university_id = request.args.get('university_id')
            else:
                data = request.get_json() or {}
                user_email = data.get('user_email') or request.headers.get('X-User-Email')
                university_id = data.get('university_id')
            
            if not user_email:
                return add_cors_headers({'success': False, 'error': 'user_email required'}, 400)
            
            result = get_essay_drafts(user_email, university_id)
            return add_cors_headers(result, 200 if result.get('success') else 500)
        
        else:
            return add_cors_headers({'error': 'Not Found'}, 404)

            
    except Exception as e:
        logger.error(f"[PROFILE_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, 500)

