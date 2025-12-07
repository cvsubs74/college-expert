#!/bin/bash

# Comprehensive Integration Test for College Expert Hybrid Agent
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
HYBRID_AGENT_URL="https://college-expert-hybrid-agent-808989169388.us-east1.run.app"
# Using the universities KB URL as seen in API.js for hybrid
KB_URL="https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
PROFILE_URL="https://profile-manager-es-pfnwjfp26a-ue.a.run.app"
TEST_USER_EMAIL="cvsubs@gmail.com"
TEST_DIR="/tmp/hybrid_agent_test_$$"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SESSION_ID=""

# Create test directory
mkdir -p "$TEST_DIR"

# Logging
LOG_FILE="test_logs/test_college_expert_hybrid_agent_$(date +%Y%m%d_%H%M%S).log"
mkdir -p test_logs
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  College Expert Hybrid Agent - Comprehensive Test Suite    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Test Configuration:${NC}"
echo -e "  Agent URL: $HYBRID_AGENT_URL"
echo -e "  Knowledge Base URL: $KB_URL"
echo -e "  Profile Manager URL: $PROFILE_URL"
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
    rm -rf "$TEST_DIR"
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

trap cleanup EXIT

# ============================================================================
# PHASE 1: Prerequisites Check
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 1: Prerequisites Check${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Verify Knowledge Base Manager is accessible (Hybrid uses / root endpoint for listing)
run_test "Verify Knowledge Base Manager is Accessible" \
    "curl -s -f '$KB_URL/' >/dev/null"

# Test 2: Verify Profile Manager is accessible
run_test "Verify Profile Manager is Accessible" \
    "curl -s '$PROFILE_URL/profiles' | grep -q 'success\|documents' || curl -s '$PROFILE_URL/' | grep -q 'success\|profile'"

# ============================================================================
# PHASE 2: Agent Session Management
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 2: Agent Session Management${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 3: Create session
echo "Creating agent session..."
SESSION_RESPONSE=$(curl -s -X POST "$HYBRID_AGENT_URL/apps/college_expert_hybrid/users/user/sessions" \
    -H 'Content-Type: application/json' \
    -d '{"user_input": "Hello"}')

echo "Session Response: $SESSION_RESPONSE"

run_test "Create Agent Session" \
    "echo '$SESSION_RESPONSE' | grep -q '\"id\"'"

# Extract session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('id', ''))" 2>/dev/null || echo "")

if [ -n "$SESSION_ID" ]; then
    echo -e "${GREEN}✓ Session created: $SESSION_ID${NC}"
else
    echo -e "${RED}✗ Failed to create session${NC}"
    exit 1
fi
echo ""

# Function to send message
send_message() {
    local message="$1"
    local check_pattern="$2"
    
    echo -e "Sending message: \"$message\""
    RESPONSE=$(curl -s -X POST "$HYBRID_AGENT_URL/run" \
        -H 'Content-Type: application/json' \
        -d "{\"app_name\":\"college_expert_hybrid\",\"user_id\":\"user\",\"session_id\":\"$SESSION_ID\",\"new_message\":{\"parts\":[{\"text\":\"$message\"}]}}")
    
    # Store response for inspection if needed
    echo "$RESPONSE" > "$TEST_DIR/last_response.json"
    
    # Check if response matches pattern (using grep -i for case insensitive)
    echo "$RESPONSE" | grep -qi "$check_pattern"
}

# ============================================================================
# PHASE 3: General University Information (No Profile)
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 3: General University Information${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 4: Basic Program Search
run_test "Q1: Basic Program Search (Universities with Business)" \
    "send_message 'What universities in the knowledge base offer business undergraduate programs?' 'business'"

# Test 5: UC Engineering
run_test "Q2: UC Engineering Programs" \
    "send_message 'Tell me about engineering programs at UC schools' 'engineering'"

# Test 6: University Comparisons
run_test "Q4: Compare Berkeley and UCLA for CS" \
    "send_message 'Compare UC Berkeley and UCLA for computer science - which has better career outcomes?' 'berkeley\|ucla\|computer science'"

# Test 7: Specific Data Queries (California Acceptance Rates)
run_test "Q7: California Acceptance Rates" \
    "send_message 'What are the acceptance rates for all universities in California?' 'acceptance\|rate'"

# Test 8: Highest Earnings
run_test "Q8: Highest Median Earnings" \
    "send_message 'Which universities have the highest median earnings for graduates?' 'earnings\|median'"

# Test 9: UCLA Requirements
run_test "Q9: UCLA Application Requirements" \
    "send_message 'Tell me about UCLA\'s application requirements and deadlines' 'ucla\|deadline\|requirement'"

# ============================================================================
# PHASE 4: Personalized Analysis (Uses Profile)
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 4: Personalized Analysis${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 10: Individual School Chances
run_test "Q12: Chances at UCLA (Profile)" \
    "send_message 'What are my chances at UCLA? [USER_EMAIL: $TEST_USER_EMAIL]' 'ucla\|chance\|profile'"

# Test 11: Multi-School Chances
run_test "Q13: Analyze chances at UC Berkeley and USC" \
    "send_message 'Analyze my chances at UC Berkeley and USC [USER_EMAIL: $TEST_USER_EMAIL]' 'berkeley\|usc\|chance'"

# Test 12: Stanford (Not in KB)
run_test "Q14: Stanford (Not in KB check)" \
    "send_message 'Should I apply to Stanford? [USER_EMAIL: $TEST_USER_EMAIL]' 'stanford\|knowledge base\|not'"

# Test 13: Profile-Based Recommendations (Safety Schools)
run_test "Q15: Safety Schools Recommendation" \
    "send_message 'Based on my profile, which universities should I consider as safety schools? [USER_EMAIL: $TEST_USER_EMAIL]' 'safety\|school'"

# Test 14: Gap Analysis
run_test "Q18: Strengthen Application to UCSD" \
    "send_message 'What aspects of my profile would strengthen my application to UC San Diego? [USER_EMAIL: $TEST_USER_EMAIL]' 'ucsd\|san diego\|strengthen\|improve'"

# ============================================================================
# PHASE 5: Complex Multi-Faceted Queries
# ============================================================================

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 5: Complex Multi-Faceted Queries${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 15: Strategic Planning (Balanced List)
run_test "Q20: Build Balanced College List" \
    "send_message 'Help me build a balanced college list for Business majors in California [USER_EMAIL: $TEST_USER_EMAIL]' 'balanced\|list\|reach\|target'"

# Test 16: Interdisciplinary Search
run_test "Q21: Marketing and Psychology Interdisciplinary" \
    "send_message 'I want to study Marketing and Psychology - which universities have programs that combine both?' 'marketing\|psychology'"

# Test 17: Application Strategy Comparison
run_test "Q23: Application Strategy Berkeley vs USC" \
    "send_message 'Compare the application strategies for UC Berkeley vs USC - what does each school prioritize?' 'strategy\|berkeley\|usc'"

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
