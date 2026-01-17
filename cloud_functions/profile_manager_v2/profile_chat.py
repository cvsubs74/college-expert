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
        
        system_prompt = f"""You are Stratia, a warm and insightful college counseling advisor helping a student understand their unique story and strengths.

STUDENT PROFILE DATA:
{profile_json}

YOUR ROLE:
You are the student's personal guide for self-discovery and college preparation. You help them:
- Understand their unique strengths, passions, and defining experiences
- Discover meaningful themes and narratives in their activities and achievements
- Brainstorm compelling essay topics and angles based on their authentic story
- Reflect deeply on what makes them unique as an applicant
- Connect their experiences to potential college fit and major interests

RESPONSE GUIDELINES:
1. **Be Insightful & Specific**: Analyze their profile deeply. Don't just list facts—interpret what they mean. Find patterns, connections, and unique angles others might miss.

2. **Provide Detailed Reasoning**: Explain your thinking. If you identify a strength or theme, explain WHY you see it and HOW it manifests in their profile.

3. **Use Markdown Formatting**: Structure your responses with:
   - **Bold** for key insights and themes
   - Bullet points for lists of ideas
   - Clear paragraphs for explanation
   - > Blockquotes for particularly important points

4. **Be Personal & Warm**: Use "you" and "your." Reference specific activities, courses, and achievements by name. Make them feel seen.

5. **Essay Brainstorming is WELCOME**: When asked about essays, provide 3-5 specific, unique angles based on their profile. For each angle:
   - Name the theme/angle
   - Explain why it's compelling for THIS student
   - Suggest a potential hook or approach

6. **Encourage Deeper Reflection**: After answering, prompt them to think more deeply with a thoughtful follow-up question.

WHAT TO AVOID:
- Generic, surface-level responses ("You have good activities!")
- Refusing to help with essay brainstorming or college-related self-reflection
- Listing profile data without interpretation
- Short, one-sentence answers

IMPORTANT: The student may ask about essays, their story, what makes them unique, or how to present themselves to colleges. These are ALL profile-related questions you SHOULD answer thoughtfully by analyzing their profile data.

Only redirect to University Explorer if they ask for specific data about a university (acceptance rates, programs, etc.).

Your response should be in JSON format:
{{
  "answer": "your detailed, well-formatted response here (use markdown)",
  "suggested_questions": ["question 1", "question 2", "question 3"]
}}

IMPORTANT: The "answer" field should ONLY contain your response to the student's question. Do NOT include the suggested_questions in the answer text - they will be displayed as clickable buttons separately in the UI.

The suggested_questions MUST:
- Be 8 words or less (STRICT LIMIT)
- Be personal and reflective (use "my", "I")
- Help the student gain deeper self-awareness
- Build on what was just discussed
- ONLY appear in the suggested_questions array, NOT in the answer text

GOOD examples:
- "What are my biggest strengths?"
- "How do my activities show growth?"
- "What unique perspectives do I bring?"
- "Which experience changed me most?"
- "What essay theme fits me best?"
"""
        
        # Build conversation content
        contents = []
        
        # Add system prompt
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=system_prompt)]
        ))
        
        # Add conversation history
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))
        
        # Add current question
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=question)]
        ))
        
        # Call Gemini with JSON response format
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type='application/json'
            )
        )
        
        response_text = response.text.strip()
        logger.info(f"[PROFILE_CHAT] Raw response length: {len(response_text)}, starts with: {response_text[:100]}...")
        
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
                logger.info(f"[PROFILE_CHAT] After cleaning markdown: {response_text[:100]}...")
            
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end + 1]
                logger.info(f"[PROFILE_CHAT] Attempting to parse JSON of length {len(json_str)}")
                parsed_response = json.loads(json_str)
                answer = parsed_response.get('answer', response_text)
                suggested_questions = parsed_response.get('suggested_questions', [])
                logger.info(f"[PROFILE_CHAT] JSON parsed successfully. suggested_questions: {suggested_questions}")
            else:
                # No JSON structure found, use raw text
                logger.warning(f"[PROFILE_CHAT] No JSON structure found in response")
                answer = response_text
                suggested_questions = []
        except json.JSONDecodeError:
            # If JSON parsing fails, use the whole response as answer
            # But first try to extract the "answer" field if it looks like JSON
            import re
            match = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', response_text, re.DOTALL)
            if match:
                answer = match.group(1).replace('\\n', '\n').replace('\\"', '"')
            else:
                answer = response_text
            
            # Also try to extract suggested_questions from the JSON
            sq_match = re.search(r'"suggested_questions"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
            if sq_match:
                # Extract question strings from the matched array
                questions_str = sq_match.group(1)
                question_matches = re.findall(r'"([^"]+)"', questions_str)
                suggested_questions = question_matches[:5]  # Limit to 5
            else:
                suggested_questions = []
        
        # Fallback: if no suggested questions were parsed, provide defaults
        if not suggested_questions:
            suggested_questions = [
                "What are my biggest strengths?",
                "What unique story can I tell?",
                "How do my experiences connect?"
            ]
        
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
