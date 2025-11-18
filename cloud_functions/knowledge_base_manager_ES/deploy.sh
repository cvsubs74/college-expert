#!/bin/bash

# Knowledge Base Manager ES - Deployment Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Knowledge Base Manager ES - Deployment                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
FUNCTION_NAME="knowledge-base-manager-es"
REGION="us-east1"
PROJECT_ID="college-counselling-478115"

# Check if required environment variables are set
echo -e "${YELLOW}Checking environment variables...${NC}"

if [ -z "$ES_CLOUD_ID" ]; then
    echo -e "${RED}Error: ES_CLOUD_ID environment variable is not set${NC}"
    echo "Please set it with: export ES_CLOUD_ID='your-elastic-cloud-id'"
    exit 1
fi

if [ -z "$ES_API_KEY" ]; then
    echo -e "${RED}Error: ES_API_KEY environment variable is not set${NC}"
    echo "Please set it with: export ES_API_KEY='your-elastic-api-key'"
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: GEMINI_API_KEY environment variable is not set${NC}"
    echo "Please set it with: export GEMINI_API_KEY='your-gemini-api-key'"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables verified${NC}"
echo ""

# Create temporary env file with actual values
echo -e "${YELLOW}Creating environment configuration...${NC}"
cat > .env.yaml << EOF
# GCP Configuration
GCP_PROJECT_ID: ${PROJECT_ID}
REGION: ${REGION}
GCS_BUCKET_NAME: college-counselling-knowledge-base
DATA_STORE: college_admissions_kb

# Elasticsearch Configuration
ES_CLOUD_ID: ${ES_CLOUD_ID}
ES_API_KEY: ${ES_API_KEY}
ES_INDEX_NAME: university_documents

# Gemini Configuration
GEMINI_API_KEY: ${GEMINI_API_KEY}
EOF

echo -e "${GREEN}✓ Environment configuration created${NC}"
echo ""

# Deploy the function
echo -e "${YELLOW}Deploying Knowledge Base Manager ES function...${NC}"
gcloud functions deploy knowledge-base-manager-es \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --runtime=python312 \
    --source=. \
    --entry-point=knowledge_base_manager_es_http_entry \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=.env.yaml \
    --timeout=540s \
    --memory=1024MB \
    --max-instances=10

echo ""

# Get the function URL
FUNCTION_URL=$(gcloud functions describe ${FUNCTION_NAME} --region=${REGION} --gen2 --format='value(serviceConfig.uri)')

echo -e "${GREEN}✓ Knowledge Base Manager ES deployed successfully!${NC}"
echo -e "${GREEN}  URL: ${FUNCTION_URL}${NC}"
echo ""

# Test the deployment
echo -e "${YELLOW}Testing deployment...${NC}"
curl -X GET "${FUNCTION_URL}" -w "\nHTTP Status: %{http_code}\n"

echo ""
echo -e "${BLUE}Available Endpoints:${NC}"
echo -e "  • POST ${FUNCTION_URL} - Index document"
echo -e "  • POST ${FUNCTION_URL}/search - Search documents"
echo -e "  • GET ${FUNCTION_URL}/list - List documents"
echo -e "  • DELETE ${FUNCTION_URL} - Delete document"
echo ""

# Clean up temporary env file
rm -f .env.yaml

echo -e "${GREEN}Deployment complete! 🎉${NC}"
