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
    
    def update_application_status(self, user_id: str, university_id: str, status_data: Dict) -> bool:
        """Update application status for a university in the college list."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('college_list').document(university_id)
            status_data['status_updated_at'] = datetime.utcnow().isoformat()
            doc_ref.update(status_data)
            logger.info(f"[Firestore] Updated application status for {university_id}: {status_data.get('status', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error updating application status: {e}")
            return False
    
    # ==================== ESSAYS ====================
    
    def save_essay(self, user_id: str, essay_id: str, essay_data: Dict) -> bool:
        """Save or update an essay draft."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('essays').document(essay_id)
            essay_data['updated_at'] = datetime.utcnow().isoformat()
            if 'created_at' not in essay_data:
                existing = doc_ref.get()
                if existing.exists:
                    essay_data['created_at'] = existing.to_dict().get('created_at', essay_data['updated_at'])
                else:
                    essay_data['created_at'] = essay_data['updated_at']
            doc_ref.set(essay_data, merge=True)
            logger.info(f"[Firestore] Saved essay {essay_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving essay: {e}")
            return False
    
    def get_essays(self, user_id: str, university_id: str = None) -> List[Dict]:
        """Get all essays for user, optionally filtered by university."""
        try:
            essays_ref = self.db.collection('users').document(user_id).collection('essays')
            if university_id:
                query = essays_ref.where(filter=FieldFilter('university_id', '==', university_id))
                docs = query.stream()
            else:
                docs = essays_ref.order_by('updated_at', direction=firestore.Query.DESCENDING).stream()
            return [{'essay_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting essays: {e}")
            return []
    
    def get_essay(self, user_id: str, essay_id: str) -> Optional[Dict]:
        """Get a specific essay."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('essays').document(essay_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting essay: {e}")
            return None
    
    def update_essay_status(self, user_id: str, essay_id: str, status: str) -> bool:
        """Update essay status (not_started, draft, review, final)."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('essays').document(essay_id)
            doc_ref.update({
                'status': status,
                'status_updated_at': datetime.utcnow().isoformat()
            })
            logger.info(f"[Firestore] Updated essay {essay_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error updating essay status: {e}")
            return False
    
    # ==================== FINANCIAL AID PACKAGES ====================
    
    def save_aid_package(self, user_id: str, university_id: str, aid_data: Dict) -> bool:
        """Save financial aid package for a university."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('aid_packages').document(university_id)
            aid_data['updated_at'] = datetime.utcnow().isoformat()
            # Calculate net cost if not provided
            if 'net_cost' not in aid_data and 'cost_of_attendance' in aid_data and 'grants_scholarships' in aid_data:
                aid_data['net_cost'] = aid_data['cost_of_attendance'] - aid_data['grants_scholarships']
            doc_ref.set(aid_data, merge=True)
            logger.info(f"[Firestore] Saved aid package for {university_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving aid package: {e}")
            return False
    
    def get_aid_packages(self, user_id: str) -> List[Dict]:
        """Get all aid packages for user."""
        try:
            aids_ref = self.db.collection('users').document(user_id).collection('aid_packages')
            docs = aids_ref.stream()
            return [{'university_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting aid packages: {e}")
            return []
    
    def get_aid_package(self, user_id: str, university_id: str) -> Optional[Dict]:
        """Get aid package for a specific university."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('aid_packages').document(university_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting aid package: {e}")
            return None
    
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
    
    # ==================== COUNSELOR CHAT CONVERSATIONS ====================
    
    def save_counselor_conversation(self, user_id: str, conversation_id: str, conversation_data: Dict) -> bool:
        """Save counselor chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('counselor_chat_conversations').document(conversation_id)
            conversation_data['updated_at'] = datetime.utcnow().isoformat()
            if 'created_at' not in conversation_data:
                # Check if exists to preserve created_at
                existing = doc_ref.get()
                if existing.exists:
                    conversation_data['created_at'] = existing.to_dict().get('created_at', conversation_data['updated_at'])
                else:
                    conversation_data['created_at'] = conversation_data['updated_at']
            doc_ref.set(conversation_data, merge=True)
            logger.info(f"[Firestore] Saved counselor conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving counselor conversation: {e}")
            return False
    
    def get_counselor_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Get counselor chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('counselor_chat_conversations').document(conversation_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[Firestore] Error getting counselor conversation: {e}")
            return None
    
    def list_counselor_conversations(self, user_id: str, limit: int = 20) -> List[Dict]:
        """List user's counselor chat conversations, ordered by most recent first."""
        try:
            convs_ref = self.db.collection('users').document(user_id).collection('counselor_chat_conversations')
            docs = convs_ref.order_by('updated_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            return [{'conversation_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error listing counselor conversations: {e}")
            return []
    
    def delete_counselor_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete counselor chat conversation."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('counselor_chat_conversations').document(conversation_id)
            doc_ref.delete()
            logger.info(f"[Firestore] Deleted counselor conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting counselor conversation: {e}")
            return False
    
    # ==================== ROADMAP TASKS ====================
    
    def save_roadmap_task(self, user_id: str, task_id: str, task_data: Dict) -> bool:
        """Save or update a roadmap task."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('roadmap_tasks').document(task_id)
            task_data['updated_at'] = datetime.utcnow().isoformat()
            if 'created_at' not in task_data:
                existing = doc_ref.get()
                if existing.exists:
                    task_data['created_at'] = existing.to_dict().get('created_at', task_data['updated_at'])
                else:
                    task_data['created_at'] = task_data['updated_at']
            doc_ref.set(task_data, merge=True)
            logger.info(f"[Firestore] Saved roadmap task {task_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error saving roadmap task: {e}")
            return False
    
    def get_roadmap_tasks(self, user_id: str, status: str = None, university_id: str = None) -> List[Dict]:
        """Get user's roadmap tasks, optionally filtered by status or university."""
        try:
            tasks_ref = self.db.collection('users').document(user_id).collection('roadmap_tasks')
            query = tasks_ref
            
            if status:
                query = query.where(filter=FieldFilter('status', '==', status))
            if university_id:
                query = query.where(filter=FieldFilter('university_id', '==', university_id))
            
            docs = query.order_by('due_date').stream()
            return [{'task_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting roadmap tasks: {e}")
            return []
    
    def update_task_status(self, user_id: str, task_id: str, status: str, completed_at: str = None) -> bool:
        """Update a roadmap task's status."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('roadmap_tasks').document(task_id)
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            if completed_at:
                update_data['completed_at'] = completed_at
            doc_ref.update(update_data)
            logger.info(f"[Firestore] Updated task {task_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error updating task status: {e}")
            return False

    # ==================== ESSAY TRACKER ====================
    
    def get_essay_tracker(self, user_id: str) -> List[Dict]:
        """Get all essay tracker entries for a user."""
        try:
            docs = self.db.collection('users').document(user_id).collection('essay_tracker').stream()
            return [{'essay_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting essay tracker: {e}")
            return []
    
    def sync_essay_tracker(self, user_id: str, essays: List[Dict]) -> bool:
        """
        Sync essay prompts to user's tracker.
        Creates new entries for prompts not already tracked.
        
        Args:
            user_id: User's email
            essays: List of essay dicts with university_id, prompt, word_limit, etc.
        """
        try:
            batch = self.db.batch()
            tracker_ref = self.db.collection('users').document(user_id).collection('essay_tracker')
            
            # Get existing essays to avoid duplicates
            existing = {doc.id: doc.to_dict() for doc in tracker_ref.stream()}
            
            for essay in essays:
                # Create unique ID from university + prompt hash
                essay_id = f"{essay.get('university_id', 'shared')}_{hash(essay.get('prompt', '')[:50]) % 100000}"
                
                if essay_id not in existing:
                    doc_ref = tracker_ref.document(essay_id)
                    essay_data = {
                        'university_id': essay.get('university_id'),
                        'university_name': essay.get('university_name'),
                        'prompt_text': essay.get('prompt'),
                        'prompt_type': essay.get('type', 'supplement'),
                        'word_limit': essay.get('word_limit'),
                        'is_required': essay.get('required', True),
                        'selection_rule': essay.get('selection_rule'),  # e.g., {"required": 4, "of": 8}
                        'status': 'not_started',
                        'word_count': 0,
                        'content': '',
                        'brainstorming_questions': essay.get('brainstorming_questions', []),
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    batch.set(doc_ref, essay_data)
            
            batch.commit()
            logger.info(f"[Firestore] Synced {len(essays)} essays for {user_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error syncing essay tracker: {e}")
            return False
    
    def update_essay_progress(self, user_id: str, essay_id: str, updates: Dict) -> bool:
        """Update essay progress (status, content, word_count)."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('essay_tracker').document(essay_id)
            updates['updated_at'] = datetime.utcnow().isoformat()
            doc_ref.update(updates)
            logger.info(f"[Firestore] Updated essay {essay_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error updating essay progress: {e}")
            return False
    
    def delete_essay_tracker_entry(self, user_id: str, essay_id: str) -> bool:
        """Delete an essay tracker entry (when school is removed from list)."""
        try:
            self.db.collection('users').document(user_id).collection('essay_tracker').document(essay_id).delete()
            logger.info(f"[Firestore] Deleted essay tracker entry {essay_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error deleting essay tracker entry: {e}")
            return False

    # ==================== SCHOLARSHIP TRACKER ====================
    
    def get_scholarship_tracker(self, user_id: str) -> List[Dict]:
        """Get all scholarship tracker entries for a user."""
        try:
            docs = self.db.collection('users').document(user_id).collection('scholarship_tracker').stream()
            return [{'scholarship_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            logger.error(f"[Firestore] Error getting scholarship tracker: {e}")
            return []
    
    def sync_scholarship_tracker(self, user_id: str, scholarships: List[Dict], user_profile: Dict = None) -> bool:
        """
        Sync scholarships to user's tracker with eligibility indicators.
        
        Args:
            user_id: User's email
            scholarships: List of scholarship dicts from university data
            user_profile: Optional user profile for eligibility calculation
        """
        try:
            batch = self.db.batch()
            tracker_ref = self.db.collection('users').document(user_id).collection('scholarship_tracker')
            
            # Get existing to avoid duplicates
            existing = {doc.id: doc.to_dict() for doc in tracker_ref.stream()}
            
            for scholarship in scholarships:
                # Create unique ID
                scholarship_id = f"{scholarship.get('university_id', 'general')}_{hash(scholarship.get('name', '')[:30]) % 100000}"
                
                if scholarship_id not in existing:
                    doc_ref = tracker_ref.document(scholarship_id)
                    
                    # Calculate potential eligibility
                    eligibility = self._calculate_eligibility(scholarship, user_profile)
                    
                    scholarship_data = {
                        'university_id': scholarship.get('university_id'),
                        'university_name': scholarship.get('university_name'),
                        'scholarship_name': scholarship.get('name'),
                        'type': scholarship.get('type', 'Need'),  # Need, Merit, Specific
                        'amount': scholarship.get('amount'),
                        'deadline': scholarship.get('deadline'),
                        'benefits': scholarship.get('benefits'),
                        'application_method': scholarship.get('application_method'),
                        'application_required': 'automatic' not in (scholarship.get('application_method', '').lower()),
                        'status': 'not_applied',  # not_applied, applied, received, not_eligible
                        'eligibility_indicator': eligibility,
                        'notes': '',
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat()
                    }
                    batch.set(doc_ref, scholarship_data)
            
            batch.commit()
            logger.info(f"[Firestore] Synced {len(scholarships)} scholarships for {user_id}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error syncing scholarship tracker: {e}")
            return False
    
    def _calculate_eligibility(self, scholarship: Dict, user_profile: Dict) -> str:
        """Calculate eligibility indicator based on scholarship type and profile."""
        if not user_profile:
            return 'unknown'
        
        scholarship_type = scholarship.get('type', '').lower()
        
        if 'need' in scholarship_type:
            # Check if need-based eligibility indicators are present
            return 'may_qualify'  # Conservative: assume most students may qualify
        elif 'merit' in scholarship_type:
            # Check GPA/test scores if available
            gpa = user_profile.get('gpa', {}).get('unweighted', 0)
            if gpa >= 3.8:
                return 'likely_eligible'
            elif gpa >= 3.5:
                return 'may_qualify'
            return 'unknown'
        
        return 'may_qualify'
    
    def update_scholarship_status(self, user_id: str, scholarship_id: str, status: str, notes: str = None) -> bool:
        """Update scholarship application status."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('scholarship_tracker').document(scholarship_id)
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            if notes is not None:
                update_data['notes'] = notes
            doc_ref.update(update_data)
            logger.info(f"[Firestore] Updated scholarship {scholarship_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"[Firestore] Error updating scholarship status: {e}")
            return False


# Global instance
_db_instance = None

def get_db() -> FirestoreDB:
    """Get or create Firestore database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = FirestoreDB()
    return _db_instance

