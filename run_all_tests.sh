#!/bin/bash

# Master Test Runner for All Cloud Functions
# Runs comprehensive integration tests for all 4 cloud functions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/test_logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TOTAL_FUNCTIONS=4
PASSED_FUNCTIONS=0
FAILED_FUNCTIONS=0

# Create log directory
mkdir -p "$LOG_DIR"

# Test results
TEST_RESULTS=""
PASSED_FUNCTIONS=0
FAILED_FUNCTIONS=0

# Function names mapping
get_function_name() {
    case "$1" in
        "test_knowledge_base_manager.sh") echo "Knowledge Base Manager (RAG)" ;;
        "test_knowledge_base_manager_es.sh") echo "Knowledge Base Manager (ES)" ;;
        "test_profile_manager.sh") echo "Profile Manager (RAG)" ;;
        "test_profile_manager_es.sh") echo "Profile Manager (ES)" ;;
        *) echo "Unknown Function" ;;
    esac
}

# Utility functions
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                    $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

print_section() {
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

run_function_test() {
    local test_file="$1"
    local function_name=$(get_function_name "$test_file")
    local log_file="$LOG_DIR/${test_file%.sh}_${TIMESTAMP}.log"
    
    echo ""
    print_section "Testing: $function_name"
    echo -e "${YELLOW}Log file: $log_file${NC}"
    echo ""
    
    # Run the test and capture output
    if "$SCRIPT_DIR/$test_file" > "$log_file" 2>&1; then
        echo -e "${GREEN}✅ $function_name: ALL TESTS PASSED${NC}"
        TEST_RESULTS="$TEST_RESULTS$test_file:PASSED,"
        ((PASSED_FUNCTIONS++))
        
        # Show summary from log
        if grep -q "TEST SUMMARY" "$log_file"; then
            echo -e "${CYAN}Test Summary:${NC}"
            grep -A 3 "TEST SUMMARY" "$log_file" | tail -n +2
        fi
    else
        echo -e "${RED}❌ $function_name: SOME TESTS FAILED${NC}"
        TEST_RESULTS="$TEST_RESULTS$test_file:FAILED,"
        ((FAILED_FUNCTIONS++))
        
        # Show error summary
        echo -e "${RED}Error Summary:${NC}"
        if grep -q "FAILED" "$log_file"; then
            grep "FAILED" "$log_file" | tail -n 5
        fi
        echo -e "${YELLOW}Check log file for details: $log_file${NC}"
    fi
}

# Main execution
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Cloud Functions Test Suite       ║${NC}"
echo -e "${BLUE}║                    Master Test Runner                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

print_header "COMPREHENSIVE INTEGRATION TESTS"
echo -e "${YELLOW}Testing all 4 cloud functions with complete coverage:${NC}"
echo -e "${CYAN}• Knowledge Base Manager (RAG)${NC}"
echo -e "${CYAN}• Knowledge Base Manager (ES)${NC}"
echo -e "${CYAN}• Profile Manager (RAG)${NC}"
echo -e "${CYAN}• Profile Manager (ES)${NC}"
echo ""

print_header "TEST EXECUTION"

# Run tests for each function
for test_file in test_knowledge_base_manager.sh test_knowledge_base_manager_es.sh test_profile_manager.sh test_profile_manager_es.sh; do
    run_function_test "$test_file"
done

# Final Results
echo ""
print_header "FINAL RESULTS"

echo -e "${BLUE}Functions Tested: $TOTAL_FUNCTIONS${NC}"
echo -e "${GREEN}✅ Passed: $PASSED_FUNCTIONS${NC}"
echo -e "${RED}❌ Failed: $FAILED_FUNCTIONS${NC}"
echo ""

echo -e "${CYAN}Detailed Results:${NC}"
for test_file in test_knowledge_base_manager.sh test_knowledge_base_manager_es.sh test_profile_manager.sh test_profile_manager_es.sh; do
    function_name=$(get_function_name "$test_file")
    
    if echo "$TEST_RESULTS" | grep -q "$test_file:PASSED"; then
        echo -e "${GREEN}✅ $function_name${NC}"
    else
        echo -e "${RED}❌ $function_name${NC}"
    fi
done

echo ""
echo -e "${CYAN}Log Files:${NC}"
echo -e "${YELLOW}All test logs saved to: $LOG_DIR/${NC}"
ls -la "$LOG_DIR"/*_${TIMESTAMP}.log 2>/dev/null || echo "No log files found"

# Overall status
echo ""
if [ $FAILED_FUNCTIONS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           🎉 ALL FUNCTIONS WORKING PERFECTLY! 🎉         ║${NC}"
    echo -e "${GREEN}║                                                              ║${NC}"
    echo -e "${GREEN}║  All cloud functions are fully operational and ready      ║${NC}"
    echo -e "${GREEN}║  for production deployment.                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║               ⚠️  SOME FUNCTIONS NEED FIXING ⚠️            ║${NC}"
    echo -e "${RED}║                                                              ║${NC}"
    echo -e "${RED}║  Please review the failed tests and fix the issues         ║${NC}"
    echo -e "${RED}║  before proceeding with deployment.                        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
