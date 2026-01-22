
import os
import logging
import json
import requests
import google.generativeai as genai
from counselor_tools import get_student_profile, get_college_list, get_all_fits, get_targeted_university_context

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found")

SYSTEM_PROMPT = """You are "Stratia Agent" - a world-class College Counselor helping high school students with college admissions. You have deep expertise and access to real student data.

CURRENT DATE: {current_date}

=== CONVERSATION RULES ===
1. NEVER REPEAT yourself. If you already mentioned deadlines passed, don't say it again.
2. Read the conversation history carefully - don't re-introduce yourself or repeat previous points.
3. Be SPECIFIC. Use actual college names, scholarship names, and dollar amounts from the context.
4. Keep responses focused and actionable. Don't give generic advice when you have specific data.

=== TIME-AWARENESS ===
- If we're past November: ED/EA deadlines are over - don't mention them
- If we're past mid-January: Most RD deadlines passed - focus on what's NEXT (decisions, aid, scholarships)
- Spring focus: Comparing admission offers, financial aid packages, enrollment deposits, housing
- Only suggest actions that are CURRENTLY POSSIBLE

=== USING CONTEXT DATA ===
You have access to:
- Student profile (GPA, test scores, graduation year)
- College list with application statuses
- Fit analysis for each college (match %, gaps, recommendations)
- University data: SPECIFIC scholarships, deadlines, financial aid info

WHEN ASKED ABOUT SCHOLARSHIPS: Reference the ACTUAL scholarships from UNIVERSITY_CONTEXT. Include:
- Scholarship names (e.g., "Hodson Trust Scholarship")
- Award amounts (e.g., "Full tuition", "$25,000/year")
- Application methods (e.g., "Automatic Consideration", "Separate application")
- Deadlines if applicable

WHEN ASKED ABOUT DEADLINES: Use ACTUAL dates from UNIVERSITY_CONTEXT, not generic estimates.

=== COUNSELOR PERSONA ===
- Warm, supportive, but honest
- Proactive: Anticipate what the student needs next
- Expert: You know the admissions landscape deeply
- Concise: Use bullet points, don't write essays

=== OUTPUT FORMAT ===
Return valid JSON:
{{
  "reply": "Your conversational response. NO action lists here. NO 'Suggested Actions:' header.",
  "suggested_actions": [
    {{"label": "Button text", "action": "action_text"}},
    {{"label": "Another button", "action": "action_text"}}
  ]
}}

CRITICAL RULES:
- Put NOTHING about suggested actions in the reply field - they appear as separate buttons
- Provide 1-3 relevant suggested_actions
- NEVER include "Suggested Actions:" or numbered action lists in the reply
"""

def chat_with_counselor(request):
    """
    Handle chat interaction with context.
    Payload: { "user_email": "...", "message": "...", "history": [...] }
    Returns: dict
    """
    try:
        data = request.get_json()
        user_email = data.get('user_email')
        message = data.get('message')
        history = data.get('history', [])
        
        if not user_email or not message:
            return {'success': False, 'error': 'Missing user_email or message'}

        # 1. Fetch Context
        profile = get_student_profile(user_email)
        college_list = get_college_list(user_email)
        fits = get_all_fits(user_email)
        
        # Fetch targeted university data (scholarships, deadlines, aid info)
        university_context = get_targeted_university_context(user_email)
        
        # Get current date/time from system (LLMs are bad at this)
        from datetime import datetime
        current_datetime = datetime.now()
        current_date = current_datetime.strftime("%B %d, %Y")  # e.g., "January 21, 2026"
        current_time = current_datetime.strftime("%I:%M %p")  # e.g., "10:15 PM"
        
        # 2. Build Context - pass data structures as JSON
        context_str = f"=== CURRENT DATE: {current_date} ({current_time}) ===\n"
        context_str += "(All deadline/scholarship guidance must be based on this date.)\n\n"
        
        context_str += f"STUDENT PROFILE:\n{json.dumps(profile, indent=2, default=str)}\n\n"
        
        context_str += f"COLLEGE LIST ({len(college_list)} schools):\n"
        context_str += json.dumps(college_list, indent=2, default=str)
        context_str += "\n\n"
        
        context_str += "FIT ANALYSIS (match %, gaps, recommendations):\n"
        context_str += json.dumps(fits, indent=2, default=str)
        context_str += "\n\n"
        
        # Add targeted university data (scholarships, deadlines, aid)
        context_str += "UNIVERSITY_CONTEXT (scholarships, deadlines, financial aid - USE THIS DATA!):\n"
        context_str += json.dumps(university_context, indent=2, default=str)
        context_str += "\n"
            
        # 3. Build Prompt with History
        # Inject current date into system prompt as well
        system_prompt_with_date = SYSTEM_PROMPT.format(current_date=current_date)
        
        model = genai.GenerativeModel('gemini-2.5-flash-lite', 
                                      system_instruction=system_prompt_with_date)
        
        chat = model.start_chat(history=history)
        
        # Inject context in the final message if it's the start or just append to user message
        # For simplicity/statelessness, we append context to the current message
        full_message = f"CONTEXT:\n{context_str}\n\nUSER MESSAGE:\n{message}"
        
        # 4. Generate Response
        response = chat.send_message(full_message)
        
        # 5. Parse JSON output
        try:
            # Clean generic markdown if present
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:-3]
            
            output = json.loads(text)
            return {
                'success': True,
                'reply': output.get('reply'),
                'suggested_actions': output.get('suggested_actions', [])
            }
        except json.JSONDecodeError:
            # Fallback if model didn't output JSON
            return {
                'success': True,
                'reply': response.text,
                'suggested_actions': []
            }
            
    except Exception as e:
        logger.error(f"Error in chat_with_counselor: {e}")
        return {'success': False, 'error': str(e)}
