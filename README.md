# College Counselor - Cloud Functions

A comprehensive college counseling system with dual backend implementations (RAG and Elasticsearch) for document and profile management.

## Architecture

### Cloud Functions

#### Knowledge Base Managers
- **RAG Implementation**: `knowledge_base_manager` - Uses Google Cloud Storage + Vertex AI
- **ES Implementation**: `knowledge_base_manager_es` - Uses Elasticsearch for indexing and search

#### Profile Managers  
- **RAG Implementation**: `profile_manager` - Uses Google Cloud Storage + Vertex AI
- **ES Implementation**: `profile_manager_es` - Uses Elasticsearch for indexing and search

### Features

#### Document Management
- Upload college documents, guides, and resources
- Full-text search across document content
- Document categorization and metadata extraction
- Support for multiple file formats (PDF, TXT, DOCX)

#### Student Profile Management
- Comprehensive student profile creation and management
- Academic information tracking (GPA, test scores, coursework)
- Extracurricular activities and achievements
- College application progress tracking

#### Search and Discovery
- Advanced search with natural language queries
- Semantic search capabilities (RAG)
- Keyword search with relevance ranking (ES)
- Cross-document content analysis

## Quick Start

### Prerequisites
- Google Cloud CLI installed and configured
- Node.js 18+ (for frontend)
- Python 3.9+ (for development)
- Elasticsearch credentials (for ES functions)

### Deployment

1. **Deploy RAG Functions**
   ```bash
   ./deploy.sh knowledge-base-manager
   ./deploy.sh profile-manager
   ```

2. **Deploy ES Functions**
   ```bash
   ./deploy.sh knowledge-es
   ./deploy.sh profile-es
   ```

3. **Deploy Agents**
   ```bash
   ./deploy.sh agent
   ```

4. **Deploy Frontend**
   ```bash
   ./deploy_frontend.sh
   ```

### Testing

Run comprehensive integration tests for all functions:

```bash
# Test all functions at once
./run_all_tests.sh

# Test individual functions
./test_knowledge_base_manager.sh      # RAG Knowledge Base
./test_knowledge_base_manager_es.sh   # ES Knowledge Base  
./test_profile_manager.sh             # RAG Profile Manager
./test_profile_manager_es.sh          # ES Profile Manager
```

## Function Endpoints

### Knowledge Base Manager (RAG)
- **URL**: `https://us-east1-college-counselling-478115.cloudfunctions.net/knowledge-base-manager`
- **Health**: `GET /health`
- **Upload**: `POST /documents` (multipart form)
- **List**: `GET /documents`
- **Search**: `POST /documents/search`
- **Get**: `POST /get-document`
- **Delete**: `DELETE /documents/{name}`

### Knowledge Base Manager (ES)
- **URL**: `https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app`
- **Health**: `GET /health`
- **Upload**: `POST /upload-document` (multipart form)
- **List**: `GET /documents`
- **Search**: `POST /documents/search`
- **Delete**: `POST /documents/delete`

### Profile Manager (RAG)
- **URL**: `https://us-east1-college-counselling-478115.cloudfunctions.net/profile-manager`
- **Health**: `GET /health`
- **Upload**: `POST /upload-profile` (multipart form)
- **List**: `GET /list-profiles`
- **Get**: `POST /get-profile-content`
- **Delete**: `DELETE /delete-profile`

### Profile Manager (ES)
- **URL**: `https://profile-manager-es-pfnwjfp26a-ue.a.run.app`
- **Health**: `GET /health`
- **Upload**: `POST /upload-profile` (multipart form)
- **List**: `GET /profiles`
- **Delete**: `POST /profiles/delete`

## API Differences

### RAG vs ES Implementation

| Feature | RAG Functions | ES Functions |
|---------|---------------|--------------|
| Storage | Google Cloud Storage | Elasticsearch |
| Search | Semantic (Vertex AI) | Keyword (ES) |
| Upload Endpoint | `/documents`, `/upload-profile` | `/upload-document`, `/upload-profile` |
| User Parameter | `user_email` | `user_id` |
| Get by ID | ✅ Available | ❌ Not Implemented |
| Response Format | `{"success":true}` | `{"success": true}` |

## Configuration

### Environment Variables

#### RAG Functions
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket
- `VERTEX_AI_PROJECT_ID`: GCP project ID
- `VERTEX_AI_LOCATION`: Vertex AI region

#### ES Functions
- `ES_CLOUD_ID`: Elasticsearch cloud ID
- `ES_API_KEY`: Elasticsearch API key
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket
- `GEMINI_API_KEY`: Google Gemini API key

## Testing Coverage

Each comprehensive test suite includes:

### Health Checks
- Basic connectivity
- Response format validation
- CORS header verification

### CRUD Operations
- Create (upload documents/profiles)
- Read (list and retrieve)
- Update (via re-upload)
- Delete operations

### Error Handling
- Invalid endpoints
- Missing required parameters
- Malformed requests
- File upload errors

### Performance Tests
- Response time validation
- Large file handling
- Concurrent operations

### Integration Tests
- End-to-end workflows
- Cross-function compatibility
- Data consistency validation

## Development

### Local Development

1. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   npm install  # in frontend directory
   ```

3. **Run Local Tests**
   ```bash
   ./run_all_tests.sh
   ```

### Project Structure

```
college_counselor/
├── cloud_functions/
│   ├── knowledge_base_manager/          # RAG implementation
│   ├── knowledge_base_manager_es/       # ES implementation
│   ├── profile_manager/                 # RAG implementation
│   └── profile_manager_es/              # ES implementation
├── agents/
│   ├── college_expert_rag/              # RAG agent
│   └── college_expert_es/               # ES agent
├── frontend/                            # React application
├── test_*.sh                            # Comprehensive test suites
├── run_all_tests.sh                     # Master test runner
├── deploy.sh                           # Deployment script
└── deploy_frontend.sh                   # Frontend deployment
```

## Monitoring and Logging

### Cloud Function Logs
```bash
# View logs for specific function
gcloud functions logs read knowledge-base-manager --limit=50
gcloud functions logs read knowledge-base-manager-es --limit=50
gcloud functions logs read profile-manager --limit=50
gcloud functions logs read profile-manager-es --limit=50
```

### Test Logs
All test logs are saved to `test_logs/` with timestamps:
```bash
ls -la test_logs/
# View latest test results
tail -f test_logs/test_*_latest.log
```

## Troubleshooting

### Common Issues

1. **ES Functions Not Connecting**
   - Verify ES credentials in `env.yaml`
   - Check Elasticsearch cluster status
   - Validate API key permissions

2. **File Upload Failures**
   - Check file size limits
   - Verify GCS bucket permissions
   - Validate file format support

3. **Search Not Working**
   - Ensure documents are indexed
   - Check search query format
   - Verify ES mapping configuration

### Debug Commands

```bash
# Test individual function health
curl -f https://function-url/health

# Check ES connectivity
curl -X GET "your-es-cluster:9200/_cluster/health"

# Validate GCS bucket access
gsutil ls gs://your-bucket-name
```

## Performance

### Benchmarks
- **Document Upload**: < 10 seconds for 1MB files
- **Search Response**: < 5 seconds for complex queries
- **Profile Processing**: < 15 seconds for comprehensive profiles
- **Health Check**: < 2 seconds response time

### Scaling
- **RAG Functions**: Auto-scales with Cloud Functions
- **ES Functions**: Scales with Elasticsearch cluster
- **Storage**: Unlimited with Google Cloud Storage
- **Search**: Millisecond response with ES indexing

## Security

### Authentication
- Firebase Auth integration for frontend
- IAM permissions for Cloud Functions
- API key authentication for ES

### Data Protection
- Encrypted storage in GCS
- TLS encryption for all API calls
- GDPR compliance considerations

## Support

### Documentation
- Function-specific documentation in each `cloud_functions/` subdirectory
- API documentation in code comments
- Test examples in test files

### Contact
- For deployment issues: Check deployment logs
- For API issues: Run comprehensive tests
- For performance issues: Check Cloud Function metrics
