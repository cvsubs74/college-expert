"""
Fit chat functionality for V2 using Firestore.
Ported from profile_manager_es with Firestore adaptations.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

from google import genai
from google.genai import types
from firestore_db import get_db
from profile_operations import get_student_profile
from fit_analysis import get_fit_analysis
from essay_copilot import fetch_university_profile

logger = logging.getLogger(__name__)


def fit_chat(user_id: str, university_id: str, question: str, conversation_history: list = None) -> dict:
    """
    Chat about a specific fit analysis using profile + fit data as context.
    Uses gemini-2.5-flash-lite with context injection.
    
    Args:
        user_id: The user's email
        university_id: The university ID to chat about
        question: User's question
        conversation_history: List of {role, content} dicts for context
    
    Returns:
        dict with answer and updated conversation history
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        # Load user profile from Firestore
        user_profile = get_student_profile(user_id)
        
        if not user_profile:
            return {
                "success": False,
                "error": "User profile not found"
            }
        
        # Load fit analysis for this university from Firestore
        fit_data = get_fit_analysis(user_id, university_id)
        
        if not fit_data:
            logger.warning(f"[FIT_CHAT] No fit found for user={user_id}, uni_id={university_id}")
            return {
                "success": False,
                "error": f"No fit analysis found for {university_id}. Please run a fit analysis first."
            }
        
        university_name = fit_data.get('university_name', university_id)
        
        # Build context with profile and fit data
        # Remove internal/metadata fields that aren't useful for the LLM
        fields_to_exclude = ['indexed_at', 'updated_at', 'created_at', '_id', 'embedding', 'chunk_id']
        profile_summary = {k: v for k, v in user_profile.items() if k not in fields_to_exclude and v}
        
        # Extract key fit fields
        fit_summary = {
            "university_name": university_name,
            "fit_category": fit_data.get("fit_category"),
            "match_score": fit_data.get("match_score") or fit_data.get("match_percentage"),
            "acceptance_rate": fit_data.get("acceptance_rate"),
            "us_news_rank": fit_data.get("us_news_rank"),
            "gap_analysis": fit_data.get("gap_analysis"),
            "recommendations": fit_data.get("recommendations"),
            "detailed_analysis": fit_data.get("detailed_analysis"),
        }
        
        # Fetch university profile from knowledge base for additional context
        university_profile = fetch_university_profile(university_id)
        university_summary = {}
        if university_profile:
            profile_data = university_profile.get('profile', university_profile)
            # Pass ENTIRE university profile as context
            university_summary = profile_data
            logger.info(f"[FIT_CHAT] Loaded FULL university profile")
        else:
            logger.warning(f"[FIT_CHAT] Could not fetch university profile for {university_id}")
        
        profile_json = json.dumps(profile_summary, indent=2, default=str)
        fit_json = json.dumps(fit_summary, indent=2, default=str)
        university_json = json.dumps(university_summary, indent=2, default=str) if university_summary else "Not available"
        
        system_prompt = f"""You are a college admissions advisor helping a student understand their fit with {university_name}. Answer questions using ONLY the data provided below.

STUDENT PROFILE:
{profile_json}

FIT ANALYSIS FOR {university_name}:
{fit_json}

UNIVERSITY INFORMATION (Colleges, Majors, Programs):
{university_json}

RULES:
- Base answers on the data provided above
- When asked about majors/programs, use the UNIVERSITY INFORMATION section
- Explain factors affecting the fit score
- Give actionable advice when asked
- Be encouraging but realistic
- Format responses in markdown when helpful
- If information is not in the data, say so honestly

SUGGESTED QUESTIONS:
Also provide 3 suggested follow-up questions that would be most useful for this student to ask next.
"Useful" means:
1. Helps the student understand their admission chances specifically
2. Explores academic fit (majors, classes) or social fit
3. Finds actionable steps to improve their application
IMPORTANT: Keep questions short and concise (max 15 words).

RESPONSE FORMAT:
Return a JSON object with this structure:
{{
  "answer": "your markdown answer here...",
  "suggested_questions": ["question 1", "question 2", "question 3"]
}}
"""
        
        # Build conversation for Gemini
        contents = []
        
        # Add system context
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=system_prompt)]
        ))
        
        # Add conversation history
        for msg in conversation_history:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            # Skip empty messages
            if not content:
                continue
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=content)]
            ))
        
        # Add current question
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=question)]
        ))
        
        # Call Gemini with JSON mode
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        
        # Parse JSON response
        try:
            response_data = json.loads(response.text)
            answer = response_data.get("answer", response.text)
            suggested_questions = response_data.get("suggested_questions", [])
        except json.JSONDecodeError:
            # Fallback if model fails to return JSON
            logger.warning("[FIT_CHAT] Model failed to return valid JSON, using raw text")
            answer = response.text
            suggested_questions = []

        # Update history - keep only text content for history
        updated_history = conversation_history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
        
        logger.info(f"[FIT_CHAT] Q: '{question[:30]}...' -> A: {len(answer)} chars, Suggestions: {len(suggested_questions)}")
        
        return {
            "success": True,
            "answer": answer,
            "suggested_questions": suggested_questions,
            "conversation_history": updated_history,
            "university_name": university_name,
            "university_id": university_id
        }
        
    except Exception as e:
        logger.error(f"Fit chat failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def save_fit_chat_conversation(user_id: str, university_id: str, university_name: str, 
                                messages: list, conversation_id: str = None, title: str = None) -> dict:
    """
    Save or update a fit chat conversation.
    
    Args:
        user_id: The user's email
        university_id: The university ID
        university_name: The university display name
        messages: List of {role, content} message dicts
        conversation_id: Optional existing ID to update (None creates new)
        title: Optional conversation title (auto-generated if not provided)
    
    Returns:
        dict with success status and conversation_id
    """
    try:
        db = get_db()
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"{user_id}_{university_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Auto-generate title from first user message if not provided
        if not title and messages:
            for msg in messages:
                if msg.get('role') == 'user':
                    first_question = msg.get('content', '')[:50]
                    title = first_question + ('...' if len(msg.get('content', '')) > 50 else '')
                    break
        
        if not title:
            title = f"Chat with {university_name}"
        
        # Build document
        conversation_data = {
            "university_id": university_id,
            "university_name": university_name,
            "conversation_id": conversation_id,
            "title": title,
            "messages": json.dumps(messages),
            "message_count": len(messages),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Check if updating existing - preserve created_at
        existing = db.get_fit_conversation(user_id, conversation_id)
        if existing:
            conversation_data["created_at"] = existing.get('created_at', conversation_data["created_at"])
        
        # Save to Firestore
        success = db.save_fit_conversation(user_id, conversation_id, conversation_data)
        
        if success:
            logger.info(f"[CHAT_HISTORY] Saved conversation {conversation_id} for {user_id}/{university_id}")
            return {
                "success": True,
                "conversation_id": conversation_id,
                "title": title
            }
        else:
            return {
                "success": False,
                "error": "Failed to save conversation"
            }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] Save failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def list_fit_chat_conversations(user_id: str, university_id: str = None, limit: int = 20) -> dict:
    """
    List saved conversations for a user, optionally filtered by university.
    
    Args:
        user_id: The user's email
        university_id: Optional filter by university
        limit: Max conversations to return
    
    Returns:
        dict with success status and conversations list
    """
    try:
        db = get_db()
        
        # Get conversations from Firestore
        conversations_data = db.list_fit_conversations(user_id, university_id, limit)
        
        conversations = []
        for conv in conversations_data:
            conversations.append({
                "conversation_id": conv.get("conversation_id"),
                "university_id": conv.get("university_id"),
                "university_name": conv.get("university_name"),
                "title": conv.get("title"),
                "message_count": conv.get("message_count", 0),
                "created_at": conv.get("created_at"),
                "updated_at": conv.get("updated_at")
            })
        
        logger.info(f"[CHAT_HISTORY] Listed {len(conversations)} conversations for {user_id}")
        
        return {
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] List failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "conversations": []
        }


def load_fit_chat_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Load a specific conversation by ID.
    
    Args:
        user_id: The user's email (for ownership verification)
        conversation_id: The conversation ID to load
    
    Returns:
        dict with success status and full conversation data
    """
    try:
        db = get_db()
        
        # Get conversation from Firestore
        conversation = db.get_fit_conversation(user_id, conversation_id)
        
        if not conversation:
            return {
                "success": False,
                "error": "Conversation not found"
            }
        
        # Parse messages
        messages = []
        try:
            messages = json.loads(conversation.get("messages", "[]"))
        except:
            pass
        
        logger.info(f"[CHAT_HISTORY] Loaded conversation {conversation_id} for {user_id}")
        
        return {
            "success": True,
            "conversation": {
                "conversation_id": conversation.get("conversation_id"),
                "university_id": conversation.get("university_id"),
                "university_name": conversation.get("university_name"),
                "title": conversation.get("title"),
                "messages": messages,
                "message_count": conversation.get("message_count", 0),
                "created_at": conversation.get("created_at"),
                "updated_at": conversation.get("updated_at")
            }
        }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] Load failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def delete_fit_chat_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Delete a conversation.
    
    Args:
        user_id: The user's email (for ownership verification)
        conversation_id: The conversation ID to delete
    
    Returns:
        dict with success status
    """
    try:
        db = get_db()
        
        # Delete from Firestore
        success = db.delete_fit_conversation(user_id, conversation_id)
        
        if success:
            logger.info(f"[CHAT_HISTORY] Deleted conversation {conversation_id} for {user_id}")
            return {
                "success": True,
                "message": "Conversation deleted"
            }
        else:
            return {
                "success": False,
                "error": "Failed to delete conversation"
            }
        
    except Exception as e:
        logger.error(f"[CHAT_HISTORY] Delete failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
