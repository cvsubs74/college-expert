"""
Knowledge Base Manager FS - Firestore Implementation
Direct Firestore integration for document management without RAG overhead.
"""

import os
import json
import logging
from flask import request
import google.cloud.firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime

# Initialize Firestore client
try:
    firestore_db = google.cloud.firestore.Client()
    print("[FIRESTORE] Firestore client initialized successfully")
except Exception as e:
    print(f"[FIRESTORE ERROR] Failed to initialize Firestore: {e}")
    firestore_db = None

def add_cors_headers(response, status_code=200):
    """Add CORS headers to response."""
    if isinstance(response, dict):
        response = (json.dumps(response), status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
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
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        })
        
        response = (data, status, headers)
    
    return response

def search_documents_firestore(query, user_id=None, limit=10, filters=None):
    """Search documents directly in Firestore."""
    try:
        if not firestore_db:
            return {"success": False, "error": "Firestore not available"}
        
        # Build the base query
        docs_ref = firestore_db.collection('knowledge_base_documents')
        
        # Add user filter if provided
        if user_id:
            docs_ref = docs_ref.where(filter=FieldFilter('user_id', '==', user_id))
        
        # Add metadata filters if provided
        if filters:
            if filters.get('university'):
                docs_ref = docs_ref.where(filter=FieldFilter('metadata.university_identity.name', '==', filters['university']))
            if filters.get('state'):
                docs_ref = docs_ref.where(filter=FieldFilter('metadata.university_identity.location.state', '==', filters['state']))
            if filters.get('document_type'):
                docs_ref = docs_ref.where(filter=FieldFilter('metadata.university_identity.type', '==', filters['document_type']))
        
        # Get all documents (Firestore doesn't have full-text search, so we'll filter in memory)
        all_docs = docs_ref.stream()
        
        # Convert to list and filter by query text
        matching_docs = []
        query_lower = query.lower()
        
        for doc in all_docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            
            # Simple text matching in content and metadata
            content_match = query_lower in doc_data.get('content', '').lower()
            title_match = query_lower in doc_data.get('metadata', {}).get('generated_content', {}).get('university_identity', {}).get('name', '').lower()
            description_match = query_lower in doc_data.get('metadata', {}).get('generated_content', {}).get('description', '').lower()
            
            if content_match or title_match or description_match:
                # Calculate simple relevance score
                score = 0
                if content_match:
                    score += doc_data.get('content', '').lower().count(query_lower) * 1
                if title_match:
                    score += 5  # Higher weight for title matches
                if description_match:
                    score += 3  # Medium weight for description matches
                
                doc_data['relevance_score'] = score
                matching_docs.append(doc_data)
        
        # Sort by relevance score and limit results
        matching_docs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        matching_docs = matching_docs[:limit]
        
        return {
            "success": True,
            "documents": matching_docs,
            "total_found": len(matching_docs),
            "query": query,
            "search_method": "firestore_direct"
        }
        
    except Exception as e:
        print(f"[FIRESTORE SEARCH ERROR] {e}")
        return {"success": False, "error": str(e)}

def get_document_by_id_firestore(document_id):
    """Get a specific document from Firestore."""
    try:
        if not firestore_db:
            return {"success": False, "error": "Firestore not available"}
        
        doc_ref = firestore_db.collection('knowledge_base_documents').document(document_id)
        doc = doc_ref.get()
        
        if doc.exists:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            return {"success": True, "document": doc_data}
        else:
            return {"success": False, "error": "Document not found"}
            
    except Exception as e:
        print(f"[FIRESTORE GET ERROR] {e}")
        return {"success": False, "error": str(e)}

def list_user_documents_firestore(user_id, limit=20):
    """List all documents for a user from Firestore."""
    try:
        if not firestore_db:
            return {"success": False, "error": "Firestore not available"}
        
        docs_ref = firestore_db.collection('knowledge_base_documents').where(
            filter=FieldFilter('user_id', '==', user_id)
        ).order_by('indexed_at', direction=google.cloud.firestore.Query.DESCENDING).limit(limit)
        
        docs = docs_ref.stream()
        documents = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            # Include only essential fields for listing
            documents.append({
                'id': doc_data['id'],
                'filename': doc_data.get('filename'),
                'indexed_at': doc_data.get('indexed_at'),
                'metadata': doc_data.get('metadata', {}),
                'content_length': len(doc_data.get('content', ''))
            })
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        print(f"[FIRESTORE LIST ERROR] {e}")
        return {"success": False, "error": str(e)}

def get_university_summary_firestore(university_name):
    """Get university summary from Firestore documents."""
    try:
        if not firestore_db:
            return {"success": False, "error": "Firestore not available"}
        
        docs_ref = firestore_db.collection('knowledge_base_documents').where(
            filter=FieldFilter('metadata.university_identity.name', '==', university_name)
        )
        
        docs = docs_ref.stream()
        documents = []
        programs = set()
        colleges = set()
        document_types = set()
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            documents.append(doc_data)
            
            # Extract metadata
            metadata = doc_data.get('metadata', {}).get('generated_content', {})
            
            # Collect programs
            for program in metadata.get('academic_structure', {}).get('programs', []):
                programs.add(program.get('name', ''))
            
            # Collect colleges
            for college in metadata.get('academic_structure', {}).get('colleges', []):
                colleges.add(college.get('name', ''))
            
            # Document types
            if metadata.get('university_identity', {}).get('type'):
                document_types.add(metadata['university_identity']['type'])
        
        return {
            "success": True,
            "university": university_name,
            "total_documents": len(documents),
            "programs": sorted(list(programs)),
            "colleges": sorted(list(colleges)),
            "document_types": sorted(list(document_types)),
            "sample_documents": documents[:5]
        }
        
    except Exception as e:
        print(f"[FIRESTORE UNIVERSITY ERROR] {e}")
        return {"success": False, "error": str(e)}

def knowledge_base_manager_fs_http(request):
    """Main HTTP entry point for Knowledge Base Manager FS."""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return add_cors_headers({}, 200)
    
    try:
        # Get request path
        path = request.path.strip('/') or 'health'
        print(f"[FS MANAGER] Request path: {path}")
        
        # Health check
        if path == 'health':
            health_status = {
                "status": "healthy",
                "service": "knowledge_base_manager_fs",
                "database": "firestore",
                "timestamp": datetime.now().isoformat()
            }
            if not firestore_db:
                health_status["database"] = "firestore_error"
            return add_cors_headers(health_status, 200)
        
        # Route to appropriate handler
        if path == 'search':
            return handle_search_firestore(request)
        elif path == 'documents':
            return handle_documents_firestore(request)
        elif path == 'university':
            return handle_university_firestore(request)
        else:
            return add_cors_headers({"error": "Endpoint not found"}, 404)
            
    except Exception as e:
        print(f"[FS MANAGER ERROR] {e}")
        return add_cors_headers({"error": f"Internal server error: {str(e)}"}, 500)

def handle_search_firestore(request):
    """Handle search requests."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    data = request.get_json()
    if not data:
        return add_cors_headers({"error": "No JSON data provided"}, 400)
    
    query = data.get('query', '')
    user_id = data.get('user_id')
    limit = data.get('limit', 10)
    filters = data.get('filters', {})
    
    if not query:
        return add_cors_headers({"error": "Query is required"}, 400)
    
    result = search_documents_firestore(query, user_id, limit, filters)
    
    if result['success']:
        return add_cors_headers({
            "success": True,
            "query": query,
            "documents": result['documents'],
            "total_found": result['total_found'],
            "search_method": "firestore_direct"
        }, 200)
    else:
        return add_cors_headers({"error": result['error']}, 500)

def handle_documents_firestore(request):
    """Handle document operations."""
    if request.method == 'GET':
        # List documents
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 20))
        
        if not user_id:
            return add_cors_headers({"error": "user_id is required"}, 400)
        
        result = list_user_documents_firestore(user_id, limit)
        
        if result['success']:
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers({"error": result['error']}, 500)
    
    elif request.method == 'POST':
        # Get specific document
        data = request.get_json()
        document_id = data.get('document_id')
        
        if not document_id:
            return add_cors_headers({"error": "document_id is required"}, 400)
        
        result = get_document_by_id_firestore(document_id)
        
        if result['success']:
            return add_cors_headers(result, 200)
        else:
            return add_cors_headers({"error": result['error']}, 404)
    
    else:
        return add_cors_headers({"error": "Method not allowed"}, 405)

def handle_university_firestore(request):
    """Handle university-specific requests."""
    if request.method != 'POST':
        return add_cors_headers({"error": "Method not allowed"}, 405)
    
    data = request.get_json()
    if not data:
        return add_cors_headers({"error": "No JSON data provided"}, 400)
    
    university_name = data.get('university_name', '')
    
    if not university_name:
        return add_cors_headers({"error": "university_name is required"}, 400)
    
    result = get_university_summary_firestore(university_name)
    
    if result['success']:
        return add_cors_headers(result, 200)
    else:
        return add_cors_headers({"error": result['error']}, 500)

# Entry point for Cloud Functions
def knowledge_base_manager_fs_http_entry(request):
    """Entry point that redirects to the main handler."""
    return knowledge_base_manager_fs_http(request)
