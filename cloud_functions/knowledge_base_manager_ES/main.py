import functions_framework
import json
import os
import logging
from flask import request
from google.cloud import storage
import google.generativeai as genai
import elasticsearch
from PyPDF2 import PdfReader
from docx import Document
import hashlib
import tempfile
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'college-counselling-478115')
REGION = os.environ.get('REGION', 'us-east1')
BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'college-counselling-knowledge-base')
DATA_STORE = os.environ.get('DATA_STORE', 'college_admissions_kb')

# Elasticsearch Configuration
ES_CLOUD_ID = os.environ.get('ES_CLOUD_ID')
ES_API_KEY = os.environ.get('ES_API_KEY')
ES_INDEX_NAME = os.environ.get('ES_INDEX_NAME', 'university_documents')

# Gemini Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- CORS Headers ---
def add_cors_headers(response, status_code=200):
    """Add CORS headers to response and return proper format."""
    if isinstance(response, dict):
        response = (json.dumps(response), status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        })
    elif isinstance(response, tuple) and len(response) >= 2:
        # Add CORS headers to existing tuple response
        if len(response) == 2:
            data, status = response
            headers = {}
        else:
            data, status, headers = response
        
        # Ensure headers is a dict
        if not headers:
            headers = {}
        
        # Add CORS headers
        headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        })
        
        response = (data, status, headers)
    
    return response

# --- Client Initialization ---
def get_storage_client():
    """Initialize Google Cloud Storage client."""
    return storage.Client(project=PROJECT_ID)

def get_elasticsearch_client():
    """Initialize Elasticsearch client."""
    if not ES_CLOUD_ID or not ES_API_KEY:
        raise ValueError("Elasticsearch credentials not configured")
    
    return elasticsearch.Elasticsearch(
        cloud_id=ES_CLOUD_ID,
        api_key=ES_API_KEY
    )

def get_gemini_client():
    """Initialize Gemini client."""
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel('gemini-1.5-flash')

# --- Elasticsearch Index Management ---
def create_elasticsearch_index():
    """Create Elasticsearch index with proper mapping."""
    es_client = get_elasticsearch_client()
    
    if es_client.indices.exists(index=ES_INDEX_NAME):
        logger.info(f"Index {ES_INDEX_NAME} already exists")
        return True
    
    mapping = {
        "mappings": {
            "properties": {
                "document_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "filename": {"type": "text", "analyzer": "standard"},
                "content": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "university_name": {"type": "text", "analyzer": "standard"},
                "metadata": {
                    "properties": {
                        "university_identity": {
                            "properties": {
                                "name": {"type": "text", "analyzer": "standard"},
                                "type": {"type": "keyword"},
                                "location": {"type": "text"},
                                "ranking": {"type": "keyword"}
                            }
                        },
                        "academic_structure": {
                            "properties": {
                                "majors_inventory": {"type": "text"},
                                "programs_offered": {"type": "text"},
                                "schools_colleges": {"type": "text"}
                            }
                        },
                        "admissions_statistics": {
                            "properties": {
                                "acceptance_rate": {"type": "float"},
                                "total_applications": {"type": "integer"},
                                "enrollment_size": {"type": "integer"}
                            }
                        }
                    }
                },
                "content_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },
                "status": {"type": "keyword"},
                "processing_stage": {"type": "keyword"},
                "indexed_at": {"type": "date"},
                "file_size": {"type": "long"},
                "file_type": {"type": "keyword"}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "1s"
        }
    }
    
    try:
        es_client.indices.create(index=ES_INDEX_NAME, body=mapping)
        logger.info(f"Created index {ES_INDEX_NAME}")
        return True
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        return False

# --- Text Processing ---
def extract_text_from_file(file_path, file_type):
    """Extract text from PDF or DOCX files."""
    try:
        if file_type.lower() == 'pdf':
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        elif file_type.lower() == 'docx':
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        else:
            return None
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return None

def generate_content_embedding(content):
    """Generate vector embedding for content using Gemini."""
    try:
        genai_model = get_gemini_client()
        
        # Use Gemini's embedding model
        import google.generativeai as genai
        embedding_model = genai.GenerativeModel('embedding-001')
        
        result = embedding_model.embed_content(
            content=content,
            task_type="retrieval_document"
        )
        
        return result['embedding']
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        return None

def generate_document_metadata(content, filename):
    """Generate structured metadata using Gemini LLM."""
    try:
        gemini_model = get_gemini_client()
        
        prompt = f"""
        Analyze the following university document content and extract structured information:
        
        Filename: {filename}
        Content: {content[:2000]}...
        
        Please extract and categorize the information into this JSON structure:
        {{
            "university_identity": {{
                "name": "University name if mentioned",
                "type": "Public/Private/Unknown",
                "location": "City, State if mentioned",
                "ranking": "National/Regional/Unknown if mentioned"
            }},
            "academic_structure": {{
                "majors_inventory": ["List of majors mentioned"],
                "programs_offered": ["Key programs highlighted"],
                "schools_colleges": ["Academic divisions mentioned"]
            }},
            "admissions_statistics": {{
                "acceptance_rate": "percentage if mentioned",
                "total_applications": "number if mentioned",
                "enrollment_size": "number if mentioned"
            }}
        }}
        
        Return only valid JSON that can be parsed.
        """
        
        response = gemini_model.generate_content(prompt)
        
        # Try to parse the response as JSON
        try:
            import json
            metadata = json.loads(response.text)
            return metadata
        except json.JSONDecodeError:
            # Fallback if response is not valid JSON
            return {
                "university_identity": {"name": "Unknown", "type": "Unknown", "location": "Unknown", "ranking": "Unknown"},
                "academic_structure": {"majors_inventory": [], "programs_offered": [], "schools_colleges": []},
                "admissions_statistics": {"acceptance_rate": None, "total_applications": None, "enrollment_size": None}
            }
            
    except Exception as e:
        logger.error(f"Error generating metadata: {str(e)}")
        return {
            "university_identity": {"name": "Unknown", "type": "Unknown", "location": "Unknown", "ranking": "Unknown"},
            "academic_structure": {"majors_inventory": [], "programs_offered": [], "schools_colleges": []},
            "admissions_statistics": {"acceptance_rate": None, "total_applications": None, "enrollment_size": None}
        }

# --- Document Operations ---
def index_document(user_id, filename, file_content=None, file_path=None):
    """Index document into Elasticsearch with metadata and embeddings."""
    try:
        # Ensure index exists
        create_elasticsearch_index()
        
        es_client = get_elasticsearch_client()
        storage_client = get_storage_client()
        
        # Generate document ID
        document_id = hashlib.sha256(f"{user_id}_{filename}".encode()).hexdigest()
        
        # Get file content if not provided
        if not file_content:
            if not file_path:
                raise ValueError("Either file_content or file_path must be provided")
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
        
        # Determine file type
        file_type = filename.split('.')[-1] if '.' in filename else 'unknown'
        
        # Create temporary file for text extraction
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Extract text content
            content = extract_text_from_file(temp_file_path, file_type)
            if not content:
                raise ValueError("Could not extract text from file")
            
            # Generate metadata
            metadata = generate_document_metadata(content, filename)
            
            # Generate embedding
            embedding = generate_content_embedding(content)
            
            # Prepare document for indexing
            document = {
                "document_id": document_id,
                "user_id": user_id,
                "filename": filename,
                "content": content,
                "university_name": metadata.get("university_identity", {}).get("name", ""),
                "metadata": metadata,
                "content_embedding": embedding if embedding else [],
                "status": "indexed",
                "processing_stage": "completed",
                "indexed_at": datetime.utcnow().isoformat(),
                "file_size": len(file_content),
                "file_type": file_type
            }
            
            # Index document
            es_client.index(
                index=ES_INDEX_NAME,
                id=document_id,
                body=document
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "message": "Document indexed successfully",
                "metadata": {
                    "filename": filename,
                    "university_name": document['university_name'],
                    "content_length": len(content),
                    "has_embedding": len(embedding) > 0,
                    "index": ES_INDEX_NAME
                }
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        
    except Exception as e:
        logger.error(f"Error indexing document: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def search_documents(user_id, query, search_type="keyword", size=10, filters=None):
    """Search documents using Elasticsearch."""
    try:
        es_client = get_elasticsearch_client()
        
        # Build search query based on type
        if search_type == "vector":
            # Generate embedding for query
            query_embedding = generate_content_embedding(query)
            if not query_embedding:
                raise ValueError("Could not generate query embedding")
            
            search_body = {
                "size": size,
                "query": {
                    "bool": {
                        "must": [
                            {
                                "script_score": {
                                    "query": {"term": {"user_id": user_id}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        elif search_type == "hybrid":
            # Combine keyword and vector search
            query_embedding = generate_content_embedding(query)
            
            search_body = {
                "size": size,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user_id": user_id}}
                        ],
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "university_name", "metadata.*"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            },
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'content_embedding') + 1.0",
                                        "params": {"query_vector": query_embedding}
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        else:
            # Default keyword search
            search_body = {
                "size": size,
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"user_id": user_id}},
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["content^2", "university_name", "metadata.*"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 3},
                        "university_name": {}
                    }
                }
            }
        
        # Add filters if provided
        if filters:
            filter_terms = []
            for field, value in filters.items():
                filter_terms.append({"term": {field: value}})
            
            if filter_terms:
                search_body["query"]["bool"]["filter"] = filter_terms
        
        # Execute search
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        # Process results
        results = []
        for hit in response['hits']['hits']:
            result = {
                "id": hit['_id'],
                "score": hit['_score'],
                "document": hit['_source'],
                "highlights": hit.get('highlight', {})
            }
            results.append(result)
        
        return {
            "success": True,
            "query": query,
            "search_type": search_type,
            "total": response['hits']['total']['value'],
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def list_documents(user_id, size=20, from_index=0):
    """List documents for a user."""
    try:
        es_client = get_elasticsearch_client()
        
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
        
        response = es_client.search(index=ES_INDEX_NAME, body=search_body)
        
        documents = []
        for hit in response['hits']['hits']:
            documents.append({
                "id": hit['_id'],
                "document": hit['_source']
            })
        
        return {
            "success": True,
            "total": response['hits']['total']['value'],
            "documents": documents,
            "size": size,
            "from": from_index
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def delete_document(user_id, document_id):
    """Delete a document."""
    try:
        es_client = get_elasticsearch_client()
        
        # First check if document exists and belongs to user
        try:
            doc = es_client.get(index=ES_INDEX_NAME, id=document_id)
            if doc['_source']['user_id'] != user_id:
                return {
                    "success": False,
                    "error": "Document not found or access denied"
                }
        except elasticsearch.NotFoundError:
            return {
                "success": False,
                "error": "Document not found"
            }
        
        # Delete document
        es_client.delete(index=ES_INDEX_NAME, id=document_id)
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# --- Main HTTP Function (Controller) ---
@functions_framework.http
def knowledge_base_manager_es_http(request):
    """HTTP Cloud Function that acts as a controller for knowledge base operations."""
    
    # Enable CORS
    if request.method == 'OPTIONS':
        return add_cors_headers({'status': 'ok'}, 200)
    
    # Parse path to determine resource type and action
    path_parts = request.path.strip('/').split('/')
    
    if not path_parts or len(path_parts) == 0:
        return add_cors_headers({'error': 'Not Found'}, 404)
    
    resource_type = path_parts[0]
    logger.info(f"Processing {request.method} request for resource_type: {resource_type}, path: {request.path}")
    
    try:
        # --- DOCUMENT ROUTES ---
        if resource_type == 'documents':
            sub_path = path_parts[1:] if len(path_parts) > 1 else []
            
            # Route: /documents (POST new document)
            if len(sub_path) == 0:
                if request.method == 'POST':
                    data = request.get_json()
                    if not data or not data.get('filename'):
                        return add_cors_headers({'error': 'Filename is required'}, 400)
                    
                    user_id = data.get('user_id')
                    filename = data.get('filename')
                    
                    if not user_id:
                        return add_cors_headers({'error': 'User ID is required'}, 400)
                    
                    # Try to get file from Google Cloud Storage
                    try:
                        storage_client = get_storage_client()
                        bucket = storage_client.bucket(BUCKET_NAME)
                        blob = bucket.blob(f"documents/{user_id}/{filename}")
                        
                        if not blob.exists():
                            return add_cors_headers({'error': 'File not found in storage'}, 404)
                        
                        # Download file content
                        file_content = blob.download_as_bytes()
                        
                        # Index document
                        result = index_document(user_id, filename, file_content=file_content)
                        
                        if result['success']:
                            return add_cors_headers(result, 200)
                        else:
                            return add_cors_headers(result, 500)
                            
                    except Exception as e:
                        return add_cors_headers({'error': f'Storage error: {str(e)}'}, 500)
                
                elif request.method == 'GET':
                    # List documents
                    data = request.args.to_dict()
                    user_id = data.get('user_id')
                    size = int(data.get('size', 20))
                    from_index = int(data.get('from', 0))
                    
                    if not user_id:
                        return add_cors_headers({'error': 'User ID is required'}, 400)
                    
                    result = list_documents(user_id, size, from_index)
                    
                    if result['success']:
                        return add_cors_headers(result, 200)
                    else:
                        return add_cors_headers(result, 500)
            
            # Route: /documents/{document_id} (DELETE specific document)
            elif len(sub_path) == 1:
                document_id = sub_path[0]
                
                if request.method == 'DELETE':
                    data = request.get_json() if request.is_json else {}
                    user_id = data.get('user_id')
                    
                    if not user_id:
                        return add_cors_headers({'error': 'User ID is required'}, 400)
                    
                    result = delete_document(user_id, document_id)
                    
                    if result['success']:
                        return add_cors_headers(result, 200)
                    else:
                        return add_cors_headers(result, 500)
        
        # --- SEARCH ROUTES ---
        elif resource_type == 'search':
            if request.method == 'POST':
                data = request.get_json()
                if not data or not data.get('query'):
                    return add_cors_headers({'error': 'Query is required'}, 400)
                
                user_id = data.get('user_id')
                query = data.get('query')
                search_type = data.get('search_type', 'keyword')
                size = int(data.get('size', 10))
                filters = data.get('filters', {})
                
                if not user_id:
                    return add_cors_headers({'error': 'User ID is required'}, 400)
                
                result = search_documents(user_id, query, search_type, size, filters)
                
                if result['success']:
                    return add_cors_headers(result, 200)
                else:
                    return add_cors_headers(result, 500)
        
        # --- HEALTH CHECK ROUTE ---
        elif resource_type == 'health':
            if request.method == 'GET':
                try:
                    # Test Elasticsearch connection
                    es_client = get_elasticsearch_client()
                    es_info = es_client.info()
                    
                    # Test Gemini connection
                    gemini_model = get_gemini_client()
                    
                    return add_cors_headers({
                        'status': 'healthy',
                        'elasticsearch': 'connected',
                        'gemini': 'connected',
                        'timestamp': datetime.utcnow().isoformat()
                    }, 200)
                except Exception as e:
                    return add_cors_headers({
                        'status': 'unhealthy',
                        'error': str(e)
                    }, 500)
        
        else:
            return add_cors_headers({'error': 'Resource not found'}, 404)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return add_cors_headers({'error': 'Internal server error'}, 500)

# Entry point for deployment
def knowledge_base_manager_es_http_entry(request):
    """Main entry point - redirects to the controller function."""
    return knowledge_base_manager_es_http(request)
