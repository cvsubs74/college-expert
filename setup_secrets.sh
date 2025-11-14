#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="college-counselling-478115"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Secret Setup                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Set project
echo -e "${YELLOW}Setting GCP project to: ${PROJECT_ID}${NC}"
gcloud config set project $PROJECT_ID
echo ""

# Check if Secret Manager API is enabled
echo -e "${YELLOW}Checking Secret Manager API...${NC}"
if ! gcloud services list --enabled --filter="name:secretmanager.googleapis.com" --format="value(name)" | grep -q secretmanager; then
    echo -e "${YELLOW}Enabling Secret Manager API...${NC}"
    gcloud services enable secretmanager.googleapis.com
    echo -e "${GREEN}✓ Secret Manager API enabled${NC}"
else
    echo -e "${GREEN}✓ Secret Manager API already enabled${NC}"
fi
echo ""

# Prompt for Gemini API Key
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Setting up Gemini API Key${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Please enter your Gemini API Key:"
echo "(You can get this from: https://aistudio.google.com/app/apikey)"
echo ""
read -s GEMINI_API_KEY

if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: No API key provided${NC}"
    exit 1
fi

# Check if secret already exists
echo ""
echo -e "${YELLOW}Checking if secret exists...${NC}"
if gcloud secrets describe gemini-api-key --project=$PROJECT_ID &>/dev/null; then
    echo -e "${YELLOW}Secret 'gemini-api-key' already exists. Updating with new version...${NC}"
    echo -n "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
    echo -e "${GREEN}✓ Secret updated successfully${NC}"
else
    echo -e "${YELLOW}Creating new secret 'gemini-api-key'...${NC}"
    echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key \
        --replication-policy="automatic" \
        --data-file=-
    echo -e "${GREEN}✓ Secret created successfully${NC}"
fi

echo ""
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Setting up Firebase Configuration (Optional)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Would you like to set up Firebase configuration secrets? (y/n)"
read -r setup_firebase

if [ "$setup_firebase" = "y" ] || [ "$setup_firebase" = "Y" ]; then
    echo ""
    echo "Please enter your Firebase API Key:"
    read -s FIREBASE_API_KEY
    
    echo ""
    echo "Please enter your Firebase App ID:"
    read -s FIREBASE_APP_ID
    
    # Create/update Firebase API Key secret
    if [ -n "$FIREBASE_API_KEY" ]; then
        if gcloud secrets describe firebase-api-key --project=$PROJECT_ID &>/dev/null; then
            echo -n "$FIREBASE_API_KEY" | gcloud secrets versions add firebase-api-key --data-file=-
            echo -e "${GREEN}✓ Firebase API Key secret updated${NC}"
        else
            echo -n "$FIREBASE_API_KEY" | gcloud secrets create firebase-api-key \
                --replication-policy="automatic" \
                --data-file=-
            echo -e "${GREEN}✓ Firebase API Key secret created${NC}"
        fi
    fi
    
    # Create/update Firebase App ID secret
    if [ -n "$FIREBASE_APP_ID" ]; then
        if gcloud secrets describe firebase-app-id --project=$PROJECT_ID &>/dev/null; then
            echo -n "$FIREBASE_APP_ID" | gcloud secrets versions add firebase-app-id --data-file=-
            echo -e "${GREEN}✓ Firebase App ID secret updated${NC}"
        else
            echo -n "$FIREBASE_APP_ID" | gcloud secrets create firebase-app-id \
                --replication-policy="automatic" \
                --data-file=-
            echo -e "${GREEN}✓ Firebase App ID secret created${NC}"
        fi
    fi
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Secret Setup Complete!                                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Secrets created in project: ${PROJECT_ID}${NC}"
echo ""
echo "To use the secret in your deployment:"
echo -e "${BLUE}export GEMINI_API_KEY=\$(gcloud secrets versions access latest --secret=gemini-api-key)${NC}"
echo ""
echo "Or run the deployment script which will automatically fetch it:"
echo -e "${BLUE}./deploy.sh${NC}"
echo ""
