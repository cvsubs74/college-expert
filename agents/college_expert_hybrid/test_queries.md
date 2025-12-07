# Hybrid Agent Test Queries

Comprehensive test cases for the College Counselor Hybrid Agent system.

## Category 1: General University Information (No Profile)

### Basic Program Search
1. **"What universities in the knowledge base offer business undergraduate programs?"**
   - Expected: List all universities with business programs from KB
   - Should NOT retrieve student profile

2. **"Tell me about engineering programs at UC schools"**
   - Expected: Search for UC schools with engineering programs
   - Should filter by UC system

3. **"Which universities offer computer science programs?"**
   - Expected: List universities with CS programs from KB only
   - Should NOT add universities from general knowledge

### University Comparisons
4. **"Compare UC Berkeley and UCLA for computer science - which has better career outcomes?"**
   - Expected: Search both universities, compare CS programs & career data
   - Should NOT retrieve student profile

5. **"Compare USC and UCLA - which is more selective?"**
   - Expected: Compare acceptance rates and admissions data
   - Should use hybrid search to find both

6. **"What's the difference between UC Berkeley and UC San Diego?"**
   - Expected: Compare institutions across multiple dimensions
   - Should pull from structured profiles

### Specific Data Queries
7. **"What are the acceptance rates for all universities in California?"**
   - Expected: Filter by state, list acceptance rates
   - Should use filters: {"state": "CA"}

8. **"Which universities have the highest median earnings for graduates?"**
   - Expected: Sort/rank by career outcomes
   - Should extract median_earnings_10yr field

9. **"Tell me about UCLA's application requirements and deadlines"**
   - Expected: Search UCLA profile, extract admissions data
   - Should include test policy, GPA ranges, deadlines

### Career Outcomes
10. **"What are the top employers hiring from UC Berkeley graduates?"**
    - Expected: Extract top_employers from outcomes data
    - Should cite specific data from profile

11. **"Compare career outcomes between public and private universities"**
    - Expected: Aggregate data across institution types
    - Should use type filter

## Category 2: Personalized Analysis (Uses Profile)

### Individual School Chances
12. **"What are my chances at UCLA?"**
    - Expected: Retrieve profile, search UCLA, compare GPA/scores
    - Should use StudentProfileAgent

13. **"Analyze my chances at UC Berkeley and USC"**
    - Expected: Profile retrieval + multi-school comparison
    - Should compare against each university's requirements

14. **"Should I apply to Stanford?"** *(if not in KB)*
    - Expected: State that Stanford is not in knowledge base
    - Should NOT hallucinate data

### Profile-Based Recommendations
15. **"Based on my profile, which universities should I consider as safety schools?"**
    - Expected: Retrieve profile, categorize by reach/target/safety
    - Should use acceptance rate + GPA comparison

16. **"What are my best match schools for business programs?"**
    - Expected: Profile + program search + fit analysis
    - Should filter by business programs, match GPA/scores

17. **"Am I competitive for any UC schools?"**
    - Expected: Profile + UC search + competitiveness analysis
    - Should filter: {"state": "CA", "type": "Public"}

### Gap Analysis
18. **"What aspects of my profile would strengthen my application to UC San Diego?"**
    - Expected: Profile comparison + gap identification
    - Should recommend specific improvements

19. **"How does my GPA compare to admitted students at UCLA?"**
    - Expected: Profile GPA vs UCLA's GPA range
    - Should cite specific numbers

## Category 3: Complex Multi-Faceted Queries

### Strategic Planning
20. **"Help me build a balanced college list for Business majors in California"**
    - Expected: Profile + CA filter + business search + categorization
    - Should create reach/target/safety breakdown

21. **"I want to study Marketing and Psychology - which universities have programs that combine both?"**
    - Expected: Interdisciplinary program search
    - Should use semantic search for program overlap

22. **"Which selective schools (under 30% acceptance rate) offer strong business programs?"**
    - Expected: Multi-criteria filter
    - Should use: {"acceptance_rate_max": 30} + program search

### Application Strategy
23. **"Compare the application strategies for UC Berkeley vs USC - what does each school prioritize?"**
    - Expected: Extract application_strategy from both profiles
    - Should cite institutional priorities

24. **"What's the difference between applying to the College of Letters and Science vs the Business School at UC schools?"**
    - Expected: Extract academic_structure data
    - Should compare application pathways

25. **"Which universities use holistic admissions vs test-score focused?"**
    - Expected: Extract admissions_philosophy & test_policy
    - Should categorize based on policy

## Category 4: Edge Cases & Error Handling

### Knowledge Base Boundaries
26. **"Tell me about Harvard's business program"** *(if not in KB)*
    - Expected: "Harvard is not in my knowledge base"
    - Should NOT hallucinate

27. **"Which Ivy League schools are in your knowledge base?"**
    - Expected: List only Ivy schools actually indexed
    - Should NOT add schools from memory

### Ambiguous Queries
28. **"What's the best university for me?"**
    - Expected: Ask for clarification OR retrieve profile + recommend
    - Should handle gracefully

29. **"Tell me about majors"**
    - Expected: Search all universities for major data
    - Should aggregate across profiles

### Mixed Intent
30. **"I'm interested in business, but also want good career outcomes - which schools fit?"**
    - Expected: Profile + program search + outcomes ranking
    - Should balance multiple criteria

---

## Success Criteria

✅ **No Hallucinations**: Only recommends universities in knowledge base
✅ **Correct Profile Use**: Only retrieves profile for personal questions (my/I/me)
✅ **Search First**: Always searches KB before answering
✅ **Complete Answers**: Uses available data without asking for unnecessary clarification
✅ **Accurate Filtering**: Properly uses state, type, acceptance_rate filters
✅ **Data Citation**: References specific numbers from profiles

## Testing Notes

- Test with email: `cvsubs@gmail.com`
- Current KB contains: UCLA, UC Berkeley, USC, UCSD, UCI, UCD, UIUC
- Student profile major: Business
- All queries assume user is logged in (email available in request)
