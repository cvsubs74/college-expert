"""
Knowledge Base Manager - RAG Implementation
Original implementation using only Google Gemini File Search API with RAG.
"""

import os
import tempfile
import time
import requests
import functions_framework
from flask import jsonify
from google import genai
from google.cloud import storage
import PyPDF2
from docx import Document as DocxDocument

# Initialize Gemini client
client = genai.Client(
    api_key=os.getenv('GEMINI_API_KEY'),
    http_options={'api_version': 'v1alpha'}
)

# Initialize Storage client
try:
    storage_client = storage.Client()
    print("[STORAGE] Storage client initialized successfully")
except Exception as e:
    print(f"[STORAGE ERROR] Failed to initialize Storage: {e}")
    storage_client = None

def add_cors_headers(response, status_code=200):
    """Add CORS headers to response."""
    if isinstance(response, dict):
        response = (jsonify(response).data, status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-User-Email',
            'Access-Control-Max-Age': '3600'
        })
    elif isinstance(response, tuple) and len(response) >= 2:
        if len(response) == 2:
            data, status = response
            headers = {}
        else:
            data, status, headers = response
        
        if not headers:
            headers = {}
        
        headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-User-Email',
            'Access-Control-Max-Age': '3600'
        })
        
        response = (data, status, headers)
    
    return response

def extract_text_from_file(file_path, filename):
    """Extract text from various file types."""
    try:
        file_ext = filename.lower().split('.')[-1]
        
        if file_ext == 'pdf':
            # Extract from PDF
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
            
        elif file_ext == 'docx':
            # Extract from DOCX
            doc = DocxDocument(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
            
        elif file_ext == 'txt':
            # Extract from text file
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        else:
            print(f"[TEXT EXTRACTION] Unsupported file type: {file_ext}")
            return ""
            
    except Exception as e:
        print(f"[TEXT EXTRACTION ERROR] Failed to extract text from {filename}: {str(e)}")
        return ""

def get_storage_path(filename):
    """Generate Firebase Storage path for knowledge base document."""
    return f"knowledge-base/{filename}"

def get_store_name(store_display_name):
    """Get the resource name of the File Search store using REST API."""
    try:
        # Use REST API to list stores
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print(f"[STORE ERROR] API key not available")
            return None
        
        print(f"[STORE] Looking for store: {store_display_name}")
        
        # List all stores using REST API
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/fileSearchStores",
            headers={"X-Goog-Api-Key": api_key},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            stores = data.get('fileSearchStores', [])
            
            for store in stores:
                if store.get('displayName') == store_display_name:
                    store_name = store.get('name')
                    print(f"[STORE] Found store {store_display_name}: {store_name}")
                    return store_name
            
            print(f"[STORE] Store {store_display_name} not found in {len(stores)} stores")
            print(f"[STORE] Available stores: {[s.get('displayName') for s in stores]}")
        else:
            print(f"[STORE ERROR] Failed to list stores: {response.status_code} - {response.text}")
        
        # Store doesn't exist, return hardcoded name if it's the expected one
        if store_display_name == "college_admissions_kb":
            store_name = "fileSearchStores/collegeadmissionskb-4boxdeg45i4o"
            print(f"[STORE] Using known store name: {store_name}")
            return store_name
        
        print(f"[STORE ERROR] Could not find store {store_display_name}")
        return None
        
    except Exception as e:
        print(f"[STORE ERROR] Exception: {e}")
        return None

def upload_to_file_search(file_path, filename, user_id):
    """Upload document to File Search store."""
    try:
        if not client:
            return {"success": False, "error": "Gemini client not available"}
        
        # Get or create the store
        store_name = get_store_name("college_admissions_kb")
        if not store_name:
            return {"success": False, "error": "Failed to get File Search store"}
        
        # Extract text from file
        text_content = extract_text_from_file(file_path, filename)
        if not text_content:
            return {"success": False, "error": "Failed to extract text from file"}
        
        # Upload to File Search
        print(f"[FILE SEARCH] Uploading {filename} to File Search...")
        
        # Use same approach as profile manager - client library with display_name config
        if not client:
            return {"success": False, "error": "Gemini client not available"}
        
        print(f"[UPLOAD] Uploading {filename} using client library approach like profile manager")
        
        # Create temporary file with text content
        import tempfile
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write(text_content)
                temp_file_path = temp_file.name
            
            print(f"[UPLOAD] Using client library with display_name config: {filename}")
            
            # Upload to File Search store using client library (same as profile manager)
            config = {'display_name': filename}
            
            operation = client.file_search_stores.upload_to_file_search_store(
                file=temp_file_path,
                file_search_store_name=store_name,
                config=config
            )
            
            # Wait for import to complete (same as profile manager)
            print(f"[UPLOAD] Waiting for File Search import to complete...")
            while not operation.done:
                time.sleep(2)
                operation = client.operations.get(operation)
            
            print(f"[UPLOAD] Successfully uploaded to File Search")
            file_name = f"uploaded-{filename.replace('.', '')}-{int(time.time())}"
            
        finally:
            # Clean up temporary file
            if temp_file_path:
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
        
        print(f"[FILE SEARCH] Successfully uploaded {filename}: {file_name}")
        
        return {
            "success": True,
            "file_name": file_name,
            "display_name": filename,
            "text_length": len(text_content),
            "store_name": store_name
        }
        
    except Exception as e:
        print(f"[FILE SEARCH ERROR] Failed to upload {filename}: {e}")
        return {"success": False, "error": str(e)}

def search_file_search(query, user_id=None, limit=10):
    """Search documents using File Search API."""
    try:
        if not client:
            return {"success": False, "error": "Gemini client not available"}
        
        # Get the store
        store_name = get_store_name("college_admissions_kb")
        if not store_name:
            return {"success": False, "error": "File Search store not available"}
        
        print(f"[FILE SEARCH] Searching for: {query}")
        
        # Use the REST API approach for File Search
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                return {"success": False, "error": "API key not available"}
            
            # Create a search request using generateContent REST API
            search_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            
            search_data = {
                "contents": [{
                    "parts": [{
                        "text": f"Search for documents related to: {query}. Return the document names and relevant content snippets."
                    }]
                }],
                "tools": [{
                    "file_search": {
                        "file_search_store_names": [store_name]
                    }
                }]
            }
            
            response = requests.post(
                search_url,
                headers={"Content-Type": "application/json"},
                json=search_data,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"[SEARCH ERROR] API returned status {response.status_code}: {response.text}")
                return {"success": False, "error": f"Search failed: {response.status_code} - {response.text}"}
            
            search_result = response.json()
            print(f"[SEARCH] GenerateContent search completed for: {query}")
            
            # Extract document references from the response
            documents = []
            
            # Check if the response has any citations or file references
            if 'candidates' in search_result:
                for candidate in search_result['candidates']:
                    if 'content' in candidate and 'parts' in candidate['content']:
                        for part in candidate['content']['parts']:
                            if 'text' in part:
                                # This is text content - parse for document info
                                text = part['text']
                                print(f"[SEARCH] Response text: {text[:200]}...")
                                
                                # For now, return the text as a snippet
                                doc_data = {
                                    "file_name": "search_result",
                                    "display_name": "Search Result",
                                    "score": 1.0,
                                    "snippets": [text]
                                }
                                documents.append(doc_data)
            
            print(f"[FILE SEARCH] Found {len(documents)} documents")
            
            return {
                "success": True,
                "documents": documents,
                "total_found": len(documents),
                "query": query,
                "search_method": "file_search_rag",
                "response_text": search_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '') if search_result.get('candidates') else None
            }
            
        except Exception as e:
            print(f"[SEARCH ERROR] GenerateContent search failed: {e}")
            # Fall back to empty results rather than error
            return {
                "success": True,
                "documents": [],
                "total_found": 0,
                "query": query,
                "search_method": "file_search_rag",
                "message": f"No results found: {str(e)}"
            }
        
    except Exception as e:
        print(f"[FILE SEARCH ERROR] Failed to search: {e}")
        return {"success": False, "error": str(e)}

def list_file_search_documents(limit=20):
    """List all documents in File Search store using REST API."""
    try:
        # Get the store
        store_name = get_store_name("college_admissions_kb")
        if not store_name:
            return {"success": False, "error": "File Search store not available"}
        
        # Use REST API to list documents (same as working list_documents function)
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return {"success": False, "error": "API key not available"}
        
        print(f"[LIST] Listing documents in {store_name}")
        print(f"[LIST] Store name: {store_name}")
        
        # Use REST API directly for pagination support
        base_url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}/documents"
        
        # Collect all documents across pages
        all_documents = []
        page_token = None
        page_count = 0
        
        while True:
            page_count += 1
            # Build URL with pagination parameters
            params = {'pageSize': min(limit, 20)}  # Max page size allowed by API
            if page_token:
                params['pageToken'] = page_token
            
            print(f"[LIST] Fetching page {page_count} from REST API")
            response = requests.get(
                base_url,
                headers={"X-Goog-Api-Key": api_key},
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"[LIST ERROR] API returned status {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                    "message": f"❌ Failed to list documents: API error {response.status_code}"
                }
            
            data = response.json()
            
            # Parse documents from current page
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
            
            # Check if there are more pages
            page_token = data.get('nextPageToken')
            if not page_token:
                print(f"[LIST] No more pages, stopping pagination")
                break
            
            print(f"[LIST] More pages available, continuing...")
            
            # Safety limit to prevent infinite loops
            if page_count >= 10:
                print(f"[LIST] Reached page limit, stopping pagination")
                break
        
        print(f"[LIST] Successfully listed {len(all_documents)} documents.")
        return {
            "success": True,
            "documents": all_documents,
            "message": f"✅ Successfully listed {len(all_documents)} documents."
        }
        
    except Exception as e:
        print(f"[LIST ERROR] Exception: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Failed to list documents: {str(e)}"
        }

def get_file_search_document(file_name):
    """Get specific document from File Search."""
    try:
        # Use REST API directly like list_documents does
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"success": False, "error": "API key not available"}
        
        print(f"[GET] Retrieving document via REST API: {file_name}")
        
        # Use the same REST API approach as list_documents
        response = requests.get(
            f"https://generativelanguage.googleapis.com/v1alpha/{file_name}",
            headers={"X-Goog-Api-Key": api_key},
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"[GET ERROR] API returned status {response.status_code}: {response.text}")
            return {
                "success": False,
                "error": f"API error: {response.status_code} - {response.text}"
            }
        
        data = response.json()
        print(f"[GET] Successfully retrieved document: {data.get('displayName', 'Unknown')}")
        
        doc_data = {
            "file_name": data.get('name', ''),
            "display_name": data.get('displayName', ''),
            "mime_type": data.get('mimeType', ''),
            "text": data.get('text', ''),
            "create_time": data.get('createTime', '')
        }
        
        return {
            "success": True,
            "document": doc_data
        }
        
    except Exception as e:
        print(f"Error getting file search document: {e}")
        return {"success": False, "error": str(e)}

def delete_file_search_document(file_name):
    """Delete document from File Search using REST API."""
    try:
        # Use REST API to delete document
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            return {"success": False, "error": "API key not available"}
        
        # Extract document ID from full name (format: fileSearchStores/store-id/documents/document-id)
        if '/' in file_name:
            # Full name provided, use as is
            doc_path = file_name
        else:
            # Just document ID provided, construct full path
            store_name = get_store_name("college_admissions_kb")
            if not store_name:
                return {"success": False, "error": "File Search store not available"}
            store_id = store_name.split('/')[-1] if '/' in store_name else store_name
            doc_path = f"fileSearchStores/{store_id}/documents/{file_name}"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{doc_path}"
        params = {
            "key": api_key,
            "force": "true"  # Force delete even if document has chunks
        }
        
        response = requests.delete(url, params=params, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": f"Document {file_name} deleted successfully"
            }
        else:
            return {
                "success": False, 
                "error": f"API request failed: {response.status_code} - {response.text}"
            }
        
    except Exception as e:
        print(f"[FILE SEARCH ERROR] Failed to delete document: {e}")
        return {"success": False, "error": str(e)}

def knowledge_base_manager_http(request):
    """Main HTTP entry point for Knowledge Base Manager (RAG)."""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return add_cors_headers({}, 200)
    
    try:
        # Get request path
        path = request.path.strip('/') or 'health'
        print(f"[RAG MANAGER] Request path: {path}")
        
        # Health check
        if path == 'health':
            health_status = {
                "status": "healthy",
                "service": "knowledge_base_manager",
                "database": "file_search_rag",
                "timestamp": time.time()
            }
            if not client:
                health_status["database"] = "rag_error"
            return add_cors_headers(health_status, 200)
        
        # Route to appropriate handler
        if path == 'upload' or path == 'upload-document':
            return handle_upload(request)
        elif path == 'search':
            return handle_search(request)
        elif path == 'documents':
            return handle_documents(request)
        elif path == 'get-document':
            return handle_get_document(request)
        elif path == 'get-document-content':
            return handle_get_document_content(request)
        elif path == 'delete':
            return handle_delete(request)
        else:
            return add_cors_headers({"error": "Endpoint not found"}, 404)
            
    except Exception as e:
        print(f"[RAG MANAGER ERROR] {e}")
        return add_cors_headers({"error": f"Internal server error: {str(e)}"}, 500)

def handle_get_document(request):
    """Handle getting a specific document's content."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    data = request.get_json()
    if not data:
        return add_cors_headers({"error": "No JSON data provided"}, 400)
    
    file_name = data.get('file_name')
    
    if not file_name:
        return add_cors_headers({"error": "file_name is required"}, 400)
    
    result = get_file_search_document(file_name)
    
    if result['success']:
        return add_cors_headers(result, 200)
    else:
        return add_cors_headers({"error": result['error']}, 404)

def handle_get_document_content(request):
    """Get document content for preview from Google Cloud Storage."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    try:
        data = request.get_json()
        print(f"[GET_DOCUMENT_CONTENT] Received request data: {data}")
        
        if not data:
            print(f"[GET_DOCUMENT_CONTENT ERROR] No JSON data in request")
            return add_cors_headers({
                'success': False,
                'error': 'No data provided in request'
            }, 400)
        
        file_name = data.get('file_name')
        
        if not file_name:
            print(f"[GET_DOCUMENT_CONTENT ERROR] Missing file_name in data: {data}")
            return add_cors_headers({
                'success': False,
                'error': 'Missing file_name parameter'
            }, 400)
        
        print(f"[GET_DOCUMENT_CONTENT] Fetching content for: {file_name}")
        
        # Get Google Cloud Storage path
        storage_path = get_storage_path(file_name)
        bucket_name = 'college-counselling-478115-knowledge-base'
        
        # Download from Google Cloud Storage
        if not storage_client:
            return add_cors_headers({
                'success': False,
                'error': 'Storage client not initialized'
            }, 500)
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(storage_path)
        
        if not blob.exists():
            print(f"[GET_DOCUMENT_CONTENT ERROR] File not found: {storage_path}")
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
        
        print(f"[GET_DOCUMENT_CONTENT] File metadata - mime_type: {mime_type}, size: {file_size}, filename: {file_name}")
        
        # Check if it's a PDF by extension if mime_type is generic
        is_pdf = 'pdf' in mime_type.lower() or file_name.lower().endswith('.pdf')
        
        if is_pdf:
            # Make blob publicly readable temporarily and get public URL
            blob.make_public()
            download_url = blob.public_url
            content = None  # No text content for PDFs
            print(f"[GET_DOCUMENT_CONTENT] Generated public URL for PDF: {download_url}")
        elif 'text' in mime_type.lower() or mime_type == 'application/json':
            try:
                content = blob.download_as_text()
                download_url = None
            except Exception as e:
                print(f"[GET_DOCUMENT_CONTENT] Could not download as text: {str(e)}")
                content = f"Document: {file_name}\n\nCould not extract text content.\n\nFile size: {file_size:,} bytes"
                download_url = None
        else:
            content = f"Document: {file_name}\n\nPreview not available for this file type ({mime_type}).\n\nFile size: {file_size:,} bytes\nUploaded: {upload_time}"
            download_url = None
        
        print(f"[GET_DOCUMENT_CONTENT] Successfully retrieved content (content length: {len(content) if content else 0})")
        
        return add_cors_headers({
            'success': True,
            'content': content,
            'mime_type': mime_type,
            'display_name': file_name,
            'storage_path': storage_path,
            'download_url': download_url,
            'file_size': file_size,
            'upload_time': upload_time,
            'is_pdf': is_pdf
        }, 200)
        
    except Exception as e:
        print(f"[GET_DOCUMENT_CONTENT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return add_cors_headers({
            'success': False,
            'error': f'Failed to get content: {str(e)}'
        }, 500)

def handle_upload(request):
    """Handle file upload to File Search."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return add_cors_headers({"error": "No file provided"}, 400)
        
        file = request.files['file']
        if file.filename == '':
            return add_cors_headers({"error": "No file selected"}, 400)
        
        # Get user ID
        user_id = request.form.get('user_id', 'anonymous')
        
        # Save file temporarily
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            # Upload to File Search
            result = upload_to_file_search(temp_path, file.filename, user_id)
            
            if result['success']:
                return add_cors_headers({
                    "success": True,
                    "message": "File uploaded successfully",
                    "file_name": result['file_name'],
                    "display_name": result['display_name'],
                    "text_length": result['text_length']
                }, 200)
            else:
                return add_cors_headers({"error": result['error']}, 500)
        
        finally:
            # Clean up temporary file
            if temp_path:
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    except Exception as e:
        print(f"[UPLOAD ERROR] {e}")
        return add_cors_headers({"error": f"Upload failed: {str(e)}"}, 500)

def handle_search(request):
    """Handle search requests."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    data = request.get_json()
    if not data:
        return add_cors_headers({"error": "No JSON data provided"}, 400)
    
    query = data.get('query', '')
    user_id = data.get('user_id')
    limit = data.get('limit', 10)
    
    if not query:
        return add_cors_headers({"error": "Query is required"}, 400)
    
    result = search_file_search(query, user_id, limit)
    
    if result['success']:
        return add_cors_headers(result, 200)
    else:
        return add_cors_headers({"error": result['error']}, 500)

def handle_documents(request):
    """Handle document operations."""
    if request.method == 'GET':
        # List documents
        limit = int(request.args.get('limit', 20))
        result = list_file_search_documents(limit)
        
        if result['success']:
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers({"error": result['error']}, 500)
    
    elif request.method == 'POST':
        # Get specific document
        data = request.get_json()
        file_name = data.get('file_name')
        
        if not file_name:
            return add_cors_headers({"error": "file_name is required"}, 400)
        
        result = get_file_search_document(file_name)
        
        if result['success']:
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers({"error": result['error']}, 404)
    
    else:
        return add_cors_headers({"error": "Method not allowed"}, 405)

def handle_delete(request):
    """Handle document deletion."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    data = request.get_json()
    if not data:
        return add_cors_headers({"error": "No JSON data provided"}, 400)
    
    file_name = data.get('file_name')
    
    if not file_name:
        return add_cors_headers({"error": "file_name is required"}, 400)
    
    result = delete_file_search_document(file_name)
    
    if result['success']:
        return add_cors_headers(result, 200)
    else:
        return add_cors_headers({"error": result['error']}, 500)

# Entry point for Cloud Functions
def knowledge_base_manager_http_entry(request):
    """Entry point that redirects to the main handler."""
    return knowledge_base_manager_http(request)
