#!/usr/bin/env python3
"""
Ingest ONLY valid (schema-passing) profiles to Elasticsearch.
"""
import os
import sys
import json
from pathlib import Path
import requests
import time

# Add parent path
sys.path.insert(0, str(Path(__file__).parent.parent))

from model import UniversityProfile

# Configuration
CLOUD_FUNCTION_URL = os.environ.get(
    'KNOWLEDGE_BASE_UNIVERSITIES_URL',
    'https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app'
)
RESEARCH_DIR = Path(__file__).parent / "research"


def is_valid_profile(filepath: Path) -> bool:
    """Check if profile passes Pydantic validation."""
    try:
        data = json.loads(filepath.read_text(encoding='utf-8'))
        UniversityProfile.model_validate(data)
        return True
    except:
        return False


def ingest_via_cloud_function(profile: dict) -> dict:
    """Ingest a profile via cloud function API."""
    try:
        response = requests.post(
            CLOUD_FUNCTION_URL,
            json={"profile": profile},
            headers={"Content-Type": "application/json"},
            timeout=300
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


def main():
    print("="*60)
    print("🎓 Ingesting VALID University Profiles Only")
    print(f"📡 API: {CLOUD_FUNCTION_URL}")
    print("="*60)
    
    # Get all JSON files
    json_files = sorted(RESEARCH_DIR.glob("*.json"))
    print(f"\n📁 Found {len(json_files)} total JSON files")
    
    # Filter to valid profiles only
    valid_files = [f for f in json_files if is_valid_profile(f)]
    print(f"✅ {len(valid_files)} pass validation")
    
    # Get existing IDs
    existing_ids = list_existing_universities()
    print(f"📋 {len(existing_ids)} already in Elasticsearch\n")
    
    success = 0
    skipped = 0
    errors = 0
    
    for filepath in valid_files:
        try:
            data = json.loads(filepath.read_text(encoding='utf-8'))
            
            # Unwrap if needed
            if 'university_profile' in data:
                profile = data['university_profile']
                for key in data:
                    if key != 'university_profile' and key not in profile:
                        profile[key] = data[key]
            else:
                profile = data
            
            university_id = profile.get('_id', filepath.stem)
            name = profile.get('metadata', {}).get('official_name', university_id)
            
            # Skip if exists
            if university_id in existing_ids:
                print(f"⏭️ {name} (exists)")
                skipped += 1
                continue
            
            print(f"📄 Ingesting {name}...", end=" ")
            result = ingest_via_cloud_function(profile)
            
            if result.get('success'):
                print("✅")
                success += 1
            else:
                print(f"❌ {result.get('error', 'Unknown')}")
                errors += 1
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            errors += 1
    
    print(f"\n{'='*50}")
    print(f"✅ Ingested: {success}")
    print(f"⏭️ Skipped: {skipped}")
    print(f"❌ Errors: {errors}")
    print("🎉 Done!")


if __name__ == "__main__":
    main()
