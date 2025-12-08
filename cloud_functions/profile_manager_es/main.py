"""
Google Cloud Function for managing student profiles in Elasticsearch.
Handles upload, list, and delete operations for student profiles.
"""

import os
import tempfile
import time
import requests
import functions_framework
from flask import jsonify, request
from google.cloud import storage
from elasticsearch import Elasticsearch
from datetime import datetime
import json
import logging
import io
from PyPDF2 import PdfReader
from docx import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ... (rest of imports and config)

def extract_text_from_file_content(file_content, filename):
    """Extract text from file content based on extension."""
    try:
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_ext == 'pdf':
            try:
                pdf_file = io.BytesIO(file_content)
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
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
                return text
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

def extract_profile_content_with_gemini(file_content, filename):
    """Extract structured content from student profile document."""
    try:
        # Extract text content
        content_text = extract_text_from_file_content(file_content, filename)
        
        if not content_text:
            content_text = "Could not extract text from document."
            
        # Truncate for summary if needed, but keep full text for indexing
        summary_text = content_text[:1000]
        
        structured_content = {
            "student_name": filename.replace('.pdf', '').replace('.txt', '').replace('.docx', ''),
            "email": "",
            "phone": "",
            "address": "",
            "academic_info": "",
            "interests": "",
            "goals": "",
            "summary": summary_text[:200] if summary_text else "Document processed"
        }
        
        return {
            "raw_content": content_text, # Now contains actual extracted text
            "structured_content": structured_content,
            "filename": filename
        }
            
    except Exception as e:
        logger.error(f"[EXTRACTION ERROR] Failed to extract content: {e}")
        return {
            "raw_content": "Error processing file",
            "structured_content": {
                "student_name": filename,
                "email": "",
                "phone": "",
                "address": "",
                "academic_info": "",
                "interests": "",
                "goals": "",
                "summary": "Error processing file"
            },
            "error": str(e)
        }

# Get configuration from environment variables
ES_CLOUD_ID = os.getenv("ES_CLOUD_ID")
ES_API_KEY = os.getenv("ES_API_KEY")
ES_INDEX_NAME = os.getenv("ES_INDEX_NAME", "student_profiles")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "college-counselling-478115-student-profiles")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

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

def index_student_profile(user_id, filename, content, metadata):
    """Index student profile in Elasticsearch."""
    try:
        client = get_elasticsearch_client()
        
        # Generate document ID
        import hashlib
        doc_content = f"{user_id}_{filename}_{content[:100]}"
        document_id = hashlib.sha256(doc_content.encode()).hexdigest()
        
        # Create document - match knowledge base manager ES structure
        document = {
            "document_id": document_id,
            "user_id": user_id,  # Use user_id like knowledge base manager ES
            "filename": filename,
            "file_name": filename,  # Add both for frontend compatibility
            "content": content,
            "metadata": metadata,
            "indexed_at": datetime.utcnow().isoformat(),
            "upload_date": datetime.utcnow().isoformat(),  # Add upload_date for frontend
            "file_size": len(content),
            "file_type": filename.split('.')[-1] if '.' in filename else 'unknown'
        }
        
        # Index document
        response = client.index(index=ES_INDEX_NAME, id=document_id, body=document)
        
        logger.info(f"[ES] Indexed profile {document_id} for user {user_id}")
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
                    "fields": ["content", "filename", "metadata.extracted_data"],
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
# DETERMINISTIC FIT ANALYSIS ENGINE
# ============================================

UNIVERSITIES_INDEX = os.getenv("UNIVERSITIES_INDEX", "universities")

import re

def parse_student_profile(profile_content):
    """Extract structured academic data from profile text content."""
    if not profile_content:
        return {}
    
    content = profile_content if isinstance(profile_content, str) else str(profile_content)
    
    def extract_float(pattern, text, default=None):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except:
                pass
        return default
    
    def extract_int(pattern, text, default=None):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except:
                pass
        return default
    
    # GPA extraction - try multiple patterns
    weighted_gpa = extract_float(r'Weighted\s*GPA[:\s]+(\d+\.\d+)', content)
    if not weighted_gpa:
        weighted_gpa = extract_float(r'GPA\s*\(Weighted\)[:\s]+(\d+\.\d+)', content)
    
    unweighted_gpa = extract_float(r'Unweighted\s*GPA[:\s]+(\d+\.\d+)', content)
    if not unweighted_gpa:
        unweighted_gpa = extract_float(r'GPA\s*\(Unweighted\)[:\s]+(\d+\.\d+)', content)
    
    uc_gpa = extract_float(r'UC\s*(?:Weighted\s*)?GPA[:\s]+(\d+\.\d+)', content)
    
    # Test scores
    sat_score = extract_int(r'SAT[:\s]+(\d{4})', content)
    if not sat_score:
        sat_score = extract_int(r'SAT\s*(?:Score)?[:\s]+(\d{4})', content)
    
    act_score = extract_int(r'ACT[:\s]+(\d{2})', content)
    if not act_score:
        act_score = extract_int(r'ACT\s*(?:Score)?[:\s]+(\d{2})', content)
    
    # AP courses and scores
    ap_scores = {}
    ap_pattern = r'AP\s+([A-Za-z\s]+?):\s*(\d)'
    for match in re.finditer(ap_pattern, content):
        course_name = match.group(1).strip()
        score = int(match.group(2))
        ap_scores[course_name] = score
    
    # Count total AP courses mentioned
    ap_count = len(ap_scores)
    if ap_count == 0:
        # Try alternate pattern
        ap_list_match = re.search(r'AP\s+Courses?[:\s]+(.*?)(?:\n\n|\Z)', content, re.DOTALL)
        if ap_list_match:
            ap_text = ap_list_match.group(1)
            ap_count = len(re.findall(r'AP\s+[A-Za-z]+', ap_text))
    
    # Intended major
    major_match = re.search(r'(?:Intended\s+)?Major[:\s]+([^\n,]+)', content, re.IGNORECASE)
    intended_major = major_match.group(1).strip() if major_match else None
    
    # Leadership detection
    has_leadership = bool(re.search(r'(?:President|Vice President|Captain|Leader|Founder|Director|Chair)', content, re.IGNORECASE))
    
    # Awards detection
    awards_section = re.search(r'AWARDS?[:\s]+(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
    awards_count = 0
    if awards_section:
        awards_count = len(re.findall(r'\n\s*[-•]', awards_section.group(1)))
    
    # Activity count
    activities_section = re.search(r'(?:ACTIVITIES|CLUBS)[:\s]+(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
    activities_count = 0
    if activities_section:
        activities_count = len(re.findall(r'\n\s*[-•]', activities_section.group(1)))
    
    return {
        'weighted_gpa': weighted_gpa or uc_gpa,
        'unweighted_gpa': unweighted_gpa,
        'sat_score': sat_score,
        'act_score': act_score,
        'ap_scores': ap_scores,
        'ap_count': ap_count if ap_count > 0 else len(ap_scores),
        'intended_major': intended_major,
        'has_leadership': has_leadership,
        'awards_count': awards_count,
        'activities_count': activities_count
    }


def fetch_university_data(university_id):
    """Fetch university admission data from the universities knowledge base."""
    try:
        client = get_elasticsearch_client()
        
        # Search for university by ID
        search_body = {
            "size": 1,
            "query": {
                "bool": {
                    "should": [
                        {"term": {"_id": university_id}},
                        {"term": {"university_id.keyword": university_id}},
                        {"match": {"metadata.official_name": university_id.replace("_", " ")}}
                    ]
                }
            }
        }
        
        response = client.search(index=UNIVERSITIES_INDEX, body=search_body)
        
        if response['hits']['total']['value'] > 0:
            return response['hits']['hits'][0]['_source']
        
        logger.warning(f"[FIT] University not found: {university_id}")
        return None
        
    except Exception as e:
        logger.error(f"[FIT] Error fetching university data: {e}")
        return None


def parse_gpa_range(gpa_string):
    """Parse GPA range like '3.90-4.00' into (min, max)."""
    if not gpa_string:
        return (3.5, 4.0)  # Default
    
    try:
        if '-' in str(gpa_string):
            parts = str(gpa_string).split('-')
            return (float(parts[0].strip()), float(parts[1].strip()))
        return (float(gpa_string), float(gpa_string))
    except:
        return (3.5, 4.0)


def parse_test_range(test_string):
    """Parse test score range like '1510-1560' into (min, max)."""
    if not test_string:
        return (1200, 1400)  # Default
    
    try:
        if '-' in str(test_string):
            parts = str(test_string).split('-')
            return (int(parts[0].strip()), int(parts[1].strip()))
        return (int(test_string), int(test_string))
    except:
        return (1200, 1400)


def calculate_comprehensive_fit(student_profile, university_data, intended_major=''):
    """
    Calculate comprehensive fit score using 7 factors.
    Returns fit_category, match_percentage, factors breakdown, and recommendations.
    """
    factors = []
    recommendations = []
    total_score = 0
    max_score = 150
    
    # Extract university admissions data
    admissions = university_data.get('admissions_data', {})
    current_status = admissions.get('current_status', {})
    admitted_profile = admissions.get('admitted_student_profile', {})
    
    acceptance_rate = current_status.get('overall_acceptance_rate', 50)
    
    gpa_data = admitted_profile.get('gpa', {})
    uni_gpa_range = gpa_data.get('unweighted_middle_50', '3.5-3.9')
    uni_gpa_25 = float(gpa_data.get('percentile_25', '3.5').replace('"', ''))
    uni_gpa_75 = float(gpa_data.get('percentile_75', '4.0').replace('"', ''))
    
    testing_data = admitted_profile.get('testing', {})
    sat_range = testing_data.get('sat_composite_middle_50', '1200-1400')
    act_range = testing_data.get('act_composite_middle_50', '26-32')
    
    # Get student data
    student_gpa = student_profile.get('weighted_gpa') or student_profile.get('unweighted_gpa') or 3.5
    student_sat = student_profile.get('sat_score')
    student_act = student_profile.get('act_score')
    ap_count = student_profile.get('ap_count', 0)
    ap_scores = student_profile.get('ap_scores', {})
    has_leadership = student_profile.get('has_leadership', False)
    awards_count = student_profile.get('awards_count', 0)
    
    # ============================================
    # FACTOR 1: GPA Match (40 points)
    # ============================================
    if student_gpa >= uni_gpa_75 + 0.1:
        gpa_score = 40
        gpa_detail = f"Your {student_gpa:.2f} exceeds 75th percentile ({uni_gpa_75})"
    elif student_gpa >= uni_gpa_75:
        gpa_score = 36
        gpa_detail = f"Your {student_gpa:.2f} is at 75th percentile"
    elif student_gpa >= (uni_gpa_25 + uni_gpa_75) / 2:
        gpa_score = 28
        gpa_detail = f"Your {student_gpa:.2f} is above median admits"
    elif student_gpa >= uni_gpa_25:
        gpa_score = 20
        gpa_detail = f"Your {student_gpa:.2f} is at 25th percentile"
    elif student_gpa >= uni_gpa_25 - 0.15:
        gpa_score = 12
        gpa_detail = f"Your {student_gpa:.2f} is slightly below typical range"
    else:
        gpa_score = 5
        gpa_detail = f"Your {student_gpa:.2f} is below typical admits"
        recommendations.append("Focus on strong upward trend in remaining semesters")
    
    total_score += gpa_score
    factors.append({'name': 'GPA Match', 'score': gpa_score, 'max': 40, 'detail': gpa_detail})
    
    # ============================================
    # FACTOR 2: Test Scores (25 points)
    # ============================================
    sat_25, sat_75 = parse_test_range(sat_range)
    act_25, act_75 = parse_test_range(act_range)
    
    test_score = 0
    test_detail = "No test scores provided"
    
    if student_sat:
        if student_sat >= sat_75:
            test_score = 25
            test_detail = f"Your SAT {student_sat} exceeds 75th percentile ({sat_75})"
        elif student_sat >= (sat_25 + sat_75) / 2:
            test_score = 20
            test_detail = f"Your SAT {student_sat} is in middle 50% ({sat_25}-{sat_75})"
        elif student_sat >= sat_25:
            test_score = 12
            test_detail = f"Your SAT {student_sat} is at 25th percentile"
        else:
            test_score = 5
            test_detail = f"Your SAT {student_sat} is below typical range"
            recommendations.append("Consider retaking SAT to reach middle 50% range")
    
    elif student_act:
        if student_act >= act_75:
            test_score = 25
            test_detail = f"Your ACT {student_act} exceeds 75th percentile ({act_75})"
        elif student_act >= (act_25 + act_75) / 2:
            test_score = 20
            test_detail = f"Your ACT {student_act} is in middle 50%"
        elif student_act >= act_25:
            test_score = 12
            test_detail = f"Your ACT {student_act} is at 25th percentile"
        else:
            test_score = 5
            test_detail = f"Your ACT {student_act} is below typical range"
    else:
        # Test optional consideration
        if current_status.get('is_test_optional'):
            test_score = 15
            test_detail = "Test optional - consider submitting if scores are strong"
        else:
            test_score = 8
            recommendations.append("Submit test scores as they are considered")
    
    total_score += test_score
    factors.append({'name': 'Test Scores', 'score': test_score, 'max': 25, 'detail': test_detail})
    
    # ============================================
    # FACTOR 3: Acceptance Rate (25 points)
    # ============================================
    if acceptance_rate >= 60:
        rate_score = 25
        rate_detail = f"{acceptance_rate}% acceptance - accessible"
    elif acceptance_rate >= 40:
        rate_score = 20
        rate_detail = f"{acceptance_rate}% acceptance - moderately selective"
    elif acceptance_rate >= 25:
        rate_score = 16
        rate_detail = f"{acceptance_rate}% acceptance - selective"
    elif acceptance_rate >= 15:
        rate_score = 12
        rate_detail = f"{acceptance_rate}% acceptance - highly selective"
    elif acceptance_rate >= 10:
        rate_score = 8
        rate_detail = f"{acceptance_rate}% acceptance - very competitive"
    elif acceptance_rate >= 5:
        rate_score = 5
        rate_detail = f"{acceptance_rate}% acceptance - extremely selective"
    else:
        rate_score = 2
        rate_detail = f"{acceptance_rate}% acceptance - ultra-selective (Ivy-tier)"
    
    total_score += rate_score
    factors.append({'name': 'Acceptance Rate', 'score': rate_score, 'max': 25, 'detail': rate_detail})
    
    # ============================================
    # FACTOR 4: Course Rigor (20 points)
    # ============================================
    ap_course_pts = min(10, ap_count * 1.2)
    
    # Quality of AP scores
    high_scores = sum(1 for s in ap_scores.values() if s >= 4)
    perfect_scores = sum(1 for s in ap_scores.values() if s == 5)
    quality_pts = min(10, high_scores * 2 + perfect_scores * 1)
    
    rigor_score = int(ap_course_pts + quality_pts)
    rigor_detail = f"{ap_count} AP courses"
    if high_scores > 0:
        rigor_detail += f", {high_scores} scores of 4+"
    
    if rigor_score < 10 and acceptance_rate < 20:
        recommendations.append("Consider taking additional AP courses to strengthen application")
    
    total_score += rigor_score
    factors.append({'name': 'Course Rigor', 'score': rigor_score, 'max': 20, 'detail': rigor_detail})
    
    # ============================================
    # FACTOR 5: Major Fit (15 points)
    # ============================================
    major_to_check = intended_major or student_profile.get('intended_major', '')
    major_score = 8  # Default - neutral
    major_detail = "No specific major selected"
    
    if major_to_check:
        # Check if major is available
        academic_structure = university_data.get('academic_structure', {})
        colleges = academic_structure.get('colleges', [])
        
        all_majors = []
        for college in colleges:
            for major in college.get('majors', []):
                all_majors.append(major.get('name', '').lower())
        
        major_lower = major_to_check.lower()
        
        if any(major_lower in m for m in all_majors):
            major_score = 15
            major_detail = f"{major_to_check} is offered"
        elif any(related in m for m in all_majors for related in [major_lower[:4], major_lower.split()[0].lower()]):
            major_score = 10
            major_detail = f"Related programs to {major_to_check} available"
        else:
            major_score = 5
            major_detail = f"{major_to_check} may not be directly offered"
            recommendations.append(f"Verify {major_to_check} is available or consider related majors")
    
    total_score += major_score
    factors.append({'name': 'Major Fit', 'score': major_score, 'max': 15, 'detail': major_detail})
    
    # ============================================
    # FACTOR 6: Activity Alignment (15 points)
    # ============================================
    activity_score = 5  # Base
    activity_details = []
    
    if has_leadership:
        activity_score += 4
        activity_details.append("Leadership experience")
    
    if awards_count >= 3:
        activity_score += 3
        activity_details.append(f"{awards_count} awards")
    elif awards_count >= 1:
        activity_score += 1
        activity_details.append(f"{awards_count} award(s)")
    
    # Cap at max and ensure positive
    activity_score = min(15, activity_score)
    activity_detail = ", ".join(activity_details) if activity_details else "Activities noted"
    
    if activity_score < 8 and acceptance_rate < 20:
        recommendations.append("Highlight unique achievements and leadership roles in essays")
    
    total_score += activity_score
    factors.append({'name': 'Activities', 'score': activity_score, 'max': 15, 'detail': activity_detail})
    
    # ============================================
    # FACTOR 7: Early Action Boost (10 points)
    # ============================================
    early_stats = current_status.get('early_admission_stats', [])
    early_score = 0
    early_detail = "No significant early advantage"
    
    for stat in early_stats:
        early_rate = stat.get('acceptance_rate', 0)
        plan_type = stat.get('plan_type', '')
        if early_rate and early_rate > acceptance_rate * 1.5:
            early_score = 10
            early_detail = f"{plan_type}: {early_rate}% vs {acceptance_rate}% regular"
            recommendations.append(f"Apply {plan_type} for significantly higher acceptance rate")
            break
        elif early_rate and early_rate > acceptance_rate * 1.2:
            early_score = 6
            early_detail = f"{plan_type} offers modest boost ({early_rate}%)"
            break
    
    total_score += early_score
    factors.append({'name': 'Early Action', 'score': early_score, 'max': 10, 'detail': early_detail})
    
    # ============================================
    # CALCULATE FINAL CATEGORY
    # ============================================
    match_percentage = int((total_score / max_score) * 100)
    
    if match_percentage >= 75:
        fit_category = 'SAFETY'
    elif match_percentage >= 55:
        fit_category = 'TARGET'
    elif match_percentage >= 35:
        fit_category = 'REACH'
    else:
        fit_category = 'SUPER_REACH'
    
    # Add default recommendation if none
    if not recommendations:
        if fit_category == 'SAFETY':
            recommendations.append("Strong match - focus on compelling essays and demonstrated interest")
        elif fit_category == 'TARGET':
            recommendations.append("Good fit - emphasize unique qualities in application")
    
    # Get university name
    uni_name = university_data.get('metadata', {}).get('official_name', 'University')
    
    return {
        'fit_category': fit_category,
        'match_percentage': match_percentage,
        'factors': factors,
        'recommendations': recommendations[:5],  # Limit to 5
        'university_name': uni_name,
        'calculated_at': datetime.utcnow().isoformat()
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
        
        # Fetch university data
        university_data = fetch_university_data(university_id)
        
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
        
        # Calculate comprehensive fit
        fit_analysis = calculate_comprehensive_fit(student_profile, university_data, intended_major)
        
        logger.info(f"[FIT] Calculated fit for {user_id} -> {university_id}: {fit_analysis['fit_category']} ({fit_analysis['match_percentage']}%)")
        
        return fit_analysis
        
    except Exception as e:
        logger.error(f"[FIT ERROR] {str(e)}")
        return None


def handle_update_college_list(request):
    """Add or remove a college from user's college list."""
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
        
        # Find user's profile document
        search_body = {
            "size": 1,
            "query": {
                "term": {"user_id.keyword": user_id}
            },
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({'error': 'No profile found for user'}, 404)
        
        doc_id = response['hits']['hits'][0]['_id']
        current_doc = response['hits']['hits'][0]['_source']
        
        # Get current college list or initialize empty
        college_list = current_doc.get('college_list', [])
        
        if action == 'add':
            # Check if already in list
            existing = next((c for c in college_list if c.get('university_id') == university['id']), None)
            if existing:
                return add_cors_headers({
                    'success': True,
                    'message': 'College already in list',
                    'college_list': college_list
                }, 200)
            
            # Calculate fit analysis automatically
            logger.info(f"[FIT] Auto-calculating fit for {university['id']}")
            fit_analysis = calculate_fit_for_college(user_id, university['id'], intended_major)
            
            # Add new college with fit analysis
            new_entry = {
                'university_id': university['id'],
                'university_name': university.get('name', ''),
                'added_at': datetime.utcnow().isoformat(),
                'intended_major': intended_major,
                'fit_analysis': fit_analysis
            }
            college_list.append(new_entry)
            
        elif action == 'remove':
            college_list = [c for c in college_list if c.get('university_id') != university['id']]
        
        # Update document with new college list
        es_client.update(
            index=ES_INDEX_NAME,
            id=doc_id,
            body={
                "doc": {
                    "college_list": college_list,
                    "college_list_updated_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        logger.info(f"[ES] Updated college list for user {user_id}: {action} {university['id']}")
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


def handle_get_college_list(request):
    """Get user's college list."""
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
        
        # Find user's profile document
        search_body = {
            "size": 1,
            "query": {
                "term": {"user_id.keyword": user_id}
            },
            "_source": ["college_list", "college_list_updated_at"],
            "sort": [{"indexed_at": {"order": "desc"}}]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        if response['hits']['total']['value'] == 0:
            return add_cors_headers({
                'success': True,
                'college_list': [],
                'message': 'No profile found, returning empty list'
            }, 200)
        
        source = response['hits']['hits'][0]['_source']
        college_list = source.get('college_list', [])
        
        return add_cors_headers({
            'success': True,
            'college_list': college_list,
            'updated_at': source.get('college_list_updated_at'),
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
                
                # Extract structured content
                extracted_content = extract_profile_content_with_gemini(file_content, filename)
                
                # Create metadata
                metadata = {
                    "filename": filename,
                    "user_id": user_id,  # Use user_id like knowledge base manager ES
                    "extracted_data": extracted_content,
                    "extraction_timestamp": datetime.utcnow().isoformat()
                }
                
                # Index in Elasticsearch
                result = index_student_profile(user_id, filename, extracted_content['raw_content'], metadata)
                
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
        
        elif resource_type == 'get-college-list':
            return handle_get_college_list(request)
        
        elif resource_type == 'update-fit-analysis' and request.method == 'POST':
            return handle_update_fit_analysis(request)
        
        elif resource_type == 'recalculate-fits':
            return handle_recalculate_all_fits(request)
        
        else:
            return add_cors_headers({'error': 'Not Found'}, 404)
            
    except Exception as e:
        logger.error(f"[PROFILE_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, 500)

