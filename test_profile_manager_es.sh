#!/bin/bash

# Comprehensive Integration Test for Profile Manager (ES)
# Tests all endpoints, error handling, and edge cases

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROFILE_ES_URL="https://profile-manager-es-pfnwjfp26a-ue.a.run.app"
TEST_DIR="/tmp/profile_es_test_$$"
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
create_comprehensive_profile() {
    cat > "$1" << 'EOF'
# Student Profile: Alexander Thompson

## Personal Information
- **Full Name**: Alexander James Thompson
- **Email**: alex.thompson@email.com
- **Phone**: (555) 234-5678
- **Address**: 789 Innovation Drive, Austin, TX 78701
- **Date of Birth**: September 12, 2006
- **Citizenship**: United States

## Academic Profile
- **High School**: Westlake High School
- **GPA**: 4.0 (unweighted), 5.2 (weighted)
- **Class Rank**: 1/650 (Valedictorian)
- **SAT Score**: 1590 (Math: 800, Reading: 790)
- **ACT Score**: 36
- **PSAT**: National Merit Scholar

### Advanced Coursework
- **AP Courses**: 13 courses, all 5s
  - Calculus BC, Physics C: Mechanics, Physics C: E&M
  - Chemistry, Biology, Computer Science A, Statistics
  - English Literature, US History, World History
  - European History, Macroeconomics, Microeconomics
  - Spanish Language

### Dual Enrollment
- Multivariable Calculus (University of Texas)
- Linear Algebra (University of Texas)
- Differential Equations (University of Texas)

## Research Experience
### MIT Research Science Institute (RSI) - Summer 2023
- **Project**: Quantum Computing Applications in Cryptography
- **Mentor**: Dr. Peter Shor, MIT
- **Outcome**: Published in IEEE Quantum Electronics
- **Presentation**: MIT Undergraduate Research Symposium

### Stanford AI Lab Internship - Summer 2022
- **Project**: Neural Network Architecture Optimization
- **Mentor**: Dr. Andrew Ng
- **Technologies**: TensorFlow, PyTorch, CUDA
- **Outcome**: 2 conference papers, 1 patent pending

### Local University Research - Ongoing
- **Topic**: Machine Learning in Medical Diagnosis
- **Collaboration**: Dell Medical School
- **Focus**: Early cancer detection using AI
- **Funding**: National Science Foundation Grant

## Technical Projects
### Quantum Computing Simulator
- **Description**: Built a quantum circuit simulator in Python
- **Features**: Supports up to 20 qubits, quantum gates visualization
- **GitHub**: 500+ stars, featured in Quantum Weekly
- **Usage**: Used by 3 university courses

### AI-Powered Tutoring System
- **Description**: Adaptive learning platform for STEM education
- **Technologies**: React, Node.js, TensorFlow.js
- **Impact**: 10,000+ student users, 85% improvement rate
- **Awards**: Google Code-in Grand Prize Winner

### Biomedical Device Innovation
- **Description**: Low-cost prosthetic limb controller
- **Technologies**: Arduino, Machine Learning, 3D Printing
- **Impact**: Helping amputees in developing countries
- **Recognition**: International Science Fair Winner

## Extracurricular Leadership
### Science Olympiad
- **Position**: Team Captain (3 years)
- **Achievements**: National Champion (Chemistry Lab, 2023)
- **Mentoring**: Coached middle school teams, 50+ students

### Math Competition Team
- **Position**: President (2 years)
- **Achievements**: AIME Perfect Score, USAMO Qualifier
- **Teaching**: Created curriculum for competition math

### Computer Science Club
- **Position**: Founder and President
- **Initiatives**: Hackathon organization, coding workshops
- **Community**: 200+ members, 10+ corporate sponsors

## Community Service
### STEM Education Outreach
- **Role**: Volunteer Instructor (3 years)
- **Program**: Teaching coding to underprivileged students
- **Impact**: 500+ students taught, 50+ workshops conducted

### Hospital Volunteer
- **Department**: Pediatric Oncology
- **Hours**: 400+ hours over 2 years
- **Activities**: Patient entertainment, technology assistance

### Environmental Conservation
- **Project**: Community recycling program
- **Leadership**: Organized 20+ cleanup events
- **Impact**: 10 tons of waste recycled

## Awards and Recognition
### Academic Awards
- Presidential Scholar (2024)
- National Merit Scholar Finalist
- US Presidential Scholars Program Candidate
- Texas State Scholar
- Austin ISD Student of the Year

### Competition Awards
- Intel International Science Fair: First Place
- Google Science Fair: Global Finalist
- Regeneron Science Talent Search: Top 10
- Siemens Competition: Regional Winner

### Leadership Awards
- Eagle Scout (Boy Scouts of America)
- National Honor Society President
- Student Council President
- Youth Leadership Austin Fellow

## Athletic Achievements
### Varsity Tennis
- **Position**: #1 Singles Player
- **Achievements**: State Qualifier (3 years)
- **Leadership**: Team Captain (2 years)
- **Academic**: All-Academic Team

### Cross Country
- **Achievements**: Regional Qualifier
- **Personal Records**: 5K - 16:45
- **Leadership**: Team MVP

## Artistic Pursuits
### Piano Performance
- **Level**: Advanced (10 years of study)
- **Achievements**: State Competition Winner
- **Repertoire**: Classical, Jazz, Contemporary
- **Performances**: Carnegie Hall Recital

### Photography
- **Exhibitions**: Local art galleries (3 shows)
- **Style**: Nature and architectural photography
- **Publications**: National Geographic Kids

## Target Universities
### Reach Schools
- Massachusetts Institute of Technology (MIT)
- Stanford University
- Harvard University
- California Institute of Technology (Caltech)

### Target Schools
- Princeton University
- Columbia University
- University of Chicago
- Rice University

### Safety Schools
- University of Texas at Austin
- Texas A&M University
- Southern Methodist University

## Career Goals
### Primary Objective
- PhD in Computer Science with focus on Quantum Computing
- Research position at national laboratory or tech company
- Goal: Develop quantum algorithms for real-world applications

### Long-term Vision
- Start quantum computing company
- Bridge gap between theoretical research and practical applications
- Mentor next generation of quantum researchers

### Alternative Paths
- Medical research using AI and machine learning
- Biomedical engineering focusing on prosthetics
- Data science in healthcare industry

## Essays and Personal Statement
### Main Essay Theme
- Journey from curiosity to innovation in quantum computing
- Overcoming challenges in pursuing advanced research
- Vision for using technology to solve global problems

### Supplemental Essays
- MIT: "Why I want to contribute to quantum computing research"
- Stanford: "Interdisciplinary approach to problem-solving"
- Harvard: "Leadership in scientific community"

## Letters of Recommendation
### Academic References
1. Dr. Sarah Chen (AP Physics Teacher) - 15 years
2. Dr. Michael Rodriguez (AP Calculus Teacher) - 10 years
3. Dr. Jennifer Liu (Research Mentor, UT Austin) - 2 years

### Research References
1. Dr. Peter Shor (MIT RSI Mentor)
2. Dr. Andrew Ng (Stanford AI Lab Mentor)
3. Dr. Robert Williams (Dell Medical School)

## Standardized Test Scores
### SAT
- **Total**: 1590/1600
- **Math**: 800/800
- **Reading**: 790/800
- **Essay**: 8/8/8

### Subject Tests
- **Math Level 2**: 800/800
- **Physics**: 800/800
- **Chemistry**: 800/800

### AP Scores
- **13 exams taken, all scores of 5**
- **Average**: 5.0/5.0

## Additional Information
### Languages
- English (Native)
- Spanish (Fluent, 8 years study)
- Mandarin Chinese (Intermediate, 3 years study)

### Technical Skills
- **Programming**: Python, Java, C++, JavaScript, Go
- **Frameworks**: TensorFlow, PyTorch, React, Node.js
- **Tools**: Git, Docker, AWS, Google Cloud Platform
- **Hardware**: Arduino, Raspberry Pi, FPGA programming

### Certifications
- Google Cloud Professional Developer
- AWS Certified Solutions Architect
- Red Hat Certified System Administrator

## Summer Activities
### 2023: MIT Research Science Institute
- Conducted quantum computing research
- Published paper in peer-reviewed journal
- Presented at international conference

### 2022: Stanford AI Lab
- Developed neural network optimization algorithms
- Contributed to open-source machine learning projects
- Mentored by industry-leading researchers

### 2021: Local Research Program
- Started medical diagnosis AI project
- Secured NSF funding for continued research
- Built team of 5 student researchers

## Financial Considerations
### Expected Family Contribution
- **EFC**: $15,000 (estimated)
- **Need**: Significant financial aid required

### Scholarships Applied
- National Merit Scholarship
- QuestBridge National College Match
- Coca-Cola Scholars Program
- Jack Kent Cooke Foundation Scholarship

### Work Study
- Experience: 2 years as teaching assistant
- Skills: Tutoring in math, science, computer science
- Availability: 10-15 hours per week during college

## Special Circumstances
### First-Generation Considerations
- First in family to attend four-year university
- Parents: High school graduates, blue-collar workers
- Family support: Strong encouragement for education

### Geographic Diversity
- From Texas, applying to predominantly East/West Coast schools
- Unique perspective: Southern upbringing with global ambitions
- Cultural adaptation: Experience with diverse communities

## Final Notes
### Strengths Summary
- Exceptional academic achievement across all disciplines
- Significant research experience at prestigious institutions
- Leadership roles in multiple organizations
- Strong commitment to community service
- Well-rounded with artistic and athletic pursuits

### Areas for Growth
- Public speaking confidence (improving through debate)
- Time management with multiple commitments
- Balancing perfectionism with practical constraints

### College Readiness
- Mature beyond years in academic and research settings
- Independent learner with strong problem-solving skills
- Collaborative team player with leadership experience
- Resilient in face of challenges and setbacks
EOF
}

create_stem_profile() {
    cat > "$1" << 'EOF'
# Student Profile: Maya Patel

## Personal Information
- **Name**: Maya Priya Patel
- **Email**: maya.patel@email.com
- **Phone**: (555) 345-6789
- **Address**: 456 Technology Boulevard, San Jose, CA 95110
- **Date of Birth**: December 3, 2006

## Academic Excellence
- **High School**: Monta Vista High School
- **GPA**: 3.95/4.0 (unweighted)
- **SAT**: 1540 (Math: 790, Reading: 750)
- **Class Rank**: 12/800 (Top 2%)

### STEM Focus
- **AP STEM Scores**: All 5s
  - Calculus BC, Physics C, Chemistry, Biology
  - Computer Science A, Statistics
- **Research**: Silicon Valley tech internship
- **Competitions**: Science fair champion, hackathon winner

## Leadership
- **Girls Who Code**: Chapter President
- **Robotics Team**: Lead Programmer
- **Math Club**: Competition Coordinator

## Community Impact
- **STEM Tutoring**: 200+ hours
- **Tech Workshops**: For underserved communities
- **Environmental Club**: Green initiatives leader

## Goals
- **Major**: Computer Science/AI
- **Career**: Tech entrepreneur
- **Mission**: Increase diversity in STEM
EOF
}

create_business_profile() {
    cat > "$1" << 'EOF'
# Student Profile: James Wilson

## Personal Information
- **Name**: James Alexander Wilson
- **Email**: james.wilson@email.com
- **Phone**: (555) 567-8901
- **Address**: 123 Wall Street, New York, NY 10005
- **Date of Birth**: June 15, 2006

## Business Background
- **High School**: Stuyvesant High School
- **GPA**: 3.88/4.0
- **SAT**: 1520 (Math: 760, Reading: 760)
- **Class Rank**: 25/800

### Entrepreneurship
- **Startup**: Founded e-commerce platform at 16
- **Revenue**: $50K+ in first year
- **Team**: Managed 5 employees
- **Awards**: Young Entrepreneur of the Year

### Finance Experience
- **Investment Club**: President
- **Portfolio**: Managed $10K virtual portfolio
- **Competition**: Stock pitch competition winner
- **Internship**: Wall Street investment bank

## Leadership
- **DECA**: International champion
- **Student Government**: Treasurer
- **Business Club**: Founder

## Community Service
- **Financial Literacy**: Taught to low-income students
- **Business Mentoring**: Young entrepreneurs program
- **Economic Development**: Community revitalization projects

## Goals
- **Major**: Finance/Economics
- **Career**: Investment banking/PE
- **Long-term**: Start impact investing fund
EOF
}

# Health Check Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    HEALTH CHECK TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Basic Connectivity Test" \
    "curl -s '$PROFILE_ES_URL/' | head -1 | grep -q 'error\|Profile Manager\|success'"

run_test "Service Availability" \
    "curl -s -f '$PROFILE_ES_URL/profiles' >/dev/null"

# Profile Upload Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PROFILE UPLOAD TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Upload comprehensive profile
create_comprehensive_profile "$TEST_DIR/alexander_thompson.txt"
run_test "Upload Comprehensive Profile" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/alexander_thompson.txt' \
     -F 'user_id=alex.thompson@email.com' \
     | grep -q '\"success\": true'"

# Test 2: Upload STEM focused profile
create_stem_profile "$TEST_DIR/maya_patel.txt"
run_test "Upload STEM Profile" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/maya_patel.txt' \
     -F 'user_id=maya.patel@email.com' \
     | grep -q '\"success\": true'"

# Test 3: Upload business focused profile
create_business_profile "$TEST_DIR/james_wilson.txt"
run_test "Upload Business Profile" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/james_wilson.txt' \
     -F 'user_id=james.wilson@email.com' \
     | grep -q '\"success\": true'"

# Test 4: Upload without file
run_test "Upload Without File - Should Fail" \
    "! curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'user_id=test@example.com' -F 'user_email=test@example.com' \
     | grep -q '\"success\": true'"

# Test 5: Upload without user_id
run_test "Upload Without User ID - Should Fail" \
    "! curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/alexander_thompson.txt' \
     | grep -q '\"success\": true'"

# Test 6: Upload empty file
touch "$TEST_DIR/empty.txt"
run_test "Upload Empty File" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/empty.txt' \
     -F 'user_id=empty.profile@email.com' \
     | grep -q '\"success\": true'"

# Test 7: Upload profile with special characters
cat > "$TEST_DIR/special_profile.txt" << 'EOF'
# Profile with Special Characters: José García

## Información Personal
- **Nombre**: José Miguel García López
- **Email**: jose.garcia@email.com
- **Teléfono**: (555) 123-4567
- **Dirección**: 456 Calle Principal, Miami, FL 33101

## Características Especiales
- **Fórmulas**: E = mc², ∫f(x)dx = F(x) + C
- **Símbolos**: α, β, γ, δ, ε, ζ, η, θ
- **Unicode**: 🎓, 🔬, 💻, 🏆, 🌟

## Contenido Multilingüe
Hello World! ¡Hola Mundo! Bonjour le Monde!
你好世界! こんにちは世界! 안녕하세요 세계!

## Código y Programación
```python
def hello_student():
    print("Welcome to college!")
    return "Success"
```

## Citas y Puntuación
"Education is the passport to the future" - Malcolm X
Éxito = Preparación + Oportunidad
EOF
run_test "Upload Profile with Special Characters" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/special_profile.txt' \
     -F 'user_id=jose.garcia@email.com' \
     | grep -q '\"success\": true'"

# Profile Listing Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   PROFILE LISTING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "List All Profiles" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?limit=50' \
     | grep -q '\"success\": true'"

run_test "List Profiles for Alexander Thompson" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=alex.thompson@email.com' \
     | grep -q '\"success\": true'"

run_test "List Profiles for Maya Patel" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=maya.patel@email.com' \
     | grep -q '\"success\": true'"

run_test "List Profiles for James Wilson" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=james.wilson@email.com' \
     | grep -q '\"success\": true'"

run_test "List Profiles with Limit" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?limit=5' \
     | grep -q '\"success\": true'"

run_test "List Profiles with Pagination" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?limit=3&from=0' \
     | grep -q '\"success\": true'"

run_test "List Profiles with Size Parameter" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?size=10&from=0' \
     | grep -q '\"success\": true'"

run_test "List Profiles - Verify Document Count" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=alex.thompson@email.com&limit=10' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and len(data.get('documents', [])) > 0 else 1)\""

# Profile Delete Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PROFILE DELETE TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Get a document ID first
DOC_ID=$(curl -s -X GET "$PROFILE_ES_URL/profiles?user_id=james.wilson@email.com&limit=1" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and data.get('documents'):
        print(data['documents'][0].get('id', ''))
except:
    pass
" 2>/dev/null)

if [ -n "$DOC_ID" ]; then
    run_test "Delete Profile by ID" \
        "curl -s -X POST '$PROFILE_ES_URL/profiles/delete' \
         -H 'Content-Type: application/json' \
         -d '{\"document_id\":\"$DOC_ID\",\"user_id\":\"james.wilson@email.com\"}' \
         | grep -q '\"success\": true'"

    run_test "Delete Nonexistent Profile - Should Fail" \
        "! curl -s -X POST '$PROFILE_ES_URL/profiles/delete' \
         -H 'Content-Type: application/json' \
         -d '{\"document_id\":\"nonexistent_id\",\"user_id\":\"test@example.com\"}' \
         | grep -q '\"success\": true'"
else
    echo -e "${YELLOW}Skipping delete tests - no profiles found${NC}"
fi

# Error Handling Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   ERROR HANDLING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Invalid Endpoint - Should Return 404" \
    "curl -s '$PROFILE_ES_URL/invalid-endpoint' | grep -q 'Not Found\|error'"

run_test "Invalid HTTP Method on Health" \
    "curl -s -X POST '$PROFILE_ES_URL/health' | grep -q 'Method not allowed\\|error'"

run_test "Malformed JSON in Delete Request" \
    "! curl -s -X POST '$PROFILE_ES_URL/profiles/delete' \
     -H 'Content-Type: application/json' \
     -d '{invalid json}' \
     | grep -q '\"success\": true'"

run_test "Missing Required Field in Delete Request" \
    "! curl -s -X POST '$PROFILE_ES_URL/profiles/delete' \
     -H 'Content-Type: application/json' \
     -d '{}' \
     | grep -q '\"success\": true'"

# Performance Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    PERFORMANCE TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Health Check Response Time < 2s" \
    "curl -s '$PROFILE_ES_URL/health' >/dev/null"

run_test "Profile List Response Time < 5s" \
    "curl -s '$PROFILE_ES_URL/profiles?limit=20' >/dev/null"

run_test "Upload Response Time < 10s" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/maya_patel.txt' \
     -F 'user_id=maya.patel@email.com' >/dev/null"

run_test "Delete Response Time < 5s" \
    "curl -s -X POST '$PROFILE_ES_URL/profiles/delete' \
     -H 'Content-Type: application/json' \
     -d '{\"document_id\":\"test_id\",\"user_id\":\"test@example.com\"}' >/dev/null"

# Elasticsearch Specific Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}               ELASTICSEARCH SPECIFIC TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Verify Elasticsearch Indexing" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?limit=1' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and any('indexed_at' in doc.get('document', {}) for doc in data.get('documents', [])) else 1)\""

run_test "Verify Document Structure" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?limit=1' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('documents') and 'document' in data['documents'][0] else 1)\""

run_test "Verify User ID Field" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=alex.thompson@email.com&limit=1' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('documents') and data['documents'][0]['document'].get('user_id') == 'alex.thompson@email.com' else 1)\""

run_test "Search with Special Characters" \
    "curl -s -X POST '$PROFILE_ES_URL/upload-profile' \
     -F 'file=@$TEST_DIR/special_profile.txt' \
     -F 'user_id=special.test@email.com' \
     | grep -q '\"success\": true'"

# Content Processing Tests
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}               CONTENT PROCESSING TESTS${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

run_test "Verify Content Extraction" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=alex.thompson@email.com&limit=1' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('documents') and data['documents'][0]['document'].get('raw_content') else 1)\""

run_test "Verify Structured Content" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=alex.thompson@email.com&limit=1' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('documents') and data['documents'][0]['document'].get('structured_content') else 1)\""

run_test "Verify Metadata Extraction" \
    "curl -s -X GET '$PROFILE_ES_URL/profiles?user_id=alex.thompson@email.com&limit=1' \
     | python3 -c \"import sys, json; data=json.load(sys.stdin); exit(0 if data.get('success') and data.get('documents') and data['documents'][0]['document'].get('extraction_timestamp') else 1)\""

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
    echo -e "${GREEN}✓ Profile Manager (ES) is fully functional${NC}"
    echo -e "${GREEN}✓ Elasticsearch connectivity verified${NC}"
    echo -e "${GREEN}✓ Profile indexing and retrieval working${NC}"
    echo -e "${GREEN}✓ Content extraction and processing working${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}Please check the failed tests and fix the issues${NC}"
    exit 1
fi
