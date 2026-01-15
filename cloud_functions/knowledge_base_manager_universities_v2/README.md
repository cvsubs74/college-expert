# Knowledge Base Manager - Universities V2 (Firestore)

This Cloud Function manages university profile documents in **Firestore** for storage and retrieval. It is API-compatible with the Elasticsearch version (`knowledge_base_manager_universities`).

## Endpoints

| Method | Endpoint/Condition | Description |
|--------|-------------------|-------------|
| GET | `/health` | Health check |
| GET | `/?id={university_id}` | Get a specific university |
| GET | `/` | List all universities |
| POST | `{"query": "...", "limit": 10}` | Search universities |
| POST | `{"profile": {...}}` | Ingest university profile |
| POST | `{"action": "chat", "university_id": "...", "question": "..."}` | Chat about university |
| POST | `{"university_ids": [...]}` | Batch get multiple universities |
| DELETE | `{"university_id": "..."}` | Delete a university |

## Search Request

```json
{
  "query": "computer science california",
  "limit": 10,
  "filters": {
    "state": "CA",
    "acceptance_rate_max": 30
  },
  "search_type": "keyword",
  "exclude_ids": ["stanford_university"],
  "sort_by": "relevance"
}
```

## Ingest Request

```json
{
  "profile": {
    "_id": "stanford_university",
    "metadata": {
      "official_name": "Stanford University",
      "location": {"city": "Stanford", "state": "CA", "type": "Private"}
    },
    "strategic_profile": {
      "us_news_rank": 3,
      "executive_summary": "..."
    },
    "admissions_data": {
      "current_status": {"overall_acceptance_rate": 4.0}
    }
  }
}
```

## Differences from ES Version

- Uses Firestore collection `universities` instead of Elasticsearch index
- Search uses in-memory text matching on pre-indexed keywords (no BM25/ELSER)
- For production semantic search, consider Algolia or Vector Search

## Deployment

```bash
./deploy.sh knowledge-universities-v2
```

## Local Development

```bash
cd cloud_functions/knowledge_base_manager_universities_v2
functions-framework --target=knowledge_base_manager_universities_v2_http_entry --port=8082
```
