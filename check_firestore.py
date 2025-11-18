#!/usr/bin/env python3
"""
Check Firestore database status and collections.
"""

import os
from google.cloud import firestore
from google.auth import default

# Authenticate using default credentials
creds, project = default()
db = firestore.Client(project="college-counselling-478115")

print("🔍 Checking Firestore database status...")

try:
    # Test database connectivity by listing collections
    collections = db.collections()
    
    collection_names = []
    for collection in collections:
        collection_names.append(collection.id)
    
    print(f"\n📊 Database Status: ✅ Connected")
    print(f"📁 Collections found: {len(collection_names)}")
    
    if collection_names:
        print("\n📋 Collections:")
        for i, collection_name in enumerate(collection_names):
            print(f"  {i+1}. {collection_name}")
            
            # Count documents in this collection
            collection_ref = db.collection(collection_name)
            doc_count = len(list(collection_ref.stream()))
            print(f"     - Documents: {doc_count}")
            
            # Show sample document if exists
            if doc_count > 0:
                sample_doc = collection_ref.limit(1).stream()
                for doc in sample_doc:
                    data = doc.to_dict()
                    print(f"     - Sample doc ID: {doc.id}")
                    print(f"     - Sample keys: {list(data.keys())[:5]}...")
                    break
            print()
    else:
        print("\n📭 No collections found - database is empty")
        print("💡 Collections will be created when documents are uploaded")
    
    print("✅ Firestore check complete!")
    
except Exception as e:
    print(f"❌ Error accessing Firestore: {str(e)}")
    print("💡 Make sure Firestore is properly configured")
