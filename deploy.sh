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
chmod +x deploy_frontend.sh

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
RAG_AGENT_SERVICE_NAME="college-expert-rag-agent"
ES_AGENT_SERVICE_NAME="college-expert-es-agent"
HYBRID_AGENT_SERVICE_NAME="college-expert-hybrid-agent"
PROFILE_MANAGER_FUNCTION="profile-manager"
PROFILE_MANAGER_ES_FUNCTION="profile-manager-es"
KNOWLEDGE_BASE_FUNCTION="knowledge-base-manager"
KNOWLEDGE_BASE_ES_FUNCTION="knowledge-base-manager-es"
KNOWLEDGE_BASE_UNIVERSITIES_FUNCTION="knowledge-base-manager-universities"
PAYMENT_MANAGER_FUNCTION="payment-manager"
UNIVERSITY_COLLECTOR_SERVICE_NAME="university-profile-collector"
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
    echo -e "${GREEN}Dynamic Approach Selection:${NC}"
    echo -e "  The agent now supports dynamic approach selection via the UI."
    echo -e "  All cloud functions (RAG, Elasticsearch) should be deployed."
    echo -e "  Users can switch between approaches without redeployment."
    echo ""
    echo -e "${GREEN}Targets:${NC}"
    echo -e "  ${YELLOW}all${NC}         - Deploy everything (both agents + all functions + frontend)"
    echo -e "  ${YELLOW}agent-rag${NC}   - Deploy RAG-based college expert agent"
    echo -e "  ${YELLOW}agent-es${NC}    - Deploy Elasticsearch-based college expert agent"
    echo -e "  ${YELLOW}agent-hybrid${NC} - Deploy Hybrid college expert agent (uses universities KB)"
    echo -e "  ${YELLOW}agents${NC}      - Deploy all agents (recommended)"
    echo -e "  ${YELLOW}profile-rag${NC}  - Deploy RAG profile manager function"
    echo -e "  ${YELLOW}profile-es${NC}  - Deploy Elasticsearch profile manager function"
    echo -e "  ${YELLOW}profile-v2${NC}  - Deploy Firestore V2 profile manager function (RECOMMENDED)"
    echo -e "  ${YELLOW}knowledge-rag${NC} - Deploy RAG knowledge base function"
    echo -e "  ${YELLOW}knowledge-es${NC} - Deploy Elasticsearch knowledge base function"
    echo -e "  ${YELLOW}knowledge-universities${NC} - Deploy Universities knowledge base function"
    echo -e "  ${YELLOW}knowledge-universities-v2${NC} - Deploy Universities KB V2 (Firestore, no ES)"
    echo -e "  ${YELLOW}payment${NC}     - Deploy Payment manager function (Stripe integration)"
    echo -e "  ${YELLOW}source-curator${NC} - Deploy Source Curator UI (React + FastAPI)"
    echo -e "  ${YELLOW}functions${NC}   - Deploy all cloud functions (recommended)"
    echo -e "  ${YELLOW}backend${NC}     - Deploy both agents + all functions (recommended)"
    echo -e "  ${YELLOW}frontend${NC}    - Deploy only frontend"
    echo ""
    echo -e "${GREEN}Examples:${NC}"
    echo -e "  ./deploy.sh                    # Deploy everything (both agents)"
    echo -e "  ./deploy.sh agents             # Deploy both agents"
    echo -e "  ./deploy.sh agent-rag          # Deploy only RAG agent"
    echo -e "  ./deploy.sh agent-es           # Deploy only ES agent"
    echo -e "  ./deploy.sh source-curator     # Deploy Source Curator UI"
    echo -e "  ./deploy.sh backend            # Deploy both agents + all cloud functions"
    echo ""
    exit 0
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Deployment Script                 ║${NC}"
echo -e "${BLUE}║     Target: ${DEPLOY_TARGET}${NC}"
echo -e "${BLUE}║     Dynamic Routing: All approaches supported              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Always fetch GEMINI_API_KEY from Secret Manager (overwrite any existing value)
echo -e "${YELLOW}Fetching GEMINI_API_KEY from Secret Manager...${NC}"
if GEMINI_API_KEY=$(gcloud secrets versions access latest --secret=gemini-api-key --project=$PROJECT_ID 2>/dev/null); then
    echo -e "${GREEN}✓ Successfully fetched GEMINI_API_KEY from Secret Manager${NC}"
    export GEMINI_API_KEY
else
    echo -e "${RED}Error: Could not fetch GEMINI_API_KEY from Secret Manager${NC}"
    echo -e "${YELLOW}Please run './setup_secrets.sh' to set up the secret first${NC}"
    exit 1
fi

# Always fetch Elasticsearch credentials from Secret Manager (needed for ES cloud functions)
echo -e "${YELLOW}Fetching ES_CLOUD_ID from Secret Manager...${NC}"
if ES_CLOUD_ID=$(gcloud secrets versions access latest --secret=es-cloud-id --project=$PROJECT_ID 2>/dev/null); then
    echo -e "${GREEN}✓ Successfully fetched ES_CLOUD_ID from Secret Manager${NC}"
    export ES_CLOUD_ID
else
    echo -e "${YELLOW}⚠ Could not fetch ES_CLOUD_ID (ES functions will be skipped)${NC}"
fi

echo -e "${YELLOW}Fetching ES_API_KEY from Secret Manager...${NC}"
if ES_API_KEY=$(gcloud secrets versions access latest --secret=es-api-key --project=$PROJECT_ID 2>/dev/null); then
    echo -e "${GREEN}✓ Successfully fetched ES_API_KEY from Secret Manager${NC}"
    export ES_API_KEY
else
    echo -e "${YELLOW}⚠ Could not fetch ES_API_KEY (ES functions will be skipped)${NC}"
fi

# Set default index name if not set
if [ -z "$ES_INDEX_NAME" ]; then
    export ES_INDEX_NAME="university_documents"
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
deploy_agent_rag() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying RAG Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Set up environment for RAG agent
    cd agents/college_expert_rag
    cat > .env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
KNOWLEDGE_BASE_MANAGER_RAG_URL=https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app
PROFILE_MANAGER_RAG_URL=https://profile-manager-pfnwjfp26a-ue.a.run.app
GOOGLE_GENAI_USE_VERTEXAI=0
EOF
    cd ../..
    
    # Deploy RAG agent from root directory, passing the agent path
    adk deploy cloud_run \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --service_name="$RAG_AGENT_SERVICE_NAME" \
        --allow_origins="*" \
        --with_ui \
        agents/college_expert_rag
    
    gcloud run services add-iam-policy-binding "$RAG_AGENT_SERVICE_NAME" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    RAG_AGENT_URL=$(gcloud run services describe $RAG_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ RAG Agent deployed: ${RAG_AGENT_URL}${NC}"
}

deploy_agent_es() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying ES Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check for Elasticsearch credentials
    if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
        echo -e "${RED}Error: Elasticsearch credentials not set${NC}"
        echo -e "${YELLOW}Please set:${NC}"
        echo -e "  export ES_CLOUD_ID='your-elastic-cloud-id'"
        echo -e "  export ES_API_KEY='your-elastic-api-key'"
        exit 1
    fi
    
    # Set up environment for ES agent
    cd agents/college_expert_es
    cat > .env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
KNOWLEDGE_BASE_MANAGER_ES_URL=https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app
PROFILE_MANAGER_ES_URL=https://profile-manager-es-pfnwjfp26a-ue.a.run.app
ES_CLOUD_ID=${ES_CLOUD_ID}
ES_API_KEY=${ES_API_KEY}
ES_INDEX_NAME=university_documents
GOOGLE_GENAI_USE_VERTEXAI=0
EOF
    cd ../..
    
    # Deploy ES agent from root directory, passing the agent path
    adk deploy cloud_run \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --service_name="$ES_AGENT_SERVICE_NAME" \
        --allow_origins="*" \
        --with_ui \
        agents/college_expert_es
    
    gcloud run services add-iam-policy-binding "$ES_AGENT_SERVICE_NAME" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    ES_AGENT_URL=$(gcloud run services describe $ES_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ ES Agent deployed: ${ES_AGENT_URL}${NC}"
}

deploy_agent_hybrid() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Hybrid Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Set up environment for Hybrid agent
    cd agents/college_expert_hybrid
    cat > .env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
KNOWLEDGE_BASE_UNIVERSITIES_URL=https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app
PROFILE_MANAGER_ES_URL=https://profile-manager-es-pfnwjfp26a-ue.a.run.app
GOOGLE_GENAI_USE_VERTEXAI=0
EOF
    cd ../..
    
    # Deploy Hybrid agent from root directory, passing the agent path
    adk deploy cloud_run \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --service_name="$HYBRID_AGENT_SERVICE_NAME" \
        --allow_origins="*" \
        --with_ui \
        agents/college_expert_hybrid
    
    gcloud run services add-iam-policy-binding "$HYBRID_AGENT_SERVICE_NAME" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    HYBRID_AGENT_URL=$(gcloud run services describe $HYBRID_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ Hybrid Agent deployed: ${HYBRID_AGENT_URL}${NC}"
    
    # Set min-instances to prevent cold starts
    echo -e "${YELLOW}Setting min-instances=1 for Hybrid Agent...${NC}"
    gcloud run services update $HYBRID_AGENT_SERVICE_NAME \
        --region=$REGION \
        --min-instances=1
    echo -e "${GREEN}✓ Hybrid Agent min-instances set to 1${NC}"
}

deploy_agents() {
    echo -e "${CYAN}Deploying all agents (RAG, ES, Hybrid)...${NC}"
    deploy_agent_rag
    deploy_agent_es
    deploy_agent_hybrid
}

deploy_profile_manager_rag() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Profile Manager RAG Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${YELLOW}Deploying RAG profile manager...${NC}"
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
    echo -e "${GREEN}✓ Profile Manager RAG deployed: ${PROFILE_MANAGER_URL}${NC}"
    cd ../..
}

deploy_profile_manager_es() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Profile Manager ES Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check for Elasticsearch credentials
    if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
        echo -e "${RED}Error: Elasticsearch credentials not set${NC}"
        echo -e "${YELLOW}Please set:${NC}"
        echo -e "  export ES_CLOUD_ID='your-elastic-cloud-id'"
        echo -e "  export ES_API_KEY='your-elastic-api-key'"
        exit 1
    fi
    
    cd cloud_functions/profile_manager_es
    gcloud functions deploy $PROFILE_MANAGER_ES_FUNCTION \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=profile_manager_es_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.yaml \
        --timeout=540s \
        --memory=1024MB \
        --min-instances=1 \
        --max-instances=10
    
    PROFILE_MANAGER_ES_URL=$(gcloud functions describe $PROFILE_MANAGER_ES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Profile Manager ES deployed: ${PROFILE_MANAGER_ES_URL}${NC}"
    cd ../..
}

deploy_profile_manager_v2() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Profile Manager V2 Function (Firestore)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${YELLOW}Deploying Profile Manager V2 (Firestore)...${NC}"
    
    cd cloud_functions/profile_manager_v2
    
    # Create deploy-time env.yaml with substituted values
    cat > env.deploy.yaml <<EOF
GCP_PROJECT_ID: ${PROJECT_ID}
REGION: ${REGION}
GCS_BUCKET_NAME: college-counselling-478115-student-profiles
GEMINI_API_KEY: ${GEMINI_API_KEY}
FIRESTORE_DATABASE: "(default)"
KNOWLEDGE_BASE_UNIVERSITIES_URL: "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
LOG_EXECUTION_ID: "true"
EOF
    
    gcloud functions deploy profile-manager-v2 \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=profile_manager_v2_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.deploy.yaml \
        --timeout=540s \
        --memory=1024MB \
        --cpu=1 \
        --min-instances=1 \
        --max-instances=10
    
    PROFILE_MANAGER_V2_URL=$(gcloud functions describe profile-manager-v2 --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Profile Manager V2 deployed: ${PROFILE_MANAGER_V2_URL}${NC}"
    
    # Clean up deploy-time env file
    rm -f env.deploy.yaml
    
    cd ../..
}

deploy_knowledge_base_manager_rag() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Knowledge Base Manager RAG Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    echo -e "${YELLOW}Deploying RAG knowledge base manager...${NC}"
    cd cloud_functions/knowledge_base_manager
    gcloud functions deploy $KNOWLEDGE_BASE_FUNCTION \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=knowledge_base_manager_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=.env.yaml \
        --timeout=540s \
        --memory=512MB
    
    KNOWLEDGE_BASE_URL=$(gcloud functions describe $KNOWLEDGE_BASE_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Knowledge Base Manager RAG deployed: ${KNOWLEDGE_BASE_URL}${NC}"
    cd ../..
}

deploy_knowledge_base_manager_es() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Knowledge Base Manager ES Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check for Elasticsearch credentials
    if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
        echo -e "${RED}Error: Elasticsearch credentials not set${NC}"
        echo -e "${YELLOW}Please set:${NC}"
        echo -e "  export ES_CLOUD_ID='your-elastic-cloud-id'"
        echo -e "  export ES_API_KEY='your-elastic-api-key'"
        exit 1
    fi
    
    cd cloud_functions/knowledge_base_manager_es
    gcloud functions deploy $KNOWLEDGE_BASE_ES_FUNCTION \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=knowledge_base_manager_es_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.yaml \
        --timeout=540s \
        --memory=1024MB \
        --max-instances=10
    
    KNOWLEDGE_BASE_ES_URL=$(gcloud functions describe $KNOWLEDGE_BASE_ES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Knowledge Base Manager ES deployed: ${KNOWLEDGE_BASE_ES_URL}${NC}"
    cd ../..
}

deploy_knowledge_base_manager_vertexai() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Knowledge Base Manager Vertex AI Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd cloud_functions/knowledge_base_manager_vertexai
    gcloud functions deploy knowledge-base-manager-vertexai \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=knowledge_base_manager_vertexai_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.yaml \
        --timeout=540s \
        --memory=1024MB \
        --max-instances=10
    
    KNOWLEDGE_BASE_VERTEXAI_URL=$(gcloud functions describe knowledge-base-manager-vertexai --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Knowledge Base Manager Vertex AI deployed: ${KNOWLEDGE_BASE_VERTEXAI_URL}${NC}"
    cd ../..
}

deploy_knowledge_base_manager_universities() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Knowledge Base Manager Universities Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check for Elasticsearch credentials
    if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
        echo -e "${RED}Error: Elasticsearch credentials not set${NC}"
        echo -e "${YELLOW}Please set:${NC}"
        echo -e "  export ES_CLOUD_ID='your-elastic-cloud-id'"
        echo -e "  export ES_API_KEY='your-elastic-api-key'"
        exit 1
    fi
    
    cd cloud_functions/knowledge_base_manager_universities
    gcloud functions deploy $KNOWLEDGE_BASE_UNIVERSITIES_FUNCTION \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=. \
        --entry-point=knowledge_base_manager_universities_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.yaml \
        --timeout=300s \
        --memory=512MB \
        --min-instances=1 \
        --max-instances=10
    
    KNOWLEDGE_BASE_UNIVERSITIES_URL=$(gcloud functions describe $KNOWLEDGE_BASE_UNIVERSITIES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Knowledge Base Manager Universities deployed: ${KNOWLEDGE_BASE_UNIVERSITIES_URL}${NC}"
    cd ../..
}

deploy_knowledge_base_manager_universities_v2() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Knowledge Base Manager Universities V2 (Firestore)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd cloud_functions/knowledge_base_manager_universities_v2
    
    # Create env.deploy.yaml with secrets
    cat > env.deploy.yaml << EOF
GEMINI_API_KEY: ${GEMINI_API_KEY}
FIRESTORE_COLLECTION: universities
EOF
    
    gcloud functions deploy knowledge-base-manager-universities-v2 \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=. \
        --entry-point=knowledge_base_manager_universities_v2_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.deploy.yaml \
        --timeout=300s \
        --memory=512MB \
        --min-instances=0 \
        --max-instances=10
    
    KNOWLEDGE_BASE_UNIVERSITIES_V2_URL=$(gcloud functions describe knowledge-base-manager-universities-v2 --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Knowledge Base Manager Universities V2 deployed: ${KNOWLEDGE_BASE_UNIVERSITIES_V2_URL}${NC}"
    
    # Cleanup temp env file
    rm -f env.deploy.yaml
    cd ../..
}

deploy_profile_manager_vertexai() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Profile Manager Vertex AI Function${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd cloud_functions/profile_manager_vertexai
    gcloud functions deploy profile-manager-vertexai \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=profile_manager_vertexai_http_entry \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.yaml \
        --timeout=540s \
        --memory=1024MB \
        --max-instances=10
    
    PROFILE_MANAGER_VERTEXAI_URL=$(gcloud functions describe profile-manager-vertexai --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Profile Manager Vertex AI deployed: ${PROFILE_MANAGER_VERTEXAI_URL}${NC}"
    cd ../..
}

deploy_payment_manager() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Payment Manager Function (Stripe)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Check for Stripe credentials from Secret Manager
    STRIPE_SECRET_KEY=$(gcloud secrets versions access latest --secret=stripe-secret-key --project=$PROJECT_ID 2>/dev/null || echo "")
    STRIPE_WEBHOOK_SECRET=$(gcloud secrets versions access latest --secret=stripe-webhook-secret --project=$PROJECT_ID 2>/dev/null || echo "")
    
    if [ -z "$STRIPE_SECRET_KEY" ]; then
        echo -e "${YELLOW}⚠ Stripe credentials not found in Secret Manager${NC}"
        echo -e "${YELLOW}  Using placeholder - payments will not work until configured${NC}"
        echo -e "${YELLOW}  To configure, run:${NC}"
        echo -e "    gcloud secrets create stripe-secret-key --project=$PROJECT_ID"
        echo -e "    echo -n 'sk_test_YOUR_KEY' | gcloud secrets versions add stripe-secret-key --data-file=-"
        STRIPE_SECRET_KEY="sk_test_placeholder"
    fi
    
    cd cloud_functions/payment_manager
    
    # Create deploy-time env.yaml with substituted values (from persistent env.yaml template)
    cp env.yaml env.deploy.yaml
    sed -i.bak \
        -e "s|\${STRIPE_SECRET_KEY}|${STRIPE_SECRET_KEY}|g" \
        -e "s|\${STRIPE_WEBHOOK_SECRET}|${STRIPE_WEBHOOK_SECRET}|g" \
        -e "s|\${ES_API_KEY}|${ES_API_KEY}|g" \
        -e "s|\${ES_CLOUD_ID}|${ES_CLOUD_ID}|g" \
        env.deploy.yaml
    rm -f env.deploy.yaml.bak
    
    gcloud functions deploy $PAYMENT_MANAGER_FUNCTION \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=payment_manager \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.deploy.yaml \
        --timeout=60s \
        --memory=256MB \
        --max-instances=10
    
    PAYMENT_MANAGER_URL=$(gcloud functions describe $PAYMENT_MANAGER_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Payment Manager deployed: ${PAYMENT_MANAGER_URL}${NC}"
    
    # Clean up deploy-time env file (contains secrets)
    rm -f env.deploy.yaml
    
    cd ../..
}

deploy_contact_form() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Contact Form Function (SMTP Email)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    cd cloud_functions/contact_form
    
    gcloud functions deploy contact-form \
        --gen2 \
        --runtime=python312 \
        --region=$REGION \
        --source=. \
        --entry-point=send_contact_email \
        --trigger-http \
        --allow-unauthenticated \
        --timeout=30s \
        --memory=256MB \
        --max-instances=5
    
    CONTACT_FORM_URL=$(gcloud functions describe contact-form --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ Contact Form deployed: ${CONTACT_FORM_URL}${NC}"
    
    cd ../..
}

deploy_agent_adk() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying ADK Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Set up environment for ADK agent
    cd agents/college_expert_adk
    cat > .env <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
GCP_PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
GOOGLE_GENAI_USE_VERTEXAI=0
EOF
    cd ../..
    
    # Deploy ADK agent from root directory, passing the agent path
    # Note: The base image error is expected and can be ignored - the agent still deploys
    adk deploy cloud_run \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --service_name="college-expert-adk-agent" \
        --allow_origins="*" \
        --with_ui \
        agents/college_expert_adk || true
    
    gcloud run services add-iam-policy-binding "college-expert-adk-agent" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    ADK_AGENT_URL=$(gcloud run services describe college-expert-adk-agent --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ ADK Agent deployed: ${ADK_AGENT_URL}${NC}"
}

deploy_university_collector() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying University Profile Collector Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Set up environment for University Collector agent
    cd agents/university_profile_collector
    cat > .env <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
GOOGLE_GENAI_USE_VERTEXAI=0
EOF
    cd ../..
    
    # Deploy University Collector agent
    adk deploy cloud_run \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --service_name="$UNIVERSITY_COLLECTOR_SERVICE_NAME" \
        --allow_origins="*" \
        --with_ui \
        agents/university_profile_collector || true
    
    gcloud run services add-iam-policy-binding "$UNIVERSITY_COLLECTOR_SERVICE_NAME" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    UNIVERSITY_COLLECTOR_URL=$(gcloud run services describe $UNIVERSITY_COLLECTOR_SERVICE_NAME --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ University Profile Collector deployed: ${UNIVERSITY_COLLECTOR_URL}${NC}"
}

deploy_datamine() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Data Discovery Agent${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    DATAMINE_SERVICE="data-discovery-agent"
    
    # Set up environment for DataMine agent
    cd agents/sourcery
    cat > .env <<EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
GOOGLE_GENAI_USE_VERTEXAI=0
EOF
    cd ../..
    
    # Deploy DataMine agent
    adk deploy cloud_run \
        --project="$PROJECT_ID" \
        --region="$REGION" \
        --service_name="$DATAMINE_SERVICE" \
        --allow_origins="*" \
        --with_ui \
        agents/sourcery || true
    
    gcloud run services add-iam-policy-binding "$DATAMINE_SERVICE" \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region="$REGION" \
        --platform=managed
    
    DATAMINE_URL=$(gcloud run services describe $DATAMINE_SERVICE --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ Data Discovery Agent deployed: ${DATAMINE_URL}${NC}"
    
    # Export URL for frontend deployment
    export DATAMINE_AGENT_URL=$DATAMINE_URL
}

deploy_sourcery_frontend() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Sourcery Frontend to Firebase${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Get agent URL if not already set
    if [ -z "$DATAMINE_AGENT_URL" ]; then
        DATAMINE_AGENT_URL=$(gcloud run services describe data-discovery-agent --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
    fi
    
    if [ -z "$DATAMINE_AGENT_URL" ]; then
        echo -e "${YELLOW}⚠ Agent URL not found. Deploy the agent first with: ./deploy.sh datamine${NC}"
        echo -e "${YELLOW}  Using placeholder URL for now${NC}"
        DATAMINE_AGENT_URL="https://data-discovery-agent-pfnwjfp26a-ue.a.run.app"
    fi
    
    echo -e "${GREEN}Using Agent URL: ${DATAMINE_AGENT_URL}${NC}"
    
    cd agents/sourcery/ui
    
    # Create .env with agent URL
    cat > .env <<EOF
VITE_AGENT_URL=${DATAMINE_AGENT_URL}
EOF
    
    # Build the frontend
    echo -e "${YELLOW}Installing dependencies...${NC}"
    npm install --silent
    
    echo -e "${YELLOW}Building frontend...${NC}"
    npm run build
    
    # Deploy to Firebase
    echo -e "${YELLOW}Deploying to Firebase...${NC}"
    firebase deploy --only hosting --project sourcery-data-app
    
    cd ../../..
    
    echo -e "${GREEN}✓ Sourcery Frontend deployed to Firebase${NC}"
    echo -e "${GREEN}  Open: https://sourcery-data-app.web.app${NC}"
}

deploy_uniminer() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying UniMiner (Cloud Function + UI)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    UNIMINER_FUNCTION="uniminer"
    
    # Get university collector agent URL
    UNIVERSITY_COLLECTOR_URL=$(gcloud run services describe university-profile-collector --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
    if [ -z "$UNIVERSITY_COLLECTOR_URL" ]; then
        echo -e "${YELLOW}⚠ University Profile Collector not deployed. Deploy it first with: ./deploy.sh university-collector${NC}"
        UNIVERSITY_COLLECTOR_URL="https://university-profile-collector-pfnwjfp26a-ue.a.run.app"
    fi
    echo -e "${GREEN}Using University Collector: ${UNIVERSITY_COLLECTOR_URL}${NC}"
    
    # Deploy cloud function from agents/uniminer/cloud_function
    echo -e "${YELLOW}Deploying UniMiner cloud function...${NC}"
    cd agents/uniminer/cloud_function
    
    # Create deploy-time env.yaml with substituted values
    cat > env.deploy.yaml <<EOF
ES_CLOUD_ID: "${ES_CLOUD_ID}"
ES_API_KEY: "${ES_API_KEY}"
COLLEGE_SCORECARD_API_KEY: "${DATA_GOV_API_KEY:-}"
KNOWLEDGE_BASE_UNIVERSITIES_URL: "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
EOF
    
    gcloud functions deploy $UNIMINER_FUNCTION \
        --gen2 \
        --runtime=python311 \
        --region=$REGION \
        --source=. \
        --entry-point=uniminer \
        --trigger-http \
        --allow-unauthenticated \
        --env-vars-file=env.deploy.yaml \
        --timeout=300s \
        --memory=512MB \
        --max-instances=10
    
    UNIMINER_FUNCTION_URL=$(gcloud functions describe $UNIMINER_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)')
    echo -e "${GREEN}✓ UniMiner cloud function deployed: ${UNIMINER_FUNCTION_URL}${NC}"
    
    # Clean up deploy-time env file
    rm -f env.deploy.yaml
    cd ../../..
    
    # Deploy UI to Firebase
    echo -e "${YELLOW}Building UniMiner UI...${NC}"
    cd agents/uniminer/ui
    
    # Create .env with API URLs (cloud function + agent)
    cat > .env <<EOF
VITE_API_URL=${UNIMINER_FUNCTION_URL}
VITE_RESEARCH_AGENT_URL=${UNIVERSITY_COLLECTOR_URL}
EOF
    
    npm install --silent
    npm run build
    
    echo -e "${YELLOW}Deploying UniMiner UI to Firebase...${NC}"
    firebase deploy --only hosting
    
    cd ../../..
    
    echo -e "${GREEN}✓ UniMiner deployed!${NC}"
    echo -e "${GREEN}  Cloud Function: ${UNIMINER_FUNCTION_URL}${NC}"
    echo -e "${GREEN}  Research Agent: ${UNIVERSITY_COLLECTOR_URL}${NC}"
    echo -e "${GREEN}  UI: https://uniminer.web.app${NC}"
}

deploy_source_curator() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Source Curator (FastAPI + React UI)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    SOURCE_CURATOR_SERVICE="source-curator"
    
    # Fetch DATA_GOV_API_KEY from Secret Manager (for College Scorecard API)
    echo -e "${YELLOW}Fetching DATA_GOV_API_KEY from Secret Manager...${NC}"
    DATA_GOV_API_KEY=$(gcloud secrets versions access latest --secret=data-gov-api-key --project=$PROJECT_ID 2>/dev/null || echo "")
    if [ -z "$DATA_GOV_API_KEY" ]; then
        echo -e "${YELLOW}⚠ DATA_GOV_API_KEY not found - College Scorecard API may not work${NC}"
    fi
    
    # Build React frontend locally
    echo -e "${YELLOW}Building React frontend...${NC}"
    cd agents/source_curator/source-curator-ui
    npm install --silent
    npm run build
    
    # Move built files to static directory
    rm -rf ../static
    mv dist ../static
    cd ../../..
    
    # Deploy to Cloud Run
    echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
    cd agents/source_curator
    
    gcloud run deploy $SOURCE_CURATOR_SERVICE \
        --source=. \
        --project=$PROJECT_ID \
        --region=$REGION \
        --allow-unauthenticated \
        --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY},DATA_GOV_API_KEY=${DATA_GOV_API_KEY}" \
        --timeout=300 \
        --memory=2Gi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=3
    
    cd ../..
    
    SOURCE_CURATOR_URL=$(gcloud run services describe $SOURCE_CURATOR_SERVICE --region=$REGION --format='value(status.url)')
    echo -e "${GREEN}✓ Source Curator deployed: ${SOURCE_CURATOR_URL}${NC}"
    echo -e "${GREEN}  Open in browser: ${SOURCE_CURATOR_URL}${NC}"
}

deploy_frontend() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Deploying Frontend${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Get backend URLs
    RAG_AGENT_URL=$(gcloud run services describe $RAG_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
    ES_AGENT_URL=$(gcloud run services describe $ES_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
    PROFILE_MANAGER_URL=$(gcloud functions describe $PROFILE_MANAGER_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    PROFILE_MANAGER_ES_URL=$(gcloud functions describe $PROFILE_MANAGER_ES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    PROFILE_MANAGER_V2_URL=$(gcloud functions describe profile-manager-v2 --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "https://profile-manager-v2-pfnwjfp26a-ue.a.run.app")
    
    # Get all knowledge base URLs for dynamic switching
    KNOWLEDGE_BASE_URL=$(gcloud functions describe $KNOWLEDGE_BASE_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    KNOWLEDGE_BASE_ES_URL=$(gcloud functions describe $KNOWLEDGE_BASE_ES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
    
    export VITE_RAG_AGENT_URL=$RAG_AGENT_URL
    export VITE_ES_AGENT_URL=$ES_AGENT_URL
    export VITE_PROFILE_MANAGER_URL=$PROFILE_MANAGER_URL
    export VITE_PROFILE_MANAGER_ES_URL=$PROFILE_MANAGER_ES_URL
    export VITE_PROFILE_MANAGER_V2_URL=$PROFILE_MANAGER_V2_URL
    export VITE_KNOWLEDGE_BASE_URL=$KNOWLEDGE_BASE_URL
    export VITE_KNOWLEDGE_BASE_ES_URL=$KNOWLEDGE_BASE_ES_URL
    
    echo -e "${GREEN}✓ URLs configured:${NC}"
    echo -e "  RAG Agent URL: ${RAG_AGENT_URL}"
    echo -e "  ES Agent URL: ${ES_AGENT_URL}"
    echo -e "  Profile Manager RAG URL: ${PROFILE_MANAGER_URL}"
    echo -e "  Profile Manager ES URL: ${PROFILE_MANAGER_ES_URL}"
    echo -e "  Profile Manager V2 URL: ${PROFILE_MANAGER_V2_URL}"
    echo -e "  Knowledge Base RAG URL: ${KNOWLEDGE_BASE_URL}"
    echo -e "  Knowledge Base ES URL: ${KNOWLEDGE_BASE_ES_URL}"
    
    # Firebase Configuration - consolidated to college-counselling-478115
    export VITE_FIREBASE_API_KEY="AIzaSyAdo23UHvjlHgGuK0BYIqjPeLUoVUEx7t4"
    export VITE_FIREBASE_AUTH_DOMAIN="college-counselling-478115.firebaseapp.com"
    export VITE_FIREBASE_PROJECT_ID="college-counselling-478115"
    export VITE_FIREBASE_STORAGE_BUCKET="college-counselling-478115.firebasestorage.app"
    export VITE_FIREBASE_MESSAGING_SENDER_ID="808989169388"
    export VITE_FIREBASE_APP_ID="1:808989169388:web:d74ceea7c5002dd4bab7c9"
    
    ./deploy_frontend.sh
    echo -e "${GREEN}✓ Frontend deployed: https://college-strategy.web.app${NC}"
}

# Execute deployment based on target
case "$DEPLOY_TARGET" in
    "agent-rag")
        deploy_agent_rag
        ;;
    "agent-es")
        deploy_agent_es
        ;;
    "agents")
        deploy_agents
        ;;
    "agent-hybrid")
        deploy_agent_hybrid
        ;;
    "profile-rag")
        deploy_profile_manager_rag
        ;;
    "profile-es")
        deploy_profile_manager_es
        ;;
    "profile-v2")
        deploy_profile_manager_v2
        ;;
    "knowledge-rag")
        deploy_knowledge_base_manager_rag
        ;;
    "knowledge-es")
        deploy_knowledge_base_manager_es
        ;;
    "knowledge-universities")
        deploy_knowledge_base_manager_universities
        ;;
    "knowledge-universities-v2")
        deploy_knowledge_base_manager_universities_v2
        ;;
    "agent-adk")
        deploy_agent_adk
        ;;
    "university-collector")
        deploy_university_collector
        ;;
    "knowledge-vertexai")
        deploy_knowledge_base_manager_vertexai
        ;;
    "profile-vertexai")
        deploy_profile_manager_vertexai
        ;;
    "payment")
        deploy_payment_manager
        ;;
    "source-curator")
        deploy_source_curator
        ;;
    "datamine")
        deploy_datamine
        ;;
    "sourcery-frontend")
        deploy_sourcery_frontend
        ;;
    "sourcery")
        echo -e "${CYAN}Deploying Sourcery (agent + frontend)...${NC}"
        deploy_datamine
        deploy_sourcery_frontend
        ;;
    "uniminer")
        deploy_uniminer
        ;;
    "vertexai")
        echo -e "${CYAN}Deploying Vertex AI backend (cloud functions + agent)...${NC}"
        deploy_knowledge_base_manager_vertexai
        deploy_profile_manager_vertexai
        deploy_agent_adk
        ;;
    "functions")
        echo -e "${CYAN}Deploying all cloud functions for dynamic routing...${NC}"
        deploy_profile_manager_rag
        deploy_profile_manager_es
        deploy_profile_manager_v2
        deploy_knowledge_base_manager_rag
        deploy_knowledge_base_manager_es
        deploy_knowledge_base_manager_universities
        deploy_payment_manager
        deploy_contact_form
        ;;
    "backend")
        echo -e "${CYAN}Deploying backend (agents + cloud functions)...${NC}"
        deploy_agents
        deploy_agent_adk
        deploy_agent_hybrid
        deploy_profile_manager_rag
        deploy_profile_manager_es
        deploy_knowledge_base_manager_rag
        deploy_knowledge_base_manager_es
        deploy_knowledge_base_manager_universities
        ;;
    "frontend")
        deploy_frontend
        ;;
    "contact")
        deploy_contact_form
        ;;
    "all")
        echo -e "${CYAN}Deploying complete system...${NC}"
        deploy_agents
        deploy_agent_adk
        deploy_profile_manager_rag
        deploy_profile_manager_es
        deploy_knowledge_base_manager_rag
        deploy_knowledge_base_manager_es
        deploy_knowledge_base_manager_universities
        deploy_payment_manager
        deploy_contact_form
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
