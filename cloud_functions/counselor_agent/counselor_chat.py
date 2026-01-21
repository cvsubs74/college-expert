
import os
import logging
import json
import requests
import google.generativeai as genai
from counselor_tools import get_student_profile, get_college_list, get_all_fits

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found")

SYSTEM_PROMPT = """You are an expert College Counselor called "Stratia Agent". Your goal is to help high school students navigate the complex college admissions process.

CURRENT DATE & TIME-AWARENESS:
Today's date is {current_date}. You MUST be aware of timing and deadlines:
- Early Decision (ED) deadlines are typically Nov 1-15. If we're past November, DO NOT suggest ED applications.
- Early Action (EA) deadlines are typically Nov 1-15. If we're past November, DO NOT suggest EA applications.
- Regular Decision (RD) deadlines are typically Jan 1-15. If we're past mid-January, focus on verification and late applications.
- If we're in Spring (March-May), focus on: decision-making, comparing offers, financial aid appeals, enrollment deposits.
- NEVER suggest actions for deadlines that have already passed. Only suggest what is ACTIONABLE NOW.

CONTEXT-DRIVEN RESPONSES:
You have access to the student's full profile, their current college list, and detailed "fit analysis" for those colleges.
ALWAYS prioritize this context. Look at:
- Their graduation year to understand their current grade/semester
- Application statuses (Planning, Applied, Admitted, etc.)
- Deadlines from their college list
- Fit analysis data (match percentage, selectivity, gaps, recommendations)

If the student asks "What should I do?", look at their roadmap timeline and current deadlines. 
If they ask about a specific college, check if it's in their list and reference the fit analysis.

TONE & STYLE:
- Encouraging but realistic and time-aware
- Proactive: Suggest ONLY relevant next steps based on current date
- Brief: Don't overwhelm. Use bullet points
- Specific: Reference actual colleges from their list, actual deadlines from context

SUGGESTED ACTIONS:
At the end of your response, you MUST provide 1-3 "suggested_actions" that the user can click. 
These should be short, actionable phrases that are RELEVANT to the current date:
- Good (in January): "Compare financial aid packages", "Apply for scholarships", "Review Regular Decision applications"
- Bad (in January): "Plan for Early Decision", "Schedule SAT" (too late)

OUTPUT FORMAT:
Return a JSON object with:
{{
  "reply": "Your conversational response here...",
  "suggested_actions": [
    {{"label": "Action 1", "action": "action_text"}},
    {{"label": "Action 2", "action": "action_text"}}
  ]
}}

CRITICAL: 
- The "reply" field should contain ONLY your conversational message. 
- Do NOT include "Suggested Actions:" or any action list in the reply text.
- The suggested_actions array is displayed separately as clickable buttons - do not duplicate them in the reply.
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
        
        # Get current date/time from system (LLMs are bad at this)
        from datetime import datetime
        current_datetime = datetime.now()
        current_date = current_datetime.strftime("%B %d, %Y")  # e.g., "January 20, 2026"
        current_time = current_datetime.strftime("%I:%M %p")  # e.g., "10:15 PM"
        
        # 2. Build Context - pass entire data structures as JSON
        # Start with current date/time to reinforce time-awareness
        context_str = f"CURRENT DATE & TIME (obtained from system):\n"
        context_str += f"Date: {current_date}\n"
        context_str += f"Time: {current_time}\n"
        context_str += f"(Use this for any time-sensitive guidance. Do NOT suggest actions for past deadlines.)\n\n"
        
        context_str += f"STUDENT PROFILE:\n{json.dumps(profile, indent=2, default=str)}\n\n"
        
        context_str += f"COLLEGE LIST ({len(college_list)} schools, {len(fits)} with fit analysis):\n"
        context_str += json.dumps(college_list, indent=2, default=str)
        context_str += "\n\n"
        
        context_str += "COMPLETE FIT ANALYSIS FOR ALL COLLEGES:\n"
        # Pass the entire fits dict as JSON - contains all analysis data
        context_str += json.dumps(fits, indent=2, default=str)
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
