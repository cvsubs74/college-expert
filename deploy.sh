#!/bin/bash

# College Counselor - Modular Deployment Script
# Supports deploying individual components or all at once
#
# Usage:
#   ./deploy.sh                    # Deploy everything
#   ./deploy.sh agent              # Deploy only the agent
#   ./deploy.sh profile            # Deploy only profile manager
#   ./deploy.sh knowledge          # Deploy only knowledge base manager
#   ./deploy.sh functions          # Deploy all cloud functions
#   ./deploy.sh backend            # Deploy agent + all functions
#   ./deploy.sh frontend           # Deploy only frontend

set -e  # Exit on error

# Make sub-scripts executable
chmod +x deploy_backend.sh deploy_frontend.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"college-counselling-478115"}
REGION="us-east1"
AGENT_SERVICE_NAME="college-counselor-agent"
PROFILE_MANAGER_FUNCTION="profile-manager"
KNOWLEDGE_BASE_FUNCTION="knowledge-base-manager"
FRONTEND_SITE_NAME="college-counselor"

# Parse command line arguments
DEPLOY_TARGET="${1:-all}"

# Show usage if help requested
if [ "$DEPLOY_TARGET" == "--help" ] || [ "$DEPLOY_TARGET" == "-h" ]; then
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     College Counselor - Deployment Script Help            ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Usage:${NC}"
    echo -e "  ./deploy.sh [target]"
    echo ""
    echo -e "${GREEN}Targets:${NC}"
    echo -e "  ${YELLOW}all${NC}         - Deploy everything (agent + functions + frontend)"
    echo -e "  ${YELLOW}agent${NC}       - Deploy only the backend agent"
    echo -e "  ${YELLOW}profile${NC}     - Deploy only profile manager function"
    echo -e "  ${YELLOW}knowledge${NC}   - Deploy only knowledge base manager function"
    echo -e "  ${YELLOW}functions${NC}   - Deploy all cloud functions (profile + knowledge)"
    echo -e "  ${YELLOW}backend${NC}     - Deploy agent + all functions"
    echo -e "  ${YELLOW}frontend${NC}    - Deploy only frontend"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo -e "  ./deploy.sh              # Deploy everything"
    echo -e "  ./deploy.sh agent        # Deploy only agent"
    echo -e "  ./deploy.sh knowledge    # Deploy only knowledge base manager"
    echo ""
    exit 0
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Deployment Script                 ║${NC}"
echo -e "${BLUE}║     Target: ${DEPLOY_TARGET}${NC}"
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

# Deployment Functions
deploy_agent() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Backend Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd agents
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
    
    gcloud run services add-iam-policy-binding "$AGENT_SERVICE_NAME" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    AGENT_URL=$(gcloud run services describe $AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ Agent deployed: ${AGENT_URL}${NC}"
    cd ..
}

deploy_profile_manager() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Profile Manager Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd cloud_functions/profile_manager
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
    echo -e "${GREEN}✓ Profile Manager deployed: ${PROFILE_MANAGER_URL}${NC}"
    cd ../..
}

deploy_knowledge_base_manager() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Knowledge Base Manager Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd cloud_functions/knowledge_base_manager
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
    echo -e "${GREEN}✓ Knowledge Base Manager deployed: ${KNOWLEDGE_BASE_URL}${NC}"
    cd ../..
}

deploy_frontend() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Frontend${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Get backend URLs
    AGENT_URL=$(gcloud run services describe $AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
    PROFILE_MANAGER_URL=$(gcloud functions describe $PROFILE_MANAGER_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    KNOWLEDGE_BASE_URL=$(gcloud functions describe $KNOWLEDGE_BASE_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    
    export VITE_API_URL=$AGENT_URL
    export VITE_PROFILE_MANAGER_URL=$PROFILE_MANAGER_URL
    export VITE_KNOWLEDGE_BASE_URL=$KNOWLEDGE_BASE_URL
    
    # Firebase Configuration
    export VITE_FIREBASE_API_KEY="AIzaSyB21YdLOZTjO1przhjsX1Es64-kFGov5XE"
    export VITE_FIREBASE_AUTH_DOMAIN="college-counsellor.firebaseapp.com"
    export VITE_FIREBASE_PROJECT_ID="college-counsellor"
    export VITE_FIREBASE_STORAGE_BUCKET="college-counsellor.firebasestorage.app"
    export VITE_FIREBASE_MESSAGING_SENDER_ID="1098097030863"
    export VITE_FIREBASE_APP_ID="1:1098097030863:web:6e7d2d9e7f1f7b7f7f7f7f"
    
    ./deploy_frontend.sh
    echo -e "${GREEN}✓ Frontend deployed: https://college-strategy.web.app${NC}"
}

# Execute deployment based on target
case "$DEPLOY_TARGET" in
    "agent")
        deploy_agent
        ;;
    "profile")
        deploy_profile_manager
        ;;
    "knowledge")
        deploy_knowledge_base_manager
        ;;
    "functions")
        deploy_profile_manager
        deploy_knowledge_base_manager
        ;;
    "backend")
        deploy_agent
        deploy_profile_manager
        deploy_knowledge_base_manager
        ;;
    "frontend")
        deploy_frontend
        ;;
    "all")
        deploy_agent
        deploy_profile_manager
        deploy_knowledge_base_manager
        deploy_frontend
        ;;
    *)
        echo -e "${RED}Error: Unknown deployment target '${DEPLOY_TARGET}'${NC}"
        echo -e "${YELLOW}Run './deploy.sh --help' for usage information${NC}"
        exit 1
        ;;
esac

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Deployment Complete! 🎉                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Deployed: ${DEPLOY_TARGET}${NC}"
echo ""
