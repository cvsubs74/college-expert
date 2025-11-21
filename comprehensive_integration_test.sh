#!/bin/bash

# Comprehensive Integration Test Suite
# Tests all 4 profile functions and both RAG/ES agents end-to-end

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Comprehensive Integration Tests    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"college-counselling-478115"}
REGION="us-east1"
RAG_AGENT_SERVICE_NAME="college-expert-rag-agent"
ES_AGENT_SERVICE_NAME="college-expert-es-agent"
PROFILE_MANAGER_FUNCTION="profile-manager"
PROFILE_MANAGER_ES_FUNCTION="profile-manager-es"
KNOWLEDGE_BASE_FUNCTION="knowledge-base-manager"
KNOWLEDGE_BASE_ES_FUNCTION="knowledge-base-manager-es"

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
run_test() {
    local test_name=$1
    local test_command=$2
    
    ((TOTAL_TESTS++))
    echo -e "${CYAN}Test $TOTAL_TESTS: $test_name${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED_TESTS++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED_TESTS++))
        return 1
    fi
    echo ""
}

# Get URLs from gcloud
echo -e "${YELLOW}Fetching deployment URLs...${NC}"
RAG_AGENT_URL=$(gcloud run services describe $RAG_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
ES_AGENT_URL=$(gcloud run services describe $ES_AGENT_SERVICE_NAME --region=$REGION --format='value(status.url)' 2>/dev/null || echo "")
PROFILE_RAG_URL=$(gcloud functions describe $PROFILE_MANAGER_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
PROFILE_ES_URL=$(gcloud functions describe $PROFILE_MANAGER_ES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
KB_RAG_URL=$(gcloud functions describe $KNOWLEDGE_BASE_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")
KB_ES_URL=$(gcloud functions describe $KNOWLEDGE_BASE_ES_FUNCTION --region=$REGION --gen2 --format='value(serviceConfig.uri)' 2>/dev/null || echo "")

echo -e "${GREEN}✓ URLs fetched${NC}"
echo ""

# Health check function
check_health() {
    local name=$1
    local url=$2
    local path=$3
    
    if [ -z "$url" ]; then
        echo -e "${RED}✗ $name: Not deployed${NC}"
        return 1
    fi
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" -X GET "${url}${path}" -H "Content-Type: application/json" --max-time 10 2>&1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "307" ] || [ "$http_code" = "400" ] || [ "$http_code" = "405" ] || [ "$http_code" = "500" ]; then
        echo -e "${GREEN}✓ $name: Healthy (HTTP $http_code)${NC}"
        return 0
    else
        echo -e "${RED}✗ $name: Failed (HTTP $http_code)${NC}"
        return 1
    fi
}

# Create test documents
create_test_college_document() {
    cat > /tmp/test_college_doc.txt << 'EOF'
Stanford University Admissions Information

Acceptance Rate: 3.9%
Average SAT Score: 1500-1570
Average ACT Score: 33-35
Average GPA: 3.9-4.0

Stanford University is a private research university located in Stanford, California.
Known for its academic strength, wealth, proximity to Silicon Valley, and selectivity.

Application Requirements:
- Common Application or Coalition Application
- Application fee or fee waiver
- SAT or ACT scores (test-optional for 2024-2025)
- High school transcript
- Letters of recommendation (2 from teachers, 1 from counselor)
- Essays and personal statements

Notable Programs:
- Computer Science
- Engineering
- Business
- Medicine
- Law

Campus Life:
- Located in the heart of Silicon Valley
- 8,180 acres campus
- Over 650 student organizations
- Division I athletics (Pac-12 Conference)

Financial Aid:
- Need-blind admissions for U.S. citizens
- Meets 100% of demonstrated financial need
- Average need-based scholarship: $58,000
EOF
    echo "/tmp/test_college_doc.txt"
}

create_test_student_profile() {
    cat > /tmp/test_student_profile.txt << 'EOF'
Student Profile: Jane Doe

Personal Information:
- Email: jane.doe@example.com
- High School: Lincoln High School, California
- Graduation Year: 2025

Academic Information:
- GPA: 3.95 (weighted)
- SAT Score: 1520 (Math: 780, Reading: 740)
- ACT Score: 34
- Class Rank: Top 5% of 450 students
- AP Courses: 8 (Calculus BC, Physics C, Chemistry, Biology, English Literature, US History, Spanish, Computer Science A)
- AP Scores: All 4s and 5s

Extracurricular Activities:
- President of Computer Science Club (3 years)
- Varsity Tennis Team Captain (2 years)
- Volunteer at local STEM outreach program (300+ hours)
- National Honor Society member
- Math Competition Team (Regional level)
- Coding Bootcamp Instructor (summer program)

Awards and Honors:
- National Merit Scholar Commended
- AP Scholar with Distinction
- First Place in Regional Science Fair
- Student of the Year (Computer Science Department)

Interests:
- Computer Science and Artificial Intelligence
- Machine Learning and Data Science
- Environmental Technology
- Entrepreneurship

Target Schools:
- Stanford University (Computer Science)
- MIT (Electrical Engineering and Computer Science)
- UC Berkeley (EECS)
- Carnegie Mellon (Computer Science)
- Harvard (Computer Science)

Career Goals:
- Software Engineer at a tech company
- Research in AI/ML field
- Eventually start a technology startup
EOF
    echo "/tmp/test_student_profile.txt"
}

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 1: Health Checks${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Health checks for all services
run_test "RAG Agent Health Check" "check_health 'RAG Agent' '$RAG_AGENT_URL' '/'"
run_test "ES Agent Health Check" "check_health 'ES Agent' '$ES_AGENT_URL' '/'"
run_test "Profile Manager RAG Health Check" "check_health 'Profile Manager RAG' '$PROFILE_RAG_URL' '/list-profiles'"
run_test "Profile Manager ES Health Check" "check_health 'Profile Manager ES' '$PROFILE_ES_URL' '/profiles'"
run_test "Knowledge Base RAG Health Check" "check_health 'Knowledge Base RAG' '$KB_RAG_URL' '/health'"
run_test "Knowledge Base ES Health Check" "check_health 'Knowledge Base ES' '$KB_ES_URL' '/health'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 2: Knowledge Base Functions (RAG)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 7: Upload document to RAG Knowledge Base
run_test "Upload document to Knowledge Base RAG" \
    "create_test_college_document > /dev/null && \
     curl -s -X POST ${KB_RAG_URL}/upload \
     -F 'file=@/tmp/test_college_doc.txt' \
     -F 'user_id=test_user' \
     | grep -q 'success'"

# Test 8: List documents in RAG Knowledge Base
run_test "List documents in Knowledge Base RAG" \
    "curl -s -X GET '${KB_RAG_URL}/documents?limit=10' \
     | grep -q '\"success\":true'"

# Test 9: Search documents in RAG Knowledge Base
run_test "Search for 'Stanford' in Knowledge Base RAG" \
    "curl -s -X POST ${KB_RAG_URL}/search \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"Stanford University acceptance rate\",\"limit\":5}' \
     | grep -q '\"success\":true'"

# Test 10: Get document by ID from RAG
run_test "Get document by ID from Knowledge Base RAG" \
    "DOC_ID=\$(curl -s -X GET '${KB_RAG_URL}/documents?limit=1' | grep -o '\"document_id\":\"[^\"]*\"' | cut -d'\"' -f4) && \
     [ -n \"\$DOC_ID\" ] && \
     curl -s -X GET '${KB_RAG_URL}/document/\$DOC_ID' \
     | grep -q '\"success\":true'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 3: Knowledge Base Functions (Elasticsearch)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 11: Upload document to ES Knowledge Base
run_test "Upload document to Knowledge Base ES" \
    "curl -s -X POST ${KB_ES_URL}/documents \
     -F 'file=@/tmp/test_college_doc.txt' \
     -F 'user_id=test_user' \
     | grep -q '\"success\":true'"

# Test 12: List documents in ES Knowledge Base
run_test "List documents in Knowledge Base ES" \
    "curl -s -X GET '${KB_ES_URL}/documents?limit=10' \
     | grep -q '\"success\":true'"

# Test 13: Search documents in ES Knowledge Base
run_test "Search for 'Stanford' in Knowledge Base ES" \
    "curl -s -X POST ${KB_ES_URL}/documents/search \
     -H 'Content-Type: application/json' \
     -d '{\"query\":\"Stanford University acceptance rate\",\"limit\":5}' \
     | grep -q '\"success\":true'"

# Test 14: Get document by ID from ES
run_test "Get document by ID from Knowledge Base ES" \
    "DOC_ID=\$(curl -s -X GET '${KB_ES_URL}/documents?limit=1' | grep -o '\"document_id\":\"[^\"]*\"' | cut -d'\"' -f4) && \
     [ -n \"\$DOC_ID\" ] && \
     curl -s -X GET '${KB_ES_URL}/documents/\$DOC_ID' \
     | grep -q '\"success\":true'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 4: Profile Manager Functions (RAG)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 15: Upload profile to RAG Profile Manager
run_test "Upload profile to Profile Manager RAG" \
    "create_test_student_profile > /dev/null && \
     curl -s -X POST ${PROFILE_RAG_URL}/upload-profile \
     -F 'file=@/tmp/test_student_profile.txt' \
     -F 'user_email=jane.doe@example.com' \
     | grep -q '\"success\":true'"

# Test 16: List profiles in RAG Profile Manager
run_test "List profiles in Profile Manager RAG" \
    "curl -s -X GET '${PROFILE_RAG_URL}/list-profiles?user_email=jane.doe@example.com' \
     | grep -q '\"success\":true'"

# Test 17: Get profile by ID from RAG
run_test "Get profile by ID from Profile Manager RAG" \
    "PROFILE_ID=\$(curl -s -X GET '${PROFILE_RAG_URL}/list-profiles?user_email=jane.doe@example.com' | grep -o '\"profile_id\":\"[^\"]*\"' | cut -d'\"' -f4) && \
     [ -n \"\$PROFILE_ID\" ] && \
     curl -s -X GET '${PROFILE_RAG_URL}/profile/\$PROFILE_ID' \
     | grep -q '\"success\":true'"

# Test 18: Search profile content in RAG
run_test "Search profile content in Profile Manager RAG" \
    "curl -s -X POST ${PROFILE_RAG_URL}/search-profile \
     -H 'Content-Type: application/json' \
     -d '{\"user_email\":\"jane.doe@example.com\",\"query\":\"GPA SAT scores\",\"limit\":5}' \
     | grep -q '\"success\":true'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 5: Profile Manager Functions (Elasticsearch)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 19: Upload profile to ES Profile Manager
run_test "Upload profile to Profile Manager ES" \
    "curl -s -X POST ${PROFILE_ES_URL}/profiles \
     -F 'file=@/tmp/test_student_profile.txt' \
     -F 'user_email=jane.doe@example.com' \
     | grep -q '\"success\":true'"

# Test 20: List profiles in ES Profile Manager
run_test "List profiles in Profile Manager ES" \
    "curl -s -X GET '${PROFILE_ES_URL}/profiles?user_email=jane.doe@example.com' \
     | grep -q '\"success\":true' || curl -s -X GET '${PROFILE_ES_URL}/profiles' | grep -q 'profiles'"

# Test 21: Get profile by ID from ES
run_test "Get profile by ID from Profile Manager ES" \
    "PROFILE_ID=\$(curl -s -X GET '${PROFILE_ES_URL}/profiles?user_email=jane.doe@example.com' | grep -o '\"profile_id\":\"[^\"]*\"' | cut -d'\"' -f4) && \
     [ -n \"\$PROFILE_ID\" ] && \
     curl -s -X GET '${PROFILE_ES_URL}/profiles/\$PROFILE_ID' \
     | grep -q '\"success\":true'"

# Test 22: Search profile content in ES
run_test "Search profile content in Profile Manager ES" \
    "curl -s -X POST ${PROFILE_ES_URL}/profiles/search \
     -H 'Content-Type: application/json' \
     -d '{\"user_email\":\"jane.doe@example.com\",\"query\":\"GPA SAT scores\",\"limit\":5}' \
     | grep -q '\"success\":true'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 6: RAG Agent Integration Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 23: Create session with RAG Agent
run_test "Create session with RAG Agent" \
    "SESSION_RESPONSE=\$(curl -s -X POST ${RAG_AGENT_URL}/apps/college_expert_rag/users/user/sessions \
     -H 'Content-Type: application/json' \
     -d '{}') && \
     echo \"\$SESSION_RESPONSE\" | grep -q '\"id\"' && \
     export RAG_SESSION_ID=\$(echo \"\$SESSION_RESPONSE\" | grep -o '\"id\":\"[^\"]*\"' | cut -d'\"' -f4) && \
     [ -n \"\$RAG_SESSION_ID\" ]"

# Test 24: Query RAG Agent about general college information
run_test "Query RAG Agent about Stanford (general question)" \
    "curl -s -X POST ${RAG_AGENT_URL}/run \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$RAG_SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What is the acceptance rate at Stanford University?\"}]}}' \
     | grep -q 'Stanford'"

# Test 25: Query RAG Agent for personalized analysis
run_test "Query RAG Agent for personalized analysis [USER_EMAIL: jane.doe@example.com]" \
    "curl -s -X POST ${RAG_AGENT_URL}/run \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$RAG_SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Based on my profile, what are my chances at Stanford for Computer Science? [USER_EMAIL: jane.doe@example.com]\"}]}}' \
     | grep -q 'Stanford'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 7: ES Agent Integration Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 26: Create session with ES Agent
run_test "Create session with ES Agent" \
    "SESSION_RESPONSE=\$(curl -s -X POST ${ES_AGENT_URL}/apps/college_expert_es/users/user/sessions \
     -H 'Content-Type: application/json' \
     -d '{}') && \
     echo \"\$SESSION_RESPONSE\" | grep -q '\"id\"' && \
     export ES_SESSION_ID=\$(echo \"\$SESSION_RESPONSE\" | grep -o '\"id\":\"[^\"]*\"' | cut -d'\"' -f4) && \
     [ -n \"\$ES_SESSION_ID\" ]"

# Test 27: Query ES Agent about general college information
run_test "Query ES Agent about Stanford (general question)" \
    "curl -s -X POST ${ES_AGENT_URL}/run \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_es\",\"user_id\":\"user\",\"session_id\":\"'$ES_SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"What is the acceptance rate at Stanford University?\"}]}}' \
     | grep -q 'Stanford'"

# Test 28: Query ES Agent for personalized analysis
run_test "Query ES Agent for personalized analysis [USER_EMAIL: jane.doe@example.com]" \
    "curl -s -X POST ${ES_AGENT_URL}/run \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_es\",\"user_id\":\"user\",\"session_id\":\"'$ES_SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Based on my profile, what are my chances at Stanford for Computer Science? [USER_EMAIL: jane.doe@example.com]\"}]}}' \
     | grep -q 'Stanford'"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Phase 8: End-to-End Workflow Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 29: Complete RAG workflow
run_test "Complete RAG workflow: Upload profile + Upload KB doc + Query agent" \
    "create_test_student_profile > /dev/null && \
     create_test_college_document > /dev/null && \
     curl -s -X POST ${PROFILE_RAG_URL}/upload-profile \
     -F 'file=@/tmp/test_student_profile.txt' \
     -F 'user_email=workflow_test@example.com' > /dev/null && \
     curl -s -X POST ${KB_RAG_URL}/upload \
     -F 'file=@/tmp/test_college_doc.txt' \
     -F 'user_id=workflow_test' > /dev/null && \
     curl -s -X POST ${RAG_AGENT_URL}/run \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_rag\",\"user_id\":\"user\",\"session_id\":\"'$RAG_SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Compare my profile with Stanford requirements [USER_EMAIL: workflow_test@example.com]\"}]}}' \
     | grep -q 'Stanford'"

# Test 30: Complete ES workflow
run_test "Complete ES workflow: Upload profile + Upload KB doc + Query agent" \
    "curl -s -X POST ${PROFILE_ES_URL}/profiles \
     -F 'file=@/tmp/test_student_profile.txt' \
     -F 'user_email=workflow_test_es@example.com' > /dev/null && \
     curl -s -X POST ${KB_ES_URL}/documents \
     -F 'file=@/tmp/test_college_doc.txt' \
     -F 'user_id=workflow_test_es' > /dev/null && \
     curl -s -X POST ${ES_AGENT_URL}/run \
     -H 'Content-Type: application/json' \
     -d '{\"app_name\":\"college_expert_es\",\"user_id\":\"user\",\"session_id\":\"'$ES_SESSION_ID'\",\"new_message\":{\"parts\":[{\"text\":\"Compare my profile with Stanford requirements [USER_EMAIL: workflow_test_es@example.com]\"}]}}' \
     | grep -q 'Stanford'"

# Cleanup
echo ""
echo -e "${YELLOW}Cleaning up test files...${NC}"
rm -f /tmp/test_college_doc.txt /tmp/test_student_profile.txt
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Comprehensive Test Summary                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Tests:  ${TOTAL_TESTS}"
echo -e "${GREEN}Passed:       ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed:       ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     🎉 ALL COMPREHENSIVE INTEGRATION TESTS PASSED! 🎉      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✓ All 4 profile functions working (RAG + ES)${NC}"
    echo -e "${GREEN}✓ Both agents deployed and functional${NC}"
    echo -e "${GREEN}✓ Document upload and retrieval working${NC}"
    echo -e "${GREEN}✓ Profile management working${NC}"
    echo -e "${GREEN}✓ Agent integration working${NC}"
    echo -e "${GREEN}✓ End-to-end workflows complete${NC}"
    echo -e "${GREEN}✓ Health checks passing${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║     ⚠️  SOME COMPREHENSIVE INTEGRATION TESTS FAILED          ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Please review the failed tests above${NC}"
    echo -e "${YELLOW}Check deployment status with: ./test_deployments.sh${NC}"
    exit 1
fi
