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

# Initialize Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'}
)

# Get the base data store name from environment variable
STUDENT_PROFILE_STORE_BASE = os.getenv("DATA_STORE", "student_profile")

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
            'Access-Control-Allow-Headers': 'Content-Type',
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
        elif path == '/delete-profile' and request.method == 'DELETE':
            return handle_delete(request, headers)
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
    """Handle student profile upload."""
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
            # Upload to File Search store
            config = {'display_name': file.filename}
            
            operation = client.file_search_stores.upload_to_file_search_store(
                file=tmp_path,
                file_search_store_name=store_name,
                config=config
            )
            
            # Wait for import to complete
            print(f"[UPLOAD] Waiting for import to complete...")
            while not operation.done:
                time.sleep(2)
                operation = client.operations.get(operation)
            
            print(f"[UPLOAD] Successfully uploaded {file.filename}")
            
            file_size = os.path.getsize(tmp_path)
            
            return jsonify({
                'success': True,
                'message': f'Successfully uploaded {file.filename}',
                'filename': file.filename,
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


def handle_delete(request, headers):
    """Delete a student profile."""
    try:
        data = request.get_json()
        document_name = data.get('document_name')
        
        if not document_name:
            return jsonify({
                'success': False,
                'error': 'Missing document_name parameter'
            }), 400, headers
        
        print(f"[DELETE] Deleting document: {document_name}")
        
        # Delete the document
        client.file_search_stores.documents.delete(name=document_name)
        
        print(f"[DELETE] Successfully deleted {document_name}")
        
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
