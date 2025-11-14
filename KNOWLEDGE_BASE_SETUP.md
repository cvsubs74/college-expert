# Knowledge Base Management Setup

## Overview

The College Counselor application now has **two separate File Search stores**:

1. **`student_profile_<user_email>`** - User-specific student profiles (private per user)
2. **`college_admissions_kb`** - Shared knowledge base for university research (shared across all users)

## Architecture

### Student Profiles (Private)
- **Store Pattern**: `student_profile_<sanitized_email>` (e.g., `student_profile_john_doe_gmail_com`)
- **Purpose**: Store individual student academic profiles (transcripts, test scores, activities)
- **Access**: Each user can only access their own profile store
- **Management**: Via "Student Profile" page
- **Cloud Function**: `profile-manager` (https://profile-manager-pfnwjfp26a-ue.a.run.app)
- **Used By**: Agent's `search_user_profile` tool for personalized admissions analysis

### Knowledge Base (Shared)
- **Store Name**: `college_admissions_kb`
- **Purpose**: Store university research documents, admissions data, college information
- **Access**: Shared across all users
- **Management**: Via "Knowledge Base" page (NEW!)
- **Cloud Function**: `knowledge-base-manager` (https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app)
- **Used By**: Agent's `search_knowledge_base` tool for answering college-related questions

## Data Flow

### Student Profile Upload & Analysis
```
User → Student Profile Page → profile-manager → student_profile_<email> store
                                                         ↓
Agent Analysis Request → search_user_profile(email) → Retrieves user's profile
                                                         ↓
                                    Personalized admissions analysis
```

### Knowledge Base Upload & Chat
```
User → Knowledge Base Page → knowledge-base-manager → college_admissions_kb store
                                                              ↓
Chat Question → search_knowledge_base(query) → Searches shared knowledge base
                                                              ↓
                                        Answer with citations
```

## Cloud Functions

### Profile Manager
- **Endpoint**: https://profile-manager-pfnwjfp26a-ue.a.run.app
- **Operations**:
  - `POST /upload-profile` - Upload student profile (requires user_email)
  - `GET /list-profiles` - List user's profiles (requires user_email)
  - `DELETE /delete-profile` - Delete profile document
- **Store**: User-specific (`student_profile_<email>`)

### Knowledge Base Manager (NEW!)
- **Endpoint**: https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app
- **Operations**:
  - `POST /upload-document` - Upload university research
  - `GET /list-documents` - List all knowledge base documents
  - `DELETE /delete-document` - Delete knowledge base document
- **Store**: Shared (`college_admissions_kb`)

## Frontend Pages

### Student Profile Page (`/profile`)
- Upload personal academic documents
- View uploaded profiles
- Delete profiles
- **Store**: User-specific profile store

### Knowledge Base Page (`/knowledge-base`) - NEW!
- Upload university research documents
- View all knowledge base documents
- Delete documents
- **Store**: Shared knowledge base store
- **Note**: Documents are shared across all users

### College Info Chat (`/chat`)
- Ask questions about colleges
- Uses `search_knowledge_base` tool
- Searches the shared `college_admissions_kb` store

### Admissions Analysis (`/analysis`)
- Get personalized admissions analysis
- Uses `search_user_profile` tool
- Retrieves from user's `student_profile_<email>` store

## Environment Variables

### Backend Agent (`agents/.env`)
```bash
GEMINI_API_KEY=AIzaSyDtb207RCMvNABwEZGq1mP6SCxcNtl6mfo
GOOGLE_GENAI_USE_VERTEXAI=0  # Use Developer API for File Search
DATA_STORE=college_admissions_kb  # Shared knowledge base store
```

### Profile Manager (`.env.yaml`)
```yaml
GEMINI_API_KEY: "AIzaSyDtb207RCMvNABwEZGq1mP6SCxcNtl6mfo"
DATA_STORE: "student_profile"  # Base name for user-specific stores
```

### Knowledge Base Manager (`.env.yaml`)
```yaml
GEMINI_API_KEY: "AIzaSyDtb207RCMvNABwEZGq1mP6SCxcNtl6mfo"
DATA_STORE: "college_admissions_kb"  # Shared knowledge base store
```

### Frontend (`.env`)
```bash
VITE_API_URL=https://college-counselor-agent-808989169388.us-east1.run.app
VITE_PROFILE_MANAGER_URL=https://profile-manager-pfnwjfp26a-ue.a.run.app
VITE_KNOWLEDGE_BASE_URL=https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app
```

## Deployment

### Deploy Knowledge Base Manager
```bash
cd cloud_functions/knowledge_base_manager
./deploy.sh
```

### Deploy Frontend
```bash
cd frontend
npm run build
firebase deploy --only hosting --project college-counsellor
```

## Usage Guide

### For Students:
1. **Upload Your Profile** → Go to "Student Profile" page
   - Upload your transcript, test scores, activities
   - This is private to you

2. **Ask Questions** → Go to "College Info Chat" page
   - Ask about any college (searches shared knowledge base)
   - Example: "What does USC look for in applicants?"

3. **Get Analysis** → Go to "Admissions Analysis" page
   - Enter target college and major
   - Agent retrieves YOUR profile and provides personalized analysis

### For Administrators:
1. **Add University Research** → Go to "Knowledge Base" page
   - Upload university research documents
   - These become available to all users
   - Documents are used for answering college questions

## Key Points

✅ **Two Separate Stores**: Student profiles (private) vs Knowledge base (shared)
✅ **User Isolation**: Each student's profile is in their own store
✅ **Shared Knowledge**: All users benefit from uploaded university research
✅ **Automatic Retrieval**: Agent automatically finds user's profile for analysis
✅ **Semantic Search**: Both stores use Gemini File Search for intelligent retrieval

## Testing

1. **Upload to Knowledge Base**:
   - Go to https://college-strategy.web.app/knowledge-base
   - Upload a university research document
   - Verify it appears in the list

2. **Test Chat**:
   - Go to https://college-strategy.web.app/chat
   - Ask a question about the uploaded document
   - Verify the agent finds and cites the document

3. **Test Profile Analysis**:
   - Upload your profile at https://college-strategy.web.app/profile
   - Go to https://college-strategy.web.app/analysis
   - Request analysis for a university
   - Verify the agent retrieves and uses YOUR profile

## Troubleshooting

**Q: Chat says it can't find university research I uploaded**
- A: Make sure you uploaded to "Knowledge Base" page, not "Student Profile" page
- Check the Knowledge Base page to verify the document is listed

**Q: Agent asks for my profile even though I uploaded it**
- A: Make sure you uploaded to "Student Profile" page, not "Knowledge Base" page
- Check the Student Profile page to verify your document is listed

**Q: Other users can see my profile**
- A: This shouldn't happen - profiles are user-specific
- Check that you're signed in with the correct account

## URLs

- **Frontend**: https://college-strategy.web.app
- **Agent**: https://college-counselor-agent-808989169388.us-east1.run.app
- **Profile Manager**: https://profile-manager-pfnwjfp26a-ue.a.run.app
- **Knowledge Base Manager**: https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app
