# College Counselor Application

AI-powered college admissions analysis system with multi-agent backend, cloud function for profile management, and React frontend.

## Features

- **College Information Chat** - Ask questions about colleges and get knowledge base powered answers
- **Student Profile Management** - Upload, view, and manage academic profiles
- **Admissions Analysis** - Comprehensive multi-agent analysis of admissions chances

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                   │
│  - College Info Chat                                        │
│  - Student Profile Management                               │
│  - Admissions Analysis                                      │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├──────────────────┐
                  │                  │
                  ▼                  ▼
┌─────────────────────────┐  ┌──────────────────────────┐
│  Backend Agent          │  │  Profile Manager         │
│  (Cloud Run)            │  │  (Cloud Function)        │
│                         │  │                          │
│  - MasterReasoningAgent │  │  - Upload Profile        │
│  - StudentProfileAgent  │  │  - List Profiles         │
│  - QuantitativeAnalyst  │  │  - Delete Profile        │
│  - BrandAnalyst         │  │                          │
│  - CommunityAnalyst     │  │  Store: student_profile  │
│  - KnowledgeBaseAnalyst │  │                          │
│                         │  │                          │
│  Store:                 │  │                          │
│  college_admissions_kb  │  │                          │
└─────────────────────────┘  └──────────────────────────┘
```

## Quick Start

### Prerequisites

- Google Cloud SDK (`gcloud`)
- Google ADK (`adk`)
- Node.js & npm
- Firebase CLI
- Python 3.11+

### Environment Variables

```bash
export GCP_PROJECT_ID='college-counsellor'
export GEMINI_API_KEY='your-gemini-api-key'
```

### Deploy Everything

```bash
# 1. Make scripts executable
chmod +x deploy.sh deploy_backend.sh deploy_frontend.sh setup.sh

# 2. Run setup
./setup.sh

# 3. Deploy
./deploy.sh
```

## Configuration

### Frontend Environment Variables

Create `frontend/.env` with:

```bash
# Backend API Configuration
VITE_API_URL=https://college-counselor-agent-xxxxx-ue.a.run.app
VITE_PROFILE_MANAGER_URL=https://us-east1-college-counsellor.cloudfunctions.net/profile-manager

# Application Settings
VITE_APP_NAME=College Counselor
VITE_APP_VERSION=1.0.0

# Default Data Stores
VITE_KNOWLEDGE_BASE_STORE=college_admissions_kb
VITE_STUDENT_PROFILE_STORE=student_profile
```

See `frontend/.env.example` for template.

### Backend Configuration

**Agent** (`agents/`):
- Model: `gemini-2.5-flash`
- Store: `college_admissions_kb`

**Cloud Function** (`cloud_functions/profile_manager/`):
- Runtime: Python 3.12
- Store: `student_profile`
- Environment: `.env.yaml`

## API Endpoints

### Backend Agent (Cloud Run)

**Base URL:** `VITE_API_URL`

- `POST /apps/agents/users/user/sessions` - Start new session
- `POST /apps/agents/users/user/sessions/{id}` - Send message
- `GET /apps/agents/users/user/sessions/{id}` - Get session

### Profile Manager (Cloud Function)

**Base URL:** `VITE_PROFILE_MANAGER_URL`

- `POST /upload-profile` - Upload student profile
- `GET /list-profiles` - List all profiles
- `DELETE /delete-profile` - Delete a profile

## Development

### Local Development

```bash
./start_local.sh
```

This starts:
- Backend: http://localhost:8080
- Frontend: http://localhost:3000

**Note:** Profile upload requires deployed cloud function.

### Backend Only

```bash
./deploy_backend.sh
```

### Frontend Only

```bash
export VITE_API_URL='your-agent-url'
export VITE_PROFILE_MANAGER_URL='your-function-url'
./deploy_frontend.sh
```

## Project Structure

```
college_counselor/
├── agents/                          # Backend Agent
│   ├── agent.py                    # Main orchestrator
│   ├── schemas/                    # Pydantic schemas
│   ├── tools/                      # Document management
│   └── sub_agents/                 # Specialist agents
│
├── cloud_functions/                # Cloud Functions
│   └── profile_manager/            # Profile management
│       ├── main.py
│       ├── requirements.txt
│       └── .env.yaml
│
├── frontend/                       # React Frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Profile.jsx        # Profile management
│   │   │   ├── Chat.jsx           # College info chat
│   │   │   └── Analysis.jsx       # Admissions analysis
│   │   ├── services/
│   │   │   └── api.js             # API client
│   │   └── App.jsx
│   ├── .env.example
│   └── firebase.json
│
├── deploy.sh                       # Complete deployment
├── deploy_backend.sh               # Backend only
├── deploy_frontend.sh              # Frontend only
├── setup.sh                        # Setup dependencies
└── start_local.sh                  # Local development
```

## Usage

### 1. Ask About Colleges

1. Visit https://college-counsellor.web.app/chat
2. Ask: "What does USC look for in applicants?"
3. Get knowledge base powered answer
4. Ask follow-up questions

### 2. Upload Profile

1. Visit https://college-counsellor.web.app
2. Select academic profile file (PDF, DOCX, TXT)
3. Click "Upload Profile"
4. Wait for confirmation

### 3. Get Analysis

1. Visit https://college-counsellor.web.app/analysis
2. Enter college name (e.g., "Stanford University")
3. Enter intended major (e.g., "Computer Science")
4. Click "Analyze Admissions Chances"
5. Wait 1-2 minutes for comprehensive report

## Agent Capabilities

### Chat Mode
- Answers questions from knowledge base only
- No general knowledge used
- Provides citations
- Conversational interface

### Analysis Mode
- Reads profile from student_profile store
- Orchestrates multiple specialist agents
- Provides risk assessment
- Detailed recommendations

## Troubleshooting

### "Failed to load profiles"
- Check cloud function is deployed
- Verify `VITE_PROFILE_MANAGER_URL` in `.env`
- Check browser console for errors

### "Analysis failed"
- Ensure profile is uploaded
- Check backend agent is running
- Verify `VITE_API_URL` in `.env`

### "GEMINI_API_KEY not set"
```bash
export GEMINI_API_KEY='your-api-key'
```

## Deployment URLs

After deployment:

- **Frontend:** https://college-counsellor.web.app
- **Backend Agent:** https://college-counselor-agent-xxxxx-ue.a.run.app
- **Cloud Function:** https://us-east1-college-counsellor.cloudfunctions.net/profile-manager

## Cost Estimate

**Monthly (Light Usage):**
- Cloud Run: $0-5
- Cloud Functions: $0-2
- Firebase Hosting: $0
- Gemini API: $5-20

**Total: ~$5-27/month**

## Support

For issues:
1. Check this README
2. Review deployment logs
3. Check browser console
4. Verify environment variables

## License

Part of the GraphRAG multi-agent system.
# college-expert
