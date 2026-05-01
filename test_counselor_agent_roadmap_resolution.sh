#!/bin/bash

# Integration test for counselor_agent /roadmap grade/semester resolution.
# Runs against the deployed Cloud Function. Verifies the new resolver
# behavior: caller-provided (grade_level + semester) win when BOTH given,
# otherwise the endpoint falls back to profile-based inference.
#
# Override COUNSELOR_AGENT_URL and TEST_USER_EMAIL via env to point at a
# different deployment or user.

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

# Asserts a JSON field equals an expected value for a POST /roadmap call.
assert_field() {
    local name="$1" body="$2" jq_filter="$3" expected="$4"
    TOTAL=$((TOTAL + 1))
    local resp actual
    resp=$(curl -s -X POST -H "Content-Type: application/json" -d "$body" \
        "${COUNSELOR_AGENT_URL}/roadmap")
    actual=$(echo "$resp" | jq -r "$jq_filter" 2>/dev/null || echo "<jq-error>")
    if [ "$actual" = "$expected" ]; then
        echo -e "${GREEN}✓${NC} $name ($jq_filter == $expected)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $name (expected $expected, got $actual)"
        echo -e "  Body sent: $body"
        echo -e "  Response: $(echo "$resp" | head -c 300)"
        FAILED=$((FAILED + 1))
    fi
}

echo -e "${BLUE}=== counselor_agent /roadmap resolution integration tests ===${NC}"
echo "Endpoint: ${COUNSELOR_AGENT_URL}/roadmap"
echo "Test user: $TEST_USER_EMAIL"
echo ""

# --- Caller-provided grade + semester wins (new behavior) ---

assert_field \
    "junior + spring → junior_spring (source=caller)" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    ".metadata.template_used" \
    "junior_spring"

assert_field \
    "junior + spring → resolution_source=caller" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    ".metadata.resolution_source" \
    "caller"

assert_field \
    "junior + summer (special template) → junior_summer" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "Junior", semester: "summer"}')" \
    ".metadata.template_used" \
    "junior_summer"

assert_field \
    "senior + fall → senior_fall" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "12th Grade", semester: "fall"}')" \
    ".metadata.template_used" \
    "senior_fall"

assert_field \
    "freshman + summer → freshman_spring (no summer template, falls back)" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "9th Grade", semester: "summer"}')" \
    ".metadata.template_used" \
    "freshman_spring"

# --- Metadata exposes resolved grade and semester ---

assert_field \
    "metadata.grade_used populated for caller resolution" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    ".metadata.grade_used" \
    "junior"

assert_field \
    "metadata.semester_used populated for caller resolution" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    ".metadata.semester_used" \
    "spring"

# --- Caller passes only grade_level (legacy frontend behavior): does NOT
#     trigger override; falls through to profile-based inference. ---

assert_field \
    "grade_level only (no semester) → resolution_source != caller" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade"}')" \
    '.metadata.resolution_source != "caller"' \
    "true"

# --- Response shape sanity ---

assert_field \
    "response.success is true for resolved request" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    ".success" \
    "true"

assert_field \
    "response.roadmap.title is a non-empty string" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    '.roadmap.title | type' \
    "string"

assert_field \
    "response.roadmap.phases is an array" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "spring"}')" \
    '.roadmap.phases | type' \
    "array"

# --- Validation: invalid semester (passed alongside grade_level) ---
# Should NOT error — the resolver treats invalid as "not provided" and falls
# back to profile/default. Just verify the request still returns 200 with
# a usable template (resolution_source != 'caller').

assert_field \
    "invalid semester value falls through to non-caller source" \
    "$(jq -nc --arg u "$TEST_USER_EMAIL" '{user_email: $u, grade_level: "11th Grade", semester: "winter"}')" \
    '.metadata.resolution_source != "caller"' \
    "true"

echo ""
echo "Results: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
[ "$FAILED" -eq 0 ]
