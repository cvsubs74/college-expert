#!/bin/bash
# Profile Manager V2 - COMPREHENSIVE Test Suite
# Tests ALL 28 endpoints

BASE_URL="https://profile-manager-v2-pfnwjfp26a-ue.a.run.app"
TEST_USER="comprehensive-test@example.com"
TEST_UNI="mit"
TEST_FILE="test_profile.txt"

echo "=========================================="
echo "Profile Manager V2 - COMPREHENSIVE TESTS"
echo "Testing ALL 28 Endpoints"
echo "=========================================="
echo ""

test_count=0
pass_count=0

test() {
    test_count=$((test_count + 1))
    printf "[%d] %s\n" "$test_count" "$1"
    response=$(eval "$2" 2>/dev/null)
    echo "Response: ${response:0:100}..."
    if echo "$response" | grep -q "$3"; then
        echo "✅ PASS"
        pass_count=$((pass_count + 1))
    else
        echo "❌ FAIL"
    fi
    echo ""
}

# Create test file
echo "Student Profile
Name: Test Student  
GPA: 4.0
SAT: 1500" > /tmp/$TEST_FILE

echo "=== CORE (2) ==="
test "Health" "curl -s $BASE_URL/health" 'healthy'
test "Search Empty" "curl -s -X POST $BASE_URL/search -H 'Content-Type: application/json' -d '{\"user_id\":\"$TEST_USER\"}'" 'success'

echo "=== PROFILE FILES (4) ==="
test "Upload" "curl -s -X POST $BASE_URL/upload-profile -H 'X-User-Email: $TEST_USER' -F 'file=@/tmp/$TEST_FILE'" 'success'
test "List Files" "curl -s '$BASE_URL/list-profiles?user_email=$TEST_USER'" 'test_profile'
test "Search With Data" "curl -s -X POST $BASE_URL/search -H 'Content-Type: application/json' -d '{\"user_id\":\"$TEST_USER\"}'" 'Test Student'
test "Download" "curl -s '$BASE_URL/download-document?user_email=$TEST_USER&filename=$TEST_FILE'" 'Student'

echo "=== COLLEGE LIST (4) ==="
test "Add to List" "curl -s -X POST $BASE_URL/add-to-list -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"university_name\":\"MIT\"}'" 'success'
test "Get List" "curl -s -X POST $BASE_URL/get-list -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\"}'" 'MIT'
test "Update Item" "curl -s -X POST $BASE_URL/update-list-item -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"category\":\"reach\"}'" 'success'

echo "=== FIT ANALYSIS (4 + 1 slow) ==="
echo "[10] Compute Fit - LLM call may take 30-60s"
test "Compute Fit" "curl -s -m 120 -X POST $BASE_URL/compute-single-fit -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" 'fit_analysis'
test "Get Fit" "curl -s -X POST $BASE_URL/get-fit-analysis -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" 'fit_category'
test "Get All Fits" "curl -s -X POST $BASE_URL/get-all-fits -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\"}'" 'mit'
test "Save Fit" "curl -s -X POST $BASE_URL/save-fit-analysis -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"fit_analysis\":{\"fit_category\":\"REACH\"}}'" 'success'

echo "=== CREDITS (4) ==="
test "Get Credits" "curl -s -X POST $BASE_URL/get-credits -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\"}'" 'credits_remaining'
test "Check Credits" "curl -s -X POST $BASE_URL/check-credits -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"credits_required\":1}'" 'available'
test "Add Credits" "curl -s -X POST $BASE_URL/add-credits -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"credits\":10,\"source\":\"test\"}'" 'success'
test "Deduct Credit" "curl -s -X POST $BASE_URL/deduct-credit -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"operation\":\"test\",\"credits\":1}'" 'success'

echo "=== AI CHAT (1) ==="
test "Profile Chat" "curl -s -X POST $BASE_URL/profile-chat -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"query\":\"What is my GPA?\"}'" 'response'

echo "=== ESSAY COPILOT (7 + 1 slow) ==="
echo "[19] Generate Starters - LLM call may take 20-30s"
test "Generate Starters" "curl -s -m 60 -X POST $BASE_URL/generate-essay-starters -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"prompt_text\":\"Why MIT?\"}'" 'starters'
test "Get Context" "curl -s -X POST $BASE_URL/get-starter-context -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" 'success'
test "Copilot Suggest" "curl -s -X POST $BASE_URL/copilot-suggest -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"current_text\":\"I want\"}'" 'suggestion'
test "Save Draft" "curl -s -X POST $BASE_URL/save-essay-draft -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"prompt_index\":0,\"prompt_text\":\"Why?\",\"draft_text\":\"MIT is great\",\"version\":1}'" 'success'
test "Get Drafts" "curl -s -X POST $BASE_URL/get-essay-drafts -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" 'drafts'
test "Draft Feedback" "curl -s -X POST $BASE_URL/draft-feedback -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"draft_text\":\"MIT is great\",\"prompt_text\":\"Why?\"}'" 'feedback'
test "Essay Chat" "curl -s -X POST $BASE_URL/essay-chat -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\",\"message\":\"Help me\"}'" 'response'

echo "=== CLEANUP (3) ==="
test "Delete Fit" "curl -s -X POST $BASE_URL/delete-fit-analysis -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" 'success'
test "Remove List" "curl -s -X POST $BASE_URL/remove-from-list -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"university_id\":\"$TEST_UNI\"}'" 'success'
test "Delete Profile" "curl -s -X POST $BASE_URL/delete-profile -H 'Content-Type: application/json' -d '{\"user_email\":\"$TEST_USER\",\"filename\":\"$TEST_FILE\"}'" 'success'

rm -f /tmp/$TEST_FILE

echo "=========================================="
echo "RESULTS: $pass_count/$test_count passed"
echo "Pass Rate: $(echo "scale=1; $pass_count * 100 / $test_count" | bc)%"
echo "=========================================="
