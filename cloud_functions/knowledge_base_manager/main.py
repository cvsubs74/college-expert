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
from google.cloud import storage

# Initialize Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'}
)

# Configuration
KNOWLEDGE_BASE_STORE = os.getenv("DATA_STORE", "college_admissions_kb")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET", "college-counselling-478115-knowledge-base")

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

def get_storage_path(filename):
    """Generate Firebase Storage path for knowledge base document."""
    return f"knowledge-base/{filename}"

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
        elif path == '/get-document-content' and request.method == 'POST':
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
    """Handle document upload to knowledge base - stores in Firebase Storage and File Search."""
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
        
        print(f"[UPLOAD] Uploading {file.filename} to knowledge base")
        
        # Get the knowledge base store
        store_name = get_store_name(KNOWLEDGE_BASE_STORE)
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name
        
        try:
            file_size = os.path.getsize(tmp_path)
            
            # Step 1: Upload to Firebase Storage
            storage_path = get_storage_path(file.filename)
            print(f"[UPLOAD] Uploading to Firebase Storage: {storage_path}")
            
            bucket = get_storage_bucket()
            blob = bucket.blob(storage_path)
            blob.upload_from_filename(tmp_path, content_type=file.content_type)
            
            # Set metadata
            blob.metadata = {
                'original_filename': file.filename,
                'uploaded_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'knowledge_base'
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
                'message': f'Successfully uploaded {file.filename} to knowledge base',
                'filename': file.filename,
                'storage_path': storage_path,
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
    """Delete a document from both GCS Storage and knowledge base using REST API."""
    try:
        data = request.get_json()
        document_name = data.get('document_name')
        filename = data.get('filename')
        
        if not document_name:
            return jsonify({
                'success': False,
                'error': 'Missing document_name parameter'
            }), 400, headers
        
        print(f"[DELETE] Deleting document: {document_name}")
        
        # Step 1: Delete from GCS Storage (if filename provided)
        if filename:
            try:
                storage_path = get_storage_path(filename)
                bucket = get_storage_bucket()
                blob = bucket.blob(storage_path)
                
                if blob.exists():
                    blob.delete()
                    print(f"[DELETE] Deleted from GCS Storage: {storage_path}")
                else:
                    print(f"[DELETE] File not found in GCS Storage: {storage_path}")
            except Exception as storage_error:
                print(f"[DELETE WARNING] GCS Storage deletion failed: {str(storage_error)}")
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
            'message': f'Successfully deleted document'
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
    """Get document content for preview from GCS Storage."""
    try:
        data = request.get_json()
        file_name = data.get('file_name')
        
        if not file_name:
            return jsonify({
                'success': False,
                'error': 'Missing file_name parameter'
            }), 400, headers
        
        print(f"[GET_CONTENT] Fetching content for: {file_name}")
        
        # Get from GCS Storage
        try:
            storage_path = get_storage_path(file_name)
            bucket = get_storage_bucket()
            blob = bucket.blob(storage_path)
            
            if not blob.exists():
                print(f"[GET_CONTENT] File not found in GCS: {storage_path}")
                return jsonify({
                    'success': False,
                    'error': 'Document not found in storage'
                }), 404, headers
            
            # Reload blob to get metadata
            blob.reload()
            
            # Get file metadata
            mime_type = blob.content_type or 'application/octet-stream'
            file_size = blob.size or 0
            upload_time = blob.time_created.strftime('%Y-%m-%d %H:%M:%S') if blob.time_created else 'Unknown'
            
            print(f"[GET_CONTENT] File metadata - mime_type: {mime_type}, size: {file_size}, filename: {file_name}")
            
            # Check if it's a PDF by extension if mime_type is generic
            is_pdf = 'pdf' in mime_type.lower() or file_name.lower().endswith('.pdf')
            
            if is_pdf:
                # Make blob publicly readable and get public URL
                blob.make_public()
                download_url = blob.public_url
                content = None
                print(f"[GET_CONTENT] Generated public URL for PDF: {download_url}")
            elif 'text' in mime_type.lower() or mime_type == 'application/json':
                try:
                    content = blob.download_as_text()
                    download_url = None
                except Exception as e:
                    print(f"[GET_CONTENT] Could not download as text: {str(e)}")
                    content = f"Document: {file_name}\n\nCould not extract text content.\n\nFile size: {file_size:,} bytes"
                    download_url = None
            else:
                content = f"Document: {file_name}\n\nPreview not available for this file type ({mime_type}).\n\nFile size: {file_size:,} bytes\nUploaded: {upload_time}"
                download_url = None
            
            print(f"[GET_CONTENT] Successfully retrieved content (content length: {len(content) if content else 0})")
            
            return jsonify({
                'success': True,
                'content': content,
                'mime_type': mime_type,
                'display_name': file_name,
                'storage_path': storage_path,
                'download_url': download_url,
                'file_size': file_size,
                'upload_time': upload_time,
                'is_pdf': is_pdf
            }), 200, headers
        
        except Exception as storage_error:
            print(f"[GET_CONTENT ERROR] Storage error: {str(storage_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Failed to get content from storage: {str(storage_error)}'
            }), 500, headers
        
    except Exception as e:
        print(f"[GET_CONTENT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Failed to get content: {str(e)}'
        }), 500, headers
