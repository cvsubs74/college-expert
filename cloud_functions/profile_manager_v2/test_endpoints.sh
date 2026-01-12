#!/bin/bash
# Profile Manager V2 Test Suite
BASE_URL="https://profile-manager-v2-pfnwjfp26a-ue.a.run.app"
TEST_USER="test-v2@example.com"
TEST_UNI="stanford_university"

echo "======================================"
echo "Profile Manager V2 - Test Suite"
echo "======================================"
echo ""

test_count=0
pass_count=0

test() {
    test_count=$((test_count + 1))
    echo "[TEST $test_count] $1"
    response=$(eval "$2" 2>/dev/null)
    echo "Response: $response"
    if echo "$response" | grep -q "$3"; then
        echo "✅ PASS"
        pass_count=$((pass_count + 1))
    else
        echo "❌ FAIL"
    fi
    echo ""
}

# Test 1: Health
test "Health Check" \
    "curl -s $BASE_URL/health" \
    'healthy'

# Test 2: Get Credits
test "Get Credits" \
    "curl -s -X POST $BASE_URL/get-credits -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\"}'" \
    'credits_remaining'

# Test 3: Add to List
test "Add to List" \
    "curl -s -X POST $BASE_URL/add-to-list -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"university_name\":\"Stanford\"}'" \
    'success'

# Test 4: Get List
test "Get List" \
    "curl -s -X POST $BASE_URL/get-list -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\"}'" \
    'Stanford'

# Test 5: Update List
test "Update List Item"  \
    "curl -s -X POST $BASE_URL/update-list-item -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"category\":\"target\"}'" \
    'success'

# Test 6: Get Essay Drafts
test "Get Essay Drafts" \
    "curl -s -X POST $BASE_URL/get-essay-drafts -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" \
    'success'

# Test 7: Generate Starters
echo "[TEST $((test_count + 1))] Generate Essay Starters (may take 30s)"
test "Generate Starters" \
    "curl -s -X POST $BASE_URL/generate-essay-starters -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"prompt_text\":\"Why Stanford?\"}'" \
    'starters'

# Test 8: Remove from List
test "Remove from List" \
    "curl -s -X POST $BASE_URL/remove-from-list -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" \
    'success'

echo "======================================"
echo "Total: $test_count | Passed: $pass_count | Failed: $((test_count - pass_count))"
echo "Pass Rate: $(echo "scale=1; $pass_count * 100 / $test_count" | bc)%"
