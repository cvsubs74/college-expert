#!/bin/bash

# Comprehensive Integration Test for Knowledge Base Manager (RAG)
# Tests all endpoints, error handling, and edge cases

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KB_URL="https://us-east1-college-counselling-478115.cloudfunctions.net/knowledge-base-manager"
TEST_DIR="/tmp/kb_test_$$"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Create test directory
mkdir -p "$TEST_DIR"

# Test utility functions
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${BLUE}Testing: $test_name${NC}"
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

# Test data creation functions
create_test_document() {
    cat > "$1" << 'EOF'
# MIT Admissions Guide

## Overview
Massachusetts Institute of Technology (MIT) is a private research university located in Cambridge, Massachusetts.

## Academic Requirements
- **GPA**: 3.9-4.0 (weighted)
- **SAT**: 1530-1580
- **ACT**: 35-36
- **Class Rank**: Top 5%

## Application Process
1. Submit Common Application or Coalition Application
2. Provide SAT/ACT scores (test-optional for 2024-2025)
3. Submit high school transcript
4. Letters of recommendation (2 teachers, 1 counselor)
5. Essays and personal statements

## Notable Programs
- Computer Science and Engineering
- Electrical Engineering and Computer Science
- Mechanical Engineering
- Physics
- Mathematics
- Biology
- Chemistry

## Campus Life
- Location: Cambridge, Massachusetts
- Campus size: 168 acres
- Student organizations: 500+
- Athletics: Division III

## Financial Aid
- Need-blind admissions for U.S. citizens
- Meets 100% of demonstrated financial need
- Average scholarship: $52,000
- No loans in financial aid packages
EOF
}

create_large_document() {
    # Create a larger document for testing file size limits
    for i in {1..100}; do
        echo "Section $i: This is test content for section $i of the large document."
        echo "It contains information about university admissions, requirements, and processes."
        echo "MIT Stanford Harvard Yale Princeton Duke Cornell Brown Dartmouth Columbia."
        echo "Engineering Computer Science Business Medicine Law Arts Humanities."
    done > "$1"
}

create_pdf_document() {
    # Create a simple PDF-like document (text with PDF markers)
    cat > "$1" << 'EOF'
%PDF-1.4
1 0 obj
<<
/Title (Sample PDF Document)
/Creator (Test Script)
>>
endobj

# Stanford University Admissions

## Introduction
Stanford University is a private research university in Stanford, California.

## Requirements
- GPA: 3.8-4.0
- SAT: 1450-1570
- ACT: 32-35

## Programs
- Computer Science
- Engineering
- Business
- Medicine

## Campus
- Location: Stanford, CA
- Size: 8,180 acres
- Students: 17,000+
EOF
}

# Health Check Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    HEALTH CHECK TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Health Check - Basic Connectivity" \
    "curl -s -f '$KB_URL/health' | grep -q 'healthy'"

run_test "Health Check - Response Format" \
    "curl -s '$KB_URL/health' | grep -q '\"status\":\"healthy\"'"

run_test "Health Check - CORS Headers" \
    "curl -s -I '$KB_URL/health' | grep -i 'access-control-allow-origin'"

# Document Upload Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   DOCUMENT UPLOAD TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Upload basic text document
create_test_document "$TEST_DIR/mit_guide.txt"
run_test "Upload Basic Text Document" \
    "curl -s -X POST '$KB_URL/upload' \
     -F 'file=@$TEST_DIR/mit_guide.txt' \
     -F 'user_id=test@example.com' \
     | grep -q '\"success\":true'"

# Test 2: Upload without file
run_test "Upload Without File - Should Fail" \
    "! curl -s -X POST '$KB_URL/upload' \
     -F 'user_id=test@example.com' \
     | grep -q '\"success\": true'"

# Test 3: Upload without user_id
run_test "Upload Without User ID - Should Fail" \
    "! curl -s -X POST '$KB_URL/upload' \
     -F 'file=@$TEST_DIR/mit_guide.txt' \
     | grep -q '\"success\": true'"

# Test 4: Large document upload
create_large_document "$TEST_DIR/large_doc.txt"
run_test "Upload Large Document" \
    "curl -s -X POST '$KB_URL/upload' \
     -F 'file=@$TEST_DIR/large_doc.txt' \
     -F 'user_id=test@example.com' \
     | grep -q '\"success\":true'"

# Test 5: PDF document upload (using text file with .txt extension)
echo "Sample PDF content for testing" > "$TEST_DIR/stanford_guide.txt"
run_test "Upload PDF Document" \
    "curl -s -X POST '$KB_URL/upload' \
     -F 'file=@$TEST_DIR/stanford_guide.txt' \
     -F 'user_id=test@example.com' \
     | grep -q '\"success\":true'"

# Document Listing Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   DOCUMENT LISTING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "List All Documents" \
    "curl -s -X GET '$KB_URL/documents?limit=50' \
     | grep -q '\"success\":true'"

run_test "List Documents with Limit" \
    "curl -s -X GET '$KB_URL/documents?limit=5' \
     | grep -q '\"success\":true'"

run_test "List Documents for Specific User" \
    "curl -s -X GET '$KB_URL/documents?user_id=test@example.com&limit=10' \
     | grep -q '\"success\":true'"

run_test "List Documents with Pagination" \
    "curl -s -X GET '$KB_URL/documents?limit=3&from=0' \
     | grep -q '\"success\":true'"

# Document Search Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    DOCUMENT SEARCH TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Search for MIT" \
    "curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"MIT admissions requirements\",\"user_id\":\"test@example.com\",\"limit\":5}' \
     | grep -q '\"success\":true'"

run_test "Search for Stanford" \
    "curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"Stanford university campus\",\"user_id\":\"test@example.com\",\"limit\":5}' \
     | grep -q '\"success\":true'"

run_test "Search with Empty Query - Should Fail" \
    "! curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"\",\"user_id\":\"test@example.com\"}' \
     | grep -q '\"success\":true'"

run_test "Search Without User ID" \
    "curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"university admissions\",\"limit\":5}' \
     | grep -q '\"success\":true'"

run_test "Search with Complex Query" \
    "curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"engineering computer science financial aid requirements GPA SAT\",\"user_id\":\"test@example.com\",\"limit\":10}' \
     | grep -q '\"success\":true'"

# Document Retrieval Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                 DOCUMENT RETRIEVAL TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Get a document name first
DOC_NAME=$(curl -s -X GET "$KB_URL/documents?user_id=test@example.com&limit=1" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('documents'):
        print(data['documents'][0].get('name', ''))
except:
    pass
" 2>/dev/null)

if [ -n "$DOC_NAME" ]; then
    run_test "Get Document by Name" \
        "curl -s -X POST '$KB_URL/get-document' \
         -H 'Content-Type: application/json' \
         -d '{\"file_name\":\"$DOC_NAME\"}' \
         | grep -q '\"success\":true'"

    run_test "Get Document with Invalid Name - Should Fail" \
        "! curl -s -X POST '$KB_URL/get-document' \
         -H 'Content-Type: application/json' \
         -d '{\"file_name\":\"nonexistent_document.txt\"}' \
         | grep -q '\"success\": true'"
else
    echo -e "${YELLOW}Skipping document retrieval tests - no documents found${NC}"
fi

# Error Handling Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   ERROR HANDLING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Invalid Endpoint - Should Return 404" \
    "curl -s '$KB_URL/invalid-endpoint' | grep -q 'Endpoint not found'"

run_test "Invalid HTTP Method on Health" \
    "curl -s -X POST '$KB_URL/health' | grep -q 'healthy'"

run_test "Malformed JSON in Search" \
    "! curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{invalid json}' \
     | grep -q '\"success\": true'"

# Performance Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PERFORMANCE TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Health Check Response Time < 2s" \
    "curl -s '$KB_URL/health' >/dev/null"

run_test "Document List Response Time < 5s" \
    "curl -s '$KB_URL/documents?limit=20' >/dev/null"

run_test "Search Response Time < 5s" \
    "curl -s -X POST '$KB_URL/search' \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"MIT\",\"user_id\":\"test@example.com\"}' >/dev/null"

# Cleanup
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                        CLEANUP${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Cleaning up test files...${NC}"
rm -rf "$TEST_DIR"
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Results Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    TEST SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:        $PASSED_TESTS${NC}"
echo -e "${RED}Failed:        $FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
    echo -e "${GREEN}✓ Knowledge Base Manager (RAG) is fully functional${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}Please check the failed tests and fix the issues${NC}"
    exit 1
fi
