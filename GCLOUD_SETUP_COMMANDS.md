# GCloud Setup Commands - College Counselor

This document contains all the gcloud commands executed to set up and deploy the College Counselor application.

## Initial Setup

### 1. Set Active Project
```bash
gcloud config set project college-counselling-478115
```

### 2. Verify Project Configuration
```bash
gcloud config get-value project
```

## IAM Permissions Setup

### 3. Grant Cloud Build Permissions
The default Cloud Build service account needed permissions to build and deploy containers.

```bash
# Get the compute service account email
# Format: PROJECT_NUMBER-compute@developer.gserviceaccount.com
# In our case: 808989169388-compute@developer.gserviceaccount.com

# Grant Cloud Build Builder role
gcloud projects add-iam-policy-binding college-counselling-478115 \
    --member="serviceAccount:808989169388-compute@developer.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.builder"

# Grant Storage Object Viewer role
gcloud projects add-iam-policy-binding college-counselling-478115 \
    --member="serviceAccount:808989169388-compute@developer.gserviceaccount.com" \
    --role="roles/storage.objectViewer"
```

## Backend Agent Deployment

### 4. Deploy Agent to Cloud Run (with ADK)
```bash
cd agents

# Deploy using ADK CLI with --with_ui flag to enable /run endpoint
adk deploy cloud_run \
    --project="college-counselling-478115" \
    --region="us-east1" \
    --service_name="college-counselor-agent" \
    --allow_origins="*" \
    --with_ui \
    .
```

**Note:** The `--with_ui` flag is critical - it enables the `/run` endpoint that allows immediate agent execution.

### 5. Set IAM Policy for Public Access
```bash
# Allow unauthenticated access to the Cloud Run service
gcloud run services add-iam-policy-binding college-counselor-agent \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --region="us-east1" \
    --platform=managed
```

### 6. Get Agent Service URL
```bash
gcloud run services describe college-counselor-agent \
    --region=us-east1 \
    --format='value(status.url)'
```

**Result:** `https://college-counselor-agent-808989169388.us-east1.run.app`

### 7. View Agent Logs
```bash
# View recent logs
gcloud run services logs read college-counselor-agent \
    --region=us-east1 \
    --limit=100

# View logs with filtering
gcloud run services logs read college-counselor-agent \
    --region=us-east1 \
    --limit=100 | grep -i "error\|exception"

# Follow logs in real-time
gcloud run services logs tail college-counselor-agent \
    --region=us-east1
```

## Profile Manager Cloud Function Deployment

### 8. Deploy Profile Manager Cloud Function
```bash
cd cloud_functions/profile_manager

# Deploy Gen 2 Cloud Function
gcloud functions deploy profile-manager \
    --gen2 \
    --runtime=python311 \
    --region=us-east1 \
    --source=. \
    --entry-point=main \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=.env.yaml \
    --timeout=540s \
    --memory=512MB
```

### 9. Get Cloud Function URL
```bash
gcloud functions describe profile-manager \
    --region=us-east1 \
    --gen2 \
    --format='value(serviceConfig.uri)'
```

**Result:** `https://profile-manager-pfnwjfp26a-ue.a.run.app`

### 10. View Cloud Function Logs
```bash
# View recent logs
gcloud functions logs read profile-manager \
    --region=us-east1 \
    --gen2 \
    --limit=100

# Follow logs in real-time
gcloud functions logs tail profile-manager \
    --region=us-east1 \
    --gen2
```

## Firebase Hosting Setup

### 11. Add Firebase to GCP Project
```bash
firebase projects:addfirebase college-counselling-478115
```

### 12. Create Firebase Web App
```bash
firebase apps:create WEB "College Counselor"
```

### 13. Create Firebase Hosting Site
```bash
firebase hosting:sites:create college-strategy
```

### 14. Deploy Frontend to Firebase Hosting
```bash
cd frontend

# Build the frontend
npm run build

# Deploy to Firebase Hosting
firebase deploy --only hosting --project college-counselling-478115
```

**Result:** `https://college-strategy.web.app`

### 15. View Firebase Hosting Logs
```bash
# View deployment history
firebase hosting:channel:list --project college-counselling-478115

# View site details
firebase hosting:sites:get college-strategy --project college-counselling-478115
```

## Testing Commands

### 16. Test Backend Agent
```bash
# Create a session
SESSION_ID=$(curl -s -X POST \
    https://college-counselor-agent-808989169388.us-east1.run.app/apps/agents/users/user/sessions \
    -H "Content-Type: application/json" \
    -d '{}' | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

echo "Session ID: $SESSION_ID"

# Send a message using /run endpoint
curl -X POST \
    "https://college-counselor-agent-808989169388.us-east1.run.app/run" \
    -H "Content-Type: application/json" \
    -d "{
        \"app_name\": \"agents\",
        \"user_id\": \"user\",
        \"session_id\": \"$SESSION_ID\",
        \"new_message\": {
            \"parts\": [{\"text\": \"Hello, can you help me with college admissions?\"}]
        },
        \"streaming\": false
    }" | python3 -m json.tool
```

### 17. Test Profile Manager
```bash
# List profiles
curl -s https://profile-manager-pfnwjfp26a-ue.a.run.app/list-profiles | python3 -m json.tool

# Health check
curl -s https://profile-manager-pfnwjfp26a-ue.a.run.app/health | python3 -m json.tool
```

## Monitoring and Debugging

### 18. View Cloud Run Service Details
```bash
gcloud run services describe college-counselor-agent \
    --region=us-east1 \
    --format=yaml
```

### 19. List All Cloud Run Services
```bash
gcloud run services list --region=us-east1
```

### 20. View Cloud Build History
```bash
gcloud builds list --limit=10
```

### 21. View Specific Build Logs
```bash
# Replace BUILD_ID with actual build ID from builds list
gcloud builds log BUILD_ID
```

### 22. Check Cloud Run Revisions
```bash
gcloud run revisions list \
    --service=college-counselor-agent \
    --region=us-east1
```

### 23. View Service Metrics
```bash
# Get service metrics (requires Cloud Monitoring API)
gcloud monitoring time-series list \
    --filter='resource.type="cloud_run_revision" AND resource.labels.service_name="college-counselor-agent"' \
    --format=json
```

## Cleanup Commands (If Needed)

### 24. Delete Cloud Run Service
```bash
gcloud run services delete college-counselor-agent \
    --region=us-east1 \
    --quiet
```

### 25. Delete Cloud Function
```bash
gcloud functions delete profile-manager \
    --region=us-east1 \
    --gen2 \
    --quiet
```

### 26. Delete Firebase Hosting Site
```bash
firebase hosting:sites:delete college-strategy --project college-counselling-478115
```

## Environment Variables

### Backend Agent (.env)
```bash
GOOGLE_GENAI_USE_VERTEXAI=0
GCP_PROJECT_ID=college-counselling-478115
GOOGLE_CLOUD_LOCATION=us-east1
GEMINI_API_KEY=your_gemini_api_key_here
DATA_STORE=college_admissions_kb
```

### Profile Manager (.env.yaml)
```yaml
GEMINI_API_KEY: "your_gemini_api_key_here"
DATA_STORE: "student_profile"
```

### Frontend (.env)
```bash
VITE_API_URL=https://college-counselor-agent-808989169388.us-east1.run.app
VITE_PROFILE_MANAGER_URL=https://profile-manager-pfnwjfp26a-ue.a.run.app
```

## Useful Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# College Counselor aliases
alias cc-logs='gcloud run services logs read college-counselor-agent --region=us-east1 --limit=100'
alias cc-tail='gcloud run services logs tail college-counselor-agent --region=us-east1'
alias cc-status='gcloud run services describe college-counselor-agent --region=us-east1 --format="value(status.url,status.conditions)"'
alias pm-logs='gcloud functions logs read profile-manager --region=us-east1 --gen2 --limit=100'
alias pm-tail='gcloud functions logs tail profile-manager --region=us-east1 --gen2'
```

## Deployment Script

The complete deployment is automated in:
- `deploy.sh` - Main deployment script
- `deploy_backend.sh` - Backend agent deployment
- `deploy_frontend.sh` - Frontend deployment

```bash
# Deploy everything
./deploy.sh

# Or deploy individually
./deploy_backend.sh
./deploy_frontend.sh
```

## Key Learnings

### 1. ADK --with_ui Flag
The `--with_ui` flag is **essential** for chat applications. It enables the `/run` endpoint which:
- Executes the agent immediately
- Returns response events
- Supports non-streaming mode

Without this flag, you can only use PATCH to sessions, which creates events but doesn't execute the agent.

### 2. IAM Permissions
The Cloud Build service account needs:
- `roles/cloudbuild.builds.builder` - To build containers
- `roles/storage.objectViewer` - To access Cloud Storage for source code

### 3. Public Access
For public-facing applications, add IAM policy binding:
```bash
gcloud run services add-iam-policy-binding SERVICE_NAME \
    --member="allUsers" \
    --role="roles/run.invoker"
```

### 4. Firebase Hosting
For new projects, you must:
1. Add Firebase to the GCP project
2. Create a web app
3. Create a hosting site
4. Add `site` property to `firebase.json`

## Troubleshooting Commands

### Check if service is running
```bash
curl -s https://college-counselor-agent-808989169388.us-east1.run.app/health
```

### Check Cloud Run service status
```bash
gcloud run services describe college-counselor-agent \
    --region=us-east1 \
    --format='value(status.conditions[0].status)'
```

### View recent errors
```bash
gcloud run services logs read college-counselor-agent \
    --region=us-east1 \
    --limit=50 | grep -i "error\|exception\|failed"
```

### Check IAM policies
```bash
gcloud run services get-iam-policy college-counselor-agent \
    --region=us-east1
```

## Summary

**Total Services Deployed:**
1. Cloud Run Service (Backend Agent)
2. Cloud Function Gen 2 (Profile Manager)
3. Firebase Hosting (Frontend)

**Total Commands Executed:** ~25 setup and deployment commands

**Deployment Time:** ~10-15 minutes total

**Result:** Fully functional college counseling application with chat, profile management, and admissions analysis capabilities.
