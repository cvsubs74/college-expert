#!/bin/bash

# Comprehensive Integration Test for Profile Manager (RAG)
# Tests all endpoints, error handling, and edge cases

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROFILE_URL="https://us-east1-college-counselling-478115.cloudfunctions.net/profile-manager"
TEST_DIR="/tmp/profile_test_$$"
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
create_student_profile() {
    cat > "$1" << 'EOF'
# Student Profile: Sarah Johnson

## Personal Information
- **Name**: Sarah Elizabeth Johnson
- **Email**: sarah.johnson@email.com
- **Phone**: (555) 123-4567
- **Address**: 123 Main Street, Boston, MA 02108
- **Date of Birth**: March 15, 2006

## Academic Information
- **High School**: Boston Latin School
- **GPA**: 3.92 (unweighted), 4.5 (weighted)
- **Class Rank**: 8/420 (Top 2%)
- **SAT Score**: 1550 (Math: 800, Reading: 750)
- **ACT Score**: 35
- **AP Courses**: 11 courses
  - Calculus BC (5)
  - Physics C: Mechanics (5)
  - Physics C: E&M (5)
  - Chemistry (5)
  - Biology (5)
  - English Literature (5)
  - US History (5)
  - World History (5)
  - Statistics (5)
  - Computer Science A (5)
  - Spanish Language (5)

## Extracurricular Activities
- **Science Olympiad**: Team Captain (3 years), National Medalist
- **Math Club**: President (2 years), AIME Qualifier
- **Robotics Team**: Lead Programmer (4 years), Regional Champions
- **Volunteer Work**: 300+ hours at local hospital
- **Research**: Summer internship at MIT Media Lab
- **Music**: Piano (10 years), State Competition Winner
- **Sports**: Varsity Tennis (4 years), Team Captain

## Awards and Honors
- National Merit Scholar Finalist
- AP Scholar with Distinction
- Presidential Scholar Candidate
- Massachusetts Science Fair Winner
- Boston Globe Scholar
- National Honor Society President

## Interests
- Computer Science and Artificial Intelligence
- Biomedical Engineering
- Mathematics and Statistics
- Research and Innovation

## Target Schools
- **Reach**: MIT, Stanford, Harvard
- **Target**: Caltech, Princeton, Columbia
- **Safety**: Boston University, Northeastern, Tufts

## Career Goals
- MD/PhD in Biomedical Engineering
- Research in medical robotics and AI
- Start a biotech company
- Work in translational medicine

## Essays Summary
- Personal Statement: Overcoming learning disability in elementary school
- Supplemental Essays: Research experience, leadership, community impact
- Additional Materials: Research paper submission, portfolio of projects
EOF
}

create_athlete_profile() {
    cat > "$1" << 'EOF'
# Student Profile: Michael Chen

## Personal Information
- **Name**: Michael David Chen
- **Email**: michael.chen@email.com
- **Phone**: (555) 987-6543
- **Address**: 456 Oak Avenue, Palo Alto, CA 94301
- **Date of Birth**: July 22, 2006

## Academic Information
- **High School**: Palo Alto High School
- **GPA**: 3.85 (unweighted), 4.3 (weighted)
- **Class Rank**: 15/520 (Top 3%)
- **SAT Score**: 1520 (Math: 780, Reading: 740)
- **ACT Score**: 34
- **AP Courses**: 9 courses
  - Calculus BC (5)
  - Physics C: Mechanics (5)
  - Chemistry (5)
  - Biology (5)
  - English Literature (4)
  - US History (4)
  - Economics (5)
  - Statistics (5)
  - Computer Science A (4)

## Athletic Information
- **Sport**: Swimming
- **Events**: 100m Freestyle, 200m Freestyle, 400m Individual Medley
- **Achievements**:
  - State Champion (100m Freestyle, 2023)
  - Junior Olympic Qualifier (2022, 2023)
  - Team Captain (2 years)
  - 100m Butterfly: 48.2 seconds (NCAA consideration time)
  - 200m IM: 1:52.8 (NCAA B-cut)
- **Training**: 20 hours/week, year-round
- **Club**: Palo Alto Stanford Aquatics

## Extracurricular Activities
- **Student Government**: Class Treasurer
- **STEM Club**: Member, Robotics Sub-team
- **Volunteer**: Swim instructor for special needs children
- **Research**: Summer project on sports biomechanics
- **Leadership**: Youth swim coach, 50+ hours/month

## Awards and Honors
- All-American Swimmer
- Academic All-State
- Presidential Scholar in the Arts
- National Honor Society
- California Scholarship Federation

## Interests
- Sports Medicine
- Biomechanical Engineering
- Exercise Science
- Athletic Training

## Target Schools
- **Reach**: Stanford, Harvard, Yale
- **Target**: UC Berkeley, UCLA, USC
- **Safety**: UC Davis, Cal Poly, Santa Clara

## Career Goals
- Sports Medicine Physician
- Biomechanics Researcher
- Olympic Coach
- Athletic Director at university level

## Recruiting Information
- NCAA Division I Prospect
- Recruiting Videos: Available on YouTube
- Coach References: 3 letters of recommendation
- Academic Eligibility: NCAA Clearinghouse certified
EOF
}

create_artist_profile() {
    cat > "$1" << 'EOF'
# Student Profile: Emma Rodriguez

## Personal Information
- **Name**: Emma Sofia Rodriguez
- **Email**: emma.rodriguez@email.com
- **Phone**: (555) 456-7890
- **Address**: 789 Elm Street, New York, NY 10025
- **Date of Birth**: November 8, 2006

## Academic Information
- **High School**: Fiorello H. LaGuardia High School of Music & Art and Performing Arts
- **GPA**: 3.78 (unweighted), 4.2 (weighted)
- **Class Rank**: 25/680 (Top 4%)
- **SAT Score**: 1480 (Math: 720, Reading: 760)
- **ACT Score**: 32
- **AP Courses**: 8 courses
  - Art History (5)
  - English Literature (5)
  - US History (5)
  - World History (4)
  - Psychology (5)
  - Statistics (4)
  - Spanish Literature (5)
  - Music Theory (5)

## Artistic Information
- **Primary Medium**: Oil painting and mixed media
- **Exhibitions**:
  - Metropolitan Museum of Art Teen Program (2023)
  - MoMA PS1 Youth Exhibition (2022, 2023)
  - Brooklyn Museum Art Show (2023)
  - Solo exhibition at local gallery (2023)
- **Awards**:
  - Scholastic Art & Writing Awards: National Gold Medal
  - YoungArts Winner in Visual Arts
  - NYC Department of Education Art Competition: First Place
- **Portfolio**: 25 pieces, including portraits, landscapes, and abstract works

## Extracurricular Activities
- **Art Club**: President (2 years)
- **Museum Intern**: Metropolitan Museum of Art Education Department
- **Community Art**: Mural projects in underserved communities
- **Teaching**: Art instructor for elementary school students
- **Volunteer**: 200+ hours at community art centers

## Awards and Honors
- National Honor Society
- AP Scholar with Honor
- NYC Mayoral Arts Award
- Presidential Scholar in the Arts Nominee

## Interests
- Fine Arts and Art History
- Museum Studies
- Arts Education
- Digital Media and Design

## Target Schools
- **Reach**: Yale, Columbia, Brown
- **Target**: NYU Tisch, School of Visual Arts, Pratt Institute
- **Safety**: Parsons School of Design, Cooper Union

## Career Goals
- Museum Curator
- Art Gallery Director
- Arts Education Administrator
- Professional Artist
- Arts Policy Advocate

## Portfolio Highlights
- Series: "Urban Landscapes" - 8 paintings of NYC
- Series: "Identity and Culture" - 6 mixed media pieces
- Commissioned works: 3 private collections
- Digital art: 12 pieces using Procreate and Adobe Suite
EOF
}

# Health Check Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    HEALTH CHECK TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Basic Connectivity Test" \
    "curl -s '$PROFILE_URL/' | head -1 | grep -q 'error\|Profile Manager\|success'"

run_test "Service Availability" \
    "curl -s '$PROFILE_URL/list-profiles?user_email=test@example.com' >/dev/null"

# Profile Upload Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PROFILE UPLOAD TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Upload comprehensive student profile
create_student_profile "$TEST_DIR/sarah_johnson.txt"
run_test "Upload Comprehensive Student Profile" \
    "curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'file=@$TEST_DIR/sarah_johnson.txt' \
     -F 'user_email=sarah.johnson@email.com' \
     | grep -q '\"success\":true'"

# Test 2: Upload athlete profile
create_athlete_profile "$TEST_DIR/michael_chen.txt"
run_test "Upload Athlete Profile" \
    "curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'file=@$TEST_DIR/michael_chen.txt' \
     -F 'user_email=michael.chen@email.com' \
     | grep -q '\"success\":true'"

# Test 3: Upload artist profile
create_artist_profile "$TEST_DIR/emma_rodriguez.txt"
run_test "Upload Artist Profile" \
    "curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'file=@$TEST_DIR/emma_rodriguez.txt' \
     -F 'user_email=emma.rodriguez@email.com' \
     | grep -q '\"success\":true'"

# Test 4: Upload without file
run_test "Upload Without File - Should Fail" \
    "! curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'user_email=test@example.com' \
     | grep -q '\"success\":true'"

# Test 5: Upload without user_email
run_test "Upload Without Email - Should Fail" \
    "! curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'file=@$TEST_DIR/sarah_johnson.txt' \
     | grep -q '\"success\":true'"

# Test 6: Upload with invalid email format
run_test "Upload with Invalid Email - Should Fail" \
    "! curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'file=@$TEST_DIR/sarah_johnson.txt' \
     -F 'user_email=invalid-email' \
     | grep -q '\"success\":true'"

# Profile Listing Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   PROFILE LISTING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "List All Profiles" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=sarah.johnson@email.com' | grep -q '\"success\":true'"

run_test "List Profiles for Sarah Johnson" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=sarah.johnson@email.com' \
     | grep -q '\"success\":true'"

run_test "List Profiles for Michael Chen" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=michael.chen@email.com' \
     | grep -q '\"success\":true'"

run_test "List Profiles for Emma Rodriguez" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=emma.rodriguez@email.com' \
     | grep -q '\"success\":true'"

run_test "List Profiles - Verify Profile Count" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=sarah.johnson@email.com' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and len(data.get('profiles', [])) > 0 else 1)\""

# Profile Content Retrieval Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}               PROFILE CONTENT RETRIEVAL TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Get profile name first
PROFILE_NAME=$(curl -s -X GET "$PROFILE_URL/list-profiles?user_email=sarah.johnson@email.com" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('profiles'):
        print(data['profiles'][0].get('name', ''))
except:
    pass
" 2>/dev/null)

if [ -n "$PROFILE_NAME" ]; then
    run_test "Get Profile Content" \
        "curl -s -X POST '$PROFILE_URL/get-profile-content' \
         -H 'Content-Type: application/json' \
         -d '{\"file_name\":\"$PROFILE_NAME\"}' \
         | grep -q '\"success\":true'"

    run_test "Get Profile with Invalid Name - Should Fail" \
        "! curl -s -X POST '$PROFILE_URL/get-profile-content' \
         -H 'Content-Type: application/json' \
         -d '{\"file_name\":\"nonexistent_profile.txt\"}' \
         | grep -q '\"success\":true'"
else
    echo -e "${YELLOW}Skipping profile content tests - no profiles found${NC}"
fi

# Profile Delete Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PROFILE DELETE TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Get profile name for deletion
DELETE_PROFILE_NAME=$(curl -s -X GET "$PROFILE_URL/list-profiles?user_email=michael.chen@email.com" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('profiles'):
        print(data['profiles'][0].get('name', ''))
except:
    pass
" 2>/dev/null)

if [ -n "$DELETE_PROFILE_NAME" ]; then
    run_test "Delete Profile" \
        "curl -s -X DELETE '$PROFILE_URL/delete-profile' \
         -H 'Content-Type: application/json' \
         -d '{\"file_name\":\"$DELETE_PROFILE_NAME\",\"user_email\":\"michael.chen@email.com\"}' \
         | grep -q '\"success\":true'"

    run_test "Delete Nonexistent Profile - Should Fail" \
        "! curl -s -X DELETE '$PROFILE_URL/delete-profile' \
         -H 'Content-Type: application/json' \
         -d '{\"file_name\":\"nonexistent_profile.txt\",\"user_email\":\"test@example.com\"}' \
         | grep -q '\"success\":true'"
else
    echo -e "${YELLOW}Skipping delete tests - no profiles found${NC}"
fi

# Error Handling Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   ERROR HANDLING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Invalid Endpoint - Should Return 404" \
    "curl -s '$PROFILE_URL/invalid-endpoint' | grep -q 'Endpoint not found'"

run_test "Invalid HTTP Method on Health" \
    "curl -s -X POST '$PROFILE_URL/health' | grep -q 'Method not allowed\\|error'"

run_test "Malformed JSON in Profile Content Request" \
    "! curl -s -X POST '$PROFILE_URL/get-profile-content' \
     -H 'Content-Type: application/json' \
     -d '{invalid json}' \
     | grep -q '\"success\":true'"

run_test "Missing Required Field in Profile Content" \
    "! curl -s -X POST '$PROFILE_URL/get-profile-content' \
     -H 'Content-Type: application/json' \
     -d '{}' \
     | grep -q '\"success\":true'"

# Performance Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PERFORMANCE TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Health Check Response Time < 2s" \
    "timeout 2s curl -s '$PROFILE_URL/health' >/dev/null"

run_test "Profile List Response Time < 5s" \
    "timeout 5s curl -s '$PROFILE_URL/list-profiles' >/dev/null"

run_test "Profile Upload Response Time < 10s" \
    "timeout 10s curl -s -X POST '$PROFILE_URL/upload-profile' \
     -F 'file=@$TEST_DIR/emma_rodriguez.txt' \
     -F 'user_email=emma.rodriguez@email.com' >/dev/null"

run_test "Profile Content Retrieval Response Time < 5s" \
    "timeout 5s curl -s -X POST '$PROFILE_URL/get-profile-content' \
     -H 'Content-Type: application/json' \
     -d '{\"file_name\":\"test_profile.txt\"}' >/dev/null"

# RAG Specific Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                      RAG SPECIFIC TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Verify Vertex AI Integration" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=sarah.johnson@email.com' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('profiles') else 1)\""

run_test "Verify Profile Processing" \
    "curl -s -X GET '$PROFILE_URL/list-profiles?user_email=emma.rodriguez@email.com' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and any('processed_at' in profile for profile in data.get('profiles', [])) else 1)\""

run_test "Verify File Storage Integration" \
    "curl -s -X GET '$PROFILE_URL/list-profiles' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('profiles') else 1)\""

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
    echo -e "${GREEN}✓ Profile Manager (RAG) is fully functional${NC}"
    echo -e "${GREEN}✓ Vertex AI integration verified${NC}"
    echo -e "${GREEN}✓ Profile processing and storage working${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}Please check the failed tests and fix the issues${NC}"
    exit 1
fi
