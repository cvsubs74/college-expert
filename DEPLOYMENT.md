# College Counselor - Deployment Guide

## Quick Start

The `deploy.sh` script supports modular deployment of individual components or all at once.

## Usage

```bash
./deploy.sh [target]
```

## Deployment Targets

### Individual Components

| Command | Description |
|---------|-------------|
| `./deploy.sh agent` | Deploy only the backend agent to Cloud Run |
| `./deploy.sh profile` | Deploy only the Profile Manager cloud function |
| `./deploy.sh knowledge` | Deploy only the Knowledge Base Manager cloud function |
| `./deploy.sh frontend` | Deploy only the frontend to Firebase |

### Grouped Deployments

| Command | Description |
|---------|-------------|
| `./deploy.sh functions` | Deploy all cloud functions (profile + knowledge base) |
| `./deploy.sh backend` | Deploy agent + all cloud functions |
| `./deploy.sh all` | Deploy everything (default) |

### Help

```bash
./deploy.sh --help
```

## Examples

### Deploy Everything
```bash
./deploy.sh
# or
./deploy.sh all
```

### Deploy Only Knowledge Base Manager (After Code Changes)
```bash
./deploy.sh knowledge
```

### Deploy Only the Agent
```bash
./deploy.sh agent
```

### Deploy All Cloud Functions
```bash
./deploy.sh functions
```

### Deploy Backend (Agent + Functions)
```bash
./deploy.sh backend
```

## Common Workflows

### 1. Update Knowledge Base Manager Configuration
```bash
# Edit cloud_functions/knowledge_base_manager/.env.yaml
# Then redeploy only that function
./deploy.sh knowledge
```

### 2. Update Agent Code
```bash
# Make changes to agents/
# Then redeploy only the agent
./deploy.sh agent
```

### 3. Update Frontend
```bash
# Make changes to frontend/
# Then redeploy only frontend
./deploy.sh frontend
```

### 4. Deploy All Cloud Functions After Updates
```bash
# After updating both profile and knowledge base managers
./deploy.sh functions
```

## Prerequisites

- Google Cloud SDK (`gcloud`)
- Google ADK (`adk`)
- Node.js and npm
- Firebase CLI
- GEMINI_API_KEY set in environment or Secret Manager

## Environment Variables

The script will automatically:
1. Try to use `$GEMINI_API_KEY` from environment
2. Fall back to fetching from Secret Manager
3. Use `$GCP_PROJECT_ID` or default to `college-counselling-478115`

## Component Details

### Backend Agent
- **Service**: Cloud Run
- **Name**: `college-counselor-agent`
- **Region**: `us-east1`
- **Framework**: Google ADK

### Profile Manager Function
- **Type**: Cloud Function Gen 2
- **Name**: `profile-manager`
- **Runtime**: Python 3.12
- **Timeout**: 540s
- **Memory**: 512MB

### Knowledge Base Manager Function
- **Type**: Cloud Function Gen 2
- **Name**: `knowledge-base-manager`
- **Runtime**: Python 3.12
- **Timeout**: 540s
- **Memory**: 512MB
- **Config**: Uses `.env.yaml` for chunking settings

### Frontend
- **Platform**: Firebase Hosting
- **Site**: `college-strategy.web.app`
- **Framework**: React + Vite

## Troubleshooting

### Deployment Fails
```bash
# Check logs for specific component
gcloud functions logs read knowledge-base-manager --region=us-east1 --limit=50
gcloud run services logs read college-counselor-agent --region=us-east1 --limit=50
```

### Environment Variables Not Set
```bash
# Verify .env.yaml files exist
ls cloud_functions/profile_manager/.env.yaml
ls cloud_functions/knowledge_base_manager/.env.yaml

# Check values are quoted strings
cat cloud_functions/knowledge_base_manager/.env.yaml
```

### Permission Errors
```bash
# Ensure you're authenticated
gcloud auth login
gcloud config set project college-counselling-478115
```

## Deployment Time Estimates

- **Agent**: ~2-3 minutes
- **Profile Manager**: ~1-2 minutes
- **Knowledge Base Manager**: ~1-2 minutes
- **Frontend**: ~1-2 minutes
- **All**: ~5-8 minutes

## Post-Deployment

After deployment, URLs are displayed:
- Backend Agent: `https://college-counselor-agent-*.run.app`
- Profile Manager: `https://profile-manager-*.run.app`
- Knowledge Base Manager: `https://knowledge-base-manager-*.run.app`
- Frontend: `https://college-strategy.web.app`

Check the deployment summary for exact URLs.
