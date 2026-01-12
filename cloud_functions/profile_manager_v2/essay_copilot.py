"""
Essay Copilot Module

Provides AI-powered essay writing assistance:
- Essay starters generation based on student profile + fit analysis + university profile
- Writing copilot suggestions (completion, next sentence, feedback)
- Draft feedback and authenticity checks
"""

import os
import logging
import json
import time
import requests
from google import genai
from google.genai import types
from firestore_db import get_db  # Use Firestore instead of ES

logger = logging.getLogger(__name__)

# Environment configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KNOWLEDGE_BASE_UNIVERSITIES_URL = os.getenv(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)


def normalize_university_id(university_id: str) -> str:
    """Normalize university ID for consistent matching."""
    if not university_id:
        return ''
    
    normalized = university_id.lower().strip()
    
    if normalized.startswith('the_'):
        normalized = normalized[4:]
    
    if normalized.endswith('_slug'):
        normalized = normalized[:-5]
    
    normalized = normalized.replace('-', '_').replace(' ', '_')
    
    while '__' in normalized:
        normalized = normalized.replace('__', '_')
    
    return normalized


def fetch_university_profile(university_id: str, max_retries: int = 3) -> dict | None:
    """Fetch full university profile from knowledge base."""
    candidate_ids = [
        university_id.strip(),
        f"{university_id.strip()}_slug",
        university_id.lower().strip(),
        f"{university_id.lower().strip()}_slug"
    ]
    
    for uid in candidate_ids:
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{KNOWLEDGE_BASE_UNIVERSITIES_URL}?university_id={uid}",
                    timeout=30
                )
                data = response.json()
                
                if data.get('success') and data.get('university'):
                    logger.info(f"[ESSAY_COPILOT] Found university: {uid}")
                    return data['university']
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"[ESSAY_COPILOT] Error fetching {uid} (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"[ESSAY_COPILOT] Unexpected error: {e}")
                break
    
    logger.warning(f"[ESSAY_COPILOT] University not found: {university_id}")
    return None


def get_student_profile(user_email: str) -> dict | None:
    """Fetch student profile from Firestore."""
    try:
        db = get_db()
        profile = db.get_profile(user_email)
        return profile
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error fetching student profile: {e}")
        return None


def get_fit_analysis(user_email: str, university_id: str) -> dict | None:
    """Fetch fit analysis for a student-university pair from Firestore."""
    try:
        db = get_db()
        fit = db.get_college_fit(user_email, university_id)
        
        # Also try normalized ID
        if not fit:
            normalized_id = normalize_university_id(university_id)
            fit = db.get_college_fit(user_email, normalized_id)
        
        return fit
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error fetching fit analysis: {e}")
        return None


def get_starter_context(
    user_email: str,
    university_id: str,
    selected_hook: str,
    prompt_text: str
) -> dict:
    """
    Get LLM-synthesized writing pointers for a selected coaching hook.
    Uses profile, university, and fit data to generate personalized guidance.
    """
    try:
        # Fetch all context data
        student_profile = get_student_profile(user_email)
        fit_analysis = get_fit_analysis(user_email, university_id)
        university_profile = fetch_university_profile(university_id)
        
        # Build context summary for LLM
        context_parts = []
        
        if student_profile:
            activities = student_profile.get('activities', [])
            activities_str = ', '.join([
                a.get('name', str(a)) if isinstance(a, dict) else str(a) 
                for a in activities[:6]
            ])
            awards = student_profile.get('honors_awards', student_profile.get('awards', []))
            awards_str = ', '.join([
                a.get('name', str(a)) if isinstance(a, dict) else str(a) 
                for a in awards[:4]
            ])
            interests = student_profile.get('academic_interests', [])
            interests_str = ', '.join(interests[:4]) if interests else ''
            
            context_parts.append(f"""STUDENT PROFILE:
- Activities: {activities_str}
- Awards: {awards_str}
- Academic Interests: {interests_str}
- Intended Major: {student_profile.get('intended_major', 'Not specified')}""")
        
        if university_profile:
            profile_data = university_profile.get('profile', university_profile)
            colleges = profile_data.get('academic_structure', {}).get('colleges', [])
            colleges_str = ', '.join([
                c.get('name', str(c)) if isinstance(c, dict) else str(c) 
                for c in colleges[:4]
            ])
            faculty = profile_data.get('academics', {}).get('notable_faculty', [])
            faculty_str = ', '.join([
                f.get('name', str(f)) if isinstance(f, dict) else str(f) 
                for f in faculty[:4]
            ])
            
            context_parts.append(f"""UNIVERSITY ({university_id}):
- Schools/Colleges: {colleges_str}
- Notable Faculty: {faculty_str}""")
        
        if fit_analysis:
            summary = fit_analysis.get('match_summary', fit_analysis.get('summary', ''))
            angles = fit_analysis.get('essay_angles', [])[:2]
            context_parts.append(f"""FIT ANALYSIS:
- Summary: {summary[:200] if summary else 'N/A'}
- Recommended angles: {json.dumps(angles, default=str)[:200]}""")
        
        # Call LLM to synthesize pointers
        system_prompt = f"""You are an expert college essay coach. A student has selected this writing prompt/hook:

SELECTED HOOK: "{selected_hook}"

ESSAY PROMPT: "{prompt_text}"

{chr(10).join(context_parts)}

Based on the hook and the student's background, generate 4-5 specific, actionable WRITING POINTERS that will help them write an authentic response. Each pointer should:
1. Connect a SPECIFIC detail from their profile/activities to the hook
2. Suggest what to explore or remember
3. Be personal and concrete, not generic

Return ONLY a JSON array of pointers (strings), each 1-2 sentences:
["Pointer 1...", "Pointer 2...", "Pointer 3...", "Pointer 4..."]

Examples of good pointers:
- "Think about the moment in your Key Club recycling initiative when you first saw the community respond - what was that feeling?"
- "Consider how your California Scholastic Press Award connects to wanting to make an impact through storytelling at Emory"
- "The Goizueta Business School's focus on community-minded leadership aligns with your Key Club work - explore how"
"""

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[types.Content(role="user", parts=[types.Part(text=system_prompt)])],
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=600
            )
        )
        
        text = response.text.strip() if response.text else ""
        
        # Clean markdown if present
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        text = text.strip()
        
        # Parse pointers
        pointers = []
        if text:
            try:
                pointers = json.loads(text)
                # Normalize to strings
                pointers = [str(p) if not isinstance(p, str) else p for p in pointers[:5]]
            except:
                # If parsing fails, split by newlines
                pointers = [line.strip() for line in text.split('\n') if line.strip() and len(line) > 10][:5]
        
        logger.info(f"[ESSAY_COPILOT] Generated {len(pointers)} synthesized pointers")
        
        return {
            "success": True,
            "hook": selected_hook,
            "prompt": prompt_text,
            "pointers": pointers,  # Now returns synthesized pointers instead of raw facts
            "profile_facts": [],   # Keep for backward compatibility
            "university_facts": [],
            "fit_insights": []
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Context retrieval failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "hook": selected_hook,
            "pointers": [],
            "profile_facts": [],
            "university_facts": [],
            "fit_insights": []
        }



def generate_essay_starters(
    user_email: str,
    university_id: str,
    prompt_text: str,
    notes: str = ""
) -> dict:
    """
    Generate personalized essay opening sentences based on:
    - Student profile
    - Fit analysis (essay_angles, recommendations)
    - Full university profile (programs, professors, culture)
    - User's brainstorming notes
    
    Returns:
        dict with 'success', 'starters' (list of 3 openers), and 'context_used'
    """
    try:
        # Fetch all context data
        student_profile = get_student_profile(user_email)
        fit_analysis = get_fit_analysis(user_email, university_id)
        university_profile = fetch_university_profile(university_id)
        
        # Build context for LLM
        context_parts = []
        context_used = []
        
        # Student profile context
        if student_profile:
            # Extract key student info
            student_summary = {
                "name": student_profile.get("full_name", ""),
                "intended_major": student_profile.get("intended_major", ""),
                "interests": student_profile.get("academic_interests", []),
                "activities": student_profile.get("activities", []),
                "achievements": student_profile.get("honors_awards", []),
                "personal_qualities": student_profile.get("personal_qualities", [])
            }
            context_parts.append(f"STUDENT PROFILE:\n{json.dumps(student_summary, indent=2, default=str)}")
            context_used.append("student_profile")
        
        # Fit analysis context (essay angles, recommendations)
        if fit_analysis:
            essay_angles = fit_analysis.get("essay_angles", [])
            recommendations = fit_analysis.get("recommendations", [])
            fit_summary = {
                "essay_angles": essay_angles,
                "recommendations": recommendations,
                "fit_category": fit_analysis.get("fit_category"),
                "match_score": fit_analysis.get("match_score")
            }
            context_parts.append(f"FIT ANALYSIS (personalized insights):\n{json.dumps(fit_summary, indent=2, default=str)}")
            context_used.append("fit_analysis")
        
        # University profile context
        if university_profile:
            profile_data = university_profile.get('profile', university_profile)
            
            # Extract relevant sections
            uni_context = {
                "name": profile_data.get("metadata", {}).get("official_name", ""),
                "academic_programs": profile_data.get("academic_structure", {}).get("colleges", [])[:3],  # Top 3 colleges
                "culture": profile_data.get("student_life", {}).get("campus_culture", ""),
                "research": profile_data.get("academic_structure", {}).get("research_opportunities", [])[:5],
                "notable_faculty": profile_data.get("academics", {}).get("notable_faculty", [])[:3],
                "essay_tips": profile_data.get("student_insights", {}).get("essay_tips", [])
            }
            context_parts.append(f"UNIVERSITY PROFILE:\n{json.dumps(uni_context, indent=2, default=str)}")
            context_used.append("university_profile")
        
        # User notes
        if notes and notes.strip():
            context_parts.append(f"STUDENT'S BRAINSTORMING NOTES:\n{notes}")
            context_used.append("notes")
        
        # Build the prompt
        system_prompt = f"""You are an expert college essay coach. Instead of writing the essay for the student, generate 3 different COACHING HOOKS that push the student to write their own authentic opening.

ESSAY PROMPT:
"{prompt_text}"

{chr(10).join(context_parts)}

CRITICAL INSTRUCTIONS - COACHING APPROACH:
1. DO NOT write complete sentences the student can copy. Instead provide:
   - A thought-provoking question to reflect on
   - A memory/moment to explore from their activities
   - A "What if you started with..." prompt
   
2. Each hook should take a distinctly different approach:
   - HOOK 1: "Recall a moment when..." - Point to a specific experience from their activities
   - HOOK 2: "What feeling or realization..." - Push reflection on emotions/growth
   - HOOK 3: "Consider starting with..." - Suggest a technique (dialogue, sensory detail, question to reader)

3. Make them PERSONAL to this student's actual profile and activities
4. **ONLY reference real data from the UNIVERSITY PROFILE above - no invented names**
5. Keep each hook to 1-2 sentences max - they are prompts, not essays

Return ONLY a JSON array of exactly 3 coaching hooks (not complete essay sentences):
["Hook 1: Recall the moment when...", "Hook 2: What did it feel like when...", "Hook 3: Try opening with..."]"""

        # Call Gemini
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[types.Content(role="user", parts=[types.Part(text=system_prompt)])],
            config=types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=1024
            )
        )
        
        # Parse response
        text = response.text.strip() if response.text else ""
        
        logger.info(f"[ESSAY_COPILOT] Raw LLM response (first 500 chars): {text[:500]}")
        
        # Handle empty response
        if not text:
            raise ValueError("LLM returned empty response")
        
        # Clean markdown if present
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        text = text.strip()
        
        # Handle case where text is still empty after cleaning
        if not text:
            raise ValueError("LLM response was empty after cleaning")
        
        starters = json.loads(text)
        
        if not isinstance(starters, list) or len(starters) < 1:
            raise ValueError("Invalid response format")
        
        # Normalize: ensure all items are plain strings (LLM sometimes returns objects)
        normalized_starters = []
        for s in starters[:3]:
            if isinstance(s, dict):
                # Extract the prompt/hook from object format
                normalized_starters.append(s.get('prompt', s.get('hook', str(s))))
            else:
                normalized_starters.append(str(s))
        
        logger.info(f"[ESSAY_COPILOT] Generated {len(normalized_starters)} starters for {user_email}/{university_id}")
        
        return {
            "success": True,
            "starters": normalized_starters,
            "context_used": context_used,
            "prompt": prompt_text
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Starters generation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "starters": []
        }


def get_copilot_suggestion(
    prompt_text: str,
    current_text: str,
    action: str = "suggest",
    university_id: str = "",
    user_email: str = ""
) -> dict:
    """
    Get real-time copilot suggestions while writing.
    
    Actions:
    - "complete": Complete the current sentence
    - "suggest": Suggest 3 different next sentence options
    - "expand": Expand on the current thought
    
    Returns:
        dict with 'success', 'suggestions' (list for suggest, single for others), 'type'
    """
    try:
        # For 'suggest', we want multiple coaching pointers
        if action == "suggest":
            system_prompt = f"""The student is writing a college essay for this prompt: "{prompt_text}"

What they've written so far: "{current_text}"

As a writing coach, give 3 different POINTERS to help them decide what to write next. DO NOT write sentences for them. Instead provide:

1. REFLECTION POINTER: Ask a question about their feelings, realizations, or growth related to what they just wrote
   Example: "What did you learn about yourself in that moment?"
   
2. DETAIL POINTER: Suggest adding sensory details or specifics
   Example: "Can you describe what you saw, heard, or felt physically?"
   
3. CONNECTION POINTER: Suggest how to connect this to the bigger picture (their goals, the university, their growth)
   Example: "How does this connect to why you want to study [their intended major]?"

Keep each pointer to ONE short question or prompt. These should push the student to think, not give them the answer.

Return ONLY a JSON array of 3 coaching pointers:
["Reflection: What did...", "Detail: Describe...", "Connection: How does..."]"""
            
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[types.Content(role="user", parts=[types.Part(text=system_prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=512
                )
            )
            
            text = response.text.strip()
            # Clean markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            suggestions = json.loads(text)
            if not isinstance(suggestions, list):
                suggestions = [suggestions]
            
            # Normalize: ensure all items are plain strings (LLM sometimes returns objects)
            normalized = []
            for s in suggestions[:3]:
                if isinstance(s, dict):
                    normalized.append(s.get('prompt', s.get('pointer', s.get('suggestion', str(s)))))
                else:
                    normalized.append(str(s))
            
            logger.info(f"[ESSAY_COPILOT] Generated {len(normalized)} suggestions")
            
            return {
                "success": True,
                "suggestions": normalized,
                "type": action
            }
        
        else:
            # For complete and expand, single coaching response
            action_prompts = {
                "complete": f"""The student is finishing a sentence for this essay prompt: "{prompt_text}"

Current text: "{current_text}"

As a coach, give ONE guiding question to help them complete their thought authentically. DO NOT write the completion for them.
Example: "What was the result of that action?" or "How did that make you feel?"
Keep it to one short question.""",

                "expand": f"""The student is writing a college essay for this prompt: "{prompt_text}"

Current text: "{current_text}"

As a coach, give ONE guiding prompt to help them deepen their last point. DO NOT write it for them. Instead ask:
- A question about specifics they could add (who, what, where, when)
- A question about the emotional impact or lesson learned
- A connection to make to their future goals

Keep it to one clear, thought-provoking question."""
            }
            
            if action not in action_prompts:
                action = "expand"
            
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[types.Content(role="user", parts=[types.Part(text=action_prompts[action])])],
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=256
                )
            )
            
            suggestion = response.text.strip()
            
            # Clean up quotes if present
            if suggestion.startswith('"') and suggestion.endswith('"'):
                suggestion = suggestion[1:-1]
            
            logger.info(f"[ESSAY_COPILOT] Generated {action} suggestion")
            
            return {
                "success": True,
                "suggestions": [suggestion],
                "type": action
            }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Copilot suggestion failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "suggestions": []
        }


def essay_chat(
    user_email: str,
    university_id: str,
    prompt_text: str,
    current_text: str,
    user_question: str
) -> dict:
    """
    Chat with AI about essay context - professors, classes, research, etc.
    Includes complete student profile, university profile, and fit analysis.
    
    Args:
        user_email: User's email for fetching profile
        university_id: University ID for context
        prompt_text: The essay prompt
        current_text: Current essay draft
        user_question: User's specific question
    
    Returns:
        dict with 'success', 'response', 'context_type'
    """
    try:
        # Fetch complete context
        student_profile = get_student_profile(user_email)
        university_profile = fetch_university_profile(university_id)
        
        # Get fit analysis if available
        fit_analysis = get_fit_analysis(user_email, university_id)
        if not fit_analysis:
            logger.warning(f"[ESSAY_CHAT] Fit analysis not found for {university_id}")
        
        # Build comprehensive context
        context_parts = []
        
        if student_profile:
            # Complete student profile
            activities = student_profile.get('activities', [])
            activities_str = ', '.join([a.get('name', a) if isinstance(a, dict) else str(a) for a in activities[:8]])
            qualities = student_profile.get('personal_qualities', [])[:5]
            qualities_str = ', '.join([q.get('name', q) if isinstance(q, dict) else str(q) for q in qualities])
            awards = student_profile.get('awards', [])[:5]
            awards_str = ', '.join([a.get('name', a) if isinstance(a, dict) else str(a) for a in awards])
            interests = student_profile.get('academic_interests', [])
            interests_str = ', '.join([i if isinstance(i, str) else str(i) for i in interests])
            
            context_parts.append(f"""COMPLETE STUDENT PROFILE:
- Name: {student_profile.get('name', 'Not specified')}
- Grade: {student_profile.get('grade', 'Not specified')}
- GPA: {student_profile.get('gpa', 'Not specified')}
- Intended Major: {student_profile.get('intended_major', 'Not specified')}
- Academic Interests: {interests_str}
- Career Goals: {student_profile.get('career_goals', 'Not specified')}
- Key Activities: {activities_str}
- Personal Qualities: {qualities_str}
- Awards/Honors: {awards_str}""")
        
        if university_profile:
            profile_data = university_profile.get('profile', university_profile)
            
            # Full university details
            academics = profile_data.get('academics', {})
            structure = profile_data.get('academic_structure', {})
            
            context_parts.append(f"""COMPLETE UNIVERSITY PROFILE:
- University: {profile_data.get('name', university_id)}
- Type: {profile_data.get('institution_type', 'Not specified')}
- Colleges/Schools: {json.dumps(structure.get('colleges', [])[:8], default=str)}
- Notable Programs: {json.dumps(academics.get('notable_programs', [])[:5], default=str)}
- Research Opportunities: {json.dumps(structure.get('research_opportunities', [])[:5], default=str)}
- Notable Faculty: {json.dumps(academics.get('notable_faculty', [])[:8], default=str)}
- Special Programs: {json.dumps(structure.get('special_programs', [])[:5], default=str)}
- Campus Culture: {profile_data.get('campus_life', {}).get('culture', 'Not specified')}""")
        
        if fit_analysis:
            context_parts.append(f"""FIT ANALYSIS FOR THIS STUDENT + UNIVERSITY:
- Overall Fit Score: {fit_analysis.get('overall_fit_score', 'N/A')}
- Academic Fit: {fit_analysis.get('academic_fit', {}).get('score', 'N/A')} - {fit_analysis.get('academic_fit', {}).get('summary', '')}
- Program Alignment: {json.dumps(fit_analysis.get('program_alignment', [])[:3], default=str)}
- Key Strengths: {json.dumps(fit_analysis.get('strengths', [])[:3], default=str)}
- Recommended Focus Areas: {json.dumps(fit_analysis.get('focus_areas', [])[:3], default=str)}""")
        
        system_prompt = f"""You are an expert college essay advisor helping a student write their essay. 

ESSAY PROMPT: "{prompt_text}"

CURRENT DRAFT: "{current_text[:500]}..."

{chr(10).join(context_parts)}

STUDENT'S QUESTION: "{user_question}"

CRITICAL RULES:
1. **ONLY reference professors, programs, classes, or research that are EXPLICITLY listed in the context above**
2. **DO NOT INVENT OR HALLUCINATE any names** - if a professor or program isn't in the provided data, say "Based on the available data, I don't have specific faculty names for that area. You may want to research [specific department]..."
3. If asked about something not in the context, clearly state the information isn't available
4. Keep the response concise (2-4 sentences max)
5. Suggest how they might incorporate accurate information into their essay"""

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[types.Content(role="user", parts=[types.Part(text=system_prompt)])],
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=400
            )
        )
        
        answer = response.text.strip()
        
        logger.info(f"[ESSAY_COPILOT] Chat response for: {user_question[:50]}...")
        
        return {
            "success": True,
            "response": answer,
            "question": user_question
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Chat failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "response": ""
        }


def get_draft_feedback(
    prompt_text: str,
    draft_text: str,
    university_name: str = ""
) -> dict:
    """
    Get detailed feedback on essay draft.
    
    Returns:
        dict with 'success', 'feedback' containing scores and suggestions
    """
    try:
        word_count = len(draft_text.split())
        
        system_prompt = f"""You are an expert college admissions essay reviewer. Analyze this essay draft and provide constructive feedback.

ESSAY PROMPT: "{prompt_text}"
UNIVERSITY: {university_name or "Not specified"}
WORD COUNT: {word_count}

DRAFT:
"{draft_text}"

Provide feedback in this exact JSON format:
{{
  "overall_score": <1-10>,
  "prompt_alignment": <1-10>,
  "authenticity": <1-10>,
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["specific improvement 1", "specific improvement 2"],
  "next_step": "One specific action to take next"
}}

Be encouraging but honest. Focus on specific, actionable feedback."""

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[types.Content(role="user", parts=[types.Part(text=system_prompt)])],
            config=types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=512
            )
        )
        
        text = response.text.strip()
        
        # Clean markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        feedback = json.loads(text)
        
        logger.info(f"[ESSAY_COPILOT] Generated draft feedback, score: {feedback.get('overall_score')}")
        
        return {
            "success": True,
            "feedback": feedback,
            "word_count": word_count
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Draft feedback failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "feedback": {}
        }


# Essay Draft Index
ES_ESSAY_DRAFTS_INDEX = os.getenv("ES_ESSAY_DRAFTS_INDEX", "essay_drafts")


def save_essay_draft(
    user_email: str,
    university_id: str,
    prompt_index: int,
    prompt_text: str,
    draft_text: str,
    notes: list = None,
    version: int = 0,
    version_name: str = ""
) -> dict:
    """
    Save essay draft to Elasticsearch.
    Supports multiple versions per prompt.
    
    Save essay draft to Firestore.
    
    Returns:
        dict with 'success' and 'draft_id'
    """
    try:
        from firestore_db import get_db
        db = get_db()
        
        # Create unique draft ID
        draft_id = f"prompt_{prompt_index}_v{version}"
        
        # Build draft document
        draft = {
            "university_id": university_id,
            "prompt_index": prompt_index,
            "prompt_text": prompt_text,
            "draft_text": draft_text,
            "notes": notes or [],
            "version": version,
            "version_name": version_name or (f"Version {version + 1}" if version > 0 else "Main Draft"),
            "word_count": len(draft_text.split()) if draft_text else 0,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Save to Firestore (will merge with existing or create new)
        success = db.save_conversation(user_email, draft_id, draft)  # Reusing conversation storage
        
        logger.info(f"[ESSAY_COPILOT] Saved draft: {draft_id}, {draft['word_count']} words")
        
        return {
            "success": success,
            "draft_id": draft_id,
            "version": version,
            "word_count": draft['word_count']
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Draft save failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
def get_essay_drafts(
    user_email: str,
    university_id: str = None
) -> dict:
    """
    Get all essay drafts for a user from Firestore.
    Optionally filter by university_id.
    
    Returns:
        dict with 'drafts' list
    """
    try:
        from firestore_db import get_db
        db = get_db()
        
        # Get all conversations (which include essay drafts)
        all_conversations = db.list_conversations(user_email)
        
        # Filter for essay drafts (those starting with "prompt_")
        drafts = []
        for conv in all_conversations:
            conv_id = conv.get('conversation_id', '')
            if conv_id.startswith('prompt_'):
                # Check university filter if provided
                if university_id and conv.get('university_id') != university_id:
                    continue
                drafts.append(conv)
        
        # Sort by updated_at descending
        drafts.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        logger.info(f"[ESSAY_COPILOT] Retrieved {len(drafts)} drafts for {user_email}")
        
        return {
            "success": True,
            "drafts": drafts,
            "count": len(drafts)
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Get drafts failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "drafts": []
        }
