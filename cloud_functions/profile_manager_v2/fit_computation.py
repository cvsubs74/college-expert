"""
Fit computation module for calculating college fit analysis.
Ported from profile_manager_es to use Firestore instead of Elasticsearch.
Contains complete LLM-based fit calculation with selectivity adjustments.
"""

import os
import logging
import json
import requests
from datetime import datetime
from google import genai
from google.genai import types
from firestore_db import get_db
from essay_copilot import fetch_university_profile

logger = logging.getLogger(__name__)

# Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def build_profile_content_from_fields(profile_doc):
    """
    Build profile content text from flat Firestore fields.
    Used when profile was created via onboarding (no raw 'content' field).
    """
    lines = ["Student Profile Summary\n"]
    
    # Personal info
    name = profile_doc.get('student_name') or profile_doc.get('name')
    school = profile_doc.get('high_school') or profile_doc.get('school')
    grade = profile_doc.get('grade_level') or profile_doc.get('grade')
    state = profile_doc.get('state') or profile_doc.get('location')
    
    if name:
        lines.append(f"Name: {name}")
    if school:
        lines.append(f"High School: {school}")
    if grade:
        lines.append(f"Grade: {grade}")
    if state:
        lines.append(f"State: {state}")
    
    # GPA
    gpa_weighted = profile_doc.get('gpa_weighted')
    gpa_unweighted = profile_doc.get('gpa_unweighted')
    gpa_uc = profile_doc.get('gpa_uc')
    
    if gpa_weighted:
        lines.append(f"Weighted GPA: {gpa_weighted}")
    if gpa_unweighted:
        lines.append(f"Unweighted GPA: {gpa_unweighted}")
    if gpa_uc:
        lines.append(f"UC GPA: {gpa_uc}")
    
    # Test scores
    sat_total = profile_doc.get('sat_composite') or profile_doc.get('sat_total')
    act_composite = profile_doc.get('act_composite')
    
    if sat_total:
        lines.append(f"SAT Score: {sat_total}")
    if act_composite:
        lines.append(f"ACT Score: {act_composite}")
    
    # Coursework
    ap_count = profile_doc.get('ap_courses_count')
    ap_exams = profile_doc.get('ap_exams', [])
    courses = profile_doc.get('courses', [])
    
    if ap_count:
        lines.append(f"AP/IB Courses: {ap_count}")
    if ap_exams:
        exam_list = ', '.join([f"{e.get('subject', 'Unknown')} ({e.get('score', 'N/A')})" for e in ap_exams[:5]])
        lines.append(f"AP Exams: {exam_list}")
    if courses:
        course_list = ', '.join([c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in courses[:10]])
        lines.append(f"Courses: {course_list}")
    
    # Extracurriculars
    extracurriculars = profile_doc.get('extracurriculars', [])
    top_activity = profile_doc.get('top_activity')
    
    if top_activity:
        lines.append(f"Top Activity: {top_activity}")
    if extracurriculars:
        ec_list = ', '.join([e.get('activity', str(e)) if isinstance(e, dict) else str(e) for e in extracurriculars[:5]])
        lines.append(f"Activities: {ec_list}")
    
    # Intended major
    intended_majors = profile_doc.get('intended_majors') or profile_doc.get('intended_major')
    if intended_majors:
        if isinstance(intended_majors, list):
            lines.append(f"Intended Major(s): {', '.join(intended_majors)}")
        else:
            lines.append(f"Intended Major: {intended_majors}")
    
    # Awards
    awards = profile_doc.get('awards', [])
    if awards:
        award_list = ', '.join([a.get('name', str(a)) if isinstance(a, dict) else str(a) for a in awards[:5]])
        lines.append(f"Awards: {award_list}")
    
    content = '\n'.join(lines)
    logger.info(f"[FIT_COMP] Built profile content: {len(content)} chars, {len(lines)} lines")
    return content


def parse_student_profile_llm(profile_content):
    """
    Use Gemini to extract structured data from any student profile format.
    More robust than regex for varied profile formats.
    """
    try:
        if not GEMINI_API_KEY:
            logger.warning("[FIT_COMP] No GEMINI_API_KEY found")
            return None
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""Extract the following fields from this student profile. 
Return ONLY valid JSON with these exact keys (use null for missing values):

{{
  "weighted_gpa": <float or null>,
  "unweighted_gpa": <float or null>,
  "uc_gpa": <float or null>,
  "sat_score": <integer or null>,
  "act_score": <integer or null>,
  "ap_count": <integer>,
  "ap_scores": {{}},
  "intended_major": <string or null>,
  "has_leadership": <boolean>,
  "awards_count": <integer>,
  "activities_count": <integer>,
  "test_optional": <boolean - true if no test scores mentioned>
}}

STUDENT PROFILE:
{profile_content[:4000]}

Return ONLY the JSON object, no markdown formatting."""

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            response_text = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        
        result = json.loads(response_text)
        
        # Normalize the result
        return {
            'weighted_gpa': result.get('weighted_gpa') or result.get('uc_gpa'),
            'unweighted_gpa': result.get('unweighted_gpa'),
            'sat_score': result.get('sat_score'),
            'act_score': result.get('act_score'),
            'ap_scores': result.get('ap_scores', {}),
            'ap_count': result.get('ap_count', 0),
            'intended_major': result.get('intended_major'),
            'has_leadership': result.get('has_leadership', False),
            'awards_count': result.get('awards_count', 0),
            'activities_count': result.get('activities_count', 0),
            'test_optional': result.get('test_optional', False)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[FIT_COMP] JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"[FIT_COMP] Error: {e}")
        return None


def parse_student_profile(profile_content):
    """
    Extract structured academic data from profile text content using LLM.
    Pure LLM-based extraction - no fallback to regex.
    """
    if not profile_content:
        return {}
    
    content = profile_content if isinstance(profile_content, str) else str(profile_content)
    
    # Use LLM-based extraction (handles varied formats better)
    try:
        llm_result = parse_student_profile_llm(content)
        if llm_result:
            logger.info(f"[FIT_COMP] LLM extraction successful: GPA={llm_result.get('weighted_gpa')}, SAT={llm_result.get('sat_score')}")
            return llm_result
    except Exception as e:
        logger.error(f"[FIT_COMP] LLM extraction failed: {e}")
    
    # Return empty dict if LLM fails (no fallback)
    return {}


def calculate_fit_with_llm(student_profile_text, university_data, intended_major='', student_profile_json=None):
    """
    COMPLETE fit calculation with Gemini LLM including 8-category comprehensive analysis.
    This is the EXACT implementation from profile_manager_es.
    """
    try:
        # Log inputs
        if len(student_profile_text) < 100:
            logger.warning(f"[FIT_COMP] ALERT: Profile text is very short! Content: {student_profile_text}")
        else:
            logger.info(f"[FIT_COMP] Profile preview: {student_profile_text[:300]}...")
        
        # Extract university details - handle both nested (profile.metadata) and flat structures
        profile_data = university_data.get('profile', university_data)
        
        # Get university name
        uni_metadata = profile_data.get('metadata', {})
        uni_name = uni_metadata.get('official_name') or university_data.get('official_name', 'University')
        
        # Get acceptance rate
        admissions = profile_data.get('admissions_data', {})
        current_status = admissions.get('current_status', {})
        acceptance_rate = current_status.get('overall_acceptance_rate')
        
        # Fallback to top-level acceptance_rate if nested not found
        if acceptance_rate is None:
            acceptance_rate = university_data.get('acceptance_rate', 50)
        
        # Ensure acceptance_rate is a number
        if isinstance(acceptance_rate, str):
            try:
                acceptance_rate = float(acceptance_rate.replace('%', ''))
            except:
                acceptance_rate = 50
        
        try:
            acceptance_rate = float(acceptance_rate)
        except (TypeError, ValueError):
            acceptance_rate = 50
        
        # Get admitted student profile for comparison
        admitted_profile = admissions.get('admitted_student_profile', {})
        
        logger.info(f"[FIT_COMP] University: {uni_name}, Acceptance Rate: {acceptance_rate}%")
        
        # Pass ENTIRE university profile to LLM
        uni_profile_full = json.dumps(profile_data, default=str)
        
        # Also serialize student profile JSON if available
        student_profile_json_str = ""
        if student_profile_json:
            student_profile_json_str = json.dumps(student_profile_json, default=str)
            logger.info(f"[FIT_COMP] Student profile JSON size: {len(student_profile_json_str)} chars")
        
        logger.info(f"[FIT_COMP] Full university profile size: {len(uni_profile_full)} chars")
        
        # Determine selectivity tier and category floor
        if acceptance_rate < 8:
            selectivity_tier = "ULTRA_SELECTIVE"
            category_floor = "SUPER_REACH"
            selectivity_note = "This is an ULTRA-SELECTIVE school (<8% acceptance). Even perfect applicants are often rejected. MINIMUM category is SUPER_REACH."
        elif acceptance_rate < 15:
            selectivity_tier = "HIGHLY_SELECTIVE"
            category_floor = "REACH"
            selectivity_note = "This is a HIGHLY SELECTIVE school (8-15% acceptance). Only top students have a chance. MINIMUM category is REACH."
        elif acceptance_rate < 25:
            selectivity_tier = "VERY_SELECTIVE"
            category_floor = None
            selectivity_note = "This is a VERY_SELECTIVE school (15-25% acceptance). Strong applicants compete."
        elif acceptance_rate < 40:
            selectivity_tier = "SELECTIVE"
            category_floor = None
            selectivity_note = "This is a SELECTIVE school (25-40% acceptance). Standard competitive admissions."
        else:
            selectivity_tier = "ACCESSIBLE"
            category_floor = None
            selectivity_note = "This is an ACCESSIBLE school (>40% acceptance). Strong students are very likely admitted."
        
        # Build student profile section
        student_section = f"""{student_profile_text}
Intended Major: {intended_major or 'Undecided'}"""
        
        if student_profile_json_str:
            student_section += f"""

**COMPLETE STUDENT PROFILE DATA (structured):**
{student_profile_json_str}"""
        
        # COMPLETE PROMPT FROM ES VERSION
        prompt = f"""You are a private college admissions counselor with 20+ years of experience placing students at Ivy League and top-50 universities. You have deep knowledge of how selective admissions works and understand that even excellent students face rejection at highly selective schools.

**STUDENT PROFILE:**
{student_section}

**COMPLETE UNIVERSITY DATA (use this for all recommendations):**
{uni_profile_full}

**SELECTIVITY CONTEXT:**
Acceptance Rate: {acceptance_rate}%
Selectivity Tier: {selectivity_tier}
{selectivity_note}

**SCORING FRAMEWORK:**

1. **ACADEMIC STRENGTH (40 points max)**
   - GPA vs admitted student profile: 0-20 points
     * GPA > school's 75th percentile → 18-20 points
     * GPA at school's 50th percentile → 12-14 points
     * GPA at school's 25th percentile → 6-8 points
     * GPA below 25th percentile → 0-5 points
   - Test Scores (SAT/ACT): 0-12 points
   - Course Rigor (AP/IB/Honors count): 0-8 points

2. **HOLISTIC PROFILE (30 points max)**
   - Extracurricular depth & impact: 0-12 points
   - Leadership positions & scope: 0-8 points
   - Awards & recognition: 0-5 points
   - Unique factors (first-gen, hooks): 0-5 points

3. **MAJOR FIT (15 points max)**
   - Major availability & strength: 0-8 points
   - Related activities/demonstrated interest: 0-4 points
   - Clarity of academic goals: 0-3 points

4. **SELECTIVITY ADJUSTMENT (-15 to +5)**
   - <8% acceptance: -15 points (SUPER_REACH floor)
   - 8-15% acceptance: -10 points (REACH floor)
   - 15-25% acceptance: -5 points
   - 25-40% acceptance: 0 points
   - >40% acceptance: +5 points (SAFETY possible)

**CATEGORY ASSIGNMENT (after selectivity adjustment):**
- **SAFETY** (score 75-100): Student significantly exceeds averages AND acceptance rate >40%
- **TARGET** (score 55-74): Student matches averages AND acceptance rate >25%
- **REACH** (score 35-54): Student slightly below averages OR acceptance rate 10-25%
- **SUPER_REACH** (score 0-34): Student below averages OR acceptance rate <10%

**CRITICAL RULES:**
1. Schools with <8% acceptance CANNOT be SAFETY or TARGET for ANY student
2. Schools with 8-15% acceptance CANNOT be SAFETY for ANY student
3. If student profile lacks GPA or test scores, they cannot qualify for SAFETY at any school
4. Always cite specific data from the student profile (actual GPA, actual activities)

**YOUR TASK:**
Analyze this student's fit for {uni_name}. Be realistic about chances at selective schools.

**8-CATEGORY COMPREHENSIVE RECOMMENDATION SYSTEM:**
You have access to COMPLETE university data. Generate recommendations across ALL 8 categories:

**CATEGORY 1: ESSAY ANGLES** (use application_process.supplemental_requirements and student_insights.essay_tips)
- Generate 2-3 specific essay angles for this student
- Reference ACTUAL essay prompts from the school if available
- Connect specific student experiences to specific school values/programs

**CATEGORY 2: APPLICATION TIMELINE** (useapplication_process.application_deadlines)
- Recommend which plan (ED/EA/RD) based on student's competitiveness
- Include financial aid deadlines from financials
- Provide key preparation milestones

**CATEGORY 3: SCHOLARSHIP MATCHES** (use financials.scholarships)
- Identify scholarships this student might qualify for
- Match based on student's GPA, activities, and demographics
- Include deadlines and application methods

**CATEGORY 4: TEST STRATEGY** (use admissions_data.admitted_student_profile.testing)
- Compare student's scores to school's middle 50%
- Recommend submit/don't submit based on competitive position
- Include school's test submission rate for context

**CATEGORY 5: MAJOR STRATEGY** (use academic_structure.colleges[].majors[])
- Find student's intended major in the data
- Check if impacted, prerequisites, internal transfer difficulty
- Recommend backup major if appropriate

**CATEGORY 6: DEMONSTRATED INTEREST** (use application_process.holistic_factors.demonstrated_interest)
- If school tracks interest, give specific tactics
- Include interview policy guidance
- Mention any optional elements that show commitment

**CATEGORY 7: RED FLAGS TO AVOID** (use student_insights.red_flags)
- Customize school-specific warnings to this student
- What mistakes would hurt THIS student's application

**CATEGORY 8: TOP STRATEGIC RECOMMENDATIONS** (synthesize all analysis)
- 3 most impactful actions this student should take
- Each must address a gap and reference school-specific context

**OUTPUT FORMAT - Return ONLY valid JSON:**
{{
  "match_percentage": <integer 0-100>,
  "fit_category": "<SAFETY|TARGET|REACH|SUPER_REACH>",
  "explanation": "<5-6 sentence analysis: Start with category justification citing acceptance rate. Mention 2-3 specific student strengths. Acknowledge gaps. End with what could strengthen the application.>",
  "factors": [
    {{ "name": "Academic", "score": <0-40>, "max": 40, "detail": "<cite actual GPA/scores from profile vs school's admitted profile>" }},
    {{ "name": "Holistic", "score": <0-30>, "max": 30, "detail": "<cite specific activities/leadership from profile>" }},
    {{ "name": "Major Fit", "score": <0-15>, "max": 15, "detail": "<assess major availability and student's demonstrated interest>" }},
    {{ "name": "Selectivity", "score": <-15 to +5>, "max": 5, "detail": "<{acceptance_rate}% acceptance rate impact>" }}
  ],
  "gap_analysis": {{
    "primary_gap": "<name of factor with lowest % score and why>",
    "secondary_gap": "<name of second lowest % score factor and why>",
    "student_strengths": ["<specific strength 1>", "<specific strength 2>", "<specific strength 3>"]
  }},
  "essay_angles": [
    {{
      "essay_prompt": "<actual essay prompt from school if available, or 'Why Us' / 'Personal Statement'>",
      "angle": "<specific angle for this student to take>",
      "student_hook": "<specific experience from their profile to highlight>",
      "school_hook": "<specific program/value/resource at {uni_name} to reference>",
      "word_limit": <word limit if known, or null>,
      "tip": "<relevant tip from student_insights.essay_tips if available>"
    }}
  ],
  "application_timeline": {{
    "recommended_plan": "<Early Decision I|Early Decision II|Early Action|Regular Decision|Rolling>",
    "deadline": "<date in YYYY-MM-DD format>",
    "is_binding": <true|false>,
    "rationale": "<why this plan is best for this student's profile and circumstances>",
    "financial_aid_deadline": "<date if different from app deadline>",
    "key_milestones": [
      "<milestone 1 with date, e.g., 'Request teacher recs by October 1'>",
      "<milestone 2 with date>",
      "<milestone 3 with date>"
    ]
  }},
  "scholarship_matches": [
    {{
      "name": "<scholarship name from financials.scholarships>",
      "amount": "<amount or range>",
      "deadline": "<deadline or 'automatic consideration'>",
      "match_reason": "<why this student qualifies - cite specific profile elements>",
      "application_method": "<how to apply>"
    }}
  ],
  "test_strategy": {{
    "recommendation": "<Submit|Don't Submit|Consider Submitting>",
    "student_sat": <student's SAT if available, or null>,
    "student_act": <student's ACT if available, or null>,
    "school_sat_middle_50": "<e.g., 1340-1500>",
    "school_act_middle_50": "<e.g., 30-33>",
    "school_submission_rate": <percentage of applicants who submit>,
    "student_score_position": "<above|in|below> middle 50%",
    "rationale": "<explanation of why submit or not>"
  }},
  "major_strategy": {{
    "intended_major": "<student's intended major>",
    "is_available": <true|false>,
    "college_within_university": "<which college/school offers this major>",
    "is_impacted": <true|false|unknown>,
    "acceptance_rate_estimate": <if available, or null>,
    "prerequisites_met": "<assessment of whether student has needed courses>",
    "backup_major": "<recommended alternative major at this school>",
    "internal_transfer_difficulty": "<easy|moderate|difficult|unknown>",
    "strategic_tip": "<from application_strategy.major_selection_tactics if relevant>"
  }},
  "demonstrated_interest_tips": [
    "<specific tactic 1 based on school's DI tracking>",
    "<specific tactic 2>",
    "<specific tactic 3>"
  ],
  "red_flags_to_avoid": [
    "<specific red flag from student_insights.red_flags customized to this student>",
    "<another relevant red flag>"
  ],
  "recommendations": [
    {{
      "action": "<specific, actionable recommendation>",
      "addresses_gap": "<which factor this improves: Academic|Holistic|Major Fit>",
      "school_specific_context": "<how this connects to {uni_name}'s specific programs/values/resources>",
      "timeline": "<when to do this: before application|during senior year|in essays|etc>",
      "impact": "<how this strengthens the application>"
    }},
    {{
      "action": "<second most important recommendation>",
      "addresses_gap": "<which factor>",
      "school_specific_context": "<school-specific connection>",
      "timeline": "<when>",
      "impact": "<outcome>"
    }},
    {{
      "action": "<third most important recommendation>",
      "addresses_gap": "<which factor>",
      "school_specific_context": "<school-specific connection>",
      "timeline": "<when>",
      "impact": "<outcome>"
    }}
  ]
}}"""

        # Call Gemini with retry logic
        max_retries = 2
        client = genai.Client(api_key=GEMINI_API_KEY)
        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=prompt
                )
                
                # Parse output
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```'):
                    lines = response_text.split('\n')
                    start_idx = 1 if lines[0].startswith('```') else 0
                    end_idx = len(lines) - 1 if lines[-1] == '```' else len(lines)
                    response_text = '\n'.join(lines[start_idx:end_idx])
                    if response_text.startswith('json'):
                        response_text = response_text[4:].strip()
                
                result = json.loads(response_text)
                
                # Validate required fields
                if 'fit_category' not in result or 'match_percentage' not in result:
                    raise ValueError("Missing required fields in LLM response")
                
                # === POST-PROCESSING: SELECTIVITY OVERRIDE ===
                original_category = result['fit_category']
                
                # Apply selectivity floor - this CANNOT be overridden
                if category_floor == "SUPER_REACH" and original_category in ['SAFETY', 'TARGET', 'REACH']:
                    result['fit_category'] = 'SUPER_REACH'
                    logger.info(f"[FIT_COMP] Selectivity override: {original_category} -> SUPER_REACH (acceptance rate {acceptance_rate}%)")
                elif category_floor == "REACH" and original_category in ['SAFETY', 'TARGET']:
                    result['fit_category'] = 'REACH'
                    logger.info(f"[FIT_COMP] Selectivity override: {original_category} -> REACH (acceptance rate {acceptance_rate}%)")
                elif category_floor == "TARGET" and original_category == 'SAFETY':
                    result['fit_category'] = 'TARGET'
                    logger.info(f"[FIT_COMP] Selectivity override: {original_category} -> TARGET (acceptance rate {acceptance_rate}%)")
                
                # === POST-PROCESSING: SELECTIVITY CEILING ===
                # Enforce alignment with soft_fit_category thresholds
                if acceptance_rate >= 50 and result['fit_category'] in ['TARGET', 'REACH', 'SUPER_REACH']:
                    logger.info(f"[FIT_COMP] Ceiling override: {result['fit_category']} -> SAFETY (acceptance rate {acceptance_rate}% >= 50%)")
                    result['fit_category'] = 'SAFETY'
                elif acceptance_rate >= 25 and result['fit_category'] in ['REACH', 'SUPER_REACH']:
                    logger.info(f"[FIT_COMP] Ceiling override: {result['fit_category']} -> TARGET (acceptance rate {acceptance_rate}% >= 25%)")
                    result['fit_category'] = 'TARGET'
                
                # Validate category is in allowed list
                valid_categories = ['SAFETY', 'TARGET', 'REACH', 'SUPER_REACH']
                if result['fit_category'] not in valid_categories:
                    result['fit_category'] = 'REACH'
                
                # === POST-PROCESSING: ENSURE MATCH_PERCENTAGE ALIGNS WITH CATEGORY ===
                # This prevents LLM from giving inconsistent percentages for same category
                original_percentage = result['match_percentage']
                category = result['fit_category']
                
                # Define percentage ranges for each category
                # SUPER_REACH: 0-34, REACH: 35-54, TARGET: 55-74, SAFETY: 75-100
                if category == 'SUPER_REACH':
                    # Cap at 34% for SUPER_REACH schools
                    if result['match_percentage'] > 34:
                        result['match_percentage'] = min(34, max(15, result['match_percentage'] - 30))
                        logger.info(f"[FIT_COMP] Match% adjusted: {original_percentage} -> {result['match_percentage']} (SUPER_REACH cap)")
                elif category == 'REACH':
                    # Clamp to 35-54% for REACH schools
                    if result['match_percentage'] < 35:
                        result['match_percentage'] = 35
                    elif result['match_percentage'] > 54:
                        result['match_percentage'] = 54
                    if original_percentage != result['match_percentage']:
                        logger.info(f"[FIT_COMP] Match% adjusted: {original_percentage} -> {result['match_percentage']} (REACH range)")
                elif category == 'TARGET':
                    # Clamp to 55-74% for TARGET schools
                    if result['match_percentage'] < 55:
                        result['match_percentage'] = 55
                    elif result['match_percentage'] > 74:
                        result['match_percentage'] = 74
                    if original_percentage != result['match_percentage']:
                        logger.info(f"[FIT_COMP] Match% adjusted: {original_percentage} -> {result['match_percentage']} (TARGET range)")
                elif category == 'SAFETY':
                    # Clamp to 75-100% for SAFETY schools
                    if result['match_percentage'] < 75:
                        result['match_percentage'] = 75
                    if original_percentage != result['match_percentage']:
                        logger.info(f"[FIT_COMP] Match% adjusted: {original_percentage} -> {result['match_percentage']} (SAFETY floor)")
                
                # Add metadata
                result['university_name'] = uni_name
                result['calculated_at'] = datetime.utcnow().isoformat()
                result['selectivity_tier'] = selectivity_tier
                result['acceptance_rate'] = acceptance_rate
                
                logger.info(f"[FIT_COMP] {uni_name}: {result['fit_category']} ({result['match_percentage']}%) - Selectivity: {selectivity_tier}")
                return result
                
            except json.JSONDecodeError as je:
                logger.warning(f"[FIT_COMP] JSON parse error (attempt {attempt+1}): {str(je)[:100]}")
                if attempt < max_retries:
                    time.sleep(0.5)
                    continue
                raise
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning(f"[FIT_COMP] Rate limited, waiting... (attempt {attempt+1})")
                    time.sleep(2 ** attempt)
                    continue
                raise

    except Exception as e:
        logger.error(f"[FIT_COMP_ERROR] {uni_name if 'uni_name' in dir() else 'Unknown'}: {str(e)}")
        # Return a sensible fallback based on acceptance rate
        if acceptance_rate < 8:
            fallback_category = 'SUPER_REACH'
        elif acceptance_rate < 15:
            fallback_category = 'REACH'
        elif acceptance_rate < 40:
            fallback_category = 'TARGET'
        else:
            fallback_category = 'SAFETY'
            
        return {
            "fit_category": fallback_category,
            "match_percentage": 50,
            "explanation": f"Detailed analysis unavailable. Based on {acceptance_rate}% acceptance rate ({selectivity_tier if 'selectivity_tier' in dir() else 'unknown selectivity'}), categorized as {fallback_category}.",
            "factors": [
                {"name": "Academic", "score": 20, "max": 40, "detail": "Unable to fully analyze"},
                {"name": "Holistic", "score": 15, "max": 30, "detail": "Unable to fully analyze"},
                {"name": "Major Fit", "score": 8, "max": 15, "detail": "Unable to fully analyze"},
                {"name": "Selectivity", "score": 0, "max": 5, "detail": f"{acceptance_rate}% acceptance rate"}
            ],
            "recommendations": ["Complete profile for accurate analysis"],
            "university_name": university_data.get('metadata', {}).get('official_name', 'University'),
            "calculated_at": datetime.utcnow().isoformat(),
            "selectivity_tier": selectivity_tier if 'selectivity_tier' in dir() else "UNKNOWN",
            "acceptance_rate": acceptance_rate
        }


def calculate_fit_for_college(user_id, university_id, intended_major=''):
    """
    Calculate fit analysis for a specific college.
    Fetches student profile from Firestore and university data from KB, then calculates fit.
    This is the main orchestrator function - EXACT logic from ES version.
    """
    try:
        db = get_db()
        
        # Get student profile from Firestore
        profile_doc = db.get_profile(user_id)
        
        if not profile_doc:
            logger.warning(f"[FIT_COMP] No profile found for user: {user_id}")
            return None
        
        # Pass the ENTIRE student profile as JSON to the LLM
        # Remove internal/metadata fields that aren't useful
        fields_to_exclude = ['indexed_at', 'updated_at', 'created_at', '_id', 'embedding', 'chunk_id', 'user_id']
        profile_data_clean = {k: v for k, v in profile_doc.items() if k not in fields_to_exclude and v}
        
        # Also get the content field for backwards compatibility
        profile_content = profile_doc.get('raw_content') or profile_doc.get('content', '')
        if not profile_content or len(profile_content.strip()) < 50:
            logger.info(f"[FIT_COMP] Building profile content from flat fields for {user_id}")
            profile_content = build_profile_content_from_fields(profile_doc)
        
        # Log profile summary
        logger.info(f"[FIT_COMP] Student profile has {len(profile_data_clean)} fields, content length: {len(profile_content)}")
        
        # Parse student profile (for legacy code compatibility)
        student_profile = parse_student_profile(profile_content)
        
        # Fetch university data via KB API
        university_data = fetch_university_profile(university_id)
        
        if university_data:
            # Log the acceptance rate for debugging
            profile_data = university_data.get('profile', university_data)
            admissions = profile_data.get('admissions_data', {})
            current_status = admissions.get('current_status', {})
            acc_rate = current_status.get('overall_acceptance_rate') or university_data.get('acceptance_rate', 'N/A')
            logger.info(f"[FIT_COMP] Fetched university {university_id}: acceptance_rate={acc_rate}%")
        
        if not university_data:
            logger.warning(f"[FIT_COMP] University data not found: {university_id}")
            return {
                'fit_category': 'TARGET',
                'match_percentage': 50,
                'factors': [{'name': 'Data Unavailable', 'score': 0, 'max': 0, 'detail': 'University data not in knowledge base'}],
                'recommendations': ['University data not available for analysis'],
                'university_name': university_id.replace('_', ' ').title(),
                'calculated_at': datetime.utcnow().isoformat()
            }
        
        # Calculate comprehensive fit using PURE LLM reasoning
        # Pass BOTH the text content AND the full profile JSON
        fit_analysis = calculate_fit_with_llm(profile_content, university_data, intended_major, profile_data_clean)
        
        logger.info(f"[FIT_COMP] Calculated fit for {user_id} -> {university_id}: {fit_analysis['fit_category']} ({fit_analysis['match_percentage']}%)")
        
        return fit_analysis
        
    except Exception as e:
        logger.error(f"[FIT_COMP ERROR] {str(e)}")
        return None
