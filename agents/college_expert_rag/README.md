# College Expert RAG Agent

A specialized AI agent for college admissions counseling using RAG (Retrieval-Augmented Generation) knowledge base.

## Features

- **Student Profile Analysis**: Analyzes academic profiles using RAG knowledge base
- **Knowledge Base Search**: Searches college admissions documents using semantic search
- **Personalized Recommendations**: Provides tailored college application advice
- **Citations**: Includes source citations for all information

## Architecture

```
CollegeExpertRAG (SequentialAgent)
├── StudentProfileAgent_RAG
│   └── search_user_profile (RAG cloud function)
├── KnowledgeBaseAnalyst_RAG  
│   └── search_knowledge_base (RAG cloud function)
└── ResponseFormatter_RAG
```

## Dependencies

- google-adk: Agent framework
- google-genai: Gemini API integration
- requests: Cloud function calls
- python-dotenv: Environment management

## Environment Variables

See `.env.example` for required environment variables:

- `GEMINI_API_KEY`: Gemini API key
- `KNOWLEDGE_BASE_MANAGER_RAG_URL`: RAG knowledge base cloud function
- `PROFILE_MANAGER_RAG_URL`: RAG profile manager cloud function

## Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
adk web

# Deploy to Cloud Run
adk deploy cloud_run --project=your-project --region=us-east1 --service_name=college-expert-rag --allow_origins="*"
```

## Usage

The agent processes student queries about college admissions:

- "What are my chances at Stanford?"
- "How should I prepare my application for MIT?"
- "What extracurriculars does Harvard look for?"

## API Endpoints

- Session Creation: `POST /apps/college_expert_rag/users/user/sessions`
- Message Sending: `POST /apps/college_expert_rag/users/user/sessions/{sessionId}`
