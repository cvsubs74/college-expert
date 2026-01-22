"""
Counselor Chat History - Firestore persistence for counselor conversations.
Mirrors fit_chat_firestore.py patterns.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import requests

logger = logging.getLogger(__name__)

# Profile Manager URL for Firestore operations
PROFILE_MANAGER_URL = os.getenv('PROFILE_MANAGER_URL', 'http://localhost:8080')


def save_counselor_conversation(
    user_id: str,
    conversation_id: str = None,
    messages: List[Dict] = None,
    title: str = None
) -> dict:
    """
    Save or update a counselor conversation to Firestore.
    
    Args:
        user_id: User's email
        conversation_id: Unique conversation ID (auto-generated if not provided)
        messages: List of {role, content} message dicts
        title: Conversation title (auto-generated from first message if not provided)
    
    Returns:
        dict with success status and conversation_id
    """
    try:
        if messages is None:
            messages = []
            
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"counselor_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Auto-generate title from first user message if not provided
        if not title and messages:
            for msg in messages:
                if msg.get('role') == 'user':
                    first_question = msg.get('content', '')[:50]
                    title = first_question + ('...' if len(msg.get('content', '')) > 50 else '')
                    break
        
        if not title:
            title = f"Counselor Chat - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        # Build conversation document
        conversation_data = {
            "conversation_id": conversation_id,
            "title": title,
            "messages": messages,  # Store as array directly
            "message_count": len(messages),
            "conversation_type": "counselor",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Call Profile Manager to save
        url = f"{PROFILE_MANAGER_URL}/save-counselor-chat"
        response = requests.post(url, json={
            "user_email": user_id,
            "conversation_id": conversation_id,
            "conversation_data": conversation_data
        }, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"[COUNSELOR_CHAT] Saved conversation {conversation_id} for {user_id}")
            return {
                "success": True,
                "conversation_id": conversation_id,
                "title": title
            }
        else:
            logger.error(f"[COUNSELOR_CHAT] Save failed: {response.status_code} {response.text}")
            return {
                "success": False,
                "error": f"Save failed: {response.text}"
            }
            
    except Exception as e:
        logger.error(f"[COUNSELOR_CHAT] Save failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def load_counselor_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Load a specific counselor conversation from Firestore.
    
    Args:
        user_id: User's email
        conversation_id: The conversation ID to load
    
    Returns:
        dict with conversation data or error
    """
    try:
        url = f"{PROFILE_MANAGER_URL}/get-counselor-chat"
        response = requests.get(url, params={
            "user_email": user_id,
            "conversation_id": conversation_id
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            conversation = data.get('conversation', {})
            
            if conversation:
                logger.info(f"[COUNSELOR_CHAT] Loaded conversation {conversation_id} for {user_id}")
                return {
                    "success": True,
                    "conversation": conversation,
                    "messages": conversation.get('messages', []),
                    "title": conversation.get('title', ''),
                    "conversation_id": conversation_id
                }
            else:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
        else:
            logger.warning(f"[COUNSELOR_CHAT] Load failed: {response.status_code}")
            return {
                "success": False,
                "error": f"Load failed: {response.status_code}"
            }
            
    except Exception as e:
        logger.error(f"[COUNSELOR_CHAT] Load failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def list_counselor_conversations(user_id: str, limit: int = 20) -> dict:
    """
    List all counselor conversations for a user.
    
    Args:
        user_id: User's email
        limit: Maximum number of conversations to return
    
    Returns:
        dict with list of conversations
    """
    try:
        url = f"{PROFILE_MANAGER_URL}/list-counselor-chats"
        response = requests.get(url, params={
            "user_email": user_id,
            "limit": limit
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            conversations = data.get('conversations', [])
            
            logger.info(f"[COUNSELOR_CHAT] Listed {len(conversations)} conversations for {user_id}")
            return {
                "success": True,
                "conversations": conversations,
                "count": len(conversations)
            }
        else:
            logger.warning(f"[COUNSELOR_CHAT] List failed: {response.status_code}")
            return {
                "success": True,
                "conversations": [],
                "count": 0
            }
            
    except Exception as e:
        logger.error(f"[COUNSELOR_CHAT] List failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_active_conversation(user_id: str) -> dict:
    """
    Get the most recent active counselor conversation for a user.
    If no recent conversation exists, returns empty.
    
    Args:
        user_id: User's email
    
    Returns:
        dict with active conversation or empty
    """
    try:
        result = list_counselor_conversations(user_id, limit=1)
        
        if result.get('success') and result.get('conversations'):
            latest = result['conversations'][0]
            conversation_id = latest.get('conversation_id')
            
            # Load full conversation
            return load_counselor_conversation(user_id, conversation_id)
        
        return {
            "success": True,
            "conversation": None,
            "messages": [],
            "conversation_id": None
        }
        
    except Exception as e:
        logger.error(f"[COUNSELOR_CHAT] Get active failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def delete_counselor_conversation(user_id: str, conversation_id: str) -> dict:
    """
    Delete a counselor conversation.
    
    Args:
        user_id: User's email
        conversation_id: The conversation ID to delete
    
    Returns:
        dict with success status
    """
    try:
        url = f"{PROFILE_MANAGER_URL}/delete-counselor-chat"
        response = requests.delete(url, params={
            "user_email": user_id,
            "conversation_id": conversation_id
        }, timeout=10)
        
        if response.status_code == 200:
            logger.info(f"[COUNSELOR_CHAT] Deleted conversation {conversation_id} for {user_id}")
            return {"success": True}
        else:
            return {
                "success": False,
                "error": f"Delete failed: {response.status_code}"
            }
            
    except Exception as e:
        logger.error(f"[COUNSELOR_CHAT] Delete failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
