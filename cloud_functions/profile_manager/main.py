"""
Google Cloud Function for managing student profiles in File Search store.
Handles upload, list, and delete operations for the student_profile store.
"""

import os
import tempfile
import time
import requests
import functions_framework
from flask import jsonify
from google import genai
from google.cloud import storage

# Initialize Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'}
)

# Get configuration from environment variables
STUDENT_PROFILE_STORE_BASE = os.getenv("DATA_STORE", "student_profile")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET", "college-counselling-478115-student-profiles")

# Initialize GCS client
storage_client = storage.Client()

def get_storage_bucket():
    """Get or create GCS bucket."""
    try:
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        if not bucket.exists():
            bucket = storage_client.create_bucket(GCS_BUCKET_NAME, location="us-east1")
            print(f"[STORAGE] Created bucket: {GCS_BUCKET_NAME}")
        return bucket
    except Exception as e:
        print(f"[STORAGE ERROR] {str(e)}")
        raise

def get_storage_path(user_email, filename):
    """Generate Firebase Storage path for user profile."""
    # Sanitize email for path
    sanitized_email = user_email.replace('@', '_').replace('.', '_').lower()
    return f"profiles/{sanitized_email}/{filename}"

def get_user_store_name(user_email):
    """
    Generate user-specific store name from email.
    Pattern: student_profile_<sanitized_email>
    Example: student_profile_john_doe_gmail_com
    """
    # Sanitize email for use in store name (replace @ and . with _)
    sanitized_email = user_email.replace('@', '_').replace('.', '_').lower()
    return f"{STUDENT_PROFILE_STORE_BASE}_{sanitized_email}"

def get_store_name(store_display_name):
    """Get the resource name of the File Search store, creating it if it doesn't exist."""
    try:
        # List all stores to find ours
        for store in client.file_search_stores.list():
            if getattr(store, 'display_name', '') == store_display_name:
                print(f"[STORE] Found store {store_display_name}: {store.name}")
                return store.name
        
        # Store doesn't exist, create it
        print(f"[STORE] Store {store_display_name} not found, creating...")
        store = client.file_search_stores.create(
            config={'display_name': store_display_name}
        )
        print(f"[STORE] Created store: {store.name}")
        return store.name
    except Exception as e:
        print(f"[STORE ERROR] Failed to get/create store: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@functions_framework.http
def profile_manager(request):
    """
    HTTP Cloud Function for managing student profiles.
    
    Supported operations:
    - POST /upload-profile - Upload a student profile
    - GET /list-profiles - List all student profiles
    - DELETE /delete-profile - Delete a student profile
    """
    
    # Enable CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-User-Email',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    try:
        path = request.path
        
        if path == '/upload-profile' and request.method == 'POST':
            return handle_upload(request, headers)
        elif path == '/list-profiles' and request.method == 'GET':
            return handle_list(request, headers)
        elif path == '/search' and request.method == 'POST':
            return handle_search(request, headers)
        elif path == '/delete-profile' and request.method == 'DELETE':
            return handle_delete(request, headers)
        elif path == '/get-profile-content' and request.method == 'POST':
            return handle_get_content(request, headers)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown endpoint: {path}'
            }), 404, headers
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500, headers


def handle_upload(request, headers):
    """Handle student profile upload - stores in Firebase Storage and File Search."""
    try:
        # Get file from request
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400, headers
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400, headers
        
        # Get user email from form data
        user_email = request.form.get('user_email')
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'Missing user_email parameter'
            }), 400, headers
        
        # Generate user-specific store name
        user_store = get_user_store_name(user_email)
        print(f"[UPLOAD] Uploading {file.filename} to {user_store} for user {user_email}")
        
        # Get the store resource name
        store_name = get_store_name(user_store)
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            file_size = os.path.getsize(tmp_path)
            
            # Step 1: Upload to Firebase Storage
            storage_path = get_storage_path(user_email, file.filename)
            print(f"[UPLOAD] Uploading to Firebase Storage: {storage_path}")
            
            bucket = get_storage_bucket()
            blob = bucket.blob(storage_path)
            blob.upload_from_filename(tmp_path, content_type=file.content_type)
            
            # Make the file accessible with authentication
            blob.metadata = {
                'user_email': user_email,
                'original_filename': file.filename,
                'uploaded_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            blob.patch()
            
            print(f"[UPLOAD] Successfully uploaded to Firebase Storage")
            
            # Step 2: Upload to File Search store for AI processing
            config = {'display_name': file.filename}
            
            operation = client.file_search_stores.upload_to_file_search_store(
                file=tmp_path,
                file_search_store_name=store_name,
                config=config
            )
            
            # Wait for import to complete
            print(f"[UPLOAD] Waiting for File Search import to complete...")
            while not operation.done:
                time.sleep(2)
                operation = client.operations.get(operation)
            
            print(f"[UPLOAD] Successfully uploaded to File Search")
            
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {file.filename}',
                'filename': file.filename,
                'storage_path': storage_path,
                'store_name': user_store,
                'user_email': user_email,
                'size_bytes': file_size
            }), 200, headers
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        print(f"[UPLOAD ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500, headers


def handle_list(request, headers):
    """List all student profiles for a specific user."""
    try:
        # Get user email from query parameters
        user_email = request.args.get('user_email')
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'Missing user_email parameter'
            }), 400, headers
        
        # Generate user-specific store name
        user_store = get_user_store_name(user_email)
        print(f"[LIST] Listing documents in {user_store} for user {user_email}")
        
        # Get the store resource name
        store_name = get_store_name(user_store)
        print(f"[LIST] Store name: {store_name}")
        
        # Use REST API for pagination support
        api_key = os.getenv("GEMINI_API_KEY")
        base_url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}/documents"
        
        # Collect all documents across pages
        all_documents = []
        page_token = None
        page_count = 0
        
        while True:
            page_count += 1
            params = {'pageSize': 20}
            if page_token:
                params['pageToken'] = page_token
            
            print(f"[LIST] Fetching page {page_count}")
            response = requests.get(
                base_url,
                headers={"X-Goog-Api-Key": api_key},
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"[LIST ERROR] API returned status {response.status_code}: {response.text}")
                return jsonify({
                    'success': False,
                    'error': f'API error: {response.status_code}'
                }), 500, headers
            
            data = response.json()
            page_documents = data.get('documents', [])
            print(f"[LIST] Page {page_count}: Found {len(page_documents)} documents")
            
            for doc in page_documents:
                all_documents.append({
                    'name': doc.get('name', ''),
                    'display_name': doc.get('displayName', ''),
                    'create_time': doc.get('createTime', ''),
                    'update_time': doc.get('updateTime', ''),
                    'state': doc.get('state', ''),
                    'size_bytes': int(doc.get('sizeBytes', 0)),
                    'mime_type': doc.get('mimeType', '')
                })
            
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        
        print(f"[LIST] Total: Found {len(all_documents)} documents")
        
        return jsonify({
            'success': True,
            'store_name': user_store,
            'user_email': user_email,
            'documents': all_documents,
            'count': len(all_documents)
        }), 200, headers
        
    except Exception as e:
        print(f"[LIST ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'List failed: {str(e)}'
        }), 500, headers


def handle_search(request, headers):
    """Search student profile using File Search API."""
    try:
        data = request.get_json()
        print(f"[SEARCH] Received request data: {data}")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided in request'
            }), 400, headers
        
        user_email = data.get('user_email')
        query = data.get('query', 'student academic profile')
        limit = data.get('limit', 5)
        
        if not user_email:
            return jsonify({
                'success': False,
                'error': 'Missing user_email parameter'
            }), 400, headers
        
        # Generate user-specific store name
        user_store = get_user_store_name(user_email)
        print(f"[SEARCH] Searching in {user_store} for user {user_email}")
        
        # Get the store resource name
        store_name = get_store_name(user_store)
        print(f"[SEARCH] Store name: {store_name}")
        
        # Use Gemini's generateContent with File Search
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key not available'
            }), 500, headers
        
        search_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        
        search_data = {
            "contents": [{
                "parts": [{
                    "text": f"Search for student profile information related to: {query}. Provide a comprehensive summary of the student's academic profile, including grades, courses, extracurricular activities, and any other relevant information."
                }]
            }],
            "tools": [{
                "file_search": {
                    "file_search_store_names": [store_name]
                }
            }]
        }
        
        print(f"[SEARCH] Calling Gemini API for query: {query}")
        response = requests.post(
            search_url,
            headers={"Content-Type": "application/json"},
            json=search_data,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"[SEARCH ERROR] API returned status {response.status_code}: {response.text}")
            return jsonify({
                'success': False,
                'error': f'Search failed: {response.status_code} - {response.text}'
            }), 500, headers
        
        search_result = response.json()
        print(f"[SEARCH] GenerateContent search completed")
        
        # Extract response and build documents list
        documents = []
        response_text = ""
        
        if 'candidates' in search_result:
            for candidate in search_result['candidates']:
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            text = part['text']
                            response_text = text
                            print(f"[SEARCH] Response text length: {len(text)}")
                            
                            # Create a document structure
                            doc_data = {
                                "id": f"profile_{user_email}",
                                "score": 1.0,
                                "document": {
                                    "filename": f"profile_{user_email}.pdf",
                                    "user_id": user_email,
                                    "content": text,
                                    "indexed_at": time.time(),
                                    "upload_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                                    "metadata": {
                                        "user_email": user_email,
                                        "query": query
                                    }
                                }
                            }
                            documents.append(doc_data)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total_found': len(documents),
            'user_email': user_email,
            'query': query,
            'response_text': response_text
        }), 200, headers
        
    except Exception as e:
        print(f"[SEARCH ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500, headers



def handle_delete(request, headers):
    """Delete a student profile from both Firebase Storage and File Search using REST API."""
    try:
        data = request.get_json()
        document_name = data.get('document_name')
        user_email = data.get('user_email')
        filename = data.get('filename')
        
        if not document_name:
            return jsonify({
                'success': False,
                'error': 'Missing document_name parameter'
            }), 400, headers
        
        print(f"[DELETE] Deleting document: {document_name}")
        
        # Step 1: Delete from Firebase Storage (if user_email and filename provided)
        if user_email and filename:
            try:
                storage_path = get_storage_path(user_email, filename)
                bucket = get_storage_bucket()
                blob = bucket.blob(storage_path)
                
                if blob.exists():
                    blob.delete()
                    print(f"[DELETE] Deleted from Firebase Storage: {storage_path}")
                else:
                    print(f"[DELETE] File not found in Firebase Storage: {storage_path}")
            except Exception as storage_error:
                print(f"[DELETE WARNING] Firebase Storage deletion failed: {str(storage_error)}")
                # Continue with File Search deletion even if storage deletion fails
        
        # Step 2: Delete from File Search using REST API with force=true
        api_key = os.getenv("GEMINI_API_KEY")
        delete_url = f"https://generativelanguage.googleapis.com/v1beta/{document_name}"
        
        delete_response = requests.delete(
            delete_url,
            headers={"X-Goog-Api-Key": api_key},
            params={"force": "true"},  # Force delete even if document has chunks
            timeout=30
        )
        
        if delete_response.status_code == 200:
            print(f"[DELETE] Successfully deleted from File Search: {document_name}")
        elif delete_response.status_code == 404:
            print(f"[DELETE] Document not found in File Search: {document_name}")
        else:
            print(f"[DELETE ERROR] File Search deletion failed: {delete_response.status_code} - {delete_response.text}")
            return jsonify({
                'success': False,
                'error': f'Failed to delete from File Search: {delete_response.status_code}'
            }), 500, headers
        
        return jsonify({
            'success': True,
            'message': 'Successfully deleted profile'
        }), 200, headers
        
    except Exception as e:
        print(f"[DELETE ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Delete failed: {str(e)}'
        }), 500, headers


def handle_get_content(request, headers):
    """Get document content for preview from Firebase Storage."""
    try:
        data = request.get_json()
        print(f"[GET_CONTENT] Received request data: {data}")
        
        if not data:
            print(f"[GET_CONTENT ERROR] No JSON data in request")
            return jsonify({
                'success': False,
                'error': 'No data provided in request'
            }), 400, headers
        
        user_email = data.get('user_email')
        filename = data.get('filename')
        
        if not user_email or not filename:
            print(f"[GET_CONTENT ERROR] Missing user_email or filename in data: {data}")
            return jsonify({
                'success': False,
                'error': 'Missing user_email or filename parameter'
            }), 400, headers
        
        print(f"[GET_CONTENT] Fetching content for: {filename} (user: {user_email})")
        
        # Get Firebase Storage path
        storage_path = get_storage_path(user_email, filename)
        
        # Download from Firebase Storage
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)
        
        if not blob.exists():
            print(f"[GET_CONTENT ERROR] File not found: {storage_path}")
            return jsonify({
                'success': False,
                'error': 'File not found in storage'
            }), 404, headers
        
        # Reload blob to get metadata
        blob.reload()
        
        # For PDFs and binary files, return a message
        # For text files, try to download as text
        mime_type = blob.content_type or 'application/octet-stream'
        file_size = blob.size or 0
        upload_time = blob.time_created.strftime('%Y-%m-%d %H:%M:%S') if blob.time_created else 'Unknown'
        
        print(f"[GET_CONTENT] File metadata - mime_type: {mime_type}, size: {file_size}, filename: {filename}")
        
        # Check if it's a PDF by extension if mime_type is generic
        is_pdf = 'pdf' in mime_type.lower() or filename.lower().endswith('.pdf')
        
        if is_pdf:
            # Make blob publicly readable temporarily and get public URL
            blob.make_public()
            download_url = blob.public_url
            content = None  # No text content for PDFs
            print(f"[GET_CONTENT] Generated public URL for PDF: {download_url}")
        elif 'text' in mime_type.lower() or mime_type == 'application/json':
            try:
                content = blob.download_as_text()
                download_url = None
            except Exception as e:
                print(f"[GET_CONTENT] Could not download as text: {str(e)}")
                content = f"Document: {filename}\n\nCould not extract text content.\n\nFile size: {file_size:,} bytes"
                download_url = None
        else:
            content = f"Document: {filename}\n\nPreview not available for this file type ({mime_type}).\n\nFile size: {file_size:,} bytes\nUploaded: {upload_time}"
            download_url = None
        
        print(f"[GET_CONTENT] Successfully retrieved content (content length: {len(content) if content else 0})")
        
        return jsonify({
            'success': True,
            'content': content,
            'mime_type': mime_type,
            'display_name': filename,
            'storage_path': storage_path,
            'download_url': download_url,
            'file_size': file_size,
            'upload_time': upload_time,
            'is_pdf': is_pdf
        }), 200, headers
        
    except Exception as e:
        print(f"[GET_CONTENT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to get content: {str(e)}'
        }), 500, headers
