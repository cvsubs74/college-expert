#!/usr/bin/env python3
"""
Fix university IDs by removing the '_slug' suffix.
This ensures the IDs match what users add to their college lists.
"""
import json
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")

def fix_slug_ids():
    json_files = sorted(RESEARCH_DIR.glob("*.json"))
    fixed = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Check for _id field with _slug suffix
            current_id = data.get('_id', '')
            if current_id.endswith('_slug'):
                new_id = current_id[:-5]  # Remove '_slug'
                data['_id'] = new_id
                
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                fixed.append((json_file.stem, current_id, new_id))
                print(f"✓ Fixed: {current_id} → {new_id}")
                
        except Exception as e:
            print(f"ERROR: {json_file.stem}: {e}")
    
    print(f"\nTotal fixed: {len(fixed)} files")
    return fixed

if __name__ == "__main__":
    fix_slug_ids()
