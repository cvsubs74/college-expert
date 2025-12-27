"""
Essay Copilot Module

Provides AI-powered essay writing assistance:
- Essay starters generation based on student profile + fit analysis + university profile
- Writing copilot suggestions (completion, next sentence, feedback)
- Draft feedback and authenticity checks
"""

import os
import json
import time
import logging
import requests
from datetime import datetime
from elasticsearch import Elasticsearch
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Environment configuration
ES_CLOUD_ID = os.getenv("ES_CLOUD_ID")
ES_API_KEY = os.getenv("ES_API_KEY")
ES_INDEX_NAME = os.getenv("ES_INDEX_NAME", "student_profiles")
ES_FITS_INDEX = os.getenv("ES_FITS_INDEX", "student_college_fits")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KNOWLEDGE_BASE_UNIVERSITIES_URL = os.getenv(
    "KNOWLEDGE_BASE_UNIVERSITIES_URL",
    "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
)


def get_elasticsearch_client():
    """Create and return Elasticsearch client."""
    try:
        client = Elasticsearch(
            cloud_id=ES_CLOUD_ID,
            api_key=ES_API_KEY,
            request_timeout=30
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Elasticsearch: {e}")
        raise


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


def get_student_profile(es_client, user_email: str) -> dict | None:
    """Fetch student profile from Elasticsearch."""
    try:
        query = {"query": {"term": {"user_id.keyword": user_email}}, "size": 1}
        response = es_client.search(index=ES_INDEX_NAME, body=query)
        
        if response['hits']['total']['value'] > 0:
            return response['hits']['hits'][0]['_source']
        return None
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error fetching student profile: {e}")
        return None


def get_fit_analysis(es_client, user_email: str, university_id: str) -> dict | None:
    """Fetch fit analysis for a student-university pair."""
    try:
        normalized_id = normalize_university_id(university_id)
        
        query = {
            "query": {
                "bool": {
                    "must": [{"term": {"user_email": user_email}}],
                    "should": [
                        {"term": {"university_id": university_id}},
                        {"term": {"university_id": normalized_id}}
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 1
        }
        
        response = es_client.search(index=ES_FITS_INDEX, body=query)
        
        if response['hits']['total']['value'] > 0:
            return response['hits']['hits'][0]['_source']
        return None
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Error fetching fit analysis: {e}")
        return None


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
        es_client = get_elasticsearch_client()
        
        # Fetch all context data
        student_profile = get_student_profile(es_client, user_email)
        fit_analysis = get_fit_analysis(es_client, user_email, university_id)
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
        system_prompt = f"""You are an expert college essay coach. Generate 3 different, compelling opening sentences/paragraphs for the given essay prompt.

ESSAY PROMPT:
"{prompt_text}"

{chr(10).join(context_parts)}

INSTRUCTIONS:
1. Each starter should be distinctly different in approach (e.g., anecdote, question, bold statement, sensory detail)
2. Make them PERSONAL to this specific student based on their profile and activities
3. Reference specific details about the university when relevant (professors, programs, culture)
4. Keep each starter to 1-3 sentences maximum
5. Make them authentic and conversational, not generic or cliché
6. If essay_angles from fit analysis are available, use those as inspiration

Return ONLY a JSON array of exactly 3 strings, no explanation:
["Starter 1...", "Starter 2...", "Starter 3..."]"""

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
        text = response.text.strip()
        
        # Clean markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        starters = json.loads(text)
        
        if not isinstance(starters, list) or len(starters) < 1:
            raise ValueError("Invalid response format")
        
        logger.info(f"[ESSAY_COPILOT] Generated {len(starters)} starters for {user_email}/{university_id}")
        
        return {
            "success": True,
            "starters": starters[:3],
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
    action: str = "suggest"
) -> dict:
    """
    Get real-time copilot suggestions while writing.
    
    Actions:
    - "complete": Complete the current sentence
    - "suggest": Suggest next sentence idea
    - "expand": Expand on the current thought
    
    Returns:
        dict with 'success', 'suggestion', 'type'
    """
    try:
        action_prompts = {
            "complete": f"""Complete this sentence naturally and authentically. The student is answering this essay prompt: "{prompt_text}"

Current text: "{current_text}"

Provide ONLY the completion (the remaining words to finish the current sentence). Keep it concise and personal.""",

            "suggest": f"""The student is writing a college essay for this prompt: "{prompt_text}"

What they've written so far: "{current_text}"

Suggest ONE natural next sentence they could write. Make it flow naturally from what they've written. Return ONLY the suggested sentence, no explanation.""",

            "expand": f"""The student is writing a college essay for this prompt: "{prompt_text}"

Current text: "{current_text}"

Suggest how they could expand on or deepen their last point with more specific detail or reflection. Return ONLY 1-2 sentences they could add."""
        }
        
        if action not in action_prompts:
            action = "suggest"
        
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
            "suggestion": suggestion,
            "type": action
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Copilot suggestion failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "suggestion": ""
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
    notes: list = None
) -> dict:
    """
    Save essay draft to Elasticsearch.
    
    Args:
        user_email: User's email
        university_id: University ID
        prompt_index: Index of the prompt (0-based)
        prompt_text: The essay prompt text
        draft_text: The essay draft content
        notes: List of brainstorming notes
    
    Returns:
        dict with 'success' and 'doc_id'
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Create unique document ID
        doc_id = f"{user_email}_{university_id}_{prompt_index}"
        
        # Build document
        doc = {
            "user_email": user_email,
            "university_id": university_id,
            "prompt_index": prompt_index,
            "prompt_text": prompt_text,
            "draft_text": draft_text,
            "notes": notes or [],
            "word_count": len(draft_text.split()) if draft_text else 0,
            "updated_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Check if document exists to preserve created_at
        try:
            existing = es_client.get(index=ES_ESSAY_DRAFTS_INDEX, id=doc_id)
            doc["created_at"] = existing["_source"].get("created_at", doc["created_at"])
        except:
            pass
        
        # Upsert document
        es_client.index(index=ES_ESSAY_DRAFTS_INDEX, id=doc_id, body=doc)
        
        logger.info(f"[ESSAY_COPILOT] Saved draft: {doc_id}, {doc['word_count']} words")
        
        return {
            "success": True,
            "doc_id": doc_id,
            "word_count": doc["word_count"],
            "updated_at": doc["updated_at"]
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Save draft failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_essay_drafts(
    user_email: str,
    university_id: str = None
) -> dict:
    """
    Get all essay drafts for a user, optionally filtered by university.
    
    Args:
        user_email: User's email
        university_id: Optional university ID to filter by
    
    Returns:
        dict with 'success' and 'drafts' (list of draft objects)
    """
    try:
        es_client = get_elasticsearch_client()
        
        # Build query - use .keyword for exact matching on text fields
        must_clauses = [{"term": {"user_email.keyword": user_email}}]
        
        if university_id:
            normalized_id = normalize_university_id(university_id)
            must_clauses.append({
                "bool": {
                    "should": [
                        {"term": {"university_id.keyword": university_id}},
                        {"term": {"university_id.keyword": normalized_id}}
                    ],
                    "minimum_should_match": 1
                }
            })
        
        query = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"updated_at": {"order": "desc"}}],
            "size": 100
        }
        
        response = es_client.search(index=ES_ESSAY_DRAFTS_INDEX, body=query)
        
        drafts = []
        for hit in response["hits"]["hits"]:
            draft = hit["_source"]
            draft["doc_id"] = hit["_id"]
            drafts.append(draft)
        
        logger.info(f"[ESSAY_COPILOT] Retrieved {len(drafts)} drafts for {user_email}")
        
        return {
            "success": True,
            "drafts": drafts,
            "count": len(drafts)
        }
        
    except Exception as e:
        logger.error(f"[ESSAY_COPILOT] Get drafts failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "drafts": []
        }

