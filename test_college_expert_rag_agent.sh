#!/bin/bash

# Comprehensive Integration Test for College Expert RAG Agent
# Tests all agent functionality including knowledge base and profile integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
RAG_AGENT_URL="https://college-expert-rag-agent-pfnwjfp26a-ue.a.run.app"
KB_RAG_URL="https://knowledge-base-manager-pfnwjfp26a-ue.a.run.app"
PROFILE_RAG_URL="https://profile-manager-pfnwjfp26a-ue.a.run.app"
TEST_USER_EMAIL="test-rag-agent@example.com"
TEST_DIR="/tmp/rag_agent_test_$$"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SESSION_ID=""

# Create test directory
mkdir -p "$TEST_DIR"

# Logging
LOG_FILE="test_logs/test_college_expert_rag_agent_$(date +%Y%m%d_%H%M%S).log"
mkdir -p test_logs
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  College Expert RAG Agent - Comprehensive Test Suite      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test Configuration:${NC}"
echo -e "  Agent URL: $RAG_AGENT_URL"
echo -e "  Knowledge Base URL: $KB_RAG_URL"
echo -e "  Profile Manager URL: $PROFILE_RAG_URL"
echo -e "  Test User: $TEST_USER_EMAIL"
echo -e "  Log File: $LOG_FILE"
echo ""

# Test utility functions
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}Test $((TOTAL_TESTS + 1)): $test_name${NC}"
    ((TOTAL_TESTS++))
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED_TESTS++))
        echo -e "${RED}Command: $test_command${NC}"
    fi
    echo ""
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up test data...${NC}"
    
    # Remove test directory
    rm -rf "$TEST_DIR"
    
    echo -e "${GREEN}✓ Cleanup complete${NC}"
    echo -e "${YELLOW}Note: Agent does not upload data - KB and Profile data managed separately${NC}"
}

trap cleanup EXIT

# ============================================================================
# PHASE 1: Prerequisites Check
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 1: Prerequisites Check${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Note: This test assumes that:${NC}"
echo -e "  1. Knowledge Base Manager has university documents uploaded"
echo -e "  2. Profile Manager has student profiles available"
echo -e "  3. The agent queries these existing services (does NOT upload data)"
echo ""

# Test 1: Verify Knowledge Base Manager is accessible
run_test "Verify Knowledge Base Manager is Accessible" \
    "curl -s -f '$KB_RAG_URL/documents' >/dev/null"

# Test 2: Verify Profile Manager is accessible
run_test "Verify Profile Manager is Accessible" \
    "curl -s '$PROFILE_RAG_URL/list-profiles' | grep -q 'success\|documents' || curl -s '$PROFILE_RAG_URL/' | grep -q 'success\|profile'"

# ============================================================================
# PHASE 2: Agent Session Management
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 2: Agent Session Management${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 3: Create session
echo "Creating agent session..."
SESSION_RESPONSE=$(curl -s -X POST "$RAG_AGENT_URL/apps/college_expert_rag/users/user/sessions" \
    -H 'Content-Type: application/json' \
    -d '{"user_input": "Hello"}')

run_test "Create Agent Session" \
    "echo '$SESSION_RESPONSE' | grep -q '\"id\"'"

# Extract session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}✓ Session created: $SESSION_ID${NC}"
else
    echo -e "${RED}✗ Failed to create session${NC}"
fi
echo ""

# ============================================================================
# PHASE 3: General Knowledge Base Queries (No Profile)
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 3: General Knowledge Base Queries${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 2: Query about Stanford admission requirements
run_test "Query Stanford Admission Requirements" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What are the admission requirements for Stanford University?\"}]}}' \
     | grep -qi 'stanford\|gpa\|sat'"

# Test 3: Query about Stanford acceptance rate
run_test "Query Stanford Acceptance Rate" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What is the acceptance rate at Stanford?\"}]}}' \
     | grep -qi 'stanford\|acceptance\|3.9%\|rate'"

# Test 4: Query about Stanford majors
run_test "Query Stanford Popular Majors" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What are the popular majors at Stanford?\"}]}}' \
     | grep -qi 'computer science\|engineering\|major'"

# Test 5: Query about application deadlines
run_test "Query Stanford Application Deadlines" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"When are the application deadlines for Stanford?\"}]}}' \
     | grep -qi 'november\|january\|deadline'"

# ============================================================================
# PHASE 4: Comparative and Analytical Queries
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 4: Comparative and Analytical Queries${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 10: Compare universities
run_test "Compare Universities" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"How does Stanford compare to other top universities?\"}]}}' \
     | grep -qi 'stanford\|university\|compare\|rank\|admission\|competitive'"

# Test 11: Major-specific query
run_test "Computer Science Program Query" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Tell me about Computer Science programs at Stanford\"}]}}' \
     | grep -qi 'computer science\|stanford\|program'"

# Test 12: Admission strategy
run_test "Admission Strategy Query" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What makes a strong Stanford application?\"}]}}' \
     | grep -qi 'stanford\|application\|strong\|admission'"

# ============================================================================
# PHASE 5: Multi-Turn Conversation
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 5: Multi-Turn Conversation${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 13: Follow-up question
run_test "Follow-up Question About Financial Aid" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What about financial aid at Stanford?\"}]}}' \
     | grep -qi 'financial aid\|need-blind\|stanford'"

# Test 14: Context retention
run_test "Context Retention - Reference Previous Topic" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Tell me more about that\"}]}}' \
     | grep -qi 'stanford\|financial\|aid'"

# ============================================================================
# PHASE 6: Error Handling and Edge Cases
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 6: Error Handling and Edge Cases${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 15: Query about unknown university
run_test "Query About Unknown University" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Tell me about Fake University that does not exist\"}]}}' \
     | grep -qi 'not\|information\|available\|find\|data\|sorry\|unable'"

# Test 16: Empty query
run_test "Handle Empty Query" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"\"}]}}' \
     | grep -qi 'help\|question\|ask\|assist'"

# Test 17: Complex multi-part query
run_test "Complex Multi-Part Query" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What are the requirements, deadlines, and financial aid options for Stanford?\"}]}}' \
     | grep -qi 'stanford\|requirement\|deadline\|financial'"

# ============================================================================
# PHASE 7: Integration Verification
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 7: Integration Verification${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 18: Verify Knowledge Base is accessible
run_test "Verify Knowledge Base Manager is Accessible" \
    "curl -s -f '$KB_RAG_URL/documents' >/dev/null"

# Test 19: Verify Profile Manager is accessible
run_test "Verify Profile Manager is Accessible" \
    "curl -s '$PROFILE_RAG_URL/list-profiles' | grep -q 'success\|documents' || curl -s '$PROFILE_RAG_URL/' | grep -q 'success\|profile'"

# Test 20: Agent can query knowledge base
run_test "Agent Successfully Queries Knowledge Base" \
    "curl -s -X POST '$RAG_AGENT_URL/run' \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Summarize what you know about Stanford\"}]}}' \
     | grep -qi 'stanford'"

# ============================================================================
# Test Summary
# ============================================================================

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Test Summary${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Total Tests:${NC} $TOTAL_TESTS"
echo -e "${GREEN}Passed:${NC} $PASSED_TESTS"
echo -e "${RED}Failed:${NC} $FAILED_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check the log file: $LOG_FILE${NC}"
    exit 1
fi
