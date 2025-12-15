#!/usr/bin/env python3
"""
Delete old student_profile indices and create fresh flattened schema.
Run this script directly to interact with Elasticsearch.
"""
import os
import subprocess
from elasticsearch import Elasticsearch

def get_secret(secret_name):
    """Get secret from GCP Secret Manager."""
    result = subprocess.run(
        ["gcloud", "secrets", "versions", "access", "latest", 
         "--secret", secret_name, "--project", "college-counselling-478115"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def main():
    print("🔧 Getting ES credentials...")
    ES_CLOUD_ID = get_secret("ES_CLOUD_ID")
    ES_API_KEY = get_secret("ES_API_KEY")
    
    print(f"✓ Cloud ID: {ES_CLOUD_ID[:30]}...")
    
    # Connect to Elasticsearch
    client = Elasticsearch(
        cloud_id=ES_CLOUD_ID,
        api_key=ES_API_KEY,
        request_timeout=30
    )
    
    print("✓ Connected to Elasticsearch")
    
    # List current indices
    print("\n📋 Current indices:")
    indices = client.cat.indices(format="json")
    for idx in indices:
        if "student" in idx.get("index", "").lower():
            print(f"  - {idx['index']}: {idx.get('docs.count', 0)} docs")
    
    # Delete old indices
    old_indices = ["student_profiles", "student_profiles_v2"]
    print("\n🗑️ Deleting old indices...")
    for idx_name in old_indices:
        try:
            if client.indices.exists(index=idx_name):
                client.indices.delete(index=idx_name)
                print(f"  ✓ Deleted: {idx_name}")
            else:
                print(f"  - {idx_name} doesn't exist")
        except Exception as e:
            print(f"  ✗ Error deleting {idx_name}: {e}")
    
    # Create new flattened student_profiles index
    print("\n📦 Creating new student_profiles with flattened schema...")
    
    flattened_mapping = {
        "mappings": {
            "properties": {
                # Core fields
                "user_id": {"type": "keyword"},
                "indexed_at": {"type": "date"},
                
                # Personal info (flattened)
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "school": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "location": {"type": "text"},
                "grade": {"type": "integer"},
                "graduation_year": {"type": "integer"},
                "intended_major": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                
                # Academics (flattened)
                "gpa_weighted": {"type": "float"},
                "gpa_unweighted": {"type": "float"},
                "gpa_uc": {"type": "float"},
                "class_rank": {"type": "keyword"},
                
                # Test scores (flattened)
                "sat_total": {"type": "integer"},
                "sat_math": {"type": "integer"},
                "sat_reading": {"type": "integer"},
                "act_composite": {"type": "integer"},
                
                # Arrays (nested for proper querying)
                "ap_exams": {
                    "type": "nested",
                    "properties": {
                        "subject": {"type": "keyword"},
                        "score": {"type": "integer"}
                    }
                },
                "courses": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "type": {"type": "keyword"},
                        "grade_level": {"type": "integer"},
                        "semester1_grade": {"type": "keyword"},
                        "semester2_grade": {"type": "keyword"}
                    }
                },
                "extracurriculars": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "role": {"type": "text"},
                        "description": {"type": "text"},
                        "grades": {"type": "keyword"},
                        "hours_per_week": {"type": "integer"},
                        "achievements": {"type": "text"}
                    }
                },
                "leadership_roles": {"type": "keyword"},
                "special_programs": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text"},
                        "description": {"type": "text"},
                        "grade": {"type": "integer"}
                    }
                },
                "awards": {
                    "type": "nested",
                    "properties": {
                        "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                        "grade": {"type": "integer"},
                        "description": {"type": "text"}
                    }
                },
                "work_experience": {
                    "type": "nested",
                    "properties": {
                        "employer": {"type": "text"},
                        "role": {"type": "text"},
                        "grades": {"type": "keyword"},
                        "hours_per_week": {"type": "integer"},
                        "description": {"type": "text"}
                    }
                },
                
                # Raw content for reference
                "raw_content": {"type": "text", "index": False}
            }
        },
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1
        }
    }
    
    try:
        client.indices.create(index="student_profiles", body=flattened_mapping)
        print("✓ Created student_profiles with flattened schema")
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        return
    
    # Verify
    print("\n📋 Final indices:")
    indices = client.cat.indices(format="json")
    for idx in indices:
        if "student" in idx.get("index", "").lower():
            print(f"  - {idx['index']}: {idx.get('docs.count', 0)} docs")
    
    print("\n✅ Done! student_profiles index ready with flattened schema.")

if __name__ == "__main__":
    main()
