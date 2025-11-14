"""
Google Cloud Function for managing college admissions knowledge base.
Handles upload, list, and delete operations for the college_admissions_kb store.
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

# Knowledge base store name
KNOWLEDGE_BASE_STORE = os.getenv("DATA_STORE", "college_admissions_kb")

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
def knowledge_base_manager(request):
    """
    HTTP Cloud Function for managing knowledge base documents.
    
    Supported operations:
    - POST /upload-document - Upload a university research document
    - GET /list-documents - List all documents in knowledge base
    - DELETE /delete-document - Delete a document from knowledge base
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
        
        if path == '/upload-document' and request.method == 'POST':
            return handle_upload(request, headers)
        elif path == '/list-documents' and request.method == 'GET':
            return handle_list(request, headers)
        elif path == '/delete-document' and request.method == 'DELETE':
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
    """Handle document upload to knowledge base."""
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
        
        print(f"[UPLOAD] Uploading {file.filename} to knowledge base store")
        
        # Get the knowledge base store
        store_name = get_store_name(KNOWLEDGE_BASE_STORE)
        
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
                'message': f'Successfully uploaded {file.filename} to knowledge base',
                'filename': file.filename,
                'store_name': KNOWLEDGE_BASE_STORE,
                'size': file_size
            }), 200, headers
            
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
            
    except Exception as e:
        print(f"[UPLOAD ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500, headers


def handle_list(request, headers):
    """List all documents in knowledge base."""
    try:
        print(f"[LIST] Listing documents in knowledge base")
        
        # Get the knowledge base store
        store_name = get_store_name(KNOWLEDGE_BASE_STORE)
        print(f"[LIST] Store name: {store_name}")
        
        # Use REST API for pagination support (same as profile manager)
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
            
            if page_documents:
                all_documents.extend(page_documents)
                print(f"[LIST] Found {len(page_documents)} documents on page {page_count}")
            
            # Check for next page
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        
        # Format documents for response
        documents = []
        for doc in all_documents:
            documents.append({
                'name': doc.get('displayName', 'Unknown'),
                'uri': doc.get('uri', ''),
                'size': doc.get('sizeBytes', 0),
                'mime_type': doc.get('mimeType', ''),
                'resource_name': doc.get('name', '')
            })
        
        print(f"[LIST] Total documents found: {len(documents)}")
        
        return jsonify({
            'success': True,
            'documents': documents,
            'store': KNOWLEDGE_BASE_STORE,
            'count': len(documents)
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
    """Delete a document from knowledge base."""
    try:
        data = request.get_json()
        
        if not data or 'file_name' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing file_name in request'
            }), 400, headers
        
        file_name = data['file_name']
        
        print(f"[DELETE] Deleting {file_name} from knowledge base")
        
        # Get the knowledge base store
        store_name = get_store_name(KNOWLEDGE_BASE_STORE)
        
        # Get store info to find the file
        store = client.file_search_stores.get(name=store_name)
        
        file_to_delete = None
        if hasattr(store, 'files') and store.files:
            for file_ref in store.files:
                try:
                    file_info = client.files.get(name=file_ref)
                    if getattr(file_info, 'display_name', '') == file_name:
                        file_to_delete = file_ref
                        break
                except Exception as e:
                    print(f"[DELETE] Error checking file {file_ref}: {e}")
        
        if not file_to_delete:
            return jsonify({
                'success': False,
                'error': f'Document {file_name} not found in knowledge base'
            }), 404, headers
        
        # Remove from store
        client.file_search_stores.remove_files(
            file_search_store=store_name,
            files=[file_to_delete]
        )
        
        # Delete the file
        client.files.delete(name=file_to_delete)
        
        print(f"[DELETE] Successfully deleted {file_name}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {file_name} from knowledge base'
        }), 200, headers
        
    except Exception as e:
        print(f"[DELETE ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Delete failed: {str(e)}'
        }), 500, headers
