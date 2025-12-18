# University Profile Deep Research - Comprehensive Prompt

This prompt incorporates all research requirements from the 13 specialized sub-agents to generate a complete university profile.

---

## Comprehensive Deep Research Prompt

Replace `{UNIVERSITY_NAME}` with the target university.

```
You are an elite college admissions research analyst. Conduct an EXHAUSTIVE research project on {UNIVERSITY_NAME} to produce a comprehensive university profile for college applicants.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 1: STRATEGIC OVERVIEW & RANKINGS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "US News National Universities ranking 2026 {UNIVERSITY_NAME}"
- "site:usnews.com {UNIVERSITY_NAME} ranking"
- "{UNIVERSITY_NAME} Forbes ranking"
- "{UNIVERSITY_NAME} admissions philosophy holistic review"
- "Reddit {UNIVERSITY_NAME} campus social life"
- "{UNIVERSITY_NAME} research opportunities undergraduates"
- "{UNIVERSITY_NAME} transportation campus"

COLLECT:
- Executive summary (2-3 sentences capturing the school's essence)
- Market position (Public Ivy, Hidden Gem, Elite Private, Research Powerhouse)
- Admissions philosophy (Holistic review, Numbers-focused, Test-free)
- US News National Universities rank (integer)
- Campus social environment from student reviews
- Transportation/accessibility impact on campus life
- Undergraduate research opportunities and industry connections

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 2: CURRENT ADMISSIONS STATISTICS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} Common Data Set 2024" 
- "site:*.edu {UNIVERSITY_NAME} Common Data Set Section C"
- "{UNIVERSITY_NAME} acceptance rate 2024"
- "{UNIVERSITY_NAME} early decision acceptance rate"
- "{UNIVERSITY_NAME} test policy test optional"
- "{UNIVERSITY_NAME} transfer acceptance rate"
- "{UNIVERSITY_NAME} international acceptance rate"

COLLECT:
- Overall acceptance rate (percentage, e.g., 23.5)
- In-state vs out-of-state acceptance rates
- International acceptance rate
- Transfer acceptance rate
- Enrolled class size
- Test policy (Required, Optional, Free, Blind)
- Early admission stats for EACH plan (ED, EA, REA, ED2):
  - Number of applications
  - Number admitted
  - Acceptance rate
  - Percentage of class filled via this plan

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 3: HISTORICAL TRENDS & WAITLIST DATA (The "Black Box")
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} Common Data Set Section C2 waitlist"
- "{UNIVERSITY_NAME} Common Data Set 2023 2022 2021"
- "{UNIVERSITY_NAME} acceptance rate history 5 years"
- "{UNIVERSITY_NAME} yield rate"
- "{UNIVERSITY_NAME} waitlist admit rate"
- "site:reddit.com {UNIVERSITY_NAME} waitlist admitted"

COLLECT for each year 2021-2025:
- Total applications
- Total admits
- Total enrolled (matriculated)
- Overall acceptance rate
- In-state and out-of-state rates if available
- Yield rate (enrolled / admitted × 100)
- WAITLIST DETAILS (Critical - often hidden):
  - Students offered waitlist spots
  - Students who accepted waitlist spot
  - Students admitted FROM waitlist
  - Waitlist admit rate = (admitted from waitlist / accepted spots) × 100
  - Whether waitlist is RANKED or unranked
- Notable events (record applications, test policy changes)

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 4: ADMITTED STUDENT PROFILE & DEMOGRAPHICS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} Common Data Set Section C GPA"
- "{UNIVERSITY_NAME} PrepScholar SAT ACT scores admitted"
- "{UNIVERSITY_NAME} Common Data Set Section B2 racial ethnic"
- "{UNIVERSITY_NAME} Niche demographics"
- "{UNIVERSITY_NAME} IPEDS data enrollment"
- "{UNIVERSITY_NAME} first generation students"
- "{UNIVERSITY_NAME} legacy admission rate"

COLLECT:
GPA Statistics:
- Weighted GPA middle 50% (format: "4.10-4.30")
- Unweighted GPA middle 50%
- Average weighted GPA
- Notes on GPA recalculation policies

Test Scores:
- SAT composite middle 50% (format: "1400-1520")
- SAT section breakdowns (Reading/Writing, Math)
- ACT composite middle 50% (format: "31-35")
- ACT section breakdowns
- Percentage submitting scores
- Test policy nuances

Demographics:
- First-generation percentage
- Legacy percentage
- International percentage
- Geographic breakdown by region/state (top 5)
- Gender breakdown with acceptance rates
- FULL racial/ethnic breakdown from IPEDS/CDS B2:
  - White, Black/African American, Hispanic/Latino, Asian
  - Native American/Alaskan, Pacific Islander
  - Two or more races, Unknown, Non-resident alien
- Religious affiliation if applicable

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 5: ACADEMIC STRUCTURE (COLLEGES & MAJORS)
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} colleges schools list"
- "{UNIVERSITY_NAME} undergraduate majors"
- "{UNIVERSITY_NAME} impacted majors capped selective"
- "{UNIVERSITY_NAME} residential college system"
- "Reddit {UNIVERSITY_NAME} housing dorms review"
- "site:reddit.com transferring into CS at {UNIVERSITY_NAME}"
- "{UNIVERSITY_NAME} computer science acceptance rate"
- "{UNIVERSITY_NAME} engineering direct admit"
- "{UNIVERSITY_NAME} change major requirements"

COLLECT for each college/school:
- College/school name
- Admissions model (Direct Admit, Pre-Major, Separate Application)
- Whether enrollment is capped/restricted
- Strategic fit advice (who should/shouldn't apply)
- Housing profile (dorm style, quality)
- Student archetype (from Reddit/Niche reviews)

COLLECT for EVERY major:
- Major name and degree type (B.S., B.A., B.F.A.)
- Whether impacted/capped
- Major-specific acceptance rate if known
- Average GPA of admitted students
- Prerequisite high school courses
- HIDDEN REQUIREMENTS (Critical):
  - minimum_gpa_to_declare: GPA floor to switch INTO this major
  - weeder_courses: Notorious filter courses (e.g., "Organic Chemistry CHEM 140A")
  - direct_admit_only: TRUE if NO internal transfers allowed
- Admissions pathway (Direct Admit, Pre-Major, Apply as Sophomore)
- Whether internal transfer is allowed
- Internal transfer GPA requirement

Include 10-15 majors per college with REAL weeder course names.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 6: APPLICATION REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} application deadline 2025"
- "{UNIVERSITY_NAME} early decision deadline"
- "{UNIVERSITY_NAME} supplemental essays"
- "{UNIVERSITY_NAME} demonstrated interest"
- "{UNIVERSITY_NAME} interview policy"
- "{UNIVERSITY_NAME} legacy consideration"
- "{UNIVERSITY_NAME} Common App Coalition"

COLLECT:
- Application platforms (Common App, Coalition, UC App, etc.)
- All deadlines (ED, EA, RD, ED2) with dates
- Supplemental requirements by program:
  - Essays (word counts, prompts)
  - Portfolios (for art/architecture)
  - Auditions (for music/theater)
  - Interviews
- Holistic factors:
  - Primary factors (Course Rigor, GPA, Essays, Recommendations)
  - Secondary factors (Extracurriculars, Talents, Character)
  - Essay importance (Critical, High, Moderate, Low)
  - Demonstrated interest policy
  - Interview policy (Required, Recommended, Evaluative, Not Offered)
  - Legacy consideration level
  - First-generation boost level

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 7: APPLICATION GAMING STRATEGIES
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "site:reddit.com {UNIVERSITY_NAME} easier majors to get into"
- "site:reddit.com {UNIVERSITY_NAME} alternate major strategy"
- "site:reddit.com {UNIVERSITY_NAME} college ranking tips"
- "{UNIVERSITY_NAME} undeclared major acceptance"
- "{UNIVERSITY_NAME} change major after admission"

COLLECT:
- Major selection tactics (3-5):
  - Which majors are easier/harder to get into
  - Using Undeclared as a strategy
  - Avoiding listing two capped majors
- College ranking tactics (for residential college systems)
- Alternate major strategy (best backup majors)

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 8: FINANCIALS & SCHOLARSHIPS
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} cost of attendance 2024-2025"
- "{UNIVERSITY_NAME} tuition fees"
- "{UNIVERSITY_NAME} financial aid statistics"
- "{UNIVERSITY_NAME} merit scholarships"
- "{UNIVERSITY_NAME} Regents Scholarship"
- "{UNIVERSITY_NAME} full ride scholarship"
- "{UNIVERSITY_NAME} need-blind admissions"
- "{UNIVERSITY_NAME} meets 100% demonstrated need"

COLLECT:
Cost of Attendance:
- Academic year (format: "2024-2025")
- In-state tuition and total COA (for public schools)
- Out-of-state tuition and total COA
- Supplemental tuition for special programs
- Tuition model (locked 4 years, annual increase)

Financial Aid:
- Aid philosophy (100% Need Met, Need-Blind, Merit Focused)
- Average need-based aid package
- Average merit aid
- Percentage receiving any aid

Scholarships (5-7 minimum):
- Scholarship name
- Type (Merit, Need, Both, Athletic, Departmental)
- Amount (per year or total)
- Non-monetary benefits (priority registration, housing, advising)
- Application method (Automatic, Separate Application, Nomination)
- Deadlines

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 9: CREDIT POLICIES
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "{UNIVERSITY_NAME} AP credit policy"
- "{UNIVERSITY_NAME} IB credit policy"
- "{UNIVERSITY_NAME} ASSIST.org transfer"
- "{UNIVERSITY_NAME} transfer credit policy"
- "{UNIVERSITY_NAME} placement exam"

COLLECT:
- Overall credit philosophy (Generous, Moderate, Strict)
- AP Policy:
  - General rule (minimum score for credit)
  - Exceptions by subject
  - How AP credits can be used (GE, prerequisites, electives)
- IB Policy:
  - General rule (HL vs SL, minimum score)
  - Diploma bonus benefits
- Transfer Articulation:
  - Tools for checking (ASSIST, Transferology, TES)
  - Credit restrictions/caps

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 10: STUDENT INSIGHTS (CROWDSOURCED)
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "site:niche.com {UNIVERSITY_NAME} reviews"
- "site:reddit.com r/ApplyingToCollege {UNIVERSITY_NAME} accepted"
- "site:reddit.com {UNIVERSITY_NAME} essays that worked"
- "site:reddit.com {UNIVERSITY_NAME} admissions advice"
- "{UNIVERSITY_NAME} College Confidential chance me"

COLLECT:
- What it takes (3-5 success factors from student perspectives)
- Common activities of admitted students (5-10)
- Essay tips from admitted students (3-5)
- Red flags to avoid (2-3 things that hurt applications)

═══════════════════════════════════════════════════════════════════════════════
RESEARCH PHASE 11: OUTCOMES & ROI (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

SEARCH for:
- "site:collegescorecard.ed.gov {UNIVERSITY_NAME}"
- "College Scorecard {UNIVERSITY_NAME} median earnings"
- "{UNIVERSITY_NAME} Common Data Set Section B retention graduation"
- "{UNIVERSITY_NAME} career center top employers"
- "LinkedIn {UNIVERSITY_NAME} alumni companies"
- "{UNIVERSITY_NAME} employment outcomes"
- "{UNIVERSITY_NAME} graduate school placement"

COLLECT (FROM OFFICIAL SOURCES ONLY):
Career Outcomes:
- Median earnings 10 years after entry (INTEGER from College Scorecard ONLY)
- 2-year employment rate
- Graduate school rate
- Top employers (5-7 from Career Center/LinkedIn Alumni)
- Loan default rate

Retention (from Common Data Set Section B):
- Freshman retention rate
- 4-year graduation rate
- 6-year graduation rate

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

Return ONLY valid JSON matching this complete structure. No markdown, no explanation.

{
  "_id": "snake_case_university_name",
  
  "metadata": {
    "official_name": "Full Official University Name",
    "location": {"city": "City", "state": "State", "type": "Public or Private"},
    "last_updated": "YYYY-MM-DD",
    "report_source_files": []
  },
  
  "strategic_profile": {
    "executive_summary": "2-3 sentence overview",
    "market_position": "Public Ivy / Hidden Gem / Elite Private / Research Powerhouse",
    "admissions_philosophy": "Holistic review / Numbers-focused / Test-free",
    "us_news_rank": integer,
    "analyst_takeaways": [
      {"category": "Selectivity/Financial/Academic/Culture/Social", "insight": "data-driven finding", "implication": "what it means for applicants"}
    ],
    "campus_dynamics": {
      "social_environment": "detailed description",
      "transportation_impact": "how it affects campus life",
      "research_impact": "undergrad research opportunities"
    }
  },
  
  "admissions_data": {
    "current_status": {
      "overall_acceptance_rate": float,
      "in_state_acceptance_rate": float or null,
      "out_of_state_acceptance_rate": float or null,
      "international_acceptance_rate": float or null,
      "transfer_acceptance_rate": float or null,
      "admits_class_size": integer or null,
      "is_test_optional": boolean,
      "test_policy_details": "Test Required/Optional/Free/Blind",
      "early_admission_stats": [
        {"plan_type": "ED/EA/REA/ED2", "applications": int, "admits": int, "acceptance_rate": float, "class_fill_percentage": float}
      ]
    },
    "longitudinal_trends": [
      {
        "year": integer,
        "cycle_name": "Class of XXXX",
        "applications_total": integer,
        "admits_total": integer,
        "enrolled_total": integer or null,
        "acceptance_rate_overall": float,
        "acceptance_rate_in_state": float or null,
        "acceptance_rate_out_of_state": float or null,
        "yield_rate": float or null,
        "waitlist_stats": {
          "year": int, "offered_spots": int, "accepted_spots": int, "admitted_from_waitlist": int, "waitlist_admit_rate": float, "is_waitlist_ranked": boolean
        },
        "notes": "notable events"
      }
    ],
    "admitted_student_profile": {
      "gpa": {"weighted_middle_50": "X.XX-X.XX", "unweighted_middle_50": "X.XX-X.XX", "average_weighted": float, "notes": ""},
      "testing": {"sat_composite_middle_50": "XXXX-XXXX", "sat_reading_middle_50": "", "sat_math_middle_50": "", "act_composite_middle_50": "XX-XX", "submission_rate": float, "policy_note": ""},
      "demographics": {
        "first_gen_percentage": float,
        "legacy_percentage": float,
        "international_percentage": float,
        "geographic_breakdown": [{"region": "name", "percentage": float}],
        "gender_breakdown": {"men": {"applicants": int, "admits": int, "acceptance_rate": float}, "women": {...}},
        "racial_breakdown": {"white": float, "black_african_american": float, "hispanic_latino": float, "asian": float, "native_american_alaskan": float, "pacific_islander": float, "two_or_more_races": float, "unknown": float, "non_resident_alien": float},
        "religious_affiliation": null or "denomination"
      }
    }
  },
  
  "academic_structure": {
    "structure_type": "Colleges/Schools/Divisions",
    "colleges": [
      {
        "name": "College/School Name",
        "admissions_model": "Direct Admit/Pre-Major/Separate Application",
        "acceptance_rate_estimate": float or null,
        "is_restricted_or_capped": boolean,
        "strategic_fit_advice": "who should apply",
        "housing_profile": "dorm description",
        "student_archetype": "typical student type",
        "majors": [
          {
            "name": "Major Name",
            "degree_type": "B.S./B.A./B.F.A.",
            "is_impacted": boolean,
            "acceptance_rate": "X%" or null,
            "average_gpa_admitted": float or null,
            "prerequisite_courses": ["course1", "course2"],
            "minimum_gpa_to_declare": float or null,
            "weeder_courses": ["Course Name with Code"],
            "special_requirements": "" or "Portfolio/Audition/etc",
            "admissions_pathway": "Direct Admit/Pre-Major/Apply as Sophomore",
            "internal_transfer_allowed": boolean,
            "direct_admit_only": boolean,
            "internal_transfer_gpa": float or null,
            "notes": ""
          }
        ]
      }
    ],
    "minors_certificates": ["list of minors and certificates"]
  },
  
  "application_process": {
    "platforms": ["Common App", "Coalition", etc],
    "application_deadlines": [{"plan_type": "ED/EA/RD", "date": "YYYY-MM-DD", "is_binding": boolean, "notes": ""}],
    "supplemental_requirements": [{"target_program": "All/specific", "requirement_type": "Essays/Portfolio/Audition", "deadline": "", "details": "specifics"}],
    "holistic_factors": {
      "primary_factors": ["list"],
      "secondary_factors": ["list"],
      "essay_importance": "Critical/High/Moderate/Low",
      "demonstrated_interest": "Important/Considered/Not Considered",
      "interview_policy": "Required/Recommended/Not Offered",
      "legacy_consideration": "Strong/Moderate/Minimal/None",
      "first_gen_boost": "Strong/Moderate/Minimal/None",
      "specific_differentiators": ""
    }
  },
  
  "application_strategy": {
    "major_selection_tactics": ["tactic1", "tactic2"],
    "college_ranking_tactics": ["for residential college systems"],
    "alternate_major_strategy": "detailed backup strategy"
  },
  
  "financials": {
    "tuition_model": "Tuition Stability/Annual Increase",
    "cost_of_attendance_breakdown": {
      "academic_year": "YYYY-YYYY",
      "in_state": {"tuition": float, "total_coa": float, "housing": float},
      "out_of_state": {"tuition": float, "total_coa": float, "supplemental_tuition": float}
    },
    "aid_philosophy": "100% Need Met/Need-Blind/Merit Focused",
    "average_need_based_aid": float,
    "average_merit_aid": float,
    "percent_receiving_aid": float,
    "scholarships": [
      {"name": "Scholarship Name", "type": "Merit/Need/Both", "amount": "$X,XXX/year", "deadline": "", "benefits": "priority registration, etc", "application_method": "Automatic/Separate Application"}
    ]
  },
  
  "credit_policies": {
    "philosophy": "Generous/Moderate/Strict",
    "ap_policy": {"general_rule": "score requirement", "exceptions": ["subject-specific rules"], "usage": "how credits apply"},
    "ib_policy": {"general_rule": "HL/SL rules", "diploma_bonus": boolean},
    "transfer_articulation": {"tools": ["ASSIST.org", "Transferology"], "restrictions": "credit caps/limits"}
  },
  
  "student_insights": {
    "what_it_takes": ["success factor 1", "factor 2"],
    "common_activities": ["activity 1", "activity 2"],
    "essay_tips": ["tip 1", "tip 2"],
    "red_flags": ["thing to avoid 1", "thing 2"],
    "insights": []
  },
  
  "outcomes": {
    "median_earnings_10yr": integer (from College Scorecard ONLY),
    "employment_rate_2yr": float or null,
    "grad_school_rate": float or null,
    "top_employers": ["Company1", "Company2"],
    "loan_default_rate": float or null
  },
  
  "student_retention": {
    "freshman_retention_rate": float,
    "graduation_rate_4_year": float,
    "graduation_rate_6_year": float
  }
}

═══════════════════════════════════════════════════════════════════════════════
ANTI-HALLUCINATION RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════

1. median_earnings_10yr must come from College Scorecard ONLY. If not found, use null.
2. DO NOT invent weeder course names. Only include courses explicitly mentioned as "weed-out" or "filter" courses.
3. DO NOT guess minimum_gpa_to_declare. Only include if found on official departmental pages.
4. DO NOT estimate acceptance rates. Use official sources only.
5. For waitlist data, if hidden, explicitly note "Waitlist data not publicly disclosed" in notes.
6. Top employers must come from official Career Center reports or LinkedIn Alumni data.
7. Use null for ANY value you cannot verify from official sources.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH THE UNIVERSITY: {UNIVERSITY_NAME}
═══════════════════════════════════════════════════════════════════════════════
```
