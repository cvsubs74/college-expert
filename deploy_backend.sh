#!/bin/bash

# College Counselor - Backend Deployment Script
# Deploys both the agent and cloud function

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="us-east1"
AGENT_SERVICE_NAME="college-counselor-agent"
PROFILE_MANAGER_FUNCTION="profile-manager"
KNOWLEDGE_BASE_FUNCTION="knowledge-base-manager"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Backend Deployment                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if agents/.env file exists
if [ ! -f agents/.env ]; then
    echo -e "${RED}Error: agents/.env file not found${NC}"
    echo -e "${YELLOW}Please create agents/.env file with GEMINI_API_KEY${NC}"
    exit 1
fi

# Load environment variables from agents/.env
echo -e "${YELLOW}Loading configuration from agents/.env...${NC}"
set -a
source agents/.env
set +a

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: GEMINI_API_KEY not set in agents/.env file${NC}"
    exit 1
fi

# Get project ID from gcloud config or use default
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID="college-counselling-478115"
    echo -e "${YELLOW}Using default project: ${PROJECT_ID}${NC}"
fi

echo -e "${GREEN}Using GCP Project: ${PROJECT_ID}${NC}"
echo -e "${GREEN}Region: ${REGION}${NC}"
echo -e "${GREEN}GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}...${NC}"
echo ""

# Set GCP project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID
echo ""

# Deploy Backend Agent
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 1: Deploying Backend Agent to Cloud Run${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd agents
echo -e "${YELLOW}Deploying agent with ADK...${NC}"

# Create .env file for the agent
cat > .env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
DATA_STORE=college_admissions_kb
GOOGLE_GENAI_USE_VERTEXAI=0
EOF

adk deploy cloud_run \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --service_name="$AGENT_SERVICE_NAME" \
    --allow_origins="*" \
    --with_ui \
    .

AGENT_URL=$(gcloud run services describe $AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)')
echo -e "${GREEN}✓ Agent deployed successfully${NC}"
echo -e "${GREEN}  URL: ${AGENT_URL}${NC}"
echo ""

# Set IAM policy to allow public access
echo -e "${YELLOW}Setting IAM policy to allow public access...${NC}"
gcloud run services add-iam-policy-binding "$AGENT_SERVICE_NAME" \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --region="$REGION" \
    --platform=managed
echo -e "${GREEN}✓ IAM policy updated${NC}"
echo ""

cd ..

# Deploy Cloud Function
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 2: Deploying Profile Manager Cloud Function${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd cloud_functions/profile_manager

echo -e "${YELLOW}Deploying Profile Manager cloud function...${NC}"
gcloud functions deploy $PROFILE_MANAGER_FUNCTION \
    --gen2 \
    --runtime=python312 \
    --region=$REGION \
    --source=. \
    --entry-point=profile_manager \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=.env.yaml \
    --timeout=540s \
    --memory=512MB

PROFILE_MANAGER_URL=$(gcloud functions describe $PROFILE_MANAGER_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
echo -e "${GREEN}✓ Profile Manager deployed successfully${NC}"
echo -e "${GREEN}  URL: ${PROFILE_MANAGER_URL}${NC}"
echo ""

cd ../..

# Deploy Knowledge Base Manager Cloud Function
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 3: Deploying Knowledge Base Manager Cloud Function${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

cd cloud_functions/knowledge_base_manager

echo -e "${YELLOW}Deploying Knowledge Base Manager cloud function...${NC}"
gcloud functions deploy $KNOWLEDGE_BASE_FUNCTION \
    --gen2 \
    --runtime=python312 \
    --region=$REGION \
    --source=. \
    --entry-point=knowledge_base_manager \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=.env.yaml \
    --timeout=540s \
    --memory=512MB

KNOWLEDGE_BASE_URL=$(gcloud functions describe $KNOWLEDGE_BASE_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
echo -e "${GREEN}✓ Knowledge Base Manager deployed successfully${NC}"
echo -e "${GREEN}  URL: ${KNOWLEDGE_BASE_URL}${NC}"
echo ""

cd ../..

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Backend Deployment Complete! 🎉               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Deployment Summary:${NC}"
echo -e "  Backend Agent:           ${AGENT_URL}"
echo -e "  Profile Manager:         ${PROFILE_MANAGER_URL}"
echo -e "  Knowledge Base Manager:  ${KNOWLEDGE_BASE_URL}"
echo ""

# Update frontend/.env file with backend URLs
if [ -f frontend/.env ]; then
    echo -e "${YELLOW}Updating frontend/.env with backend URLs...${NC}"
    
    # Update or add URLs in frontend/.env
    sed -i.bak "s|^VITE_API_URL=.*|VITE_API_URL=${AGENT_URL}|" frontend/.env
    sed -i.bak "s|^VITE_PROFILE_MANAGER_URL=.*|VITE_PROFILE_MANAGER_URL=${PROFILE_MANAGER_URL}|" frontend/.env
    sed -i.bak "s|^VITE_KNOWLEDGE_BASE_URL=.*|VITE_KNOWLEDGE_BASE_URL=${KNOWLEDGE_BASE_URL}|" frontend/.env
    
    rm -f frontend/.env.bak
    echo -e "${GREEN}✓ Frontend .env file updated${NC}"
else
    echo -e "${YELLOW}Note: frontend/.env not found. Create it from frontend/.env.example${NC}"
fi

echo ""
echo -e "${GREEN}Next step: Deploy frontend with ./deploy_frontend.sh${NC}"
