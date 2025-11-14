#!/bin/bash

# College Counselor - Complete Deployment Script
# Deploys backend agent, cloud function, and frontend

set -e  # Exit on error

# Make sub-scripts executable
chmod +x deploy_backend.sh deploy_frontend.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"college-counselling-478115"}
REGION="us-east1"
AGENT_SERVICE_NAME="college-counselor-agent"
CLOUD_FUNCTION_NAME="profile-manager"
FRONTEND_SITE_NAME="college-counselor"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Complete Deployment Script        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check and fetch GEMINI_API_KEY if not set
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}GEMINI_API_KEY not set. Attempting to fetch from Secret Manager...${NC}"
    if GEMINI_API_KEY=$(gcloud secrets versions access latest --secret=gemini-api-key --project=$PROJECT_ID 2>/dev/null); then
        echo -e "${GREEN}✓ Successfully fetched GEMINI_API_KEY from Secret Manager${NC}"
        export GEMINI_API_KEY
    else
        echo -e "${RED}Error: Could not fetch GEMINI_API_KEY from Secret Manager${NC}"
        echo -e "${YELLOW}Please run './setup_secrets.sh' to set up the secret first${NC}"
        exit 1
    fi
fi
echo ""

# Check if project ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID environment variable is not set${NC}"
    echo "Please set it with: export GCP_PROJECT_ID='your-project-id'"
    exit 1
fi

echo -e "${GREEN}Using GCP Project: ${PROJECT_ID}${NC}"
echo -e "${GREEN}Region: ${REGION}${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check required tools
echo -e "${YELLOW}Checking required tools...${NC}"
MISSING_TOOLS=()

if ! command_exists gcloud; then
    MISSING_TOOLS+=("gcloud (Google Cloud SDK)")
fi

if ! command_exists adk; then
    MISSING_TOOLS+=("adk (Google ADK)")
fi

if ! command_exists npm; then
    MISSING_TOOLS+=("npm (Node.js)")
fi

if ! command_exists firebase; then
    MISSING_TOOLS+=("firebase (Firebase CLI)")
fi

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    echo -e "${RED}Missing required tools:${NC}"
    for tool in "${MISSING_TOOLS[@]}"; do
        echo -e "  - ${tool}"
    done
    exit 1
fi

echo -e "${GREEN}✓ All required tools are installed${NC}"
echo ""

# Set GCP project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID
echo ""

# Deploy Backend (Agent + Cloud Function)
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 1: Deploying Backend${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Export environment variables for the backend deployment script
export GCP_PROJECT_ID=$PROJECT_ID
export GEMINI_API_KEY=$GEMINI_API_KEY

./deploy_backend.sh

# Extract URLs from backend deployment
AGENT_URL=$(gcloud run services describe $AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
FUNCTION_URL=$(gcloud functions describe $CLOUD_FUNCTION_NAME --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")

if [ -z "$AGENT_URL" ] || [ -z "$FUNCTION_URL" ]; then
    echo -e "${RED}Error: Failed to get backend URLs${NC}"
    exit 1
fi

# Deploy Frontend
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 2: Deploying Frontend${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

export VITE_API_URL=$AGENT_URL
export VITE_PROFILE_MANAGER_URL=$FUNCTION_URL

./deploy_frontend.sh

FRONTEND_URL="https://college-strategy.web.app"

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Deployment Complete! 🎉                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Deployment Summary:${NC}"
echo -e "  Backend Agent:      ${AGENT_URL}"
echo -e "  Cloud Function:     ${FUNCTION_URL}"
echo -e "  Frontend:           ${FRONTEND_URL}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Visit ${FRONTEND_URL}"
echo -e "  2. Upload your student profile in the 'Student Profile' tab"
echo -e "  3. Enter college information in the 'Admissions Analysis' tab"
echo -e "  4. Click 'Analyze' to get your admissions assessment"
echo ""
echo -e "${GREEN}Happy analyzing! 🎓${NC}"
