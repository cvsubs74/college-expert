# Knowledge Base Manager - Universities

Cloud Function for managing university profile documents in Elasticsearch with hybrid search support.

## Features

- **Hybrid Search**: Combines BM25 text search with semantic vector search
- **Ingest**: Add new university profiles with automatic embedding generation
- **Search**: Query universities using keyword, semantic, or hybrid search
- **Filter**: Filter by state, type, acceptance rate, market position
- **CRUD**: Full create, read, update, delete operations

## API Endpoints

### Health Check
```
GET /?action=health
```

### List Universities
```
GET /
```

### Get University
```
GET /?id=ucb
```

### Search Universities
```
POST /
{
    "query": "computer science research university California",
    "limit": 10,
    "search_type": "hybrid",  // "hybrid", "semantic", or "keyword"
    "filters": {
        "state": "CA",
        "acceptance_rate_max": 30
    }
}
```

### Ingest University
```
POST /
{
    "profile": {
        "_id": "stanford",
        "metadata": {
            "official_name": "Stanford University",
            "location": {"city": "Stanford", "state": "CA", "type": "Private"}
        },
        ...
    }
}
```

### Delete University
```
DELETE /
{
    "id": "stanford"
}
```

## Environment Variables

- `ES_CLOUD_ID`: Elasticsearch Cloud ID
- `ES_API_KEY`: Elasticsearch API Key
- `ES_INDEX_NAME`: Index name (default: `knowledgebase_universities`)
- `GEMINI_API_KEY`: Google Gemini API key for embeddings

## Deployment

```bash
cd cloud_functions/knowledge_base_manager_universities

gcloud functions deploy knowledge-base-manager-universities \
    --gen2 \
    --runtime=python311 \
    --region=us-east1 \
    --source=. \
    --entry-point=knowledge_base_manager_universities_http_entry \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=env.yaml \
    --memory=512MB \
    --timeout=300s
```

## Index Schema

The Elasticsearch index supports:

- **Text Fields**: `searchable_text`, `official_name` for BM25 search
- **Vector Field**: `embedding` (768 dims, Gemini text-embedding-004)
- **Filter Fields**: `acceptance_rate`, `test_policy`, `market_position`, `location.*`
- **Storage**: Full `profile` object stored for retrieval

## Dependencies

- `functions-framework` - Cloud Functions framework
- `elasticsearch` - Elasticsearch client
- `google-generativeai` - Gemini API for embeddings
