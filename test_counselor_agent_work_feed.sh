#!/bin/bash

# Integration test for the counselor_agent /work-feed endpoint.
# Runs against the deployed Cloud Function. Override COUNSELOR_AGENT_URL
# and TEST_USER_EMAIL via env to point at a different deployment or user.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COUNSELOR_AGENT_URL=${COUNSELOR_AGENT_URL:-"https://us-east1-college-counselling-478115.cloudfunctions.net/counselor-agent"}
TEST_USER_EMAIL=${TEST_USER_EMAIL:-"sarah.johnson@email.com"}

TOTAL=0
PASSED=0
FAILED=0

assert_status() {
    local name="$1" url="$2" expected="$3"
    ((TOTAL++))
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name (HTTP $actual)"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $name (expected $expected, got $actual)"
        echo -e "  URL: $url"
        ((FAILED++))
    fi
}

assert_json_field() {
    local name="$1" url="$2" jq_filter="$3" expected="$4"
    ((TOTAL++))
    local body actual
    body=$(curl -s "$url")
    actual=$(echo "$body" | jq -r "$jq_filter" 2>/dev/null || echo "<jq-error>")
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name ($jq_filter == $expected)"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $name (expected $expected, got $actual)"
        echo -e "  Body: $(echo "$body" | head -c 200)"
        ((FAILED++))
    fi
}

echo -e "${BLUE}=== counselor_agent /work-feed integration tests ===${NC}"
echo "Endpoint: $COUNSELOR_AGENT_URL"
echo "Test user: $TEST_USER_EMAIL"
echo ""

# --- Validation errors ---

assert_status \
    "missing user_email returns 400" \
    "${COUNSELOR_AGENT_URL}/work-feed" \
    "400"

assert_status \
    "non-integer limit returns 400" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=abc" \
    "400"

# --- Happy path ---

assert_status \
    "valid call returns 200" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=8" \
    "200"

assert_json_field \
    "response has success=true" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=8" \
    ".success" \
    "true"

assert_json_field \
    "response has items array" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=8" \
    ".items | type" \
    "array"

assert_json_field \
    "response has total field" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=8" \
    ".total | type" \
    "number"

# --- Limit clamping ---

assert_json_field \
    "limit=1 returns at most 1 item" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=1" \
    ".items | length <= 1" \
    "true"

assert_json_field \
    "limit=999 is clamped to <=50 items" \
    "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=999" \
    ".items | length <= 50" \
    "true"

# --- Item shape (only if at least one item exists) ---

ITEM_COUNT=$(curl -s "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=50" | jq -r '.items | length')
if [ "$ITEM_COUNT" != "0" ] && [ "$ITEM_COUNT" != "null" ]; then
    assert_json_field \
        "every item has a source field of expected type" \
        "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=50" \
        '[.items[].source] | all(. as $s | ["roadmap_task","essay","scholarship","college_deadline"] | index($s) != null)' \
        "true"

    assert_json_field \
        "every item has an id" \
        "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=50" \
        '[.items[].id | type] | all(. == "string")' \
        "true"

    assert_json_field \
        "items with due_date are sorted ascending" \
        "${COUNSELOR_AGENT_URL}/work-feed?user_email=${TEST_USER_EMAIL}&limit=50" \
        '[.items[] | select(.due_date != null) | .due_date] as $dates | $dates == ($dates | sort)' \
        "true"
else
    echo -e "${YELLOW}note: test user has no items in any source; shape checks skipped${NC}"
fi

echo ""
echo "Results: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
[ "$FAILED" -eq 0 ]
