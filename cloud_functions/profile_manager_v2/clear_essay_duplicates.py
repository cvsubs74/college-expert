#!/usr/bin/env python3
"""
Script to clear essay tracker for a user to fix duplicates.
Run this once after deploying the hashlib fix.
"""

from google.cloud import firestore

# Initialize Firestore client
db = firestore.Client()

# Replace with your user email
USER_EMAIL = "cvsubramanian@outlook.com"

def clear_essay_tracker(user_email: str):
    """Delete all essay_tracker entries for a user."""
    tracker_ref = db.collection('users').document(user_email).collection('essay_tracker')
    
    # Get all essays
    essays = list(tracker_ref.stream())
    print(f"Found {len(essays)} essays for {user_email}")
    
    # Delete each
    for essay in essays:
        essay.reference.delete()
        print(f"Deleted: {essay.id}")
    
    print(f"\n✅ Cleared {len(essays)} essays. Refresh the page to re-sync with new IDs.")

if __name__ == "__main__":
    confirm = input(f"This will delete all essay_tracker entries for {USER_EMAIL}. Continue? (y/n): ")
    if confirm.lower() == 'y':
        clear_essay_tracker(USER_EMAIL)
    else:
        print("Aborted.")
