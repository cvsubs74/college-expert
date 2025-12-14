#!/usr/bin/env python3
"""
Migration script to split monolithic student_profiles into 3 separate indices:
1. student_profiles_v2 (core data only)
2. student_college_list_items (one doc per user+university)
3. student_college_fits (one doc per user+university)

Run this script to migrate existing data. The old index is preserved for rollback.
"""

import os
import json
import hashlib
from datetime import datetime
from elasticsearch import Elasticsearch, helpers

# Configuration
ES_CLOUD_ID = os.getenv("ES_CLOUD_ID")
ES_API_KEY = os.getenv("ES_API_KEY")

# Index names
OLD_INDEX = "student_profiles"
NEW_PROFILES_INDEX = "student_profiles_v2"
LIST_ITEMS_INDEX = "student_college_list"
FITS_INDEX = "student_college_fits"

def get_es_client():
    """Create Elasticsearch client."""
    return Elasticsearch(
        cloud_id=ES_CLOUD_ID,
        api_key=ES_API_KEY,
        request_timeout=60
    )

def create_indices(es):
    """Create the 3 new indices with proper mappings."""
    
    # 1. Core profiles index (lightweight)
    profiles_mapping = {
        "mappings": {
            "properties": {
                "user_email": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "name": {"type": "text"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "academics": {
                    "type": "object",
                    "properties": {
                        "weighted_gpa": {"type": "float"},
                        "unweighted_gpa": {"type": "float"},
                        "sat_score": {"type": "integer"},
                        "act_score": {"type": "integer"},
                        "ap_courses": {"type": "keyword"},
                        "class_rank": {"type": "text"}
                    }
                },
                "preferences": {
                    "type": "object",
                    "properties": {
                        "majors": {"type": "keyword"},
                        "location_preference": {"type": "keyword"},
                        "campus_type": {"type": "keyword"},
                        "budget": {"type": "integer"}
                    }
                },
                "activities": {"type": "object", "enabled": False},
                "awards": {"type": "object", "enabled": False},
                "profile_content": {"type": "text"},
                "profile_source": {"type": "keyword"},
                "profile_version": {"type": "keyword"}
            }
        }
    }
    
    # 2. College list items index
    list_items_mapping = {
        "mappings": {
            "properties": {
                "user_email": {"type": "keyword"},
                "university_id": {"type": "keyword"},
                "university_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "status": {"type": "keyword"},
                "order": {"type": "integer"},
                "added_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "student_notes": {"type": "text"}
            }
        }
    }
    
    # 3. College fits index
    fits_mapping = {
        "mappings": {
            "properties": {
                "user_email": {"type": "keyword"},
                "university_id": {"type": "keyword"},
                "university_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "computed_at": {"type": "date"},
                "profile_version_hash": {"type": "keyword"},
                "fit_category": {"type": "keyword"},
                "match_score": {"type": "integer"},
                "explanation": {"type": "text"},
                "factors": {"type": "object", "enabled": False},
                "recommendations": {"type": "text"},
                "acceptance_rate": {"type": "float"},
                "us_news_rank": {"type": "integer"},
                "location": {"type": "object", "enabled": False},
                "market_position": {"type": "keyword"}
            }
        }
    }
    
    # Create indices (delete if exists for clean migration)
    for index_name, mapping in [
        (NEW_PROFILES_INDEX, profiles_mapping),
        (LIST_ITEMS_INDEX, list_items_mapping),
        (FITS_INDEX, fits_mapping)
    ]:
        if es.indices.exists(index=index_name):
            print(f"[WARN] Index {index_name} exists. Deleting for clean migration...")
            es.indices.delete(index=index_name)
        
        es.indices.create(index=index_name, body=mapping)
        print(f"[OK] Created index: {index_name}")

def generate_doc_id(user_email, university_id):
    """Generate a unique document ID for user+university pair."""
    email_hash = hashlib.md5(user_email.encode()).hexdigest()[:8]
    return f"{email_hash}_{university_id}"

def migrate_data(es):
    """Migrate data from old index to new indices."""
    
    # Fetch all documents from old index
    print(f"\n[INFO] Fetching all documents from {OLD_INDEX}...")
    
    query = {"query": {"match_all": {}}, "size": 1000}
    response = es.search(index=OLD_INDEX, body=query)
    
    hits = response.get('hits', {}).get('hits', [])
    print(f"[INFO] Found {len(hits)} profiles to migrate")
    
    stats = {
        "profiles": 0,
        "list_items": 0,
        "fits": 0,
        "errors": []
    }
    
    for hit in hits:
        source = hit.get('_source', {})
        # The field is 'user_id' but contains email
        user_email = source.get('user_id')
        
        if not user_email:
            stats["errors"].append(f"No user_id in doc {hit['_id']}")
            continue
        
        print(f"\n[MIGRATING] {user_email}")
        
        try:
            # 1. Extract and save core profile
            core_profile = {
                "user_email": user_email,
                "document_id": source.get('document_id'),
                "filename": source.get('filename'),
                "file_type": source.get('file_type'),
                "created_at": source.get('indexed_at'),
                "updated_at": source.get('content_updated_at') or source.get('indexed_at'),
                "profile_content": source.get('content'),  # The main profile text
                "needs_fit_recomputation": source.get('needs_fit_recomputation', False),
                "fits_computed_at": source.get('fits_computed_at')
            }
            
            # Remove None values
            core_profile = {k: v for k, v in core_profile.items() if v is not None}
            
            es.index(index=NEW_PROFILES_INDEX, id=user_email, body=core_profile)
            stats["profiles"] += 1
            print(f"  [OK] Core profile saved")
            
            # 2. Extract and save college list items
            college_list = source.get('college_list', [])
            for item in college_list:
                uni_id = item.get('university_id')
                if not uni_id:
                    continue
                
                list_doc = {
                    "user_email": user_email,
                    "university_id": uni_id,
                    "university_name": item.get('university_name'),
                    "status": item.get('status', 'favorites'),
                    "order": item.get('order'),
                    "added_at": item.get('added_at'),
                    "updated_at": item.get('added_at'),  # Use added_at as updated_at
                    "intended_major": item.get('intended_major'),
                    "student_notes": item.get('notes')
                }
                
                # Remove None values
                list_doc = {k: v for k, v in list_doc.items() if v is not None}
                
                doc_id = generate_doc_id(user_email, uni_id)
                es.index(index=LIST_ITEMS_INDEX, id=doc_id, body=list_doc)
                stats["list_items"] += 1
            
            print(f"  [OK] {len(college_list)} list items saved")
            
            # 3. Extract and save college fits (from college_fits field, NOT from college_list)
            college_fits = source.get('college_fits', {})
            if isinstance(college_fits, str):
                try:
                    college_fits = json.loads(college_fits)
                except:
                    college_fits = {}
            
            for uni_id, fit_data in college_fits.items():
                if not fit_data:
                    continue
                
                fit_doc = {
                    "user_email": user_email,
                    "university_id": uni_id,
                    "university_name": fit_data.get('university_name'),
                    "computed_at": fit_data.get('computed_at') or datetime.utcnow().isoformat(),
                    "fit_category": fit_data.get('fit_category'),
                    "match_score": fit_data.get('match_score') or fit_data.get('match_percentage'),
                    "explanation": fit_data.get('explanation'),
                    "factors": fit_data.get('factors', []),
                    "recommendations": fit_data.get('recommendations', []),
                    "acceptance_rate": fit_data.get('acceptance_rate'),
                    "us_news_rank": fit_data.get('us_news_rank'),
                    "location": fit_data.get('location'),
                    "market_position": fit_data.get('market_position')
                }
                
                # Remove None values
                fit_doc = {k: v for k, v in fit_doc.items() if v is not None}
                
                doc_id = generate_doc_id(user_email, uni_id)
                es.index(index=FITS_INDEX, id=doc_id, body=fit_doc)
                stats["fits"] += 1
            
            print(f"  [OK] {len(college_fits)} fits saved")
            
        except Exception as e:
            stats["errors"].append(f"{user_email}: {str(e)}")
            print(f"  [ERROR] {e}")
    
    return stats

def verify_migration(es):
    """Verify data was migrated correctly."""
    print("\n" + "="*50)
    print("VERIFICATION")
    print("="*50)
    
    # Count documents in each index
    for index in [OLD_INDEX, NEW_PROFILES_INDEX, LIST_ITEMS_INDEX, FITS_INDEX]:
        try:
            count = es.count(index=index)['count']
            print(f"{index}: {count} documents")
        except Exception as e:
            print(f"{index}: ERROR - {e}")

def main():
    print("="*50)
    print("PROFILE DATA MIGRATION")
    print("="*50)
    print(f"Source: {OLD_INDEX}")
    print(f"Targets: {NEW_PROFILES_INDEX}, {LIST_ITEMS_INDEX}, {FITS_INDEX}")
    print("="*50)
    
    # Connect to ES
    es = get_es_client()
    print("[OK] Connected to Elasticsearch")
    
    # Step 1: Create new indices
    print("\n[STEP 1] Creating new indices...")
    create_indices(es)
    
    # Step 2: Migrate data
    print("\n[STEP 2] Migrating data...")
    stats = migrate_data(es)
    
    # Step 3: Verify
    print("\n[STEP 3] Verifying migration...")
    verify_migration(es)
    
    # Summary
    print("\n" + "="*50)
    print("MIGRATION COMPLETE")
    print("="*50)
    print(f"Profiles migrated: {stats['profiles']}")
    print(f"List items created: {stats['list_items']}")
    print(f"Fits created: {stats['fits']}")
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats['errors']:
            print(f"  - {err}")
    
    print("\n[NEXT STEPS]")
    print("1. Verify data integrity manually")
    print("2. Update backend code to use new indices")
    print("3. Deploy and test")

if __name__ == "__main__":
    main()
