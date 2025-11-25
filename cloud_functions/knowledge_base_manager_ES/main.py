"""
Knowledge Base Manager - Elasticsearch
Handles pre-chunked markdown files with context tags.
Parses chunks, generates embeddings, and stores in Elasticsearch.
"""
import functions_framework
import json
import os
import logging
import re
from flask import request
from google.cloud import storage
import google.generativeai as genai
from elasticsearch import Elasticsearch
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'college-counselling-478115')
BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'college-counselling-knowledge-base')
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = os.environ.get('ES_INDEX_NAME', 'university_documents')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- CORS Headers ---
def add_cors_headers(response, status_code=200):
    """Add CORS headers to response."""
    if isinstance(response, dict):
        return (json.dumps(response), status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-User-Email',
            'Access-Control-Max-Age': '3600'
        })
    return response

# --- Client Initialization ---
def get_storage_client():
    """Initialize Google Cloud Storage client."""
    return storage.Client(project=PROJECT_ID)

def get_elasticsearch_client():
    """Initialize Elasticsearch client."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("Elasticsearch credentials not configured")
    return Elasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)

def init_gemini():
    """Initialize Gemini API."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    genai.configure(api_key=GEMINI_API_KEY)

# --- Elasticsearch Index Management ---
def ensure_index_exists(es_client):
    """Ensure Elasticsearch index exists with correct mappings."""
    if not es_client.indices.exists(index=ES_INDEX_NAME):
        logger.info(f"Creating index: {ES_INDEX_NAME}")
        es_client.indices.create(
            index=ES_INDEX_NAME,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 1
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {
                            "type": "keyword",
                            "doc_values": True
                        },
                        "chunk_index": {
                            "type": "integer"
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "standard",
                            "term_vector": "with_positions_offsets"
                        },
                        "content_vector": {
                            "type": "dense_vector",
                            "dims": 768,  # Gemini text-embedding-004 dimension
                            "index": True,
                            "similarity": "cosine"
                        },
                        "metadata": {
                            "properties": {
                                "document_title": {
                                    "type": "keyword"
                                },
                                "filename": {
                                    "type": "keyword"
                                },
                                "chapter_section": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                },
                                "topic": {
                                    "type": "keyword",
                                    "ignore_above": 256
                                },
                                "full_context_path": {
                                    "type": "text",
                                    "analyzer": "standard",
                                    "fields": {
                                        "raw": {
                                            "type": "keyword"
                                        }
                                    }
                                },
                                "total_chunks": {
                                    "type": "integer"
                                },
                                "content_length": {
                                    "type": "integer"
                                }
                            }
                        },
                        "created_at": {
                            "type": "date"
                        }
                    }
                }
            }
        )

# --- Markdown Parsing ---
def parse_markdown_chunks(markdown_text):
    """
    Parse markdown file into chunks separated by '---'.
    Expected format (UCSB):
    ---
    **Context:** Section context/title
    Content...
    ---
    """
    chunks = []
    
    # Split by '---' separator
    sections = markdown_text.split('\n---\n')
    
    # Process each section
    for i, section in enumerate(sections):
        section = section.strip()
        
        # Skip empty sections
        if not section or section == '---':
            continue
        
        # Extract context line and content
        lines = section.split('\n')
        context = ""
        content_lines = []
        
        for line in lines:
            # Check for **Context:** line
            if line.startswith('**Context:**'):
                context = line.replace('**Context:**', '').strip()
            else:
                content_lines.append(line)
        
        # Combine content
        content = '\n'.join(content_lines).strip()
        
        if content:
            chunks.append({
                'chunk_number': i + 1,
                'title': context or f"Section {i + 1}",
                'content': content
            })
    
    return chunks

# --- Embedding Generation ---
def generate_embedding(text):
    """Generate embedding for text using Gemini."""
    try:
        result = genai.embed_content(
            model='models/text-embedding-004',
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise

# --- Upload and Index ---
def upload_and_index_document(file, filename):
    """Upload markdown document to GCS and index chunks in Elasticsearch."""
    temp_path = None
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.md', mode='w+b') as tmp_file:
            file.save(tmp_file.name)
            temp_path = tmp_file.name
        
        # Upload to GCS
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_filename(temp_path)
        
        logger.info(f"Uploaded {filename} to GCS")
        
        # Read markdown content
        with open(temp_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        
        # Parse chunks
        chunks = parse_markdown_chunks(markdown_text)
        logger.info(f"Parsed {len(chunks)} chunks from {filename}")
        
        if not chunks:
            raise ValueError("No chunks found in markdown file. Please ensure file follows the chunk format.")
        
        # Initialize Gemini
        init_gemini()
        
        # Index chunks in Elasticsearch
        es_client = get_elasticsearch_client()
        ensure_index_exists(es_client)
        
        for chunk in chunks:
            # Generate embedding
            embedding = generate_embedding(chunk['content'])
            
            # Extract metadata from context path (UCSB format)
            # Example: "An Institutional Analysis of UCSB > I. Profile > Overview"
            context_path = chunk['title']
            parts = [p.strip() for p in context_path.split('>')]
            
            # Extract components
            document_title = parts[0] if parts else filename
            chapter_section = parts[1] if len(parts) > 1 else ""
            topic = parts[-1] if len(parts) > 1 else context_path
            
            # Create document with structured metadata
            doc = {
                "chunk_id": f"{filename}_chunk_{chunk['chunk_number']}",
                "chunk_index": chunk['chunk_number'],
                "content": chunk['content'],
                "content_vector": embedding,
                "metadata": {
                    "document_title": document_title,
                    "filename": filename,
                    "chapter_section": chapter_section,
                    "topic": topic,
                    "full_context_path": context_path,
                    "total_chunks": len(chunks),
                    "content_length": len(chunk['content'])
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Debug log the document structure
            logger.info(f"Indexing chunk {chunk['chunk_number']} with metadata: {doc['metadata']}")
            
            # Index in Elasticsearch (use 'document' param for ES 8.x)
            doc_id = f"{filename}_chunk_{chunk['chunk_number']}"
            es_client.index(index=ES_INDEX_NAME, id=doc_id, document=doc)
        
        logger.info(f"Indexed {len(chunks)} chunks for {filename}")
        
        return {
            "success": True,
            "filename": filename,
            "chunks_indexed": len(chunks),
            "message": f"Successfully uploaded and indexed {filename}"
        }
        
    except Exception as e:
        logger.error(f"Upload and index failed: {e}", exc_info=True)
        raise
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# --- List Documents ---
def list_documents():
    """List all documents from GCS."""
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs()
        
        documents = []
        for blob in blobs:
            documents.append({
                "name": blob.name,
                "size": blob.size,
                "uploaded": blob.time_created.isoformat() if blob.time_created else None,
                "content_type": blob.content_type
            })
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
    except Exception as e:
        logger.error(f"List documents failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "documents": []
        }

# --- Delete Document ---
def delete_document(filename):
    """Delete document from GCS and Elasticsearch."""
    try:
        # Delete from GCS
        storage_client = get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.delete()
        
        # Delete from Elasticsearch
        es_client = get_elasticsearch_client()
        
        # Delete all chunks for this document
        delete_query = {
            "query": {
                "term": {
                    "metadata.filename": filename
                }
            }
        }
        es_client.delete_by_query(index=ES_INDEX_NAME, body=delete_query)
        
        logger.info(f"Deleted {filename} from GCS and Elasticsearch")
        
        return {
            "success": True,
            "message": f"Successfully deleted {filename}"
        }
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise

# --- Search Documents ---
def search_documents(query, limit=10):
    """Search documents using semantic vector search."""
    try:
        # Initialize Gemini for embeddings
        init_gemini()
        
        # Generate query embedding
        query_embedding = generate_embedding(query)
        
        # Search in Elasticsearch using vector similarity
        es_client = get_elasticsearch_client()
        
        search_body = {
            "size": limit,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'content_vector') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            },
            "_source": ["chunk_id", "chunk_index", "content", "metadata", "created_at"]
        }
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        # Format results
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            metadata = source.get('metadata', {})
            
            results.append({
                "id": hit['_id'],
                "score": hit['_score'] - 1.0,  # Remove the +1.0 offset
                "document": {
                    "filename": metadata.get('filename', ''),
                    "chunk_index": source.get('chunk_index', 0),
                    "title": metadata.get('full_context_path', ''),
                    "content": source.get('content', ''),
                    "upload_timestamp": source.get('created_at', ''),
                    "metadata": metadata
                }
            })
        
        logger.info(f"Found {len(results)} results for query: {query}")
        
        return {
            "success": True,
            "results": results,
            "total": len(results),
            "query": query
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": []
        }

# --- HTTP Entry Point ---
@functions_framework.http
def knowledge_base_manager_es_http_entry(req):
    """HTTP Cloud Function entry point."""
    
    # Handle CORS preflight
    if req.method == 'OPTIONS':
        return add_cors_headers({}, 204)
    
    try:
        # GET - List documents
        if req.method == 'GET':
            result = list_documents()
            return add_cors_headers(result)
        
        # POST - Could be search, upload, or delete
        elif req.method == 'POST':
            # Check if this is a search request (POST /search endpoint with JSON body)
            # Safely check for JSON content type before accessing req.json
            is_json = req.content_type and 'application/json' in req.content_type
            
            if is_json:
                data = req.get_json()
                
                # Check if this is a search request
                if 'query' in data and not data.get('file_name') and not data.get('name'):
                    query = data.get('query', '')
                    limit = data.get('limit', 10)
                    result = search_documents(query, limit)
                    return add_cors_headers(result)
                
                # Check if this is a delete request
                filename = data.get('file_name') or data.get('name')
                if filename:
                    result = delete_document(filename)
                    return add_cors_headers(result)
            
            # Otherwise, check if it's a file upload request
            if 'file' in req.files:
                file = req.files['file']
                if file.filename == '':
                    return add_cors_headers({"error": "No file selected"}, 400)
                
                if not file.filename.endswith('.md'):
                    return add_cors_headers({"error": "Only markdown (.md) files are supported"}, 400)
                
                result = upload_and_index_document(file, file.filename)
                return add_cors_headers(result)
            else:
                return add_cors_headers({"error": "No file provided or invalid request"}, 400)
        
        # DELETE - Delete document (alternative method)
        elif req.method == 'DELETE':
            data = req.get_json()
            if not data or 'name' not in data:
                return add_cors_headers({"error": "Document name required"}, 400)
            
            result = delete_document(data['name'])
            return add_cors_headers(result)
        
        else:
            return add_cors_headers({"error": "Method not allowed"}, 405)
            
    except Exception as e:
        logger.error(f"Request failed: {e}", exc_info=True)
        return add_cors_headers({
            "success": False,
            "error": str(e)
        }, 500)
