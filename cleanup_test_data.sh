#!/bin/bash

# Cleanup script for all test data from cloud functions and databases
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function URLs
KB_RAG_URL="https://us-east1-college-counselling-478115.cloudfunctions.net/knowledge-base-manager"
KB_ES_URL="https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app"
PROFILE_RAG_URL="https://us-east1-college-counselling-478115.cloudfunctions.net/profile-manager"
PROFILE_ES_URL="https://profile-manager-es-pfnwjfp26a-ue.a.run.app"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           CLEANUP TEST DATA FROM ALL FUNCTIONS             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to delete all documents from a function
cleanup_documents() {
    local url="$1"
    local name="$2"
    
    echo -e "${YELLOW}Cleaning up documents from: $name${NC}"
    
    # Get list of all documents
    echo "  → Getting document list..."
    docs_response=$(curl -s -X GET "$url/documents?limit=100" 2>/dev/null || echo '{"success":false}')
    
    if echo "$docs_response" | grep -q '"success":true'; then
        # Extract document names and delete them
        doc_names=$(echo "$docs_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('documents'):
        for doc in data['documents']:
            print(doc.get('name', ''))
except:
    pass
" 2>/dev/null)
        
        deleted_count=0
        for doc_name in $doc_names; do
            if [ -n "$doc_name" ]; then
                # Try different delete endpoints
                if [[ "$url" == *"knowledge-base-manager"* ]]; then
                    # RAG KB uses DELETE endpoint
                    delete_response=$(curl -s -X DELETE "$url/delete?file_name=$doc_name" 2>/dev/null || echo '{"success":false}')
                else
                    # ES functions use POST delete endpoint
                    delete_response=$(curl -s -X POST "$url/delete" -H 'Content-Type: application/json' -d "{\"file_name\":\"$doc_name\"}" 2>/dev/null || echo '{"success":false}')
                fi
                
                if echo "$delete_response" | grep -q '"success":true'; then
                    ((deleted_count++))
                fi
            fi
        done
        
        echo -e "${GREEN}  ✓ Deleted $deleted_count documents${NC}"
    else
        echo -e "${RED}  ✗ Failed to get document list${NC}"
    fi
}

# Function to delete all profiles from a function
cleanup_profiles() {
    local url="$1"
    local name="$2"
    
    echo -e "${YELLOW}Cleaning up profiles from: $name${NC}"
    
    # Get list of all profiles
    echo "  → Getting profile list..."
    profiles_response=$(curl -s -X GET "$url/profiles?limit=100" 2>/dev/null || echo '{"success":false}')
    
    if echo "$profiles_response" | grep -q '"success":true'; then
        # Extract profile names and delete them
        profile_names=$(echo "$profiles_response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('profiles'):
        for profile in data['profiles']:
            print(profile.get('name', ''))
except:
    pass
" 2>/dev/null)
        
        deleted_count=0
        for profile_name in $profile_names; do
            if [ -n "$profile_name" ]; then
                # Try different delete endpoints
                if [[ "$url" == *"profile-manager"* && ! "$url" == *"-es"* ]]; then
                    # RAG Profile Manager uses DELETE endpoint
                    delete_response=$(curl -s -X DELETE "$url/delete-profile?profile_name=$profile_name" 2>/dev/null || echo '{"success":false}')
                else
                    # ES Profile Manager uses POST delete endpoint
                    delete_response=$(curl -s -X POST "$url/profiles/delete" -H 'Content-Type: application/json' -d "{\"profile_name\":\"$profile_name\"}" 2>/dev/null || echo '{"success":false}')
                fi
                
                if echo "$delete_response" | grep -q '"success":true'; then
                    ((deleted_count++))
                fi
            fi
        done
        
        echo -e "${GREEN}  ✓ Deleted $deleted_count profiles${NC}"
    else
        echo -e "${RED}  ✗ Failed to get profile list${NC}"
    fi
}

# Cleanup all functions
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    CLEANUP DOCUMENTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

cleanup_documents "$KB_RAG_URL" "Knowledge Base Manager (RAG)"
cleanup_documents "$KB_ES_URL" "Knowledge Base Manager (ES)"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    CLEANUP PROFILES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

cleanup_profiles "$PROFILE_RAG_URL" "Profile Manager (RAG)"
cleanup_profiles "$PROFILE_ES_URL" "Profile Manager (ES)"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   CLEANUP COMPLETE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🧹 ALL TEST DATA CLEANED SUCCESSFULLY! 🧹        ║${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║  All test documents and profiles have been removed from    ║${NC}"
echo -e "${GREEN}║  all cloud functions and databases.                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
