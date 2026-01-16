"""
Firestore database layer for Payment Manager V2.
Provides clean interface for user purchase and subscription operations.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from google.cloud import firestore

logger = logging.getLogger(__name__)


class PaymentFirestoreDB:
    """Firestore database client for payment and subscription operations."""
    
    def __init__(self):
        """Initialize Firestore client."""
        self.db = firestore.Client()
        logger.info("[PaymentFirestore] Client initialized")
    
    # ==================== USER PURCHASES ====================
    
    def get_purchases(self, user_id: str) -> Optional[Dict]:
        """
        Get user's purchase record.
        
        Args:
            user_id: User's email address
            
        Returns:
            Purchase dict or None if not found
        """
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('purchases').document('data')
            doc = doc_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"[PaymentFirestore] Error getting purchases for {user_id}: {e}")
            return None
    
    def save_purchases(self, user_id: str, purchases_data: Dict) -> bool:
        """
        Save or update user's purchase record.
        
        Args:
            user_id: User's email address
            purchases_data: Purchase data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('purchases').document('data')
            purchases_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            purchases_data['user_email'] = user_id
            doc_ref.set(purchases_data, merge=True)
            logger.info(f"[PaymentFirestore] Saved purchases for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[PaymentFirestore] Error saving purchases for {user_id}: {e}")
            return False
    
    # ==================== CREDITS SYNC ====================
    
    def get_credits(self, user_id: str) -> Optional[Dict]:
        """Get user's credit information (for reading unified state)."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('credits').document('data')
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"[PaymentFirestore] Error getting credits: {e}")
            return None
    
    def save_credits(self, user_id: str, credits_data: Dict) -> bool:
        """Save user's credit information (for updating unified state)."""
        try:
            doc_ref = self.db.collection('users').document(user_id).collection('credits').document('data')
            credits_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            doc_ref.set(credits_data, merge=True)
            logger.info(f"[PaymentFirestore] Saved credits for {user_id}")
            return True
        except Exception as e:
            logger.error(f"[PaymentFirestore] Error saving credits: {e}")
            return False
    
    def add_purchase_record(self, user_id: str, purchase_details: Dict) -> bool:
        """
        Add a purchase record to user's purchase history.
        
        Args:
            user_id: User's email address
            purchase_details: Details of the purchase
            
        Returns:
            True if successful
        """
        try:
            history_ref = self.db.collection('users').document(user_id).collection('purchase_history')
            purchase_details['timestamp'] = datetime.now(timezone.utc).isoformat()
            history_ref.add(purchase_details)
            
            logger.info(f"[PaymentFirestore] Added purchase record for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[PaymentFirestore] Error adding purchase record: {e}")
            return False
    
    def find_user_by_stripe_subscription(self, subscription_id: str) -> Optional[str]:
        """
        Find user email by Stripe subscription ID.
        Note: This requires iterating through users, or we can use
        a separate index collection. For now, we rely on Stripe customer email.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            User email or None
        """
        # This is a limitation - Firestore doesn't have cross-document queries like ES
        # We rely on getting the customer email from Stripe directly instead
        logger.warning(f"[PaymentFirestore] find_user_by_stripe_subscription not implemented for {subscription_id}")
        return None


# Global instance
_db_instance = None

def get_payment_db() -> PaymentFirestoreDB:
    """Get or create Payment Firestore database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = PaymentFirestoreDB()
    return _db_instance
