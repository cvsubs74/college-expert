"""
Elasticsearch Tools for Knowledge Base Analyst
Direct interaction with Elasticsearch for document search and retrieval
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Elasticsearch Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = os.environ.get('ES_INDEX_NAME', 'university_documents')

def get_elasticsearch_client():
    """Initialize Elasticsearch client."""
    try:
        from elasticsearch import Elasticsearch
        if not ES_CLOUD_ID or not ES_API_KEY:
            raise ValueError("Missing Elasticsearch configuration")
        
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

def search_documents(query: str, user_id: str = "", search_type: str = "hybrid", 
                    size: int = 10, filters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Search documents in Elasticsearch using various search strategies.
    
    Args:
        query: Search query text
        user_id: Optional user ID for user-specific filtering
        search_type: Type of search - "keyword", "vector", or "hybrid"
        size: Maximum number of results to return
        filters: Optional filters for metadata (e.g., {"university": "Stanford"})
    
    Returns:
        Dictionary with search results including documents and metadata
    """
    try:
        client = get_elasticsearch_client()
        
        # Build the base query
        search_body = {
            "size": size,
            "query": {
                "bool": {
                    "must": [],
                    "filter": []
                }
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 150,
                        "number_of_fragments": 3
                    },
                    "metadata.generated_content.description": {
                        "fragment_size": 150,
                        "number_of_fragments": 2
                    }
                }
            }
        }
        
        # Add user filter if provided
        if user_id and user_id.strip():
            search_body["query"]["bool"]["filter"].append({
                "term": {"user_id": user_id}
            })
        
        # Add metadata filters if provided
        if filters:
            for key, value in filters.items():
                if key in ["university", "state", "country", "institution_type"]:
                    search_body["query"]["bool"]["filter"].append({
                        "term": {f"metadata.{key}.keyword": value}
                    })
        
        # Add search query based on type
        if search_type == "keyword":
            search_body["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "content^2.0",
                        "metadata.generated_content.title^3.0",
                        "metadata.generated_content.description^2.5",
                        "metadata.generated_content.university_identity.name^3.0",
                        "metadata.generated_content.university_identity.programs^2.0"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
        elif search_type == "vector":
            # Generate embedding for the query (you'd need to implement this)
            # For now, fall back to keyword search
            search_body["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["content", "metadata.*"],
                    "type": "best_fields"
                }
            })
        else:  # hybrid
            # Combine keyword and semantic search
            search_body["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "content^2.0",
                        "metadata.generated_content.title^3.0",
                        "metadata.generated_content.description^2.5"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
        
        # Execute search
        response = client.search(index=ES_INDEX_NAME, body=search_body)
        
        # Process results
        hits = response.get('hits', {}).get('hits', [])
        documents = []
        
        for hit in hits:
            source = hit['_source']
            highlight = hit.get('highlight', {})
            
            document = {
                "id": hit['_id'],
                "score": hit['_score'],
                "filename": source.get('filename'),
                "user_id": source.get('user_id'),
                "indexed_at": source.get('indexed_at'),
                "title": source.get('title', ''),
                "content": source.get('content', ''),
                "university": source.get('university', ''),
                "content_snippet": highlight.get('content', [source.get('content', '')[:200] + "..."])[0],
                "metadata": source.get('metadata', {}),
                "highlights": {
                    "content": highlight.get('content', []),
                    "description": highlight.get('metadata.generated_content.description', [])
                }
            }
            documents.append(document)
        
        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "total": response.get('hits', {}).get('total', {}).get('value', 0),
            "documents": documents,
            "filters_applied": bool(filters or (user_id and user_id.strip()))
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "documents": []
        }

def get_document_by_id(document_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific document by its Elasticsearch ID.
    
    Args:
        document_id: The Elasticsearch document ID
    
    Returns:
        Dictionary with document content and metadata
    """
    try:
        client = get_elasticsearch_client()
        
        response = client.get(index=ES_INDEX_NAME, id=document_id)
        source = response['_source']
        
        return {
            "success": True,
            "document": {
                "id": response['_id'],
                "filename": source.get('filename'),
                "user_id": source.get('user_id'),
                "indexed_at": source.get('indexed_at'),
                "content": source.get('content'),
                "metadata": source.get('metadata', {}),
                "embeddings": source.get('embeddings', [])
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "document_id": document_id
        }

def list_user_documents(user_id: str, size: int = 20, from_index: int = 0) -> Dict[str, Any]:
    """
    List all documents for a specific user.
    
    Args:
        user_id: The user ID to filter documents
        size: Number of documents to return
        from_index: Starting index for pagination
    
    Returns:
        Dictionary with list of user documents
    """
    try:
        client = get_elasticsearch_client()
        
        search_body = {
            "size": size,
            "from": from_index,
            "query": {
                "term": {"user_id": user_id}
            },
            "sort": [
                {"indexed_at": {"order": "desc"}}
            ]
        }
        
        response = client.search(index=ES_INDEX_NAME, body=search_body)
        hits = response.get('hits', {}).get('hits', [])
        
        documents = []
        for hit in hits:
            source = hit['_source']
            document = {
                "id": hit['_id'],
                "filename": source.get('filename'),
                "indexed_at": source.get('indexed_at'),
                "metadata": source.get('metadata', {}),
                "content_length": len(source.get('content', ''))
            }
            documents.append(document)
        
        return {
            "success": True,
            "documents": documents,
            "total": response.get('hits', {}).get('total', {}).get('value', 0),
            "from": from_index,
            "size": size
        }
        
    except Exception as e:
        logger.error(f"Failed to list documents for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "documents": []
        }

def get_document_metadata(document_id: str) -> Dict[str, Any]:
    """
    Get structured metadata for a specific document.
    
    Args:
        document_id: The Elasticsearch document ID
    
    Returns:
        Dictionary with structured metadata
    """
    try:
        result = get_document_by_id(document_id)
        
        if not result["success"]:
            return result
        
        metadata = result["document"].get("metadata", {})
        generated_content = metadata.get("generated_content", {})
        
        return {
            "success": True,
            "document_id": document_id,
            "filename": result["document"]["filename"],
            "university_identity": generated_content.get("university_identity", {}),
            "academic_structure": generated_content.get("academic_structure", {}),
            "admissions_statistics": generated_content.get("admissions_statistics", {}),
            "indexed_at": result["document"]["indexed_at"]
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
    Search documents specifically for a university.
    
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
    Get a summary of all documents for a specific university.
    
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
            academic = metadata.get("generated_content", {}).get("academic_structure", {})
            
            # Collect programs and majors
            for program in academic.get("programs", []):
                programs.add(program.get("name", ""))
                for major in program.get("majors", []):
                    majors.add(major.get("name", ""))
            
            # Collect colleges
            for college in academic.get("colleges", []):
                colleges.add(college.get("name", ""))
            
            # Document types
            if metadata.get("generated_content", {}).get("university_identity", {}).get("type"):
                document_types.add(metadata["generated_content"]["university_identity"]["type"])
        
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
