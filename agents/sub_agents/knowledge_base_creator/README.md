# Knowledge Base Creator Agent

## Overview

The Knowledge Base Creator is a sophisticated multi-agent system that researches universities comprehensively and generates structured knowledge base profiles. It uses **5 parallel research agents** to gather data efficiently across different domains.

## Architecture

```
KnowledgeBaseCreator (Sequential)
├── ParallelUniversityResearchers (Parallel)
│   ├── IdentityProfileResearcher
│   ├── AdmissionsDataResearcher
│   ├── AcademicsMajorsResearcher
│   ├── FinancialsResearcher
│   └── StudentLifeOutcomesResearcher
└── KnowledgeBaseSynthesizer
```

## Research Domains

### 1. Identity & Profile Researcher
**Focus:** University identity, mission, culture, and demographics

**Research Questions:**
- Full name, location, setting (urban/suburban/rural)
- University type (public/private/liberal arts/research)
- Religious affiliation
- Undergraduate enrollment
- Student-to-faculty ratio
- Average class size
- Mission statement
- Campus culture descriptors

### 2. Admissions Data Researcher
**Focus:** Comprehensive admissions statistics and holistic review factors

**Research Questions:**
- Total applications, admitted students, acceptance rate
- Yield rate
- ED/EA/RD deadlines and acceptance rates
- GPA ranges (25th-75th percentile)
- SAT/ACT ranges (25th-75th percentile)
- Test policy (required/optional/blind)
- % submitting test scores
- % in top 10% of class
- CDS C7 holistic review factors

### 3. Academics & Majors Researcher
**Focus:** Academic programs, majors, and transfer policies

**Research Questions:**
- List of undergraduate colleges/schools
- Application process (direct to major vs. undeclared)
- Internal acceptance rates by college/school
- Impacted/capped majors
- Top 10 most popular majors
- Alternative majors for competitive programs
- Major change policy
- Internal transfer process and competitiveness

### 4. Financials Researcher
**Focus:** Cost of attendance and financial aid

**Research Questions:**
- Total COA breakdown (tuition, fees, room, board)
- Need-blind/need-aware policy (domestic & international)
- Meets 100% of demonstrated need?
- % receiving financial aid
- % receiving need-based aid
- Average need-based award
- Major merit scholarships
- Merit scholarship application process

### 5. Student Life & Outcomes Researcher
**Focus:** Campus life and career outcomes

**Research Questions:**
- Housing policy and guarantees
- % of students on campus
- Diversity statistics
- Job placement rate
- Average starting salary
- Top 5-10 hiring companies
- Top 5 graduate schools

## Output Schema

The agent produces a comprehensive `UniversityKnowledgeBase` object containing:

```python
{
  "university_name": str,
  "identity": UniversityIdentity,
  "admissions": AdmissionsData,
  "academics": AcademicsData,
  "financials": FinancialsData,
  "student_life": StudentLifeOutcomes,
  "data_sources": List[str],
  "research_date": str,
  "summary": str
}
```

## Usage

### As a Standalone Agent

```python
from agents.sub_agents.knowledge_base_creator.agent import KnowledgeBaseCreator

result = KnowledgeBaseCreator.run(
    user_prompt="Research and create a comprehensive knowledge base for Stanford University."
)

kb = result["university_knowledge_base"]
```

### Using the Test Script

```bash
# From the college_counselor directory
python test_kb_creator.py "Stanford University"
python test_kb_creator.py "UC Berkeley"
python test_kb_creator.py "MIT"
```

The test script will:
1. Run all 5 parallel research agents
2. Synthesize the findings
3. Print a summary
4. Save the full knowledge base to a JSON file

### Output Files

The test script generates JSON files named:
```
kb_stanford_university_20251116.json
kb_uc_berkeley_20251116.json
```

These JSON files can be:
- Converted to PDFs for upload to the knowledge base
- Used directly by the main agent
- Archived for annual updates

## Integration with Main Agent

The knowledge base creator can be integrated into the main workflow:

```python
# In main agent.py
from .sub_agents.knowledge_base_creator.agent import KnowledgeBaseCreator

# Add as a tool
tools=[
    AgentTool(KnowledgeBaseCreator),
    # ... other tools
]
```

## Benefits

✅ **Parallel Processing:** 5 agents run simultaneously for faster research  
✅ **Comprehensive Coverage:** All aspects of university research covered  
✅ **Structured Output:** Consistent schema for all universities  
✅ **Source Tracking:** All data sources documented  
✅ **Focused Research:** Each agent has specific questions to answer  
✅ **Annual Updates:** Easy to re-run for updated data  
✅ **PDF Ready:** Output can be formatted into PDFs for knowledge base  

## Data Sources

The agents search for data from:
- Common Data Set (CDS) files
- Official university websites
- Admissions statistics pages
- Career services reports
- Financial aid offices
- Student life pages
- Third-party education sites (when official data unavailable)

## Best Practices

1. **Run Annually:** Universities update data once per year
2. **Verify Critical Stats:** Double-check acceptance rates and GPA ranges
3. **Note Missing Data:** The schema uses Optional fields for unavailable data
4. **Save Sources:** All sources are tracked for credibility
5. **Review Summary:** The executive summary provides a quick overview

## Example Output

```json
{
  "university_name": "Stanford University",
  "identity": {
    "full_name": "Stanford University",
    "location": "Stanford, California",
    "setting": "Suburban",
    "university_type": "Private Research University",
    "total_undergrad_enrollment": "~7,600",
    "student_faculty_ratio": "5:1",
    "mission_statement": "...",
    "campus_culture": ["collaborative", "innovative", "entrepreneurial", "interdisciplinary", "global"]
  },
  "admissions": {
    "acceptance_rate": "3.9%",
    "gpa_range": "3.9-4.0 (unweighted)",
    "sat_range": "1470-1570",
    "test_policy": "Test-Optional",
    ...
  },
  ...
}
```

## Future Enhancements

- [ ] Add PDF generation directly from JSON
- [ ] Implement caching to avoid duplicate searches
- [ ] Add comparison mode (compare 2+ universities)
- [ ] Include historical trend analysis
- [ ] Add visualization generation (charts, graphs)
