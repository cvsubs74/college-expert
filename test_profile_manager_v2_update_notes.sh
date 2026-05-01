#!/bin/bash

# Integration test for the profile_manager_v2 /update-notes endpoint.
# Runs against the deployed Cloud Function. Override PROFILE_MANAGER_V2_URL
# and TEST_USER_EMAIL via env to point at a different deployment or user.
#
# Note: validation paths are tested unconditionally. The 404 path is tested
# against a guaranteed-missing item_id. The success round-trip is NOT tested
# here because it would require deterministic seed data; that's covered by
# manual verification on a real user with items.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROFILE_MANAGER_V2_URL=${PROFILE_MANAGER_V2_URL:-"https://us-east1-college-counselling-478115.cloudfunctions.net/profile-manager-v2"}
TEST_USER_EMAIL=${TEST_USER_EMAIL:-"sarah.johnson@email.com"}

TOTAL=0
PASSED=0
FAILED=0

# Asserts the HTTP status code returned by a POST with a JSON body.
assert_status() {
    local name="$1" body="$2" expected="$3"
    TOTAL=$((TOTAL + 1))
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST -H "Content-Type: application/json" \
        -d "$body" \
        "${PROFILE_MANAGER_V2_URL}/update-notes")
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name (HTTP $actual)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $name (expected $expected, got $actual)"
        echo -e "  Body sent: $body"
        FAILED=$((FAILED + 1))
    fi
}

# Asserts a JSON field on the response equals an expected value.
assert_json_field() {
    local name="$1" body="$2" jq_filter="$3" expected="$4"
    TOTAL=$((TOTAL + 1))
    local resp actual
    resp=$(curl -s \
        -X POST -H "Content-Type: application/json" \
        -d "$body" \
        "${PROFILE_MANAGER_V2_URL}/update-notes")
    actual=$(echo "$resp" | jq -r "$jq_filter" 2>/dev/null || echo "<jq-error>")
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name ($jq_filter == $expected)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $name (expected $expected, got $actual)"
        echo -e "  Response: $(echo "$resp" | head -c 200)"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}=== profile_manager_v2 /update-notes integration tests ===${NC}"
echo "Endpoint: ${PROFILE_MANAGER_V2_URL}/update-notes"
echo "Test user: $TEST_USER_EMAIL"
echo ""

# --- Validation errors (400) ---

assert_status \
    "missing user_email returns 400" \
    "$(jq -nc --arg c roadmap_tasks --arg id t1 '{collection: $c, item_id: $id, notes: "x"}')" \
    "400"

assert_status \
    "missing collection returns 400" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" --arg id t1 '{user_email: $u, item_id: $id, notes: "x"}')" \
    "400"

assert_status \
    "missing item_id returns 400" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" --arg c roadmap_tasks '{user_email: $u, collection: $c, notes: "x"}')" \
    "400"

assert_status \
    "invalid collection name returns 400" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, collection: "users", item_id: "x", notes: "y"}')" \
    "400"

assert_status \
    "non-string notes returns 400" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, collection: "roadmap_tasks", item_id: "x", notes: 123}')" \
    "400"

# Build a 50001-char string to exceed the 50000 cap.
LONG_NOTES=$(python3 -c "print('a' * 50001, end='')")
assert_status \
    "oversize notes (50001 chars) returns 400" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" --arg n "$LONG_NOTES" '{user_email: $u, collection: "roadmap_tasks", item_id: "x", notes: $n}')" \
    "400"

# --- 404: valid input but no such item ---

# This item_id is intentionally bizarre to guarantee a miss even on real users.
GUARANTEED_MISSING_ID="__never_existed_$(date +%s)_$RANDOM"

assert_status \
    "unknown item_id returns 404" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" --arg id "$GUARANTEED_MISSING_ID" '{user_email: $u, collection: "roadmap_tasks", item_id: $id, notes: "test"}')" \
    "404"

assert_json_field \
    "404 response has success=false" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" --arg id "$GUARANTEED_MISSING_ID" '{user_email: $u, collection: "roadmap_tasks", item_id: $id, notes: "test"}')" \
    ".success" \
    "false"

# --- Each whitelisted collection accepts a 404 (proves dispatcher reaches all five) ---

for COLL in roadmap_tasks essay_tracker scholarship_tracker college_list aid_packages; do
    assert_status \
        "collection=$COLL with missing id returns 404 (not 400)" \
        "$(jq -nc --arg u "$TEST_USER_EMAIL" --arg c "$COLL" --arg id "$GUARANTEED_MISSING_ID" '{user_email: $u, collection: $c, item_id: $id, notes: "x"}')" \
        "404"
done

echo ""
echo "Results: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
[ "$FAILED" -eq 0 ]
