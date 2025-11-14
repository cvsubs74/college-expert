#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Firebase Configuration Setup                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

PROJECT_ID="college-counselling-478115"

echo -e "${YELLOW}To get your Firebase configuration:${NC}"
echo ""
echo "1. Go to: https://console.firebase.google.com/project/${PROJECT_ID}/settings/general"
echo "2. Scroll down to 'Your apps' section"
echo "3. If you don't have a web app, click 'Add app' → Web (</>) icon"
echo "4. Register app with nickname: 'College Counselor'"
echo "5. Copy the configuration values"
echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Get backend URLs from deployment
AGENT_URL=$(gcloud run services describe college-counselor-agent --region=us-east1 --format='value(status.url)' 2>/dev/null || echo "https://college-counselor-agent-pfnwjfp26a-ue.a.run.app")
FUNCTION_URL=$(gcloud run services describe profile-manager --region=us-east1 --format='value(status.url)' 2>/dev/null || echo "https://profile-manager-pfnwjfp26a-ue.a.run.app")

echo "Please enter your Firebase configuration values:"
echo ""

read -p "Firebase API Key: " FIREBASE_API_KEY
read -p "Firebase Auth Domain (e.g., ${PROJECT_ID}.firebaseapp.com): " FIREBASE_AUTH_DOMAIN
read -p "Firebase Project ID (default: ${PROJECT_ID}): " FIREBASE_PROJECT_ID
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-$PROJECT_ID}
read -p "Firebase Storage Bucket (e.g., ${PROJECT_ID}.appspot.com): " FIREBASE_STORAGE_BUCKET
read -p "Firebase Messaging Sender ID: " FIREBASE_MESSAGING_SENDER_ID
read -p "Firebase App ID: " FIREBASE_APP_ID

echo ""
echo -e "${YELLOW}Creating .env file...${NC}"

# Create .env file
cat > frontend/.env << EOF
# Backend API Configuration
VITE_API_URL=${AGENT_URL}
VITE_PROFILE_MANAGER_URL=${FUNCTION_URL}

# Firebase Configuration
VITE_FIREBASE_API_KEY=${FIREBASE_API_KEY}
VITE_FIREBASE_AUTH_DOMAIN=${FIREBASE_AUTH_DOMAIN}
VITE_FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}
VITE_FIREBASE_STORAGE_BUCKET=${FIREBASE_STORAGE_BUCKET}
VITE_FIREBASE_MESSAGING_SENDER_ID=${FIREBASE_MESSAGING_SENDER_ID}
VITE_FIREBASE_APP_ID=${FIREBASE_APP_ID}

# Application Settings
VITE_APP_NAME=College Counselor
VITE_APP_VERSION=1.0.0

# Default Data Stores
VITE_KNOWLEDGE_BASE_STORE=college_admissions_kb
VITE_STUDENT_PROFILE_STORE=student_profile
EOF

echo -e "${GREEN}✓ .env file created successfully!${NC}"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  API URL: ${AGENT_URL}"
echo "  Profile Manager: ${FUNCTION_URL}"
echo "  Firebase Project: ${FIREBASE_PROJECT_ID}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Enable Firebase Authentication:"
echo "   https://console.firebase.google.com/project/${PROJECT_ID}/authentication/providers"
echo ""
echo "2. Enable Google Sign-In provider"
echo ""
echo "3. Add authorized domains:"
echo "   - localhost"
echo "   - college-strategy.web.app"
echo ""
echo "4. Rebuild and redeploy frontend:"
echo -e "   ${BLUE}cd frontend && npm run build && firebase deploy --only hosting${NC}"
echo ""
