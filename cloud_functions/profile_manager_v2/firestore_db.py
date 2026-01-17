"""
Database abstraction layer for Firestore operations.
Provides clean interface for all profile manager database operations.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)

class FirestoreDB:
    """Firestore database client with methods for all profile operations."""
    
    def __init__(self):
        """Initialize Firestore client."""
        self.db = firestore.Client()
        logger.info("[Firestore] Client initialized")
    
    # ==================== USER PROFILES ====================
    
    def get_profile(self, user_id: str) -> Optional[Dict]:
        """
        Get user's profile document.
        
        Args:
            user_id: User's email address
            
        Returns:
            Profile dict or None if not found
        """
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('profile').document('data')
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"[Firestore] Error getting profile for {user_id}: {e}")
            return None
    
    def save_profile(self, user_id: str, profile_data: Dict, merge: bool = True) -> bool:
        """
        Save or update user's profile.
        
        Args:
            user_id: User's email address
            profile_data: Profile data to save
            merge: If True, merge with existing data. If False, overwrite.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('profile').document('data')
            doc_ref.set(profile_data, merge=merge)
            logger.info(f"[Firestore] Saved profile for {user_id} (merge={merge})")
            return True
            
        except Exception as e:
            logger.error(f"[Firestore] Error saving profile for {user_id}: {e}")
            return False
    
    def delete_profile(self, user_id: str) -> bool:
        """
        Delete user's entire profile.
        
        Args:
            user_id: User's email address
            
        Returns:
            True if successful
        """
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('profile').document('data')
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted profile for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[Firestore] Error deleting profile for {user_id}: {e}")
            return False
    
    # ==================== FILE METADATA ====================
    
    def save_file_metadata(self, user_id: str, file_id: str, metadata: Dict) -> bool:
        """Save file metadata to files subcollection."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('files').document(file_id)
            doc_ref.set(metadata)
            logger.info(f"[Firestore] Saved file metadata: {file_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving file metadata: {e}")
            return False
    
    def get_file_metadata(self, user_id: str, file_id: str) -> Optional[Dict]:
        """Get file metadata."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('files').document(file_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting file metadata: {e}")
            return None
    
    def list_files(self, user_id: str) -> List[Dict]:
        """List all files for a user."""
        try:
            files_ref = self.db.collection('users').document(user_id).collection('files')
            docs = files_ref.stream()
            return [{'file_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error listing files: {e}")
            return []
    
    def delete_file_metadata(self, user_id: str, file_id: str) -> bool:
        """Delete file metadata."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('files').document(file_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted file metadata: {file_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting file metadata: {e}")
            return False
    
    # ==================== CREDITS ====================
    
    def get_credits(self, user_id: str) -> Optional[Dict]:
        """Get user's credit information."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('credits').document('data')
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting credits: {e}")
            return None
    
    def save_credits(self, user_id: str, credits_data: Dict) -> bool:
        """Save user's credit information."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('credits').document('data')
            doc_ref.set(credits_data, merge=True)
            logger.info(f"[Firestore] Saved credits for {user_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving credits: {e}")
            return False
    
    # ==================== COLLEGE LIST ====================
    
    def add_to_college_list(self, user_id: str, university_id: str, data: Dict) -> bool:
        """Add university to user's college list."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('college_list').document(university_id)
            data['added_at'] = datetime.utcnow().isoformat()
            doc_ref.set(data, merge=True)
            logger.info(f"[Firestore] Added {university_id} to college list")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error adding to college list: {e}")
            return False
    
    def get_college_list(self, user_id: str) -> List[Dict]:
        """Get user's college list."""
        try:
            list_ref = self.db.collection('users').document(user_id).collection('college_list')
            docs = list_ref.stream()
            return [{'university_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting college list: {e}")
            return []
    
    def remove_from_college_list(self, user_id: str, university_id: str) -> bool:
        """Remove university from college list."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('college_list').document(university_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Removed {university_id} from college list")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error removing from college list: {e}")
            return False
    
    # ==================== COLLEGE FITS ====================
    
    def save_college_fit(self, user_id: str, university_id: str, fit_data: Dict) -> bool:
        """Save college fit analysis."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('college_fits').document(university_id)
            fit_data['computed_at'] = datetime.utcnow().isoformat()
            doc_ref.set(fit_data, merge=True)
            logger.info(f"[Firestore] Saved fit for {university_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving fit: {e}")
            return False
    
    def get_college_fit(self, user_id: str, university_id: str) -> Optional[Dict]:
        """Get college fit analysis."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('college_fits').document(university_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting fit: {e}")
            return None
    
    def get_all_fits(self, user_id: str) -> List[Dict]:
        """Get all college fits for user."""
        try:
            fits_ref = self.db.collection('users').document(user_id).collection('college_fits')
            docs = fits_ref.stream()
            return [{'university_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting fits: {e}")
            return []
    
    def delete_college_fit(self, user_id: str, university_id: str) -> bool:
        """Delete college fit analysis."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('college_fits').document(university_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted fit for {university_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting fit: {e}")
            return False
    
    # ==================== CHAT CONVERSATIONS ====================
    
    def save_conversation(self, user_id: str, conversation_id: str, conversation_data: Dict) -> bool:
        """Save chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('chat_conversations').document(conversation_id)
            conversation_data['updated_at'] = datetime.utcnow().isoformat()
            doc_ref.set(conversation_data, merge=True)
            logger.info(f"[Firestore] Saved conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving conversation: {e}")
            return False
    
    def get_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Get chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('chat_conversations').document(conversation_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting conversation: {e}")
            return None
    
    def list_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """List user's chat conversations."""
        try:
            convs_ref = self.db.collection('users').document(user_id).collection('chat_conversations')
            docs = convs_ref.order_by('updated_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'conversation_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error listing conversations: {e}")
            return []
    
    def delete_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('chat_conversations').document(conversation_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting conversation: {e}")
            return False
    
    # ==================== FIT CHAT CONVERSATIONS ====================
    
    def save_fit_conversation(self, user_id: str, conversation_id: str, conversation_data: Dict) -> bool:
        """Save fit chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('fit_chat_conversations').document(conversation_id)
            conversation_data['updated_at'] = datetime.utcnow().isoformat()
            doc_ref.set(conversation_data, merge=True)
            logger.info(f"[Firestore] Saved fit conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving fit conversation: {e}")
            return False
    
    def get_fit_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Get fit chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('fit_chat_conversations').document(conversation_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting fit conversation: {e}")
            return None
    
    def list_fit_conversations(self, user_id: str, university_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """List user's fit chat conversations, optionally filtered by university."""
        try:
            convs_ref = self.db.collection('users').document(user_id).collection('fit_chat_conversations')
            
            # Filter by university if provided
            if university_id:
                query = convs_ref.where(filter=FieldFilter('university_id', '==', university_id))
            else:
                query = convs_ref
            
            # Order by updated_at descending and limit
            docs = query.order_by('updated_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'conversation_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error listing fit conversations: {e}")
            return []
    
    def delete_fit_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete fit chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('fit_chat_conversations').document(conversation_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted fit conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting fit conversation: {e}")
            return False
    
    # ==================== PROFILE CHAT (SELF-DISCOVERY) CONVERSATIONS ====================
    # Supports multiple conversations per user, matching fit_chat pattern
    
    def save_profile_conversation(self, user_id: str, conversation_id: str, conversation_data: Dict) -> bool:
        """Save profile chat (Self-Discovery) conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('profile_chat_conversations').document(conversation_id)
            conversation_data['updated_at'] = datetime.utcnow().isoformat()
            doc_ref.set(conversation_data, merge=True)
            logger.info(f"[Firestore] Saved profile conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving profile conversation: {e}")
            return False
    
    def get_profile_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Get profile chat (Self-Discovery) conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('profile_chat_conversations').document(conversation_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting profile conversation: {e}")
            return None
    
    def list_profile_conversations(self, user_id: str, limit: int = 20) -> List[Dict]:
        """List user's profile chat (Self-Discovery) conversations."""
        try:
            convs_ref = self.db.collection('users').document(user_id).collection('profile_chat_conversations')
            docs = convs_ref.order_by('updated_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'conversation_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error listing profile conversations: {e}")
            return []
    
    def delete_profile_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete profile chat (Self-Discovery) conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('profile_chat_conversations').document(conversation_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted profile conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting profile conversation: {e}")
            return False

    
    # ==================== UNIVERSITY CHAT CONVERSATIONS ====================
    
    def save_university_conversation(self, user_id: str, university_id: str, conversation_data: Dict) -> bool:
        """Save university chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('university_chat_conversations').document(university_id)
            conversation_data['updated_at'] = datetime.utcnow().isoformat()
            doc_ref.set(conversation_data, merge=True)
            logger.info(f"[Firestore] Saved university conversation for {user_id}/{university_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving university conversation: {e}")
            return False
    
    def get_university_conversation(self, user_id: str, university_id: str) -> Optional[Dict]:
        """Get university chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('university_chat_conversations').document(university_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting university conversation: {e}")
            return None
    
    def list_university_conversations(self, user_id: str, limit: int = 20) -> List[Dict]:
        """List user's university chat conversations."""
        try:
            convs_ref = self.db.collection('users').document(user_id).collection('university_chat_conversations')
            docs = convs_ref.order_by('updated_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'university_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error listing university conversations: {e}")
            return []
    
    def clear_university_conversation(self, user_id: str, university_id: str) -> bool:
        """Clear university chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('university_chat_conversations').document(university_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Cleared university conversation for {user_id}/{university_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error clearing university conversation: {e}")
            return False


# Global instance
_db_instance = None

def get_db() -> FirestoreDB:
    """Get or create Firestore database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = FirestoreDB()
    return _db_instance
