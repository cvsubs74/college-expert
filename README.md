# College Counselor Application

AI-powered college admissions analysis system with multi-agent backend, cloud functions for document management, and React frontend. Uses Google Gemini 2.5 Flash for intelligent analysis and Google Cloud Storage for file management.

## 🎯 Features

### Core Capabilities
- **College Information Chat** - Ask questions about colleges and get knowledge base powered answers
- **Student Profile Management** - Upload, view, preview, and manage academic profiles (PDF, DOCX, TXT)
- **Knowledge Base Management** - Upload and manage university research documents
- **Admissions Analysis** - Comprehensive multi-agent analysis of admissions chances
- **Bulk Operations** - Select and delete multiple files simultaneously
- **PDF Preview** - View PDF documents directly in the browser
- **Multi-file Upload** - Upload multiple files in parallel with progress tracking

### Recent Improvements (Nov 2025)
- ✅ Simplified agent instructions for better reliability (200 lines → 30 lines)
- ✅ Fixed profile retrieval to always call StudentProfileAgent first
- ✅ Added bulk delete functionality with parallel processing
- ✅ Implemented PDF preview using GCS public URLs
- ✅ Increased API timeout to 5 minutes for complex analysis
- ✅ Enhanced security with comprehensive .gitignore
- ✅ Removed node_modules from git (500MB → 5MB repository)

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                        │
│  - College Info Chat                                             │
│  - Student Profile Management (Upload, Preview, Bulk Delete)     │
│  - Knowledge Base Management (Upload, Preview, Bulk Delete)      │
│  - Admissions Analysis                                           │
└─────────────────┬────────────────────────────────────────────────┘
                  │
                  ├──────────────────┬──────────────────┐
                  │                  │                  │
                  ▼                  ▼                  ▼
┌──────────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  Backend Agent       │  │  Profile Manager  │  │  KB Manager      │
│  (Cloud Run)         │  │  (Cloud Function) │  │  (Cloud Function)│
│                      │  │                   │  │                  │
│  MasterReasoningAgent│  │  - Upload         │  │  - Upload        │
│  ├─StudentProfile    │  │  - List           │  │  - List          │
│  ├─Quantitative      │  │  - Delete         │  │  - Delete        │
│  ├─Brand             │  │  - Get Content    │  │  - Get Content   │
│  ├─Community         │  │                   │  │                  │
│  └─KnowledgeBase     │  │  Store:           │  │  Store:          │
│                      │  │  student_profile  │  │  college_kb      │
│  Store:              │  │  (user-specific)  │  │  (shared)        │
│  college_admissions  │  │                   │  │                  │
└──────────────────────┘  └───────────────────┘  └──────────────────┘
                                    │                      │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────┐
                              │  Google Cloud Storage       │
                              │  college-counselling-       │
                              │  478115-student-profiles    │
                              └─────────────────────────────┘
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
VITE_PROFILE_MANAGER_URL=https://profile-manager-pfnwjfp26a-ue.a.run.app
VITE_KNOWLEDGE_BASE_URL=https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app

# Firebase Configuration
VITE_FIREBASE_API_KEY=your-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=college-counselling-478115.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=college-counselling-478115
VITE_FIREBASE_STORAGE_BUCKET=college-counselling-478115-student-profiles
VITE_FIREBASE_APP_ID=your-firebase-app-id

# Application Settings
VITE_APP_NAME=College Counselor
VITE_APP_VERSION=2.0.0
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

## 📡 API Endpoints

### Backend Agent (Cloud Run)

**Base URL:** `VITE_API_URL`

- `POST /apps/agents/users/user/sessions` - Start new session
- `POST /apps/agents/users/user/sessions/{id}` - Send message with `{user_input: "message"}`
- `GET /apps/agents/users/user/sessions/{id}` - Get session state

**Timeout:** 5 minutes (300 seconds) for complex multi-agent analysis

### Profile Manager (Cloud Function)

**Base URL:** `VITE_PROFILE_MANAGER_URL`

- `POST /upload-profile` - Upload student profile (multipart/form-data)
  - Body: `{file: File, user_email: string}`
- `GET /list-profiles?user_email=email` - List user's profiles
- `DELETE /delete-profile` - Delete a profile
  - Body: `{document_name: string, user_email: string, filename: string}`
- `POST /get-document-content` - Get profile content for preview
  - Body: `{file_name: string, user_email: string}`
  - Returns: `{success: bool, content: string, download_url: string, is_pdf: bool}`

### Knowledge Base Manager (Cloud Function)

**Base URL:** `VITE_KNOWLEDGE_BASE_URL`

- `POST /upload-document` - Upload knowledge base document
  - Body: `{file: File}`
- `GET /list-documents` - List all knowledge base documents
- `DELETE /delete-document` - Delete a document
  - Body: `{document_name: string, filename: string}`
- `POST /get-document-content` - Get document content for preview
  - Body: `{file_name: string}`
  - Returns: `{success: bool, content: string, download_url: string, is_pdf: bool}`

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

## 📖 Usage Guide

### 1. Ask About Colleges (General Questions)

1. Visit https://college-strategy.web.app/chat
2. Ask general questions like:
   - "What does USC look for in applicants?"
   - "Compare career outcomes for UC Berkeley vs UCLA business programs"
   - "What are the admission requirements for Stanford?"
3. Agent automatically calls 5 specialist agents:
   - QuantitativeAnalyst (admissions stats)
   - BrandAnalyst (institutional priorities)
   - CommunityAnalyst (student experiences)
   - CareerOutcomesAnalyst (employment & career data)
   - KnowledgeBaseAnalyst (general info)
4. Get comprehensive answer with data from all sources
5. Use suggested questions for deeper exploration

**Note:** General questions do NOT require uploading your profile

### 2. Manage Student Profiles

**Upload:**
1. Visit https://college-strategy.web.app (Profile tab)
2. Select one or multiple files (PDF, DOCX, TXT)
3. Click "Upload Profile"
4. Watch upload progress for each file
5. Wait for confirmation

**Preview:**
1. Click the eye icon next to any profile
2. View PDF in browser or read text content
3. Click "Open in new tab" for full-screen PDF view

**Bulk Delete:**
1. Check boxes next to profiles to delete
2. Or click "Select All" to select everything
3. Click "Delete X" button
4. Confirm deletion
5. See success/failure summary

### 3. Manage Knowledge Base

**Upload Documents:**
1. Visit Knowledge Base tab
2. Select university research documents
3. Upload multiple files simultaneously
4. Track individual upload progress

**Bulk Operations:**
- Same bulk delete functionality as profiles
- Preview PDFs and documents
- Manage shared knowledge base

### 4. Get Admissions Analysis (Personalized)

1. **First, upload your profile** (see step 2 above)
2. Visit https://college-strategy.web.app/analysis
3. Type your question (e.g., "Analyze my chances at Stanford for Computer Science")
4. Agent automatically:
   - Retrieves YOUR profile from student_profile store
   - Calls ALL 6 specialist agents:
     * StudentProfileAgent (your academic profile)
     * QuantitativeAnalyst (compare your stats to university)
     * BrandAnalyst (assess your fit with institutional priorities)
     * CommunityAnalyst (evaluate your extracurricular alignment)
     * CareerOutcomesAnalyst (career prospects for your major)
     * KnowledgeBaseAnalyst (program-specific information)
   - Synthesizes personalized admissions prediction
5. Wait 2-5 minutes for detailed report
6. Review risk assessment and recommendations

**Note:** Admissions analysis REQUIRES uploading your profile first

## 🤖 Agent Capabilities

### MasterReasoningAgent (Orchestrator)
- **Two-Mode Operation:**
  - **General Questions:** Calls 5 agents (all except StudentProfile)
  - **Personal Analysis:** Calls all 6 agents (including StudentProfile)
- **Smart Routing:** Automatically detects if question is general or personal
- **Multi-Agent Coordination:** Orchestrates up to 6 specialist agents
- **Data Validation:** Ensures no hallucination, only uses retrieved data
- **Timeout Handling:** 5-minute processing window

### StudentProfileAgent
- Retrieves user-specific profile from File Search store
- Parses academic data (GPA, courses, test scores)
- Analyzes extracurriculars and awards
- Identifies student's "spike" or theme
- Returns structured StudentProfile schema

### QuantitativeAnalyst
- Analyzes numerical academic metrics
- Compares to university percentiles
- Calculates academic fit scores

### BrandAnalyst
- Evaluates university brand alignment
- Analyzes institutional priorities
- Assesses cultural fit

### CommunityAnalyst
- Reviews extracurricular alignment
- Evaluates community impact
- Assesses leadership potential

### CareerOutcomesAnalyst
- Searches for employment statistics and salary data
- Identifies top employers and common industries
- Analyzes job titles and career paths
- Reviews graduate school placement rates
- Evaluates career services and support
- Assesses data availability (Comprehensive/Partial/Limited)
- Returns structured CareerOutcomesData schema

### KnowledgeBaseAnalyst
- Searches shared knowledge base
- Retrieves university-specific information
- Provides expert insights and data
- Returns citation-free answers

### Response Formatter
- Formats final output as structured JSON
- Generates 4 relevant follow-up questions
- Ensures proper Markdown formatting
- Returns OrchestratorOutput schema

## 🔧 Troubleshooting

### "Failed to load profiles"
- Check cloud function is deployed: `gcloud functions list`
- Verify `VITE_PROFILE_MANAGER_URL` in `.env`
- Check browser console for errors
- Ensure user is signed in with Firebase Auth

### "Analysis failed" or "Profile not found"
- Ensure profile is uploaded in Profile tab
- Check that StudentProfileAgent is being called (see logs)
- Verify backend agent is running
- Check `VITE_API_URL` in `.env`
- Look for timeout errors (should be 5 minutes)

### "Timeout of 300000ms exceeded"
- Analysis is taking too long (>5 minutes)
- Check agent logs for stuck operations
- Verify all sub-agents are responding
- Consider simplifying the query

### "PDF preview not working"
- Ensure GCS bucket has public access configured
- Check CORS settings on bucket
- Verify blob.make_public() is working
- Check browser console for CORS errors

### "Bulk delete failing"
- Check that all selected items have valid resource_name
- Verify delete permissions on GCS and File Search
- Check cloud function logs for specific errors
- Try deleting items individually first

### "GEMINI_API_KEY not set"
```bash
export GEMINI_API_KEY='your-api-key'
# Or use Secret Manager
gcloud secrets versions access latest --secret=gemini-api-key
```

### "node_modules in git"
- Already removed from tracking
- Run `npm install` locally to get dependencies
- Never commit node_modules

## 🌐 Deployment URLs

**Production:**
- **Frontend:** https://college-strategy.web.app
- **Backend Agent:** https://college-counselor-agent-xxxxx-ue.a.run.app
- **Profile Manager:** https://profile-manager-pfnwjfp26a-ue.a.run.app
- **Knowledge Base Manager:** https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app

**GCP Project:** `college-counselling-478115`

## 💰 Cost Estimate

**Monthly (Light Usage - ~100 analyses):**
- Cloud Run (Agent): $0-5
- Cloud Functions (2): $0-4
- Firebase Hosting: $0
- Cloud Storage: $0-1
- Gemini API: $10-30
- File Search API: $5-15

**Total: ~$15-55/month**

**Monthly (Heavy Usage - ~1000 analyses):**
- Cloud Run: $10-20
- Cloud Functions: $5-10
- Firebase Hosting: $0
- Cloud Storage: $1-3
- Gemini API: $50-100
- File Search API: $20-50

**Total: ~$86-183/month**

## 🔒 Security Features

- **Environment Variables:** All secrets in `.env` files (gitignored)
- **API Keys:** Stored in Google Cloud Secret Manager
- **Service Accounts:** Minimal permissions (Firestore, Storage, Secret Manager)
- **CORS:** Configured for specific origins only
- **User Authentication:** Firebase Auth for profile isolation
- **File Access:** User-specific File Search stores
- **Git Protection:** Comprehensive .gitignore for sensitive files

## 📊 Performance Metrics

- **Repository Size:** 5-10MB (down from 500MB)
- **Frontend Build:** ~1.5 seconds
- **API Timeout:** 5 minutes (300 seconds)
- **Parallel Uploads:** Up to 75% faster than sequential
- **Bulk Delete:** All items processed simultaneously
- **PDF Preview:** Instant (via GCS public URLs)

## 🚀 Recent Updates

### November 2025
- ✅ Simplified agent instructions (87% reduction)
- ✅ Fixed profile retrieval workflow
- ✅ Added bulk delete with parallel processing
- ✅ Implemented PDF preview for both pages
- ✅ Increased API timeout to 5 minutes
- ✅ Enhanced security and git hygiene
- ✅ Multi-file upload with progress tracking
- ✅ Knowledge Base manager cloud function
- ✅ GCS storage integration

## 📝 Support

For issues:
1. Check this README
2. Review deployment logs: `gcloud logging read`
3. Check browser console (F12)
4. Verify environment variables
5. Check cloud function logs in GCP Console
6. Review agent logs in Cloud Run

## 📄 License

Part of the GraphRAG multi-agent system.

## 🙏 Acknowledgments

- Google Gemini 2.5 Flash for AI capabilities
- Google Cloud Platform for infrastructure
- Firebase for hosting and authentication
- React and Vite for frontend framework
