# College Expert ES Agent

A specialized AI agent for college admissions counseling using Elasticsearch knowledge base.

## Features

- **Student Profile Analysis**: Analyzes academic profiles using Elasticsearch
- **Knowledge Base Search**: Searches college admissions documents using keyword/vector search
- **Personalized Recommendations**: Provides tailored college application advice
- **Multiple Search Types**: Supports keyword, vector, and hybrid search

## Architecture

```
CollegeExpertES (SequentialAgent)
├── StudentProfileAgent_ES
│   └── search_documents (ES cloud function)
├── KnowledgeBaseAnalyst_ES  
│   └── search_documents (ES cloud function)
└── ResponseFormatter_ES
```

## Dependencies

- google-adk: Agent framework
- google-genai: Gemini API integration
- requests: Cloud function calls
- python-dotenv: Environment management
- elasticsearch: ES client library

## Environment Variables

See `.env.example` for required environment variables:

- `GEMINI_API_KEY`: Gemini API key
- `ES_CLOUD_ID`: Elasticsearch cloud ID
- `ES_API_KEY`: Elasticsearch API key
- `KNOWLEDGE_BASE_MANAGER_ES_URL`: ES knowledge base cloud function
- `PROFILE_MANAGER_ES_URL`: ES profile manager cloud function

## Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
adk web

# Deploy to Cloud Run
adk deploy cloud_run --project=your-project --region=us-east1 --service_name=college-expert-es --allow_origins="*"
```

## Usage

The agent processes student queries about college admissions:

- "What are my chances at Stanford?"
- "How should I prepare my application for MIT?"
- "What extracurriculars does Harvard look for?"

## API Endpoints

- Session Creation: `POST /apps/college_expert_es/users/user/sessions`
- Message Sending: `POST /apps/college_expert_es/users/user/sessions/{sessionId}`

## Search Types

- **Keyword Search**: Traditional text search
- **Vector Search**: Semantic similarity search
- **Hybrid Search**: Combines keyword and vector search
