"""
Document Management Tools for Gemini File Search Store.

These tools allow uploading, listing, and deleting documents in the File Search store.
Based on the Regulatory Risk Analyzer cloud function implementation.
"""
import os
import tempfile
import time
import requests
from typing import Dict, Any, List, Optional
from google import genai
from .tool_logger import log_tool_call

# Initialize Gemini Developer API client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options={'api_version': 'v1alpha'}
)

# Get the data store name from environment variable
DATA_STORE = os.getenv("DATA_STORE", "college_admissions_kb")


def get_store_name():
    """Get the resource name of the File Search store, creating it if it doesn't exist."""
    try:
        # List all stores to find ours
        for store in client.file_search_stores.list():
            if getattr(store, 'display_name', '') == DATA_STORE:
                print(f"[STORE] Found store {DATA_STORE}: {store.name}")
                return store.name
        
        # Store doesn't exist, create it
        print(f"[STORE] Store {DATA_STORE} not found, creating...")
        store = client.file_search_stores.create(
            config={'display_name': DATA_STORE}
        )
        print(f"[STORE] Created store: {store.name}")
        return store.name
    except Exception as e:
        print(f"[STORE ERROR] Failed to get/create store: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@log_tool_call
def upload_document(
    file_path: str,
    display_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a document to the File Search store.
    
    Args:
        file_path: Path to the file to upload
        display_name: Optional display name for the document (defaults to filename)
        
    Returns:
        Dictionary with upload status and details
        
    Example:
        upload_document(
            file_path="/path/to/document.pdf",
            display_name="College Admissions Guide 2024"
        )
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "message": f"❌ File does not exist: {file_path}"
            }
        
        filename = os.path.basename(file_path)
        if display_name is None:
            display_name = filename
        
        print(f"[UPLOAD] Uploading {filename} to {DATA_STORE}")
        
        # Get the store resource name
        store_name = get_store_name()
        
        # Upload to File Search store
        config = {'display_name': display_name}
        
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
            config=config
        )
        
        # Wait for import to complete
        print(f"[UPLOAD] Waiting for import to complete...")
        while not operation.done:
            time.sleep(2)
            operation = client.operations.get(operation)
        
        print(f"[UPLOAD] Successfully uploaded {filename}")
        
        file_size = os.path.getsize(file_path)
        
        return {
            "success": True,
            "message": f"✅ Successfully uploaded {filename} to File Search store",
            "filename": filename,
            "display_name": display_name,
            "store_name": DATA_STORE,
            "operation_name": operation.name,
            "size_bytes": file_size
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Upload failed: {str(e)}"
        }


@log_tool_call
def list_documents() -> Dict[str, Any]:
    """
    List all documents in the File Search store.
    
    Returns:
        Dictionary with list of documents and their metadata
        
    Example:
        list_documents()
    """
    try:
        print(f"[LIST] Listing documents in {DATA_STORE}")
        
        # Get the store resource name
        store_name = get_store_name()
        print(f"[LIST] Store name: {store_name}")
        
        # Use REST API directly for pagination support
        api_key = os.getenv("GEMINI_API_KEY")
        base_url = f"https://generativelanguage.googleapis.com/v1beta/{store_name}/documents"
        
        # Collect all documents across pages
        all_documents = []
        page_token = None
        page_count = 0
        
        while True:
            page_count += 1
            # Build URL with pagination parameters
            params = {'pageSize': 20}  # Max page size allowed by API
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
        
        print(f"[LIST] Total: Found {len(all_documents)} documents across {page_count} page(s) in {DATA_STORE}")
        
        return {
            "success": True,
            "store_name": DATA_STORE,
            "documents": all_documents,
            "count": len(all_documents),
            "pages_fetched": page_count,
            "message": f"✅ Found {len(all_documents)} documents in {DATA_STORE}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ List failed: {str(e)}"
        }


@log_tool_call
def delete_document(document_name: str) -> Dict[str, Any]:
    """
    Delete a document from the File Search store.
    
    Args:
        document_name: Full resource name of the document to delete
                      (e.g., "fileSearchStores/.../documents/...")
        
    Returns:
        Dictionary with deletion status
        
    Example:
        delete_document(
            document_name="fileSearchStores/abc123/documents/doc456"
        )
    """
    try:
        print(f"[DELETE] Deleting document: {document_name}")
        
        # Delete the document
        client.file_search_stores.documents.delete(name=document_name)
        
        print(f"[DELETE] Successfully deleted {document_name}")
        
        return {
            "success": True,
            "message": f"✅ Successfully deleted document",
            "document_name": document_name
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Delete failed: {str(e)}"
        }


@log_tool_call
def get_document_count() -> Dict[str, Any]:
    """
    Get the count of documents in the File Search store.
    
    Returns:
        Dictionary with document count
        
    Example:
        get_document_count()
    """
    try:
        result = list_documents()
        if result["success"]:
            return {
                "success": True,
                "count": result["count"],
                "store_name": result["store_name"],
                "message": f"✅ Store contains {result['count']} documents"
            }
        else:
            return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"❌ Failed to get document count: {str(e)}"
        }
