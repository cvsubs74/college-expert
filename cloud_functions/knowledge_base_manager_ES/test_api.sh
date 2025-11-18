#!/bin/bash

# Knowledge Base Manager ES - API Test Script

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Function URL (update this after deployment)
FUNCTION_URL="https://knowledge-base-manager-es-pfnwjfp26a-ue.a.run.app"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Knowledge Base Manager ES - API Tests                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}1. Testing Health Check...${NC}"
response=$(curl -s -w "\n%{http_code}" "$FUNCTION_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ Health check failed (HTTP $http_code)${NC}"
    echo "Response: $body"
fi
echo ""

# Test 2: Search (empty results)
echo -e "${YELLOW}2. Testing Search API...${NC}"
response=$(curl -s -w "\n%{http_code}" \
  -X POST "$FUNCTION_URL/search" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "query": "university admissions"}')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ Search API working${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ Search API failed (HTTP $http_code)${NC}"
    echo "Response: $body"
fi
echo ""

# Test 3: Document Index (expected error)
echo -e "${YELLOW}3. Testing Document Index (expected 404)...${NC}"
response=$(curl -s -w "\n%{http_code}" \
  -X POST "$FUNCTION_URL/documents" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test123", "filename": "test.pdf"}')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✓ Document index API working (expected 404)${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ Document index API unexpected response (HTTP $http_code)${NC}"
    echo "Response: $body"
fi
echo ""

# Test 4: CORS Preflight
echo -e "${YELLOW}4. Testing CORS Preflight...${NC}"
response=$(curl -s -w "\n%{http_code}" \
  -X OPTIONS "$FUNCTION_URL/health" \
  -H "Origin: *" \
  -H "Access-Control-Request-Method: GET")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ CORS preflight working${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ CORS preflight failed (HTTP $http_code)${NC}"
    echo "Response: $body"
fi
echo ""

# Test 5: Error Handling
echo -e "${YELLOW}5. Testing Error Handling...${NC}"
response=$(curl -s -w "\n%{http_code}" "$FUNCTION_URL/unknown")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "404" ]; then
    echo -e "${GREEN}✓ Error handling working${NC}"
    echo "Response: $body"
else
    echo -e "${RED}✗ Error handling failed (HTTP $http_code)${NC}"
    echo "Response: $body"
fi
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    API Tests Complete                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
