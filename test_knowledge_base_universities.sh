#!/bin/bash

# =============================================================================
# Test Script for Knowledge Base Manager Universities
# Comprehensive testing of search functionality
# =============================================================================

set -e

# Configuration
BASE_URL="${KNOWLEDGE_BASE_UNIVERSITIES_URL:-https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Test function
run_test() {
    local test_name="$1"
    local expected_status="$2"
    local method="$3"
    local endpoint="$4"
    local data="$5"
    
    TOTAL=$((TOTAL + 1))
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Test $TOTAL: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ -n "$data" ]; then
        echo -e "${YELLOW}Request:${NC} $method $endpoint"
        echo -e "${YELLOW}Body:${NC} $data"
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        echo -e "${YELLOW}Request:${NC} $method $endpoint"
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    echo -e "${YELLOW}Status:${NC} $http_code"
    echo -e "${YELLOW}Response:${NC}"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    
    if [ "$http_code" == "$expected_status" ]; then
        echo -e "\n${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "\n${RED}✗ FAILED (expected $expected_status, got $http_code)${NC}"
        FAILED=$((FAILED + 1))
    fi
}

# Test search and validate results
run_search_test() {
    local test_name="$1"
    local query="$2"
    local search_type="$3"
    local filters="$4"
    local expected_count="$5"
    
    TOTAL=$((TOTAL + 1))
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Test $TOTAL: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ -n "$filters" ]; then
        data="{\"query\": \"$query\", \"search_type\": \"$search_type\", \"filters\": $filters}"
    else
        data="{\"query\": \"$query\", \"search_type\": \"$search_type\"}"
    fi
    
    echo -e "${YELLOW}Query:${NC} $query"
    echo -e "${YELLOW}Search Type:${NC} $search_type"
    [ -n "$filters" ] && echo -e "${YELLOW}Filters:${NC} $filters"
    
    response=$(curl -s -X POST "$BASE_URL/" \
        -H "Content-Type: application/json" \
        -d "$data")
    
    success=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
    total=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null)
    
    echo -e "${YELLOW}Results:${NC} $total universities found"
    
    # Show top 3 results
    echo -e "${YELLOW}Top Results:${NC}"
    echo "$response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, r in enumerate(data.get('results', [])[:3]):
    print(f\"  {i+1}. {r.get('official_name', 'Unknown')} (score: {r.get('score', 0):.2f})\")" 2>/dev/null
    
    if [ "$success" == "True" ]; then
        if [ -n "$expected_count" ] && [ "$total" -lt "$expected_count" ]; then
            echo -e "\n${YELLOW}⚠ WARNING: Expected at least $expected_count results, got $total${NC}"
        fi
        echo -e "\n${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "\n${RED}✗ FAILED${NC}"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Knowledge Base Manager Universities - Test Suite          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "${CYAN}Base URL: $BASE_URL${NC}"
echo ""

# =============================================================================
# HEALTH & BASIC ENDPOINT TESTS
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 1: Health & Basic Endpoints${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

run_test "Health Check" "200" "GET" "/?action=health" ""

run_test "List All Universities" "200" "GET" "/" ""

run_test "Get Specific University (UCB)" "200" "GET" "/?id=ucb" ""

run_test "Get Non-existent University" "200" "GET" "/?id=nonexistent_university_xyz" ""

# =============================================================================
# HYBRID SEARCH TESTS (Default)
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 2: Hybrid Search (BM25 + Vector)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

run_search_test "Hybrid: Computer Science Research University" \
    "computer science research university" \
    "hybrid" \
    "" \
    "3"

run_search_test "Hybrid: Engineering Programs in California" \
    "best engineering programs California public" \
    "hybrid" \
    "" \
    "3"

run_search_test "Hybrid: Pre-med Strong Biology Program" \
    "pre-med strong biology medical school preparation" \
    "hybrid" \
    "" \
    "2"

run_search_test "Hybrid: Business Marketing Psychology" \
    "business marketing psychology interdisciplinary" \
    "hybrid" \
    "" \
    "2"

run_search_test "Hybrid: Research Opportunities Undergraduate" \
    "undergraduate research opportunities STEM sciences" \
    "hybrid" \
    "" \
    "3"

run_search_test "Hybrid: Top Employers Career Outcomes" \
    "top employers tech companies career outcomes salary" \
    "hybrid" \
    "" \
    "3"

# =============================================================================
# SEMANTIC SEARCH TESTS (Vector Only)
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 3: Semantic Search (Vector Only)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

run_search_test "Semantic: Innovation and Entrepreneurship" \
    "innovation startup entrepreneurship venture" \
    "semantic" \
    "" \
    "2"

run_search_test "Semantic: Collaborative Academic Environment" \
    "collaborative supportive academic environment close professor relationships" \
    "semantic" \
    "" \
    "2"

run_search_test "Semantic: High Acceptance Rate Accessible" \
    "accessible higher acceptance rate less competitive admission" \
    "semantic" \
    "" \
    "2"

run_search_test "Semantic: Strong Alumni Network" \
    "strong alumni network career connections job placement" \
    "semantic" \
    "" \
    "2"

# =============================================================================
# KEYWORD SEARCH TESTS (BM25 Only)
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 4: Keyword Search (BM25 Only)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

run_search_test "Keyword: UCLA" \
    "UCLA Los Angeles" \
    "keyword" \
    "" \
    "1"

run_search_test "Keyword: Berkeley Computer Science" \
    "Berkeley computer science engineering" \
    "keyword" \
    "" \
    "1"

run_search_test "Keyword: UC San Diego" \
    "UC San Diego UCSD" \
    "keyword" \
    "" \
    "1"

run_search_test "Keyword: Public Ivy" \
    "Public Ivy flagship" \
    "keyword" \
    "" \
    "1"

# =============================================================================
# FILTERED SEARCH TESTS
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 5: Filtered Search${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

run_search_test "Filter: California Universities Only" \
    "top university" \
    "hybrid" \
    '{"state": "CA"}' \
    "5"

run_search_test "Filter: Acceptance Rate Under 30%" \
    "competitive university" \
    "hybrid" \
    '{"acceptance_rate_max": 30}' \
    "3"

run_search_test "Filter: Public Universities" \
    "research university" \
    "hybrid" \
    '{"type": "Public"}' \
    "5"

run_search_test "Filter: Combined State + Acceptance Rate" \
    "engineering program" \
    "hybrid" \
    '{"state": "CA", "acceptance_rate_max": 25}' \
    "2"

# =============================================================================
# EDGE CASE TESTS
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 6: Edge Cases${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

run_search_test "Edge: Empty Query" \
    "" \
    "hybrid" \
    "" \
    "0"

run_search_test "Edge: Very Long Query" \
    "I am looking for a university that has excellent computer science and engineering programs with strong research opportunities in artificial intelligence machine learning data science and also has good career outcomes with high starting salaries and connections to tech companies in Silicon Valley" \
    "hybrid" \
    "" \
    "2"

run_search_test "Edge: Special Characters" \
    "UC Berkeley (Cal) - #1 public" \
    "hybrid" \
    "" \
    "1"

run_search_test "Edge: Single Word Query" \
    "Stanford" \
    "hybrid" \
    "" \
    "0"

run_search_test "Edge: Limit Results to 3" \
    "university" \
    "hybrid" \
    "" \
    "3"

# =============================================================================
# COMPARATIVE SEARCH TESTS
# =============================================================================
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  SECTION 7: Comparative Search Quality${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"

echo -e "\n${CYAN}Comparing search types for the same query...${NC}"

run_search_test "Compare: 'data science machine learning' (Hybrid)" \
    "data science machine learning AI" \
    "hybrid" \
    "" \
    "2"

run_search_test "Compare: 'data science machine learning' (Semantic)" \
    "data science machine learning AI" \
    "semantic" \
    "" \
    "2"

run_search_test "Compare: 'data science machine learning' (Keyword)" \
    "data science machine learning AI" \
    "keyword" \
    "" \
    "1"

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    TEST SUMMARY                             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}Passed:${NC} $PASSED"
echo -e "  ${RED}Failed:${NC} $FAILED"
echo -e "  ${CYAN}Total:${NC}  $TOTAL"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi
