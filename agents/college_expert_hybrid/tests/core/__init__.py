"""
Core infrastructure for LLM-as-Judge evaluation suite.

This module provides shared utilities, data structures, and the LLM judge
functionality used by all test categories.
"""
import os
import json
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from google import genai
from google.genai import types

# Configure Gemini Client
# We use the new SDK pattern: client = genai.Client(api_key=...)
try:
    _eval_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    print(f"Warning: Failed to initialize GenAI client: {e}")
    _eval_client = None

JUDGE_MODEL_ID = "gemini-2.0-flash"

# Agent configuration
CLOUD_URL = "https://college-expert-hybrid-agent-808989169388.us-east1.run.app"
LOCAL_URL = "http://localhost:8000"
BASE_URL = CLOUD_URL  # Default to cloud
APP_NAME = "college_expert_hybrid"
DEFAULT_USER_EMAIL = "cvsubs@gmail.com"

def set_local_mode(local: bool = True):
    """Switch between local and cloud testing."""
    global BASE_URL
    BASE_URL = LOCAL_URL if local else CLOUD_URL
    return BASE_URL



@dataclass
class EvalCase:
    """A single evaluation case."""
    eval_id: str
    category: str
    user_query: str
    expected_intent: str
    criteria: list[str]
    requires_profile: bool = False


@dataclass
class EvalResult:
    """Result of an LLM-as-judge evaluation."""
    eval_id: str
    category: str
    passed: bool
    score: float
    reasoning: str
    criteria_met: dict[str, bool] = field(default_factory=dict)
    response_snippet: str = ""
    full_response: str = ""  # Complete agent response
    query: str = ""  # Original user query
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())



@dataclass
class ConversationTurn:
    """A single turn in a multi-turn conversation."""
    user_message: str
    criteria: list[str]
    description: str


@dataclass
class MultiTurnConversation:
    """A multi-turn conversation test case."""
    conv_id: str
    description: str
    turns: list[ConversationTurn]
    requires_profile: bool = False


def create_judge_prompt(case: EvalCase, actual_response: str) -> str:
    """Create a prompt for the LLM judge."""
    criteria_list = "\n".join([f"  {i+1}. {c}" for i, c in enumerate(case.criteria)])
    num_criteria = len(case.criteria)
    
    return f"""You are an expert evaluator assessing an AI college counseling agent's response quality.

## Evaluation Context
- **Category**: {case.category}
- **Requires Profile**: {case.requires_profile}
- **Number of Criteria**: {num_criteria}

## User Query
"{case.user_query}"

## Expected Intent
{case.expected_intent}

## Criteria to Evaluate
{criteria_list}

## Agent's Actual Response
{actual_response}

## Scoring Instructions
1. Evaluate each criterion independently - mark as "met": true or "met": false
2. Calculate overall_score as: (number of criteria met) / {num_criteria}
   - If {num_criteria} criteria and all met: score = 1.0
   - If {num_criteria} criteria and {num_criteria - 1} met: score = {(num_criteria - 1) / num_criteria:.2f}
   - If none met: score = 0.0
3. Set overall_pass = true if score >= 0.6, otherwise false
4. Be precise with scoring - do NOT default to 0.85

## Required Output Format
Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "overall_pass": <true or false based on score >= 0.6>,
    "overall_score": <calculated as criteria_met_count / {num_criteria}>,
    "reasoning": "<one sentence explanation>",
    "criteria_results": {{
        "1": {{"met": <true/false>, "note": "<brief note>"}},
        "2": {{"met": <true/false>, "note": "<brief note>"}}
    }}
}}
"""



async def run_agent(user_query: str, user_email: str = DEFAULT_USER_EMAIL, session_id: str = None) -> str:
    """Run the agent via HTTP API and get its response."""
    import aiohttp
    
    user_id = "eval_user"
    if session_id is None:
        session_id = f"eval_{uuid.uuid4().hex[:8]}"
    
    # Prepend email to query so agent can see it (per agent instructions)
    message_with_email = f"[USER_EMAIL: {user_email}] {user_query}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Create session
            create_url = f"{BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}"
            async with session.post(
                create_url,
                json={"state": {"user_email": user_email}},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                pass  # Session created
            
            # Run agent with email prepended to message
            return await send_message(session, user_id, session_id, message_with_email)
    except Exception as e:
        return f"Request failed: {str(e)}"



async def send_message(http_session, user_id: str, session_id: str, message: str) -> str:
    """Send a message to an existing session."""
    run_url = f"{BASE_URL}/run"
    run_payload = {
        "app_name": APP_NAME,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False
    }
    
    async with http_session.post(
        run_url,
        json=run_payload,
        headers={"Content-Type": "application/json"},
        timeout=aiohttp.ClientTimeout(total=120)
    ) as response:
        if response.status == 200:
            result = await response.json()
            return extract_response_text(result)
        else:
            return f"Error: {response.status} - {await response.text()}"


def extract_response_text(result) -> str:
    """Extract text from agent response."""
    # Extract from list of events
    if isinstance(result, list):
        for event in reversed(result):
            if isinstance(event, dict) and event.get("content"):
                content = event["content"]
                if content.get("role") == "model" and content.get("parts"):
                    for part in content["parts"]:
                        if "text" in part and part["text"]:
                            return part["text"]
    
    # Extract from dict
    if isinstance(result, dict):
        if "result" in result:
            return result["result"]
        if "content" in result and result["content"]:
            parts = result["content"].get("parts", [])
            if parts:
                return parts[0].get("text", str(result))
    
    return str(result)[:500]


def judge_response(case: EvalCase, actual_response: str) -> EvalResult:
    """Use LLM to judge the response."""
    prompt = create_judge_prompt(case, actual_response)
    
    try:
        if _eval_client is None:
            return EvalResult(
                eval_id=case.eval_id,
                category=case.category,
                passed=False,
                score=0.0,
                reasoning="Judge error: GenAI client not initialized (missing API key?)",
                criteria_met={},
                response_snippet=actual_response[:200]
            )
            
        response = _eval_client.models.generate_content(
            model=JUDGE_MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        result_text = response.text.strip()
        
        # Extract JSON (SDK might return it directly if mime_type is json, but safety check)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        result_json = json.loads(result_text.strip())
        
        criteria_met = {}
        for i, criterion in enumerate(case.criteria):
            key = str(i + 1)
            if key in result_json.get("criteria_results", {}):
                criteria_met[criterion] = result_json["criteria_results"][key].get("met", False)
        
        return EvalResult(
            eval_id=case.eval_id,
            category=case.category,
            passed=result_json.get("overall_pass", False),
            score=result_json.get("overall_score", 0.0),
            reasoning=result_json.get("reasoning", "No reasoning"),
            criteria_met=criteria_met,
            response_snippet=actual_response[:200]
        )
    except Exception as e:
        return EvalResult(
            eval_id=case.eval_id,
            category=case.category,
            passed=False,
            score=0.0,
            reasoning=f"Judge error: {e}",
            criteria_met={},
            response_snippet=actual_response[:200]
        )


def judge_conversation_turn(turn: ConversationTurn, actual_response: str, turn_num: int) -> dict:
    """Judge a single conversation turn."""
    criteria_list = "\n".join([f"  {i+1}. {c}" for i, c in enumerate(turn.criteria)])
    num_criteria = len(turn.criteria)
    
    prompt = f"""You are evaluating turn {turn_num} of a multi-turn conversation with a college counseling AI.

## Turn Context
This is turn {turn_num}. The user message may reference previous context from the conversation.

## User Message
"{turn.user_message}"

## Turn Description
{turn.description}

## Criteria to Evaluate ({num_criteria} total)
{criteria_list}

## Agent Response
{actual_response}

## Scoring Instructions
1. Evaluate each criterion - mark as met (true) or not met (false)
2. Calculate score = (criteria met count) / {num_criteria}
   - All {num_criteria} met: score = 1.0
   - {num_criteria - 1} of {num_criteria} met: score = {(num_criteria - 1) / num_criteria:.2f}
3. Check if context is maintained from previous turns
4. passed = true if score >= 0.5 AND context is maintained

Respond ONLY with JSON:
{{
    "passed": <true/false>,
    "score": <calculated 0.0-1.0>,
    "reasoning": "<brief explanation>",
    "context_maintained": <true/false>
}}
"""
    
    try:
        if _eval_client is None:
             return {
                "passed": False,
                "score": 0.0,
                "reasoning": "Judge error: GenAI client not initialized",
                "context_maintained": False
            }

        response = _eval_client.models.generate_content(
            model=JUDGE_MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        result_text = response.text.strip()
        
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0]
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
        
        return json.loads(result_text.strip())
    except Exception as e:
        return {
            "passed": False,
            "score": 0.0,
            "reasoning": f"Judge error: {e}",
            "context_maintained": False
        }


# Need to import aiohttp at module level for type hints
import aiohttp
