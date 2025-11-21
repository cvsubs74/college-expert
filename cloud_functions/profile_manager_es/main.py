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
    """Get profile content for preview from Google Cloud Storage."""
    try:
        data = request.get_json()
        logger.info(f"[GET_CONTENT] Received request data: {data}")
        
        if not data:
            logger.error(f"[GET_CONTENT ERROR] No JSON data in request")
            return add_cors_headers({
                'success': False,
                'error': 'No data provided in request'
            }, 400)
            
        user_email = data.get('user_email')
        filename = data.get('filename')
        
        if not user_email or not filename:
            logger.error(f"[GET_CONTENT ERROR] Missing user_email or filename in data: {data}")
            return add_cors_headers({
                'success': False,
                'error': 'Missing user_email or filename parameter'
            }, 400)
        
        logger.info(f"[GET_CONTENT] Fetching content for: {filename} (user: {user_email})")
        
        # Get Google Cloud Storage path
        # Sanitize user email for path (replace @ and . with _)
        user_email_sanitized = user_email.replace('@', '_').replace('.', '_')
        storage_path = f"profiles/{user_email_sanitized}/{filename}"
        bucket_name = 'college-counselling-478115-student-profiles'
        
        # Download from Google Cloud Storage
        storage_client = get_storage_client()
        if not storage_client:
            return add_cors_headers({
                'success': False,
                'error': 'Storage client not initialized'
            }, 500)
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(storage_path)
        
        if not blob.exists():
            logger.error(f"[GET_CONTENT ERROR] File not found: {storage_path}")
            return add_cors_headers({
                'success': False,
                'error': 'File not found in storage'
            }, 404)
        
        # Reload blob to get metadata
        blob.reload()
        
        # Get file metadata
        mime_type = blob.content_type or 'application/octet-stream'
        file_size = blob.size or 0
        upload_time = blob.time_created.strftime('%Y-%m-%d %H:%M:%S') if blob.time_created else 'Unknown'
        
        logger.info(f"[GET_CONTENT] File metadata - mime_type: {mime_type}, size: {file_size}, filename: {filename}")
        
        # Check if it's a PDF by extension if mime_type is generic
        is_pdf = 'pdf' in mime_type.lower() or filename.lower().endswith('.pdf')
        
        if is_pdf:
            # Make blob publicly readable temporarily and get public URL
            blob.make_public()
            download_url = blob.public_url
            content = None  # No text content for PDFs
            logger.info(f"[GET_CONTENT] Generated public URL for PDF: {download_url}")
        elif 'text' in mime_type.lower() or mime_type == 'application/json':
            try:
                content = blob.download_as_text()
                download_url = None
            except Exception as e:
                logger.error(f"[GET_CONTENT] Could not download as text: {str(e)}")
                content = f"Document: {filename}\n\nCould not extract text content.\n\nFile size: {file_size:,} bytes"
                download_url = None
        else:
            content = f"Document: {filename}\n\nPreview not available for this file type ({mime_type}).\n\nFile size: {file_size:,} bytes\nUploaded: {upload_time}"
            download_url = None
        
        logger.info(f"[GET_CONTENT] Successfully retrieved content (content length: {len(content) if content else 0})")
        
        return add_cors_headers({
            'success': True,
            'content': content,
            'mime_type': mime_type,
            'display_name': filename,
            'storage_path': storage_path,
            'download_url': download_url,
            'file_size': file_size,
            'upload_time': upload_time,
            'is_pdf': is_pdf
        }, 200)
        
    except Exception as e:
        logger.error(f"[GET_CONTENT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return add_cors_headers({
            'success': False,
            'error': f'Failed to get content: {str(e)}'
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
        
        else:
            return add_cors_headers({'error': 'Not Found'}, 404)
            
    except Exception as e:
        logger.error(f"[PROFILE_ES ERROR] {str(e)}")
        return add_cors_headers({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, 500)

