#!/bin/bash

# College Counselor - Frontend Deployment Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Frontend Deployment               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if URLs are provided
if [ -z "$VITE_API_URL" ]; then
    echo -e "${RED}Error: VITE_API_URL not set${NC}"
    echo "Please set it with: export VITE_API_URL='your-agent-url'"
    exit 1
fi

if [ -z "$VITE_PROFILE_MANAGER_URL" ]; then
    echo -e "${RED}Error: VITE_PROFILE_MANAGER_URL not set${NC}"
    echo "Please set it with: export VITE_PROFILE_MANAGER_URL='your-function-url'"
    exit 1
fi

cd frontend

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Create .env file
echo -e "${YELLOW}Creating .env file...${NC}"
cat > .env << EOF
VITE_API_URL=${VITE_API_URL}
VITE_PROFILE_MANAGER_URL=${VITE_PROFILE_MANAGER_URL}
EOF

echo -e "${GREEN}✓ Environment configured${NC}"
echo -e "  API URL: ${VITE_API_URL}"
echo -e "  Profile Manager URL: ${VITE_PROFILE_MANAGER_URL}"
echo ""

# Build
echo -e "${YELLOW}Building frontend...${NC}"
npm run build

# Deploy to Firebase
echo -e "${YELLOW}Deploying to Firebase...${NC}"
firebase deploy --only hosting

echo ""
echo -e "${GREEN}✓ Frontend deployed successfully!${NC}"
echo -e "${GREEN}  URL: https://college-counsellor.web.app${NC}"
echo ""
