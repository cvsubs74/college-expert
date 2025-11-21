"""
Knowledge Base Tools - Interface to Knowledge Base Manager Cloud Function
Calls the knowledge base manager ES cloud function for document search and retrieval
"""
import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Knowledge Base Manager Cloud Function URL
KNOWLEDGE_BASE_MANAGER_ES_URL = os.environ.get('KNOWLEDGE_BASE_MANAGER_ES_URL', 'https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app')

def search_documents(query: str, user_id: str = "", search_type: str = "keyword", 
                    size: int = 10, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Search documents via the Knowledge Base Manager Cloud Function.
    Knowledge base is a generic store accessible to all users.
    
    Args:
        query: Search query text
        user_id: Optional user ID (ignored for generic knowledge base search)
        search_type: Type of search - "keyword", "vector", or "hybrid"
        size: Maximum number of results to return
        filters: Optional filters for metadata (e.g., {"university": "Stanford"})
    
    Returns:
        Dictionary with search results including documents and metadata
    """
    try:
        # Call the knowledge base manager cloud function
        url = f"{KNOWLEDGE_BASE_MANAGER_ES_URL}/search"
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": "knowledge_base_user"  # Generic user for knowledge base access
        }
        
        data = {
            "query": query,
            "user_id": "",  # Empty for generic knowledge base search
            "search_type": search_type,
            "size": size,
            "filters": filters or {}
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("success"):
            # Transform to match expected agent format
            documents = []
            for doc in result.get("documents", []):
                document = {
                    "id": doc["id"],
                    "score": doc.get("score", 1.0),
                    "filename": doc["document"].get("filename"),
                    "file_name": doc["document"].get("filename"),
                    "user_id": doc["document"].get("user_id"),
                    "indexed_at": doc["document"].get("indexed_at"),
                    "upload_date": doc["document"].get("upload_date"),
                    "title": doc["document"].get("filename", ""),
                    "content": doc["document"].get("content", ""),
                    "university": doc["document"].get("university_name", ""),
                    "university_name": doc["document"].get("university_name", ""),
                    "metadata": doc["document"].get("metadata", {}),
                    "file_size": doc["document"].get("file_size"),
                    "file_type": doc["document"].get("file_type"),
                    "num_chunks": doc["document"].get("num_chunks", 0)
                }
                documents.append(document)
            
            return {
                "success": True,
                "query": query,
                "search_type": search_type,
                "total": result.get("total", 0),
                "documents": documents,
                "filters_applied": bool(filters)
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "query": query,
                "documents": []
            }
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "documents": []
        }

def get_document_by_id(document_id: str, user_id: str = "") -> Dict[str, Any]:
    """
    Retrieve a specific document by ID via the Knowledge Base Manager Cloud Function.
    Knowledge base is a generic store accessible to all users.
    
    Args:
        document_id: The document ID to retrieve
        user_id: The user ID (ignored for generic knowledge base access)
    
    Returns:
        Dictionary with document content and metadata
    """
    try:
        # For generic knowledge base, we'll search for documents and find the one we want
        result = search_documents("", size=100)  # Get all documents
        
        if result["success"]:
            # Find the document with the matching ID
            for document in result["documents"]:
                if document["id"] == document_id:
                    return {
                        "success": True,
                        "document": document
                    }
            
            return {
                "success": False,
                "error": f"Document {document_id} not found",
                "document_id": document_id
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id
        }

def list_user_documents(user_id: str = "", size: int = 20, from_index: int = 0) -> Dict[str, Any]:
    """
    List all documents in the generic knowledge base via the Knowledge Base Manager Cloud Function.
    Knowledge base is accessible to all users, not tied to specific user IDs.
    
    Args:
        user_id: The user ID (ignored for generic knowledge base access)
        size: Number of documents to return
        from_index: Starting index for pagination
    
    Returns:
        Dictionary with list of knowledge base documents
    """
    try:
        # Call the knowledge base manager cloud function for generic access
        url = f"{KNOWLEDGE_BASE_MANAGER_ES_URL}/documents"
        params = {
            "user_id": "",  # Empty for generic knowledge base access
            "size": size,
            "from": from_index
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Email": "knowledge_base_user"  # Generic user for knowledge base access
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            # Transform to match expected agent format
            documents = []
            for doc in data.get("documents", []):
                document = {
                    "id": doc["id"],
                    "filename": doc["document"].get("filename"),
                    "file_name": doc["document"].get("filename"),
                    "user_id": doc["document"].get("user_id"),
                    "indexed_at": doc["document"].get("indexed_at"),
                    "upload_date": doc["document"].get("upload_date"),
                    "university_name": doc["document"].get("university_name"),
                    "metadata": doc["document"].get("metadata", {}),
                    "content_length": len(doc["document"].get("content", "")),
                    "file_size": doc["document"].get("file_size"),
                    "file_type": doc["document"].get("file_type"),
                    "num_chunks": doc["document"].get("num_chunks", 0)
                }
                documents.append(document)
            
            return {
                "success": True,
                "documents": documents,
                "total": data.get("total", 0),
                "from": from_index,
                "size": size
            }
        else:
            return {
                "success": False,
                "error": data.get("error", "Unknown error"),
                "documents": []
            }
            
    except Exception as e:
        logger.error(f"Failed to list knowledge base documents: {e}")
        return {
            "success": False,
            "error": str(e),
            "documents": []
        }

def get_document_metadata(document_id: str, user_id: str = "") -> Dict[str, Any]:
    """
    Get structured metadata for a specific document via the Knowledge Base Manager Cloud Function.
    Knowledge base is a generic store accessible to all users.
    
    Args:
        document_id: The document ID to retrieve metadata for
        user_id: The user ID (ignored for generic knowledge base access)
    
    Returns:
        Dictionary with structured metadata
    """
    try:
        # Get the full document first
        result = get_document_by_id(document_id)
        
        if not result["success"]:
            return result
        
        document = result["document"]
        metadata = document.get("metadata", {})
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": document["filename"],
            "file_name": document["file_name"],
            "university_identity": metadata.get("university_identity", {}),
            "academic_structure": metadata.get("academic_structure", {}),
            "admissions_statistics": metadata.get("admissions_statistics", {}),
            "indexed_at": document["indexed_at"],
            "upload_date": document["upload_date"],
            "university_name": document["university_name"],
            "file_size": document["file_size"],
            "file_type": document["file_type"],
            "num_chunks": document["num_chunks"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get metadata for document {document_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id
        }

def search_by_university(university_name: str, query: str = "", size: int = 10) -> Dict[str, Any]:
    """
    Search documents specifically for a university via the Knowledge Base Manager Cloud Function.
    Knowledge base is a generic store accessible to all users.
    
    Args:
        university_name: Name of the university to search
        query: Additional search query within the university documents
        size: Maximum number of results
    
    Returns:
        Dictionary with university-specific search results
    """
    try:
        filters = {"university": university_name}
        return search_documents(
            query=query or university_name,
            user_id="",  # Empty user_id for generic knowledge base search
            search_type="keyword",
            size=size,
            filters=filters
        )
        
    except Exception as e:
        logger.error(f"University search failed for {university_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "university": university_name,
            "documents": []
        }

def get_university_summary(university_name: str) -> Dict[str, Any]:
    """
    Get a summary of all documents for a specific university via the Knowledge Base Manager Cloud Function.
    Knowledge base is a generic store accessible to all users.
    
    Args:
        university_name: Name of the university
    
    Returns:
        Dictionary with university summary including programs and stats
    """
    try:
        # Search for all documents from this university
        result = search_by_university(university_name, "", size=50)
        
        if not result["success"]:
            return result
        
        documents = result["documents"]
        
        # Aggregate information
        programs = set()
        majors = set()
        colleges = set()
        document_types = set()
        
        for doc in documents:
            metadata = doc.get("metadata", {})
            academic = metadata.get("academic_structure", {})
            
            # Collect programs and majors
            for program in academic.get("programs_offered", []):
                programs.add(program)
            
            # Collect majors
            for major in academic.get("majors_inventory", []):
                majors.add(major)
            
            # Collect colleges
            for college in academic.get("schools_colleges", []):
                colleges.add(college)
            
            # Document types
            if metadata.get("university_identity", {}).get("type"):
                document_types.add(metadata["university_identity"]["type"])
        
        return {
            "success": True,
            "university": university_name,
            "total_documents": len(documents),
            "programs": sorted(list(programs)),
            "majors": sorted(list(majors)),
            "colleges": sorted(list(colleges)),
            "document_types": sorted(list(document_types)),
            "sample_documents": documents[:5]  # Return first 5 documents as samples
        }
        
    except Exception as e:
        logger.error(f"Failed to get university summary for {university_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "university": university_name
        }
