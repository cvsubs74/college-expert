# Knowledge Base Manager - Universities V2 (Firestore)

This Cloud Function manages university profile documents in **Firestore** for storage and retrieval. It is API-compatible with the Elasticsearch version (`knowledge_base_manager_universities`).

## Endpoints

| Method | Endpoint/Condition | Description |
|--------|-------------------|-------------|
| GET | `/health` | Health check |
| GET | `/?id={university_id}` | Get a specific university (current cycle) |
| GET | `/?id={id}&year=2025` | Get that cycle year's snapshot (ADR 0002); a miss lists available years |
| GET | `/?id={id}&sections=admissions_data,financials` | Project the profile to just those top-level sections (`sections_returned` / `unknown_sections` in response; all-typo request → 400) |
| GET | `/?id={id}&action=versions` | List stored cycle-year snapshots |
| GET | `/?id={id}&action=majors` | Trust-labeled per-major entry facts (entry_path enum + verbatim wording, structural entry_risk, basis labels, richness_tier); `&college=`/`&q=` filter, `&year=` reads a snapshot |
| GET | `/?id={id}&action=history` | Two-axis year view: compact per-cycle `snapshots` + school-reported `reported_trends` (`verified:false`); `&sections=` returns raw per-year sections, `&years=2024,2025` filters |
| GET | `/` | List all universities |
| POST | `{"query": "...", "limit": 10}` | Search universities |
| POST | `{"profile": {...}, "year": 2026}` | Ingest university profile as a cycle-year snapshot |
| POST | `{"action": "chat", "university_id": "...", "question": "..."}` | Chat about university |
| POST | `{"university_ids": [...]}` | Batch get multiple universities (main docs only) |
| DELETE | `{"university_id": "...", "year": 2025}` | Delete a university (all years), or one snapshot (`year`) |

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
