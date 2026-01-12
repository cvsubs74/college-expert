"""
Gemini AI integration for profile document processing.
Handles markdown conversion and structured data extraction.
"""

import os
import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def extract_profile_content(raw_text, filename):
    """
    Extract and format student profile using Gemini.
    Converts raw text to clean Markdown AND structured JSON.
    
    Args:
        raw_text: Raw extracted text from PDF/DOCX
        filename: Original filename
        
    Returns:
        Dict with markdown content and structured profile data
    """
    try:
        # Convert to clean markdown
        content_markdown = convert_to_markdown(raw_text, filename)
        
        # Extract structured profile data (MATCH ES EXACTLY)
        structured_profile = extract_structured_profile_with_gemini(raw_text)
        
        return {
            "raw_content": raw_text,
            "content_markdown": content_markdown,
            "structured_profile": structured_profile,
            "filename": filename
        }
            
    except Exception as e:
        logger.error(f"[GEMINI_PROCESSING] Failed: {e}")
        return {
            "raw_content": raw_text,
            "content_markdown": f"# Student Profile\\n\\nError processing file: {str(e)}",
            "structured_profile": None,
            "error": str(e)
        }


def convert_to_markdown(raw_text: str, filename: str) -> str:
    """
    Use Gemini to convert raw profile text to clean, well-formatted Markdown.
    
    Args:
        raw_text: Raw text extracted from document
        filename: Original filename for context
        
    Returns:
        Clean markdown formatted text
    """
    try:
        api_key = GEMINI_API_KEY
        if not api_key:
            logger.error("[GEMINI] API key not configured")
            return f"# Student Profile\\n\\n{raw_text}"
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are a college admissions document formatter. Convert the following student profile content into a clean, well-formatted Markdown document.

IMPORTANT RULES:
1. Create clear section headers using ## for major sections (e.g., ## Academic Information, ## Extracurricular Activities)
2. Use bullet points (•) for lists
3. Preserve all data exactly as provided - don't add or remove information
4. Format GPAs, test scores, and grades clearly
5. Keep chronological information organized
6. Use **bold** for important labels (GPA, SAT, ACT, etc.)
7. Create tables for course lists or test scores if appropriate
8. Do not add commentary or analysis - just format the content

Content to format:
{raw_text[:20000]}

Return ONLY the formatted Markdown, no explanation."""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096
            )
        )
        
        if response and response.text:
            return response.text.strip()
        else:
            logger.warning("[GEMINI] No response for markdown conversion")
            return f"# Student Profile\\n\\n{raw_text}"
            
    except Exception as e:
        logger.error(f"[GEMINI] Markdown conversion failed: {e}")
        return f"# Student Profile\\n\\n{raw_text}"


def extract_structured_profile_with_gemini(raw_text: str) -> dict:
    """
    Extract complete structured profile from raw text using Gemini.
    Returns FLATTENED JSON with top-level fields for Firestore.
    COPIED EXACTLY FROM profile_manager_es FOR COMPATIBILITY.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("[GEMINI] No API key, returning empty structured profile")
            return None
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Extract ALL information from this student profile into structured JSON.
Be thorough - extract EVERY piece of information present. Use null for missing fields.

STUDENT PROFILE TEXT:
{raw_text[:20000]}

REQUIRED JSON SCHEMA (FLAT structure - all fields at top level):
{{
  "name": "student's full name or null",
  "school": "high school name or null",
  "location": "city, state or null",
  "grade": integer 9-12 or null,
  "graduation_year": integer or null,
  "intended_major": "primary intended major or null",
  
  "gpa_weighted": float or null,
  "gpa_unweighted": float or null,
  "gpa_uc": float or null,
  "class_rank": "e.g. '15/400' or null",
  
  "sat_total": integer or null,
  "sat_math": integer or null,
  "sat_reading": integer or null,
  "act_composite": integer or null,
  
  "ap_exams": [
    {{"subject": "AP Subject Name", "score": integer 1-5}}
  ],
  "courses": [
    {{
      "name": "course name",
      "type": "AP" or "Honors" or "IB" or "Regular",
      "grade_level": integer 9-12,
      "semester1_grade": "A" or "B+" etc or null,
      "semester2_grade": "A" or "B+" etc or null
    }}
  ],
  "extracurriculars": [
    {{
      "name": "activity name",
      "role": "position/role or null",
      "description": "brief description or null",
      "grades": "e.g. '9-12' or '11-12'",
      "hours_per_week": integer or null,
      "achievements": ["achievement 1", "achievement 2"]
    }}
  ],
  "leadership_roles": ["role 1", "role 2"],
  "special_programs": [
    {{"name": "program name", "description": "description or null", "grade": integer or null}}
  ],
  "awards": [
    {{"name": "award name", "grade": integer or null, "description": "description or null"}}
  ],
  "work_experience": [
    {{
      "employer": "company/organization name",
      "role": "job title",
      "grades": "e.g. '10-11'",
      "hours_per_week": integer or null,
      "description": "job description or null"
    }}
  ]
}}

EXTRACTION RULES:
1. Extract EVERY activity, course, award mentioned - don't summarize
2. For AP exams, include ALL subjects and scores found
3. For courses, categorize type based on name (AP Physics = "AP", Honors English = "Honors")
4. Parse grades like "A/A-" as semester1_grade: "A", semester2_grade: "A-"
5. For activities without hours, estimate based on involvement level or use null
6. Include ALL leadership positions in BOTH extracurriculars and leadership_roles
7. Return ONLY valid JSON, no markdown formatting or explanation

TRANSCRIPT-SPECIFIC RULES (IMPORTANT):
8. Look for "Cumulative" GPA - use cumulative weighted GPA for gpa_weighted, cumulative unweighted for gpa_unweighted
9. Extract EVERY course from ALL grade levels (9, 10, 11, 12) - parse markdown tables if present
10. For class rank, look for patterns like "1 of 487" or "15/400" - format as "1/487"
11. Extract graduation year from "Expected Graduation" or class year
12. Look for AP exam SCORES (1-5) separate from AP courses - scores are typically listed with year or after course tables

Return ONLY the JSON object."""

        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        response_text = response.text.strip()
        
        # Clean up response - remove markdown code blocks if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            start_idx = 1 if lines[0].startswith('```') else 0
            end_idx = len(lines) - 1 if lines[-1] == '```' else len(lines)
            response_text = '\n'.join(lines[start_idx:end_idx])
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
        
        profile = json.loads(response_text)
        
        # Ensure arrays exist (flattened structure)
        array_keys = ['courses', 'extracurriculars', 'leadership_roles', 'special_programs', 'awards', 'work_experience', 'ap_exams']
        for key in array_keys:
            if key not in profile or profile[key] is None:
                profile[key] = []
        
        # Enhanced logging for debugging
        logger.info(f"[GEMINI] Extracted flattened profile:")
        logger.info(f"  - Name: {profile.get('name')}, School: {profile.get('school')}")
        logger.info(f"  - GPA weighted: {profile.get('gpa_weighted')}, unweighted: {profile.get('gpa_unweighted')}")
        logger.info(f"  - SAT: {profile.get('sat_total')}, ACT: {profile.get('act_composite')}")
        logger.info(f"  - Class rank: {profile.get('class_rank')}, Grad year: {profile.get('graduation_year')}")
        logger.info(f"  - Courses: {len(profile.get('courses', []))}, AP exams: {len(profile.get('ap_exams', []))}")
        logger.info(f"  - Activities: {len(profile.get('extracurriculars', []))}, Awards: {len(profile.get('awards', []))}")
        return profile
        
    except json.JSONDecodeError as e:
        logger.error(f"[GEMINI] JSON parse error in structured extraction: {e}")
        if 'response_text' in locals():
            logger.error(f"[GEMINI] Response was: {response_text[:500]}...")
        return None
    except Exception as e:
        logger.error(f"[GEMINI] Structured extraction error: {e}")
        return None


# Keep old function for backwards compatibility but redirect to new one
def extract_structured_data(raw_text: str) -> dict:
    """Legacy function - redirects to extract_structured_profile_with_gemini"""
    return extract_structured_profile_with_gemini(raw_text)


def evaluate_profile_changes(old_content: str, new_content: str) -> dict:
    """
    Use LLM to determine if profile changes would affect college fit calculations.
    
    Args:
        old_content: Previous profile markdown
        new_content: New profile markdown
        
    Returns:
        Dict with should_recompute flag and reason
    """
    try:
        api_key = GEMINI_API_KEY
        if not api_key:
            return {"should_recompute": True, "reason": "Unable to evaluate changes"}
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Compare these two student profile versions and determine if college fit analysis should be recomputed.

Recompute if there are SIGNIFICANT changes to:
- GPA or test scores
- Major/intended field of study
- Awards or achievements
- Extracurricular activities
- Academic rigor (AP/IB courses)

DO NOT recompute for:
- Minor formatting changes
- Small additions to existing lists
- Typo corrections

OLD PROFILE:
{old_content[:5000]}

NEW PROFILE:
{new_content[:5000]}

Return JSON: {{"should_recompute": true/false, "reason": "brief explanation"}}"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        if response and response.text:
            result = json.loads(response.text)
            return result
        else:
            return {"should_recompute": True, "reason": "Unable to evaluate"}
            
    except Exception as e:
        logger.error(f"[GEMINI] Change evaluation failed: {e}")
        return {"should_recompute": True, "reason": f"Error: {str(e)}"}
