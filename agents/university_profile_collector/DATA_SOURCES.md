# University Profile Collector - Data Categories & Sources

> **Last Updated:** 2024-12-24  
> **Architecture:** Hybrid API + LLM Research Agents

---

## API Keys Used

| Variable | Value | Purpose |
|----------|-------|---------|
| `DATA_GOV_API_KEY` | `XJUVgSykeBGlbFICrNqdDbtbVgC6qTiwSYJq20Mo` | College Scorecard API (data.gov) |
| `GEMINI_API_KEY` | `AIzaSyCRn7stUUxosclh4c6yJEMVZOquYR9PMIE` | Google Gemini LLM for agent research |

---

## APIs in Use

| API | Base URL | Authentication | Data Categories |
|-----|----------|----------------|-----------------|
| **College Scorecard** | `https://api.data.gov/ed/collegescorecard/v1/schools` | API Key (`DATA_GOV_API_KEY`) | Admissions, Test Scores, Tuition, Demographics, Outcomes, Retention |
| **Urban Institute IPEDS** | `https://educationdata.urban.org/api/v1/college-university/ipeds` | None (Public) | Admissions (enrollment/admissions counts), Tuition |

---

## Architecture Overview

The system uses a **hybrid architecture** combining:
1. **API-backed agents** → structured, factual data from government APIs
2. **LLM research agents** → qualitative data via Google Search

```
┌─────────────────────────────────────────────────────────────────┐
│                   UniversityProfile (model.py)                  │
├─────────────────────────────────────────────────────────────────┤
│  13 Specialized Sub-Agents (LLM-based)                          │
│  ├── 4 API-Backed Agents (College Scorecard + Urban IPEDS)      │
│  │   ├── api_admissions_agent                                   │
│  │   ├── api_demographics_agent                                 │
│  │   ├── api_financials_agent                                   │
│  │   └── api_outcomes_agent                                     │
│  └── 9 Google Search Agents (Qualitative research)              │
│      ├── strategy_agent                                         │
│      ├── admissions_current_agent                               │
│      ├── admissions_trends_agent                                │
│      ├── admitted_profile_agent                                 │
│      ├── colleges_agent                                         │
│      ├── majors_agent                                           │
│      ├── application_agent                                      │
│      ├── strategy_tactics_agent                                 │
│      ├── credit_policies_agent                                  │
│      ├── scholarships_agent                                     │
│      └── student_insights_agent                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Categories by Agent

### 1. Metadata & Strategic Profile

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `strategy_agent` | `official_name`, `city`, `state`, `type`, `us_news_rank`, `executive_summary`, `market_position`, `admissions_philosophy`, `campus_dynamics` | **Google Search:** Official .edu sites, US News, Niche, Forbes, Reddit |

**File:** `sub_agents/strategy_agent.py`

---

### 2. Admissions Data

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `api_admissions_agent` | `overall_acceptance_rate`, `is_test_optional`, `test_policy_details`, `admits_class_size`, `transfer_acceptance_rate`, `early_admission_stats` (ED/EA/REA/ED2), `gpa_profile`, `testing_profile` (SAT/ACT), `international_acceptance_rate`, `in_state_acceptance_rate`, `out_of_state_acceptance_rate` | **APIs:** College Scorecard, Urban Institute IPEDS; **Google Search** for supplementary data |
| `admissions_current_agent` | Current cycle stats | **Google Search:** Common Data Set, US News, Niche |
| `admissions_trends_agent` | `longitudinal_trends`, `waitlist_stats` | **Google Search:** Common Data Set archives, Prep Scholar, news |

**Files:** 
- `sub_agents/api_admissions_agent.py`
- `sub_agents/admissions_current_agent.py`
- `sub_agents/admissions_trends_agent.py`

---

### 3. Demographics

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `api_demographics_agent` | `first_gen_percentage`, `legacy_percentage`, `geographic_breakdown`, `gender_breakdown` (men/women/non_binary stats), `racial_breakdown` (IPEDS categories) | **API:** College Scorecard; **Google Search:** Common Data Set Section C |

**Racial Breakdown Categories (IPEDS Standard):**
- `white`
- `black_african_american`
- `hispanic_latino`
- `asian`
- `native_american_alaskan`
- `pacific_islander`
- `two_or_more_races`
- `unknown`
- `non_resident_alien` (international students)

**File:** `sub_agents/api_demographics_agent.py`

---

### 4. Financials & Scholarships

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `api_financials_agent` | `tuition_model`, `in_state_tuition`, `out_of_state_tuition`, `total_coa`, `housing`, `aid_philosophy`, `average_need_based_aid`, `average_merit_aid`, `percent_receiving_aid` | **APIs:** College Scorecard, Urban Institute IPEDS; **Google Search** for scholarship details |
| `scholarships_agent` | `scholarships[]` (name, type, amount, eligibility, application_method) | **Google Search:** Official scholarships pages, merit listings |

**Files:**
- `sub_agents/api_financials_agent.py`
- `sub_agents/scholarships_agent.py`

---

### 5. Career Outcomes & Retention

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `api_outcomes_agent` | `median_earnings_10yr`, `employment_rate_2yr`, `grad_school_rate`, `loan_default_rate`, `top_employers`, `freshman_retention_rate`, `graduation_rate_4_year`, `graduation_rate_6_year` | **API:** College Scorecard; **Google Search:** Career center reports, LinkedIn alumni data |

**College Scorecard Fields Used:**
- `latest.earnings.10_yrs_after_entry.median`
- `latest.completion.rate_suppressed.four_year`
- `latest.student.retention_rate.four_year.full_time`

**File:** `sub_agents/api_outcomes_agent.py`

---

### 6. Academic Structure

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `colleges_agent` | `structure_type`, `colleges[]` (name, admissions_model, acceptance_rate_estimate, housing_profile, student_archetype) | **Google Search:** Official college pages, Reddit, Niche |
| `majors_agent` | `majors[]` (name, degree_type, is_impacted, acceptance_rate, prerequisite_courses, weeder_courses, admissions_pathway, internal_transfer_gpa, curriculum, notable_professors) | **Google Search:** Official major pages, department catalogs, Reddit |

**Files:**
- `sub_agents/colleges_agent.py`
- `sub_agents/majors_agent.py`

---

### 7. Application Process

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `application_agent` | `platforms`, `application_deadlines`, `supplemental_requirements`, `holistic_factors` | **Google Search:** Official admissions page, Common App requirements, Niche |

**Holistic Factors Include:**
- `primary_factors`, `secondary_factors`
- `essay_importance`
- `demonstrated_interest`
- `interview_policy`
- `legacy_consideration`
- `first_gen_boost`

**File:** `sub_agents/application_agent.py`

---

### 8. Strategic Gaming

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `strategy_tactics_agent` | `major_selection_tactics`, `college_ranking_tactics`, `alternate_major_strategy` | **Google Search:** Reddit, College Confidential, admissions consultants |

**File:** `sub_agents/strategy_tactics_agent.py`

---

### 9. Credit Policies

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `credit_policies_agent` | `philosophy`, `ap_policy`, `ib_policy`, `transfer_articulation` | **Google Search:** Official credit policy pages, ASSIST.org, Transferology |

**File:** `sub_agents/credit_policies_agent.py`

---

### 10. Student Insights (Crowdsourced)

| Agent | Data Fields | Data Sources |
|-------|-------------|--------------|
| `student_insights_agent` | `what_it_takes`, `common_activities`, `essay_tips`, `red_flags` | **Google Search:** Niche, Reddit, College Confidential, student blogs |

**File:** `sub_agents/student_insights_agent.py`

---

## College Scorecard API Fields

The following fields are fetched from the College Scorecard API (`api_tools.py`):

```python
SCORECARD_FIELDS = [
    "id", "school.name", "school.city", "school.state",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.25th_percentile.critical_reading",
    "latest.admissions.sat_scores.25th_percentile.math",
    "latest.admissions.sat_scores.75th_percentile.critical_reading",
    "latest.admissions.sat_scores.75th_percentile.math",
    "latest.admissions.act_scores.25th_percentile.cumulative",
    "latest.admissions.act_scores.75th_percentile.cumulative",
    "latest.student.size",
    "latest.student.demographics.race_ethnicity.white",
    "latest.student.demographics.race_ethnicity.black",
    "latest.student.demographics.race_ethnicity.hispanic",
    "latest.student.demographics.race_ethnicity.asian",
    "latest.student.demographics.race_ethnicity.non_resident_alien",
    "latest.student.demographics.first_generation",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.aid.pell_grant_rate",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.student.retention_rate.four_year.full_time",
    "latest.completion.rate_suppressed.four_year",
]
```

---

## IPEDS Unit ID Mapping

The Urban Institute IPEDS API requires a `unitid` for each university. The following mappings are defined in `api_tools.py`:

| University | IPEDS Unit ID |
|------------|---------------|
| Stanford University | 243744 |
| MIT | 166683 |
| Yale University | 130794 |
| Harvard University | 166027 |
| Princeton University | 186131 |
| UC Berkeley | 110635 |
| USC | 123961 |
| UCLA | 110662 |
| Columbia University | 190150 |
| University of Pennsylvania | 215062 |
| Duke University | 152651 |
| Northwestern University | 147767 |
| Cornell University | 190415 |
| Brown University | 217156 |
| Dartmouth College | 182670 |
| University of Chicago | 144050 |
| Johns Hopkins University | 162928 |
| Rice University | 227757 |
| Vanderbilt University | 221999 |
| Carnegie Mellon University | 211440 |
| University of Notre Dame | 152080 |
| Georgetown University | 131496 |
| University of Michigan | 170976 |
| NYU | 193900 |
| Boston University | 164988 |
| Georgia Tech | 139755 |
| University of Florida | 134130 |
| UT Austin | 228778 |
| Caltech | 110404 |

---

## File Structure

```
university_profile_collector/
├── .env                      # API keys
├── agent.py                  # Main orchestration agent
├── api_tools.py              # College Scorecard & IPEDS API wrappers
├── model.py                  # Pydantic data models (44KB)
├── tools.py                  # File writing utilities
├── sub_agents/
│   ├── __init__.py
│   ├── strategy_agent.py
│   ├── api_admissions_agent.py
│   ├── api_demographics_agent.py
│   ├── api_financials_agent.py
│   ├── api_outcomes_agent.py
│   ├── admissions_current_agent.py
│   ├── admissions_trends_agent.py
│   ├── admitted_profile_agent.py
│   ├── colleges_agent.py
│   ├── majors_agent.py
│   ├── application_agent.py
│   ├── strategy_tactics_agent.py
│   ├── financials_agent.py
│   ├── scholarships_agent.py
│   ├── credit_policies_agent.py
│   ├── student_insights_agent.py
│   ├── profile_builder.py
│   └── file_saver.py
└── research/                 # Output JSON profiles
```
