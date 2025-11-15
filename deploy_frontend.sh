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

cd frontend

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: frontend/.env file not found${NC}"
    echo -e "${YELLOW}Please create frontend/.env file with your configuration.${NC}"
    echo -e "${YELLOW}You can copy from .env.example: cp frontend/.env.example frontend/.env${NC}"
    exit 1
fi

# Load environment variables from .env file
echo -e "${YELLOW}Loading configuration from .env file...${NC}"
set -a
source .env
set +a

# Validate required variables
if [ -z "$VITE_API_URL" ]; then
    echo -e "${RED}Error: VITE_API_URL not set in .env file${NC}"
    exit 1
fi

if [ -z "$VITE_PROFILE_MANAGER_URL" ]; then
    echo -e "${RED}Error: VITE_PROFILE_MANAGER_URL not set in .env file${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
npm install

# Create .env file
echo -e "${YELLOW}Creating .env file...${NC}"
cat > .env << EOF
VITE_API_URL=${VITE_API_URL}
VITE_PROFILE_MANAGER_URL=${VITE_PROFILE_MANAGER_URL}
VITE_KNOWLEDGE_BASE_URL=${VITE_KNOWLEDGE_BASE_URL}

# Firebase Configuration
VITE_FIREBASE_API_KEY=${VITE_FIREBASE_API_KEY}
VITE_FIREBASE_AUTH_DOMAIN=${VITE_FIREBASE_AUTH_DOMAIN}
VITE_FIREBASE_PROJECT_ID=${VITE_FIREBASE_PROJECT_ID}
VITE_FIREBASE_STORAGE_BUCKET=${VITE_FIREBASE_STORAGE_BUCKET}
VITE_FIREBASE_MESSAGING_SENDER_ID=${VITE_FIREBASE_MESSAGING_SENDER_ID}
VITE_FIREBASE_APP_ID=${VITE_FIREBASE_APP_ID}
EOF

echo -e "${GREEN}✓ Environment configured${NC}"
echo -e "  API URL: ${VITE_API_URL}"
echo -e "  Profile Manager URL: ${VITE_PROFILE_MANAGER_URL}"
echo -e "  Knowledge Base URL: ${VITE_KNOWLEDGE_BASE_URL}"
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
