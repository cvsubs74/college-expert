"""
Profile Chat Module
Provides a chat interface for answering questions about user profiles.
Does NOT update profiles or answer university-related questions.
"""

import os
import logging
import json
from google import genai
from google.genai import types
from firestore_db import get_db  # Use Firestore instead of ES

logger = logging.getLogger(__name__)

# Get configuration from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def profile_chat(user_id: str, question: str, conversation_history: list = None) -> dict:
    """
    Answer questions about the user's profile using their full profile data as context.
    
    RULES:
    - Only answers questions about the user's profile
    - Does NOT update or modify the profile
    - Does NOT answer university-related questions
    
    Args:
        user_id: The user's email
        question: User's question about their profile
        conversation_history: List of {role, content} dicts for context
    
    Returns:
        dict with answer, updated conversation history, and suggested follow-up questions
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        # Load user profile from Firestore
        db = get_db()
        user_profile = db.get_profile(user_id)
        
        if not user_profile:
            return {
                "success": False,
                "error": "No profile found. Please upload your profile documents first."
            }
        
        # Remove internal/metadata fields that aren't useful for the LLM
        fields_to_exclude = ['indexed_at', 'updated_at', 'created_at', '_id', 'embedding', 'chunk_id', 'user_id']
        profile_data = {k: v for k, v in user_profile.items() if k not in fields_to_exclude and v}
        
        # Build system prompt with profile context and restrictions
        import json
        profile_json = json.dumps(profile_data, indent=2)
        
        system_prompt = f"""You are a helpful assistant that answers questions about this student's profile.

PROFILE DATA:
{profile_json}

RULES:
1. Only answer questions about THIS specific student profile
2. Do NOT make any updates or changes to the profile
3. Do NOT answer questions about universities, colleges, or college admissions
4. If asked about universities, politely redirect: "I can only answer questions about your profile. For university information, please use the University Explorer."
5. If asked to update the profile, respond: "I can't update your profile. Please use the Profile Editor tab to make changes."
6. Be concise and accurate
7. If a field is empty or missing from the profile, say so clearly
8. Use friendly, conversational language
9. After answering, suggest 2-3 insightful follow-up questions that help the student reflect on their profile

Your response should be in JSON format:
{{
  "answer": "your response here",
  "suggested_questions": ["question 1", "question 2", "question 3"]
}}

The suggested questions MUST:
- Be 8 words or less (STRICT LIMIT)
- Be personal and reflective (use "my", "I")
- Help the student gain self-awareness
- Build on what was just discussed
- Be direct and conversational

GOOD examples:
- "What are my biggest strengths?"
- "How do my activities connect to courses?"
- "What unique perspectives do I bring?"
- "Where have I shown the most growth?"

BAD examples (too long):
- "How do you think your performance in community college courses has prepared you for studying business in college?"
- "Are there any academic areas you feel you need to improve in before starting college?"
"""
        
        # Build conversation content
        contents = []
        
        # Add system prompt
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "I understand. I'll answer questions about your profile only, and provide insightful follow-up questions."}]})
        
        # Add conversation history
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        # Add current question
        contents.append({"role": "user", "parts": [{"text": question}]})
        
        # Call Gemini
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=contents
        )
        
        response_text = response.text.strip()
        
        # Parse JSON response
        try:
            # Clean markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                start_idx = 1 if lines[0].startswith('```') else 0
                end_idx = len(lines) - 1 if lines[-1] == '```' else len(lines)
                response_text = '\n'.join(lines[start_idx:end_idx])
                if response_text.startswith('json'):
                    response_text = response_text[4:].strip()
            
            parsed_response = json.loads(response_text)
            answer = parsed_response.get('answer', response_text)
            suggested_questions = parsed_response.get('suggested_questions', [])
        except json.JSONDecodeError:
            # If JSON parsing fails, use the whole response as answer
            answer = response_text
            suggested_questions = []
        
        # Update conversation history
        updated_history = conversation_history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        logger.info(f"[PROFILE_CHAT] Answered question for {user_id}, generated {len(suggested_questions)} follow-ups")
        
        return {
            "success": True,
            "answer": answer,
            "suggested_questions": suggested_questions,
            "conversation_history": updated_history
        }
        
    except Exception as e:
        logger.error(f"Profile chat failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
