#!/usr/bin/env python3
"""
Re-index all universities to Elasticsearch with logo URLs.
"""

import json
import os
from pathlib import Path
from elasticsearch import Elasticsearch

# ES Configuration
ES_CLOUD_ID = os.getenv('ES_CLOUD_ID')
ES_API_KEY = os.getenv('ES_API_KEY')
ES_INDEX = "universities"

# Paths
RESEARCH_DIR = Path(__file__).parent / "research"


def get_es_client():
    """Initialize Elasticsearch client."""
    return Elasticsearch(
        cloud_id=ES_CLOUD_ID,
        api_key=ES_API_KEY
    )


def index_university(es_client, university_id: str, data: dict):
    """Index or update a university document."""
    try:
        es_client.index(
            index=ES_INDEX,
            id=university_id,
            document=data
        )
        return True
    except Exception as e:
        print(f"  ✗ Index failed: {e}")
        return False


def main():
    """Re-index all universities with logo URLs."""
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    print(f"Found {len(json_files)} university files")
    print(f"Indexing to ES: {ES_INDEX}")
    print("-" * 60)
    
    es_client = get_es_client()
    
    indexed = 0
    failed = []
    
    for json_path in sorted(json_files):
        university_id = json_path.stem
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Check if logo_url exists
            has_logo = False
            if 'profile' in data and 'logo_url' in data['profile']:
                has_logo = True
            elif 'logo_url' in data:
                has_logo = True
            
            logo_status = "✓" if has_logo else "✗"
            print(f"→ {university_id} {logo_status}...")
            
            if index_university(es_client, university_id, data):
                print(f"  ✓ Indexed")
                indexed += 1
            else:
                failed.append(university_id)
        
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed.append(university_id)
    
    print("-" * 60)
    print(f"\nSummary:")
    print(f"  Indexed: {indexed}/{len(json_files)}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed:")
        for uni in failed:
            print(f"  - {uni}")


if __name__ == "__main__":
    main()
