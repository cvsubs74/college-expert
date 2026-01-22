"""
Script to clear essay tracker data from Firestore.
This is needed after the UC school grouping fix to remove duplicate UC entries.

Usage:
    python clear_essay_tracker.py cvsubramanian@outlook.com
"""

import sys
import os
from google.cloud import firestore

def clear_essay_tracker(user_email):
    """Clear all essay tracker entries for a user."""
    db = firestore.Client()
    
    print(f"Clearing essay tracker for {user_email}...")
    
    # Get reference to essay_tracker subcollection
    user_ref = db.collection('users').document(user_email)
    essay_tracker_ref = user_ref.collection('essay_tracker')
    
    # Delete all documents in the essay_tracker subcollection
    docs = essay_tracker_ref.stream()
    deleted_count = 0
    
    for doc in docs:
        doc.reference.delete()
        deleted_count += 1
        print(f"  Deleted: {doc.id}")
    
    print(f"\n✅ Cleared {deleted_count} essay tracker entries")
    print(f"\nNext step: Refresh the app at https://college-strategy.web.app/progress")
    print("The essays will automatically re-sync with the corrected grouping.\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clear_essay_tracker.py <user_email>")
        sys.exit(1)
    
    user_email = sys.argv[1]
    clear_essay_tracker(user_email)
