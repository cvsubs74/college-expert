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
import google.generativeai as genai


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
    Converts PDF/DOCX text to clean, well-formatted Markdown.
    """
    try:
        # Extract raw text content from PDF/DOCX
        raw_text = extract_text_from_file_content(file_content, filename)
        
        if not raw_text:
            raw_text = "Could not extract text from document."
            logger.warning(f"[EXTRACTION] No text extracted from {filename}")
        
        # Use Gemini to convert raw text to clean markdown
        content_markdown = convert_to_markdown_with_gemini(raw_text, filename)
        
        return {
            "raw_content": raw_text,  # Original extracted text (for search)
            "content_markdown": content_markdown,  # Clean markdown (for display)
            "filename": filename
        }
            
    except Exception as e:
        logger.error(f"[EXTRACTION ERROR] Failed to extract content: {e}")
        return {
            "raw_content": raw_text if 'raw_text' in dir() else "Error processing file",
            "content_markdown": f"# Student Profile\n\nError processing file: {str(e)}",
            "error": str(e)
        }


def convert_to_markdown_with_gemini(raw_text: str, filename: str) -> str:
    """
    Use Gemini to convert raw profile text to clean, well-formatted Markdown.
    """
    import google.generativeai as genai
    
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("[GEMINI] No API key, returning raw text as markdown")
            return f"# Student Profile\n\n{raw_text}"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
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

        response = model.generate_content(prompt)
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


def evaluate_profile_change_impact(old_content: str, new_content: str) -> dict:
    """
    Use LLM to determine if profile changes would affect college fit calculations.
    Returns: {"should_recompute": bool, "reason": str, "changes_detected": []}
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
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
        
        response = model.generate_content(prompt)
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
ES_INDEX_NAME = os.getenv("ES_INDEX_NAME", "student_profiles")  # Legacy - kept for migration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "college-counselling-478115-student-profiles")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# New separated indices (v2 architecture)
ES_PROFILES_INDEX = os.getenv("ES_PROFILES_INDEX", "student_profiles_v2")
ES_LIST_ITEMS_INDEX = os.getenv("ES_LIST_ITEMS_INDEX", "student_college_list")
ES_FITS_INDEX = os.getenv("ES_FITS_INDEX", "student_college_fits")

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)



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

def index_student_profile(user_id, filename, content_markdown, metadata=None):
    """Index student profile in Elasticsearch.
    Stores clean markdown content in the content field with minimal metadata.
    
    Args:
        user_id: User's email
        filename: Original filename
        content_markdown: Clean markdown content (from Gemini)
        metadata: Optional minimal metadata (filename, upload time, gcs_url later)
    """
    try:
        client = get_elasticsearch_client()
        
        # Generate document ID based on user + filename
        import hashlib
        doc_content = f"{user_id}_{filename}"
        document_id = hashlib.sha256(doc_content.encode()).hexdigest()
        
        # Create minimal document - just content and essential metadata
        document = {
            "document_id": document_id,
            "user_id": user_id,
            "filename": filename,
            "content": content_markdown,  # Clean markdown for search and display
            "indexed_at": datetime.utcnow().isoformat(),
            "file_type": filename.split('.')[-1] if '.' in filename else 'unknown'
        }
        
        # Add optional GCS URL to metadata if provided (for future use)
        if metadata and metadata.get('gcs_url'):
            document['gcs_url'] = metadata.get('gcs_url')
        
        # Index document (upsert - replace if exists)
        response = client.index(index=ES_INDEX_NAME, id=document_id, body=document)
        
        logger.info(f"[ES] Indexed profile {document_id} for user {user_id}")
        logger.info(f"[ES] Content: {len(content_markdown)} chars")
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
        
        # Build search query
        must_conditions = [{"term": {"user_id.keyword": user_id}}]
        
        if query_text:
            must_conditions.append({
                "multi_match": {
                    "query": query_text,
                    "fields": ["content", "filename"],
                    "type": "best_fields"
                }
            })

            
        search_body = {
            "size": size,
            "from": from_index,
            "query": {
                "bool": {
                    "must": must_conditions
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"indexed_at": {"order": "desc"}}
            ]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        documents = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            doc_id = hit['_id']
            
            documents.append({
                "name": doc_id,  # Use ID as name
                "display_name": source.get('filename', source.get('file_name', 'Unknown')),
                "create_time": source.get('upload_date', source.get('indexed_at', '')),
                "update_time": source.get('indexed_at', ''),
                "state": "ACTIVE",
                "size_bytes": source.get('file_size', 0),
                "mime_type": "text/plain", # Default for ES
                "id": doc_id, # Keep ID for reference
                "document": source # Keep full source for backward compatibility if needed
            })
        
        return {
            "success": True,
            "total": response['hits']['total']['value'],
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
        
        if not document_id:
             return add_cors_headers({'error': 'Document ID is required'}, 400)
             
        # If we only have filename and user_id, we might need to search for the ID
        # But for now assuming document_id is passed correctly or is the filename
        
        result = delete_student_profile(document_id)
        
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

def delete_student_profile(document_id):
    """Delete student profile from Elasticsearch."""
    try:
        client = get_elasticsearch_client()
        
        # Delete document
        response = client.delete(index=ES_INDEX_NAME, id=document_id)
        
        logger.info(f"[ES] Deleted profile {document_id}")
        return {
            "success": True,
            "message": "Profile deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"[ES ERROR] Failed to delete profile: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# FIT ANALYSIS ENGINE
# ============================================

# Note: 're' imported at module level

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
        import google.generativeai as genai
        
        # Configure Gemini
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.warning("[PROFILE PARSE LLM] No GEMINI_API_KEY found")
            return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
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

        response = model.generate_content(prompt)
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


def calculate_fit_with_llm(student_profile_text, university_data, intended_major=''):
    """
    Calculate fit using comprehensive LLM reasoning with selectivity override rules.
    Acts as an expert private college admissions counselor with 20+ years experience.
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
        # DEBUG: Log the actual student profile text being analyzed
        logger.info(f"[LLM_FIT] Student profile text length: {len(student_profile_text)} chars")
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
        
        # Prepare university summary for prompt (limit size)
        uni_summary = json.dumps({
            "name": uni_name,
            "location": university_data.get('location', profile_data.get('location', {})),
            "acceptance_rate": acceptance_rate,
            "admitted_profile": admitted_profile,
            "academic_structure": profile_data.get('academic_structure', {}).get('colleges', [])[:5]
        }, default=str)[:2500]
        
        # Determine selectivity tier and category floor
        if acceptance_rate < 8:
            selectivity_tier = "ULTRA_SELECTIVE"
            category_floor = "SUPER_REACH"
            selectivity_note = "This is an ULTRA-SELECTIVE school (<8% acceptance). Even perfect applicants are often rejected. MINIMUM category is SUPER_REACH."
        elif acceptance_rate < 15:
            selectivity_tier = "HIGHLY_SELECTIVE"
            category_floor = "REACH"
            selectivity_note = "This is a HIGHLY SELECTIVE school (8-15% acceptance). Even strong applicants face uncertain outcomes. MINIMUM category is REACH."
        elif acceptance_rate < 25:
            selectivity_tier = "VERY_SELECTIVE"
            category_floor = "TARGET"
            selectivity_note = "This is a VERY SELECTIVE school (15-25% acceptance). Strong applicants have reasonable chances."
        elif acceptance_rate < 40:
            selectivity_tier = "SELECTIVE"
            category_floor = None
            selectivity_note = "This is a SELECTIVE school (25-40% acceptance). Standard competitive admissions."
        else:
            selectivity_tier = "ACCESSIBLE"
            category_floor = None
            selectivity_note = "This is an ACCESSIBLE school (>40% acceptance). Strong students are very likely admitted."
        
        prompt = f"""You are a private college admissions counselor with 20+ years of experience placing students at Ivy League and top-50 universities. You have deep knowledge of how selective admissions works and understand that even excellent students face rejection at highly selective schools.

**STUDENT PROFILE:**
{student_profile_text}
Intended Major: {intended_major or 'Undecided'}

**UNIVERSITY DATA:**
{uni_summary}

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

**OUTPUT FORMAT - Return ONLY valid JSON:**
{{
  "match_percentage": <integer 0-100>,
  "fit_category": "<SAFETY|TARGET|REACH|SUPER_REACH>",
  "explanation": "<5-6 sentence analysis: Start with the category justification citing acceptance rate. Then mention 2-3 specific student strengths from their profile. Then acknowledge any gaps or concerns. End with what could strengthen the application.>",
  "factors": [
    {{ "name": "Academic", "score": <0-40>, "max": 40, "detail": "<cite actual GPA/scores from profile>" }},
    {{ "name": "Holistic", "score": <0-30>, "max": 30, "detail": "<cite specific activities/leadership>" }},
    {{ "name": "Major Fit", "score": <0-15>, "max": 15, "detail": "<major availability assessment>" }},
    {{ "name": "Selectivity", "score": <-15 to +5>, "max": 5, "detail": "<{acceptance_rate}% acceptance rate impact>" }}
  ],
  "recommendations": ["<specific actionable rec 1>", "<specific actionable rec 2>", "<specific actionable rec 3>"]
}}"""

        # Call Gemini with retry logic
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                response = model.generate_content(prompt)
                
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
        profile_content = profile_doc.get('content', '')
        
        # Parse student profile
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
        fit_analysis = calculate_fit_with_llm(profile_content, university_data, intended_major)
        
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
        
        # Normalize university ID for consistent matching with fits
        original_uni_id = university['id']
        normalized_uni_id = normalize_university_id(original_uni_id)
        
        # Generate unique document ID for this user+university pair
        email_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        doc_id = f"{email_hash}_{normalized_uni_id}"
        
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
            
            # Create new list item document with normalized ID
            list_doc = {
                'user_email': user_id,
                'university_id': normalized_uni_id,  # Use normalized ID for matching with fits
                'university_name': university.get('name', ''),
                'status': 'favorites',
                'added_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'intended_major': intended_major
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
        
        # Fetch updated college list
        college_list = get_user_college_list(es_client, user_id)
        
        return add_cors_headers({
            'success': True,
            'action': action,
            'university_id': university['id'],
            'college_list': college_list,
            'message': f'College {"added to" if action == "add" else "removed from"} list'
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
            'added_at': item.get('added_at'),
            'intended_major': item.get('intended_major')
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



def handle_get_college_list(request):
    """Get user's college list from the new separated index."""
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
        
        # Convert individual docs to list items
        college_list = []
        for hit in response['hits']['hits']:
            item = hit['_source']
            college_list.append({
                'university_id': item.get('university_id'),
                'university_name': item.get('university_name'),
                'status': item.get('status', 'favorites'),
                'order': item.get('order'),
                'added_at': item.get('added_at'),
                'intended_major': item.get('intended_major'),
                'notes': item.get('student_notes')
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
    Compute fit analysis for a single university without adding it to the college list.
    
    POST /compute-single-fit
    {
        "user_email": "student@gmail.com",
        "university_id": "harvard_university_slug"
    }
    
    Returns:
    {
        "success": true,
        "university_id": "harvard_university_slug",
        "university_name": "Harvard University",
        "fit_analysis": {...}
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_email') or data.get('user_id')
        university_id = data.get('university_id')
        intended_major = data.get('intended_major', '')
        
        if not user_id:
            return add_cors_headers({'error': 'User email is required'}, 400)
        if not university_id:
            return add_cors_headers({'error': 'University ID is required'}, 400)
        
        logger.info(f"[COMPUTE_SINGLE_FIT] Computing fit for {university_id} for user {user_id}")
        
        # Call the existing calculate_fit_for_college function
        fit_analysis = calculate_fit_for_college(user_id, university_id, intended_major)
        
        if not fit_analysis:
            return add_cors_headers({
                'success': False,
                'error': 'Failed to compute fit analysis',
                'university_id': university_id
            }, 500)
        
        logger.info(f"[COMPUTE_SINGLE_FIT] Result: {fit_analysis.get('fit_category')} ({fit_analysis.get('match_percentage')}%)")
        
        return add_cors_headers({
            'success': True,
            'university_id': university_id,
            'university_name': fit_analysis.get('university_name', university_id),
            'fit_analysis': fit_analysis
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
        
        # Recalculate fit for each college
        updated_count = 0
        for college in college_list:
            university_id = college.get('university_id')
            intended_major = college.get('intended_major', '')
            
            logger.info(f"[FIT] Recalculating fit for {university_id}")
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
    
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}?university_id={university_id}",
                timeout=30
            )
            data = response.json()
            
            if data.get('success'):
                return data.get('university', {})
            
            # If not found, don't retry
            if 'NotFoundError' in str(data.get('error', '')):
                logger.warning(f"[KB] University not found: {university_id}")
                return None
                
            return None
            
        except requests.exceptions.SSLError as e:
            logger.warning(f"[KB] SSL error fetching {university_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))  # Exponential backoff: 1s, 2s, 3s
                continue
            logger.error(f"[KB] Max retries exceeded for {university_id}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"[KB] Request error fetching {university_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            logger.error(f"[KB] Max retries exceeded for {university_id}")
            return None
            
        except Exception as e:
            logger.error(f"[KB] Unexpected error fetching university {university_id}: {e}")
            return None
    
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
        profile_content = profile_source.get('content', '')
        
        # Get existing computed fits (to merge with new batch)
        existing_fits_json = profile_source.get('college_fits', '{}')
        try:
            existing_fits = json.loads(existing_fits_json) if existing_fits_json else {}
        except:
            existing_fits = {}
        
        # Step 2: Fetch all universities from KB
        all_universities = fetch_all_universities()
        total_universities = len(all_universities)
        
        if not all_universities:
            return add_cors_headers({
                'success': False,
                'error': 'Could not fetch universities from knowledge base'
            }, 500)
        
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
                fit_analysis = calculate_fit_with_llm(profile_content, uni_profile, '')
                
                # Store computed fit
                fit_result = {
                    'fit_category': fit_analysis.get('fit_category', 'UNKNOWN'),
                    'match_percentage': fit_analysis.get('match_percentage', 0),
                    'match_score': fit_analysis.get('match_percentage', 0),
                    'university_name': uni_summary.get('official_name', university_id),
                    'explanation': fit_analysis.get('explanation', ''),
                    'factors': fit_analysis.get('factors', []),
                    'recommendations': fit_analysis.get('recommendations', []),
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
            fit_doc = {
                'user_email': user_id,
                'university_id': university_id,
                'university_name': fit_result.get('university_name'),
                'computed_at': fits_computed_at,
                'fit_category': fit_result.get('fit_category'),
                'match_score': fit_result.get('match_score'),
                'explanation': fit_result.get('explanation'),
                'factors': fit_result.get('factors', []),
                'recommendations': fit_result.get('recommendations', []),
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
            
            results.append({
                'university_id': normalize_university_id(fit.get('university_id')),  # Normalized for matching
                'university_name': fit.get('university_name'),
                'fit_category': fit.get('fit_category'),
                'match_score': fit.get('match_score'),
                'explanation': fit.get('explanation'),
                'factors': fit.get('factors', []),
                'recommendations': fit.get('recommendations', []),
                'acceptance_rate': fit.get('acceptance_rate'),
                'us_news_rank': fit.get('us_news_rank'),
                'location': fit.get('location'),
                'market_position': fit.get('market_position'),
                'computed_at': fit.get('computed_at')
            })
        
        # Apply limit after filtering (important when state filter expands fetch size)
        results = results[:limit]
        
        return add_cors_headers({
            'success': True,
            'results': results,
            'total': response['hits']['total']['value'],
            'returned': len(results),
            'fits_ready': len(results) > 0,
            'filters_applied': filters
        }, 200)
        
    except Exception as e:
        logger.error(f"[GET_FITS ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to get fits: {str(e)}'
        }, 500)


def handle_update_profile(request):
    """Update the student's profile content directly.
    Expects the caller (agent) to provide the complete updated content.
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
        
        # Update the content field directly
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={
                "doc": {
                    "content": content,
                    "content_updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"[UPDATE_PROFILE] Updated content for user {user_id}")
        return add_cors_headers({
            'success': True,
            'message': 'Successfully updated profile'
        }, 200)
        
    except Exception as e:
        logger.error(f"[UPDATE_PROFILE ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Failed to update profile: {str(e)}'
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
                
                # Extract and convert to markdown using Gemini
                extracted_content = extract_profile_content_with_gemini(file_content, filename)
                content_markdown = extracted_content.get('content_markdown', '')
                
                if not content_markdown:
                    # Fallback to raw content if markdown conversion failed
                    content_markdown = extracted_content.get('raw_content', 'Error: Could not extract content')
                
                # Index in Elasticsearch with just the markdown content
                result = index_student_profile(user_id, filename, content_markdown)
                
                if result["success"]:
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
        
        # --- PROFILE UPDATE ROUTES ---
        elif resource_type == 'update-profile' and request.method == 'POST':
            return handle_update_profile(request)
        
        elif resource_type == 'update-profile-content' and request.method == 'POST':
            return handle_update_profile_content(request)
        
        # --- SEARCH USER PROFILE (for agent tools) ---
        elif resource_type == 'search-user-profile' and request.method == 'POST':
            return handle_search(request)
        
        else:
            return add_cors_headers({'error': 'Not Found'}, 404)

            
    except Exception as e:
        logger.error(f"[PROFILE_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, 500)

