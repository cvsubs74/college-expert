#!/bin/bash

# Quick test script to verify frontend API endpoints work correctly
# Tests the same endpoints that the frontend will use

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
RAG_AGENT_URL="https://college-expert-rag-agent-pfnwjfp26a-ue.a.run.app"
ES_AGENT_URL="https://college-expert-es-agent-pfnwjfp26a-ue.a.run.app"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Frontend API Endpoint Test${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Test 1: RAG Agent - Create Session
echo -e "${YELLOW}Test 1: Create RAG Agent Session${NC}"
RAG_SESSION_RESPONSE=$(curl -s -X POST "$RAG_AGENT_URL/apps/college_expert_rag/users/user/sessions" \
    -H 'Content-Type: application/json' \
    -d '{"user_input": "Hello, I need help with college applications"}')

RAG_SESSION_ID=$(echo "$RAG_SESSION_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$RAG_SESSION_ID" ]; then
    echo -e "${GREEN}✓ RAG Session created: $RAG_SESSION_ID${NC}"
    
    # Extract and display response
    RESPONSE_TEXT=$(echo "$RAG_SESSION_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); events = data.get('events', []); print(events[0]['content']['parts'][0]['text'][:200] if events else 'No response')" 2>/dev/null || echo "")
    echo -e "${BLUE}Response preview: ${RESPONSE_TEXT}...${NC}"
else
    echo -e "${RED}✗ Failed to create RAG session${NC}"
    echo "$RAG_SESSION_RESPONSE"
    exit 1
fi
echo ""

# Test 2: RAG Agent - Send Message
echo -e "${YELLOW}Test 2: Send Message to RAG Agent${NC}"
RAG_MESSAGE_RESPONSE=$(curl -s -X POST "$RAG_AGENT_URL/run" \
    -H 'Content-Type: application/json' \
    -d "{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"$RAG_SESSION_ID\",\"new_message\":{\"parts\":[{\"text\":\"What are the requirements for Stanford?\"}]}}")

if echo "$RAG_MESSAGE_RESPONSE" | grep -q "events"; then
    echo -e "${GREEN}✓ RAG Message sent successfully${NC}"
    
    # Extract and display response
    RESPONSE_TEXT=$(echo "$RAG_MESSAGE_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); events = data.get('events', []); print(events[0]['content']['parts'][0]['text'][:200] if events else 'No response')" 2>/dev/null || echo "")
    echo -e "${BLUE}Response preview: ${RESPONSE_TEXT}...${NC}"
else
    echo -e "${RED}✗ Failed to send message to RAG agent${NC}"
    echo "$RAG_MESSAGE_RESPONSE"
    exit 1
fi
echo ""

# Test 3: ES Agent - Create Session
echo -e "${YELLOW}Test 3: Create ES Agent Session${NC}"
ES_SESSION_RESPONSE=$(curl -s -X POST "$ES_AGENT_URL/apps/college_expert_es/users/user/sessions" \
    -H 'Content-Type: application/json' \
    -d '{"user_input": "Hello, I need help with college applications"}')

ES_SESSION_ID=$(echo "$ES_SESSION_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$ES_SESSION_ID" ]; then
    echo -e "${GREEN}✓ ES Session created: $ES_SESSION_ID${NC}"
    
    # Extract and display response
    RESPONSE_TEXT=$(echo "$ES_SESSION_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); events = data.get('events', []); print(events[0]['content']['parts'][0]['text'][:200] if events else 'No response')" 2>/dev/null || echo "")
    echo -e "${BLUE}Response preview: ${RESPONSE_TEXT}...${NC}"
else
    echo -e "${RED}✗ Failed to create ES session${NC}"
    echo "$ES_SESSION_RESPONSE"
    exit 1
fi
echo ""

# Test 4: ES Agent - Send Message
echo -e "${YELLOW}Test 4: Send Message to ES Agent${NC}"
ES_MESSAGE_RESPONSE=$(curl -s -X POST "$ES_AGENT_URL/run" \
    -H 'Content-Type: application/json' \
    -d "{\"app_name\":\"college_expert_es\",\"user_id\":\"user\",\"session_id\":\"$ES_SESSION_ID\",\"new_message\":{\"parts\":[{\"text\":\"What are the requirements for MIT?\"}]}}")

if echo "$ES_MESSAGE_RESPONSE" | grep -q "events"; then
    echo -e "${GREEN}✓ ES Message sent successfully${NC}"
    
    # Extract and display response
    RESPONSE_TEXT=$(echo "$ES_MESSAGE_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); events = data.get('events', []); print(events[0]['content']['parts'][0]['text'][:200] if events else 'No response')" 2>/dev/null || echo "")
    echo -e "${BLUE}Response preview: ${RESPONSE_TEXT}...${NC}"
else
    echo -e "${RED}✗ Failed to send message to ES agent${NC}"
    echo "$ES_MESSAGE_RESPONSE"
    exit 1
fi
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ All Frontend API Tests Passed!${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Frontend is ready to use these endpoints:${NC}"
echo -e "  RAG Agent: $RAG_AGENT_URL"
echo -e "  ES Agent: $ES_AGENT_URL"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. cd frontend"
echo -e "  2. npm install"
echo -e "  3. npm run dev"
echo -e "  4. Test the chat interface at http://localhost:5173"
