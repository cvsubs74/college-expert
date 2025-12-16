#!/usr/bin/env python3
"""
Ingest University Profiles via Cloud Function API.

This script:
1. Reads all JSON files from the research directory
2. Sends each profile to the knowledge-base-manager-universities cloud function
3. The cloud function computes soft_fit_category and indexes with ELSER semantic search
"""
import os
import sys
import json
from pathlib import Path

import requests
import time


# Configuration
CLOUD_FUNCTION_URL = os.environ.get(
    'KNOWLEDGE_BASE_UNIVERSITIES_URL',
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app'
)
RESEARCH_DIR = Path(__file__).parent.parent / "agents" / "university_profile_collector" / "research"


def ingest_via_cloud_function(profile: dict) -> dict:
    """
    Ingest a university profile via the cloud function API.
    The cloud function computes soft_fit_category and handles all indexing.
    """
    try:
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json={"profile": profile},
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 min timeout for ELSER processing
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_existing_universities() -> set:
    """Get list of existing university IDs from cloud function."""
    try:
        response = requests.get(CLOUD_FUNCTION_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get('success'):
            return {u['university_id'] for u in data.get('universities', [])}
    except Exception as e:
        print(f"⚠️ Could not fetch existing universities: {e}")
    return set()


def ingest_profiles(skip_existing=True):
    """Ingest all university profiles via cloud function."""
    json_files = list(RESEARCH_DIR.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {RESEARCH_DIR}")
        return
    
    # Get existing IDs if skipping
    existing_ids = list_existing_universities() if skip_existing else set()
    if existing_ids:
        print(f"📋 Found {len(existing_ids)} existing universities in index")
    
    print(f"\n📁 Found {len(json_files)} university profiles to process\n")
    
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            # Load profile
            with open(json_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            
            university_id = profile.get('_id', json_file.stem)
            official_name = profile.get('metadata', {}).get('official_name', university_id)
            
            # Skip if already exists
            if skip_existing and university_id in existing_ids:
                print(f"⏭️  Skipping {official_name} (already indexed)")
                skipped_count += 1
                continue
            
            print(f"📄 Ingesting {official_name}...")
            
            # Call cloud function
            result = ingest_via_cloud_function(profile)
            
            if result.get('success'):
                print(f"  ✅ Indexed: {result.get('official_name', official_name)}")
                success_count += 1
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                error_count += 1
            
            # Small delay between requests
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ❌ Error processing {json_file.name}: {e}")
            error_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Successfully indexed: {success_count}")
    print(f"⏭️  Skipped (already indexed): {skipped_count}")
    print(f"❌ Errors: {error_count}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingest university profiles via cloud function API")
    parser.add_argument("--force", action="store_true", help="Force re-ingest all documents (ignore existing)")
    args = parser.parse_args()
    
    print("="*60)
    print("🎓 University Profile Ingestion via Cloud Function")
    print(f"📡 API: {CLOUD_FUNCTION_URL}")
    print("="*60)
    
    if args.force:
        print("⚠️  Force mode enabled - will re-ingest all universities")
    
    # Ingest profiles
    ingest_profiles(skip_existing=not args.force)
    
    print("\n🎉 Ingestion complete!")
    print("\n📝 Note: Cloud function computes soft_fit_category during ingest.")
    print("   ELSER semantic embeddings are generated automatically.")


if __name__ == "__main__":
    main()
