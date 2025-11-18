# Knowledge Base Manager ES

Elasticsearch-powered document management system for college counseling knowledge base with AI-powered metadata generation and vector search capabilities.

## Features

- **Document Indexing**: PDF and DOCX file processing with full text extraction
- **AI Metadata Generation**: Gemini LLM generates structured metadata for university documents
- **Vector Search**: Semantic search using embeddings for intelligent document retrieval
- **Multiple Search Types**: Keyword, vector, and hybrid search capabilities
- **User Isolation**: Multi-user support with document access control
- **RESTful API**: Clean HTTP API with path-based routing

## Architecture

Single Cloud Function with path-based routing following enterprise patterns:

```
POST   /documents     # Index document
GET    /documents     # List documents  
DELETE /documents/{id} # Delete document
POST   /search        # Search documents
GET    /health        # Health check
```

## Deployment

### Prerequisites
- Google Cloud Project with Cloud Functions API enabled
- Elasticsearch Cloud instance
- Gemini API key
- Google Cloud Storage bucket

### Environment Variables
```yaml
ES_CLOUD_ID: your-elastic-cloud-id
ES_API_KEY: your-elastic-api-key
GEMINI_API_KEY: your-gemini-api-key
ES_INDEX_NAME: university_documents
GCP_PROJECT_ID: your-project-id
GCS_BUCKET_NAME: your-bucket-name
DATA_STORE: college_admissions_kb
REGION: us-east1
```

### Deploy
```bash
# From the agents/college_counselor directory
./deploy.sh knowledge-es
```

## API Usage

### Health Check
```bash
curl -X GET "https://your-function-url/health"
```

### Search Documents
```bash
curl -X POST "https://your-function-url/search" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "query": "university admissions requirements",
    "search_type": "hybrid",
    "size": 10
  }'
```

### Index Document
```bash
# First upload file to GCS
gsutil cp document.pdf gs://your-bucket/documents/user123/document.pdf

# Then index it
curl -X POST "https://your-function-url/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "filename": "document.pdf"
  }'
```

### List Documents
```bash
curl -X GET "https://your-function-url/documents?user_id=user123&size=20&from=0"
```

### Delete Document
```bash
curl -X DELETE "https://your-function-url/documents/document-id" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user123"}'
```

## Search Types

1. **Keyword**: Traditional text search with fuzzy matching
2. **Vector**: Semantic search using document embeddings
3. **Hybrid**: Combines keyword and vector search for best results

## Document Processing

1. **Text Extraction**: PDF/DOCX files processed to extract text content
2. **Metadata Generation**: Gemini LLM analyzes content and generates structured metadata:
   - University identity (name, type, location, ranking)
   - Academic structure (majors, programs, colleges)
   - Admissions statistics (acceptance rate, applications, enrollment)
3. **Embedding Generation**: Vector embeddings created for semantic search
4. **Elasticsearch Indexing**: Document indexed with full text and vector data

## File Structure

```
knowledge_base_manager_es/
├── main.py              # Main function implementation
├── requirements.txt     # Python dependencies
├── env.yaml            # Environment variables
├── deploy.sh           # Deployment script
└── README.md           # This file
```

## Dependencies

- `functions-framework==3.0.0` - Google Cloud Functions framework
- `google-cloud-storage==2.10.0` - Google Cloud Storage client
- `google-generativeai==0.3.2` - Gemini AI client
- `elasticsearch==8.11.0` - Elasticsearch client
- `PyPDF2==3.0.1` - PDF text extraction
- `python-docx==1.1.0` - DOCX text extraction
- `Flask<3.0.0` - HTTP request handling

## Error Handling

- **400**: Bad request (missing parameters, invalid data)
- **404**: Resource not found (file not in storage, document not found)
- **500**: Internal server error (processing failures, service issues)

All responses include CORS headers and consistent JSON error format.

## Monitoring

- Health check endpoint monitors Elasticsearch and Gemini connectivity
- Cloud Function logs capture processing errors and performance metrics
- Google Cloud Monitoring can track function invocations and error rates

## Security

- User-based document isolation
- API key authentication for external services
- CORS configuration for web client access
- No sensitive data in function logs

## Deployment URL

https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app
